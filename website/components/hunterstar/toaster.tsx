"use client"

import { useStore } from "@/lib/hunterstar-store"

export function Toaster() {
  const { toasts } = useStore()
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type === "error" ? "toast-error" : ""}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
