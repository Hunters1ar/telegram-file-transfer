import { Archive, Code2, FileText, ImageIcon, Music, Video, File } from "lucide-react"
import { getFileCategory } from "@/lib/hunterstar-store"

export function FileIcon({ name, className = "f-icon" }: { name: string; className?: string }) {
  const cat = getFileCategory(name)
  const Icon =
    cat === "image"
      ? ImageIcon
      : cat === "video"
        ? Video
        : cat === "audio"
          ? Music
          : cat === "document"
            ? FileText
            : cat === "archive"
              ? Archive
              : cat === "code"
                ? Code2
                : File
  return <Icon className={className} aria-hidden="true" />
}
