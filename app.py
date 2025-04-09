import streamlit as st
import os
from pathlib import Path
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state.authenticated = True
            st.session_state.password = ""  # Clear the password
        else:
            st.session_state.authenticated = False
            st.session_state.password = ""  # Clear the password

    # First run or password not correct
    if not st.session_state.authenticated:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    return True

def main():
    st.title("Translation App")
    
    # Check authentication
    if not check_password():
        st.stop()
    
    # Main app content
    st.write("Welcome to the Translation App!")
    
    # Text input
    text_to_translate = st.text_area("Enter text to translate:", height=150)
    
    # Language selection
    languages = {
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
    
    selected_languages = st.multiselect(
        "Select languages to translate to:",
        options=list(languages.keys()),
        default=["JP", "CN", "DE"]
    )
    
    if st.button("Translate"):
        if not text_to_translate:
            st.error("Please enter some text to translate")
            return
            
        if not selected_languages:
            st.error("Please select at least one language")
            return
            
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process translations
        translations = {}
        for i, lang_code in enumerate(selected_languages):
            lang_name = languages[lang_code]
            status_text.text(f"Translating to {lang_name}...")
            
            try:
                # Get enhanced system message
                system_message = f"""You are a professional translator for {lang_name}. Follow these guidelines:
1. Translate the text naturally as a native {lang_name} speaker would express it
2. Adapt idioms and expressions to local equivalents in {lang_name}
3. Use appropriate formality levels for the target culture
4. Keep branded terms and proper nouns in English
5. Return the translation as a single continuous paragraph with no line breaks
6. Provide ONLY the translation, no explanations or notes"""
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": text_to_translate}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                translation = response.choices[0].message.content.strip()
                translations[lang_code] = translation
                
            except Exception as e:
                st.error(f"Error translating to {lang_name}: {str(e)}")
                translations[lang_code] = f"Error: {str(e)}"
            
            # Update progress
            progress_bar.progress((i + 1) / len(selected_languages))
        
        # Display results
        st.subheader("Translations")
        for lang_code, translation in translations.items():
            with st.expander(f"{languages[lang_code]} ({lang_code})"):
                st.write(translation)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

if __name__ == "__main__":
    main() 