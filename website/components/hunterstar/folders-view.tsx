"use client"

import { useState } from "react"
import { FolderClosed, X } from "lucide-react"
import { formatBytes, useStore } from "@/lib/hunterstar-store"
import { FileRow } from "./file-row"

export function FoldersView() {
  const { folders, files, createFolder, deleteFolder, moveToFolder } = useStore()
  const [openFolder, setOpenFolder] = useState<string | null>(null)
  const [dragId, setDragId] = useState<string | null>(null)

  const unfoldered = files.filter((f) => !f.folderId)

  if (openFolder) {
    const folder = folders.find((f) => f.id === openFolder)
    const folderFiles = files.filter((f) => f.folderId === openFolder)
    return (
      <div className="dashboard-scroll">
        <div className="view-head">
          <h2>Folders</h2>
          <p>Organize your files into custom folders.</p>
        </div>
        <div>
          <button className="folder-back" onClick={() => setOpenFolder(null)}>
            ← All folders
          </button>
          <h3 className="subhead">{folder?.name}</h3>
          <div className="file-list always-actions">
            {folderFiles.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: 13 }}>This folder is empty.</p>
            ) : (
              folderFiles.map((f) => <FileRow key={f.id} file={f} />)
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-scroll">
      <div className="view-head view-head-row">
        <div>
          <h2>Folders</h2>
          <p>Organize your files into custom folders.</p>
        </div>
        <button
          className="btn-crimson"
          onClick={() => {
            const name = window.prompt("Enter folder name:")
            if (name) createFolder(name)
          }}
        >
          + New Folder
        </button>
      </div>

      <div className="folder-grid">
        {folders.length === 0 && (
          <div className="empty-state" style={{ gridColumn: "1 / -1" }}>
            <img src="/icons/folders-icon.webp" className="empty-icon" alt="folder" />
            <p>No folders yet. Click &apos;+ New Folder&apos; to create one.</p>
          </div>
        )}
        {folders.map((folder) => {
          const folderFiles = files.filter((f) => f.folderId === folder.id)
          const bytes = folderFiles.reduce((s, f) => s + f.sizeBytes, 0)
          return (
            <div
              key={folder.id}
              className="folder-card"
              onClick={() => setOpenFolder(folder.id)}
              onDragOver={(e) => {
                e.preventDefault()
                e.currentTarget.classList.add("drag-over")
              }}
              onDragLeave={(e) => e.currentTarget.classList.remove("drag-over")}
              onDrop={(e) => {
                e.preventDefault()
                e.currentTarget.classList.remove("drag-over")
                const id = e.dataTransfer.getData("text/plain")
                if (id) moveToFolder(id, folder.id)
              }}
            >
              <div className="folder-card-top">
                <FolderClosed className="folder-card-icon" aria-hidden="true" />
                <button
                  className="f-btn f-btn-danger"
                  title="Delete folder"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm(`Delete folder "${folder.name}"? Files move to the dashboard.`)) {
                      deleteFolder(folder.id)
                    }
                  }}
                >
                  <X size={15} />
                </button>
              </div>
              <span className="folder-card-name">{folder.name}</span>
              <span className="folder-card-meta">
                {folderFiles.length} file{folderFiles.length === 1 ? "" : "s"}
                {bytes ? ` · ${formatBytes(bytes)}` : ""}
              </span>
            </div>
          )
        })}
      </div>

      <div>
        <h3 className="subhead">Unorganized Files</h3>
        <p className="subhead-note">Drag files from here onto a folder.</p>
        <div className="file-list" onDragStart={(e) => setDragId((e.target as HTMLElement).dataset.id ?? null)}>
          {unfoldered.length === 0 ? (
            <div className="empty-state">
              <p style={{ margin: 0, fontSize: 13 }}>No unorganized files.</p>
            </div>
          ) : (
            unfoldered.map((f) => <FileRow key={f.id} file={f} />)
          )}
        </div>
      </div>
    </div>
  )
}
