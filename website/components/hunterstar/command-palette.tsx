"use client"

import { useEffect, useMemo, useState } from "react"
import { FolderPlus, Globe, Moon, Search, Settings, Sun, Upload } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { useStore } from "@/lib/hunterstar-store"

export function CommandPalette({ onUpload }: { onUpload: () => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const { setView, createFolder } = useStore()
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setOpen((v) => !v)
      }
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("keydown", handler)
    return () => document.removeEventListener("keydown", handler)
  }, [])

  const actions = useMemo(
    () => [
      { iconSrc: "/icons/upload.webp", label: "Upload File", run: onUpload },
      {
        iconSrc: "/icons/folders-icon.webp",
        label: "Create Folder",
        run: () => {
          setView("folders")
          const name = window.prompt("Enter folder name:")
          if (name) createFolder(name)
        },
      },
      { iconSrc: "/icons/settings-icon.webp", label: "Settings", run: () => setView("settings") },
      { iconSrc: "/icons/stats-icon.webp", label: "Analytics", run: () => setView("analytics") },
      {
        icon: theme === "dark" ? Sun : Moon,
        label: theme === "dark" ? "Switch to Light theme" : "Switch to Dark theme",
        run: toggleTheme,
      },
    ],
    [onUpload, setView, createFolder, theme, toggleTheme],
  )

  const filtered = actions.filter((a) => a.label.toLowerCase().includes(query.toLowerCase()))

  if (!open) return null

  return (
    <div className="cmd-overlay" onClick={() => setOpen(false)}>
      <div className="cmd-palette" onClick={(e) => e.stopPropagation()}>
        <div className="cmd-search">
          <Search size={18} aria-hidden="true" />
          {/* eslint-disable-next-line jsx-a11y/no-autofocus */}
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search or run a command..."
            aria-label="Command search"
          />
        </div>
        <div className="cmd-results">
          {filtered.map((a) => {
            const Icon = a.icon
            return (
              <div
                key={a.label}
                className="cmd-item"
                onClick={() => {
                  a.run()
                  setOpen(false)
                  setQuery("")
                }}
              >
                {a.iconSrc ? <img src={a.iconSrc} className="svg-icon" alt={a.label} style={{ width: 18, height: 18 }} /> : (Icon && <Icon size={18} />)} {a.label}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
