#!/usr/bin/env python3
"""
Integration tests for main functionality and helper utilities.

These tests focus on comprehensive coverage of utility functions and 
less common code paths.
"""

import unittest
import tempfile
import os
import sys
import json
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intonation_trainer as trainer


class TestYAMLParsing(unittest.TestCase):
    """Test YAML configuration parsing."""

    def test_parse_yaml_valid(self):
        """Test parsing valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            config_data = {
                'scale': {'name': 'A minor', 'root': 'A3', 'type': 'natural_minor'},
                'vocal_range': {'lowest_note': 'A2', 'highest_note': 'A4'},
                'content': {'intervals': {}, 'triads': {'enabled': True}}
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            result = trainer.parse_yaml(config_path)
            self.assertEqual(result['scale']['name'], 'A minor')
            self.assertEqual(result['vocal_range']['lowest_note'], 'A2')

    def test_parse_yaml_invalid_path(self):
        """Test parsing YAML with invalid path."""
        with self.assertRaises(FileNotFoundError):
            trainer.parse_yaml('/nonexistent/path.yaml')


class TestSynthSimpleWAV(unittest.TestCase):
    """Test simple WAV synthesizer."""

    def test_synth_simple_wav_single_note(self):
        """Test synthesizing a single note."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav = os.path.join(tmpdir, 'test_note.wav')
            trainer.synth_simple_wav([60], 1.0, out_wav)
            
            self.assertTrue(os.path.exists(out_wav))
            # Verify WAV file format
            import wave
            with wave.open(out_wav, 'rb') as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)

    def test_synth_simple_wav_multiple_notes(self):
        """Test synthesizing multiple notes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav = os.path.join(tmpdir, 'test_chord.wav')
            trainer.synth_simple_wav([60, 64, 67], 1.0, out_wav)
            
            self.assertTrue(os.path.exists(out_wav))
            
            import wave
            with wave.open(out_wav, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                # Should have audio data
                self.assertGreater(len(frames), 0)

    def test_synth_simple_wav_custom_sample_rate(self):
        """Test synthesis with custom sample rate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav = os.path.join(tmpdir, 'test_48k.wav')
            trainer.synth_simple_wav([60], 1.0, out_wav, sample_rate=48000)
            
            import wave
            with wave.open(out_wav, 'rb') as wf:
                self.assertEqual(wf.getframerate(), 48000)


class TestWriteMIDIForExercise(unittest.TestCase):
    """Test write_midi_for_exercise function."""

    def test_write_midi_single_note(self):
        """Test writing MIDI with single note."""
        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = os.path.join(tmpdir, 'test_single.mid')
            events = [(60, 0.0, 1.0, 90)]
            
            trainer.write_midi_for_exercise(events, midi_path)
            
            self.assertTrue(os.path.exists(midi_path))
            from mido import MidiFile
            mid = MidiFile(midi_path)
            # Should have one track
            self.assertEqual(len(mid.tracks), 1)

    def test_write_midi_sequence(self):
        """Test writing MIDI with sequential notes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = os.path.join(tmpdir, 'test_seq.mid')
            events = [
                (60, 0.0, 1.0, 90),
                (64, 1.1, 1.0, 90),
                (67, 2.2, 1.0, 90),
            ]
            
            trainer.write_midi_for_exercise(events, midi_path, tempo_bpm=120)
            
            from mido import MidiFile
            mid = MidiFile(midi_path)
            track = mid.tracks[0]
            
            # Count note_on messages
            note_ons = [m for m in track if hasattr(m, 'type') and m.type == 'note_on']
            self.assertEqual(len(note_ons), 3)

    def test_write_midi_custom_tempo(self):
        """Test MIDI writing with custom tempo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = os.path.join(tmpdir, 'test_tempo.mid')
            events = [(60, 0.0, 1.0, 90)]
            
            trainer.write_midi_for_exercise(events, midi_path, tempo_bpm=180)
            
            from mido import MidiFile
            mid = MidiFile(midi_path)
            # Check that tempo was set (it's in a MetaMessage)
            tempo_messages = [m for m in mid.tracks[0] if hasattr(m, 'type') and 'tempo' in str(m)]
            self.assertGreater(len(tempo_messages), 0)


class TestMusicTheory(unittest.TestCase):
    """Test music theory utilities."""

    def test_build_scale_notes_consistency(self):
        """Test that scale notes are consistent."""
        for octave in [1, 2, 3, 4, 5]:
            root = trainer.note_name_to_midi(f'C{octave}')
            notes = trainer.build_scale_notes(root, 'major')
            
            # All notes should be >= root
            self.assertTrue(all(n >= root for n in notes))
            # Scale should be in ascending order
            self.assertEqual(notes, sorted(notes))

    def test_expand_scale_boundary_conditions(self):
        """Test scale expansion at boundaries."""
        root = trainer.note_name_to_midi('C4')
        low = root
        high = root + 12
        
        pool = trainer.expand_scale_over_range(root, 'major', low, high)
        
        # All notes should be in range
        self.assertTrue(all(low <= n <= high for n in pool))
        # Should include the root
        self.assertIn(root, pool)


class TestExerciseGeneration(unittest.TestCase):
    """Test exercise generation logic."""

    def test_generate_intervals_uniqueness(self):
        """Test that generated intervals are unique."""
        pool = list(range(60, 72))
        intervals = trainer.generate_intervals(pool, ascending=True, descending=True, max_interval=12)
        
        # Check uniqueness
        unique_pairs = set((iv[1], iv[2]) for iv in intervals)
        self.assertEqual(len(unique_pairs), len(intervals))

    def test_generate_triads_uniqueness(self):
        """Test that generated triads are unique."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]
        pool = list(range(60, 72))
        
        triads = trainer.generate_triads(scale_notes, pool, include_inversions=True)
        
        # Check uniqueness
        unique_triads = set(tr[1] for tr in triads)
        self.assertEqual(len(unique_triads), len(triads))


if __name__ == '__main__':
    unittest.main()
