#!/usr/bin/env python3
import unittest
import tempfile
import os
from types import SimpleNamespace

import intonation_trainer as trainer


class TestMainHelpers(unittest.TestCase):
    def test_build_final_list_with_sequences(self):
        cfg = {
            'sequences': {
                'notes': ['|C4 D4 E4|']
            }
        }
        args = SimpleNamespace(from_text=None, max_duration=600, output=None)
        final_list, scale_name, out_name, est = trainer.build_final_list(cfg, args)
        self.assertTrue(len(final_list) >= 1)
        self.assertEqual(scale_name, 'session')

    def test_build_final_list_from_text(self):
        # create a temp text log
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        try:
            # write a simple text log using helper
            ex = [('interval', 60, 64), ('triad', (60,64,67))]
            trainer.write_text_log(path, ex, ticks_per_beat=480, scale_name='X')
            args = SimpleNamespace(from_text=path, max_duration=600, output=None)
            final_list, scale_name, out_name, est = trainer.build_final_list({}, args)
            # final_list should contain the two exercises (or a subset depending on duration)
            self.assertTrue(len(final_list) >= 1)
        finally:
            os.remove(path)

    def test_repetitions_and_exercises_count(self):
        # config with explicit exercises_count and repetitions
        cfg = {
            'scale': {'root': 'A3'},
            'exercises_count': 2,
            'repetitions_per_exercise': 3,
        }
        args = SimpleNamespace(from_text=None, max_duration=600, output=None)
        final_list, scale_name, out_name, est = trainer.build_final_list(cfg, args)
        # repetitions_per_exercise should cause more entries per unique exercise
        self.assertTrue(len(final_list) >= 1)


if __name__ == '__main__':
    unittest.main()
