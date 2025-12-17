#!/usr/bin/env python3
"""Tests for melody transposition functionality."""

import unittest
import sys
import os

# Add parent directory to path to import intonation_trainer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import intonation_trainer as trainer


class TestTranspose(unittest.TestCase):
    """Test cases for transpose_notes function."""

    def test_transpose_up_by_one_semitone(self):
        """Test transposing notes up by 1 semitone."""
        notes = [(60, 1.0), (62, 1.0), (64, 1.0)]  # C4, D4, E4
        result = trainer.transpose_notes(notes, 1)
        expected = [(61, 1.0), (63, 1.0), (65, 1.0)]  # C#4, D#4, F4
        self.assertEqual(result, expected)

    def test_transpose_down_by_one_semitone(self):
        """Test transposing notes down by 1 semitone."""
        notes = [(60, 1.0), (62, 1.0), (64, 1.0)]  # C4, D4, E4
        result = trainer.transpose_notes(notes, -1)
        expected = [(59, 1.0), (61, 1.0), (63, 1.0)]  # B3, C#4, D#4
        self.assertEqual(result, expected)

    def test_transpose_up_octave(self):
        """Test transposing notes up by one octave (12 semitones)."""
        notes = [(60, 1.0), (64, 1.0), (67, 1.0)]  # C4, E4, G4
        result = trainer.transpose_notes(notes, 12)
        expected = [(72, 1.0), (76, 1.0), (79, 1.0)]  # C5, E5, G5
        self.assertEqual(result, expected)

    def test_transpose_down_octave(self):
        """Test transposing notes down by one octave (12 semitones)."""
        notes = [(72, 1.0), (76, 1.0), (79, 1.0)]  # C5, E5, G5
        result = trainer.transpose_notes(notes, -12)
        expected = [(60, 1.0), (64, 1.0), (67, 1.0)]  # C4, E4, G4
        self.assertEqual(result, expected)

    def test_transpose_zero_semitones(self):
        """Test that transposing by 0 semitones returns unchanged notes."""
        notes = [(60, 1.0), (62, 1.0), (64, 1.0)]
        result = trainer.transpose_notes(notes, 0)
        self.assertEqual(result, notes)

    def test_transpose_with_rests(self):
        """Test that rests are preserved during transposition."""
        notes = [(60, 1.0), ('rest', 1.0), (64, 1.0)]  # C4, rest, E4
        result = trainer.transpose_notes(notes, 2)
        expected = [(62, 1.0), ('rest', 1.0), (66, 1.0)]  # D4, rest, F#4
        self.assertEqual(result, expected)

    def test_transpose_clamp_to_midi_range_high(self):
        """Test that transposition clamps to valid MIDI range (0-127) when going too high."""
        notes = [(125, 1.0)]  # Very high note
        result = trainer.transpose_notes(notes, 5)
        # Should clamp to 127 (max MIDI)
        self.assertEqual(result[0][0], 127)

    def test_transpose_clamp_to_midi_range_low(self):
        """Test that transposition clamps to valid MIDI range (0-127) when going too low."""
        notes = [(2, 1.0)]  # Very low note
        result = trainer.transpose_notes(notes, -5)
        # Should clamp to 0 (min MIDI)
        self.assertEqual(result[0][0], 0)

    def test_transpose_with_different_durations(self):
        """Test that transposition preserves different note durations."""
        notes = [(60, 0.5), (62, 1.0), (64, 2.0), (67, 1.5)]
        result = trainer.transpose_notes(notes, 3)
        expected = [(63, 0.5), (65, 1.0), (67, 2.0), (70, 1.5)]
        self.assertEqual(result, expected)

    def test_transpose_up_by_5_semitones(self):
        """Test transposing up by 5 semitones (perfect fourth)."""
        notes = [(60, 1.0), (64, 1.0), (67, 1.0)]  # C4, E4, G4 (C major triad)
        result = trainer.transpose_notes(notes, 5)
        expected = [(65, 1.0), (69, 1.0), (72, 1.0)]  # F4, A4, C5 (F major triad)
        self.assertEqual(result, expected)

    def test_transpose_down_by_7_semitones(self):
        """Test transposing down by 7 semitones (perfect fifth)."""
        notes = [(67, 1.0), (71, 1.0), (74, 1.0)]  # G4, B4, D5
        result = trainer.transpose_notes(notes, -7)
        expected = [(60, 1.0), (64, 1.0), (67, 1.0)]  # C4, E4, G4
        self.assertEqual(result, expected)


class TestTransposeIntegration(unittest.TestCase):
    """Integration tests for transposition with parse_sequences_from_config."""

    def test_transpose_in_config(self):
        """Test transposition applied via config."""
        config = {
            'signature': '4/4',
            'unit_length': 1.0,
            'transpose': 2,  # Transpose up by 2 semitones
            'notes': ['C4 D4 E4']
        }
        exercises = trainer.parse_sequences_from_config(config)
        self.assertEqual(len(exercises), 1)
        self.assertEqual(exercises[0][0], 'sequence')
        # C4=60, D4=62, E4=64 transposed up 2 -> D4=62, E4=64, F#4=66
        notes = exercises[0][1]
        self.assertEqual(notes[0][0], 62)  # D4
        self.assertEqual(notes[1][0], 64)  # E4
        self.assertEqual(notes[2][0], 66)  # F#4

    def test_transpose_negative_in_config(self):
        """Test transposition down via config."""
        config = {
            'signature': '4/4',
            'unit_length': 1.0,
            'transpose': -3,  # Transpose down by 3 semitones
            'notes': ['C4 D4 E4']
        }
        exercises = trainer.parse_sequences_from_config(config)
        notes = exercises[0][1]
        # C4=60, D4=62, E4=64 transposed down 3 -> A3=57, B3=59, C#4=61
        self.assertEqual(notes[0][0], 57)  # A3
        self.assertEqual(notes[1][0], 59)  # B3
        self.assertEqual(notes[2][0], 61)  # C#4

    def test_no_transpose_when_zero(self):
        """Test that transpose=0 or missing transpose doesn't change notes."""
        config = {
            'signature': '4/4',
            'unit_length': 1.0,
            'transpose': 0,
            'notes': ['C4 D4 E4']
        }
        exercises = trainer.parse_sequences_from_config(config)
        notes = exercises[0][1]
        self.assertEqual(notes[0][0], 60)  # C4
        self.assertEqual(notes[1][0], 62)  # D4
        self.assertEqual(notes[2][0], 64)  # E4

    def test_transpose_with_rests_in_config(self):
        """Test transposition preserves rests in config."""
        config = {
            'signature': '4/4',
            'unit_length': 1.0,
            'transpose': 5,
            'notes': ['C4 z D4 z E4']
        }
        exercises = trainer.parse_sequences_from_config(config)
        notes = exercises[0][1]
        # Should have 5 items: note, rest, note, rest, note
        self.assertEqual(len(notes), 5)
        self.assertEqual(notes[0][0], 65)  # F4 (C4+5)
        self.assertEqual(notes[1][0], 'rest')  # rest
        self.assertEqual(notes[2][0], 67)  # G4 (D4+5)
        self.assertEqual(notes[3][0], 'rest')  # rest
        self.assertEqual(notes[4][0], 69)  # A4 (E4+5)


if __name__ == '__main__':
    unittest.main()
