from app.domain.entities.file import FileMetadata

def get_file_emoji(category: str) -> str:
    if category == "photo": return "🖼"
    if category == "video": return "🎬"
    if category == "audio": return "🎵"
    return "📄" # default document

def format_file_card(file_meta: FileMetadata) -> str:
    size_mb = file_meta.size / (1024 * 1024)
    visibility = "🌍 Public" if file_meta.sharing.mode == "public" else "🔒 Private"
    date_str = file_meta.uploaded_at.strftime("%d %b %Y")
    emoji = get_file_emoji(file_meta.category)
    
    return (
        f"{emoji} <b>{file_meta.original_filename}</b>\n\n"
        f"🆔 <code>{file_meta.share_id}</code>\n"
        f"📁 {file_meta.category.capitalize()}\n"
        f"📦 {size_mb:.2f} MB\n"
        f"{visibility}\n"
        f"📅 {date_str}\n\n"
        f"⬇ {file_meta.download_count} Downloads\n"
        f"━━━━━━━━━━━━━━━"
    )
