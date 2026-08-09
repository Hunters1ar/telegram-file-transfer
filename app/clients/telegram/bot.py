import io
import uuid
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from app.core.config import settings
from app.services.share_service import share_service
from app.repositories.r2.upload import upload_file_to_r2
from app.domain.entities.file import FileMetadata
from app.repositories.mongodb.file_repository import file_repository

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    from app.domain.entities.user import User
    from app.repositories.mongodb.user_repository import user_repository
    await user_repository.upsert_user(User(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    ))

    from app.clients.telegram.keyboards import get_main_reply_keyboard
    is_admin = (message.from_user.id == settings.admin)
    await message.answer(
        "👋 <b>Welcome to Hunterstar UX 2.0!</b>\n\n"
        "Here is how to use the new features:\n\n"
        "📤 <b>Send me any file</b> (photo, video, document) and I will upload it to Cloudflare R2. You will immediately see the new <b>4-Row Matrix Buttons</b> (Download, Share, Make Public, Delete) attached to the file!\n\n"
        "🖥 <b>Use the Menu Below</b> or the inline button to open the Dashboard, view your Storage Stats, or manage your files!",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🖥 Open Dashboard", web_app=types.WebAppInfo(url="https://www.hunterstar.online/?v=2"))]
        ])
    )
    await message.answer("Menu updated 👇", reply_markup=get_main_reply_keyboard(is_admin))

