import io
import re
import uuid
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.config import settings
from app.services.share_service import share_service
from app.repositories.r2.upload import upload_file_to_r2
from app.domain.entities.file import FileMetadata
from app.repositories.mongodb.file_repository import file_repository
from app.clients.telegram.i18n import t, get_all_translations

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

def markdown_to_html(text: str) -> str:
    """Convert Markdown formatting to Telegram HTML parse_mode markup."""
    # Escape HTML special chars first (except ones we'll add ourselves)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Code blocks (``` ... ```) — must come before inline code
    text = re.sub(r"```(?:\w+)?\n?(.*?)```", lambda m: f"<pre><code>{m.group(1).strip()}</code></pre>", text, flags=re.DOTALL)

    # Inline code (`code`)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text, flags=re.DOTALL)

    # Italic: *text* or _text_ (single, not double)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", text)

    # Headings (### Heading → <b>Heading</b> with a newline)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # Strikethrough: ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # Horizontal rules (--- or ***) → just a blank line
    text = re.sub(r"^[-*]{3,}$", "", text, flags=re.MULTILINE)

    return text

class NamingState(StatesGroup):
    waiting_for_name = State()

class TTSState(StatesGroup):
    waiting_for_text = State()

class ImageState(StatesGroup):
    waiting_for_prompt = State()

def api_url(path: str) -> str:
    return f"{settings.api_base_url.rstrip('/')}{path}"

@dp.message(Command("language"))
async def command_language_handler(message: types.Message) -> None:
    from app.clients.telegram.keyboards import get_language_keyboard
    await message.answer(
        "Please choose your language / Пожалуйста, выберите язык:",
        reply_markup=get_language_keyboard()
    )

@dp.message(Command("image"))
async def command_image_handler(message: types.Message, state: FSMContext):
    prompt = message.text.replace("/image", "").strip()
    if not prompt:
        await state.set_state(ImageState.waiting_for_prompt)
        from app.repositories.mongodb.user_repository import user_repository
        user = await user_repository.get_by_telegram_id(message.from_user.id)
        lang = user.language if user and user.language else "en"
        return await message.answer(t("🎨 Please send me the prompt for the image you want to generate:", lang))
        
    await process_image_generation(message, prompt, state)

@dp.message(ImageState.waiting_for_prompt)
async def process_image_prompt_state(message: types.Message, state: FSMContext):
    if not message.text:
        return await message.answer("Please send a text prompt.")
    
    await process_image_generation(message, message.text, state)

async def process_image_generation(message: types.Message, prompt: str, state: FSMContext):
    msg = await message.answer("🎨 Generating image, please wait...")
    
    from app.services.img_generator_service import img_generator_service
    image_stream = await img_generator_service.generate_image(prompt)
    
    if image_stream:
        from aiogram.types import BufferedInputFile
        input_file = BufferedInputFile(image_stream.getvalue(), filename="image.jpg")
        await message.answer_photo(photo=input_file, caption=f"Prompt: {prompt}")
        await msg.delete()
    else:
        await msg.edit_text("❌ Failed to generate image. Please try again later.")
    
    await state.clear()


@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    from app.domain.entities.user import User
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    if not user:
        user = await user_repository.upsert_user(User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        ))
        
    if not user.language:
        from app.clients.telegram.keyboards import get_language_keyboard
        await message.answer(
            "Please choose your language / Пожалуйста, выберите язык:",
            reply_markup=get_language_keyboard()
        )
        return

    await send_welcome_message(message.from_user.id, user.language)

async def send_welcome_message(chat_id: int, lang: str):
    from app.clients.telegram.keyboards import get_main_reply_keyboard
    is_admin = (chat_id == settings.admin)
    
    try:
        await bot.send_sticker(chat_id, sticker="CAACAgIAAxUAAWqDtCg6hAF9t12ZmiXZe3MQjfbEAAKBlgAC1C7gS3CRkIli2NC_PQQ")
    except Exception as e:
        import logging
        logging.error(f"Failed to send start sticker: {e}")
        
    welcome_text = (
        f"🛰️ <b>{t('Welcome to Hunterstar File Transfer', lang)}</b>\n\n"
        f"{t('Hunterstar File Transfer is a service for convenient file transfer, storage, and sharing in one place.', lang)}\n\n"
        f"{t('You can send documents, images, videos, archives, and other file types, manage your saved files, and grant access to other users when necessary.', lang)}\n\n"
        f"<b>{t('Key features:', lang)}</b>\n\n"
        f"📤 <b>{t('File Transfer', lang)}</b>\n"
        f"{t('Send files directly to this chat. Once uploaded, they will be available for further management.', lang)}\n\n"
        f"📁 <b>{t('File Management', lang)}</b>\n"
        f"{t('View your saved files, get necessary information about them, and manage your collection.', lang)}\n\n"
        f"🔗 <b>{t('Sharing', lang)}</b>\n"
        f"{t('Create links to share files with other users without having to re-send the file itself.', lang)}\n\n"
        f"🔐 <b>{t('Access Control', lang)}</b>\n"
        f"{t('Manage file visibility and determine who can access them.', lang)}\n\n"
        f"📊 <b>{t('File Information', lang)}</b>\n"
        f"{t('Get details about the size, format, upload date, and other parameters of your saved files.', lang)}\n\n"
        f"⚙️ <b>{t('Settings', lang)}</b>\n"
        f"{t('Manage service parameters and personal settings.', lang)}\n\n"
        f"{t('To get started, simply send a file to this chat.', lang)}\n\n"
        f"{t('You can also use the menu below to view and manage your saved files.', lang)}\n\n"
        f"<i>{t('Hunterstar File Transfer is designed to make file transfer and management simple, clear, and accessible from a single interface. Start by sending your first file.', lang)}</i>"
    )
    
    await bot.send_message(chat_id, welcome_text, parse_mode="HTML")
    await bot.send_message(chat_id, t("Enjoy!", lang), reply_markup=get_main_reply_keyboard(is_admin, lang))

