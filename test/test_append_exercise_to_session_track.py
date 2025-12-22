#!/usr/bin/env python3

import unittest

from mido import MidiFile, MidiTrack

import intonation_trainer as trainer


class TestAppendExerciseToSessionTrack(unittest.TestCase):
    def _mk_track(self):
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        ticks_per_beat = mid.ticks_per_beat

        def secs_to_ticks(s):
            return int(s * ticks_per_beat)

        return track, secs_to_ticks

    def test_interval_appends_note_events(self):
        track, secs_to_ticks = self._mk_track()
        ex = ('interval', trainer.note_name_to_midi('C4'), trainer.note_name_to_midi('E4'))
        trainer.append_exercise_to_session_track(
            track,
            ex,
            velocity=90,
            secs_to_ticks=secs_to_ticks,
            note_dur=0.1,
            intra_interval_gap=0.01,
            rest_between=0.0,
        )
        note_on = [m for m in track if getattr(m, 'type', None) == 'note_on']
        note_off = [m for m in track if getattr(m, 'type', None) == 'note_off']
        self.assertEqual(len(note_on), 2)
        self.assertEqual(len(note_off), 2)

    def test_triad_sequential(self):
        track, secs_to_ticks = self._mk_track()
        ex = ('triad', (60, 64, 67))
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
        self.assertEqual(len(note_on), 3)

    def test_chord_simultaneous(self):
        track, secs_to_ticks = self._mk_track()
        ex = ('chord', (60, 64, 67))
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
        self.assertEqual(len(note_on), 3)
        self.assertEqual(len(note_off), 3)

    def test_rhythm_vocal(self):
        track, secs_to_ticks = self._mk_track()
        ex = ('rhythm_vocal', [(60, 0.1), (60, 0.2)])
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
        self.assertEqual(len(note_on), 2)
        self.assertEqual(len(note_off), 2)

    def test_sequence_plain_ints(self):
        track, secs_to_ticks = self._mk_track()
        ex = ('sequence', [60, 62, 64])
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
        self.assertEqual(len(note_on), 3)

    def test_sequence_ties_and_rests_tuple_mode(self):
        track, secs_to_ticks = self._mk_track()
        c4 = trainer.note_name_to_midi('C4')
        d4 = trainer.note_name_to_midi('D4')
        # Exercise tuple-mode paths: rest flush, tie continuation extends, new note flush.
        seq = [
            (c4, 0.1),
            (c4, 0.2, 'tie'),
            ('rest', 0.1),
            (d4, 0.1),
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
        self.assertGreaterEqual(len(note_on), 2)
        self.assertGreaterEqual(len(note_off), 2)


if __name__ == '__main__':
    unittest.main()
