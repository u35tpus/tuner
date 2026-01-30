#!/usr/bin/env python3

import unittest

import intonation_trainer as trainer


class TestVocalRangeLadderDown(unittest.TestCase):
    def test_generate_ladder_down_structure_and_steps(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('B2')

        exercises = trainer.generate_vocal_range_ladder_down(lowest, highest, repetitions_per_step=1)
        self.assertGreaterEqual(len(exercises), 3)

        # A2 ladder: A2, G2, F2, Eb2, Db2, B1
        self.assertEqual(exercises[0][0], 'sequence')
        expected_a2 = [
            trainer.note_name_to_midi('A2'),
            trainer.note_name_to_midi('G2'),
            trainer.note_name_to_midi('F2'),
            trainer.note_name_to_midi('Eb2'),
            trainer.note_name_to_midi('Db2'),
            trainer.note_name_to_midi('B1'),
        ]
        self.assertEqual(exercises[0][1], expected_a2)

        # A#2 ladder: Bb2, Ab2, Gb2, E2, D2, B1
        expected_bb2 = [
            trainer.note_name_to_midi('Bb2'),
            trainer.note_name_to_midi('Ab2'),
            trainer.note_name_to_midi('Gb2'),
            trainer.note_name_to_midi('E2'),
            trainer.note_name_to_midi('D2'),
            trainer.note_name_to_midi('C2'),
        ]
        self.assertEqual(exercises[1][1], expected_bb2)

        # B2 ladder: B2, A2, G2, F2, Eb2, Db2
        expected_b2 = [
            trainer.note_name_to_midi('B2'),
            trainer.note_name_to_midi('A2'),
            trainer.note_name_to_midi('G2'),
            trainer.note_name_to_midi('F2'),
            trainer.note_name_to_midi('Eb2'),
            trainer.note_name_to_midi('Db2'),
        ]
        self.assertEqual(exercises[2][1], expected_b2)

    def test_generate_ladder_down_repetitions(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('A2')

        exercises = trainer.generate_vocal_range_ladder_down(lowest, highest, repetitions_per_step=3)
        self.assertEqual(len(exercises), 3)
        self.assertTrue(all(ex[0] == 'sequence' for ex in exercises))
        self.assertEqual(exercises[0][1], exercises[1][1])
        self.assertEqual(exercises[1][1], exercises[2][1])

    def test_generate_ladder_down_zero_step_sizes_are_handled(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('B2')

        # step_semitones=0 and start_step_semitones=0 should degrade gracefully to 1.
        exercises = trainer.generate_vocal_range_ladder_down(
            lowest,
            highest,
            repetitions_per_step=1,
            steps_down=1,
            step_semitones=0,
            start_step_semitones=0,
        )
        # With start_step=1 we should get A2, A#2, B2 start notes.
        self.assertEqual(len(exercises), 3)
        self.assertEqual(exercises[0][1][0], trainer.note_name_to_midi('A2'))
        self.assertEqual(exercises[1][1][0], trainer.note_name_to_midi('Bb2'))
        self.assertEqual(exercises[2][1][0], trainer.note_name_to_midi('B2'))

    def test_generate_ladder_down_clamps_to_midi_range(self):
        lowest = trainer.note_name_to_midi('C0')  # 12
        highest = trainer.note_name_to_midi('C0')

        exercises = trainer.generate_vocal_range_ladder_down(
            lowest,
            highest,
            repetitions_per_step=1,
            steps_down=20,
            step_semitones=2,
            start_step_semitones=2,
        )
        self.assertEqual(len(exercises), 1)
        seq = exercises[0][1]
        self.assertTrue(all(0 <= n <= 127 for n in seq))
        self.assertIn(lowest, seq)

    def test_build_final_list_ladder_down_does_not_double_repeat(self):
        cfg = {
            'output': {'filename': 'Vocal_{date}.mp3'},
            'vocal_range': {'lowest_note': 'A2', 'highest_note': 'A2', 'mode': 'ladder_down'},
            'timing': {'note_duration': 0.1, 'pause_between_reps': 0.0},
            'repetitions_per_exercise': 3,
            'max_duration': 10,
        }

        class Args:
            max_duration = 10
            from_text = None
            output = None

        final_list, scale_name, out_name, estimated_duration = trainer.build_final_list(cfg, Args())
        self.assertEqual(scale_name, 'vocal_range')
        self.assertTrue(out_name.endswith('.mp3'))
        # One start note (A2) repeated 3 times by the generator.
        self.assertEqual(len(final_list), 3)
        self.assertGreaterEqual(estimated_duration, 0.0)


if __name__ == '__main__':
    unittest.main()
