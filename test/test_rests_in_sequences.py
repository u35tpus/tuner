#!/usr/bin/env python3
"""Unit tests for rest/pause support in sequences with various durations."""
import unittest
import intonation_trainer as trainer


class TestRestsInSequences(unittest.TestCase):
    """Test rest/pause notation in sequences with different durations."""
    
    def test_basic_rest_quarter_note(self):
        """Test basic rest with default duration (quarter note)."""
        result = trainer.parse_abc_note_with_duration('z', 1.0)
        self.assertEqual(result, ('rest', 1.0))
    
    def test_rest_half_note(self):
        """Test rest with duration 2 (half note)."""
        result = trainer.parse_abc_note_with_duration('z2', 1.0)
        self.assertEqual(result, ('rest', 2.0))
    
    def test_rest_whole_note(self):
        """Test rest with duration 4 (whole note)."""
        result = trainer.parse_abc_note_with_duration('z4', 1.0)
        self.assertEqual(result, ('rest', 4.0))
    
    def test_rest_eighth_note(self):
        """Test rest with division (eighth note)."""
        result = trainer.parse_abc_note_with_duration('z/2', 1.0)
        self.assertEqual(result, ('rest', 0.5))
    
    def test_rest_sixteenth_note(self):
        """Test rest with division (sixteenth note)."""
        result = trainer.parse_abc_note_with_duration('z/4', 1.0)
        self.assertEqual(result, ('rest', 0.25))
    
    def test_rest_dotted_half(self):
        """Test rest with explicit duration (dotted half = 3 beats)."""
        result = trainer.parse_abc_note_with_duration('z:3', 1.0)
        self.assertEqual(result, ('rest', 3.0))
    
    def test_rest_explicit_decimal(self):
        """Test rest with explicit decimal duration."""
        result = trainer.parse_abc_note_with_duration('z:1.5', 1.0)
        self.assertEqual(result, ('rest', 1.5))
    
    def test_rest_multiplication_syntax(self):
        """Test rest with multiplication syntax."""
        result = trainer.parse_abc_note_with_duration('z*2', 1.0)
        self.assertEqual(result, ('rest', 2.0))
    
    def test_uppercase_rest(self):
        """Test uppercase Z notation for rest."""
        result = trainer.parse_abc_note_with_duration('Z', 1.0)
        self.assertEqual(result, ('rest', 1.0))
        
        result = trainer.parse_abc_note_with_duration('Z2', 1.0)
        self.assertEqual(result, ('rest', 2.0))
    
    def test_x_rest_notation(self):
        """Test x notation for rest (alternative)."""
        result = trainer.parse_abc_note_with_duration('x', 1.0)
        self.assertEqual(result, ('rest', 1.0))
        
        result = trainer.parse_abc_note_with_duration('x2', 1.0)
        self.assertEqual(result, ('rest', 2.0))
    
    def test_sequence_with_mixed_rests(self):
        """Test sequence with notes and rests of different durations."""
        # C4 (quarter), rest (half), D4 (quarter), rest (eighth), E4 (quarter)
        result = trainer.parse_abc_sequence('C4 z2 D4 z/2 E4', 1.0)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)
        
        # Check each element
        self.assertEqual(result[0][0], 60)  # C4
        self.assertEqual(result[0][1], 1.0)
        
        self.assertEqual(result[1], ('rest', 2.0))  # z2
        
        self.assertEqual(result[2][0], 62)  # D4
        self.assertEqual(result[2][1], 1.0)
        
        self.assertEqual(result[3], ('rest', 0.5))  # z/2
        
        self.assertEqual(result[4][0], 64)  # E4
        self.assertEqual(result[4][1], 1.0)
    
    def test_sequence_with_bars_and_rests(self):
        """Test sequence with bar lines and various rest durations."""
        # Start with rest, then notes with bar lines
        result = trainer.parse_abc_sequence('| z | C4 D4 | z2 | E4 F4 G4 |', 1.0)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 7)
        
        self.assertEqual(result[0], ('rest', 1.0))  # z
        self.assertEqual(result[1][0], 60)  # C4
        self.assertEqual(result[2][0], 62)  # D4
        self.assertEqual(result[3], ('rest', 2.0))  # z2
        self.assertEqual(result[4][0], 64)  # E4
        self.assertEqual(result[5][0], 65)  # F4
        self.assertEqual(result[6][0], 67)  # G4
    
    def test_sequence_all_rests(self):
        """Test sequence with only rests."""
        result = trainer.parse_abc_sequence('z z2 z4 z/2', 1.0)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        
        self.assertEqual(result[0], ('rest', 1.0))
        self.assertEqual(result[1], ('rest', 2.0))
        self.assertEqual(result[2], ('rest', 4.0))
        self.assertEqual(result[3], ('rest', 0.5))
    
    def test_sequence_with_explicit_rest_durations(self):
        """Test sequence with explicit decimal rest durations."""
        result = trainer.parse_abc_sequence('C4 z:0.25 D4 z:1.5 E4', 1.0)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)
        
        self.assertEqual(result[0][0], 60)  # C4
        self.assertEqual(result[1], ('rest', 0.25))  # z:0.25
        self.assertEqual(result[2][0], 62)  # D4
        self.assertEqual(result[3], ('rest', 1.5))  # z:1.5
        self.assertEqual(result[4][0], 64)  # E4
    
    def test_musical_phrase_with_rests(self):
        """Test realistic musical phrase with rests for breathing."""
        # Musical phrase: C D E rest(quarter) E F G rest(half) G A B C
        result = trainer.parse_abc_sequence('C4 D4 E4 z E4 F4 G4 z2 G4 A4 B4 C5', 1.0)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 12)
        
        # Verify rest positions
        self.assertEqual(result[3], ('rest', 1.0))  # After E
        self.assertEqual(result[7], ('rest', 2.0))  # After G (longer)
    
    def test_parse_sequences_from_config_with_rests(self):
        """Test parsing sequences from config dict with rests."""
        config = {
            'signature': '4/4',
            'unit_length': 1.0,
            'notes': [
                'C4 z D4 E4',
                'z2 F4 G4 z',
                'A4 z/2 B4 z:1.5 C5'
            ]
        }
        
        exercises = trainer.parse_sequences_from_config(config)
        
        self.assertEqual(len(exercises), 3)
        
        # First sequence: C4 z D4 E4
        seq1 = exercises[0][1]
        self.assertEqual(len(seq1), 4)
        self.assertEqual(seq1[0][0], 60)  # C4
        self.assertEqual(seq1[1], ('rest', 1.0))  # z
        self.assertEqual(seq1[2][0], 62)  # D4
        self.assertEqual(seq1[3][0], 64)  # E4
        
        # Second sequence: z2 F4 G4 z
        seq2 = exercises[1][1]
        self.assertEqual(len(seq2), 4)
        self.assertEqual(seq2[0], ('rest', 2.0))  # z2
        self.assertEqual(seq2[1][0], 65)  # F4
        self.assertEqual(seq2[2][0], 67)  # G4
        self.assertEqual(seq2[3], ('rest', 1.0))  # z
        
        # Third sequence: A4 z/2 B4 z:1.5 C5
        seq3 = exercises[2][1]
        self.assertEqual(len(seq3), 5)
        self.assertEqual(seq3[0][0], 69)  # A4
        self.assertEqual(seq3[1], ('rest', 0.5))  # z/2
        self.assertEqual(seq3[2][0], 71)  # B4
        self.assertEqual(seq3[3], ('rest', 1.5))  # z:1.5
        self.assertEqual(seq3[4][0], 72)  # C5


