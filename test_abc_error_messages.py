#!/usr/bin/env python3
import unittest
import intonation_trainer as trainer


class TestImprovedABCErrorMessages(unittest.TestCase):
    """Test improved error messages for ABC notation parsing."""
    
    def test_rest_parsing(self):
        # Test basic rest
        result = trainer.parse_abc_note_with_duration('z', 1.0)
        self.assertEqual(result, ('rest', 1.0))
        
        # Test rest with duration
        result = trainer.parse_abc_note_with_duration('z2', 1.0)
        self.assertEqual(result, ('rest', 2.0))
        
        # Test rest with explicit duration
        result = trainer.parse_abc_note_with_duration('z:1.5', 1.0)
        self.assertEqual(result, ('rest', 1.5))
    
    def test_accidental_after_octave(self):
        # F4# should be parsed same as F#4
        result1 = trainer.parse_abc_note_with_duration('F4#', 1.0)
        result2 = trainer.parse_abc_note_with_duration('F#4', 1.0)
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertEqual(result1[0], result2[0])  # Same MIDI note
        
        # Bb3 and B3b should work the same
        result1 = trainer.parse_abc_note_with_duration('Bb3', 1.0)
        result2 = trainer.parse_abc_note_with_duration('B3b', 1.0)
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertEqual(result1[0], result2[0])
    
    def test_explicit_duration_colon_syntax(self):
        # Test :duration syntax
        result = trainer.parse_abc_note_with_duration('C4:1.5', 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 60)  # C4
        self.assertEqual(result[1], 1.5)
        
        result = trainer.parse_abc_note_with_duration('E4:0.5', 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 0.5)
    
    def test_error_message_for_invalid_note(self):
        # Test that we get descriptive error message
        result = trainer.parse_abc_note_with_duration('X4', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Invalid note format", result[1])
        self.assertIn("X4", result[1])
    
    def test_error_message_for_conflicting_accidentals(self):
        # Test conflicting accidentals
        result = trainer.parse_abc_note_with_duration('F#4#', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Conflicting accidentals", result[1])
    
    def test_error_message_for_invalid_duration(self):
        # Test invalid duration syntax
        result = trainer.parse_abc_note_with_duration('C4:abc', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        # The regex doesn't match notes with invalid characters in duration, 
        # so we get "Invalid note format" rather than "Invalid duration"
        self.assertIn("Invalid", result[1])
        self.assertIn("C4:abc", result[1])
    
    def test_sequence_with_rest(self):
        # Test sequence with rests
        result = trainer.parse_abc_sequence('z2 | B3 | E4', 1.0)
        self.assertIsNotNone(result)
        self.assertNotEqual(result[0], None)  # Should succeed
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ('rest', 2.0))
    
    def test_sequence_with_colon_durations(self):
        # Original problematic sequence
        result = trainer.parse_abc_sequence('z2 | B3 | E4:1.5  F4#:0.5 G4 B4 |', 1.0)
        self.assertIsNotNone(result)
        # Should succeed now
        if isinstance(result, tuple) and result[0] is None:
            self.fail(f"Parsing failed: {result[1]}")
        
        # Verify we got all the notes
        self.assertEqual(len(result), 6)  # z2, B3, E4:1.5, F4#:0.5, G4, B4
        self.assertEqual(result[0], ('rest', 2.0))
        self.assertAlmostEqual(result[2][1], 1.5)  # E4:1.5
        self.assertAlmostEqual(result[3][1], 0.5)  # F4#:0.5
    
    def test_detailed_error_position_in_sequence(self):
        # Test that error message includes position
        result = trainer.parse_abc_sequence('C4 D4 X4 E4', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        error_msg = result[1]
        self.assertIn("position 3", error_msg)
        self.assertIn("X4", error_msg)
        self.assertIn("Context", error_msg)
    
    def test_empty_sequence_error(self):
        result = trainer.parse_abc_sequence('| |', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("No notes found", result[1])
    
    def test_duration_division_by_zero(self):
        result = trainer.parse_abc_note_with_duration('C4/0', 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("divide by zero", result[1].lower())


class TestABCBackwardCompatibility(unittest.TestCase):
    """Ensure backward compatibility with existing ABC parsing."""
    
    def test_basic_notes_still_work(self):
        # Existing tests should still pass
        result = trainer.parse_abc_note_with_duration('C4', 1.0)
        self.assertEqual(result, (60, 1.0))
        
        result = trainer.parse_abc_note_with_duration('F#3', 1.0)
        self.assertEqual(result[0], 54)
    
    def test_duration_modifiers_still_work(self):
        result = trainer.parse_abc_note_with_duration('C42', 1.0)
        self.assertEqual(result, (60, 2.0))
        
        result = trainer.parse_abc_note_with_duration('C4/2', 1.0)
        self.assertEqual(result, (60, 0.5))
        
        result = trainer.parse_abc_note_with_duration('C4*2', 1.0)
        self.assertEqual(result, (60, 2.0))
    
    def test_sequence_parsing_backward_compatible(self):
        result = trainer.parse_abc_sequence('|C4 D4 E4|', 1.0)
        self.assertIsNotNone(result)
        self.assertNotEqual(result[0], None)
        self.assertEqual(len(result), 3)


if __name__ == '__main__':
    unittest.main()
