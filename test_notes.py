#!/usr/bin/env python3
import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intonation_trainer as trainer


class TestNoteConversion(unittest.TestCase):
    """Test note name to MIDI conversion and vice versa."""

    def test_note_name_to_midi_basic(self):
        self.assertEqual(trainer.note_name_to_midi('C4'), 60)
        self.assertEqual(trainer.note_name_to_midi('A4'), 69)
        self.assertEqual(trainer.note_name_to_midi('A3'), 57)

    def test_note_name_to_midi_with_accidentals(self):
        self.assertEqual(trainer.note_name_to_midi('C#4'), 61)
        self.assertEqual(trainer.note_name_to_midi('Db4'), 61)
        self.assertEqual(trainer.note_name_to_midi('F#3'), 54)

    def test_midi_to_freq_a4(self):
        freq = trainer.midi_to_freq(69)
        self.assertAlmostEqual(freq, 440.0, places=1)

    def test_midi_to_freq_consistency(self):
        freq_c4 = trainer.midi_to_freq(60)
        freq_a4 = trainer.midi_to_freq(69)
        self.assertLess(freq_c4, freq_a4)


if __name__ == '__main__':
    unittest.main()
