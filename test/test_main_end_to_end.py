#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest

import yaml


import intonation_trainer as trainer


class ArgvContext:
    def __init__(self, argv):
        self._argv = argv
        self._old = None

    def __enter__(self):
        self._old = sys.argv
        sys.argv = self._argv
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.argv = self._old
        return False


class TestMainEndToEnd(unittest.TestCase):
    def _write_yaml(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False)

    def test_main_sequences_dry_run_writes_text_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_txt = os.path.join(tmpdir, 'out.txt')
            cfg = {
                'output': {'filename': 'Sequences_{date}.mp3'},
                'sequences': {
                    'signature': '4/4',
                    'unit_length': 1.0,
                    'combine_sequences_to_one': False,
                    'validate_time_signature': False,
                    'notes': [
                        # Tie across a barline
                        'C4- | C4',
                    ],
                },
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'repetitions_per_exercise': 1,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(out_txt))

    def test_main_sequences_writes_session_midi_non_verbose(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_mp3 = os.path.join(tmpdir, 'out.mp3')
            cfg = {
                'output': {'filename': 'Sequences_{date}.mp3'},
                'sequences': {
                    'signature': '4/4',
                    'unit_length': 1.0,
                    'combine_sequences_to_one': False,
                    'validate_time_signature': False,
                    'notes': ['C4- C4'],
                },
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0, 'intro_bpm': 120},
                'repetitions_per_exercise': 1,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--output',
                out_mp3,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'out.mid')))

    def test_main_sequences_writes_session_midi_and_text_log_verbose(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_mp3 = os.path.join(tmpdir, 'out.mp3')
            cfg = {
                'output': {'filename': 'Sequences_{date}.mp3'},
                'sequences': {
                    'signature': '4/4',
                    'unit_length': 1.0,
                    'combine_sequences_to_one': False,
                    'validate_time_signature': False,
                    'notes': ['C4 D4'],
                },
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0, 'intro_bpm': 120},
                'repetitions_per_exercise': 1,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--output',
                out_mp3,
                '--verbose',
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'out.mid')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'out.txt')))

    def test_main_scale_intervals_triads_and_rhythm_vocal_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_txt = os.path.join(tmpdir, 'out.txt')
            cfg = {
                'output': {'filename': 'Test_{date}.mp3'},
                'vocal_range': {'lowest_note': 'C4', 'highest_note': 'E4'},
                'scale': {
                    'name': 'TestScale',
                    'notes': ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4'],
                },
                'content': {
                    'intervals': {'ascending': True, 'descending': False},
                    'triads': {'enabled': True, 'include_inversions': False, 'types': ['major']},
                    'rhythm_vocal': {'enabled': True, 'base_note': 'C4', 'num_exercises': 2, 'max_pattern_length': 3},
                },
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'repetitions_per_exercise': 1,
                'random_seed': 123,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(out_txt))

    def test_main_vocal_range_scale_step_triads_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_txt = os.path.join(tmpdir, 'out.txt')
            cfg = {
                'output': {'filename': 'Vocal_{date}.mp3'},
                'vocal_range': {'lowest_note': 'C4', 'highest_note': 'D4', 'mode': 'scale_step_triads'},
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'repetitions_per_exercise': 1,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(out_txt))

    def test_main_vocal_range_ladder_down_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            out_txt = os.path.join(tmpdir, 'out.txt')
            cfg = {
                'output': {'filename': 'Vocal_{date}.mp3'},
                'vocal_range': {'lowest_note': 'A2', 'highest_note': 'B2', 'mode': 'ladder_down'},
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'repetitions_per_exercise': 1,
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(out_txt))

    def test_main_from_text_empty_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            in_txt = os.path.join(tmpdir, 'in.txt')
            out_txt = os.path.join(tmpdir, 'out.txt')

            # Minimal config; generation is bypassed by --from-text.
            cfg = {
                'output': {'filename': 'FromText_{date}.mp3'},
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)
            with open(in_txt, 'w', encoding='utf-8') as f:
                f.write('')

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--from-text',
                in_txt,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            # When no exercises are loaded, main returns early and should not write an output text log.
            self.assertFalse(os.path.exists(out_txt))

    def test_main_from_text_roundtrip_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, 'cfg.yaml')
            in_txt = os.path.join(tmpdir, 'in.txt')
            out_txt = os.path.join(tmpdir, 'out.txt')

            cfg = {
                'output': {'filename': 'FromText_{date}.mp3'},
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'max_duration': 1,
            }
            self._write_yaml(cfg_path, cfg)

            # Create a small valid text log via the module helper.
            exercises = [
                ('interval', trainer.note_name_to_midi('C4'), trainer.note_name_to_midi('E4')),
                ('sequence', [(trainer.note_name_to_midi('C4'), 1.0)]),
            ]
            trainer.write_text_log(in_txt, exercises, scale_name='from_text', time_signature='4/4')

            with ArgvContext([
                'intonation_trainer.py',
                cfg_path,
                '--from-text',
                in_txt,
                '--dry-run',
                '--text-file',
                out_txt,
                '--max-duration',
                '1',
            ]):
                trainer.main()

            self.assertTrue(os.path.exists(out_txt))


if __name__ == '__main__':
    unittest.main()
