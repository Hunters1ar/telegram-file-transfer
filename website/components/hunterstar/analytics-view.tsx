"use client"

import { CATEGORY_LABEL, type FileCategory, formatBytes, getFileCategory, useStore } from "@/lib/hunterstar-store"

const CATEGORY_ORDER: FileCategory[] = ["image", "video", "audio", "document", "archive", "code", "other"]

export function AnalyticsView() {
  const { files, usedBytes, storageLimit } = useStore()

  const totalFiles = files.length
  const publicCount = files.filter((f) => f.sharing === "public").length
  const privateCount = totalFiles - publicCount
  const favCount = files.filter((f) => f.isFavorite).length
  const pct = Math.min((usedBytes / storageLimit) * 100, 100)

  const counts = CATEGORY_ORDER.map((cat) => ({
    cat,
    label: CATEGORY_LABEL[cat],
    count: files.filter((f) => getFileCategory(f.name || "").toLowerCase() === cat.toLowerCase()).length,
  }))
    .filter((c) => c.count > 0)
    .sort((a, b) => b.count - a.count)
  const maxCount = counts.reduce((m, c) => Math.max(m, c.count), 0) || 1

  const total = totalFiles || 1

  return (
    <div className="dashboard-scroll">
      <div className="view-head">
        <h2>Analytics</h2>
        <p>An overview of your storage and library.</p>
      </div>

      <section className="storage-hero">
        <div className="storage-hero-info">
          <span className="w-label">STORAGE USED</span>
          <span className="storage-hero-val">{formatBytes(usedBytes)}</span>
          <span className="storage-hero-sub">of 100 GB</span>
        </div>
        <div className="storage-hero-bar">
          <div className="storage-hero-fill" style={{ width: `${pct}%` }} />
        </div>
      </section>

      <section className="widgets">
        <div className="widget">
          <span className="w-label">FILES</span>
          <span className="w-val">{totalFiles}</span>
        </div>
        <div className="widget">
          <span className="w-label">PUBLIC</span>
          <span className="w-val">{publicCount}</span>
        </div>
        <div className="widget">
          <span className="w-label">FAVORITES</span>
          <span className="w-val">{favCount}</span>
        </div>
      </section>

      <section className="content-split analytics-split">
        <div className="chart-card">
          <h3>By file type</h3>
          <div className="bar-chart">
            {counts.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No files to analyze yet.</p>
            ) : (
              counts.map((c) => (
                <div className="bar-row" key={c.cat}>
                  <div className="bar-label">
                    <span className="bar-name">{c.label}</span>
                    <span>{c.count}</span>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(c.count / maxCount) * 100}%` }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="chart-card">
          <h3>Visibility</h3>
          <div className="split-chart">
            <div className="split-track">
              <div className="split-seg-public" style={{ width: `${(publicCount / total) * 100}%` }} />
              <div className="split-seg-private" style={{ width: `${(privateCount / total) * 100}%` }} />
            </div>
            <div className="split-legend">
              <div className="legend-row">
                <span className="legend-dot" style={{ background: "var(--crimson)" }} />
                Public <span className="count">{publicCount}</span>
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ background: "var(--private)" }} />
                Private <span className="count">{privateCount}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
