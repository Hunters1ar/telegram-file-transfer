const I18N = {
  currentLanguage: 'en',
  translations: {},
  supportedLanguages: ['en', 'ru', 'uz', 'ko', 'zh'],

  async init(defaultLang = 'en') {
    // Try to get language from localStorage or Telegram WebApp
    let lang = localStorage.getItem('app_lang');
    if (!lang) {
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
            const tgLang = window.Telegram.WebApp.initDataUnsafe.user.language_code;
            if (this.supportedLanguages.includes(tgLang)) {
                lang = tgLang;
            }
        }
    }
    this.currentLanguage = lang || defaultLang;

    if (this.currentLanguage !== 'en') {
      await this.loadTranslations(this.currentLanguage);
    }
    
    this.translatePage();
  },

  async loadTranslations(lang) {
    if (lang === 'en') return; // English is the source
    if (this.translations[lang]) return; // Already loaded

    try {
      const res = await fetch(`locales/${lang}.json?v=${new Date().getTime()}`);
      if (res.ok) {
        this.translations[lang] = await res.json();
      } else {
        console.warn(`Could not load translations for ${lang}`);
      }
    } catch (e) {
      console.error(`Error loading translations for ${lang}:`, e);
    }
  },

  async setLanguage(lang) {
    if (!this.supportedLanguages.includes(lang)) return;
    this.currentLanguage = lang;
    localStorage.setItem('app_lang', lang);
    await this.loadTranslations(lang);
    this.translatePage();
    
    // Optional: trigger a custom event if other scripts need to re-render
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: lang }));
  },

  t(text) {
    if (this.currentLanguage === 'en' || !this.translations[this.currentLanguage]) {
      return text;
    }
    return this.translations[this.currentLanguage][text] || text;
  },

  translatePage() {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
      // Save the original English string on first pass
      if (!el.hasAttribute('data-i18n-key')) {
        let key = el.getAttribute('data-i18n');
        if (!key) {
            key = el.textContent.trim();
        }
        el.setAttribute('data-i18n-key', key);
      }

      const key = el.getAttribute('data-i18n-key');
      const translated = this.t(key);
      
      // We use textContent by default, but if it's an input/textarea we might need to set placeholder/value
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (el.hasAttribute('placeholder')) {
            el.setAttribute('placeholder', translated);
        } else {
            el.value = translated;
        }
      } else {
        el.textContent = translated;
      }
    });
  }
};

// Expose global t() function
window.t = (text) => I18N.t(text);

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  await I18N.init();
  
  // Bind language selector if it exists
  const langSelector = document.getElementById('lang-selector');
  if (langSelector) {
    langSelector.value = I18N.currentLanguage;
    langSelector.addEventListener('change', (e) => {
      I18N.setLanguage(e.target.value);
    });
  }
});
