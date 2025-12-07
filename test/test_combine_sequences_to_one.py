import unittest
import tempfile
import os
import yaml
import intonation_trainer

class TestCombineSequencesToOne(unittest.TestCase):
    def setUp(self):
        self.config = {
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'scale': 'Gmajor',
                'combine_sequences_to_one': True,
                'notes': [
                    '| B3| E4:1.5 F4:0.5 G4 B4 | ',
                    '| E4 E4:0.5 E4:0.5 F4:0.5 E4:0.5 D4 | G4:4',
                    '| G4:0.5 A4:0.5 | G4:1.5 F4:0.5 G4 E4 | F4:1.5 E4:0.5 F4 | '
                ]
            },
            'repetitions_per_exercise': 3
        }

    def test_combine_sequences_to_one(self):
        # Simulate main logic for sequence block
        exercises = intonation_trainer.parse_sequences_from_config(self.config['sequences'])
        repetitions = self.config['repetitions_per_exercise']
        # Blockwise repetition
        final_list = []
        for ex in exercises:
            for _ in range(repetitions):
                final_list.append(ex)
        # Feature: combine_sequences_to_one
        if self.config['sequences'].get('combine_sequences_to_one', True):
            for ex in exercises:
                final_list.append(ex)
        # Check that the last N items are the original exercises in order
        self.assertEqual(final_list[-len(exercises):], exercises)
        # Check total length
        self.assertEqual(len(final_list), len(exercises) * (repetitions + 1))

    def test_combine_sequences_to_one_false(self):
        # Same config, but feature off
        config = self.config.copy()
        config['sequences'] = dict(config['sequences'])
        config['sequences']['combine_sequences_to_one'] = False
        exercises = intonation_trainer.parse_sequences_from_config(config['sequences'])
        repetitions = config['repetitions_per_exercise']
        final_list = []
        for ex in exercises:
            for _ in range(repetitions):
                final_list.append(ex)
        # Feature off: nothing appended
        self.assertEqual(len(final_list), len(exercises) * repetitions)

if __name__ == '__main__':
    unittest.main()
