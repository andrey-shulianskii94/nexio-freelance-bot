"""
debug_channels.py — смотрим реальные тексты из каналов чтобы подобрать маркеры
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

# Каналы которые должны были попасть в список но не попали
TARGET_CHANNELS = [
    "aiogram_jobs", "django_jobs_board", "freelance_orders",
    "freelance_tg", "it_remote", "it_vacancy", "marketplace_jobs",
    "ozon_jobs", "avito_jobs", "python_freelance",
]

async def main():
    from pyrogram import Client
    async with Client(
        "freelance_session",
        api_id=API_ID, api_hash=API_HASH,
        workdir="data",
    ) as app:
        for ch in TARGET_CHANNELS:
            print(f"\n{'='*60}")
            print(f"@{ch}")
            print(f"{'='*60}")
            count = 0
            try:
                async for msg in app.get_chat_history(ch, limit=3):
                    if msg.text:
                        # Первые 200 символов каждого сообщения
                        print(f"  MSG: {msg.text[:200].strip()}")
                        print()
                        count += 1
            except Exception as e:
                print(f"  ОШИБКА: {e}")
            if count == 0:
                print("  (нет текстовых сообщений)")

asyncio.run(main())
