import unittest
import intonation_trainer as trainer

class TestABCPreparse(unittest.TestCase):
    def test_preparse_valid(self):
        # All notes valid
        result = trainer.preparse_abc_notes("C4 D4 E4 F#4 G4", 1.0)
        self.assertTrue(result)

    def test_preparse_invalid_note(self):
        # One invalid note
        result = trainer.preparse_abc_notes("C4 D4 X4 F#4", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Pre-parsing error", result[1])
        self.assertIn("X4", result[1])

    def test_preparse_invalid_duration(self):
        # Invalid duration
        result = trainer.preparse_abc_notes("C4:abc D4", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Pre-parsing error", result[1])
        self.assertIn("C4:abc", result[1])

    def test_preparse_rest(self):
        # Valid rest
        result = trainer.preparse_abc_notes("z2 C4 D4", 1.0)
        self.assertTrue(result)

    def test_preparse_multiple_errors(self):
        # Multiple errors, should report first
        result = trainer.preparse_abc_notes("C4 Y4 Z4", 1.0)
        self.assertIsNotNone(result)
        self.assertIsNone(result[0])
        self.assertIn("Y4", result[1])

if __name__ == "__main__":
    unittest.main()
