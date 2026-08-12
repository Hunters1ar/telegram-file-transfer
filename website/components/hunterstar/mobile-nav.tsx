"use client"

import { FolderClosed, LayoutDashboard, Settings, Star, Upload } from "lucide-react"
import { useStore, type ViewKey } from "@/lib/hunterstar-store"

export function MobileNav({ onUpload }: { onUpload: () => void }) {
  const { view, setView } = useStore()

  const item = (key: ViewKey, iconSrc: string, label: string) => (
    <a
      href="#"
      className={`m-nav-item ${view === key ? "active" : ""}`}
      aria-label={label}
      onClick={(e) => {
        e.preventDefault()
        setView(key)
      }}
    >
      <img src={iconSrc} className="m-svg-icon" alt={label} />
    </a>
  )

  return (
    <nav className="mobile-nav">
      {item("dashboard", "/icons/dashboard-icon.webp", "Dashboard")}
      {item("folders", "/icons/folders-icon.webp", "Folders")}
      <a
        href="#"
        className="m-nav-item upload-btn"
        aria-label="Upload file"
        onClick={(e) => {
          e.preventDefault()
          onUpload()
        }}
      >
        <img src="/icons/upload.webp" className="m-svg-icon" alt="Upload" />
      </a>
      {item("favorites", "/icons/favourite-icon.webp", "Favorites")}
      {item("settings", "/icons/settings-icon.webp", "Settings")}
    </nav>
  )
}
