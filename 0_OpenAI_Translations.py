import argparse
import os
import sys
from openai import OpenAI
from pathlib import Path
import time
import re
import asyncio
import aiofiles
from openai import AsyncOpenAI
from dotenv import load_dotenv
import requests
import aiohttp

# Load environment variables from .env file
load_dotenv()

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def get_model_selection():
    """Get user's model selection"""
    while True:
        print("\nSelect translation model:")
        print("1. OpenAI GPT-4o")
        print("2. DeepSeek")
        try:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice in ["1", "2"]:
                return choice
            print("Please enter either 1 or 2")
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again")

def get_first_sentence(text):
    """Extract the first sentence from text"""
    # Split by common sentence endings
    sentences = re.split(r'[.!?]+', text)
    # Get the first non-empty sentence and clean it
    first_sentence = next((s.strip() for s in sentences if s.strip()), "translation")
    # Replace spaces with underscores and remove special characters
    return re.sub(r'[^a-zA-Z0-9\s]', '', first_sentence).replace(' ', '_')[:50]

def get_text_from_terminal():
    """Get text input directly from terminal"""
    print("\nEnter or paste your text below (Press Enter twice to finish):")
    print("-" * 50)
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "" and lines:  # Empty line and we have some content
                break
            lines.append(line)
            
        text = "\n".join(lines).strip()
        if not text:
            print("No text entered. Please run the script again.")
            sys.exit(1)
        # Clean up the input if it contains existing translations
        if "[EN]" in text:
            text = text.split("[EN]")[1].split("\n\n")[0].strip().strip('"')
        return text
    except Exception as e:
        print(f"\nError reading input: {str(e)}")
        sys.exit(1)

class TranslationError(Exception):
    """Custom exception for translation errors"""
    pass

def get_enhanced_system_message(target_language):
    """Get enhanced system message for more localized translations"""
    base_message = """You are a professional translator for {target_language}. Follow these guidelines:
1. Translate the text naturally as a native {target_language} speaker would express it
2. Adapt idioms and expressions to local equivalents in {target_language}
3. Use appropriate formality levels for the target culture
4. Keep branded terms and proper nouns in English
5. Return the translation as a single continuous paragraph with no line breaks
6. Provide ONLY the translation, no explanations or notes

Important: Return the translation as one continuous paragraph with sentences separated by spaces. Do not include line breaks or multiple paragraphs."""
    
    # Add language-specific instructions for certain languages
    language_specific = {
        "Japanese": " Use appropriate honorifics (敬語) and particles.",
        "Korean": " Use appropriate honorific levels (존댓말/반말).",
        "Arabic": " Use Modern Standard Arabic with appropriate diacritical marks."
    }
    
    message = base_message.format(target_language=target_language)
    if target_language in language_specific:
        message += language_specific[target_language]
    
    return message

def clean_translation(translation):
    """Clean up translation response to remove explanations"""
    # Get first non-empty line that's not a heading
    lines = [line.strip() for line in translation.split('\n')]
    lines = [line for line in lines if line and not line.startswith('===')]
    
    # Return first meaningful line
    for line in lines:
        if line and not line.startswith('[') and not line.startswith('(') and not line.startswith('Cultural'):
            return line.strip('"').strip()
    
    return translation.strip()

def translate_text(text, target_language, api_key=None, model="gpt-4o", max_retries=3, retry_delay=2):
    """Translate text to target language using OpenAI API with retry mechanism"""
    client = OpenAI(api_key=api_key)
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*80}")
            print(f"Translating to {target_language}... (Attempt {attempt + 1}/{max_retries})")
            print(f"{'='*80}")
            start_time = time.time()
            
            # Use enhanced system message
            system_message = get_enhanced_system_message(target_language)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            translation = response.choices[0].message.content.strip()
            
            # Validate translation is not empty
            if not translation.strip():
                raise TranslationError("Received empty translation")
                
            # Success - print results and return
            elapsed_time = time.time() - start_time
            print_translation_results(text, translation, target_language, elapsed_time)
            return translation
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*50}")
            print(f"❌ Error on attempt {attempt + 1}/{max_retries}: {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                print(f"{'='*50}\n")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts")
                print(f"{'='*50}\n")
                return None

def print_translation_results(original_text, translation, target_language, elapsed_time):
    """Helper function to print translation results"""
    print(f"\nOriginal text:")
    print("-" * 50)
    print(original_text)
    print("-" * 50)
    print(f"\n{target_language} translation:")
    print("-" * 50)
    print(translation)
    print("-" * 50)
    print(f"\nTranslation completed in {elapsed_time:.2f} seconds")
    print(f"{'='*80}\n")

