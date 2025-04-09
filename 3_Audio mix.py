from pathlib import Path
import subprocess
import os
import sys
import argparse
import shutil
import unicodedata
import re

# Parse command line arguments
parser = argparse.ArgumentParser(description="Mix audio with video")
parser.add_argument("--volume-settings", help="Path to volume settings file")
args = parser.parse_args()

# Get volume settings from file or use defaults
original_volume = 0.6
voiceover_volume = 1.5

if args.volume_settings and os.path.exists(args.volume_settings):
    try:
        with open(args.volume_settings, "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                original_volume = float(lines[0].strip())
                voiceover_volume = float(lines[1].strip())
                print(f"Loaded volume settings from file: original={original_volume}, voiceover={voiceover_volume}")
    except Exception as e:
        print(f"Error reading volume settings file: {e}")
        print("Using default values instead")
else:
    # Fallback to environment variables if file not provided
    try:
        original_volume = float(os.environ.get("ORIGINAL_VOLUME", "0.5"))
        voiceover_volume = float(os.environ.get("VOICEOVER_VOLUME", "1.5"))
        print(f"Using volume settings from environment: original={original_volume}, voiceover={voiceover_volume}")
    except ValueError as e:
        print(f"Error parsing volume values: {e}")
        print("Using default values instead")

# Define the paths to the directories using the new structure
base_dir = Path('/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025')
audio_dir = base_dir / 'audio'
video_dir = base_dir / 'video'
export_dir = base_dir / 'export'

# Ensure that all directories exist
for directory in [audio_dir, video_dir, export_dir]:
    directory.mkdir(exist_ok=True)

# Find the first video file in the video directory (supporting both .mp4 and .mov)
video_files = list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.mov'))
if not video_files:
    print("No video files (mp4 or mov) found in the video directory.")
    sys.exit(1)

# Using the first found video file
video_file = video_files[0]
print(f"Using video file: {video_file}")

def extract_language_code(filename):
    """Extract language code from filename for all voice types"""
    parts = filename.stem.split('_')
    
    # Check if the filename starts with any of the supported voice types
    supported_voices = ['TomCruise', 'DojaCat', 'KIM', 'Chris']
    if len(parts) >= 2 and parts[0] in supported_voices:
        # The language code is always the second part
        return parts[1]
    
    return 'unknown'

def sanitize_filename(filename):
    """Create a safe version of the filename"""
    name = os.path.basename(filename)
    name = name.replace(' ', '_')
    name = name.replace("'", "")
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode()
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    return name

def validate_audio_file(file_path):
    """Validate if the audio file is properly formatted"""
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return False, "File is empty or doesn't exist"

        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"FFprobe error: {result.stderr}"
        
        codec = result.stdout.strip()
        if not codec:
            return False, "No audio stream found"
            
        return True, f"Valid audio file with codec: {codec}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def process_audio_file(audio_file, video_file, export_dir, original_volume, voiceover_volume):
    """Process a single audio file with error handling"""
    temp_audio = None
    try:
        # Create a temporary copy of the audio file with a safe name
        temp_dir = Path('/tmp/audio_processing')
        temp_dir.mkdir(exist_ok=True)
        
        print(f"\nProcessing file: {audio_file}")
        print(f"Original file size: {os.path.getsize(audio_file)} bytes")
        print(f"Video file size: {os.path.getsize(video_file)} bytes")
        
        safe_name = sanitize_filename(audio_file.name)
        temp_audio = temp_dir / safe_name
        shutil.copy2(audio_file, temp_audio)
        
        # Validate the audio file before processing
        is_valid, message = validate_audio_file(temp_audio)
        print(f"Validation result: {message}")
        
        if not is_valid:
            print(f"Invalid audio file {audio_file.name}: {message}")
            return False
        
        # Extract language code from original filename
        language_code = extract_language_code(audio_file)
        if language_code == 'unknown':
            print(f"Skipping file with unknown format: {audio_file.name}")
            return False
            
        # Create output filename using video name and language code
        output_file_path = export_dir / f"{video_file.stem}_{language_code}.mp4"
        
        print(f"Processing: {audio_file.name} -> {output_file_path}")
        print(f"Using volume settings: original={original_volume}, voiceover={voiceover_volume}")

        # First, check if we can read the video's audio stream
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_file)
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error probing video file: {result.stderr}")
            return False
            
        print(f"Video audio codec: {result.stdout.strip()}")

        # Simplified FFmpeg command for mixing audio
        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", str(video_file),
            "-i", str(temp_audio),
            "-filter_complex",
            f"[0:a]volume={original_volume}[a1];[1:a]volume={voiceover_volume}[a2];[a1][a2]amix=inputs=2:duration=first",
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            str(output_file_path)
        ]

        print("Executing FFmpeg command:")
        print(" ".join(str(x) for x in ffmpeg_command))

        # Run FFmpeg with more verbose output
        result = subprocess.run(ffmpeg_command, capture_output=True, text=True)
        
        # Always print the output for debugging
        if result.stdout:
            print(f"FFmpeg stdout: {result.stdout}")
        if result.stderr:
            print(f"FFmpeg stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"Error processing {audio_file.name}:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            if output_file_path.exists():
                output_file_path.unlink()
            return False
        
        # Verify the output file
        if not output_file_path.exists():
            print(f"Output file was not created: {output_file_path}")
            return False
            
        output_size = output_file_path.stat().st_size
        if output_size < 1000000:  # Less than 1MB
            print(f"Output file is too small ({output_size} bytes)")
            output_file_path.unlink()
            return False
            
        # Verify the output file has both video and audio streams
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output_file_path)
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0 or 'video' not in result.stdout or 'audio' not in result.stdout:
            print(f"Output file is missing video or audio streams: {result.stdout}")
            output_file_path.unlink()
            return False
            
        print(f"Successfully generated: {output_file_path} ({output_size} bytes)")
        return True
            
    except Exception as e:
        print(f"Error processing {audio_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temporary files
        if temp_audio and temp_audio.exists():
            try:
                temp_audio.unlink()
                print(f"Cleaned up temporary file: {temp_audio}")
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")

# Debug info
print(f"Looking for audio files in: {audio_dir}")
audio_files = list(audio_dir.glob('*.mp3'))
print(f"Found {len(audio_files)} MP3 files")
for file in audio_files:
    print(f"File: {file.name}, Size: {file.stat().st_size} bytes")

# Main processing loop
print("Starting to process audio files...")
processed_count = 0
success_count = 0
audio_files = list(audio_dir.glob('*.mp3'))
total_files = len(audio_files)

print(f"Found {total_files} MP3 files to process")
for audio_file in audio_files:
    try:
        print(f"\nProcessing file {processed_count + 1} of {total_files}")
        if process_audio_file(audio_file, video_file, export_dir, original_volume, voiceover_volume):
            success_count += 1
        processed_count += 1
        print(f"Progress: {processed_count}/{total_files} files processed, {success_count} successful")
    except Exception as e:
        print(f"Error in main loop processing {audio_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()

# Clean up temporary directory
temp_dir = Path('/tmp/audio_processing')
if temp_dir.exists():
    try:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up temporary directory: {e}")

print(f"Batch processing complete. Successfully processed {success_count} out of {total_files} files.")