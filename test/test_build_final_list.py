#!/usr/bin/env python3

import os
import tempfile
import unittest
from types import SimpleNamespace

import intonation_trainer as trainer


class TestBuildFinalList(unittest.TestCase):
    def test_build_final_list_sequences_repetition(self):
        cfg = {
            'output': {'filename': 'Seq_{date}.mp3'},
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'combine_sequences_to_one': False,
                'validate_time_signature': False,
                'notes': ['C4 D4'],
            },
            'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
            'repetitions_per_exercise': 3,
            'max_duration': 1,
        }
        args = SimpleNamespace(max_duration=1, from_text=None, output=None)
        final_list, scale_name, out_name, estimated_duration = trainer.build_final_list(cfg, args)
        self.assertEqual(scale_name, 'session')
        self.assertTrue(out_name.endswith('.mp3'))
        self.assertEqual(len(final_list), 3)
        self.assertGreaterEqual(estimated_duration, 0.0)

    def test_build_final_list_from_text_respects_exercises_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_txt = os.path.join(tmpdir, 'in.txt')
            # Build a text log containing more exercises than we will later request.
            exercises = [
                ('interval', trainer.note_name_to_midi('C4'), trainer.note_name_to_midi('E4')),
                ('interval', trainer.note_name_to_midi('D4'), trainer.note_name_to_midi('F4')),
                ('sequence', [(trainer.note_name_to_midi('C4'), 1.0)]),
            ]
            trainer.write_text_log(in_txt, exercises, scale_name='from_text', time_signature='4/4')

            cfg = {
                'output': {'filename': 'FromText_{date}.mp3'},
                'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
                'max_duration': 1,
                'exercises_count': 2,
            }
            args = SimpleNamespace(max_duration=1, from_text=in_txt, output=None)
            final_list, scale_name, out_name, estimated_duration = trainer.build_final_list(cfg, args)
            self.assertEqual(len(final_list), 2)
            self.assertEqual(scale_name, 'session')
            self.assertTrue(out_name.endswith('.mp3'))
            self.assertGreaterEqual(estimated_duration, 0.0)

    def test_build_final_list_vocal_range_note_chains(self):
        cfg = {
            'output': {'filename': 'Vocal_{date}.mp3'},
            'vocal_range': {'lowest_note': 'C4', 'highest_note': 'D4', 'mode': 'note_chains'},
            'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
            'random_seed': 123,
            'max_duration': 1,
            'num_note_chains': 3,
            'max_note_chain_length': 3,
            'max_interval_length': 3,
        }
        args = SimpleNamespace(max_duration=1, from_text=None, output=None)
        final_list, scale_name, out_name, estimated_duration = trainer.build_final_list(cfg, args)
        self.assertEqual(scale_name, 'vocal_range')
        self.assertTrue(len(final_list) >= 1)
        self.assertTrue(out_name.endswith('.mp3'))
        self.assertGreaterEqual(estimated_duration, 0.0)

    def test_build_final_list_scale_root_type_with_bad_exercises_count(self):
        # exercises_count as a non-int should be handled gracefully.
        cfg = {
            'output': {'filename': 'Scale_{date}.mp3'},
            'vocal_range': {'lowest_note': 'C4', 'highest_note': 'E4'},
            'scale': {'name': 'C major', 'root': 'C4', 'type': 'major'},
            'content': {
                'intervals': {'ascending': True, 'descending': False},
                'triads': {'enabled': True, 'include_inversions': False, 'types': ['major']},
            },
            'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
            'repetitions_per_exercise': 1,
            'exercises_count': 'not-an-int',
            'random_seed': 123,
            'max_duration': 1,
        }
        args = SimpleNamespace(max_duration=1, from_text=None, output=None)
        final_list, scale_name, out_name, estimated_duration = trainer.build_final_list(cfg, args)
        self.assertEqual(scale_name, 'C major')
        self.assertTrue(len(final_list) >= 1)
        self.assertTrue(out_name.endswith('.mp3'))
        self.assertGreaterEqual(estimated_duration, 0.0)

    def test_append_exercise_to_session_track_graceful_tie_degrade(self):
        # Cover the defensive branch in append_exercise_to_session_track where a tie continuation
        # appears without a matching active note.
        from mido import MidiFile, MidiTrack

        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        ticks_per_beat = mid.ticks_per_beat

        def secs_to_ticks(s):
            return int(s * ticks_per_beat)

        seq = [
            (trainer.note_name_to_midi('C4'), 0.1, 'tie'),
            (trainer.note_name_to_midi('C4'), 0.1),
        ]
        ex = ('sequence', seq)

        trainer.append_exercise_to_session_track(
            track,
            ex,
            velocity=90,
            secs_to_ticks=secs_to_ticks,
            note_dur=0.1,
            intra_interval_gap=0.0,
            rest_between=0.0,
        )

        note_on = [m for m in track if getattr(m, 'type', None) == 'note_on']
        note_off = [m for m in track if getattr(m, 'type', None) == 'note_off']
        self.assertGreaterEqual(len(note_on), 1)
        self.assertGreaterEqual(len(note_off), 1)


if __name__ == '__main__':
    unittest.main()
