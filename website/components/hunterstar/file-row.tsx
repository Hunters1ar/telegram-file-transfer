"use client"

import { Download, Globe, Link2, Lock, Star, Trash2 } from "lucide-react"
import { type FileItem, formatBytes, useStore } from "@/lib/hunterstar-store"
import { FileIcon } from "./file-icon"

export function FileRow({ file }: { file: FileItem }) {
  const { openDetails, toggleFavorite, deleteFile, copyText } = useStore()

  return (
    <div
      className="file-row"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", file.id)
        e.currentTarget.classList.add("dragging")
      }}
      onDragEnd={(e) => e.currentTarget.classList.remove("dragging")}
      onClick={() => openDetails(file)}
    >
      <div className="f-info">
        <FileIcon name={file.name} />
        <span className="f-name">{file.name}</span>
      </div>
      <div className="f-meta">
        <span>{formatBytes(file.sizeBytes)}</span>
        <span className="f-vis">
          {file.sharing === "public" ? <Globe size={13} /> : <Lock size={13} />}
          {file.sharing === "public" ? "Public" : "Private"}
        </span>
      </div>
      <div className="f-actions" onClick={(e) => e.stopPropagation()}>
        <button
          className={`f-btn f-star ${file.isFavorite ? "is-fav" : ""}`}
          title="Favorite"
          onClick={() => toggleFavorite(file.id)}
        >
          <img src="/icons/favourite-icon.webp" className="svg-icon" alt="favorite" style={{ opacity: file.isFavorite ? 1 : 0.5 }} />
        </button>
        <button
          className="f-btn"
          title="Download"
          onClick={() => copyText(`https://t.me/hunterstar_bot?start=${file.id}`, "Download link")}
        >
          <Download size={15} />
        </button>
        <button
          className="f-btn"
          title="Copy link"
          onClick={() => copyText(`https://t.me/hunterstar_bot?start=${file.id}`, "Link")}
        >
          <Link2 size={15} />
        </button>
        <button
          className="f-btn f-btn-danger"
          title="Delete"
          onClick={() => deleteFile(file.id)}
        >
          <img src="/icons/trash-icon.webp" className="svg-icon" alt="delete"  />
        </button>
      </div>
    </div>
  )
}
