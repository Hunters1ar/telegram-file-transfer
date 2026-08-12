"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { useI18n } from "@/lib/i18n"
import type { Language } from "@/lib/i18n"

export function SettingsView() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useI18n()

  return (
    <div className="dashboard-scroll">
      <div className="view-head">
        <h2>{t("Settings")}</h2>
        <p>{t("Manage your account and app preferences.")}</p>
      </div>

      <section className="settings-section">
        <div className="settings-card">
          <div className="settings-row">
            <div>
              <h3>{t("Theme")}</h3>
              <p>{t("Luxury Crimson — dark or light")}</p>
            </div>
            <div className="theme-toggle" role="group" aria-label="Theme">
              <button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}>
                <Sun /> {t("Light")}
              </button>
              <button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}>
                <Moon /> {t("Dark")}
              </button>
            </div>
          </div>

          <div className="settings-row">
            <div>
              <h3>{t("Language")}</h3>
              <p>{t("Interface language")}</p>
            </div>
            <select className="hs-select" value={language} onChange={(e) => setLanguage(e.target.value as Language)} aria-label="Language">
              <option value="en">English</option>
              <option value="ru">Русский</option>
              <option value="uz">O&apos;zbek</option>
              <option value="ko">한국어</option>
              <option value="zh">中文</option>
            </select>
          </div>

          <div className="settings-row">
            <div>
              <h3>{t("File Limit")}</h3>
              <p>{t("Maximum upload size")}</p>
            </div>
            <p>100 GB</p>
          </div>
        </div>
      </section>
    </div>
  )
}
