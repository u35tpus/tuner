import unittest
import intonation_trainer as trainer
import random

class TestRhythmVocalExercises(unittest.TestCase):
    def setUp(self):
        self.base_note = 60  # C4
        random.seed(42)
    
    def test_rhythm_vocal_generation(self):
        """Test basic rhythm vocal exercise generation"""
        exercises = trainer.generate_rhythm_vocal_exercises(self.base_note, num_exercises=5, max_pattern_length=8)
        
        # Check we got the right number
        self.assertEqual(len(exercises), 5)
        
        # Check structure
        for ex in exercises:
            self.assertEqual(ex[0], 'rhythm_vocal')
            self.assertIsInstance(ex[1], list)
            self.assertGreater(len(ex[1]), 0)
            
            # Check all notes are base_note with varying durations
            for note, duration in ex[1]:
                self.assertEqual(note, self.base_note)
                self.assertGreater(duration, 0)
    
    def test_rhythm_vocal_max_pattern_length(self):
        """Test that max_pattern_length is respected"""
        max_len = 4
        exercises = trainer.generate_rhythm_vocal_exercises(self.base_note, num_exercises=10, max_pattern_length=max_len)
        
        for ex in exercises:
            notes_with_dur = ex[1]
            self.assertLessEqual(len(notes_with_dur), max_len)
    
    def test_rhythm_vocal_different_base_notes(self):
        """Test rhythm exercises with different base notes"""
        base_notes = [60, 64, 67]  # C4, E4, G4
        
        for base in base_notes:
            exercises = trainer.generate_rhythm_vocal_exercises(base, num_exercises=3)
            
            for ex in exercises:
                for note, duration in ex[1]:
                    self.assertEqual(note, base)
    
    def test_rhythm_vocal_variety(self):
        """Test that different rhythm patterns are generated"""
        exercises = trainer.generate_rhythm_vocal_exercises(self.base_note, num_exercises=10)
        
        # Collect all patterns
        patterns = []
        for ex in exercises:
            pattern = tuple(d for n, d in ex[1])
            patterns.append(pattern)
        
        # Check we have some variety (at least 50% unique)
        unique_patterns = set(patterns)
        self.assertGreaterEqual(len(unique_patterns), len(patterns) * 0.5)

if __name__ == '__main__':
    unittest.main()
