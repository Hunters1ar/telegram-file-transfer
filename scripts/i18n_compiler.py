import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import generation_types

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = Path(__file__).parent.parent
WEBSITE_DIR = BASE_DIR / 'website'
LOCALES_DIR = WEBSITE_DIR / 'locales'
LOCALES_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
LANGUAGES = ['ru', 'uz', 'ko', 'zh']

# Initialize API Keys list from .env
API_KEYS = []
for i in range(1, 10):
    key = os.getenv(f'GEMINI_AI_API{i}')
    if key:
        API_KEYS.append(key)

if not API_KEYS:
    # Try default GEMINI_API_KEY
    key = os.getenv('GEMINI_API_KEY')
    if key:
        API_KEYS.append(key)

if not API_KEYS:
    print("Error: No GEMINI_AI_API keys found in .env")
    exit(1)

current_api_key_index = 0

def get_current_model():
    genai.configure(api_key=API_KEYS[current_api_key_index])
    # Use gemini-2.5-flash as it's fast and good for translation
    return genai.GenerativeModel('gemini-2.5-flash')

def rotate_api_key():
    global current_api_key_index
    current_api_key_index += 1
    if current_api_key_index >= len(API_KEYS):
        print("Error: Exhausted all available API keys.")
        return False
    print(f"\n[!] Switching to API Key {current_api_key_index + 1} due to rate limits or errors...")
    return True

def extract_strings_from_html(file_path):
    strings = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        # Find all elements with data-i18n attribute
        for el in soup.find_all(attrs={"data-i18n": True}):
            key = el.get("data-i18n")
            if not key:
                key = el.get_text(strip=True)
            if key:
                strings.add(key)
    return strings

def extract_strings_from_js(file_path):
    strings = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find all t("...") or t('...') calls, allowing for extra parameters like t('...', lang)
        matches = re.findall(r't\(\s*[\'"]([^\'"]+)[\'"]\s*(?:,[^)]*)?\)', content)
        for match in matches:
            strings.add(match)
    return strings

def get_all_strings():
    all_strings = set()
    
    # 1. Scan website HTML and JS
    for root, _, files in os.walk(WEBSITE_DIR):
        for file in files:
            path = os.path.join(root, file)
            if path.endswith('.html'):
                all_strings.update(extract_strings_from_html(path))
            elif path.endswith('.js') and 'i18n.js' not in file:
                all_strings.update(extract_strings_from_js(path))
                
    # 2. Scan telegram bot Python files for t("...") calls
    TELEGRAM_DIR = BASE_DIR / 'app' / 'clients' / 'telegram'
    if TELEGRAM_DIR.exists():
        for root, _, files in os.walk(TELEGRAM_DIR):
            for file in files:
                path = os.path.join(root, file)
                if path.endswith('.py'):
                    all_strings.update(extract_strings_from_js(path)) # extract_strings_from_js regex works identically for Python

    return all_strings

def translate_strings(strings_to_translate, target_lang):
    if not strings_to_translate:
        return {}
        
    prompt = f"""
Translate the following English strings into {target_lang}.
Return ONLY a valid JSON object where keys are the original English strings and values are the {target_lang} translations.
Ensure the JSON is perfectly formatted. Do not include markdown formatting like ```json.

Strings to translate:
{json.dumps(list(strings_to_translate), ensure_ascii=False, indent=2)}
"""

    while True:
        model = get_current_model()
        try:
            print(f"Translating {len(strings_to_translate)} strings to {target_lang} using API key {current_api_key_index + 1}...")
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
            
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str or "overloaded" in err_str:
                if rotate_api_key():
                    continue
                else:
                    raise Exception("All API keys exhausted.")
            else:
                print(f"Failed to translate to {target_lang}: {e}")
                # If it's a parsing error or something else, we might just return empty and try again later
                return {}

def main():
    print("Starting i18n compilation...")
    strings = get_all_strings()
    print(f"Extracted {len(strings)} unique translatable strings from source.")
    
    # Save base english strings
    en_file = LOCALES_DIR / 'en.json'
    en_data = {s: s for s in strings}
    with open(en_file, 'w', encoding='utf-8') as f:
        json.dump(en_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    for lang in LANGUAGES:
        lang_file = LOCALES_DIR / f"{lang}.json"
        
        # Load existing
        existing_data = {}
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}
        
        # Find missing
        missing_strings = [s for s in strings if s not in existing_data]
        
        if missing_strings:
            print(f"\n[{lang}] Found {len(missing_strings)} missing translations.")
            new_translations = translate_strings(missing_strings, lang)
            
            if new_translations:
                existing_data.update(new_translations)
                with open(lang_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2, sort_keys=True)
                print(f"Saved updated translations for {lang}")
        else:
            print(f"{lang} is up to date.")
            
    print("\nCompilation complete!")

if __name__ == '__main__':
    main()
