def preparse_abc_notes(abc_str, default_length=1.0):
    """Pre-Parsing: Check each note in ABC string before main parsing. Returns error if any note fails."""
    original_str = abc_str
    abc_str = abc_str.replace('|', ' ')
    note_strs = [n.strip() for n in abc_str.split() if n.strip()]
    for i, note_str in enumerate(note_strs):
        parsed = parse_abc_note_with_duration(note_str, default_length)
        if parsed is None or (isinstance(parsed, tuple) and len(parsed) == 2 and parsed[0] is None):
            error_msg = parsed[1] if parsed and len(parsed) == 2 else "Unknown error"
            context = " ".join(note_strs[max(0,i-1):min(len(note_strs),i+2)])
            return (None, f"Pre-parsing error: Note '{note_str}' at position {i+1} in sequence '{original_str}' did not pass pre-check. Reason: {error_msg}\nContext: ...{context}...")
    return True
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

# Audio rendering has been removed; this tool produces MIDI files only.


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


def parse_abc_note_with_duration(note_str, default_length=1.0):
    """Parse ABC note string with optional duration suffix.
    
    Examples:
      "C4" -> (60, 1.0)  [quarter note at default length]
      "C4/2" -> (60, 0.5)  [eighth note, half the length]
      "C4*2" or "C42" -> (60, 2.0)  [half note, double the length]
      "G#3" or "G3#" -> (56, 1.0)
      "C4:1.5" -> (60, 1.5)  [explicit duration]
      "z2" -> ('rest', 2.0)  [rest with duration 2]
    
    Args:
        note_str: String like "C4", "C42", "C4/2", "G#3*2", "z2"
        default_length: Base unit length in beats (typically 1.0 for quarter note)
    
    Returns:
        Tuple (midi_number, duration_in_beats) or ('rest', duration) for rests
        or tuple (None, error_message) if parsing fails
    """
    import re
    note_str = note_str.strip()
    
    if not note_str:
        return (None, "Empty note string")
    
    # Check for rest notation (z, Z, or x)
    rest_match = re.match(r'^([zZx])([\d.:/*]*)$', note_str)
    if rest_match:
        rest_symbol = rest_match.group(1)
        length_part = rest_match.group(2)
        duration = default_length
        if length_part:
            try:
                duration = _parse_duration_modifier(length_part, default_length)
            except ValueError as e:
                return (None, f"Invalid duration '{length_part}' for rest '{rest_symbol}': {e}")
        return ('rest', duration)
    
    # Try to parse as note: letter + optional accidental (before or after octave) + octave + optional duration
    # Support patterns: C#4, C4#, Db4, D4b, C4:1.5, C42, C4/2, C4*2
    match = re.match(r'^([A-G])([#b]?)(\d)([#b]?)([\d.:/*]*)$', note_str, re.IGNORECASE)
    if not match:
        return (None, f"Invalid note format '{note_str}'. Expected format: <Letter>[#/b]<Octave>[duration], e.g., 'C4', 'F#3', 'G4:1.5', 'A#42', 'Bb4/2'")
    
    letter = match.group(1).upper()
    accidental_before = match.group(2)
    octave = match.group(3)
    accidental_after = match.group(4)
    length_part = match.group(5)
    
    # Combine accidentals (prefer one before octave, but accept after)
    accidental = accidental_before or accidental_after
    if accidental_before and accidental_after:
        return (None, f"Conflicting accidentals in '{note_str}': both '{accidental_before}' (before octave) and '{accidental_after}' (after octave) specified")
    
    note_name_part = letter + accidental + octave
    
    try:
        midi = note_name_to_midi(note_name_part)
    except Exception as e:
        return (None, f"Could not convert '{note_name_part}' to MIDI: {e}")
    
    # Parse duration modifier
    duration = default_length
    if length_part:
        try:
            duration = _parse_duration_modifier(length_part, default_length)
        except ValueError as e:
            return (None, f"Invalid duration '{length_part}' for note '{note_name_part}': {e}")
    
    return (midi, duration)


