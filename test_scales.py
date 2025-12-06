#!/usr/bin/env python3
import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intonation_trainer as trainer


class TestScaleGeneration(unittest.TestCase):
    """Test scale generation and note validation."""

    def test_major_scale(self):
        root = trainer.note_name_to_midi('C4')
        notes = trainer.build_scale_notes(root, 'major')
        self.assertEqual(len(notes), 7)
        self.assertEqual(notes[0], root)

    def test_natural_minor_scale(self):
        root = trainer.note_name_to_midi('A3')
        notes = trainer.build_scale_notes(root, 'natural_minor')
        self.assertEqual(len(notes), 7)
        self.assertEqual(notes[0], root)

    def test_scale_type_error(self):
        root = trainer.note_name_to_midi('C4')
        with self.assertRaises(ValueError):
            trainer.build_scale_notes(root, 'invalid_scale_type')

    def test_expand_scale_over_range(self):
        root = trainer.note_name_to_midi('A3')
        low = trainer.note_name_to_midi('A2')
        high = trainer.note_name_to_midi('C4')
        pool = trainer.expand_scale_over_range(root, 'natural_minor', low, high)
        self.assertTrue(all(low <= n <= high for n in pool))
        self.assertGreater(len(pool), 7)


if __name__ == '__main__':
    unittest.main()
