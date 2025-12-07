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
        # Simulate main logic for note chains
        vocal = self.config['vocal_range']
        lowest = trainer.note_name_to_midi(vocal['lowest_note'])
        highest = trainer.note_name_to_midi(vocal['highest_note'])
        pool = list(range(lowest, highest+1))
        max_note_chain_length = self.config['max_note_chain_length']
        max_interval_length = self.config['max_interval_length']
        num_chains = self.config['num_note_chains']
        chains = []
        for _ in range(num_chains):
            chain_len = random.randint(2, max_note_chain_length)
            chain = []
            note = random.choice(pool)
            chain.append(note)
            for _ in range(chain_len-1):
                candidates = [n for n in pool if abs(n-note) <= max_interval_length and n != note]
                if not candidates:
                    break
                note = random.choice(candidates)
                chain.append(note)
            chains.append(chain)
        # Check number of chains
        self.assertEqual(len(chains), num_chains)
        # Check chain lengths
        for chain in chains:
            self.assertTrue(2 <= len(chain) <= max_note_chain_length)
            # Check intervals
            for i in range(1, len(chain)):
                self.assertTrue(abs(chain[i]-chain[i-1]) <= max_interval_length)
                self.assertTrue(lowest <= chain[i] <= highest)

if __name__ == '__main__':
    unittest.main()