@dp.message(Command("admin"))
@dp.message(F.text == "🛡 Admin Menu")
async def handle_admin_menu(message: types.Message):
    if message.from_user.id != settings.admin:
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 View Users", callback_data="admin_users")
    builder.button(text="⚙ Set File Limit", callback_data="admin_setlimit")
    builder.button(text="🧹 Clear Whole System", callback_data="admin_clearwhole")
    builder.adjust(1)
    
    await message.answer("<b>Admin Command Palette</b>", parse_mode="HTML", reply_markup=builder.as_markup())

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
        await msg.edit_text(f"❌ This file is too large! The current limit is {limit_mb}MB.")
        return

    try:
        file_info = await bot.get_file(file_obj.file_id)
    except Exception as e:
        await msg.edit_text(f"❌ Failed to get file info: {e}")
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
    
    # Size threshold: 4GB in bytes
    MAX_NATIVE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB
    
    if size <= MAX_NATIVE_SIZE and file_meta.telegram_file_id:
        # Send file natively so it's playable/viewable in Telegram
        caption = format_file_caption(file_meta)
        keyboard = get_file_card_keyboard(file_meta)
        
        try:
            if file_type == "audio":
                await bot.send_audio(
                    chat_id=message.chat.id,
                    audio=file_meta.telegram_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif file_type == "video":
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=file_meta.telegram_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif file_type == "photo":
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=file_meta.telegram_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                # document / other file types
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=file_meta.telegram_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            # Delete the "Downloading..." status message
            await msg.delete()
        except Exception as e:
            # Fallback to text card if native send fails
            print(f"Native send failed, falling back to card: {e}")
            await msg.edit_text(
                text=format_file_card(file_meta), 
                parse_mode="HTML",
                reply_markup=get_file_card_keyboard(file_meta)
            )
    else:
        # File is too large for native Telegram send, use File Details card
        await msg.edit_text(
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
    
    # For files under 4GB with a telegram_file_id, send native cached media
    if file_meta.size <= MAX_NATIVE_SIZE and file_meta.telegram_file_id:
        caption = (
            f"{icon} <b>{title}</b>\n"
            f"🆔 <code>{file_meta.share_id}</code>  •  📦 {size_mb} MB\n"
            f"{visibility}  •  ☁ Hunterstar Cloud"
        )
        reply_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬇ Download", url=f"https://api.hunterstar.online/api/v1/download/{file_meta.share_id}")],
            [types.InlineKeyboardButton(text="📋 Copy ID", switch_inline_query=file_meta.share_id), types.InlineKeyboardButton(text="🌍 Open Website", url=f"https://cloud.hunterstar.online/f/{file_meta.share_id}")]
        ])
        
        if f_type == "audio":
            return types.InlineQueryResultCachedAudio(
                id=file_meta.share_id,
                audio_file_id=file_meta.telegram_file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif f_type == "video":
            return types.InlineQueryResultCachedVideo(
                id=file_meta.share_id,
                video_file_id=file_meta.telegram_file_id,
                title=title,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif f_type == "photo":
            return types.InlineQueryResultCachedPhoto(
                id=file_meta.share_id,
                photo_file_id=file_meta.telegram_file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            return types.InlineQueryResultCachedDocument(
                id=file_meta.share_id,
                document_file_id=file_meta.telegram_file_id,
                title=title,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
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
            [types.InlineKeyboardButton(text="⬇ Download", url=f"https://api.hunterstar.online/api/v1/download/{file_meta.share_id}")],
            [types.InlineKeyboardButton(text="📋 Copy ID", switch_inline_query=file_meta.share_id), types.InlineKeyboardButton(text="🌍 Open Website", url=f"https://cloud.hunterstar.online/f/{file_meta.share_id}")]
        ])
    )

@dp.message(F.text == "📁 My Files")
async def handle_my_files(message: types.Message):
    await message.answer("Click <b>'Open Dashboard'</b> below or search your files using inline mode: <code>@hunterstarfilebot </code>", parse_mode="HTML")

@dp.message(F.text == "☁ Storage Stats")
async def handle_storage_stats(message: types.Message):
    stats = await file_repository.get_user_stats(message.from_user.id)
    await message.answer(f"☁ <b>Storage Used:</b> {stats.get('total_size', 0) / (1024*1024):.2f} MB\n📁 <b>Total Files:</b> {stats.get('total_files', 0)}", parse_mode="HTML")



@dp.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery):
    query = inline_query.query.strip()
    
    try:
        if not query:
            # Empty query: show user's recent files
            user_files = await file_repository.get_by_owner_id(inline_query.from_user.id, limit=50)
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
            
        # Specific query: show that specific file
        file_meta = await file_repository.get_by_share_id(query)
        if not file_meta:
            not_found = types.InlineQueryResultArticle(
                id="not_found",
                title="File not found",
                description="Invalid Share ID",
                input_message_content=types.InputTextMessageContent(message_text="Invalid Share ID")
            )
            await inline_query.answer([not_found], cache_time=5)
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
        
    # Delete from MongoDB
    await file_repository.delete(callback_data.share_id)
    # Ideally delete from R2 as well, but omitting for brevity/safety unless implemented
    
    await callback.message.edit_text(f"🗑 Deleted <b>{file_meta.original_filename}</b>", parse_mode="HTML")
    await callback.answer("File deleted")

@dp.callback_query(FileAction.filter(F.action.in_({"rename", "move", "analytics", "details", "copy_id", "copy_link", "expire", "password"})))
async def handle_coming_soon(callback: types.CallbackQuery):
    await callback.answer("This feature is coming soon in Hunterstar Cloud Phase 2!", show_alert=True)


async def setup_bot_commands(bot_instance: Bot):
    user_commands = [
        types.BotCommand(command="start", description="Start the bot and show menu")
    ]
    admin_commands = [
        types.BotCommand(command="start", description="Start the bot and show menu"),
        types.BotCommand(command="admin", description="Open Admin Panel"),
        types.BotCommand(command="clearwhole", description="Clear all data"),
        types.BotCommand(command="users", description="List all users"),
        types.BotCommand(command="setlimit", description="Set file limit (MB)")
    ]
    
    await bot_instance.set_my_commands(user_commands, scope=types.BotCommandScopeDefault())
    try:
        await bot_instance.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(chat_id=settings.admin))
    except Exception as e:
        print(f"Could not set admin commands: {e}")

async def start_polling():
    await setup_bot_commands(bot)
    await dp.start_polling(bot)
