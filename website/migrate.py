import re
import os

path = 'lib/hunterstar-store.tsx'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Replace INITIAL_ data block with API setup
api_setup = """const API_BASE = "https://api.hunterstar.online/api/v1"
let tgInitData = ""
if (typeof window !== "undefined") {
  const tg = (window as any).Telegram?.WebApp
  if (tg) {
    tg.ready()
    tg.expand()
    if (tg.platform !== "unknown" && tg.platform !== undefined) {
      document.body.classList.add("tg-miniapp")
      tgInitData = tg.initData
    }
  }
  if (!tgInitData) tgInitData = "user=%7B%22id%22%3A123456%7D&hash=mock"
}

const getHeaders = () => ({ "x-tg-data": tgInitData, "Content-Type": "application/json" })
"""

code = re.sub(
    r'const INITIAL_FOLDERS: Folder\[\] = \[.*?\]\n\nconst INITIAL_FILES: FileItem\[\] = \[.*?\]\n\nconst INITIAL_ACTIVITY: ActivityLog\[\] = \[.*?\]\n',
    api_setup,
    code,
    flags=re.DOTALL
)

# 2. Replace state initialization
state_init_repl = """  const [files, setFiles] = useState<FileItem[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [activity, setActivity] = useState<ActivityLog[]>([])
  const [storageLimit, setStorageLimit] = useState<number>(100 * 1024 * 1024 * 1024)
  const [usedBytes, setUsedBytes] = useState<number>(0)
  
  useEffect(() => {
    // Fetch initial data
    const loadData = async () => {
      try {
        const statsRes = await fetch(`${API_BASE}/stats/`, { headers: getHeaders() })
        if (statsRes.ok) {
          const stats = await statsRes.json()
          setStorageLimit(stats.limit_bytes || 20 * 1024 * 1024)
          setUsedBytes(stats.used_bytes || 0)
        }
        
        const fldRes = await fetch(`${API_BASE}/folders/`, { headers: getHeaders() })
        if (fldRes.ok) {
          const flds = await fldRes.json()
          setFolders(flds.map((f: any) => ({ id: f.id, name: f.name })))
        }

        const filRes = await fetch(`${API_BASE}/files/`, { headers: getHeaders() })
        if (filRes.ok) {
          const fils = await filRes.json()
          setFiles(fils.map((f: any) => ({
            id: f.id,
            name: f.filename,
            sizeBytes: f.size,
            sharing: f.is_public ? "public" : "private",
            isFavorite: f.is_favorite || false,
            folderId: f.folder_id,
            downloads: f.downloads || 0,
            uploadedAt: f.upload_date ? new Date(f.upload_date).getTime() : Date.now()
          })))
        }
      } catch (e) {
        console.error("Failed to load initial data", e)
      }
    }
    loadData()
  }, [])
"""

code = re.sub(
    r'  const \[files, setFiles\] = useState<FileItem\[\]>\(INITIAL_FILES\)\n  const \[folders, setFolders\] = useState<Folder\[\]>\(INITIAL_FOLDERS\)\n  const \[activity, setActivity\] = useState<ActivityLog\[\]>\(INITIAL_ACTIVITY\)\n',
    state_init_repl,
    code
)

# 3. Update toggleFavorite
fav_repl = """  const toggleFavorite = useCallback(
    async (id: string) => {
      const f = files.find((x) => x.id === id)
      if (!f) return
      const newFav = !f.isFavorite
      setFiles((prev) => prev.map((x) => (x.id === id ? { ...x, isFavorite: newFav } : x)))
      
      try {
        const res = await fetch(`${API_BASE}/files/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: getHeaders(),
          body: JSON.stringify({ is_favorite: newFav })
        })
        if (!res.ok) throw new Error("Failed to update favorite")
        pushToast(newFav ? "Added to favorites" : "Removed from favorites")
        if (newFav) addLog("fav", `Favorited ${f.name}`)
      } catch (e) {
        setFiles((prev) => prev.map((x) => (x.id === id ? { ...x, isFavorite: !newFav } : x)))
        pushToast("Could not update favorite", "error")
      }
    },
    [files, pushToast, addLog]
  )"""

code = re.sub(r'  const toggleFavorite = useCallback\(.*?\n    \[files, pushToast, addLog\],\n  \)', fav_repl, code, flags=re.DOTALL)

# 4. Update deleteFile
del_repl = """  const deleteFile = useCallback(
    async (id: string) => {
      const f = files.find((x) => x.id === id)
      if (!f) return
      
      try {
        const res = await fetch(`${API_BASE}/files/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: getHeaders()
        })
        if (!res.ok) throw new Error("Failed to delete")
        setFiles((prev) => prev.filter((x) => x.id !== id))
        setActiveFileId((cur) => (cur === id ? null : cur))
        addLog("trash", `Deleted ${f.name}`)
        pushToast("File deleted")
      } catch (e) {
        pushToast("Could not delete file", "error")
      }
    },
    [files, addLog, pushToast]
  )"""