def _parse_duration_modifier(length_str, default_length):
    """Parse duration modifier string and return duration in beats.
    
    Supports:
      - Direct multiplier: "2" means 2x length
      - Division: "/2" means half length
      - Multiplication: "*2" means 2x length
      - Explicit duration: ":1.5" means 1.5 beats
    
    Raises ValueError if parsing fails.
    """
    if not length_str:
        return default_length
    
    if length_str.startswith(':'):
        # Explicit duration: :1.5
        try:
            return float(length_str[1:])
        except ValueError:
            raise ValueError(f"Cannot parse explicit duration '{length_str[1:]}' as number")
    elif length_str.startswith('/'):
        # Division: /2 means half duration
        try:
            divisor = float(length_str[1:])
            if divisor == 0:
                raise ValueError("Cannot divide by zero")
            return default_length / divisor
        except ValueError as e:
            raise ValueError(f"Cannot parse divisor '{length_str[1:]}': {e}")
    elif length_str.startswith('*'):
        # Multiplication: *2 means double duration
        try:
            multiplier = float(length_str[1:])
            return default_length * multiplier
        except ValueError:
            raise ValueError(f"Cannot parse multiplier '{length_str[1:]}' as number")
    else:
        # Direct multiplier: "2" means 2x length (ABC standard notation)
        try:
            multiplier = float(length_str)
            return default_length * multiplier
        except ValueError:
            raise ValueError(f"Cannot parse '{length_str}' as number")


def parse_abc_sequence(abc_str, default_length=1.0):
    """Parse ABC notation sequence with durations into list of (midi, duration) tuples.
    
    ABC format: |D#3 A#2 C4| C4 |  or  |C4 D42 E4/2 F4|
    Pipes (|) mark bar lines and are ignored.
    Notes are space-separated within bars.
    Default length (L) can be specified (e.g., 1.0 = quarter note).
    Supports rests: z, Z, or x with optional duration.
    
    Args:
        abc_str: ABC notation string (e.g., "|C4 D42 E4|" or "z2 | B3 | E4:1.5")
        default_length: Unit length in beats (default 1.0 for quarter note)
    
    Returns:
        List of (midi_number, duration) tuples (or ('rest', duration) for rests)
        or tuple (None, error_message) if parsing fails
    """
    # Pre-parsing check
    precheck = preparse_abc_notes(abc_str, default_length)
    if precheck is not True:
        return precheck
    original_str = abc_str
    abc_str = abc_str.replace('|', ' ')
    note_strs = [n.strip() for n in abc_str.split() if n.strip()]
    if not note_strs:
        return (None, f"No notes found in ABC sequence '{original_str}'")
    notes_with_durations = []
    for i, note_str in enumerate(note_strs):
        parsed = parse_abc_note_with_duration(note_str, default_length)
        if parsed is None or (isinstance(parsed, tuple) and len(parsed) == 2 and parsed[0] is None):
            error_msg = parsed[1] if parsed and len(parsed) == 2 else "Unknown error"
            position_info = f"at position {i+1} ('{note_str}')"
            context = " ".join(note_strs[max(0,i-1):min(len(note_strs),i+2)])
            return (None, f"Failed to parse ABC sequence '{original_str}' {position_info}.\nError: {error_msg}\nContext: ...{context}...")
        notes_with_durations.append(parsed)
    return notes_with_durations


