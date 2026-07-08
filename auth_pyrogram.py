"""
auth_pyrogram.py
================
РАЗОВЫЙ скрипт авторизации через Pyrogram (read-only userbot).
Запускается ОДИН РАЗ - создаёт файл data/freelance_session.session
После этого бот подключается сам без повторного входа.

Запуск: python auth_pyrogram.py
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
PHONE    = os.getenv("TG_PHONE", "")


async def main():
    # Фикс для Python 3.14 — создаём event loop явно
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    from pyrogram import Client

    if not API_ID or not API_HASH or not PHONE:
        print("Не заполнены TG_API_ID / TG_API_HASH / TG_PHONE в .env")
        return

    print("=" * 50)
    print("  Авторизация Pyrogram (read-only userbot)")
    print("=" * 50)
    print(f"Номер: {PHONE}")
    print("Код придёт в Telegram на телефон (не SMS)")
    print("-" * 50)

    async with Client(
        "freelance_session",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE,
        workdir="data",
    ) as app:
        me = await app.get_me()
        print("-" * 50)
        print(f"Успешный вход: {me.first_name} @{me.username}")
        print(f"Сессия сохранена: data/freelance_session.session")
        print("Перезапусти main.py - бот будет читать каналы через userbot.")


if __name__ == "__main__":
    asyncio.run(main())
