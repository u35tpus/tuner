#!/usr/bin/env python3
"""
Test that error messages are printed in red color
"""
import unittest
import sys
import io
from contextlib import redirect_stdout
import intonation_trainer


class TestColoredErrorOutput(unittest.TestCase):
    
    def test_print_red_function_exists(self):
        """Test that print_red function exists"""
        self.assertTrue(hasattr(intonation_trainer, 'print_red'))
        self.assertTrue(callable(intonation_trainer.print_red))
    
    def test_print_red_output_contains_ansi_codes(self):
        """Test that print_red produces ANSI color codes"""
        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            intonation_trainer.print_red("Test error message")
        
        output = captured_output.getvalue()
        # Check for ANSI red color code (91m) and reset code (0m)
        self.assertIn('\033[91m', output, "Output should contain red color ANSI code")
        self.assertIn('\033[0m', output, "Output should contain ANSI reset code")
        self.assertIn('Test error message', output, "Output should contain the message")


if __name__ == '__main__':
    unittest.main()
