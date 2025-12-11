#!/usr/bin/env python3
"""Unit tests for time signature validation."""
import unittest
import tempfile
import os
import yaml
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import intonation_trainer as trainer


class TestTimeSignatureValidation(unittest.TestCase):
    """Test time signature validation functionality."""

    def test_valid_4_4_measure(self):
        """Test a valid 4/4 measure."""
        # 4 quarter notes = 4 beats
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            (65, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, _, _ = trainer.validate_time_signature(notes, '4/4')
        self.assertTrue(is_valid, f"Should be valid but got error: {error_msg}")

    def test_invalid_4_4_measure_too_short(self):
        """Test an invalid 4/4 measure with too few beats."""
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, _, _ = trainer.validate_time_signature(notes, '4/4')
        self.assertFalse(is_valid, "Should be invalid (only 3 beats in 4/4)")
        self.assertIn("3", error_msg)
        self.assertIn("4", error_msg)

    def test_invalid_4_4_measure_too_long(self):
        """Test an invalid 4/4 measure with too many beats."""
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            (65, 1.0),
            (67, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, _, _ = trainer.validate_time_signature(notes, '4/4')
        self.assertFalse(is_valid, "Should be invalid (5 beats in 4/4)")

    def test_valid_3_4_measure(self):
        """Test a valid 3/4 measure."""
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, _, _ = trainer.validate_time_signature(notes, '3/4')
        self.assertTrue(is_valid, f"Should be valid but got error: {error_msg}")

    def test_inline_time_signature_change(self):
        """Test inline time signature change (e.g., |3 for 3/4 measure)."""
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            (65, 1.0),
            ('measure_end', None),
            ('measure_start', 3),  # Inline: next measure is 3/4
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, _, _ = trainer.validate_time_signature(notes, '4/4')
        self.assertTrue(is_valid, f"Should be valid but got error: {error_msg}")

    def test_partial_measure_at_start(self):
        """Test partial measure at start (no opening |)."""
        notes = [
            (60, 1.0),
            (62, 1.0),
            ('measure_end', None),
            ('measure_start', None),
            (64, 1.0),
            (65, 1.0),
            (67, 1.0),
            (69, 1.0),
            ('measure_end', None)
        ]
        is_valid, error_msg, has_partial_start, _ = trainer.validate_time_signature(notes, '4/4')
        self.assertTrue(is_valid, f"Should be valid (partial start allowed) but got: {error_msg}")
        self.assertTrue(has_partial_start, "Should detect partial start")

    def test_partial_measure_at_end(self):
        """Test partial measure at end (no closing |)."""
        notes = [
            ('measure_start', None),
            (60, 1.0),
            (62, 1.0),
            (64, 1.0),
            (65, 1.0),
            ('measure_end', None),
            ('measure_start', None),
            (67, 1.0),
            (69, 1.0)
        ]
        is_valid, error_msg, _, has_partial_end = trainer.validate_time_signature(notes, '4/4')
        self.assertTrue(is_valid, f"Should be valid (partial end allowed) but got: {error_msg}")
        self.assertTrue(has_partial_end, "Should detect partial end")

    def test_parse_abc_with_measure_markers(self):
        """Test parsing ABC notation with measure markers."""
        abc_str = "| C4 D4 | E4 F4 |"
        notes = trainer.parse_abc_sequence(abc_str, 1.0, include_markers=True)
        
        # Should have measure markers
        self.assertIsInstance(notes, list)
        # Check for measure markers
        markers = [n for n in notes if isinstance(n, tuple) and n[0] in ['measure_start', 'measure_end']]
        self.assertGreater(len(markers), 0, "Should have measure markers")

    def test_parse_abc_with_inline_time_signature(self):
        """Test parsing ABC notation with inline time signature."""
        abc_str = "|3 C4 D4 E4 | F4 G4 A4 B4 |"
        notes = trainer.parse_abc_sequence(abc_str, 1.0, include_markers=True)
        
        # Should have inline time signature marker
        self.assertIsInstance(notes, list)
        inline_markers = [n for n in notes if isinstance(n, tuple) and n[0] == 'measure_start' and len(n) > 1 and n[1] == 3]
        self.assertGreater(len(inline_markers), 0, "Should have inline time signature marker")

    def test_validation_disabled(self):
        """Test that validation can be disabled via config."""
        config = {
            'output': {'filename': 'test.mid', 'format': 'mid'},
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'validate_time_signature': False,  # Disabled
                'notes': [
                    "| C4 D4 E4 |"  # Invalid: only 3 beats in 4/4
                ]
            },
            'timing': {'note_duration': 1.0, 'pause_between_reps': 1.0},
            'repetitions_per_exercise': 1,
            'max_duration': 60
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Should parse without errors (validation disabled)
            exercises = trainer.parse_sequences_from_config(config['sequences'])
            self.assertEqual(len(exercises), 1, "Should have parsed 1 sequence")


if __name__ == '__main__':
    unittest.main()
