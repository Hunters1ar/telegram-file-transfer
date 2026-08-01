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
    from app.clients.telegram.keyboards import get_main_reply_keyboard
    await message.answer(
        "👋 <b>Welcome to Hunterstar UX 2.0!</b>\n\n"
        "Here is how to use the new features:\n\n"
        "📤 <b>Send me any file</b> (photo, video, document) and I will upload it to Cloudflare R2. You will immediately see the new <b>4-Row Matrix Buttons</b> (Download, Share, Make Public, Delete) attached to the file!\n\n"
        "🖥 <b>Use the Menu Below</b> to open the Dashboard, view your Storage Stats, or manage your files!",
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard()
    )

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
    
    # Telegram Bot API limit is 20MB for download without a local server.
    if size > 20 * 1024 * 1024:
        await msg.edit_text("❌ This file is too large! The standard Telegram Bot API limits downloads to 20MB. Please test with a smaller file (like a photo or small document) for now.")
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
    from app.clients.telegram.messages import format_file_card

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
    
    # Respond with File Card
    await msg.edit_text(
        text=format_file_card(file_meta), 
        parse_mode="HTML",
        reply_markup=get_file_card_keyboard(file_meta)
    )

def get_inline_result(file_meta):
    f_type = file_meta.file_type or "document"
    title = file_meta.original_filename
    
    if f_type == "photo":
        return types.InlineQueryResultCachedPhoto(
            id=file_meta.share_id,
            photo_file_id=file_meta.telegram_file_id,
            title=title,
            caption=title
        )
    elif f_type == "video":
        return types.InlineQueryResultCachedVideo(
            id=file_meta.share_id,
            video_file_id=file_meta.telegram_file_id,
            title=title,
            caption=title
        )
    elif f_type == "audio":
        return types.InlineQueryResultCachedAudio(
            id=file_meta.share_id,
            audio_file_id=file_meta.telegram_file_id,
            caption=title
        )
    else:
        return types.InlineQueryResultCachedDocument(
            id=file_meta.share_id,
            document_file_id=file_meta.telegram_file_id,
            title=title,
            caption=title
        )

@dp.message(F.text == "📁 My Files")
async def handle_my_files(message: types.Message):
    await message.answer("Click <b>'Open Dashboard'</b> below or search your files using inline mode: <code>@hunterstarfilebot </code>", parse_mode="HTML")

@dp.message(F.text == "☁ Storage Stats")
async def handle_storage_stats(message: types.Message):
    stats = await file_repository.get_user_stats(message.from_user.id)
    await message.answer(f"☁ <b>Storage Used:</b> {stats.get('total_size', 0) / (1024*1024):.2f} MB\n📁 <b>Total Files:</b> {stats.get('total_files', 0)}", parse_mode="HTML")

@dp.message(F.text == "⚙ Settings" or F.text == "⭐ Premium")
async def handle_coming_soon_menu(message: types.Message):
    await message.answer("🚧 This feature is coming soon in Phase 2!")

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

@dp.callback_query(FileAction.filter(F.action.in_({"rename", "move", "analytics"})))
async def handle_coming_soon(callback: types.CallbackQuery):
    await callback.answer("This feature is coming soon in UX 2.0 Phase 2!", show_alert=True)


async def start_polling():
    await dp.start_polling(bot)