code = re.sub(r'  const deleteFile = useCallback\(.*?\n    \[files, addLog, pushToast\],\n  \)', del_repl, code, flags=re.DOTALL)

# 5. Update renameFile
ren_repl = """  const renameFile = useCallback(
    async (id: string, name: string) => {
      try {
        const res = await fetch(`${API_BASE}/files/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: getHeaders(),
          body: JSON.stringify({ filename: name })
        })
        if (!res.ok) throw new Error("Failed to rename")
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, name } : f)))
        pushToast("File renamed")
      } catch (e) {
        pushToast("Could not rename file", "error")
      }
    },
    [pushToast]
  )"""
code = re.sub(r'  const renameFile = useCallback\(.*?\n    \[pushToast\],\n  \)', ren_repl, code, flags=re.DOTALL)

# 6. Update setVisibility
vis_repl = """  const setVisibility = useCallback(
    async (id: string, sharing: Sharing) => {
      const is_public = sharing === "public"
      try {
        const res = await fetch(`${API_BASE}/files/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: getHeaders(),
          body: JSON.stringify({ is_public })
        })
        if (!res.ok) throw new Error("Failed to update visibility")
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, sharing } : f)))
        pushToast(is_public ? "File is now public" : "File is now private")
        if (is_public) {
          const f = files.find((x) => x.id === id)
          if (f) addLog("public", `${f.name} made public`)
        }
      } catch (e) {
        pushToast("Could not update visibility", "error")
      }
    },
    [files, pushToast, addLog]
  )"""
code = re.sub(r'  const setVisibility = useCallback\(.*?\n    \[files, pushToast, addLog\],\n  \)', vis_repl, code, flags=re.DOTALL)

# 7. Update moveToFolder
move_repl = """  const moveToFolder = useCallback(
    async (id: string, folderId: string | null) => {
      try {
        const res = await fetch(`${API_BASE}/files/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: getHeaders(),
          body: JSON.stringify({ folder_id: folderId })
        })
        if (!res.ok) throw new Error("Failed to move")
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, folderId } : f)))
        pushToast("File moved successfully")
        addLog("move", "Moved a file to a folder")
      } catch (e) {
        pushToast("Could not move file", "error")
      }
    },
    [pushToast, addLog]
  )"""
code = re.sub(r'  const moveToFolder = useCallback\(.*?\n    \[pushToast, addLog\],\n  \)', move_repl, code, flags=re.DOTALL)

# 8. Update createFolder
cf_repl = """  const createFolder = useCallback(
    async (name: string) => {
      const trimmed = name.trim()
      if (!trimmed) return
      try {
        const res = await fetch(`${API_BASE}/folders/`, {
          method: "POST",
          headers: getHeaders(),
          body: JSON.stringify({ name: trimmed })
        })
        if (!res.ok) throw new Error("Failed to create folder")
        const newFolder = await res.json()
        setFolders((prev) => [...prev, { id: newFolder.id, name: newFolder.name }])
        pushToast("Folder created")
      } catch (e) {
        pushToast("Could not create folder", "error")
      }
    },
    [pushToast]
  )"""
code = re.sub(r'  const createFolder = useCallback\(.*?\n    \[pushToast\],\n  \)', cf_repl, code, flags=re.DOTALL)

# 9. Update deleteFolder
df_repl = """  const deleteFolder = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`${API_BASE}/folders/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: getHeaders()
        })
        if (!res.ok) throw new Error("Failed to delete folder")
        setFiles((prev) => prev.map((f) => (f.folderId === id ? { ...f, folderId: null } : f)))
        setFolders((prev) => prev.filter((f) => f.id !== id))
        pushToast("Folder deleted")
      } catch (e) {
        pushToast("Could not delete folder", "error")
      }
    },
    [pushToast]
  )"""
code = re.sub(r'  const deleteFolder = useCallback\(.*?\n    \[pushToast\],\n  \)', df_repl, code, flags=re.DOTALL)

# 10. Update dependencies array in StoreContext.Provider value
# Remove hardcoded usedBytes & storageLimit calculation if present
code = re.sub(
    r'  const usedBytes = useMemo.*?\[files\]\)\n',
    '',
    code,
    flags=re.DOTALL
)

# 11. Add useEffect to imports
if 'useEffect' not in code:
    code = code.replace('useState }', 'useState, useEffect }')

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)
print("Migration of hunterstar-store complete")
