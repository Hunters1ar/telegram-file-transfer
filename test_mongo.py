import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def test():
    print('Testing without certifi...')
    client = AsyncIOMotorClient(settings.mongodb_uri)
    try:
        await client.admin.command('ping')
        print('Success without certifi!')
    except Exception as e:
        print('Failed without certifi:', e)

    print('Testing with certifi...')
    client2 = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    try:
        await client2.admin.command('ping')
        print('Success with certifi!')
    except Exception as e:
        print('Failed with certifi:', e)

asyncio.run(test())
