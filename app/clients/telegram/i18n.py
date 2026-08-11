import json
from pathlib import Path

# Cache the translations in memory
_translations = {}

LOCALES_DIR = Path(__file__).parent.parent.parent.parent / "website" / "locales"

def load_translations(lang: str):
    if lang in _translations:
        return
        
    locale_file = LOCALES_DIR / f"{lang}.json"
    if locale_file.exists():
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        except Exception as e:
            print(f"Failed to load translation {lang}: {e}")
            _translations[lang] = {}
    else:
        _translations[lang] = {}

def t(text: str, lang: str = "en") -> str:
    """
    Translates a text to the specified language.
    If the language is English or the translation is not found, returns the original text.
    """
    if not lang or lang == "en":
        return text
        
    if lang not in _translations:
        load_translations(lang)
        
    lang_dict = _translations.get(lang, {})
    return lang_dict.get(text, text)

def get_all_translations(text: str) -> list[str]:
    """Returns a list of all translations for a given string to be used with F.text.in_()"""
    res = [text]
    for lang in ["ru", "uz", "ko", "zh"]:
        if lang not in _translations:
            load_translations(lang)
        lang_dict = _translations.get(lang, {})
        translated = lang_dict.get(text, text)
        if translated not in res:
            res.append(translated)
    return res

