import os
import json
from pathlib import Path
from openai import OpenAI
import shutil
import re

# Maximum lengths dictionary for CJK languages - Move this to the top
max_lengths = {'CN': 16, 'JP': 16, 'KR': 16, 'HK': 16}

def parse_timecode(timecode):
    """Convert timecode string to milliseconds."""
    hours, minutes, seconds, milliseconds = map(int, re.split('[:|,]', timecode))
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds

def format_timecode(milliseconds):
    """Convert milliseconds to a timecode string."""
    hours = milliseconds // 3600000
    minutes = (milliseconds % 3600000) // 60000
    seconds = (milliseconds % 60000) // 1000
    milliseconds = milliseconds % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def split_lines(text, max_length, is_cjk):
    """Split text into lines respecting word boundaries and preserving specific terms and English words."""
    lines = []
    current_line = ""
    
    if is_cjk:  # For CJK languages, split per character but preserve specific terms and English words
        preserved_terms = ["Photoroom", "AI"]  # Add any other terms you want to preserve
        i = 0
        while i < len(text):
            # Check for preserved terms
            for term in preserved_terms:
                if text[i:].startswith(term):
                    if len(current_line) + len(term) <= max_length:
                        current_line += term
                        i += len(term)
                    else:
                        lines.append(current_line)
                        current_line = term
                        i += len(term)
                    break
            else:
                # Check for English words (assuming they're space-separated)
                if text[i].isascii() and text[i].isalnum():
                    word_end = text.find(' ', i)
                    if word_end == -1:
                        word_end = len(text)
                    word = text[i:word_end]
                    if len(current_line) + len(word) <= max_length:
                        current_line += word
                        i = word_end
                    else:
                        lines.append(current_line)
                        current_line = word
                        i = word_end
                else:
                    # Handle CJK characters
                    if len(current_line) + 1 <= max_length:
                        current_line += text[i]
                    else:
                        lines.append(current_line)
                        current_line = text[i]
                    i += 1
            
            # Move to next character if it's a space
            if i < len(text) and text[i] == ' ':
                i += 1

        if current_line:
            lines.append(current_line)
    else:  # For non-CJK languages, respect word boundaries
        words = text.split()
        for word in words:
            if len(current_line) + (len(word) + 1) <= max_length:  # +1 for space
                current_line += (' ' + word if current_line else word)
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    return lines

def process_srt(file_path, max_lengths):
    """Process an SRT file with language-specific line lengths respecting word boundaries for non-CJK languages."""
    language = 'EN'  # Default to English
    is_cjk = False
    if '_JP' in file_path:
        language = 'JP'
        is_cjk = True
    elif '_CN' in file_path:
        language = 'CN'
        is_cjk = True
    elif '_KR' in file_path:
        language = 'KR'
        is_cjk = True
    elif '_HK' in file_path:
        language = 'HK'
        is_cjk = True

    max_length = max_lengths.get(language, 24)  # Get specific max length or default to 24

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    entries = content.split('\n\n')
    new_entries = []
    for entry in entries:
        if entry.strip() == '':
            continue
        parts = entry.split('\n')
        index = parts[0]
        times = parts[1]
        text = ' '.join(parts[2:])
        
        # Only remove punctuation at the end of the line
        text = re.sub(r'[.,。!?！？]$', '', text.strip())
        
        lines = split_lines(text, max_length, is_cjk)
        num_lines = len(lines)
        start_time, end_time = times.split(' --> ')
        start_ms = parse_timecode(start_time)
        end_ms = parse_timecode(end_time)
        increment = (end_ms - start_ms) // num_lines

        new_entry = []
        for i, line in enumerate(lines):
            # Only remove punctuation at the end of the line
            line = re.sub(r'[.,。!?！？]$', '', line.strip())
            new_start_time = format_timecode(start_ms + i * increment)
            new_end_time = format_timecode(start_ms + (i + 1) * increment)
            new_entry.append(f"{len(new_entries) + 1}\n{new_start_time} --> {new_end_time}\n{line}")
            new_entries.append('\n'.join(new_entry))
            new_entry = []

    # Save modified content to a new file with '_split' suffix
    new_file_path = file_path.replace('.srt', '_split.srt')
    with open(new_file_path, 'w', encoding='utf-8') as new_file:
        new_file.write('\n\n'.join(new_entries))
    print(f"Processed and saved: {new_file_path}")
    
    # Remove the original SRT file
    try:
        os.remove(file_path)
        print(f"Removed original file: {file_path}")
    except Exception as e:
        print(f"Error removing original file {file_path}: {e}")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to format time for SRT files
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"

# Custom JSON encoder subclass to handle non-serializable objects
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)  # Last resort

