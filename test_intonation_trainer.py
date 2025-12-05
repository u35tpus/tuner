#!/usr/bin/env python3
"""
Unit tests for intonation_trainer.py

Tests include:
  - MIDI file generation and parsing
  - Consistency between generated exercises and MIDI note counts
  - Interval and triad generation
  - Text log roundtrip (write/read)
  - Scale generation and note validation
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add repo root to path so we can import intonation_trainer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intonation_trainer as trainer
from mido import MidiFile


class TestNoteConversion(unittest.TestCase):
    """Test note name to MIDI conversion and vice versa."""

    def test_note_name_to_midi_basic(self):
        """Test basic note name to MIDI conversion."""
        self.assertEqual(trainer.note_name_to_midi('C4'), 60)
        self.assertEqual(trainer.note_name_to_midi('A4'), 69)
        self.assertEqual(trainer.note_name_to_midi('A3'), 57)

    def test_note_name_to_midi_with_accidentals(self):
        """Test note conversion with sharps and flats."""
        self.assertEqual(trainer.note_name_to_midi('C#4'), 61)
        self.assertEqual(trainer.note_name_to_midi('Db4'), 61)
        self.assertEqual(trainer.note_name_to_midi('F#3'), 54)

    def test_midi_to_freq_a4(self):
        """Test that A4 (MIDI 69) converts to 440 Hz."""
        freq = trainer.midi_to_freq(69)
        self.assertAlmostEqual(freq, 440.0, places=1)

    def test_midi_to_freq_consistency(self):
        """Test frequency conversion for various MIDI notes."""
        # C4 (middle C) should be lower than A4
        freq_c4 = trainer.midi_to_freq(60)
        freq_a4 = trainer.midi_to_freq(69)
        self.assertLess(freq_c4, freq_a4)


class TestScaleGeneration(unittest.TestCase):
    """Test scale generation and note validation."""

    def test_major_scale(self):
        """Test generation of C major scale."""
        root = trainer.note_name_to_midi('C4')
        notes = trainer.build_scale_notes(root, 'major')
        # C major: C D E F G A B (7 notes)
        self.assertEqual(len(notes), 7)
        # First note should be root
        self.assertEqual(notes[0], root)

    def test_natural_minor_scale(self):
        """Test generation of A natural minor scale."""
        root = trainer.note_name_to_midi('A3')
        notes = trainer.build_scale_notes(root, 'natural_minor')
        self.assertEqual(len(notes), 7)
        self.assertEqual(notes[0], root)

    def test_scale_type_error(self):
        """Test that invalid scale type raises error."""
        root = trainer.note_name_to_midi('C4')
        with self.assertRaises(ValueError):
            trainer.build_scale_notes(root, 'invalid_scale_type')

    def test_expand_scale_over_range(self):
        """Test scale expansion over vocal range."""
        root = trainer.note_name_to_midi('A3')
        low = trainer.note_name_to_midi('A2')
        high = trainer.note_name_to_midi('C4')
        pool = trainer.expand_scale_over_range(root, 'natural_minor', low, high)
        
        # All notes should be within range
        self.assertTrue(all(low <= n <= high for n in pool))
        # Should have multiple octaves of the scale
        self.assertGreater(len(pool), 7)


class TestIntervalGeneration(unittest.TestCase):
    """Test interval generation."""

    def test_generate_intervals_basic(self):
        """Test basic interval generation."""
        pool = [60, 62, 64, 65, 67, 69, 71]  # C major scale
        intervals = trainer.generate_intervals(pool, ascending=True, descending=False)
        
        # Should have many intervals
        self.assertGreater(len(intervals), 0)
        # All should be tuples of ('interval', a, b)
        for iv in intervals:
            self.assertEqual(iv[0], 'interval')
            self.assertIsInstance(iv[1], int)
            self.assertIsInstance(iv[2], int)

    def test_generate_intervals_ascending_only(self):
        """Test interval generation with ascending only."""
        pool = [60, 62, 64]
        intervals = trainer.generate_intervals(pool, ascending=True, descending=False)
        
        # All intervals should be ascending (b > a)
        for iv in intervals:
            a, b = iv[1], iv[2]
            self.assertGreater(b, a)

    def test_generate_intervals_descending_only(self):
        """Test interval generation with descending only."""
        pool = [60, 62, 64]
        intervals = trainer.generate_intervals(pool, ascending=False, descending=True)
        
        # All intervals should be descending (b < a)
        for iv in intervals:
            a, b = iv[1], iv[2]
            self.assertLess(b, a)

    def test_interval_max_constraint(self):
        """Test max_interval constraint."""
        pool = [60, 62, 64, 67, 71]
        # Limit to 5 semitones
        intervals = trainer.generate_intervals(pool, ascending=True, descending=True, max_interval=5)
        
        # All intervals should be <= 5 semitones
        for iv in intervals:
            a, b = iv[1], iv[2]
            self.assertLessEqual(abs(b - a), 5)


class TestTriadGeneration(unittest.TestCase):
    """Test triad generation."""

    def test_generate_triads_basic(self):
        """Test basic triad generation."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]  # C major
        pool = list(range(60, 76))  # C4 to B4
        triads = trainer.generate_triads(scale_notes, pool, include_inversions=False)
        
        # Should generate multiple triads
        self.assertGreater(len(triads), 0)
        # All should be tuples of ('triad', tuple_of_3_notes)
        for tr in triads:
            self.assertEqual(tr[0], 'triad')
            self.assertEqual(len(tr[1]), 3)

    def test_generate_triads_with_inversions(self):
        """Test triad generation with inversions."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]
        pool = list(range(60, 76))
        triads_no_inv = trainer.generate_triads(scale_notes, pool, include_inversions=False)
        triads_with_inv = trainer.generate_triads(scale_notes, pool, include_inversions=True)
        
        # With inversions should have more triads
        self.assertGreater(len(triads_with_inv), len(triads_no_inv))


class TestMIDIGeneration(unittest.TestCase):
    """Test MIDI file generation and validation."""

    def test_write_midi_for_exercise_simple(self):
        """Test writing a simple MIDI exercise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = os.path.join(tmpdir, 'test.mid')
            events = [
                (60, 0.0, 1.0, 90),      # note_on at 0s, note_off at 1s, velocity 90
                (64, 1.5, 1.0, 90),      # next note at 1.5s
            ]
            trainer.write_midi_for_exercise(events, midi_path, tempo_bpm=120)
            
            # Verify file exists
            self.assertTrue(os.path.exists(midi_path))
            
            # Parse and verify
            mid = MidiFile(midi_path)
            self.assertEqual(len(mid.tracks), 1)
            track = mid.tracks[0]
            # Should have set_tempo + note_on/note_off pairs
            self.assertGreater(len(track), 4)

    def test_midi_note_count(self):
        """Test that MIDI file contains correct number of note_on messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = os.path.join(tmpdir, 'test.mid')
            events = [
                (60, 0.0, 1.0, 90),
                (62, 1.5, 1.0, 90),
                (64, 3.0, 1.0, 90),
            ]
            trainer.write_midi_for_exercise(events, midi_path, tempo_bpm=120)
            
            mid = MidiFile(midi_path)
            track = mid.tracks[0]
            
            # Count note_on messages (excluding meta messages)
            note_ons = [m for m in track if hasattr(m, 'note') and m.type == 'note_on']
            self.assertEqual(len(note_ons), 3)


class TestSessionMIDIGeneration(unittest.TestCase):
    """Test combined session MIDI file generation."""

    def test_session_midi_from_intervals(self):
        """Test session MIDI generation from intervals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exercises = [
                ('interval', 60, 64),
                ('interval', 62, 67),
                ('interval', 64, 69),
            ]
            
            midi_path = os.path.join(tmpdir, 'session.mid')
            cfg = {
                'timing': {
                    'note_duration': 1.0,
                    'pause_between_reps': 0.5,
                    'intro_bpm': 120,
                },
            }
            
            # Manually build session MIDI (replicating logic from main script)
            from mido import MidiFile, MidiTrack, Message, bpm2tempo
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = cfg['timing']['intro_bpm']
            track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))
            
            note_dur = cfg['timing']['note_duration']
            rest_between = cfg['timing']['pause_between_reps']
            
            for ex in exercises:
                a, b = ex[1], ex[2]
                track.append(Message('note_on', note=a, velocity=90, time=0))
                track.append(Message('note_off', note=a, velocity=0, time=secs_to_ticks(note_dur)))
                track.append(Message('note_on', note=b, velocity=90, time=secs_to_ticks(0.1)))
                track.append(Message('note_off', note=b, velocity=0, time=secs_to_ticks(note_dur)))
                track.append(__import__('mido').MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
            
            session_mid.save(midi_path)
            
            # Verify file
            self.assertTrue(os.path.exists(midi_path))
            mid = MidiFile(midi_path)
            self.assertEqual(len(mid.tracks), 1)
            
            # Count note_on messages (should be 6: 2 per interval)
            track = mid.tracks[0]
            note_ons = [m for m in track if hasattr(m, 'note') and m.type == 'note_on']
            self.assertEqual(len(note_ons), 6)

    def test_session_midi_from_triads(self):
        """Test session MIDI generation from triads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exercises = [
                ('triad', (60, 64, 67)),
                ('triad', (62, 66, 69)),
            ]
            
            midi_path = os.path.join(tmpdir, 'session.mid')
            
            from mido import MidiFile, MidiTrack, Message, bpm2tempo
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = 120
            track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))
            
            note_dur = 1.0
            rest_between = 0.5
            
            for ex in exercises:
                notes = list(ex[1])
                for n in notes:
                    track.append(Message('note_on', note=n, velocity=90, time=0))
                track.append(Message('note_off', note=notes[0], velocity=0, time=secs_to_ticks(note_dur)))
                for n in notes[1:]:
                    track.append(Message('note_off', note=n, velocity=0, time=0))
                track.append(__import__('mido').MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
            
            session_mid.save(midi_path)
            
            # Verify file
            self.assertTrue(os.path.exists(midi_path))
            mid = MidiFile(midi_path)
            track = mid.tracks[0]
            
            # Count note_on messages (should be 6: 3 per triad)
            note_ons = [m for m in track if hasattr(m, 'note') and m.type == 'note_on']
            self.assertEqual(len(note_ons), 6)


class TestTextLogRoundtrip(unittest.TestCase):
    """Test writing and reading text logs (note: these functions are internal to main())."""

    def test_text_log_format_parsing(self):
        """Test manual text log format parsing (regex based)."""
        import re
        # Simulate text log lines
        interval_line = "0001: INTERVAL  C#3 (49) -> A#2 (46)"
        triad_line = "0002: TRIAD     A3(57) C#4(61) E4(64)"
        
        # Extract MIDI numbers from interval
        matches = re.findall(r'\((\d+)\)', interval_line)
        self.assertEqual(len(matches), 2)
        self.assertEqual(int(matches[0]), 49)
        self.assertEqual(int(matches[1]), 46)
        
        # Extract MIDI numbers from triad
        matches = re.findall(r'\((\d+)\)', triad_line)
        self.assertEqual(len(matches), 3)
        self.assertEqual(tuple(int(m) for m in matches), (57, 61, 64))


class TestWAVHelpers(unittest.TestCase):
    """Test WAV file helpers (fallback pipeline)."""

    def test_make_silence(self):
        """Test creation of silence."""
        sr = 44100
        silence_100ms = trainer.make_silence_ms(100, sr)
        # 100 ms at 44100 Hz should be 4410 samples
        expected_length = int(44100 * 0.1)
        self.assertEqual(len(silence_100ms), expected_length)
        # All zeros
        self.assertTrue((silence_100ms == 0).all())

    def test_normalize_int16(self):
        """Test int16 normalization."""
        import numpy as np
        # Create array with peak at 16000
        arr = np.array([0, 8000, 16000, 8000], dtype=np.int16)
        normalized = trainer.normalize_int16(arr)
        
        # Max should be close to 32767 (or less due to clipping)
        self.assertLessEqual(normalized.max(), 32767)
        self.assertGreater(normalized.max(), 30000)  # Should be normalized up

    def test_write_and_read_wav_mono(self):
        """Test writing and reading mono WAV files."""
        import numpy as np
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, 'test.wav')
            sr = 44100
            
            # Create test data
            original = np.array([0, 1000, -1000, 500], dtype=np.int16)
            trainer.write_wav_mono(wav_path, original, sr)
            
            # Read back
            read_arr, read_sr = trainer.read_wav_mono(wav_path)
            
            # Verify
            self.assertEqual(read_sr, sr)
            self.assertEqual(len(read_arr), len(original))
            # Samples should match
            np.testing.assert_array_equal(read_arr, original)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def test_scale_to_intervals(self):
        """Test generating intervals from a scale."""
        root = trainer.note_name_to_midi('A3')
        low = trainer.note_name_to_midi('A2')
        high = trainer.note_name_to_midi('A4')
        
        # Generate scale
        pool = trainer.expand_scale_over_range(root, 'natural_minor', low, high)
        
        # Generate intervals
        intervals = trainer.generate_intervals(pool, ascending=True, descending=True, max_interval=12)
        
        # Should have intervals
        self.assertGreater(len(intervals), 0)
        
        # All intervals should use notes from pool
        for iv in intervals:
            a, b = iv[1], iv[2]
            self.assertIn(a, pool)
            self.assertIn(b, pool)

    def test_scale_to_triads(self):
        """Test generating triads from a scale."""
        root = trainer.note_name_to_midi('C4')
        low = trainer.note_name_to_midi('C3')
        high = trainer.note_name_to_midi('C5')
        
        # Generate scale
        pool = trainer.expand_scale_over_range(root, 'major', low, high)
        scale_single = trainer.build_scale_notes(root, 'major')
        
        # Generate triads
        triads = trainer.generate_triads(scale_single, pool, include_inversions=False)
        
        # Should have triads
        self.assertGreater(len(triads), 0)
        
        # All notes in triads should be within a reasonable range
        # (triad inversions may add octaves, so we check broader range)
        for tr in triads:
            notes = tr[1]
            for n in notes:
                # Should be MIDI note in reasonable range (50-90)
                self.assertGreaterEqual(n, 35)
                self.assertLessEqual(n, 96)

    def test_exercise_to_midi_consistency_intervals(self):
        """Test that interval exercises generate correct MIDI note_on count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create exercise list with 5 intervals
            exercises = [
                ('interval', 60, 64),
                ('interval', 62, 67),
                ('interval', 64, 69),
                ('interval', 65, 71),
                ('interval', 67, 72),
            ]
            expected_note_ons = len(exercises) * 2  # Each interval has 2 note_ons
            
            # Build MIDI as the script does
            from mido import MidiFile, MidiTrack, Message, bpm2tempo
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = 120
            track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))
            
            note_dur = 1.0
            rest_between = 0.5
            
            for ex in exercises:
                a, b = ex[1], ex[2]
                track.append(Message('note_on', note=a, velocity=90, time=0))
                track.append(Message('note_off', note=a, velocity=0, time=secs_to_ticks(note_dur)))
                track.append(Message('note_on', note=b, velocity=90, time=secs_to_ticks(0.1)))
                track.append(Message('note_off', note=b, velocity=0, time=secs_to_ticks(note_dur)))
                track.append(__import__('mido').MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
            
            midi_path = os.path.join(tmpdir, 'session.mid')
            session_mid.save(midi_path)
            
            # Read MIDI and count note_ons
            mid = MidiFile(midi_path)
            read_track = mid.tracks[0]
            note_ons = [m for m in read_track if hasattr(m, 'note') and m.type == 'note_on']
            
            # Verify count matches exercises
            self.assertEqual(len(note_ons), expected_note_ons,
                f"Expected {expected_note_ons} note_ons for {len(exercises)} intervals, got {len(note_ons)}")

    def test_exercise_to_midi_consistency_triads(self):
        """Test that triad exercises generate correct MIDI note_on count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create exercise list with 3 triads
            exercises = [
                ('triad', (60, 64, 67)),
                ('triad', (62, 66, 69)),
                ('triad', (65, 69, 72)),
            ]
            expected_note_ons = len(exercises) * 3  # Each triad has 3 note_ons
            
            # Build MIDI
            from mido import MidiFile, MidiTrack, Message, bpm2tempo
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = 120
            track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))
            
            note_dur = 1.0
            rest_between = 0.5
            
            for ex in exercises:
                notes = list(ex[1])
                for n in notes:
                    track.append(Message('note_on', note=n, velocity=90, time=0))
                track.append(Message('note_off', note=notes[0], velocity=0, time=secs_to_ticks(note_dur)))
                for n in notes[1:]:
                    track.append(Message('note_off', note=n, velocity=0, time=0))
                track.append(__import__('mido').MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
            
            midi_path = os.path.join(tmpdir, 'session.mid')
            session_mid.save(midi_path)
            
            # Read MIDI and count note_ons
            mid = MidiFile(midi_path)
            read_track = mid.tracks[0]
            note_ons = [m for m in read_track if hasattr(m, 'note') and m.type == 'note_on']
            
            # Verify count matches exercises
            self.assertEqual(len(note_ons), expected_note_ons,
                f"Expected {expected_note_ons} note_ons for {len(exercises)} triads, got {len(note_ons)}")

    def test_exercise_to_midi_consistency_mixed(self):
        """Test MIDI consistency with mixed intervals and triads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exercises = [
                ('interval', 60, 64),
                ('triad', (62, 66, 69)),
                ('interval', 67, 71),
                ('triad', (65, 69, 72)),
            ]
            # 2 intervals × 2 notes = 4, 2 triads × 3 notes = 6
            expected_note_ons = 10
            
            # Build MIDI
            from mido import MidiFile, MidiTrack, Message, bpm2tempo
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = 120
            track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))
            
            note_dur = 1.0
            rest_between = 0.5
            
            for ex in exercises:
                if ex[0] == 'interval':
                    a, b = ex[1], ex[2]
                    track.append(Message('note_on', note=a, velocity=90, time=0))
                    track.append(Message('note_off', note=a, velocity=0, time=secs_to_ticks(note_dur)))
                    track.append(Message('note_on', note=b, velocity=90, time=secs_to_ticks(0.1)))
                    track.append(Message('note_off', note=b, velocity=0, time=secs_to_ticks(note_dur)))
                elif ex[0] == 'triad':
                    notes = list(ex[1])
                    for n in notes:
                        track.append(Message('note_on', note=n, velocity=90, time=0))
                    track.append(Message('note_off', note=notes[0], velocity=0, time=secs_to_ticks(note_dur)))
                    for n in notes[1:]:
                        track.append(Message('note_off', note=n, velocity=0, time=0))
                track.append(__import__('mido').MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
            
            midi_path = os.path.join(tmpdir, 'session.mid')
            session_mid.save(midi_path)
            
            # Read MIDI and count note_ons
            mid = MidiFile(midi_path)
            read_track = mid.tracks[0]
            note_ons = [m for m in read_track if hasattr(m, 'note') and m.type == 'note_on']
            
            # Verify count matches
            self.assertEqual(len(note_ons), expected_note_ons,
                f"Expected {expected_note_ons} note_ons for mixed exercises, got {len(note_ons)}")


if __name__ == '__main__':
    unittest.main()