from app.clients.telegram.keyboards import LanguageAction
@dp.callback_query(LanguageAction.filter())
async def handle_language_selection(callback_query: types.CallbackQuery, callback_data: LanguageAction):
    from app.repositories.mongodb.user_repository import user_repository
    
    lang = callback_data.code
    await user_repository.set_language(callback_query.from_user.id, lang)
    
    await callback_query.message.delete()
    await send_welcome_message(callback_query.from_user.id, lang)


@dp.message(Command("admin"))
@dp.message(F.text.in_(get_all_translations("👑 Admin Menu")))
async def handle_admin_menu(message: types.Message):
    """Swap the bottom reply keyboard to the admin panel keyboard."""
    if message.from_user.id != settings.admin:
        return

    from app.repositories.mongodb.user_repository import user_repository
    from app.clients.telegram.keyboards import get_admin_reply_keyboard
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"

    await message.answer(
        t("👑 <b>Admin Panel</b>\n\nChoose an action below:", lang),
        parse_mode="HTML",
        reply_markup=get_admin_reply_keyboard(lang=lang),
    )


@dp.message(F.text.in_(get_all_translations("🔙 Back")))
async def handle_admin_back(message: types.Message):
    """Return from the admin keyboard back to the main reply keyboard."""
    from app.repositories.mongodb.user_repository import user_repository
    from app.clients.telegram.keyboards import get_main_reply_keyboard
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"

    await message.answer(
        t("Main menu 👇", lang),
        reply_markup=get_main_reply_keyboard(is_admin=True, lang=lang),
    )


@dp.message(F.text.in_(get_all_translations("👥 Users")))
async def handle_admin_users_btn(message: types.Message):
    """Show a list of all registered users."""
    if message.from_user.id != settings.admin:
        return

    from app.repositories.mongodb.user_repository import user_repository
    users = await user_repository.get_all_users()

    text = f"👥 <b>Total Users: {len(users)}</b>\n\n"
    for idx, u in enumerate(users[:100]):
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        uname = f"@{u.username}" if u.username else "No Username"
        text += f"{idx+1}. <b>{name}</b> ({uname}) – ID: <code>{u.telegram_id}</code>\n"

    if len(users) > 100:
        text += f"\n… and {len(users) - 100} more."

    for chunk in range(0, len(text), 4000):
        await message.answer(text[chunk:chunk + 4000], parse_mode="HTML")


@dp.message(F.text.in_(get_all_translations("📈 Stats")))
async def handle_admin_stats_btn(message: types.Message):
    """Show system-wide storage stats."""
    if message.from_user.id != settings.admin:
        return

    from app.repositories.mongodb.user_repository import user_repository
    from app.repositories.mongodb.file_repository import file_repository as _fr
    total_users = len(await user_repository.get_all_users())
    all_stats = await _fr.get_global_stats() if hasattr(_fr, "get_global_stats") else {}
    total_files = all_stats.get("total_files", "N/A")
    total_size_mb = all_stats.get("total_size", 0) / (1024 * 1024) if all_stats.get("total_size") else 0

    await message.answer(
        f"📈 <b>System Stats</b>\n\n"
        f"👥 Users: <b>{total_users}</b>\n"
        f"📁 Files: <b>{total_files}</b>\n"
        f"☁ Storage: <b>{total_size_mb:.2f} MB</b>",
        parse_mode="HTML",
    )


@dp.message(F.text.in_(get_all_translations("📢 Broadcast")))
async def handle_admin_broadcast_btn(message: types.Message):
    """Placeholder — broadcast is not yet implemented."""
    if message.from_user.id != settings.admin:
        return
    await message.answer(
        "📢 <b>Broadcast</b>\n\nThis feature is coming soon!\n"
        "Use <code>/broadcast &lt;message&gt;</code> once available.",
        parse_mode="HTML",
    )


