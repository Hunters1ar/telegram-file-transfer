"use client"

import { Bell, Moon, Search, Sun } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { useStore } from "@/lib/hunterstar-store"
import { useI18n, Language } from "@/lib/i18n"

export function Topbar() {
  const { search, setSearch, pushToast } = useStore()
  const { theme, toggleTheme } = useTheme()
  const { t, language, setLanguage } = useI18n()

  const handleLanguageToggle = () => {
    const langs: Language[] = ["en", "ru", "uz", "ko", "zh"]
    const nextIndex = (langs.indexOf(language) + 1) % langs.length
    setLanguage(langs[nextIndex])
  }

  return (
    <header className="topbar">
      <div className="search-bar">
        <Search size={16} aria-hidden="true" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("Search files...")}
          aria-label={t("Search files")}
        />
      </div>
      <div className="topbar-actions">
        <button
          className="topbar-btn"
          title={t("Change Language")}
          aria-label={t("Change Language")}
          onClick={handleLanguageToggle}
        >
          <img src="/icons/translatebutton.webp" className="svg-icon" alt="translate-icon" />
        </button>
        <button
          className="topbar-btn"
          title={theme === "dark" ? t("Switch to light mode") : t("Switch to dark mode")}
          aria-label={t("Toggle theme")}
          onClick={toggleTheme}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button
          className="topbar-btn"
          title={t("Notifications")}
          aria-label={t("Notifications")}
          onClick={() => pushToast(t("No new notifications"))}
        >
          <img src="/icons/notification-icon.webp" className="svg-icon" alt="notification-icon"  />
        </button>
      </div>
    </header>
  )
}
