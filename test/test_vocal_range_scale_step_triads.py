import unittest

import intonation_trainer as trainer


class TestVocalRangeScaleStepTriads(unittest.TestCase):
    def test_generates_expected_first_step_and_stops_at_range(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('E3')

        exercises = trainer.generate_vocal_range_scale_step_triads(lowest, highest)

        # For A2..E3, only the A2 step fits fully (A2-B2-C#3-...-E3)
        self.assertEqual(len(exercises), 2)
        self.assertEqual(exercises[0][0], 'chord')
        self.assertEqual(exercises[0][1], (lowest, trainer.note_name_to_midi('C#3'), highest))
        self.assertEqual(exercises[1][0], 'sequence')
        self.assertEqual(exercises[1][1], [lowest, trainer.note_name_to_midi('B2'), lowest])

    def test_repetitions_per_step_repeats_chord_and_sequence(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('E3')

        exercises = trainer.generate_vocal_range_scale_step_triads(lowest, highest, repetitions_per_step=3)

        # For A2..E3 only one root fits, repeated 3 times => 3*(CHORD+SEQUENCE) == 6 entries
        self.assertEqual(len(exercises), 6)
        for i in range(0, 6, 2):
            self.assertEqual(exercises[i][0], 'chord')
            self.assertEqual(exercises[i][1], (lowest, trainer.note_name_to_midi('C#3'), highest))
            self.assertEqual(exercises[i + 1][0], 'sequence')
            self.assertEqual(exercises[i + 1][1], [lowest, trainer.note_name_to_midi('B2'), lowest])

    def test_empty_when_range_too_small_for_triad(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('B2')

        exercises = trainer.generate_vocal_range_scale_step_triads(lowest, highest)
        self.assertEqual(exercises, [])

    def test_chord_is_written_concurrently_in_midi_track(self):
        from mido import MidiFile, MidiTrack, bpm2tempo
        import mido

        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        tempo_bpm = 120
        track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
        ticks_per_beat = mid.ticks_per_beat

        def secs_to_ticks(s):
            return int(s * (ticks_per_beat * tempo_bpm / 60.0))

        ex = ('chord', (60, 64, 67))
        trainer.append_exercise_to_session_track(
            track,
            ex,
            velocity=90,
            secs_to_ticks=secs_to_ticks,
            note_dur=1.0,
            intra_interval_gap=0.1,
            rest_between=0.5,
        )

        note_msgs = [m for m in track if getattr(m, 'type', None) in ('note_on', 'note_off')]
        self.assertEqual([m.type for m in note_msgs[:3]], ['note_on', 'note_on', 'note_on'])
        self.assertTrue(all(m.time == 0 for m in note_msgs[:3]))

        # The first note_off carries the duration delta; the others are at time 0.
        self.assertEqual([m.type for m in note_msgs[3:6]], ['note_off', 'note_off', 'note_off'])
        self.assertEqual(note_msgs[3].time, secs_to_ticks(1.0))
        self.assertEqual(note_msgs[4].time, 0)
        self.assertEqual(note_msgs[5].time, 0)


class TestVocalRangeScaleStepTriads13531(unittest.TestCase):
    def test_generates_expected_pattern_and_stops(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('E3')

        exercises = trainer.generate_vocal_range_scale_step_triads_13531(lowest, highest)

        # Only the A2 step fits fully; should produce CHORD + SEQUENCE(1-3-5-3-1)
        self.assertEqual(len(exercises), 2)
        self.assertEqual(exercises[0][0], 'chord')
        self.assertEqual(exercises[0][1], (lowest, trainer.note_name_to_midi('C#3'), highest))
        self.assertEqual(exercises[1][0], 'sequence')
        self.assertEqual(
            exercises[1][1],
            [lowest, trainer.note_name_to_midi('C#3'), highest, trainer.note_name_to_midi('C#3'), lowest],
        )

    def test_repetitions_per_step_repeats_full_step(self):
        lowest = trainer.note_name_to_midi('A2')
        highest = trainer.note_name_to_midi('E3')

        exercises = trainer.generate_vocal_range_scale_step_triads_13531(lowest, highest, repetitions_per_step=5)

        # One step, repeated 5 times => 10 entries
        self.assertEqual(len(exercises), 10)
        for i in range(0, 10, 2):
            self.assertEqual(exercises[i][0], 'chord')
            self.assertEqual(exercises[i + 1][0], 'sequence')


if __name__ == '__main__':
    unittest.main()