@dp.message(F.text.in_(get_all_translations("🛠 Maintenance")))
async def handle_admin_maintenance_btn(message: types.Message):
    """Show maintenance options as an inline keyboard."""
    if message.from_user.id != settings.admin:
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙ Set File Limit", callback_data="admin_setlimit")
    builder.button(text="🧹 Clear Whole System", callback_data="admin_clearwhole")
    builder.adjust(1)

    await message.answer(
        "🛠 <b>Maintenance</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

@dp.callback_query(F.data == "admin_users")
async def handle_admin_users_cb(callback: types.CallbackQuery):
    if callback.from_user.id != settings.admin:
        return
    
    from app.repositories.mongodb.user_repository import user_repository
    users = await user_repository.get_all_users()
    
    text = f"👥 <b>Total Users: {len(users)}</b>\n\n"
    for idx, u in enumerate(users[:100]):
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        uname = f"@{u.username}" if u.username else "No Username"
        text += f"{idx+1}. <b>{name}</b> ({uname}) - ID: <code>{u.telegram_id}</code>\n"
        
    if len(users) > 100:
        text += f"\n... and {len(users) - 100} more."
        
    await callback.message.edit_text(text[:4000], parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_setlimit")
async def handle_admin_setlimit_cb(callback: types.CallbackQuery):
    if callback.from_user.id != settings.admin:
        return
    await callback.message.edit_text("To set a global file size limit, send the command:\n<code>/setlimit &lt;MB&gt;</code>\nExample: <code>/setlimit 50</code>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_clearwhole")
async def handle_admin_clearwhole_cb(callback: types.CallbackQuery):
    if callback.from_user.id != settings.admin:
        return
    await callback.message.edit_text("🧹 Cleaning up system (MongoDB and Cloudflare R2)...")
    try:
        from app.repositories.r2.r2_service import empty_r2_bucket
        await empty_r2_bucket()
        await file_repository.clear_all()
        await callback.message.edit_text("✅ System is completely clean! All files and data have been wiped.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Failed to clean system: {e}")

@dp.message(Command("users"))
async def command_users_handler(message: types.Message):
    if message.from_user.id != settings.admin:
        return
    
    from app.repositories.mongodb.user_repository import user_repository
    users = await user_repository.get_all_users()
    
    text = f"👥 <b>Total Users: {len(users)}</b>\n\n"
    for idx, u in enumerate(users[:100]):
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        uname = f"@{u.username}" if u.username else "No Username"
        text += f"{idx+1}. <b>{name}</b> ({uname}) - ID: <code>{u.telegram_id}</code>\n"
        
    if len(users) > 100:
        text += f"\n... and {len(users) - 100} more."
        
    for x in range(0, len(text), 4000):
        await message.answer(text[x:x+4000], parse_mode="HTML")

@dp.message(Command("setlimit"))
async def command_setlimit_handler(message: types.Message):
    if message.from_user.id != settings.admin:
        return
    
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("❌ Usage: /setlimit <MB>\nExample: /setlimit 20")
        
    limit_mb = int(parts[1])
    if limit_mb > 20:
        await message.answer("⚠ Warning: Telegram Bot API restricts downloads to 20MB unless you use a local bot API server. Setting limit anyway.")
        
    from app.repositories.mongodb.settings_repository import settings_repository
    await settings_repository.set_global_file_limit(limit_mb)
    
    await message.answer(f"✅ Global file size limit set to <b>{limit_mb}MB</b>.", parse_mode="HTML")

@dp.message(Command("settings"))
@dp.message(F.text.in_(get_all_translations("⚙️ Settings")))
async def command_settings_handler(message: types.Message):
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    show_others = getattr(user, 'show_others_files', True) if user else True
    lang = user.language if user and user.language else "en"
    
    try:
        await message.answer_sticker(sticker="CAACAgIAAxUAAWqDy_S7KzGo0vy0_Ctf6DI8rYhjAAKp6QACHaAgSFg2W-4xtcqvPQQ")
    except Exception as e:
        import logging
        logging.error(f"Failed to send settings sticker: {e}")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    text = f"{t('See others files', lang)} (✅)" if show_others else f"{t('See others files', lang)} (❌)"
    builder.button(text=text, callback_data="toggle_show_others")
    builder.button(text=f"🌐 {t('Change Language', lang)}", callback_data="change_language")
    builder.adjust(1)
    
    await message.answer(f"<b>{t('Settings', lang)}</b>\n\n{t('Manage your preferences below.', lang)}", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "change_language")
async def handle_change_language_cb(callback: types.CallbackQuery):
    from app.clients.telegram.keyboards import get_language_keyboard
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "en"
    await callback.message.edit_text(
        t("Please choose your language / Пожалуйста, выберите язык:", lang),
        reply_markup=get_language_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "toggle_show_others")
async def handle_toggle_show_others_cb(callback: types.CallbackQuery):
    from app.repositories.mongodb.user_repository import user_repository
    new_value = await user_repository.toggle_show_others_files(callback.from_user.id)
    user = await user_repository.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user and user.language else "en"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    text = f"{t('See others files', lang)} (✅)" if new_value else f"{t('See others files', lang)} (❌)"
    builder.button(text=text, callback_data="toggle_show_others")
    builder.button(text=f"🌐 {t('Change Language', lang)}", callback_data="change_language")
    builder.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer(t("Setting updated!", lang))

@dp.message(Command("clearwhole"))
async def command_clearwhole_handler(message: types.Message) -> None:
    if message.from_user.id != settings.admin:
        return
    
    msg = await message.answer("🧹 Cleaning up system (MongoDB and Cloudflare R2)...")
    try:
        from app.repositories.r2.r2_service import empty_r2_bucket
        await empty_r2_bucket()
        await file_repository.clear_all()
        await msg.edit_text("✅ System is completely clean! All files and data have been wiped.")
    except Exception as e:
        await msg.edit_text(f"❌ Failed to clean system: {e}")

@dp.message(F.sticker | F.animation)
async def handle_sticker_animation(message: types.Message, state: FSMContext):
    if message.sticker:
        file_obj = message.sticker
        category = "sticker"
        mime_type = "image/webp" if not file_obj.is_animated and not file_obj.is_video else "application/x-tgsticker"
    else:
        file_obj = message.animation
        category = "animation"
        mime_type = getattr(file_obj, "mime_type", "video/mp4")
        
    size = getattr(file_obj, "file_size", 0)
    
    await state.update_data(
        file_id=file_obj.file_id,
        file_unique_id=file_obj.file_unique_id,
        category=category,
        mime_type=mime_type,
        size=size
    )
    
    await state.set_state(NamingState.waiting_for_name)
    await message.reply(f"It looks like you sent a {category}. Ok, please give a name for it to add to your collection.")

@dp.message(NamingState.waiting_for_name)
async def handle_naming_sticker(message: types.Message, state: FSMContext):
    if not message.text:
        return await message.reply("Please send a text name.")
        
    data = await state.get_data()
    from app.services.upload_service import upload_service
    
    file_meta = await upload_service.process_virtual_upload(
        owner_id=message.from_user.id,
        chat_id=message.chat.id,
        original_filename=message.text.strip(),
        mime_type=data["mime_type"],
        size=data["size"],
        category=data["category"],
        telegram_file_id=data["file_id"],
        telegram_unique_id=data["file_unique_id"]
    )
    
    await state.clear()
    
    from app.clients.telegram.keyboards import get_file_card_keyboard
    from app.clients.telegram.messages import format_file_card
    
    await message.reply(
        text=f"✅ Saved! You can now send it by typing <code>@hunterstarfilebot {message.text.strip()}</code> anywhere.\n\n" + format_file_card(file_meta),
        parse_mode="HTML",
        reply_markup=get_file_card_keyboard(file_meta)
    )

@dp.message(F.document | F.video | F.audio | F.photo)
async def handle_file_upload(message: types.Message):
    from app.domain.entities.user import User
    from app.repositories.mongodb.user_repository import user_repository
    await user_repository.upsert_user(User(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    ))

    # Determine file type and get file object
    file_type = "document"
    if message.document:
        file_obj = message.document
    elif message.video:
        file_obj = message.video
        file_type = "video"
    elif message.audio:
        file_obj = message.audio
        file_type = "audio"
    elif message.photo:
        file_obj = message.photo[-1] # Highest resolution photo
        file_type = "photo"
    else:
        return

    # Acknowledge receipt
    try:
        msg = await message.answer_sticker("CAACAgIAAxUAAWqDy_SEyGbgd58sTpNtE-zy-dBrAAKAnQAC0DohSK4gWejez-s-PQQ")
    except Exception:
        msg = await message.reply("Downloading file from Telegram...")
    
    # Original filename, mime_type, and size
    original_filename = getattr(file_obj, "file_name", f"{file_obj.file_unique_id}.bin")
    if file_type == "photo":
        original_filename = f"{file_obj.file_unique_id}.jpg"
        
    mime_type = getattr(file_obj, "mime_type", "application/octet-stream")
    if file_type == "photo":
        mime_type = "image/jpeg"
        
    size = getattr(file_obj, "file_size", 0)
    
    from app.repositories.mongodb.settings_repository import settings_repository
    limit_mb = await settings_repository.get_global_file_limit()
    
    if size > limit_mb * 1024 * 1024:
        await msg.delete()
        await message.answer(f"❌ This file is too large! The current limit is {limit_mb}MB.")
        return

    try:
        file_info = await bot.get_file(file_obj.file_id)
    except Exception as e:
        await msg.delete()
        await message.answer(f"❌ Failed to get file info: {e}")
        return
        
    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    file_stream.seek(0)
    
    from app.services.upload_service import upload_service
    from app.clients.telegram.keyboards import get_file_card_keyboard
    from app.clients.telegram.messages import format_file_card, format_file_caption

    file_meta = await upload_service.process_upload(
        file_stream=file_stream,
        owner_id=message.from_user.id,
        chat_id=message.chat.id,
        original_filename=original_filename,
        mime_type=mime_type,
        size=size,
        telegram_file_id=file_obj.file_id,
        telegram_unique_id=file_obj.file_unique_id,
        category=file_type
    )
    
    # File is too large for native Telegram send, use File Details card
    await msg.delete()
    await message.answer(
        text=format_file_card(file_meta), 
        parse_mode="HTML",
        reply_markup=get_file_card_keyboard(file_meta)
    )

def get_inline_result(file_meta):
    f_type = getattr(file_meta, "category", "document")
    title = file_meta.original_filename
    size_mb = f"{file_meta.size / (1024*1024):.2f}"
    
    # Handle the premium rich card view as requested
    icon = "🎬" if f_type == "video" else "🖼" if f_type == "photo" else "🎵" if f_type == "audio" else "📄"
    visibility = "🌍 Public" if getattr(file_meta.sharing, "mode", "private") == "public" else "🔒 Private"
    
    MAX_NATIVE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB
    
    # For files under 4GB with a telegram_file_id, send native cached media WITHOUT UI
    if file_meta.size <= MAX_NATIVE_SIZE and file_meta.telegram_file_id:
        if f_type == "audio":
            return types.InlineQueryResultCachedAudio(
                id=file_meta.share_id,
                audio_file_id=file_meta.telegram_file_id
            )
        elif f_type == "video":
            return types.InlineQueryResultCachedVideo(
                id=file_meta.share_id,
                video_file_id=file_meta.telegram_file_id,
                title=title
            )
        elif f_type == "photo":
            return types.InlineQueryResultCachedPhoto(
                id=file_meta.share_id,
                photo_file_id=file_meta.telegram_file_id
            )
        elif f_type == "sticker":
            return types.InlineQueryResultCachedSticker(
                id=file_meta.share_id,
                sticker_file_id=file_meta.telegram_file_id
            )
        elif f_type == "animation":
            return types.InlineQueryResultCachedMpeg4Gif(
                id=file_meta.share_id,
                mpeg4_file_id=file_meta.telegram_file_id,
                title=title
            )
        else:
            return types.InlineQueryResultCachedDocument(
                id=file_meta.share_id,
                document_file_id=file_meta.telegram_file_id,
                title=title
            )
    
    # For files over 4GB or without telegram_file_id, use text article card
    message_text = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{icon} <b>{title}</b>\n\n"
        f"🆔 <code>{file_meta.share_id}</code>\n"
        f"📦 {size_mb} MB\n"
        f"👤 {visibility}\n"
        f"☁ Hunterstar Cloud\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Download securely below."
    )
    
    return types.InlineQueryResultArticle(
        id=file_meta.share_id,
        title=title,
        description=f"Size: {size_mb} MB | 📁 {f_type.capitalize()}",
        input_message_content=types.InputTextMessageContent(
            message_text=message_text,
            parse_mode="HTML"
        ),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬇ Download", url=api_url(f"/api/v1/download/{file_meta.share_id}"))],
            [types.InlineKeyboardButton(text="📋 Copy ID", switch_inline_query=file_meta.share_id), types.InlineKeyboardButton(text="🌍 Open App", url=settings.webapp_url)]
        ])
    )

