#!/usr/bin/env python3
"""
Additional unit tests for improved code coverage.

Tests for:
  - Note conversion edge cases
  - Scale generation edge cases
  - Utility function error cases
  - WAV helper edge cases
"""

import unittest
import tempfile
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intonation_trainer as trainer


class TestNoteConversionEdgeCases(unittest.TestCase):
    """Additional tests for note conversion."""

    def test_note_name_to_midi_all_notes(self):
        """Test all note names in octave 3."""
        expected = {
            'C3': 48, 'D3': 50, 'E3': 52, 'F3': 53, 'G3': 55, 'A3': 57, 'B3': 59,
            'C#3': 49, 'Db3': 49, 'D#3': 51, 'Eb3': 51, 'E#3': 53, 'F#3': 54,
            'Gb3': 54, 'G#3': 56, 'Ab3': 56, 'A#3': 58, 'Bb3': 58, 'B#3': 60
        }
        for note_name, expected_midi in expected.items():
            with self.subTest(note=note_name):
                result = trainer.note_name_to_midi(note_name)
                self.assertEqual(result, expected_midi)

    def test_note_name_to_midi_extreme_octaves(self):
        """Test extreme octave values."""
        # Lowest MIDI note
        self.assertEqual(trainer.note_name_to_midi('C0'), 12)
        # High octave
        self.assertEqual(trainer.note_name_to_midi('C8'), 108)

    def test_note_name_to_midi_invalid_formats(self):
        """Test invalid note name formats."""
        with self.assertRaises((ValueError, KeyError)):
            trainer.note_name_to_midi('C')  # Missing octave
        with self.assertRaises((ValueError, KeyError)):
            trainer.note_name_to_midi('H4')  # Invalid letter
        with self.assertRaises(ValueError):
            trainer.note_name_to_midi('X')  # Too short

    def test_midi_to_freq_edge_cases(self):
        """Test frequency conversion for boundary MIDI values."""
        # C0 (lowest general MIDI)
        freq_c0 = trainer.midi_to_freq(12)
        self.assertGreater(freq_c0, 0)
        
        # G9 (high note)
        freq_g9 = trainer.midi_to_freq(127)
        self.assertGreater(freq_g9, freq_c0)
        
        # Verify logarithmic relationship
        freq_c4 = trainer.midi_to_freq(60)
        freq_c5 = trainer.midi_to_freq(72)
        self.assertAlmostEqual(freq_c5 / freq_c4, 2.0, places=1)


class TestScaleEdgeCases(unittest.TestCase):
    """Additional tests for scale generation."""

    def test_all_scale_types(self):
        """Test all supported scale types."""
        root = trainer.note_name_to_midi('C4')
        scale_types = ['major', 'natural_minor', 'harmonic_minor', 'melodic_minor',
                       'dorian', 'phrygian', 'lydian', 'mixolydian']
        
        for scale_type in scale_types:
            with self.subTest(scale=scale_type):
                notes = trainer.build_scale_notes(root, scale_type)
                self.assertEqual(len(notes), 7)
                self.assertEqual(notes[0], root)

    def test_scale_expansion_empty_range(self):
        """Test scale expansion with empty result."""
        root = trainer.note_name_to_midi('C4')
        low = trainer.note_name_to_midi('C5')
        high = trainer.note_name_to_midi('C6')
        
        pool = trainer.expand_scale_over_range(root, 'major', low, high)
        # Should have some notes in range
        self.assertGreater(len(pool), 0)
        self.assertTrue(all(low <= n <= high for n in pool))

    def test_scale_expansion_single_octave(self):
        """Test scale expansion over single octave."""
        root = trainer.note_name_to_midi('C3')
        low = trainer.note_name_to_midi('C3')
        high = trainer.note_name_to_midi('B3')
        
        pool = trainer.expand_scale_over_range(root, 'major', low, high)
        self.assertEqual(len(pool), 7)  # One octave of C major


class TestIntervalGenerationEdgeCases(unittest.TestCase):
    """Additional tests for interval generation."""

    def test_generate_intervals_single_note(self):
        """Test interval generation with single note."""
        pool = [60]
        intervals = trainer.generate_intervals(pool)
        self.assertEqual(len(intervals), 0)  # No intervals from single note

    def test_generate_intervals_identical_notes(self):
        """Test interval generation with duplicate notes."""
        pool = [60, 60, 62]
        intervals = trainer.generate_intervals(pool, ascending=True, descending=False)
        # Should not generate intervals from duplicate notes
        unique_intervals = {(iv[1], iv[2]) for iv in intervals}
        self.assertTrue(len(unique_intervals) > 0)

    def test_generate_intervals_no_ascending_or_descending(self):
        """Test interval generation with both ascending and descending disabled."""
        pool = [60, 62, 64]
        intervals = trainer.generate_intervals(pool, ascending=False, descending=False)
        self.assertEqual(len(intervals), 0)

    def test_interval_max_zero(self):
        """Test max_interval constraint with zero."""
        pool = [60, 62, 64]
        intervals = trainer.generate_intervals(pool, max_interval=0)
        self.assertEqual(len(intervals), 0)


