from app.domain.entities.file import FileMetadata

def format_file_card(file_meta: FileMetadata) -> str:
    # Convert size to MB
    size_mb = file_meta.size / (1024 * 1024)
    
    visibility = "🌍 Public" if file_meta.sharing.mode == "public" else "🔒 Private"
    date_str = file_meta.uploaded_at.strftime("%d %b %Y")
    
    return (
        f"📄 <b>{file_meta.original_filename}</b>\n\n"
        f"🆔 <code>{file_meta.share_id}</code>\n"
        f"📦 {size_mb:.2f} MB\n"
        f"👤 {visibility}\n"
        f"📅 {date_str}\n\n"
        f"⬇ Downloads: {file_meta.download_count}"
    )