@dp.message(F.text.in_(get_all_translations("📁 My Files")))
async def handle_my_files(message: types.Message):
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"

    files = await file_repository.get_by_owner_id(message.from_user.id, limit=50)
    if not files:
        await message.answer(t("📁 You have no files yet.\n\nSend me any file to get started!", lang))
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for f in files:
        icon = "🎬" if f.category == "video" else "🖼" if f.category == "photo" else "🎵" if f.category == "audio" else "📄"
        size_str = f"{f.size / (1024*1024):.1f} MB" if f.size >= 1024*1024 else f"{f.size // 1024} KB"
        builder.button(
            text=f"{icon} {f.original_filename[:28]} · {size_str}",
            callback_data=FileAction(action="back_to_main", share_id=f.share_id)
        )
    builder.adjust(1)
    await message.answer(f"📁 <b>{t('Your Files', lang)}</b> ({len(files)} {t('total', lang)}):", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.message(F.text.in_(get_all_translations("🔗 My Links")))
async def handle_my_links(message: types.Message):
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"
    await message.answer(t("Tap the 'Menu' button to open the Web App and manage your links.", lang))

@dp.message(F.text.in_(get_all_translations("📤 Send File")))
async def handle_send_file(message: types.Message):
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"
    await message.answer(t("Simply drag and drop or attach a file to this chat to upload it to Hunterstar File Transfer.", lang))

@dp.message(F.text.in_(get_all_translations("📊 Storage")))
async def handle_storage_stats(message: types.Message):
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"

    stats = await file_repository.get_user_stats(message.from_user.id)
    await message.answer(f"☁ <b>{t('Storage Used', lang)}:</b> {stats.get('total_size', 0) / (1024*1024):.2f} MB\n📁 <b>{t('Total Files', lang)}:</b> {stats.get('total_files', 0)}", parse_mode="HTML")

@dp.message(F.text.in_(get_all_translations("🎨 Generate Image")))
async def handle_generate_image_button(message: types.Message, state: FSMContext):
    await state.set_state(ImageState.waiting_for_prompt)
    from app.repositories.mongodb.user_repository import user_repository
    user = await user_repository.get_by_telegram_id(message.from_user.id)
    lang = user.language if user and user.language else "en"
    await message.answer(t("🎨 Please send me the prompt for the image you want to generate:", lang))

@dp.message(F.text.in_(get_all_translations("🎵 Generate Audio")))
async def handle_generate_audio_button(message: types.Message, state: FSMContext):
    from app.core.config import settings as _s
    if not _s.tts_enabled:
        await message.answer("🔇 TTS is currently disabled.")
        return
    await state.set_state(TTSState.waiting_for_text)
    await message.answer(
        "🎙️ <b>TTS mode active!</b>\n"
        "Send me any text and I'll speak it for you.",
        parse_mode="HTML",
    )


@dp.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery):
    query = inline_query.query.strip()
    requester_id = inline_query.from_user.id

    try:
        if not query:
            # Empty query: show files based on the user's "show_others_files" preference.
            # This is the ONLY place where that setting takes effect — the website always
            # shows only the user's own files regardless.
            from app.repositories.mongodb.user_repository import user_repository
            user_model = await user_repository.get_by_telegram_id(requester_id)
            show_others = getattr(user_model, 'show_others_files', True) if user_model else True

            user_files = await file_repository.get_files_for_user(requester_id, show_others, limit=50)
            if not user_files:
                no_files = types.InlineQueryResultArticle(
                    id="no_files",
                    title="No files found",
                    description="You haven't uploaded any files yet.",
                    input_message_content=types.InputTextMessageContent(message_text="I haven't uploaded anything yet!")
                )
                await inline_query.answer([no_files], cache_time=5, is_personal=True)
                return

            results = [get_inline_result(f) for f in user_files]
            await inline_query.answer(results, cache_time=5, is_personal=True)
            return

        # Specific query by share_id
        file_meta = await file_repository.get_by_share_id(query)
        if not file_meta:
            # Search by name instead
            search_results = await file_repository.search_files_by_name(requester_id, query, limit=50)
            if search_results:
                results = [get_inline_result(f) for f in search_results]
                await inline_query.answer(results, cache_time=5, is_personal=True)
                return

            not_found = types.InlineQueryResultArticle(
                id="not_found",
                title="File not found",
                description="No matching file or invalid Share ID",
                input_message_content=types.InputTextMessageContent(message_text="File not found")
            )
            await inline_query.answer([not_found], cache_time=5)
            return

        # Privacy gate: block private files that belong to another user
        is_own = (file_meta.owner_id == requester_id)
        is_public = (file_meta.sharing.mode == "public")
        if not is_own and not is_public:
            blocked = types.InlineQueryResultArticle(
                id="blocked",
                title="Private file",
                description="This file is private and cannot be shared.",
                input_message_content=types.InputTextMessageContent(message_text="This file is private and cannot be shared.")
            )
            await inline_query.answer([blocked], cache_time=5)
            return

        result = get_inline_result(file_meta)
        await inline_query.answer([result], cache_time=5, is_personal=False)

    except Exception as e:
        print(f"Inline query error: {e}")
        error_result = types.InlineQueryResultArticle(
            id="error",
            title="Error Occurred",
            description=str(e),
            input_message_content=types.InputTextMessageContent(message_text=f"Error: {e}")
        )
        await inline_query.answer([error_result], cache_time=5)

