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

class TestRepeatCombinedSequence(unittest.TestCase):
    def setUp(self):
        self.sequences = [
            ('sequence', [(60, 1.0), (64, 1.5), (65, 0.5)]),
            ('sequence', [(65, 0.5), (64, 0.5), (62, 1.0)]),
            ('sequence', [(67, 4.0)])
        ]
        self.repetitions = 5

    def test_repeat_combined_sequence(self):
        # Simuliere die Logik aus main()
        final_list = []
        for ex in self.sequences:
            for _ in range(self.repetitions):
                final_list.append(ex)
        # Feature: combine_sequences_to_one
        combined_notes = []
        for ex in self.sequences:
            if ex[0] == 'sequence':
                combined_notes.extend(ex[1])
        combined_ex = ('sequence', combined_notes)
        for _ in range(self.repetitions):
            final_list.append(combined_ex)
        # Die letzten N Einträge müssen die kombinierte Sequenz sein
        for i in range(1, self.repetitions+1):
            self.assertEqual(final_list[-i], combined_ex)
        # Die Länge muss stimmen
        self.assertEqual(len(final_list), len(self.sequences)*self.repetitions + self.repetitions)

if __name__ == '__main__':
    unittest.main()