class TestRestsWithDifferentUnitLengths(unittest.TestCase):
    """Test rests with different unit_length values."""
    
    def test_rest_with_half_note_unit(self):
        """Test rest when unit_length is 0.5 (half note basis)."""
        # With unit_length=0.5, 'z' = 0.5 beats, 'z2' = 1.0 beats
        result = trainer.parse_abc_note_with_duration('z', 0.5)
        self.assertEqual(result, ('rest', 0.5))
        
        result = trainer.parse_abc_note_with_duration('z2', 0.5)
        self.assertEqual(result, ('rest', 1.0))
    
    def test_rest_with_eighth_note_unit(self):
        """Test rest when unit_length is 0.25 (eighth note basis)."""
        result = trainer.parse_abc_note_with_duration('z', 0.25)
        self.assertEqual(result, ('rest', 0.25))
        
        result = trainer.parse_abc_note_with_duration('z4', 0.25)
        self.assertEqual(result, ('rest', 1.0))
    
    def test_sequence_with_different_unit_length(self):
        """Test sequence parsing with non-standard unit_length."""
        config = {
            'signature': '4/4',
            'unit_length': 0.5,  # Half note as unit
            'notes': [
                'C4 z D4 z2 E4'  # C, rest(half), D, rest(whole), E
            ]
        }
        
        exercises = trainer.parse_sequences_from_config(config)
        seq = exercises[0][1]
        
        self.assertEqual(len(seq), 5)
        self.assertEqual(seq[0][1], 0.5)  # C4 duration
        self.assertEqual(seq[1], ('rest', 0.5))  # z = 0.5
        self.assertEqual(seq[2][1], 0.5)  # D4 duration
        self.assertEqual(seq[3], ('rest', 1.0))  # z2 = 1.0
        self.assertEqual(seq[4][1], 0.5)  # E4 duration


if __name__ == '__main__':
    unittest.main()
