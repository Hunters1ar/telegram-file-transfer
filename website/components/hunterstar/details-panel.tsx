"use client"

import { useState } from "react"
import { Download, FolderInput, Globe, Link2, Lock, Pencil, Trash2, X } from "lucide-react"
import { formatBytes, timeAgo, useStore } from "@/lib/hunterstar-store"

export function DetailsPanel() {
  const {
    activeFile,
    closeDetails,
    folders,
    copyText,
    renameFile,
    deleteFile,
    setVisibility,
    moveToFolder,
  } = useStore()
  const [showMove, setShowMove] = useState(false)

  const file = activeFile
  const isPublic = file?.sharing === "public"

  return (
    <>
      <aside className={`details-panel ${file ? "open" : ""}`} aria-hidden={!file}>
        {file && (
          <>
            <div className="dp-header">
              <button className="dp-close" onClick={closeDetails} aria-label="Close details">
                <X size={18} />
              </button>
              <h3>{file.name}</h3>
              <p>{formatBytes(file.sizeBytes)}</p>
            </div>

            <div className="dp-body">
              <div className="dp-row">
                <span>File ID</span>
                <span>{file.id}</span>
              </div>
              <div className="dp-row">
                <span>Storage</span>
                <span>Secure</span>
              </div>
              <div className="dp-row">
                <span>Downloads</span>
                <span>{file.downloads}</span>
              </div>
              <div className="dp-row">
                <span>Visibility</span>
                <span>{isPublic ? "Public" : "Private"}</span>
              </div>
              <div className="dp-row">
                <span>Created</span>
                <span>{timeAgo(file.uploadedAt)}</span>
              </div>
            </div>

            <div className="dp-actions">
              <button
                className="dp-btn"
                onClick={() => copyText(`https://t.me/hunterstar_bot?start=${file.id}`, "Download link")}
              >
                <Download /> Download
              </button>
              <button
                className="dp-btn"
                onClick={() => copyText(`https://t.me/hunterstar_bot?start=${file.id}`, "Link")}
              >
                <Link2 /> Share
              </button>
              <button className="dp-btn" onClick={() => setShowMove(true)}>
                <FolderInput /> Move to...
              </button>
              <button
                className="dp-btn"
                onClick={() => {
                  const name = window.prompt("Rename file", file.name)
                  if (name && name !== file.name) renameFile(file.id, name)
                }}
              >
                <Pencil /> Rename
              </button>
              <button className="dp-btn" onClick={() => setVisibility(file.id, isPublic ? "private" : "public")}>
                {isPublic ? <Lock /> : <Globe />}
                {isPublic ? "Make Private" : "Make Public"}
              </button>
              <button className="dp-btn dp-danger" onClick={() => deleteFile(file.id)}>
                <img src="/icons/trash-icon.webp" className="svg-icon" alt="trash" style={{ width: 18, height: 18 }} /> Delete
              </button>
            </div>
          </>
        )}
      </aside>

      {showMove && file && (
        <div className="cmd-overlay" onClick={() => setShowMove(false)}>
          <div className="cmd-palette modal-panel" onClick={(e) => e.stopPropagation()}>
            <h3>Move to Folder</h3>
            <div className="modal-list">
              <div
                className="cmd-item"
                onClick={() => {
                  moveToFolder(file.id, null)
                  setShowMove(false)
                }}
              >
                <FolderInput size={18} /> Dashboard (Remove from folder)
              </div>
              {folders.map((folder) => (
                <div
                  key={folder.id}
                  className="cmd-item"
                  onClick={() => {
                    moveToFolder(file.id, folder.id)
                    setShowMove(false)
                  }}
                >
                  <FolderInput size={18} /> {folder.name}
                </div>
              ))}
            </div>
            <button className="modal-cancel" onClick={() => setShowMove(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  )
}
