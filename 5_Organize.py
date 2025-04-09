import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('organization.log'),
        logging.StreamHandler()
    ]
)

class ProjectOrganizer:
    def __init__(self):
        # Get the base directory (where this script is located)
        self.base_dir = Path(__file__).parent
        
        # Define the main directories
        self.dirs = {
            'source': {
                'video': self.base_dir / 'video',
                'audio': self.base_dir / 'audio',
                'translations': self.base_dir / 'translations',
                'srt': self.base_dir / 'SRT',
                'export': self.base_dir / 'export'
            },
            'output': {
                'main': self.base_dir / 'output',
                'archive': self.base_dir / 'output' / 'archive'
            }
        }
        
        # Create all necessary directories
        self._create_directories()

    def _create_directories(self):
        """Create all necessary directories if they don't exist."""
        for category in self.dirs.values():
            for dir_path in category.values():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logging.info(f"Created/verified directory: {dir_path}")
                except Exception as e:
                    logging.error(f"Error creating directory {dir_path}: {e}")
                    raise

    def _validate_file(self, file_path, expected_extensions):
        """Validate if a file exists and has the correct extension."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.suffix.lower() not in expected_extensions:
            raise ValueError(f"Invalid file extension for {file_path}")
        return True

    def organize_project(self, project_name):
        """Organize files for a specific project."""
        try:
            # Create project-specific directories (directly in output folder)
            project_dir = self.dirs['output']['main'] / project_name
            project_dir.mkdir(exist_ok=True)
            
            # Create subdirectories for different file types
            subdirs = {
                'video': project_dir / 'video',
                'audio': project_dir / 'audio',
                'subtitles': project_dir / 'subtitles',
                'translations': project_dir / 'translations'
            }
            
            # Create all subdirectories
            for dir_path in subdirs.values():
                dir_path.mkdir(exist_ok=True)

            # Process video files
            self._process_video_files(subdirs['video'])
            
            # Process audio files
            self._process_audio_files(subdirs['audio'])
            
            # Process subtitle files
            self._process_subtitle_files(subdirs['subtitles'])
            
            # Process translation files
            self._process_translation_files(subdirs['translations'])
            
            logging.info(f"Successfully organized project: {project_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error organizing project {project_name}: {e}")
            return False

    def _process_video_files(self, dest_dir):
        """Process and organize video files."""
        # Process files from video directory
        video_files = list(self.dirs['source']['video'].glob('*.mp4'))
        for video_file in video_files:
            try:
                self._validate_file(video_file, ['.mp4'])
                dest_path = dest_dir / video_file.name
                shutil.move(str(video_file), str(dest_path))
                logging.info(f"Moved video file to: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing video file {video_file}: {e}")

        # Process files from export directory
        export_files = list(self.dirs['source']['export'].glob('*.mp4'))
        for export_file in export_files:
            try:
                self._validate_file(export_file, ['.mp4'])
                dest_path = dest_dir / export_file.name
                shutil.move(str(export_file), str(dest_path))
                logging.info(f"Moved export file to: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing export file {export_file}: {e}")

    def _process_audio_files(self, dest_dir):
        """Process and organize audio files."""
        audio_files = list(self.dirs['source']['audio'].glob('*.mp3'))
        for audio_file in audio_files:
            try:
                self._validate_file(audio_file, ['.mp3'])
                dest_path = dest_dir / audio_file.name
                shutil.move(str(audio_file), str(dest_path))
                logging.info(f"Moved audio file to: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing audio file {audio_file}: {e}")

    def _process_subtitle_files(self, dest_dir):
        """Process and organize subtitle files."""
        srt_files = list(self.dirs['source']['srt'].glob('*.srt'))
        for srt_file in srt_files:
            try:
                self._validate_file(srt_file, ['.srt'])
                dest_path = dest_dir / srt_file.name
                shutil.move(str(srt_file), str(dest_path))
                logging.info(f"Moved subtitle file to: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing subtitle file {srt_file}: {e}")

    def _process_translation_files(self, dest_dir):
        """Process and organize translation files."""
        translation_files = list(self.dirs['source']['translations'].glob('*.txt'))
        for trans_file in translation_files:
            try:
                self._validate_file(trans_file, ['.txt'])
                dest_path = dest_dir / trans_file.name
                shutil.move(str(trans_file), str(dest_path))
                logging.info(f"Moved translation file to: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing translation file {trans_file}: {e}")

def main():
    try:
        # Get the video file name to use as project name
        video_dir = Path(__file__).parent / 'video'
        video_files = list(video_dir.glob('*.mp4'))
        
        if not video_files:
            logging.error("No video files found in the video directory.")
            return
        
        # Use the first video file name as project name
        project_name = video_files[0].stem
        
        # Initialize and run the organizer
        organizer = ProjectOrganizer()
        if organizer.organize_project(project_name):
            logging.info("Project organization completed successfully.")
            # Updated path to open the project directory
            os.system(f'open "{organizer.dirs["output"]["main"] / project_name}"')
        else:
            logging.error("Project organization failed.")
            
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
