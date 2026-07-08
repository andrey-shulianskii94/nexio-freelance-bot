"""
auth_telegram.py — РАЗОВЫЙ скрипт входа в Telegram под личным аккаунтом.
Запускается ОДИН РАЗ. Создаёт файл сессии data/andrey_session.session —
после этого бот подключается сам, без повторного входа.
"""

import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
PHONE = os.getenv("TG_PHONE")

SESSION_PATH = "data/andrey_session"


def main():
    if not API_ID or not API_HASH or not PHONE:
        print("❌ Не заполнены TG_API_ID / TG_API_HASH / TG_PHONE в .env")
        return

    os.makedirs("data", exist_ok=True)

    print("Подключаюсь к Telegram...")
    print(f"Номер: {PHONE}")
    print("-" * 50)

    with TelegramClient(SESSION_PATH, int(API_ID), API_HASH) as client:
        client.start(phone=PHONE)
        me = client.get_me()
        username = f"@{me.username}" if me.username else "(без username)"
        print("-" * 50)
        print(f"✅ Успешный вход: {me.first_name} {username}")
        print(f"✅ Файл сессии сохранён: {SESSION_PATH}.session")
        print("Дальше можно закрыть окно — сессия сохранена.")


if __name__ == "__main__":
    main()