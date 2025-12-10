import unittest
import tempfile
import os
from intonation_trainer import write_text_log

class TestMeasureMarkers(unittest.TestCase):
    def test_measure_markers_in_sequence(self):
        """Test that measure markers are correctly inserted in sequences."""
        # Create a sequence with notes that span multiple measures in 4/4 time
        # 4 quarter notes = 1 measure in 4/4
        exercises = [
            ('sequence', [
                (60, 1.0),  # C4, 1 beat
                (62, 1.0),  # D4, 1 beat
                (64, 1.0),  # E4, 1 beat
                (65, 1.0),  # F4, 1 beat - end of measure 1
                (67, 1.0),  # G4, 1 beat - start of measure 2
                (69, 1.0),  # A4, 1 beat
                (71, 1.0),  # B4, 1 beat
                (72, 1.0),  # C5, 1 beat - end of measure 2
            ])
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            write_text_log(temp_path, exercises, ticks_per_beat=480, scale_name='test', time_signature='4/4')
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check that measure markers are present
            self.assertIn('|M1|', content, "Should have measure 1 marker")
            self.assertIn('|M2|', content, "Should have measure 2 marker")
            
            # Check that the time signature is in the header
            self.assertIn('Time Signature: 4/4', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_measure_markers_with_rests(self):
        """Test measure markers work correctly with rests."""
        exercises = [
            ('sequence', [
                ('rest', 1.0),  # Rest, 1 beat
                ('rest', 1.0),  # Rest, 1 beat
                ('rest', 1.0),  # Rest, 1 beat
                (60, 1.0),      # C4, 1 beat - end of measure 1
                (62, 2.0),      # D4, 2 beats - start of measure 2
                (64, 2.0),      # E4, 2 beats - end of measure 2
            ])
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            write_text_log(temp_path, exercises, ticks_per_beat=480, scale_name='test', time_signature='4/4')
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check that measure markers are present
            self.assertIn('|M1|', content, "Should have measure 1 marker")
            self.assertIn('|M2|', content, "Should have measure 2 marker")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_measure_markers_3_4_time(self):
        """Test measure markers in 3/4 time signature."""
        exercises = [
            ('sequence', [
                (60, 1.0),  # C4, 1 beat
                (62, 1.0),  # D4, 1 beat
                (64, 1.0),  # E4, 1 beat - end of measure 1 (3/4 = 3 beats per measure)
                (65, 1.0),  # F4, 1 beat - start of measure 2
                (67, 1.0),  # G4, 1 beat
                (69, 1.0),  # A4, 1 beat - end of measure 2
            ])
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            write_text_log(temp_path, exercises, ticks_per_beat=480, scale_name='test', time_signature='3/4')
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check that measure markers are present
            self.assertIn('|M1|', content, "Should have measure 1 marker")
            self.assertIn('|M2|', content, "Should have measure 2 marker")
            
            # Check that the time signature is in the header
            self.assertIn('Time Signature: 3/4', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

if __name__ == '__main__':
    unittest.main()
