import unittest
import os
import glob
import subprocess
import tempfile
import shutil

class TestTracksConfigs(unittest.TestCase):
    def test_all_tracks_configs(self):
        """
        Recursively find all YAML configs in 'tracks' folder and try to generate MIDI for each.
        Fails if the script returns a non-zero exit code.
        """
        # Get the root of the workspace
        workspace_root = os.path.dirname(os.path.abspath(__file__))
        tracks_dir = os.path.join(workspace_root, 'tracks')
        
        # Find all .yaml files recursively
        yaml_files = []
        for root, dirs, files in os.walk(tracks_dir):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    yaml_files.append(os.path.join(root, file))
        
        if not yaml_files:
            print("No YAML files found in tracks folder. Skipping test.")
            return

        # Create a temporary directory for outputs
        with tempfile.TemporaryDirectory() as temp_dir:
            for config_file in yaml_files:
                with self.subTest(config_file=config_file):
                    print(f"Testing config: {config_file}")
                    
                    # Define output path in temp dir
                    output_file = os.path.join(temp_dir, 'test_output.mid')
                    
                    # Construct command: python3 intonation_trainer.py <config> --output <temp_output>
                    cmd = [
                        'python3', 
                        'intonation_trainer.py', 
                        config_file, 
                        '--output', 
                        output_file
                    ]
                    
                    # Run the command
                    try:
                        result = subprocess.run(
                            cmd, 
                            cwd=workspace_root, 
                            capture_output=True, 
                            text=True, 
                            check=True
                        )
                        # If check=True, it raises CalledProcessError on non-zero exit code
                        
                        # Additionally check if the output file was created
                        # Note: intonation_trainer appends .mid if not present, or replaces extension?
                        # Let's check if any file starting with test_output exists or if the specific file exists.
                        # The script says: session_midi_path = base + '.mid'
                        # So if we pass '.../test_output.mid', base is '.../test_output', so it writes '.../test_output.mid'
                        
                        self.assertTrue(os.path.exists(output_file), f"MIDI file was not created for {config_file}")
                        
                    except subprocess.CalledProcessError as e:
                        self.fail(f"Failed to process {config_file}.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")

if __name__ == '__main__':
    unittest.main()
