from app.domain.entities.file import FileMetadata
from app.clients.telegram.i18n import t

def get_file_emoji(category: str) -> str:
    if category == "photo": return "🖼"
    if category == "video": return "🎬"
    if category == "audio": return "🎵"
    return "📄" # default document

def format_file_card(file_meta: FileMetadata, lang: str = "en") -> str:
    size_mb = file_meta.size / (1024 * 1024)
    visibility = f"🌍 {t('Public', lang)}" if file_meta.sharing.mode == "public" else f"🔒 {t('Private', lang)}"
    date_str = file_meta.uploaded_at.strftime("%d %b %Y")
    emoji = get_file_emoji(file_meta.category)
    
    return (
        f"{emoji} <b>{t('File Details', lang)}</b>\n\n"
        f"🆔 <code>{file_meta.share_id}</code>\n"
        f"📁 {t(file_meta.category.capitalize(), lang)}\n"
        f"📦 {size_mb:.2f} MB\n"
        f"{visibility}\n"
        f"📅 {date_str}\n\n"
        f"⬇ {file_meta.download_count} {t('Downloads', lang)}\n"
        f"━━━━━━━━━━━━━━━"
    )

def format_file_caption(file_meta: FileMetadata, lang: str = "en") -> str:
    """Compact caption for native file sends (Telegram caption limit: 1024 chars)."""
    size_mb = file_meta.size / (1024 * 1024)
    emoji = get_file_emoji(file_meta.category)
    visibility = f"🌍 {t('Public', lang)}" if file_meta.sharing.mode == "public" else f"🔒 {t('Private', lang)}"
    
    return (
        f"{emoji} <b>{file_meta.original_filename}</b>\n"
        f"🆔 <code>{file_meta.share_id}</code>  •  📦 {size_mb:.2f} MB\n"
        f"{visibility}  •  ☁ Hunterstar Cloud"
    )

