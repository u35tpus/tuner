import unittest
import intonation_trainer as trainer
import yaml
import os

class TestScalesParsing(unittest.TestCase):
    def setUp(self):
        self.gmajor_cfg = {
            'signature': '4/4',
            'scale': 'Gmajor',
            'unit_length': 1.0,
            'notes': [
                "F4 G4 A4",  # F should be F#
                "F!4 G4"     # F! should be F
            ]
        }
        self.fminor_cfg = {
            'signature': '4/4',
            'scale': 'Fminor',
            'unit_length': 1.0,
            'notes': [
                "A4 B4 D4 E4",  # A, B, D, E should be with b
                "A!4 B!4 D!4 E!4" # override: no b
            ]
        }

    def test_gmajor_default_and_override(self):
        # F4 should be F#4, F!4 should be F4
        seqs = trainer.parse_sequences_from_config(self.gmajor_cfg)
        midi_fsharp = trainer.note_name_to_midi('F#4')
        midi_f = trainer.note_name_to_midi('F4')
        # First sequence: F4 G4 A4 -> F#4 G4 A4
        self.assertEqual(seqs[0][1][0][0], midi_fsharp)
        # Second sequence: F!4 G4 -> F4 G4
        self.assertEqual(seqs[1][1][0][0], midi_f)

    def test_fminor_default_and_override(self):
        # A4, B4, D4, E4 should be Ab4, Bb4, Db4, Eb4
        seqs = trainer.parse_sequences_from_config(self.fminor_cfg)
        midi_ab = trainer.note_name_to_midi('Ab4')
        midi_bb = trainer.note_name_to_midi('Bb4')
        midi_db = trainer.note_name_to_midi('Db4')
        midi_eb = trainer.note_name_to_midi('Eb4')
        # First sequence: A4 B4 D4 E4 -> Ab4 Bb4 Db4 Eb4
        self.assertEqual(seqs[0][1][0][0], midi_ab)
        self.assertEqual(seqs[0][1][1][0], midi_bb)
        self.assertEqual(seqs[0][1][2][0], midi_db)
        self.assertEqual(seqs[0][1][3][0], midi_eb)
        # Second sequence: A!4 B!4 D!4 E!4 -> A4 B4 D4 E4
        midi_a = trainer.note_name_to_midi('A4')
        midi_b = trainer.note_name_to_midi('B4')
        midi_d = trainer.note_name_to_midi('D4')
        midi_e = trainer.note_name_to_midi('E4')
        self.assertEqual(seqs[1][1][0][0], midi_a)
        self.assertEqual(seqs[1][1][1][0], midi_b)
        self.assertEqual(seqs[1][1][2][0], midi_d)
        self.assertEqual(seqs[1][1][3][0], midi_e)

    def test_dminor_alias_default_and_override(self):
        # D minor has Bb in the key signature: B should become Bb unless overridden.
        dminor_cfg = {
            'signature': '4/4',
            'scale': 'Dminor',
            'unit_length': 1.0,
            'notes': [
                "B3",     # should become Bb3
                "B!3"     # override: natural B3
            ]
        }
        seqs = trainer.parse_sequences_from_config(dminor_cfg)
        midi_bb3 = trainer.note_name_to_midi('Bb3')
        midi_b3 = trainer.note_name_to_midi('B3')

        self.assertEqual(seqs[0][1][0][0], midi_bb3)
        self.assertEqual(seqs[1][1][0][0], midi_b3)

if __name__ == "__main__":
    unittest.main()#!/usr/bin/env python3
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
