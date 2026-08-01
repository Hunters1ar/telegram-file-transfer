import io
import uuid
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from app.core.config import settings
from app.services.share_service import share_service
from app.repositories.r2.upload import upload_file_to_r2
from app.domain.entities.file import FileMetadata
from app.repositories.mongodb.file_repository import file_repository

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer("Hello! Send me any file, and I will upload it to Cloudflare R2 and give you a Share ID.")

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

async def start_polling():
    await dp.start_polling(bot)