from app.clients.telegram.keyboards import FileAction, get_file_card_keyboard, get_delete_confirmation_keyboard, get_more_menu_keyboard
from app.clients.telegram.messages import format_file_card

@dp.callback_query(FileAction.filter(F.action == "public"))
async def handle_make_public(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta or file_meta.owner_id != callback.from_user.id:
        return await callback.answer("File not found or unauthorized.", show_alert=True)
    
    file_meta.sharing.mode = "public"
    await file_repository.update(file_meta)
    await callback.message.edit_text(format_file_card(file_meta), parse_mode="HTML", reply_markup=get_file_card_keyboard(file_meta))
    await callback.answer("File is now public 🌍")

@dp.callback_query(FileAction.filter(F.action == "private"))
async def handle_make_private(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta or file_meta.owner_id != callback.from_user.id:
        return await callback.answer("File not found or unauthorized.", show_alert=True)
    
    file_meta.sharing.mode = "private"
    await file_repository.update(file_meta)
    await callback.message.edit_text(format_file_card(file_meta), parse_mode="HTML", reply_markup=get_file_card_keyboard(file_meta))
    await callback.answer("File is now private 🔒")

@dp.callback_query(FileAction.filter(F.action == "favorite"))
async def handle_favorite(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta or file_meta.owner_id != callback.from_user.id:
        return await callback.answer("File not found or unauthorized.", show_alert=True)
    
    file_meta.is_favorite = not file_meta.is_favorite
    await file_repository.update(file_meta)
    await callback.message.edit_reply_markup(reply_markup=get_file_card_keyboard(file_meta))
    msg = "Added to favorites ⭐" if file_meta.is_favorite else "Removed from favorites"
    await callback.answer(msg)

@dp.callback_query(FileAction.filter(F.action == "more"))
async def handle_more_menu(callback: types.CallbackQuery, callback_data: FileAction):
    await callback.message.edit_reply_markup(reply_markup=get_more_menu_keyboard(callback_data.share_id))
    await callback.answer()

@dp.callback_query(FileAction.filter(F.action == "back_to_main"))
async def handle_back_to_main(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if file_meta:
        await callback.message.edit_reply_markup(reply_markup=get_file_card_keyboard(file_meta))
    await callback.answer()

@dp.callback_query(FileAction.filter(F.action == "delete"))
async def handle_delete_prompt(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta or file_meta.owner_id != callback.from_user.id:
        return await callback.answer("File not found or unauthorized.", show_alert=True)
        
    await callback.message.edit_text(f"⚠ Delete file? <b>{file_meta.original_filename}</b>", parse_mode="HTML", reply_markup=get_delete_confirmation_keyboard(file_meta.share_id))
    await callback.answer()

@dp.callback_query(FileAction.filter(F.action == "cancel_delete"))
async def handle_cancel_delete(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta:
        return await callback.answer("File not found.", show_alert=True)
        
    await callback.message.edit_text(format_file_card(file_meta), parse_mode="HTML", reply_markup=get_file_card_keyboard(file_meta))
    await callback.answer()

@dp.callback_query(FileAction.filter(F.action == "confirm_delete"))
async def handle_confirm_delete(callback: types.CallbackQuery, callback_data: FileAction):
    file_meta = await file_repository.get_by_share_id(callback_data.share_id)
    if not file_meta or file_meta.owner_id != callback.from_user.id:
        return await callback.answer("File not found or unauthorized.", show_alert=True)

    # Delete from R2 first, then MongoDB
    try:
        from app.repositories.r2.r2_service import delete_file_from_r2
        await delete_file_from_r2(file_meta.r2_object_key)
    except Exception as e:
        print(f"R2 delete failed for {file_meta.r2_object_key}: {e}")

    await file_repository.delete(callback_data.share_id)
    await callback.message.edit_text(f"🗑 Deleted <b>{file_meta.original_filename}</b>", parse_mode="HTML")
    await callback.answer("File deleted")

@dp.callback_query(FileAction.filter(F.action.in_({"rename", "move", "analytics", "details", "copy_id", "copy_link", "expire", "password"})))
async def handle_coming_soon(callback: types.CallbackQuery):
    await callback.answer("This feature is coming soon!", show_alert=True)


async def setup_bot_commands(bot_instance: Bot):
    user_commands = [
        types.BotCommand(command="start", description="Start the bot and show menu"),
        types.BotCommand(command="tts", description="Convert text to voice 🎙️"),
        types.BotCommand(command="image", description="Generate an image using AI 🎨"),
        types.BotCommand(command="settings", description="Manage file visibility"),
        types.BotCommand(command="language", description="Change Language")
    ]
    admin_commands = [
        types.BotCommand(command="start", description="Start the bot and show menu"),
        types.BotCommand(command="tts", description="Convert text to voice 🎙️"),
        types.BotCommand(command="image", description="Generate an image using AI 🎨"),
        types.BotCommand(command="settings", description="Manage file visibility"),
        types.BotCommand(command="language", description="Change Language"),
        types.BotCommand(command="admin", description="Open Admin Panel"),
        types.BotCommand(command="clearwhole", description="Clear all data"),
        types.BotCommand(command="users", description="List all users"),
        types.BotCommand(command="setlimit", description="Set file limit (MB)")
    ]
    
    await bot_instance.set_my_commands(user_commands, scope=types.BotCommandScopeDefault())
    try:
        await bot_instance.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(chat_id=settings.telegram_admin_user_id))
    except Exception as e:
        print(f"Could not set admin commands: {e}")

async def setup_bot_ui(bot_instance: Bot):
    await setup_bot_commands(bot_instance)
    try:
        await bot_instance.set_chat_menu_button(
            menu_button=types.MenuButtonWebApp(
                text="Open", 
                web_app=types.WebAppInfo(url=settings.webapp_url)
            )
        )
    except Exception as e:
        print(f"Could not set menu button: {e}")

async def start_polling():
    await setup_bot_ui(bot)
    await dp.start_polling(bot)


# ==========================================
# ==========================================
# TTS + AI Agent Fallback Handlers
# MUST REMAIN AT THE BOTTOM OF THE FILE
# ==========================================

async def _send_voice_or_fallback(
    message: types.Message,
    text: str,
    fallback_label: str = "",
    lang: str = "",
) -> None:
    """
    Try to synthesize *text* and send as a Telegram voice note.
    If TTS fails, send the plain text with a short notice instead.
    """
    from app.services.tts_service import tts_service, TTSError

    # If language isn't explicitly passed, try to fetch the user's preferred language
    if not lang:
        try:
            from app.repositories.mongodb.user_repository import user_repository
            user = await user_repository.get_by_telegram_id(message.from_user.id)
            lang = user.language if user and user.language else "en"
        except Exception:
            lang = "en"
    
    try:
        audio_bytes = await tts_service.synthesize(text, lang=lang)
        voice_file = types.BufferedInputFile(audio_bytes, filename="voice.mp3")
        await message.answer_voice(voice_file)
    except (TTSError, ValueError) as tts_exc:
        import logging as _log
        _log.warning("TTS failed, falling back to text. Reason: %s", tts_exc)
        notice = "\n\n<i>🔇 Couldn't generate audio — here's the text instead.</i>" if not fallback_label else f"\n\n<i>🔇 {fallback_label}</i>"
        await message.answer(markdown_to_html(text) + notice, parse_mode="HTML")


@dp.message(Command("tts"))
async def command_tts_handler(message: types.Message, state: FSMContext) -> None:
    """
    /tts <text>  ->  Telegram voice note of <text>.
    /tts alone   ->  Enter waiting state; the next message will be spoken.
    Bypasses the AI entirely.
    """
    from app.core.config import settings as _s
    if not _s.tts_enabled:
        await message.answer("🔇 TTS is currently disabled.")
        return

    # Strip the command itself to get the body
    body = message.text[len("/tts"):].strip() if message.text else ""

    if not body:
        # Enter FSM state — next message will be spoken as voice
        await state.set_state(TTSState.waiting_for_text)
        await message.answer(
            "🎙️ <b>TTS mode active!</b>\n"
            "Send me any text and I'll speak it for you.",
            parse_mode="HTML",
        )
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    await _send_voice_or_fallback(message, body)


@dp.message(TTSState.waiting_for_text)
async def handle_tts_awaited_text(message: types.Message, state: FSMContext) -> None:
    """Handles the text message that follows a bare /tts command."""
    await state.clear()
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Please send some text to speak.")
        return
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    await _send_voice_or_fallback(message, text)


@dp.message(F.text)
async def ai_agent_fallback_handler(message: types.Message, state: FSMContext):
    import re as _re

    raw_text = message.text or ""
    is_group = message.chat.type in ("group", "supergroup")

    # ── Group chat: only respond when the bot is @mentioned ───────────────────
    if is_group:
        bot_mention = f"@{settings.bot_username}"
        if bot_mention.lower() not in raw_text.lower():
            return
        # Strip the mention so the rest of the handler sees clean text
        effective_text = _re.sub(
            _re.escape(bot_mention), "", raw_text, flags=_re.IGNORECASE
        ).strip()
    else:
        effective_text = raw_text

    # ── Handle "@bot /tts text" mention-first pattern in groups ───────────────
    # Also handles plain "/tts text" that slipped past the Command handler
    if effective_text.lower().startswith("/tts"):
        from app.core.config import settings as _s
        if not _s.tts_enabled:
            await message.answer("🔇 TTS is currently disabled.")
            return
        body = _re.sub(r"^/tts(@\S+)?\s*", "", effective_text, flags=_re.IGNORECASE).strip()
        if body:
            await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
            await _send_voice_or_fallback(message, body)
        else:
            await state.set_state(TTSState.waiting_for_text)
            await message.answer(
                "🎙️ <b>TTS mode active!</b>\nSend me the text to speak.",
                parse_mode="HTML",
            )
        return

    # ── Ignore other unrecognised slash commands ───────────────────────────────
    if effective_text.startswith("/"):
        return

    from app.services.ai_service import ask_agent
    from app.repositories.mongodb.user_repository import user_repository

    # ── 4. TTS intent detection ────────────────────────────────────────────────
    from app.core.config import settings as _s
    if _s.tts_enabled:
        from app.services.tts_service import detect_tts_intent, TTSIntentKind

        tts_intent = detect_tts_intent(effective_text)

        if tts_intent.kind == TTSIntentKind.DIRECT_TTS:
            await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
            await _send_voice_or_fallback(message, tts_intent.text)
            return

        if tts_intent.kind == TTSIntentKind.AI_TTS:
            try:
                thinking_msg = await message.answer_sticker("CAACAgIAAxUAAWqDy_T--ZTKHa7kh8YqbDAAAeIqRwACKpoAAkJqIEhMY1khmFrSKz0E")
            except Exception:
                thinking_msg = await message.answer("💭 <i>Thinking...</i>", parse_mode="HTML")
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")

            try:
                user = await user_repository.get_by_telegram_id(message.from_user.id)
                lang = user.language if user and user.language else "en"
                _is_admin = (message.from_user.id == settings.telegram_admin_user_id)
                ai_text = await ask_agent(message.from_user.id, effective_text, lang=lang, is_admin=_is_admin)
                await thinking_msg.delete()
                await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
                await _send_voice_or_fallback(message, ai_text)
            except Exception as e:
                import logging
                logging.error(f"AI_TTS handler error for {message.from_user.id}: {e}")
                await thinking_msg.delete()
                await message.answer("⚠️ An unexpected error occurred. Please try again.")
            return

    # ── 5. Normal AI text response ────────────────────────────────────────────
    try:
        thinking_msg = await message.answer_sticker("CAACAgIAAxUAAWqDy_T--ZTKHa7kh8YqbDAAAeIqRwACKpoAAkJqIEhMY1khmFrSKz0E")
    except Exception:
        thinking_msg = await message.answer("💭 <i>Thinking...</i>", parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        from app.clients.telegram.keyboards import get_main_reply_keyboard
        from app.core.config import settings
        user = await user_repository.get_by_telegram_id(message.from_user.id)
        lang = user.language if user and user.language else "en"
        _is_admin = (message.from_user.id == settings.telegram_admin_user_id)

        response = await ask_agent(message.from_user.id, effective_text, lang=lang, is_admin=_is_admin)

        # Refetch user to get the latest language (in case the AI changed it)
        user_after = await user_repository.get_by_telegram_id(message.from_user.id)
        current_lang = user_after.language if user_after and user_after.language else "en"
        is_admin = _is_admin  # already computed above, reuse for keyboard

        import re
        img_match = re.search(r"\[IMAGE:\s*(.*?)\]", response, re.IGNORECASE | re.DOTALL)
        img_bytes = None
        if img_match:
            img_prompt = img_match.group(1).strip()
            response = response.replace(img_match.group(0), "").strip()
            from app.services.img_generator_service import img_generator_service
            import io
            # Let the user know we are painting something
            await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
            img_io = await img_generator_service.generate_image(img_prompt)
            if img_io:
                img_bytes = img_io.getvalue()
        
        await thinking_msg.delete()
        
        if img_bytes:
            await message.answer_photo(
                types.BufferedInputFile(img_bytes, filename="selfie.jpg"),
                caption=markdown_to_html(response) if response else "",
                parse_mode="HTML",
                reply_markup=get_main_reply_keyboard(is_admin, current_lang)
            )
        else:
            if response:
                await message.answer(
                    markdown_to_html(response), 
                    parse_mode="HTML",
                    reply_markup=get_main_reply_keyboard(is_admin, current_lang)
                )

    except Exception as e:
        import logging
        logging.error(f"Error in AI handler: {e}")
        await thinking_msg.delete()
        await message.answer("⚠️ An unexpected error occurred while communicating with the AI agent.", parse_mode="HTML")

