from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.domain.entities.file import FileMetadata

class FileAction(CallbackData, prefix="file"):
    action: str
    share_id: str

def get_file_card_keyboard(file_meta: FileMetadata):
    builder = InlineKeyboardBuilder()
    
    # Download Link
    download_url = f"https://storage.hunterstar.uz/file/{file_meta.share_id}"
    builder.button(text="⬇ Download", url=download_url)
    
    # Privacy Toggle
    if file_meta.sharing.mode == "public":
        builder.button(text="🔒 Make Private", callback_data=FileAction(action="private", share_id=file_meta.share_id))
    else:
        builder.button(text="🌍 Make Public", callback_data=FileAction(action="public", share_id=file_meta.share_id))
        
    builder.button(text="📊 Details", callback_data=FileAction(action="details", share_id=file_meta.share_id))
    builder.button(text="✏ Rename", callback_data=FileAction(action="rename", share_id=file_meta.share_id))
    
    fav_text = "⭐ Unfavorite" if file_meta.is_favorite else "⭐ Favorite"
    builder.button(text=fav_text, callback_data=FileAction(action="favorite", share_id=file_meta.share_id))
    
    builder.button(text="🗑 Delete", callback_data=FileAction(action="delete", share_id=file_meta.share_id))
    
    # Adjust layout (e.g., 2 buttons per row)
    builder.adjust(1, 2, 2, 1)
    
    return builder.as_markup()
