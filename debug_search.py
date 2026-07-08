"""
debug_search.py — проверяем что умеет Pyrogram search_global
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

async def main():
    from pyrogram import Client
    from pyrogram.enums import ChatType

    async with Client(
        "freelance_session",
        api_id=API_ID, api_hash=API_HASH,
        workdir="data",
    ) as app:
        print("=== Тест 1: search_global('фриланс заказы') ===")
        count = 0
        try:
            async for chat in app.search_global("фриланс заказы", limit=10):
                print(f"  type={chat.__class__.__name__} | {getattr(chat,'username','—')} | {getattr(chat,'title','—')} | members={getattr(chat,'members_count','?')}")
                count += 1
        except Exception as e:
            print(f"  ОШИБКА: {e}")
        print(f"  Итого: {count}\n")

        print("=== Тест 2: search_global('freelance jobs') ===")
        count = 0
        try:
            async for chat in app.search_global("freelance jobs", limit=10):
                print(f"  type={chat.__class__.__name__} | {getattr(chat,'username','—')} | {getattr(chat,'title','—')}")
                count += 1
        except Exception as e:
            print(f"  ОШИБКА: {e}")
        print(f"  Итого: {count}\n")

        print("=== Тест 3: get_dialogs (свои каналы) ===")
        count = 0
        try:
            async for dialog in app.get_dialogs():
                if dialog.chat.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                    print(f"  @{dialog.chat.username} | {dialog.chat.title} | members={getattr(dialog.chat,'members_count','?')}")
                    count += 1
                    if count >= 15:
                        break
        except Exception as e:
            print(f"  ОШИБКА: {e}")
        print(f"  Итого диалогов-каналов: {count}")

asyncio.run(main())
