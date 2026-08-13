from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from app.domain.entities.file import FileMetadata
from app.core.config import settings

class FileAction(CallbackData, prefix="file"):
    action: str
    share_id: str

def get_file_card_keyboard(file_meta: FileMetadata):
    builder = InlineKeyboardBuilder()
    
    # ROW 1
    download_url = f"{settings.api_base_url.rstrip('/')}/api/v1/download/{file_meta.share_id}"
    builder.button(text="⬇ Download", url=download_url)
    
    # ROW 2
    builder.button(text="🔗 Share", switch_inline_query=file_meta.share_id)
    
    # ROW 3
    fav_text = "⭐ Unfavorite" if file_meta.is_favorite else "⭐ Favorite"
    builder.button(text=fav_text, callback_data=FileAction(action="favorite", share_id=file_meta.share_id))
    
    if file_meta.sharing.mode == "public":
        builder.button(text="🔒 Make Private", callback_data=FileAction(action="private", share_id=file_meta.share_id))
    else:
        builder.button(text="🌍 Make Public", callback_data=FileAction(action="public", share_id=file_meta.share_id))
        
    # ROW 4
    builder.button(text="⋮ More", callback_data=FileAction(action="more", share_id=file_meta.share_id))
    
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()

def get_delete_confirmation_keyboard(share_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Yes, Delete", callback_data=FileAction(action="confirm_delete", share_id=share_id))
    builder.button(text="Cancel", callback_data=FileAction(action="cancel_delete", share_id=share_id))
    builder.adjust(2)
    return builder.as_markup()
    
def get_more_menu_keyboard(share_id: str):
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏ Rename", callback_data=FileAction(action="rename", share_id=share_id))
    builder.button(text="🗑 Delete", callback_data=FileAction(action="delete", share_id=share_id))
    builder.button(text="📊 Analytics", callback_data=FileAction(action="analytics", share_id=share_id))
    builder.button(text="📋 Copy ID", callback_data=FileAction(action="copy_id", share_id=share_id))
    builder.button(text="🔗 Copy Link", callback_data=FileAction(action="copy_link", share_id=share_id))
    builder.button(text="🔑 Password", callback_data=FileAction(action="password", share_id=share_id))
    
    builder.button(text="🔙 Back", callback_data=FileAction(action="back_to_main", share_id=share_id))
    
    builder.adjust(2, 2, 2, 2, 1, 1)
    return builder.as_markup()

class LanguageAction(CallbackData, prefix="lang"):
    code: str

def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇬🇧 English", callback_data=LanguageAction(code="en"))
    builder.button(text="🇷🇺 Русский", callback_data=LanguageAction(code="ru"))
    builder.button(text="🇺🇿 O'zbek", callback_data=LanguageAction(code="uz"))
    builder.button(text="🇰🇷 한국어", callback_data=LanguageAction(code="ko"))
    builder.button(text="🇨🇳 中文", callback_data=LanguageAction(code="zh"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()

from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_reply_keyboard(is_admin: bool = False, lang: str = "en"):
    from app.clients.telegram.i18n import t
    builder = ReplyKeyboardBuilder()
    
    builder.button(text=t("📁 My Files", lang))
    builder.button(text=t("📊 Storage", lang))
    builder.button(text=t("⚙️ Settings", lang))
    
    if is_admin:
        builder.button(text=t("👑 Admin Menu", lang))
        
    builder.adjust(2, 2, 1, 1) if is_admin else builder.adjust(2, 2, 1)
        
    return builder.as_markup(resize_keyboard=True, persistent=True)