# Usage in the save_transcript_and_create_srt function
def save_transcript_and_create_srt(transcript, base_path):
    text_file_path = base_path.with_suffix('.txt')
    # Save SRT directly to SRT folder
    srt_folder = Path("/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT")
    srt_file_path = srt_folder / base_path.with_suffix('.srt').name

    # Save the transcript as JSON using the custom encoder
    with open(text_file_path, 'w') as text_file:
        json.dump(transcript, text_file, cls=JSONEncoder)

    # Generate and save the SRT file
    srt_content = ""
    for i, segment in enumerate(transcript['segments']):
        start_time = format_time(segment['start'])
        end_time = format_time(segment['end'])
        text = segment['text'].strip()
        # Split long sentences at punctuation marks
        sentences = re.split(r'([.!?。！？])', text)
        # Remove empty strings and combine punctuation with sentences
        sentences = [''.join(i) for i in zip(sentences[::2], sentences[1::2] + [''])]
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) > 1:
            # Calculate time per sentence
            duration = segment['end'] - segment['start']
            time_per_sentence = duration / len(sentences)
            
            for j, sentence in enumerate(sentences):
                sent_start = segment['start'] + (j * time_per_sentence)
                sent_end = sent_start + time_per_sentence
                # Only remove punctuation at the end of the line
                sentence = re.sub(r'[.,。!?！？]$', '', sentence.strip())
                srt_content += f"{i+j+1}\n{format_time(sent_start)} --> {format_time(sent_end)}\n{sentence}\n\n"
        else:
            # Only remove punctuation at the end of the line
            text = re.sub(r'[.,。!?！？]$', '', text.strip())
            srt_content += f"{i+1}\n{start_time} --> {end_time}\n{text}\n\n"
    
    # Create SRT folder if it doesn't exist and save the file
    srt_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_file_path, 'w', encoding='utf-8') as srt_file:
        srt_file.write(srt_content)

    return srt_file_path

background_terms = (
    "AI Backgrounds, "
    "Photoroom, "  # Added a space after Photoroom
    "خلفيات الذكاء الاصطناعي, "  # Arabic
    "AI 背景, "                 # Chinese Simplified
    "AI 背景, "                 # Chinese Traditional (unchanged)
    "AI-baggrunde, "           # Danish
    "AI-Achtergronden, "       # Dutch
    "AI-taustat, "             # Finnish
    "Fonds IA, "               # French
    "AI Backgrounds, "         # German
    "Φόντα ΤΝ, "               # Greek
    "רקעים ב-AI, "             # Hebrew
    "AI hátterek, "            # Hungarian
    "Latar Belakang AI, "      # Indonesian
    "Sfondi IA, "              # Italian
    "AI 背景生成, "             # Japanese
    "AI 배경, "                 # Korean
    "Latar Belakang AI, "      # Malay
    "KI-bakgrunner, "          # Norwegian
    "AI Backgrounds, "         # Persian
    "AI Backgrounds, "         # Polish
    "Fundos IA, "              # Portuguese (Brazil)
    "Fundos IA, "              # Portuguese (Portugal)
    "Fundaluri IA, "           # Romanian
    "ИИ-фоны, "                # Russian
    "Fondos IA, "              # Spanish
    "AI-bakgrunder, "          # Swedish
    "พื้นหลัง AI, "            # Thai
    "YZ Arka Planlar, "        # Turkish
    "ШІ-фони, "                # Ukrainian
    "Hình nền AI"              # Vietnamese
    "AI 背景 (繁體中文)"         # Explicitly mentioning Traditional Chinese
)


def transcribe_with_prompt(audio_file_path):
    specific_terms = f"{background_terms}"  # Merge with previously defined AI Backgrounds terms
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="verbose_json",
            prompt=specific_terms
        )
    # Ensure the transcription object is in a serializable format
    if hasattr(transcription, 'model_dump'):
        return transcription.model_dump()
    else:
        return transcription  # Handle non-serializable case as fallback

# Directory containing your audio files
audio_files_directory = "/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/audio"

# Iterate through audio files in the directory
for audio_file_path in Path(audio_files_directory).glob('*.mp3'):
    # Transcribe with Whisper considering specific terms
    transcript = transcribe_with_prompt(audio_file_path)

    # Save transcript as JSON and create SRT file
    srt_file_path = save_transcript_and_create_srt(transcript, audio_file_path)

    # Delete the generated .txt file
    text_file_path = audio_file_path.with_suffix('.txt')
    text_file_path.unlink(missing_ok=True)

    print(f"Transcript and SRT saved successfully: {srt_file_path}")

    # Process the SRT file immediately after creation
    process_srt(str(srt_file_path), max_lengths)

# Call the processing function on the SRT files generated by the first script
srt_files_directory = "/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT"

# Process all SRT files in the directory
for filename in os.listdir(srt_files_directory):
    # Only process original SRT files (not ones that already end with _split.srt)
    if filename.endswith(".srt") and not filename.endswith("_split.srt"):
        file_path = os.path.join(srt_files_directory, filename)
        process_srt(file_path, max_lengths)