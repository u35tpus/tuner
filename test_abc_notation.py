#!/usr/bin/env python3
"""
Unit tests for ABC notation parsing and sequence generation.

This module tests:
  - ABC note parsing with duration modifiers
  - ABC sequence parsing with bar lines
  - Structured sequence config with unit_length
  - Per-note duration handling in MIDI generation
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add repo root to path so we can import intonation_trainer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intonation_trainer as trainer
from mido import MidiFile


class TestABCNoteWithDuration(unittest.TestCase):
    """Test ABC note parsing with duration modifiers."""

    def test_parse_abc_note_with_duration_basic(self):
        """Test parsing ABC notes with duration modifiers."""
        # C4 with default length 1.0 should be (60, 1.0)
        result = trainer.parse_abc_note_with_duration("C4", 1.0)
        self.assertEqual(result, (60, 1.0))
        
        # C42 should be double the length (2.0)
        result = trainer.parse_abc_note_with_duration("C42", 1.0)
        self.assertEqual(result, (60, 2.0))
        
        # C4/2 should be half the length (0.5)
        result = trainer.parse_abc_note_with_duration("C4/2", 1.0)
        self.assertEqual(result, (60, 0.5))
        
        # C4*2 should be double the length (2.0)
        result = trainer.parse_abc_note_with_duration("C4*2", 1.0)
        self.assertEqual(result, (60, 2.0))

    def test_parse_abc_note_with_duration_accidentals(self):
        """Test parsing ABC notes with accidentals and durations."""
        # D#3 with default length
        result = trainer.parse_abc_note_with_duration("D#3", 1.0)
        self.assertEqual(result, (51, 1.0))
        
        # D#32 (double length)
        result = trainer.parse_abc_note_with_duration("D#32", 1.0)
        self.assertEqual(result, (51, 2.0))
        
        # Db3 with default length
        result = trainer.parse_abc_note_with_duration("Db3", 1.0)
        self.assertEqual(result, (49, 1.0))

    def test_parse_abc_note_with_duration_division(self):
        """Test duration division with /N modifier."""
        # C4/4 should be 0.25 (quarter of default)
        result = trainer.parse_abc_note_with_duration("C4/4", 1.0)
        self.assertEqual(result, (60, 0.25))
        
        # C4/8 should be 0.125
        result = trainer.parse_abc_note_with_duration("C4/8", 1.0)
        self.assertEqual(result, (60, 0.125))

    def test_parse_abc_note_with_duration_multiplication(self):
        """Test duration multiplication with *N modifier."""
        # C4*4 should be 4.0 (quadruple)
        result = trainer.parse_abc_note_with_duration("C4*4", 1.0)
        self.assertEqual(result, (60, 4.0))
        
        # C4*3 should be 3.0
        result = trainer.parse_abc_note_with_duration("C4*3", 1.0)
        self.assertEqual(result, (60, 3.0))

    def test_parse_abc_note_custom_unit_length(self):
        """Test parsing with custom unit length (e.g., L:1/16)."""
        # With L:1/16 (0.25), C42 should be 0.5 (quarter note = 0.25 * 2)
        result = trainer.parse_abc_note_with_duration("C42", 0.25)
        self.assertEqual(result, (60, 0.5))
        
        # C4/2 should be 0.125 (half of 0.25)
        result = trainer.parse_abc_note_with_duration("C4/2", 0.25)
        self.assertEqual(result, (60, 0.125))

    def test_parse_abc_note_invalid(self):
        """Test that invalid note names return None."""
        self.assertIsNone(trainer.parse_abc_note_with_duration("X4", 1.0))
        self.assertIsNone(trainer.parse_abc_note_with_duration("C", 1.0))
        self.assertIsNone(trainer.parse_abc_note_with_duration("", 1.0))
        self.assertIsNone(trainer.parse_abc_note_with_duration("4C", 1.0))


class TestABCSequence(unittest.TestCase):
    """Test ABC sequence parsing."""

    def test_parse_abc_sequence_with_durations(self):
        """Test parsing ABC notation with note durations."""
        result = trainer.parse_abc_sequence("|C4 D42 E4|", 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        
        # First note: C4 (quarter note)
        self.assertEqual(result[0], (60, 1.0))
        
        # Second note: D42 (half note, doubled)
        self.assertEqual(result[1], (62, 2.0))
        
        # Third note: E4 (quarter note)
        self.assertEqual(result[2], (64, 1.0))

    def test_parse_abc_sequence_helper(self):
        """Test the parse_abc_sequence helper function with durations."""
        # New format returns list of (midi, duration) tuples
        result = trainer.parse_abc_sequence("|C4 D42 E4|")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        
        # Verify format
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], int)  # MIDI number
            self.assertIsInstance(item[1], float)  # Duration

    def test_parse_abc_sequence_multiple_bars(self):
        """Test ABC notation with multiple bars."""
        result = trainer.parse_abc_sequence("|C4 D42| |E4 G3|", 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        
        midi_notes = [n[0] for n in result]
        self.assertEqual(midi_notes, [60, 62, 64, 55])

    def test_parse_abc_sequence_with_accidentals(self):
        """Test ABC notation with sharps and flats."""
        result = trainer.parse_abc_sequence("|C#4 Db4 F#3|", 1.0)
        self.assertIsNotNone(result)
        
        midi_notes = [n[0] for n in result]
        self.assertEqual(midi_notes, [61, 61, 54])  # C#4=Db4=61

    def test_parse_abc_sequence_invalid(self):
        """Test that invalid ABC sequences return None."""
        self.assertIsNone(trainer.parse_abc_sequence("|invalid notes|"))
        self.assertIsNone(trainer.parse_abc_sequence("||"))
        self.assertIsNone(trainer.parse_abc_sequence("|X4 Y5|"))

    def test_parse_abc_sequence_single_note(self):
        """Test ABC sequence with single note."""
        result = trainer.parse_abc_sequence("|C4|", 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (60, 1.0))

    def test_parse_abc_sequence_with_whitespace(self):
        """Test ABC sequence with extra whitespace."""
        result = trainer.parse_abc_sequence("|  C4   D42   E4  |", 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0][0], 60)
        self.assertEqual(result[1][1], 2.0)


class TestSequenceParsing(unittest.TestCase):
    """Test sequence configuration parsing (both comma-separated and ABC)."""

    def test_parse_sequences_comma_separated_basic(self):
        """Test parsing basic comma-separated note sequences (backward compatible)."""
        sequences_cfg = [
            "D#3, A#2, C4",
            "G3, C4",
        ]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        
        # Now returns list of (midi, duration) tuples
        self.assertEqual(exercises[0][0], 'sequence')
        self.assertEqual(len(exercises[0][1]), 3)
        # First sequence: [(51, 1.0), (46, 1.0), (60, 1.0)]
        self.assertEqual(exercises[0][1][0][0], 51)
        self.assertEqual(exercises[0][1][1][0], 46)
        self.assertEqual(exercises[0][1][2][0], 60)
        
        # Second sequence: [(55, 1.0), (60, 1.0)]
        self.assertEqual(exercises[1][0], 'sequence')
        self.assertEqual(exercises[1][1][0][0], 55)
        self.assertEqual(exercises[1][1][1][0], 60)

    def test_parse_sequences_abc_notation_basic(self):
        """Test parsing ABC notation sequences with bar lines."""
        sequences_cfg = [
            "|D#3 A#2 C4|",
            "|G3 C4 A4 D3|",
        ]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        
        # First sequence: [(51, 1.0), (46, 1.0), (60, 1.0)]
        self.assertEqual(exercises[0][0], 'sequence')
        notes1 = exercises[0][1]
        self.assertEqual(notes1[0][0], 51)
        self.assertEqual(notes1[1][0], 46)
        self.assertEqual(notes1[2][0], 60)
        
        # Second sequence: [(55, 1.0), (60, 1.0), (69, 1.0), (50, 1.0)]
        notes2 = exercises[1][1]
        self.assertEqual(notes2[0][0], 55)
        self.assertEqual(notes2[1][0], 60)
        self.assertEqual(notes2[2][0], 69)
        self.assertEqual(notes2[3][0], 50)

    def test_parse_sequences_abc_multiple_bars(self):
        """Test ABC notation with multiple bars."""
        sequences_cfg = [
            "|D#3 A#2 C4| C4 |",
            "|G3 C4| A4 D3 |",
        ]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        
        # Bar lines should be stripped, notes extracted in order
        notes1 = exercises[0][1]
        self.assertEqual([n[0] for n in notes1], [51, 46, 60, 60])
        
        notes2 = exercises[1][1]
        self.assertEqual([n[0] for n in notes2], [55, 60, 69, 50])

    def test_parse_sequences_single_note(self):
        """Test parsing single-note sequences."""
        sequences_cfg = ["C4", "D4", "E4"]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 3)
        # Now returns list of tuples
        self.assertEqual(exercises[0][1][0][0], 60)
        self.assertEqual(exercises[1][1][0][0], 62)
        self.assertEqual(exercises[2][1][0][0], 64)

    def test_parse_sequences_single_note_abc(self):
        """Test parsing ABC notation with single note."""
        sequences_cfg = ["|C4|", "|D4|"]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        self.assertEqual(exercises[0][1][0][0], 60)
        self.assertEqual(exercises[1][1][0][0], 62)

    def test_parse_sequences_with_accidentals(self):
        """Test parsing sequences with sharps and flats."""
        sequences_cfg = ["C#3, Db4", "F#2, Gb3"]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        # C#3 = 49, Db4 = 61
        midi_notes1 = [n[0] for n in exercises[0][1]]
        self.assertEqual(midi_notes1, [49, 61])
        # F#2 = 42, Gb3 = 54
        midi_notes2 = [n[0] for n in exercises[1][1]]
        self.assertEqual(midi_notes2, [42, 54])

    def test_parse_sequences_abc_with_accidentals(self):
        """Test ABC notation with sharps and flats."""
        sequences_cfg = ["|C#3 Db4|", "|F#2 Gb3|"]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        midi_notes1 = [n[0] for n in exercises[0][1]]
        self.assertEqual(midi_notes1, [49, 61])
        midi_notes2 = [n[0] for n in exercises[1][1]]
        self.assertEqual(midi_notes2, [42, 54])

    def test_parse_sequences_empty(self):
        """Test parsing empty sequence list."""
        exercises = trainer.parse_sequences_from_config(None)
        self.assertEqual(len(exercises), 0)
        
        exercises = trainer.parse_sequences_from_config([])
        self.assertEqual(len(exercises), 0)

    def test_parse_sequences_whitespace_handling(self):
        """Test that whitespace is properly handled in both formats."""
        sequences_cfg = [
            "  D#3  ,  A#2  ,  C4  ",  # Extra spaces in comma-separated
            "G3,C4",  # No spaces
            "|  D#3  A#2  C4  |",  # Extra spaces in ABC
            "|G3 C4|",  # Normal ABC
        ]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 4)
        # All should parse correctly despite whitespace differences
        midi1 = [n[0] for n in exercises[0][1]]
        self.assertEqual(midi1, [51, 46, 60])
        
        midi2 = [n[0] for n in exercises[1][1]]
        self.assertEqual(midi2, [55, 60])
        
        midi3 = [n[0] for n in exercises[2][1]]
        self.assertEqual(midi3, [51, 46, 60])
        
        midi4 = [n[0] for n in exercises[3][1]]
        self.assertEqual(midi4, [55, 60])

    def test_sequence_type_in_exercises(self):
        """Test that parsed sequences have type 'sequence' (both formats)."""
        sequences_cfg = ["C4, E4, G4", "|C4 E4 G4|"]
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        for ex in exercises:
            self.assertEqual(ex[0], 'sequence')
            self.assertIsInstance(ex[1], list)

    def test_parse_sequences_structured_format(self):
        """Test parsing sequences with structured config (signature, L, notes)."""
        sequences_cfg = {
            'signature': '4/4',
            'unit_length': 1.0,  # Use numeric unit_length for clarity
            'notes': [
                "|C4 D42 E4|",
                "|G3 A3/2|"
            ]
        }
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 2)
        
        # First sequence: C4 (1.0), D4 (2.0), E4 (1.0)
        self.assertEqual(exercises[0][0], 'sequence')
        notes1 = exercises[0][1]
        self.assertEqual(len(notes1), 3)
        self.assertEqual(notes1[0], (60, 1.0))
        self.assertEqual(notes1[1], (62, 2.0))
        self.assertEqual(notes1[2], (64, 1.0))
        
        # Second sequence: G3 (1.0), A3 (0.5)
        notes2 = exercises[1][1]
        self.assertEqual(len(notes2), 2)
        self.assertEqual(notes2[0], (55, 1.0))
        self.assertEqual(notes2[1], (57, 0.5))

    def test_parse_sequences_structured_format_with_unit_length(self):
        """Test structured config with numeric unit_length."""
        sequences_cfg = {
            'signature': '4/4',
            'unit_length': 0.5,  # Half note as default
            'notes': ["|C42|"]  # Doubled = 1.0
        }
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 1)
        
        notes = exercises[0][1]
        self.assertEqual(len(notes), 1)
        # With unit_length=0.5, C42 should be 0.5 * 2 = 1.0
        self.assertEqual(notes[0], (60, 1.0))

    def test_parse_sequences_structured_format_with_L_notation(self):
        """Test structured config with L:ratio notation."""
        sequences_cfg = {
            'signature': '4/4',
            'L': '1/4',  # L notation (quarter note)
            'notes': ["|C42|"]  # Doubled = 0.5
        }
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        self.assertEqual(len(exercises), 1)
        
        notes = exercises[0][1]
        self.assertEqual(len(notes), 1)
        # With L:1/4 (0.25), C42 should be 0.25 * 2 = 0.5
        self.assertEqual(notes[0], (60, 0.5))


class TestSequenceMIDIDurations(unittest.TestCase):
    """Test that per-note durations are correctly reflected in MIDI."""

    def test_sequence_midi_durations_respected_in_session(self):
        """Ensure that per-note durations from ABC sequences are reflected in session MIDI ticks.

        Example: unit_length=1.0 (quarter note). Sequence: |G#2 C4 E32|
        E32 means E3 with multiplier 2 -> duration = 2.0 beats (half note).
        At 120 BPM and ticks_per_beat=480, a quarter note -> 960 ticks, half -> 1920 ticks.
        """
        seq_cfg = {
            'notes': ["|G#2 C4 E32|"],
            'unit_length': 1.0,
        }
        exercises = trainer.parse_sequences_from_config(seq_cfg, default_unit_length=1.0)
        self.assertEqual(len(exercises), 1)
        ex = exercises[0]
        self.assertEqual(ex[0], 'sequence')
        notes_with_dur = ex[1]
        # Expect three notes with durations: (G#2,1.0), (C4,1.0), (E3,2.0)
        self.assertEqual(len(notes_with_dur), 3)
        self.assertEqual(notes_with_dur[0][1], 1.0)
        self.assertEqual(notes_with_dur[1][1], 1.0)
        self.assertEqual(notes_with_dur[2][1], 2.0)

        # Build a session MIDI just like main() does and inspect tick values
        from mido import MidiFile, MidiTrack, Message, bpm2tempo
        session_mid = MidiFile()
        track = MidiTrack()
        session_mid.tracks.append(track)
        tempo_bpm = 120
        track.append(__import__('mido').MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
        ticks_per_beat = session_mid.ticks_per_beat
        def secs_to_ticks(s):
            return int(s * (ticks_per_beat * tempo_bpm / 60.0))

        # Append notes as main() would
        for midi_note, dur in notes_with_dur:
            track.append(Message('note_on', note=int(midi_note), velocity=90, time=0))
            track.append(Message('note_off', note=int(midi_note), velocity=0, time=secs_to_ticks(dur)))

        # Now inspect the track to find the note_off for E3
        # E3 MIDI value:
        e3 = trainer.note_name_to_midi('E3')
        note_offs = [m for m in track if hasattr(m, 'note') and m.type == 'note_off' and m.note == e3]
        self.assertTrue(len(note_offs) >= 1)
        # The time field on the note_off event should be ticks for half note (1920)
        expected_half_ticks = secs_to_ticks(2.0)
        self.assertEqual(note_offs[0].time, expected_half_ticks)

    def test_sequence_with_mixed_durations(self):
        """Test sequence with various duration modifiers."""
        sequences_cfg = {
            'notes': ["|C4 D4/2 E42 F4/4|"],
            'unit_length': 1.0,
        }
        exercises = trainer.parse_sequences_from_config(sequences_cfg)
        notes = exercises[0][1]
        
        # C4: 1.0, D4/2: 0.5, E4*2: 2.0, F4/4: 0.25
        self.assertEqual(notes[0][1], 1.0)
        self.assertEqual(notes[1][1], 0.5)
        self.assertEqual(notes[2][1], 2.0)
        self.assertEqual(notes[3][1], 0.25)


if __name__ == '__main__':
    unittest.main()