def parse_sequences_from_config(sequences_cfg, default_unit_length=1.0):
    """Parse sequences from config and return list of exercises.
    
    Supports multiple formats:
    1. Comma-separated notes (old): "D#3, A#2, C4"
    2. ABC notation (simple): "|D#3 A#2 C4|"
    3. ABC notation with durations: "|C4 D42 E4/2|" (requires default_unit_length)
    4. Full structure with signature, L, notes:
       sequences:
         signature: "4/4"
         unit_length: 0.25  # or L: 1/4
         notes: ["|C4 D42|", "..."]
    
    Returns list of ('sequence', notes_with_durations) exercises.
    notes_with_durations is list of (midi, duration) tuples.
    """
    exercises = []
    if not sequences_cfg:
        return exercises
    
    # Handle structured format (dict with signature, L, notes)
    if isinstance(sequences_cfg, dict):
        notes_list = sequences_cfg.get('notes', [])
        unit_length_val = sequences_cfg.get('unit_length', 1.0)
        
        # Also support 'L' format (e.g., "1/4" -> 0.25)
        if 'L' in sequences_cfg:
            L_str = sequences_cfg['L']
            if isinstance(L_str, str) and '/' in L_str:
                parts = L_str.split('/')
                unit_length_val = float(parts[0]) / float(parts[1])
        
        for seq_str in notes_list:
            notes_with_dur = parse_abc_sequence(seq_str, unit_length_val)
            if notes_with_dur and not (isinstance(notes_with_dur, tuple) and notes_with_dur[0] is None):
                exercises.append(('sequence', notes_with_dur))
            else:
                error_msg = notes_with_dur[1] if notes_with_dur and len(notes_with_dur) == 2 else "Unknown error"
                print(f'Warning: {error_msg}')
        return exercises
    
    # Handle list format (simple strings, backward compatible)
    for seq_str in sequences_cfg:
        # Detect format: if contains pipe (|), treat as ABC; else as comma-separated
        if '|' in seq_str:
            # ABC format (with optional durations)
            notes_with_dur = parse_abc_sequence(seq_str, default_unit_length)
            if notes_with_dur and not (isinstance(notes_with_dur, tuple) and notes_with_dur[0] is None):
                exercises.append(('sequence', notes_with_dur))
            else:
                error_msg = notes_with_dur[1] if notes_with_dur and len(notes_with_dur) == 2 else "Unknown error"
                print(f'Warning: {error_msg}')
        else:
            # Comma-separated format (backward compatible, no durations)
            note_names = [n.strip() for n in seq_str.split(',')]
            try:
                notes = [(note_name_to_midi(n), default_unit_length) for n in note_names]
                exercises.append(('sequence', notes))
            except Exception as e:
                print(f'Warning: Could not parse sequence "{seq_str}": {e}')
    
    return exercises


# ------------------ Helpers extracted from main for testing -----------------
def midi_to_note_name(midi: int) -> str:
    octave = (midi // 12) - 1
    pc = midi % 12
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    name = names[pc]
    return f"{name}{octave}"


def write_text_log(path: str, exercises_list, ticks_per_beat: int = None, scale_name: str = 'session'):
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
            elif ex[0] == 'sequence':
                notes_with_dur = ex[1]
                if notes_with_dur and isinstance(notes_with_dur[0], tuple):
                    if ticks_per_beat is None:
                        ticks_per_beat = 480
                    parts = []
                    for n, d in notes_with_dur:
                        name = midi_to_note_name(n)
                        midi_num = int(n)
                        beats = float(d)
                        ticks = int(beats * ticks_per_beat)
                        parts.append(f"{name}({midi_num}):d{beats:.2f}:t{ticks}")
                    names = ' '.join(parts)
                else:
                    names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes_with_dur])
                f.write(f"{i:04d}: SEQUENCE  {names}\n")
            else:
                f.write(f"{i:04d}: UNKNOWN   {ex}\n")
    return path


