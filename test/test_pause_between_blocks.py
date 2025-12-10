#!/usr/bin/env python3
"""Unit tests for pause_between_blocks functionality."""
import unittest
import tempfile
import os
import yaml
import intonation_trainer as trainer
from mido import MidiFile, bpm2tempo


class TestPauseBetweenBlocks(unittest.TestCase):
    """Test that pause_between_blocks works correctly."""

    def test_pause_between_blocks_zero(self):
        """Test that setting pause_between_blocks to 0 results in no pause between blocks."""
        config = {
            'output': {'filename': 'test.mid', 'format': 'mid'},
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'notes': [
                    "C4",  # Exercise 1
                    "D4",  # Exercise 2
                ],
                'combine_sequences_to_one': False
            },
            'timing': {
                'note_duration': 1.0,
                'pause_between_reps': 0.5,  # Pause between reps within a block
                'pause_between_blocks': 0.0  # No pause between blocks
            },
            'repetitions_per_exercise': 2,  # Each exercise repeated 2 times
            'max_duration': 60
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Run the trainer
            import sys
            sys_argv_backup = sys.argv
            try:
                output_path = os.path.join(tmpdir, 'test.mid')
                sys.argv = ['intonation_trainer.py', config_path, '--output', output_path]
                trainer.main()
                
                # Read the generated MIDI file
                mid = MidiFile(output_path)
                track = mid.tracks[0]
                
                # Extract note events and pauses
                # Expected structure with repetitions_per_exercise=2:
                # Block 1: C4, pause_between_reps, C4, pause_between_blocks
                # Block 2: D4, pause_between_reps, D4, (final pause)
                
                tempo_bpm = 120
                ticks_per_beat = mid.ticks_per_beat
                
                def secs_to_ticks(s):
                    return int(s * (ticks_per_beat * tempo_bpm / 60.0))
                
                # Find all pauses (time values in messages)
                events = []
                for msg in track:
                    if hasattr(msg, 'note') and msg.type == 'note_on':
                        events.append(('note_on', msg.note, msg.time))
                    elif hasattr(msg, 'note') and msg.type == 'note_off':
                        events.append(('note_off', msg.note, msg.time))
                    elif msg.type == 'track_name' and msg.time > 0:
                        events.append(('pause', msg.time))
                
                # Find pauses
                pauses = [e[1] for e in events if e[0] == 'pause']
                
                # We expect 3 pauses total (pause_between_blocks=0 doesn't create a message):
                # 1. After first C4 (pause_between_reps = 0.5s)
                # 2. After second C4 (pause_between_blocks = 0.0s) - NO MESSAGE when 0
                # 3. After first D4 (pause_between_reps = 0.5s)
                # 4. After second D4 (pause_between_reps = 0.5s) - final pause
                
                self.assertEqual(len(pauses), 3, f"Expected 3 pauses (0-duration pauses create no MIDI event), got {len(pauses)}")
                
                expected_pause_reps = secs_to_ticks(0.5)
                
                # Check pauses - all should be pause_between_reps
                self.assertAlmostEqual(pauses[0], expected_pause_reps, delta=5, 
                                      msg="First pause should be pause_between_reps")
                self.assertAlmostEqual(pauses[1], expected_pause_reps, delta=5,
                                      msg="Second pause should be pause_between_reps (block boundary had 0 pause)")
                self.assertAlmostEqual(pauses[2], expected_pause_reps, delta=5,
                                      msg="Third pause should be pause_between_reps")
                
            finally:
                sys.argv = sys_argv_backup

    def test_pause_between_blocks_nonzero(self):
        """Test that pause_between_blocks adds correct pause between different exercise blocks."""
        config = {
            'output': {'filename': 'test.mid', 'format': 'mid'},
            'sequences': {
                'signature': '4/4',
                'unit_length': 1.0,
                'notes': [
                    "C4",  # Exercise 1
                    "E4",  # Exercise 2
                ],
                'combine_sequences_to_one': False
            },
            'timing': {
                'note_duration': 1.0,
                'pause_between_reps': 0.3,  # Short pause between reps
                'pause_between_blocks': 2.0  # Longer pause between blocks
            },
            'repetitions_per_exercise': 3,  # Each exercise repeated 3 times
            'max_duration': 60
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Run the trainer
            import sys
            sys_argv_backup = sys.argv
            try:
                output_path = os.path.join(tmpdir, 'test.mid')
                sys.argv = ['intonation_trainer.py', config_path, '--output', output_path]
                trainer.main()
                
                # Read the generated MIDI file
                mid = MidiFile(output_path)
                track = mid.tracks[0]
                
                tempo_bpm = 120
                ticks_per_beat = mid.ticks_per_beat
                
                def secs_to_ticks(s):
                    return int(s * (ticks_per_beat * tempo_bpm / 60.0))
                
                # Find all pauses
                events = []
                for msg in track:
                    if msg.type == 'track_name' and msg.time > 0:
                        events.append(('pause', msg.time))
                
                pauses = [e[1] for e in events if e[0] == 'pause']
                
                # We expect 6 pauses total:
                # Block 1 (C4): rep1, pause_reps, rep2, pause_reps, rep3, pause_blocks
                # Block 2 (E4): rep1, pause_reps, rep2, pause_reps, rep3, pause_reps
                
                self.assertEqual(len(pauses), 6, f"Expected 6 pauses, got {len(pauses)}")
                
                expected_pause_reps = secs_to_ticks(0.3)
                expected_pause_blocks = secs_to_ticks(2.0)
                
                # Pauses 0, 1: within block 1 (should be pause_between_reps)
                self.assertAlmostEqual(pauses[0], expected_pause_reps, delta=5,
                                      msg="Pause 0 should be pause_between_reps")
                self.assertAlmostEqual(pauses[1], expected_pause_reps, delta=5,
                                      msg="Pause 1 should be pause_between_reps")
                
                # Pause 2: between blocks (should be pause_between_blocks)
                self.assertAlmostEqual(pauses[2], expected_pause_blocks, delta=5,
                                      msg="Pause 2 should be pause_between_blocks (2.0s)")
                
                # Pauses 3, 4, 5: within block 2 (should be pause_between_reps)
                self.assertAlmostEqual(pauses[3], expected_pause_reps, delta=5,
                                      msg="Pause 3 should be pause_between_reps")
                self.assertAlmostEqual(pauses[4], expected_pause_reps, delta=5,
                                      msg="Pause 4 should be pause_between_reps")
                
            finally:
                sys.argv = sys_argv_backup


if __name__ == '__main__':
    unittest.main()