async def translate_text_async(text, target_language, api_key=None, model="gpt-4o", max_retries=3, retry_delay=2):
    """Async version of translate_text"""
    client = AsyncOpenAI(api_key=api_key)
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*80}")
            print(f"Starting translation to {target_language}... (Attempt {attempt + 1}/{max_retries})")
            print(f"{'='*80}")
            start_time = time.time()
            
            # Use enhanced system message
            system_message = get_enhanced_system_message(target_language)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            translation = response.choices[0].message.content.strip()
            translation = clean_translation(translation)
            
            if not translation.strip():
                raise TranslationError("Received empty translation")
                
            elapsed_time = time.time() - start_time
            print_translation_results(text, translation, target_language, elapsed_time)
            return target_language, translation
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*50}")
            print(f"❌ Error translating to {target_language} (Attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Retrying {target_language} in {wait_time} seconds...")
                print(f"{'='*50}\n")
                await asyncio.sleep(wait_time)
            else:
                print(f"Failed {target_language} after {max_retries} attempts")
                print(f"{'='*50}\n")
                return target_language, None

async def save_translation_async(output_file, consolidated_file_path, general_consolidated_path, lang_code, translation, filename_prefix, verbose=False):
    """Async function to save translation to files"""
    try:
        # Format translation as a single paragraph
        formatted_translation = translation.replace('\n', '  ').replace('  ', ' ').strip()
        
        # Save to filename-specific consolidated file
        async with aiofiles.open(consolidated_file_path, "a", encoding="utf-8") as consolidated_file:
            escaped_translation = formatted_translation.replace('"', '\\"')
            await consolidated_file.write(f'[{lang_code}] "{escaped_translation}"\n\n')
        
        # Save to general all_translations.txt file
        async with aiofiles.open(general_consolidated_path, "a", encoding="utf-8") as general_file:
            escaped_translation = formatted_translation.replace('"', '\\"')
            await general_file.write(f'[{lang_code}] "{escaped_translation}"\n\n')
            
        return True
    except Exception as e:
        print(f"Error saving translation for {lang_code}: {str(e)}")
        return False

async def process_translations(text, languages, all_languages, api_key, model, output_dir, filename_prefix, args, model_choice):
    """Process all translations concurrently"""
    tasks = []
    model_identifier = "openai" if model_choice == "1" else "deepseek"
    consolidated_file_path = output_dir / f"{filename_prefix}_{model_identifier}_all_translations.txt"
    general_consolidated_path = output_dir / "all_translations.txt"
    
    # Format original text as a single paragraph and ensure it's included
    formatted_text = text.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Overwrite all_translations.txt instead of appending
    async with aiofiles.open(consolidated_file_path, "w", encoding="utf-8") as file1, \
              aiofiles.open(general_consolidated_path, "w", encoding="utf-8") as file2:
        await file1.write(f'[EN] "{formatted_text}"\n\n')
        await file2.write(f'[EN] "{formatted_text}"\n\n')
    
    # Create tasks for each language
    for lang_code in languages:
        if lang_code == "EN":
            continue
            
        lang_name = all_languages.get(lang_code, lang_code)
        if model_choice == "1":
            tasks.append(translate_text_async(text, lang_name, api_key, model))
        else:
            tasks.append(translate_with_deepseek_async(text, lang_name))
    
    # Process translations with progress tracking
    print(f"\nProcessing {len(tasks)} translations...")
    results = []
    for i, task in enumerate(tasks):
        try:
            result = await task
            results.append(result)
            print(f"Completed {i+1}/{len(tasks)} translations")
        except Exception as e:
            print(f"Error processing translation: {str(e)}")
            results.append((None, None))
    
    successful_translations = 0
    for lang_name, translation in results:
        if translation:
            lang_code = next(code for code, name in all_languages.items() if name == lang_name)
            
            # Removed individual file creation, only save to consolidated files
            success = await save_translation_async(
                None,  # No individual output file
                consolidated_file_path,
                general_consolidated_path,
                lang_code,
                translation,
                filename_prefix,
                args.verbose
            )
            
            if success:
                successful_translations += 1
    
    return successful_translations

def translate_with_deepseek(text, target_language, max_retries=3, retry_delay=2):
    """Translate text using DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_message = get_enhanced_system_message(target_language)
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*80}")
            print(f"Translating to {target_language} using DeepSeek... (Attempt {attempt + 1}/{max_retries})")
            print(f"{'='*80}")
            start_time = time.time()
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip()
            
            if not translation.strip():
                raise TranslationError("Received empty translation")
                
            elapsed_time = time.time() - start_time
            print_translation_results(text, translation, target_language, elapsed_time)
            return translation
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*50}")
            print(f"❌ Error on attempt {attempt + 1}/{max_retries}: {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Retrying in {wait_time} seconds...")
                print(f"{'='*50}\n")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts")
                print(f"{'='*50}\n")
                return None

async def translate_with_deepseek_async(text, target_language, max_retries=3, retry_delay=2):
    """Async version of translate_with_deepseek"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_message = get_enhanced_system_message(target_language)
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*80}")
            print(f"Starting translation to {target_language} using DeepSeek... (Attempt {attempt + 1}/{max_retries})")
            print(f"{'='*80}")
            start_time = time.time()
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            # Add timeout to the request
            timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"API Error: Status {response.status}, Response: {error_text}")
                            raise TranslationError(f"API returned status {response.status}")
                        
                        result = await response.json()
                        
                except asyncio.TimeoutError:
                    print(f"Request timed out after 60 seconds")
                    raise TranslationError("Request timed out")
                except aiohttp.ClientError as e:
                    print(f"Network error: {str(e)}")
                    raise TranslationError(f"Network error: {str(e)}")
                    
            translation = result['choices'][0]['message']['content'].strip()
            
            if not translation.strip():
                raise TranslationError("Received empty translation")
                
            elapsed_time = time.time() - start_time
            print_translation_results(text, translation, target_language, elapsed_time)
            return target_language, translation
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*50}")
            print(f"❌ Error translating to {target_language} (Attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Retrying {target_language} in {wait_time} seconds...")
                print(f"{'='*50}\n")
                await asyncio.sleep(wait_time)
            else:
                print(f"Failed {target_language} after {max_retries} attempts")
                print(f"{'='*50}\n")
                return target_language, None

