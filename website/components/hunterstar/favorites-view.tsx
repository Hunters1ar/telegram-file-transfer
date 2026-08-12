"use client"

import { Star } from "lucide-react"
import { useStore } from "@/lib/hunterstar-store"
import { FileRow } from "./file-row"

export function FavoritesView() {
  const { files } = useStore()
  const favs = files.filter((f) => f.isFavorite)

  return (
    <div className="dashboard-scroll">
      <div className="view-head">
        <h2>Favorites</h2>
        <p>Files you have starred for quick access.</p>
      </div>
      <div className="file-list always-actions">
        {favs.length === 0 ? (
          <div className="empty-state">
            <img src="/icons/favourite-icon.webp" className="empty-icon" alt="favorites" style={{ width: 48, height: 48, display: "block", margin: "0 auto 16px" }} />
            <p>No favorites yet. Tap the star on a file to add it here.</p>
          </div>
        ) : (
          favs.map((f) => <FileRow key={f.id} file={f} />)
        )}
      </div>
    </div>
  )
}
