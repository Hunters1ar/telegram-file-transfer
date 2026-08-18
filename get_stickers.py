import asyncio
import json
from aiogram import Bot

BOT_TOKEN = "7336214068:AAE_x6X7F2aKx_gZ2pMv5zYw9zHq_T7E_2A"

async def main():
    from app.core.config import settings
    bot = Bot(token=settings.bot_token)
    try:
        sticker_set = await bot.get_sticker_set("hunterstar")
        res = []
        for sticker in sticker_set.stickers:
            res.append({"file_id": sticker.file_id, "emoji": sticker.emoji})
        with open("stickers.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error:", e)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
