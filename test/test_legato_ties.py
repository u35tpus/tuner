import unittest

import intonation_trainer as trainer


class TestLegatoTiesParsing(unittest.TestCase):
    def test_parse_abc_sequence_tie_marks_continuation(self):
        # C4- ties into the next C4 (same pitch). The continuation note is marked.
        result = trainer.parse_abc_sequence("| C4- C4 D4 |", 1.0)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], (60, 1.0))
        self.assertEqual(result[1][0], 60)
        self.assertEqual(result[1][1], 1.0)
        self.assertEqual(result[1][2], 'tie')
        self.assertEqual(result[2], (62, 1.0))

    def test_parse_abc_sequence_tie_can_cross_bar_lines(self):
        # Tie may cross measure markers. Bar lines are ignored for the returned note list.
        result = trainer.parse_abc_sequence("| C4- | C4 | D4 |", 1.0)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], (60, 1.0))
        self.assertEqual(result[1][2], 'tie')
        self.assertEqual(result[2], (62, 1.0))

    def test_parse_abc_sequence_tie_must_repeat_same_pitch(self):
        result = trainer.parse_abc_sequence("| C4- D4 |", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Tie continuation must repeat the same pitch", result[1])

    def test_parse_abc_sequence_tie_cannot_tie_a_rest(self):
        result = trainer.parse_abc_sequence("| z- z |", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Cannot tie a rest", result[1])

    def test_parse_abc_sequence_tie_cannot_end_sequence(self):
        result = trainer.parse_abc_sequence("| C4- |", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Tie marker '-' at end", result[1])


class TestLegatoTiesMidi(unittest.TestCase):
    def test_tied_notes_are_not_rearticulated(self):
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

        ex = ('sequence', [(60, 1.0), (60, 0.5, 'tie'), (62, 1.0)])
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

        # Only one note_on for the tied pitch.
        note_on_60 = [m for m in note_msgs if m.type == 'note_on' and m.note == 60]
        self.assertEqual(len(note_on_60), 1)

        # The note_off for 60 should carry the combined duration.
        note_off_60 = [m for m in note_msgs if m.type == 'note_off' and m.note == 60]
        self.assertEqual(len(note_off_60), 1)
        self.assertEqual(note_off_60[0].time, secs_to_ticks(1.5))

        # Then D4 (62) plays normally.
        note_on_62 = [m for m in note_msgs if m.type == 'note_on' and m.note == 62]
        note_off_62 = [m for m in note_msgs if m.type == 'note_off' and m.note == 62]
        self.assertEqual(len(note_on_62), 1)
        self.assertEqual(len(note_off_62), 1)
        self.assertEqual(note_off_62[0].time, secs_to_ticks(1.0))


if __name__ == '__main__':
    unittest.main()