def parse_text_log(path: str):
    """Parse exercises from a text log file generated by write_text_log."""
    exercises = []
    try:
        with open(path, 'r', encoding='utf8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                parts = line.split(':', 1)
                if len(parts) < 2:
                    continue
                content = parts[1].strip()
                if content.startswith('INTERVAL'):
                    rest = content[len('INTERVAL'):].strip()
                    import re
                    matches = re.findall(r'\((\d+)\)', rest)
                    if len(matches) >= 2:
                        a, b = int(matches[0]), int(matches[1])
                        exercises.append(('interval', a, b))
                elif content.startswith('TRIAD'):
                    rest = content[len('TRIAD'):].strip()
                    import re
                    matches = re.findall(r'\((\d+)\)', rest)
                    if len(matches) >= 3:
                        notes = tuple(int(m) for m in matches)
                        exercises.append(('triad', notes))
                elif content.startswith('SEQUENCE'):
                    # parse simple sequence names (no durations)
                    rest = content[len('SEQUENCE'):].strip()
                    import re
                    matches = re.findall(r'([A-G][#b]?\d)\((\d+)\)', rest)
                    if matches:
                        notes = [int(m[1]) for m in matches]
                        exercises.append(('sequence', notes))
    except Exception:
        return []
    return exercises


def build_final_list(cfg: dict, args) -> tuple:
    """Construct the final_list of exercises based on cfg and CLI-like args.

    Returns: (final_list, scale_name, out_name, estimated_duration)
    """
    # Get max_duration from config, then override with CLI if provided
    config_max_duration = cfg.get('max_duration', 600)
    if getattr(args, 'max_duration', 600) != 600:
        max_duration_seconds = args.max_duration
    else:
        max_duration_seconds = config_max_duration

    vocal = cfg.get('vocal_range', {})
    lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
    highest = note_name_to_midi(vocal.get('highest_note', 'A4'))

    repetitions = cfg.get('repetitions_per_exercise', 10)
    seed = cfg.get('random_seed', None)
    if seed is not None:
        random.seed(seed)

    sequences_cfg = cfg.get('sequences', None)

    scale_name = 'session'

    if getattr(args, 'from_text', None):
        exercises = parse_text_log(args.from_text)
    elif sequences_cfg:
        exercises = parse_sequences_from_config(sequences_cfg)
    else:
        scale_cfg = cfg.get('scale', {})
        scale_name = scale_cfg.get('name', 'scale')
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

        max_interval = 12
        include_m3 = intervals_cfg.get('include_minor_3rd_even_in_major', True)
        ascending = intervals_cfg.get('ascending', True)
        descending = intervals_cfg.get('descending', True)

        exercises = []
        exercises += generate_intervals(pool, ascending=ascending, descending=descending, max_interval=max_interval, include_m3=include_m3)
        if triads_cfg.get('enabled', True):
            tri_types = triads_cfg.get('types', ['major','minor','diminished'])
            triads = generate_triads(
                scale_single_octave,
                pool,
                include_inversions=triads_cfg.get('include_inversions', True),
                triad_types=tri_types,
                low=lowest,
                high=highest,
            )
            exercises += triads

    random.shuffle(exercises)
    # timing
    note_duration = cfg.get('timing', {}).get('note_duration', 1.8)
    pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
    time_per_exercise = note_duration + pause_between_reps

    exercises_count_cfg = cfg.get('exercises_count', None)
    repetitions_per_exercise_cfg = cfg.get('repetitions_per_exercise', 1)

    exercises_count = None
    if exercises_count_cfg is not None:
        try:
            exercises_count = int(exercises_count_cfg)
        except Exception:
            exercises_count = None

    actual_reps = 1
    max_unique_exercises = len(exercises) if len(exercises) > 0 else 1

    if repetitions_per_exercise_cfg > 1:
        actual_reps = repetitions_per_exercise_cfg
    elif exercises_count is not None and exercises_count > 0:
        actual_reps = 1
        max_unique_exercises = exercises_count
    else:
        max_total_exercises = int(max_duration_seconds / time_per_exercise)
        if max_total_exercises < 1:
            max_total_exercises = 1
        if max_unique_exercises > 0:
            actual_reps = max(1, max_total_exercises // max_unique_exercises)
        else:
            actual_reps = 1

    final_list = []
    if len(exercises) > 0:
        if getattr(args, 'from_text', None):
            if exercises_count is not None and exercises_count > 0:
                final_list = exercises[:exercises_count]
            else:
                max_count = int(max_duration_seconds / time_per_exercise)
                final_list = exercises[:max(1, max_count)]
        else:
            for ex in exercises:
                if exercises_count is not None and len(final_list) >= exercises_count:
                    break
                for _ in range(actual_reps):
                    final_list.append(ex)
                    if exercises_count is not None and len(final_list) >= exercises_count:
                        break

    estimated_duration = len(final_list) * time_per_exercise

    # determine out_name similar to main
    outcfg = cfg.get('output', {})
    fname_template = outcfg.get('filename', 'Intonation_{scale}_{date}.mp3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale_label = cfg.get('scale', {}).get('name', scale_name)
    out_name = getattr(args, 'output', None) or fname_template.format(scale=scale_label.replace(' ', '_'), date=timestamp)

    return final_list, scale_name, out_name, estimated_duration



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


def generate_triads(scale_notes_single_octave_midi, pool_notes, include_inversions=True, triad_types=('major','minor','diminished'), low=None, high=None):
    """Generate triads from a pool of notes.

    If `low` and/or `high` are provided, any generated triad (including inversions)
    that contains notes outside the inclusive range [low, high] will be discarded.
    """
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

        def in_range(notes_tuple):
            if low is None and high is None:
                return True
            for p in notes_tuple:
                if low is not None and p < low:
                    return False
                if high is not None and p > high:
                    return False
            return True

        if quality in triad_types:
            base_tri = tuple(tri)
            if in_range(base_tri):
                triads.append(('triad', base_tri))
            if include_inversions:
                inv1 = tuple([tri[1], tri[2], tri[0] + 12])
                inv2 = tuple([tri[2], tri[0] + 12, tri[1] + 12])
                if in_range(inv1):
                    triads.append(('triad', inv1))
                if in_range(inv2):
                    triads.append(('triad', inv2))

    uniq = []
    seen = set()
    for t in triads:
        if t[1] not in seen:
            seen.add(t[1])
            uniq.append(t)
    return uniq


# ---------------------- Audio rendering -------------------------------

# Audio rendering via external tools removed. MIDI-only output maintained.


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


def make_silence_ms(ms, sr=44100):
    """Return a numpy int16 array of silence for given milliseconds at sample rate sr."""
    n = int(sr * (ms / 1000.0))
    return np.zeros(n, dtype=np.int16)


def normalize_int16(arr):
    """Normalize an array to int16 amplitude range [-32767,32767].

    If `arr` is already int16, scale it so the maximum absolute value becomes 32767.
    If `arr` is float, scale by its max absolute value and convert to int16.
    """
    a = np.asarray(arr)
    if a.size == 0:
        return a.astype(np.int16)
    if a.dtype == np.int16:
        mx = np.max(np.abs(a))
        if mx == 0:
            return a
        scale = 32767.0 / float(mx)
        out = (a.astype(np.float64) * scale).astype(np.int16)
        return out
    else:
        mx = np.max(np.abs(a))
        if mx == 0:
            return a.astype(np.int16)
        scaled = a.astype(np.float64) / mx * 32767.0
        return scaled.astype(np.int16)


def write_wav_mono(path, arr, sr=44100):
    """Write a mono int16 numpy array to a WAV file."""
    a = np.asarray(arr)
    if a.dtype != np.int16:
        a = normalize_int16(a)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(a.tobytes())


def read_wav_mono(path):
    """Read a mono WAV file and return (numpy int16 array, sample_rate)."""
    with wave.open(path, 'rb') as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sampwidth != 2:
        raise RuntimeError('Unsupported sample width')
    arr = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        # Reduce to mono by taking first channel
        arr = arr[::channels]
    return arr, sr


# ---------------------- Main program ---------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--output', '-o', help='Output filename (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Do not render audio; only write a text log of generated exercises')
    parser.add_argument('--verbose', action='store_true', help='Also write a text log of generated exercises alongside the audio output')
    parser.add_argument('--text-file', help='Explicit path for the text log (overrides default)')
    parser.add_argument('--max-duration', type=int, default=600, help='Maximum session duration in seconds (default 600=10 min)')
    parser.add_argument('--from-text', help='Read exercises from a text log file instead of generating them from config')
    args = parser.parse_args()

    cfg = parse_yaml(args.config)
    outcfg = cfg.get('output', {})
    fname_template = outcfg.get('filename', 'Intonation_{scale}_{date}.mp3')
    fmt = outcfg.get('format', 'mp3')
    normalize_lufs = outcfg.get('normalize_lufs', -16)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale_name = cfg.get('scale', {}).get('name', 'scale')
    out_name = args.output or fname_template.format(scale=scale_name.replace(' ', '_'), date=timestamp)

    # Define helper functions early so they can be used throughout
    def midi_to_note_name(midi: int) -> str:
        # Convert MIDI number back to a note name like C4, Db3
        octave = (midi // 12) - 1
        pc = midi % 12
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        name = names[pc]
        return f"{name}{octave}"

    def write_text_log(path: str, exercises_list, ticks_per_beat: int = None):
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
                elif ex[0] == 'sequence':
                    notes_with_dur = ex[1]
                    # Handle both old format (just MIDI numbers) and new format (with durations)
                    if notes_with_dur and isinstance(notes_with_dur[0], tuple):
                        # New format: list of (midi, duration) tuples
                        # Include duration in beats and ticks
                        if ticks_per_beat is None:
                            ticks_per_beat = 480
                        parts = []
                        for n, d in notes_with_dur:
                            name = midi_to_note_name(n)
                            midi_num = int(n)
                            beats = float(d)
                            ticks = int(beats * ticks_per_beat)
                            parts.append(f"{name}({midi_num}):d{beats:.2f}:t{ticks}")
                        names = ' '.join(parts)
                    else:
                        # Old format: just MIDI numbers
                        names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes_with_dur])
                    f.write(f"{i:04d}: SEQUENCE  {names}\n")
                else:
                    f.write(f"{i:04d}: UNKNOWN   {ex}\n")
        print(f'Wrote text log to {path}')

    def parse_text_log(path: str):
        """Parse exercises from a text log file generated by write_text_log."""
        exercises = []
        try:
            with open(path, 'r', encoding='utf8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    # Format: "0001: INTERVAL  C#3 (49) -> A#2 (46)"
                    #         "0001: TRIAD     A3(57) C#4(61) E4(64)"
                    parts = line.split(':', 1)
                    if len(parts) < 2:
                        continue
                    content = parts[1].strip()
                    if content.startswith('INTERVAL'):
                        # Parse: "INTERVAL  C#3 (49) -> A#2 (46)"
                        rest = content[len('INTERVAL'):].strip()
                        # Extract MIDI numbers in parentheses
                        import re
                        matches = re.findall(r'\((\d+)\)', rest)
                        if len(matches) >= 2:
                            a, b = int(matches[0]), int(matches[1])
                            exercises.append(('interval', a, b))
                    elif content.startswith('TRIAD'):
                        # Parse: "TRIAD     A3(57) C#4(61) E4(64)"
                        rest = content[len('TRIAD'):].strip()
                        import re
                        matches = re.findall(r'\((\d+)\)', rest)
                        if len(matches) >= 3:
                            notes = tuple(int(m) for m in matches)
                            exercises.append(('triad', notes))
        except Exception as e:
            print(f'Error parsing text log {path}: {e}')
            return []
        return exercises

    # Get max_duration from config, then override with CLI if provided
    config_max_duration = cfg.get('max_duration', 600)
    if args.max_duration != 600:  # CLI was explicitly set
        max_duration_seconds = args.max_duration
    else:
        max_duration_seconds = config_max_duration

    vocal = cfg.get('vocal_range', {})
    lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
    highest = note_name_to_midi(vocal.get('highest_note', 'A4'))

    repetitions = cfg.get('repetitions_per_exercise', 10)
    seed = cfg.get('random_seed', None)
    if seed is not None:
        random.seed(seed)

    # Check if sequences are specified in config
    sequences_cfg = cfg.get('sequences', None)
    
    # Set default scale_name that will be used in output filename
    scale_name = 'session'
    
    # If --from-text is provided, load exercises from text file instead of generating
    if args.from_text:
        exercises = parse_text_log(args.from_text)
        if not exercises:
            print(f'No exercises loaded from {args.from_text}. Exiting.')
            return
        print(f'Loaded {len(exercises)} exercises from {args.from_text}')
    elif sequences_cfg:
        # Use explicit note sequences if provided
        exercises = parse_sequences_from_config(sequences_cfg)
        if not exercises:
            print('No valid sequences found in config. Exiting.')
            return
        print(f'Loaded {len(exercises)} sequences from config')
    else:
        # Normal mode: generate exercises from scale and content
        scale_cfg = cfg.get('scale', {})
        scale_name = scale_cfg.get('name', 'scale')
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

        # Generate exercises from config
        exercises = []
        exercises += generate_intervals(pool, ascending=ascending, descending=descending, max_interval=max_interval, include_m3=include_m3)
        if triads_cfg.get('enabled', True):
            tri_types = triads_cfg.get('types', ['major','minor','diminished'])
            triads = generate_triads(
                scale_single_octave,
                pool,
                include_inversions=triads_cfg.get('include_inversions', True),
                triad_types=tri_types,
                low=lowest,
                high=highest,
            )
            exercises += triads

    random.shuffle(exercises)
    final_list = []
    # Calculate actual repetitions based on max_duration target
    note_duration = cfg.get('timing', {}).get('note_duration', 1.8)
    pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
    # Each exercise takes ~note_duration + pause_between_reps seconds
    time_per_exercise = note_duration + pause_between_reps
    
    # Get configuration for exercise count and repetitions
    exercises_count_cfg = cfg.get('exercises_count', None)
    repetitions_per_exercise_cfg = cfg.get('repetitions_per_exercise', 1)
    
    # Convert exercises_count to integer if provided
    exercises_count = None
    if exercises_count_cfg is not None:
        try:
            exercises_count = int(exercises_count_cfg)
        except Exception:
            exercises_count = None
    
    # Determine how many times to repeat each exercise
    # Priority: repetitions_per_exercise (if > 1) > exercises_count > duration-based calculation
    actual_reps = 1
    max_unique_exercises = len(exercises) if len(exercises) > 0 else 1
    
    if repetitions_per_exercise_cfg > 1:
        # If repetitions_per_exercise is explicitly set, use it
        actual_reps = repetitions_per_exercise_cfg
    elif exercises_count is not None and exercises_count > 0:
        # If exercises_count is set, calculate how many unique exercises to include
        # such that unique_exercises * repetitions = exercises_count
        # For simplicity, use exercises_count as the total count with reps = 1
        actual_reps = 1
        max_unique_exercises = exercises_count
    else:
        # Fall back to duration-based calculation
        max_total_exercises = int(max_duration_seconds / time_per_exercise)
        if max_total_exercises < 1:
            max_total_exercises = 1
        # Calculate how many times to repeat to fill the duration
        if max_unique_exercises > 0:
            actual_reps = max(1, max_total_exercises // max_unique_exercises)
        else:
            actual_reps = 1
    
    # Build final list with exercises repeated according to actual_reps
    final_list = []
    if len(exercises) > 0:
        if args.from_text:
            # When loading from text, use exercises as-is without repetition
            # Respect exercises_count if set
            if exercises_count is not None and exercises_count > 0:
                final_list = exercises[:exercises_count]
            else:
                max_count = int(max_duration_seconds / time_per_exercise)
                final_list = exercises[:max(1, max_count)]
        else:
            # Blockweises Wiederholen: Jede Sequenz wird repetitions_per_exercise-mal wiederholt, dann die nächste
            total_time = 0.0
            for ex in exercises:
                for _ in range(actual_reps):
                    if exercises_count is not None and len(final_list) >= exercises_count:
                        break
                    if total_time + time_per_exercise > max_duration_seconds:
                        break
                    final_list.append(ex)
                    total_time += time_per_exercise
                if exercises_count is not None and len(final_list) >= exercises_count:
                    break
                if total_time + time_per_exercise > max_duration_seconds:
                    break
    
    # Calculate estimated final duration
    estimated_duration = len(final_list) * time_per_exercise
    
    if not args.dry_run:
        print(f'Target duration: {max_duration_seconds}s ({max_duration_seconds//60}m {max_duration_seconds%60}s)')
        print(f'Estimated duration: ~{int(estimated_duration)}s ({int(estimated_duration)//60}m {int(estimated_duration)%60}s)')
        print(f'Generated {len(final_list)} exercises from {len(exercises)} unique exercise(s)')
        print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_name = args.output or fname_template.format(scale=scale_name.replace(' ', '_'), date=timestamp)

    tmpdir = tempfile.mkdtemp(prefix='intonation_')
    parts = []
    # If dry run requested, write only the text log and exit (no audio rendering)
    if args.dry_run:
        text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
        write_text_log(text_path, final_list)
        shutil.rmtree(tmpdir)
        return

    # Prepare sound config early (velocity used for MIDI creation)
    sf_cfg = cfg.get('sound', {})
    method = sf_cfg.get('method', 'soundfont')
    sf2_path = sf_cfg.get('soundfont_path', 'piano/SalamanderGrandPiano.sf2')
    velocity = sf_cfg.get('velocity', 90)

    # Also build a combined MIDI file representing the whole session so the
    # user can open it in a MIDI editor. This MIDI is written regardless
    # of whether FluidSynth is used for audio rendering.
    if final_list:
        try:
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = cfg.get('timing', {}).get('intro_bpm', 120)
            track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            # helper to convert seconds -> ticks (approx using bpm)
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))

            note_dur = cfg.get('timing', {}).get('note_duration', 1.8)
            intra_interval_gap = 0.1  # 100 ms gap between two notes of an interval
            rest_between = cfg.get('timing', {}).get('pause_between_reps', 1.0)

            for ex in final_list:
                if ex[0] == 'interval':
                    a, b = int(ex[1]), int(ex[2])
                    # note on A
                    track.append(Message('note_on', note=a, velocity=velocity, time=0))
                    # note off A after note_dur
                    track.append(Message('note_off', note=a, velocity=0, time=secs_to_ticks(note_dur)))
                    # small gap before second note
                    track.append(Message('note_on', note=b, velocity=velocity, time=secs_to_ticks(intra_interval_gap)))
                    track.append(Message('note_off', note=b, velocity=0, time=secs_to_ticks(note_dur)))
                    # rest between exercises
                    track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
                elif ex[0] == 'triad':
                    notes = [int(n) for n in ex[1]]
                    # Play notes consecutively with no pause between them
                    for i, n in enumerate(notes):
                        track.append(Message('note_on', note=n, velocity=velocity, time=0))
                        track.append(Message('note_off', note=n, velocity=0, time=secs_to_ticks(note_dur)))
                    # rest between exercises
                    track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
                elif ex[0] == 'sequence':
                    # ex[1] may be either a sequence of MIDI ints (old format)
                    # or a sequence of (midi, duration) tuples (new ABC format).
                    seq = ex[1]
                    # Play notes consecutively; respect per-note durations when provided.
                    if seq and isinstance(seq[0], tuple):
                        # New format: list of (midi, duration) tuples
                        for midi_note, dur in seq:
                            midi_note = int(midi_note)
                            ticks = secs_to_ticks(dur)
                            track.append(Message('note_on', note=midi_note, velocity=velocity, time=0))
                            track.append(Message('note_off', note=midi_note, velocity=0, time=ticks))
                    else:
                        # Old format: list of MIDI ints, use default note_dur
                        notes = [int(n) for n in seq]
                        for n in notes:
                            track.append(Message('note_on', note=n, velocity=velocity, time=0))
                            track.append(Message('note_off', note=n, velocity=0, time=secs_to_ticks(note_dur)))
                    # rest between exercises
                    track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
                else:
                    # unknown entry: skip with a small rest
                    track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))

            base = os.path.splitext(out_name)[0]
            session_midi_path = base + '.mid'
            session_mid.save(session_midi_path)
            print(f'Wrote session MIDI to {session_midi_path}')
            # Audio rendering removed: this tool now produces MIDI files only.
            # Skip the rest of the audio rendering pipeline (fluidsynth/ffmpeg/pydub).
            if not args.verbose:
                # If user did not request verbose text log, exit now after writing MIDI
                return
            # If verbose requested, fall through to write the text log and then exit
        except Exception as e:
            print(f'Warning: failed to write session MIDI: {e}')

    try:
        # No audio rendering: write the text log using the actual MIDI ticks per beat
        text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
        ticks_val = session_mid.ticks_per_beat if 'session_mid' in locals() else 480
        write_text_log(text_path, final_list, ticks_per_beat=ticks_val)
        return
    except Exception as e:
        print(f'Warning: failed to write text log: {e}')

    finally:
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()
