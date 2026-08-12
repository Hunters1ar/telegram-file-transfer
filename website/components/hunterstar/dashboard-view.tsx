"use client"

import { useCallback, useRef, useState } from "react"
import {
  Activity,
  ArrowUp,
  CheckCircle2,
  Copy,
  Globe,
  Link2,
  Star,
  Trash2,
  Upload,
  X,
} from "lucide-react"
import { formatBytes, useStore } from "@/lib/hunterstar-store"
import { FileRow } from "./file-row"

interface QueueItem {
  id: string
  name: string
  sizeBytes: number
  progress: number
  status: "uploading" | "done" | "cancelled"
}

type Phase = "default" | "queue" | "success"

const ACTIVITY_ICON: Record<string, typeof ArrowUp> = {
  upload: ArrowUp,
  fav: Star,
  public: Globe,
  trash: Trash2,
  move: Activity,
}

export function DashboardView() {
  const { files, activity, search, addUploads } = useStore()
  const [phase, setPhase] = useState<Phase>("default")
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [dragover, setDragover] = useState(false)
  const [lastSuccess, setLastSuccess] = useState<{ name: string; id: string } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const timers = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const visible = files.filter((f) => (f.name || "").toLowerCase().includes(search.toLowerCase()))
  const recent = [...visible].sort((a, b) => b.uploadedAt - a.uploadedAt).slice(0, 6)

  const publicCount = files.filter((f) => f.sharing === "public").length
  const totalDownloads = files.reduce((s, f) => s + f.downloads, 0)

  const runUpload = useCallback(
    (selected: { name: string; sizeBytes: number }[]) => {
      const items: QueueItem[] = selected.map((s) => ({
        id: Math.random().toString(36).slice(2, 8),
        name: s.name,
        sizeBytes: s.sizeBytes,
        progress: 0,
        status: "uploading",
      }))
      setQueue(items)
      setPhase("queue")

      items.forEach((item) => {
        timers.current[item.id] = setInterval(() => {
          setQueue((prev) => {
            const next = prev.map((q) => {
              if (q.id !== item.id || q.status !== "uploading") return q
              const inc = Math.random() * 22 + 8
              const progress = Math.min(q.progress + inc, 100)
              return { ...q, progress, status: progress >= 100 ? "done" : "uploading" }
            })
            const target = next.find((q) => q.id === item.id)
            if (target && target.progress >= 100) {
              clearInterval(timers.current[item.id])
              delete timers.current[item.id]
              const allDone = next.every((q) => q.status !== "uploading")
              if (allDone) {
                const succeeded = next.filter((q) => q.status === "done")
                if (succeeded.length) {
                  addUploads(succeeded.map((q) => ({ name: q.name, sizeBytes: q.sizeBytes })))
                  const last = succeeded[succeeded.length - 1]
                  setLastSuccess({ name: last.name, id: Math.random().toString(36).slice(2, 8).toUpperCase() })
                  setPhase("success")
                } else {
                  setPhase("default")
                }
              }
            }
            return next
          })
        }, 400)
      })
    },
    [addUploads],
  )

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return
      runUpload(Array.from(list).map((f) => ({ name: f.name, sizeBytes: f.size })))
    },
    [runUpload],
  )

  const cancel = useCallback((id: string) => {
    if (timers.current[id]) {
      clearInterval(timers.current[id])
      delete timers.current[id]
    }
    setQueue((prev) => {
      const next = prev.map((q) => (q.id === id ? { ...q, status: "cancelled" as const } : q))
      if (next.every((q) => q.status !== "uploading")) {
        if (!next.some((q) => q.status === "done")) setTimeout(() => setPhase("default"), 400)
      }
      return next
    })
  }, [])

  return (
    <div className="dashboard-scroll">
      {/* Widgets */}
      <section className="widgets">
        <div className="widget">
          <span className="w-label">STORAGE</span>
          <span className="w-val">{formatBytes(files.reduce((s, f) => s + f.sizeBytes, 0))}</span>
        </div>
        <div className="widget">
          <span className="w-label">FILES</span>
          <span className="w-val">{files.length}</span>
        </div>
        <div className="widget">
          <span className="w-label">DOWNLOADS</span>
          <span className="w-val">{totalDownloads}</span>
        </div>
        <div className="widget">
          <span className="w-label">SHARED</span>
          <span className="w-val">{publicCount}</span>
        </div>
      </section>

      {/* Dropzone */}
      <section>
        <div
          className={`pro-dropzone ${dragover ? "dragover" : ""}`}
          onDragEnter={(e) => {
            e.preventDefault()
            setDragover(true)
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={() => setDragover(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragover(false)
            handleFiles(e.dataTransfer.files)
          }}
        >
          <input
            id="hs-file-input"
            ref={inputRef}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ""
            }}
          />

          {phase === "default" && (
            <div className="dz-content">
              <img src="/icons/upload.webp" className="dz-icon-large" alt="Upload" />
              <h3>Drop files here</h3>
              <p>
                or{" "}
                <button className="dz-browse" onClick={() => inputRef.current?.click()}>
                  Choose File
                </button>
              </p>
              <span className="dz-limit">Supports files up to 100 GB</span>
            </div>
          )}

          {phase === "queue" && (
            <div className="dz-queue">
              {queue.map((q) => (
                <div className="queue-item" key={q.id}>
                  <div className="q-header">
                    <span>{q.name}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{Math.floor(q.progress)}%</span>
                      {q.status === "uploading" && (
                        <button className="q-cancel-btn" title="Cancel" onClick={() => cancel(q.id)}>
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="q-bar-track">
                    <div
                      className="q-bar-fill"
                      style={{
                        width: `${q.progress}%`,
                        background: q.status === "cancelled" ? "var(--danger)" : undefined,
                      }}
                    />
                  </div>
                  <div className="q-meta">
                    <span>
                      {formatBytes((q.sizeBytes * q.progress) / 100)} / {formatBytes(q.sizeBytes)}
                    </span>
                    <span>
                      {q.status === "cancelled" ? "Cancelled" : q.status === "done" ? "Done" : "Uploading..."}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {phase === "success" && lastSuccess && (
            <div className="dz-success">
              <CheckCircle2 className="success-icon" aria-hidden="true" />
              <h3>Upload Complete</h3>
              <p className="success-file">{lastSuccess.name}</p>
              <p className="success-id">ID {lastSuccess.id}</p>
              <div className="success-actions">
                <button onClick={() => setPhase("default")}>
                  <Copy size={15} /> Copy ID
                </button>
                <button onClick={() => setPhase("default")}>
                  <Link2 size={15} /> Copy Link
                </button>
                <button className="btn-public" onClick={() => setPhase("default")}>
                  <Globe size={15} /> Make Public
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* File list + activity */}
      <section className="content-split">
        <div>
          <h3 className="section-title">Recent Files</h3>
          <div className="file-list">
            {recent.length === 0 ? (
              <div className="empty-state">
                <img src="/icons/upload.webp" className="empty-icon" alt="upload" />
                <p>No files yet.</p>
                <button className="empty-btn" onClick={() => inputRef.current?.click()}>
                  Upload your first file
                </button>
              </div>
            ) : (
              recent.map((f) => <FileRow key={f.id} file={f} />)
            )}
          </div>
        </div>

        <div>
          <h3 className="section-title">Recent Activity</h3>
          <div className="activity-list">
            {activity.map((log) => {
              const Icon = ACTIVITY_ICON[log.kind] ?? Activity
              return (
                <div className="act-item" key={log.id}>
                  <Icon className="act-icon" aria-hidden="true" />
                  <div>
                    <span>{log.msg}</span>
                    <span className="act-time">{log.time}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>
    </div>
  )
}
