"use client"

import { BarChart3, FolderClosed, LayoutDashboard, Settings, Shield, Star } from "lucide-react"
import { formatBytes, useStore, type ViewKey } from "@/lib/hunterstar-store"
import { useI18n } from "@/lib/i18n"

const NAV: { key: ViewKey; label: string; iconSrc: string }[] = [
  { key: "dashboard", label: "Dashboard", iconSrc: "/icons/dashboard-icon.webp" },
  { key: "folders", label: "Folders", iconSrc: "/icons/folders-icon.webp" },
  { key: "favorites", label: "Favorites", iconSrc: "/icons/favourite-icon.webp" },
  { key: "analytics", label: "Analytics", iconSrc: "/icons/stats-icon.webp" },
  { key: "settings", label: "Settings", iconSrc: "/icons/settings-icon.webp" },
]

export function Sidebar() {
  const { view, setView, usedBytes, storageLimit } = useStore()
  const { t } = useI18n()
  const pct = Math.min((usedBytes / storageLimit) * 100, 100)

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" stroke="#B00020" strokeWidth="1.5"/>
        </svg>
        <span>HUNTERSTAR</span>
      </div>

      <div className="sidebar-storage">
        <div className="storage-text">
          <span>{t("Storage")}</span>
          <span>{`${formatBytes(usedBytes)} / 100 GB`}</span>
        </div>
        <div className="storage-bar">
          <div className="storage-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ key, label, iconSrc }) => (
          <a
            key={key}
            href="#"
            className={`nav-item ${view === key ? "active" : ""}`}
            onClick={(e) => {
              e.preventDefault()
              setView(key)
            }}
          >
            <span><img src={iconSrc} className="svg-icon" alt={`${key}-icon`} /></span>
            <span>{t(label)}</span>
          </a>
        ))}
      </nav>
    </aside>
  )
}
