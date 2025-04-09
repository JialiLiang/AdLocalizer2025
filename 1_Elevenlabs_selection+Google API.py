from elevenlabs.client import ElevenLabs
import os
import time
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/jiali/Documents/AdLocaliserV1/videosrt-404520-510427b83721.json"
import re
import logging
from google.cloud import texttospeech
import argparse
import sys
import requests
import unicodedata

# Initialize Google Text-to-Speech client
google_client = texttospeech.TextToSpeechClient()

# Set up ElevenLabs
API_KEY = "b34683726054d06b5cd8c70a74c0c18a"
eleven_labs_client = ElevenLabs(api_key=API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Language and their corresponding abbreviations
language_codes = {
    "English":"EN",
    "Japanese": "JP",
    "Chinese": "CN",
    "German": "DE",
    "Hindi": "IN",
    "French (France)": "FR",
    "Korean": "KR",
    "Portuguese (Brazil)": "BR",
    "Italian": "IT",
    "Spanish (Spain)": "ES",
    "Indonesian": "ID",
    "Dutch": "NL",
    "Turkish": "TR",
    "Filipino": "PH",
    "Polish": "PL",
    "Arabic": "SA",
    "Malay": "MY",
    "Vietnamese": "VN",
    "Thai": "TH",
    "Cantonese": "HK",
}

# Update the default paths
translations_file_path = '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/translations/all_translations.txt'
audio_output_directory = '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/audio'
directory_path = '/Users/jiali/Documents/AdLocaliserV1'

def extract_first_words(text, max_words=3, max_chars=20):
    """
    Extract the first few words from the text to create a clean filename.
    """
    # Remove any non-ASCII characters and convert to basic ASCII
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode()
    
    # Replace problematic characters
    text = text.replace("'", "").replace('"', "")
    
    # Split the text into words and remove empty strings
    words = [word for word in text.split() if word]
    
    # Take only the first few words
    first_words = words[:max_words]
    
    # Join them with underscores
    result = "_".join(first_words)
    
    # Remove any non-alphanumeric characters (except underscores)
    result = re.sub(r'[^a-zA-Z0-9_]', '', result)
    
    # Truncate if too long
    if len(result) > max_chars:
        result = result[:max_chars].rstrip('_')
    
    return result

def sanitize_filename(text):
    """Remove special characters from filename"""
    return re.sub(r'[^\w\s-]', '', text).replace(' ', '_')

def generate_elevenlabs_voice_direct(text, language_code, output_directory, voice_id, voice_name, english_identifier):
    """Generate voice using ElevenLabs API with direct HTTP request"""
    try:
        # Create a clean voice name without spaces
        clean_voice_name = voice_name.replace(" ", "")
        
        # Create a simplified filename
        safe_name = f"{clean_voice_name}_{language_code}_{english_identifier}"
        
        # Create the final output filename
        output_file = f"{output_directory}/{safe_name}.mp3"
        
        # Direct API call to ElevenLabs
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": API_KEY
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        logging.info(f"Sending request to ElevenLabs API for {language_code}")
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            logging.info(f"Generated and saved voice for {language_code} as {output_file}.")
            return output_file
        else:
            logging.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error generating voice for {language_code}: {str(e)}")
        return None

def generate_google_tts_voice(text, language_code, output_directory, english_identifier):
    """Generate voice using Google Text-to-Speech API"""
    try:
        # Create a safe filename based on the first few words of the text
        filename_base = extract_first_words(text, max_words=3, max_chars=20)
        
        # Initialize the TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        # Create a shorter output filename
        output_file = f"{output_directory}/GoogleTTS_{language_code}_{english_identifier}_{filename_base}.mp3"
        
        # Check if the filename is still too long
        if len(output_file) > 240:  # Safe limit for most filesystems
            # Use an even shorter approach - just use the language code
            output_file = f"{output_directory}/GoogleTTS_{language_code}_{english_identifier}_audio.mp3"
        
        # The response's audio_content is binary
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            
        logging.info(f"Generated and saved Google TTS voice for {language_code} as {output_file}.")
        return output_file
    except Exception as e:
        logging.error(f"Error generating Google TTS voice for {language_code}: {str(e)}")
        return None

def process_translations(input_file, output_directory):
    """Process translations from the input file and generate voices"""
    global voice_id, voice_name
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the translations using regex
        translations = {}
        pattern = r'\[(\w+)\]\s*"([^"]+)"'
        matches = re.findall(pattern, content)
        
        if not matches:
            logging.error("No translations found in the expected format: [XX] \"text\"")
            return False
            
        # Convert matches to dictionary
        for lang_code, text in matches:
            translations[lang_code] = text.strip()
            
        # Get the English text for the identifier
        english_text = translations.get("EN", "")
        if not english_text:
            logging.error("No English text found in translations")
            return False
            
        english_identifier = extract_first_words(english_text, max_words=2, max_chars=15)
        logging.info(f"Found {len(translations)} translations with identifier: {english_identifier}")
        
        # Generate voices for each translation
        for lang_code, text in translations.items():
            try:
                if lang_code in ["TH", "HK"]:
                    # Use Google TTS for Thai and Cantonese
                    google_lang_code = "th-TH" if lang_code == "TH" else "yue-HK"
                    output_file = generate_google_tts_voice(
                        text, 
                        google_lang_code, 
                        output_directory, 
                        english_identifier
                    )
                else:
                    # Use ElevenLabs for all other languages
                    output_file = generate_elevenlabs_voice_direct(
                        text, 
                        lang_code, 
                        output_directory, 
                        voice_id, 
                        voice_name, 
                        english_identifier
                    )
                
                if output_file:
                    logging.info(f"Successfully generated voice for {lang_code}")
                else:
                    logging.error(f"Failed to generate voice for {lang_code}")
                    
            except Exception as e:
                logging.error(f"Error processing {lang_code}: {str(e)}")
                continue
                
        logging.info("Translation process completed.")
        return True
        
    except Exception as e:
        logging.error(f"Error processing translations: {str(e)}")
        return False

def main():
    """Main function to parse arguments and run the voice generation process"""
    global voice_id, voice_name
    
    # Define available voices
    available_voices = {
        "1": {"name": "Tom Cruise", "id": "g60FwKJuhCJqbDCeuXjm"},
        "2": {"name": "Doja Cat", "id": "E1c1pVuZVvPrme6B9ryw"},
        "3": {"name": "KIM", "id": "mxPqESMukHdTPuSCpjw9"},
        "4": {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B"}
    }
    
    # Display voice options
    print("\nAvailable voices:")
    for key, voice in available_voices.items():
        print(f"{key}. {voice['name']}")
    
    # Get user selection
    while True:
        choice = input("\nPlease select a voice (1-4): ")
        if choice in available_voices:
            selected_voice = available_voices[choice]
            voice_id = selected_voice["id"]
            voice_name = selected_voice["name"]
            print(f"\nSelected voice: {voice_name}")
            break
        else:
            print("Invalid selection. Please choose a number between 1 and 4.")
    
    parser = argparse.ArgumentParser(description="Generate voice using ElevenLabs API")
    parser.add_argument("--input", 
                       default="/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/translations/all_translations.txt", 
                       help="Input file with translations")
    parser.add_argument("--output_dir", 
                       default="/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/audio", 
                       help="Output directory for voice files")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Process the translations
    logging.info("Starting the translation process...")
    
    # Try to use the provided input file, if it fails, use the default file
    input_file = args.input
    if not os.path.exists(input_file):
        fallback_file = "/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/translations/all_translations.txt"
        logging.warning(f"Input file {input_file} not found. Trying fallback file: {fallback_file}")
        if os.path.exists(fallback_file):
            input_file = fallback_file
        else:
            logging.error(f"Fallback file {fallback_file} also not found. Exiting.")
            sys.exit(1)
    
    success = process_translations(input_file, args.output_dir)
    
    if success:
        logging.info("Translation process completed.")
    else:
        logging.error("Translation process failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
