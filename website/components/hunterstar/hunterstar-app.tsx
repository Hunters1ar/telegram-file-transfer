"use client"

import { useCallback } from "react"
import { HunterstarProvider, useStore } from "@/lib/hunterstar-store"
import { Sidebar } from "./sidebar"
import { MobileNav } from "./mobile-nav"
import { Topbar } from "./topbar"
import { DashboardView } from "./dashboard-view"
import { FoldersView } from "./folders-view"
import { FavoritesView } from "./favorites-view"
import { AnalyticsView } from "./analytics-view"
import { SettingsView } from "./settings-view"
import { DetailsPanel } from "./details-panel"
import { CommandPalette } from "./command-palette"
import { Toaster } from "./toaster"

function Shell() {
  const { view, setView } = useStore()

  const triggerUpload = useCallback(() => {
    setView("dashboard")
    requestAnimationFrame(() => {
      const input = document.getElementById("hs-file-input") as HTMLInputElement | null
      input?.click()
    })
  }, [setView])

  return (
    <div className="hs-app">
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Topbar />
          {view === "dashboard" && <DashboardView />}
          {view === "folders" && <FoldersView />}
          {view === "favorites" && <FavoritesView />}
          {view === "analytics" && <AnalyticsView />}
          {view === "settings" && <SettingsView />}
        </main>
        <DetailsPanel />
      </div>
      <MobileNav onUpload={triggerUpload} />
      <CommandPalette onUpload={triggerUpload} />
      <Toaster />
    </div>
  )
}

export function HunterstarApp() {
  return (
    <HunterstarProvider>
      <Shell />
    </HunterstarProvider>
  )
}
