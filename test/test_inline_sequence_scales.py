import unittest

import intonation_trainer as trainer


class TestInlineSequenceScales(unittest.TestCase):
    def test_inline_scale_prefix_overrides_global_sequence_scale(self):
        cfg = {
            'signature': '4/4',
            'scale': 'Dminor',
            'unit_length': 1.0,
            'notes': [
                'Fminor| B2 E2 A2 D2 |',
            ],
        }

        seqs = trainer.parse_sequences_from_config(cfg)

        self.assertEqual(seqs[0][1][0][0], trainer.note_name_to_midi('Bb2'))
        self.assertEqual(seqs[0][1][1][0], trainer.note_name_to_midi('Eb2'))
        self.assertEqual(seqs[0][1][2][0], trainer.note_name_to_midi('Ab2'))
        self.assertEqual(seqs[0][1][3][0], trainer.note_name_to_midi('Db2'))

    def test_sequence_without_inline_prefix_keeps_global_scale(self):
        cfg = {
            'signature': '4/4',
            'scale': 'Dminor',
            'unit_length': 1.0,
            'notes': [
                '| B2 E2 |',
            ],
        }

        seqs = trainer.parse_sequences_from_config(cfg)

        self.assertEqual(seqs[0][1][0][0], trainer.note_name_to_midi('Bb2'))
        self.assertEqual(seqs[0][1][1][0], trainer.note_name_to_midi('E2'))


if __name__ == '__main__':
    unittest.main()
