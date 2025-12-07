import unittest
import tempfile
import os
import yaml
import intonation_trainer as trainer

class TestRepetitionsPerExercise(unittest.TestCase):
    def setUp(self):
        self.base_config = {
            'output': {'filename': 'test.mid', 'format': 'mid'},
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'notes': [
                    "C4 D4 E4",
                    "F4 G4 A4"
                ]
            },
            'timing': {'note_duration': 1.0, 'pause_between_reps': 1.0},
            'repetitions_per_exercise': 2,
            'max_duration': 20
        }

    def test_blockwise_repetitions(self):
        # Write config to temp file
        with tempfile.NamedTemporaryFile('w+', suffix='.yaml', delete=False) as f:
            yaml.dump(self.base_config, f)
            f.flush()
            config_path = f.name
        try:
            # Patch sys.argv for main()
            import sys
            sys_argv_backup = sys.argv
            sys.argv = ['intonation_trainer.py', config_path, '--dry-run', '--text-file', 'test.txt']
            # Run main()
            trainer.main()
            # Read text log
            with open('test.txt', 'r') as logf:
                lines = [l for l in logf if l.strip().startswith('000')]
            # Es gibt 2 Sequenzen, jede 2x, also 4 Zeilen
            self.assertEqual(len(lines), 4)
            # Die ersten beiden Zeilen müssen denselben Sequenzinhalt haben (erste Sequenz), dann 2x zweite Sequenz
            seq0 = lines[0].split(':',1)[1]
            seq1 = lines[1].split(':',1)[1]
            seq2 = lines[2].split(':',1)[1]
            seq3 = lines[3].split(':',1)[1]
            self.assertEqual(seq0, seq1)
            self.assertEqual(seq2, seq3)
            self.assertNotEqual(seq0, seq2)
        finally:
            os.remove(config_path)
            if os.path.exists('test.txt'):
                os.remove('test.txt')

if __name__ == '__main__':
    unittest.main()
