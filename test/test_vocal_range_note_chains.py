import unittest
import intonation_trainer as trainer
import random

class TestVocalRangeNoteChains(unittest.TestCase):
    def setUp(self):
        self.config = {
            'vocal_range': {
                'lowest_note': 'A2',
                'highest_note': 'C4'
            },
            'max_note_chain_length': 4,
            'max_interval_length': 5,
            'num_note_chains': 10
        }

    def test_note_chains_generation(self):
        # Patch random seed for reproducibility
        random.seed(42)
        vocal = self.config['vocal_range']
        lowest = trainer.note_name_to_midi(vocal['lowest_note'])
        highest = trainer.note_name_to_midi(vocal['highest_note'])
        max_note_chain_length = self.config['max_note_chain_length']
        max_interval_length = self.config['max_interval_length']
        num_chains = self.config['num_note_chains']

        exercises = trainer.generate_vocal_range_note_chains(
            lowest,
            highest,
            max_note_chain_length=max_note_chain_length,
            max_interval_length=max_interval_length,
            num_chains=num_chains,
            rng=random,
        )

        # Check number of chains
        self.assertEqual(len(exercises), num_chains)
        for ex in exercises:
            self.assertEqual(ex[0], 'sequence')
            chain = [n for (n, _dur) in ex[1]]
            self.assertTrue(2 <= len(chain) <= max_note_chain_length)
            for i in range(1, len(chain)):
                self.assertTrue(abs(chain[i] - chain[i-1]) <= max_interval_length)
                self.assertTrue(lowest <= chain[i] <= highest)

if __name__ == '__main__':
    unittest.main()
