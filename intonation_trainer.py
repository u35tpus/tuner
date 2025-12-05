#!/usr/bin/env python3
"""
Intonation Trainer – Scale-Aware Random Interval & Triad Generator (CLI)

Usage:
  python intonation_trainer.py config.yaml
  python intonation_trainer.py config.yaml --output my_session.mp3

This script implements the functionality described in `docs/spec.txt`.

It attempts to render audio via `fluidsynth` + SoundFont if available.
If not available, it falls back to a simple synthesized tone generator (sine waves).

Dependencies: pyyaml, mido, numpy, pydub

See `requirements.txt` for an installable list.
"""
import argparse
import os
import sys
import tempfile
import shutil
import subprocess
import math
import random
from datetime import datetime

try:
    import yaml
except Exception:
    print("Missing dependency 'pyyaml'. Install with: pip install pyyaml")
    raise

# Try to import pydub for convenient audio handling. If it's missing or
# the system Python lacks the native audioop extension (some macOS builds),
# fall back to a pure-WAV pipeline implemented with `wave` + `numpy`.
PYDUB_AVAILABLE = False
try:
    from pydub import AudioSegment, effects
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

# Fallback helpers (used when pydub is not available)
def read_wav_mono(path):
    with wave.open(path, 'rb') as wf:
        sr = wf.getframerate()
        nchan = wf.getnchannels()
        frames = wf.readframes(wf.getnframes())
        arr = np.frombuffer(frames, dtype=np.int16)
        if nchan > 1:
            arr = arr.reshape(-1, nchan).mean(axis=1).astype(np.int16)
        return arr, sr


def write_wav_mono(path, arr, sr=44100):
    # arr: numpy int16
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(arr.tobytes())


def make_silence_ms(ms, sr=44100):
    length = int(sr * (ms / 1000.0))
    return np.zeros(length, dtype=np.int16)


def normalize_int16(arr):
    if arr.size == 0:
        return arr
    maxv = np.max(np.abs(arr.astype(np.int32)))
    if maxv == 0:
        return arr
    factor = 32767.0 / maxv
    out = (arr.astype(np.float32) * factor).clip(-32767, 32767).astype(np.int16)
    return out


try:
    import mido
    from mido import Message, MidiFile, MidiTrack, bpm2tempo
except Exception:
    print("Missing dependency 'mido'. Install with: pip install mido")
    raise

import numpy as np
import wave


# ------------------------- Utilities ---------------------------------
NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_name_to_midi(name: str) -> int:
    name = name.strip()
    if len(name) < 2:
        raise ValueError(f"Invalid note name: {name}")
    letter = name[0].upper()
    rest = name[1:]
    accidental = 0
    octave_str = ''
    if rest[0] in ('#', 'b', 'B'):
        if rest[0] == '#':
            accidental = 1
        else:
            accidental = -1
        octave_str = rest[1:]
    else:
        octave_str = rest
    octave = int(octave_str)
    semitone = NOTE_BASE[letter] + accidental
    midi = 12 + octave * 12 + semitone
    return midi


def midi_to_freq(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12.0))


SCALE_PATTERNS = {
    'major': [2, 2, 1, 2, 2, 2, 1],
    'natural_minor': [2, 1, 2, 2, 1, 2, 2],
    'harmonic_minor': [2, 1, 2, 2, 1, 3, 1],
    'melodic_minor': [2, 1, 2, 2, 2, 2, 1],
    'dorian': [2, 1, 2, 2, 2, 1, 2],
    'phrygian': [1, 2, 2, 2, 1, 2, 2],
    'lydian': [2, 2, 2, 1, 2, 2, 1],
    'mixolydian': [2, 2, 1, 2, 2, 1, 2],
}


def build_scale_notes(root_midi: int, kind: str):
    if kind in SCALE_PATTERNS:
        pattern = SCALE_PATTERNS[kind]
    else:
        raise ValueError(f"Unknown scale type: {kind}")
    notes = [root_midi]
    cur = root_midi
    for step in pattern:
        cur += step
        notes.append(cur)
    return notes[:-1]