async def validate_deepseek_api_key():
    """Validate the DeepSeek API key by making a simple request"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 5
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout for validation
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                if response.status == 401:
                    print("❌ Invalid DeepSeek API key. Please check your API key.")
                    return False
                elif response.status != 200:
                    print(f"❌ DeepSeek API error: Status {response.status}")
                    return False
                return True
    except Exception as e:
        print(f"❌ Error validating DeepSeek API key: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Translate text to multiple languages using OpenAI or DeepSeek API")
    parser.add_argument("--languages", default="all", help="Comma-separated list of language codes to translate to")
    parser.add_argument("--api_key", help="OpenAI API key (optional, can use environment variable)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use for translation")
    
    args = parser.parse_args()
    
    print("\nInitializing translation process...")
    
    # Get model selection
    model_choice = get_model_selection()
    
    # Set API key based on model choice
    if model_choice == "1":
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("\n❌ Error: No OpenAI API key found. Please:")
            print("1. Create a .env file with OPENAI_API_KEY=your-key")
            print("2. Set the OPENAI_API_KEY environment variable")
            print("3. Use the --api_key argument")
            sys.exit(1)
        print("✅ OpenAI API key found successfully")
    else:
        api_key = DEEPSEEK_API_KEY
        print("✅ Using DeepSeek API key")
        
        # Validate DeepSeek API key
        if not asyncio.run(validate_deepseek_api_key()):
            print("Please check your DeepSeek API key and try again.")
            sys.exit(1)
        print("✅ DeepSeek API key validated successfully")
    
    # Set default output directory in the same folder as the script
    script_dir = Path(__file__).parent
    output_dir = script_dir / "translations"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory created/verified at: {output_dir}")
    
    # Get input text from terminal
    print("\nPlease enter your text to translate...")
    text = get_text_from_terminal()
    
    if not text:
        print("❌ No text was entered. Please run the script again.")
        sys.exit(1)
    
    print(f"\n✅ Text received successfully ({len(text)} characters)")
    
    # Get the first sentence for filename prefix
    filename_prefix = get_first_sentence(text)
    print(f"✅ Generated filename prefix: {filename_prefix}")
    
    # Define consolidated file path
    consolidated_file_path = output_dir / f"{filename_prefix}_all_translations.txt"
    
    # Define language codes
    all_languages = {
        "JP": "Japanese",
        "CN": "Traditional Chinese",
        "DE": "German",
        "IN": "Hindi",
        "FR": "French",
        "KR": "Korean",
        "BR": "Brazilian Portuguese",
        "IT": "Italian",
        "ES": "Spanish",
        "ID": "Indonesian",
        "TR": "Turkish",
        "PH": "Filipino",
        "PL": "Polish",
        "SA": "Arabic",
        "MY": "Malay",
        "VN": "Vietnamese",
        "TH": "Thai"
    }
    
    # Determine which languages to translate to
    if args.languages.lower() == "all":
        languages = list(all_languages.keys())
        print(f"\n✅ Using all available languages ({len(languages)} languages)")
    else:
        languages = [lang.strip().upper() for lang in args.languages.split(",")]
        print(f"\n✅ Using specified languages: {', '.join(languages)}")
    
    print("\nStarting translation process...")
    print("=" * 80)
    
    try:
        successful_translations = asyncio.run(process_translations(
            text=text,
            languages=languages,
            all_languages=all_languages,
            api_key=api_key,
            model=args.model,
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            args=args,
            model_choice=model_choice
        ))
        
        skipped_languages = sum(1 for lang in languages if lang == "EN")
        
        print(f"\n{'='*80}")
        print(f"TRANSLATION PROCESS COMPLETED")
        print(f"{'='*80}")
        print(f"Successfully created {successful_translations} out of {len(languages) - skipped_languages} translation files")
        print(f"Files are saved in: {output_dir}")
        print(f"Consolidated translations file: {consolidated_file_path}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n❌ Error during translation process: {str(e)}")
        print("Please check your API key and internet connection.")
        sys.exit(1)

if __name__ == "__main__":
    main()
