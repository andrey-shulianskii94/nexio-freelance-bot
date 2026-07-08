"""
debug_scan.py — запускает _scan изолированно, без GUI.
Показывает точную ошибку если есть.

Запуск: python debug_scan.py
"""
import asyncio, os, sys, traceback
from dotenv import load_dotenv

load_dotenv()
API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

print(f"API_ID={API_ID}, API_HASH={'***' if API_HASH else 'НЕ ЗАДАН!'}")
print(f"Сессия: data/freelance_session.session")
print(f"Файл существует: {os.path.exists('data/freelance_session.session')}")
print("-" * 60)

async def test_scan():
    from pyrogram import Client
    from pyrogram.enums import ChatType

    print("Подключаюсь к Telegram...")
    try:
        async with Client(
            "freelance_session",
            api_id=API_ID,
            api_hash=API_HASH,
            workdir="data"
        ) as app:
            me = await app.get_me()
            print(f"✅ Сессия активна: {me.first_name} (@{me.username})")

            chats = []
            print("Загружаю диалоги...")
            async for d in app.get_dialogs():
                c = d.chat
                if c.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                    chats.append(c)

            print(f"Каналов/групп найдено: {len(chats)}")
            if chats:
                print("Первые 5:")
                for c in chats[:5]:
                    print(f"  - {c.title} (@{getattr(c,'username','?')}) [{getattr(c,'members_count',0)} подп.]")
            else:
                print("❌ Диалогов 0 — сессия есть, но каналов нет (или нет прав)")

    except Exception:
        print("❌ ОШИБКА:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scan())