def expand_scale_over_range(scale_root_midi: int, scale_type: str, low_m: int, high_m: int):
    base_scale = build_scale_notes(scale_root_midi % 12 + (scale_root_midi // 12) * 12, scale_type)
    pool = []
    for midi in range(low_m, high_m + 1):
        semis = [n % 12 for n in base_scale]
        if (midi % 12) in semis:
            pool.append(midi)
    return sorted(set(pool))


def parse_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf8') as f:
        return yaml.safe_load(f)


# ---------------------- Exercise generation ---------------------------

def generate_intervals(pool_notes, ascending=True, descending=True, max_interval=12, include_m3=False):
    intervals = []
    n = len(pool_notes)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = pool_notes[i]
            b = pool_notes[j]
            semis = b - a
            if abs(semis) > max_interval:
                continue
            if semis > 0 and not ascending:
                continue
            if semis < 0 and not descending:
                continue
            intervals.append(('interval', a, b))
    unique = []
    seen = set()
    for it in intervals:
        key = (it[1], it[2])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


def generate_triads(scale_notes_single_octave_midi, pool_notes, include_inversions=True, triad_types=('major','minor','diminished')):
    triads = []
    semitone_to_index = {n % 12: i for i, n in enumerate(scale_notes_single_octave_midi)}
    for root in pool_notes:
        root_pc = root % 12
        if root_pc not in semitone_to_index:
            continue
        deg = semitone_to_index[root_pc]
        tri = []
        for offset in (0, 2, 4):
            idx = (deg + offset) % 7
            octave_shift = (deg + offset) // 7
            pitch = (scale_notes_single_octave_midi[idx] - scale_notes_single_octave_midi[0]) + root + octave_shift * 12
            tri.append(pitch)
        a, b, c = tri
        int1 = b - a
        int2 = c - b
        quality = None
        if int1 == 4 and int2 == 3:
            quality = 'major'
        elif int1 == 3 and int2 == 4:
            quality = 'minor'
        elif int1 == 3 and int2 == 3:
            quality = 'diminished'
        else:
            quality = 'other'
        if quality in triad_types:
            triads.append(('triad', tuple(tri)))
            if include_inversions:
                triads.append(('triad', tuple([tri[1], tri[2], tri[0]+12])))
                triads.append(('triad', tuple([tri[2], tri[0]+12, tri[1]+12])))
    uniq = []
    seen = set()
    for t in triads:
        if t[1] not in seen:
            seen.add(t[1])
            uniq.append(t)
    return uniq


# ---------------------- Audio rendering -------------------------------

def render_midi_to_wav(midi_path: str, sf2_path: str, out_wav: str, sample_rate=44100):
    fluidsynth = shutil.which('fluidsynth')
    if not fluidsynth:
        return False
    cmd = [fluidsynth, '-ni', sf2_path, midi_path, '-F', out_wav, '-r', str(sample_rate)]
    subprocess.check_call(cmd)
    return True


def write_midi_for_exercise(events, midi_path, tempo_bpm=120, channel=0):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
    ticks_per_beat = mid.ticks_per_beat
    for note, start, dur, vel in events:
        start_ticks = int(start * (ticks_per_beat * tempo_bpm / 60.0))
        duration_ticks = int(dur * (ticks_per_beat * tempo_bpm / 60.0))
        track.append(Message('note_on', note=note, velocity=vel, time=0))
        track.append(Message('note_off', note=note, velocity=0, time=duration_ticks))
    mid.save(midi_path)


def synth_simple_wav(notes, duration, out_wav, sample_rate=44100, velocity=90):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = np.zeros_like(t)
    for n in notes:
        freq = midi_to_freq(int(n))
        tone = 0.6 * np.sin(2 * np.pi * freq * t) * np.exp(-3 * t)
        data += tone
    maxv = np.max(np.abs(data))
    if maxv > 0:
        data = data / maxv * 0.9
    audio = (data * 32767).astype(np.int16)
    with wave.open(out_wav, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


# ---------------------- Main program ---------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--output', '-o', help='Output filename (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Do not render audio; only write a text log of generated exercises')
    parser.add_argument('--verbose', action='store_true', help='Also write a text log of generated exercises alongside the audio output')
    parser.add_argument('--text-file', help='Explicit path for the text log (overrides default)')
    parser.add_argument('--max-duration', type=int, default=600, help='Maximum session duration in seconds (default 600=10 min)')
    args = parser.parse_args()

    cfg = parse_yaml(args.config)
    outcfg = cfg.get('output', {})
    fname_template = outcfg.get('filename', 'Intonation_{scale}_{date}.mp3')
    fmt = outcfg.get('format', 'mp3')
    normalize_lufs = outcfg.get('normalize_lufs', -16)
    
    # Get max_duration from config, then override with CLI if provided
    config_max_duration = cfg.get('max_duration', 600)
    # CLI args.max_duration has default=600; we use it only if different from default
    # OR we can simplify: always prefer CLI if explicitly passed
    # For simplicity: use config value, but CLI can override
    if args.max_duration != 600:  # CLI was explicitly set
        max_duration_seconds = args.max_duration
    else:
        max_duration_seconds = config_max_duration

    vocal = cfg.get('vocal_range', {})
    lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
    highest = note_name_to_midi(vocal.get('highest_note', 'A4'))

    scale_cfg = cfg.get('scale', {})
    if 'notes' in scale_cfg and scale_cfg['notes']:
        custom_notes = [note_name_to_midi(n) for n in scale_cfg['notes']]
        pool = [n for n in custom_notes if lowest <= n <= highest]
        scale_single_octave = sorted(set([n % 12 + 12 for n in custom_notes]))[:7]
    else:
        root = note_name_to_midi(scale_cfg.get('root', 'A3'))
        stype = scale_cfg.get('type', 'natural_minor')
        pool = expand_scale_over_range(root, stype, lowest, highest)
        scale_single_octave = build_scale_notes(root, stype)

    content = cfg.get('content', {})
    intervals_cfg = content.get('intervals', {})
    triads_cfg = content.get('triads', {})

    max_interval_name = intervals_cfg.get('max_interval', 'perfect_octave')
    max_interval = 12
    include_m3 = intervals_cfg.get('include_minor_3rd_even_in_major', True)
    ascending = intervals_cfg.get('ascending', True)
    descending = intervals_cfg.get('descending', True)

    repetitions = cfg.get('repetitions_per_exercise', 10)
    seed = cfg.get('random_seed', None)
    if seed is not None:
        random.seed(seed)

    exercises = []
    exercises += generate_intervals(pool, ascending=ascending, descending=descending, max_interval=max_interval, include_m3=include_m3)
    if triads_cfg.get('enabled', True):
        tri_types = triads_cfg.get('types', ['major','minor','diminished'])
        triads = generate_triads(scale_single_octave, pool, include_inversions=triads_cfg.get('include_inversions', True), triad_types=tri_types)
        exercises += triads

    random.shuffle(exercises)
    final_list = []
    # Calculate actual repetitions based on max_duration target
    note_duration = cfg.get('timing', {}).get('note_duration', 1.8)
    pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
    # Each exercise takes ~note_duration + pause_between_reps seconds
    time_per_exercise = note_duration + pause_between_reps
    max_exercises = int(max_duration_seconds / time_per_exercise)
    if max_exercises < 1:
        max_exercises = 1
    
    # Build final list with enough exercises to fill (or approach) max_duration
    final_list = []
    if len(exercises) > 0:
        # Try to fit as many repetitions as possible
        actual_reps = max(1, max_exercises // len(exercises))
        for ex in exercises:
            for _ in range(actual_reps):
                final_list.append(ex)
                if len(final_list) >= max_exercises:
                    break
            if len(final_list) >= max_exercises:
                break
    
    # Calculate estimated final duration
    estimated_duration = len(final_list) * time_per_exercise
    
    if not args.dry_run:
        print(f'Target duration: {max_duration_seconds}s ({max_duration_seconds//60}m {max_duration_seconds%60}s)')
        print(f'Estimated duration: ~{int(estimated_duration)}s ({int(estimated_duration)//60}m {int(estimated_duration)%60}s)')
        print(f'Generated {len(final_list)} exercises from {len(exercises)} unique exercise(s)')
        print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale_name = scale_cfg.get('name', 'scale')
    out_name = args.output or fname_template.format(scale=scale_name.replace(' ', '_'), date=timestamp)

    def midi_to_note_name(midi: int) -> str:
        # Convert MIDI number back to a note name like C4, Db3
        octave = (midi // 12) - 1
        pc = midi % 12
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        name = names[pc]
        return f"{name}{octave}"

    def write_text_log(path: str, exercises_list):
        with open(path, 'w', encoding='utf8') as f:
            f.write(f"Intonation Trainer Log\n")
            f.write(f"Scale: {scale_name}\n")
            f.write(f"Generated: {len(exercises_list)} exercises (with repetitions)\n\n")
            for i, ex in enumerate(exercises_list, start=1):
                if ex[0] == 'interval':
                    a, b = ex[1], ex[2]
                    f.write(f"{i:04d}: INTERVAL  {midi_to_note_name(a)} ({a}) -> {midi_to_note_name(b)} ({b})\n")
                elif ex[0] == 'triad':
                    notes = ex[1]
                    names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes])
                    f.write(f"{i:04d}: TRIAD     {names}\n")
                else:
                    f.write(f"{i:04d}: UNKNOWN   {ex}\n")
        print(f'Wrote text log to {path}')

    tmpdir = tempfile.mkdtemp(prefix='intonation_')
    parts = []
    # If dry run requested, write only the text log and exit (no audio rendering)
    if args.dry_run:
        text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
        write_text_log(text_path, final_list)
        shutil.rmtree(tmpdir)
        return

    try:
        sf_cfg = cfg.get('sound', {})
        method = sf_cfg.get('method', 'soundfont')
        sf2_path = sf_cfg.get('soundfont_path', 'piano/SalamanderGrandPiano.sf2')
        velocity = sf_cfg.get('velocity', 90)

        for idx, ex in enumerate(final_list):
            typ = ex[0]
            out_wav = os.path.join(tmpdir, f'ex_{idx:04d}.wav')
            if typ == 'interval':
                a, b = ex[1], ex[2]
                midi_path = os.path.join(tmpdir, f'ex_{idx:04d}.mid')
                mid = MidiFile()
                track = MidiTrack()
                mid.tracks.append(track)
                tempo_bpm = cfg.get('timing', {}).get('intro_bpm', 120)
                track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
                track.append(Message('note_on', note=int(a), velocity=velocity, time=0))
                dur = cfg.get('timing', {}).get('note_duration', 1.8)
                ticks = int(mid.ticks_per_beat * (dur * tempo_bpm / 60.0))
                track.append(Message('note_off', note=int(a), velocity=0, time=ticks))
                track.append(Message('note_on', note=int(b), velocity=velocity, time=0))
                track.append(Message('note_off', note=int(b), velocity=0, time=ticks))
                mid.save(midi_path)
                rendered = False
                if method == 'soundfont' and os.path.exists(sf2_path):
                    try:
                        rendered = render_midi_to_wav(midi_path, sf2_path, out_wav)
                    except Exception:
                        rendered = False
                if not rendered:
                    a_wav = os.path.join(tmpdir, f'a_{idx}.wav')
                    b_wav = os.path.join(tmpdir, f'b_{idx}.wav')
                    synth_simple_wav([a], dur, a_wav)
                    synth_simple_wav([b], dur, b_wav)
                    if PYDUB_AVAILABLE:
                        seg = AudioSegment.from_wav(a_wav) + AudioSegment.silent(duration=100) + AudioSegment.from_wav(b_wav)
                        seg.export(out_wav, format='wav')
                    else:
                        arr_a, sr = read_wav_mono(a_wav)
                        arr_b, sr2 = read_wav_mono(b_wav)
                        silence = make_silence_ms(100, sr)
                        combined = np.concatenate([arr_a, silence, arr_b])
                        combined = normalize_int16(combined)
                        write_wav_mono(out_wav, combined, sr)
            elif typ == 'triad':
                notes = list(ex[1])
                midi_path = os.path.join(tmpdir, f'ex_{idx:04d}.mid')
                mid = MidiFile()
                track = MidiTrack()
                mid.tracks.append(track)
                tempo_bpm = cfg.get('timing', {}).get('intro_bpm', 120)
                track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
                dur = cfg.get('timing', {}).get('note_duration', 1.8)
                ticks = int(mid.ticks_per_beat * (dur * tempo_bpm / 60.0))
                for n in notes:
                    track.append(Message('note_on', note=int(n), velocity=velocity, time=0))
                track.append(Message('note_off', note=int(notes[0]), velocity=0, time=ticks))
                for n in notes[1:]:
                    track.append(Message('note_off', note=int(n), velocity=0, time=0))
                mid.save(midi_path)
                rendered = False
                if method == 'soundfont' and os.path.exists(sf2_path):
                    try:
                        rendered = render_midi_to_wav(midi_path, sf2_path, out_wav)
                    except Exception:
                        rendered = False
                if not rendered:
                    synth_simple_wav(notes, cfg.get('timing', {}).get('note_duration', 1.8), out_wav)
            else:
                continue
            if PYDUB_AVAILABLE:
                parts.append(AudioSegment.from_wav(out_wav))
            else:
                arr, sr = read_wav_mono(out_wav)
                parts.append((arr, sr))

        if not parts:
            print('No exercises generated. Exiting.')
            return

        pause_rep = int(cfg.get('timing', {}).get('pause_between_reps', 1.0) * 1000)
        pause_block = int(cfg.get('timing', {}).get('pause_between_blocks', 4.0) * 1000)
        out_ext = fmt.lower()
        if PYDUB_AVAILABLE:
            session = AudioSegment.silent(duration=0)
            for i, p in enumerate(parts):
                session += p + AudioSegment.silent(duration=pause_rep)
            session = effects.normalize(session)
            if not out_name.lower().endswith('.' + out_ext):
                out_name = out_name + '.' + out_ext
            session.export(out_name, format=out_ext)
            print(f'Wrote session to {out_name}')
        else:
            # Build combined numpy array (mono, int16)
            target_sr = 44100
            combined = np.zeros(0, dtype=np.int16)
            for i, (arr, sr) in enumerate(parts):
                if sr != target_sr:
                    # simple resample via numpy (nearest) if needed
                    factor = float(target_sr) / float(sr)
                    indices = (np.arange(int(len(arr) * factor)) / factor).astype(int)
                    arr = arr[indices]
                combined = np.concatenate([combined, arr, make_silence_ms(pause_rep, target_sr)])
            combined = normalize_int16(combined)
            # Write WAV; if target format is not WAV, try ffmpeg to convert
            if out_ext == 'wav':
                if not out_name.lower().endswith('.wav'):
                    out_name = out_name + '.wav'
                write_wav_mono(out_name, combined, target_sr)
                print(f'Wrote session WAV to {out_name}')
            else:
                temp_wav = os.path.join(tmpdir, 'session.wav')
                write_wav_mono(temp_wav, combined, target_sr)
                ffmpeg = shutil.which('ffmpeg')
                if ffmpeg:
                    if not out_name.lower().endswith('.' + out_ext):
                        out_name = out_name + '.' + out_ext
                    cmd = [ffmpeg, '-y', '-i', temp_wav, out_name]
                    subprocess.check_call(cmd)
                    print(f'Wrote session to {out_name} (via ffmpeg)')
                    try:
                        os.remove(temp_wav)
                    except Exception:
                        pass
                else:
                    print(f'ffmpeg not found — wrote WAV to {temp_wav}. To get {out_ext}, install ffmpeg and re-run.')
        # If verbose requested, always write the text log alongside audio output
        if args.verbose:
            text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
            write_text_log(text_path, final_list)

    finally:
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()