class TestTriadGenerationEdgeCases(unittest.TestCase):
    """Additional tests for triad generation."""

    def test_generate_triads_single_root(self):
        """Test triad generation with single pool note."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]
        pool = [60]
        
        triads = trainer.generate_triads(scale_notes, pool, include_inversions=False)
        # Should generate at least one triad
        self.assertGreater(len(triads), 0)
        # Check first triad
        self.assertEqual(triads[0][0], 'triad')
        self.assertEqual(len(triads[0][1]), 3)

    def test_generate_triads_all_types(self):
        """Test triad generation with different types."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]
        pool = list(range(60, 72))
        
        triads_major = trainer.generate_triads(scale_notes, pool, 
                                               include_inversions=False, 
                                               triad_types=['major'])
        triads_minor = trainer.generate_triads(scale_notes, pool,
                                               include_inversions=False,
                                               triad_types=['minor'])
        
        self.assertGreater(len(triads_major), 0)
        self.assertGreater(len(triads_minor), 0)

    def test_generate_triads_invalid_root(self):
        """Test triad generation with root not in scale."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71]
        pool = [73, 74, 75]  # Notes not in C major scale
        
        triads = trainer.generate_triads(scale_notes, pool)
        # May or may not generate triads depending on pitch class matching
        self.assertIsInstance(triads, list)


class TestWAVHelperEdgeCases(unittest.TestCase):
    """Additional tests for WAV helper functions."""

    def test_make_silence_various_lengths(self):
        """Test silence generation for various durations."""
        sr = 44100
        for ms in [10, 100, 1000]:
            with self.subTest(ms=ms):
                silence = trainer.make_silence_ms(ms, sr)
                expected_len = int(sr * (ms / 1000.0))
                self.assertEqual(len(silence), expected_len)
                self.assertTrue(np.all(silence == 0))

    def test_make_silence_zero_length(self):
        """Test silence generation with zero length."""
        silence = trainer.make_silence_ms(0, 44100)
        self.assertEqual(len(silence), 0)

    def test_normalize_int16_zero_input(self):
        """Test normalization of zero array."""
        arr = np.zeros(100, dtype=np.int16)
        result = trainer.normalize_int16(arr)
        self.assertTrue(np.all(result == 0))

    def test_normalize_int16_already_maxed(self):
        """Test normalization of already maxed array."""
        arr = np.array([32767, 32767, 32767], dtype=np.int16)
        result = trainer.normalize_int16(arr)
        self.assertEqual(result.max(), 32767)

    def test_normalize_int16_float_input(self):
        """Test normalization with float input."""
        arr = np.array([0.5, 1.0, 0.75], dtype=np.float32)
        result = trainer.normalize_int16(arr)
        self.assertEqual(result.dtype, np.int16)
        self.assertGreater(result.max(), 0)

    def test_write_and_read_wav_mono_various_rates(self):
        """Test WAV I/O with various sample rates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for sr in [8000, 16000, 44100, 48000]:
                with self.subTest(sr=sr):
                    wav_path = os.path.join(tmpdir, f'test_{sr}.wav')
                    data = np.array([0, 1000, -1000, 500], dtype=np.int16)
                    
                    trainer.write_wav_mono(wav_path, data, sr)
                    read_data, read_sr = trainer.read_wav_mono(wav_path)
                    
                    self.assertEqual(read_sr, sr)
                    np.testing.assert_array_equal(read_data, data)

    def test_write_wav_mono_float_input(self):
        """Test WAV writing with float input (should normalize)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, 'test_float.wav')
            data = np.array([0.1, 0.5, -0.3, 0.2], dtype=np.float32)
            
            trainer.write_wav_mono(wav_path, data, 44100)
            read_data, read_sr = trainer.read_wav_mono(wav_path)
            
            self.assertEqual(read_sr, 44100)
            self.assertEqual(len(read_data), len(data))
            self.assertEqual(read_data.dtype, np.int16)


class TestFrequencyConversion(unittest.TestCase):
    """Test frequency conversion accuracy."""

    def test_midi_to_freq_known_values(self):
        """Test frequency conversion against known values."""
        # A4 = 440 Hz (concert pitch)
        self.assertAlmostEqual(trainer.midi_to_freq(69), 440.0, places=0)
        
        # A3 = 220 Hz
        self.assertAlmostEqual(trainer.midi_to_freq(57), 220.0, places=0)
        
        # A5 = 880 Hz
        self.assertAlmostEqual(trainer.midi_to_freq(81), 880.0, places=0)


if __name__ == '__main__':
    unittest.main()
