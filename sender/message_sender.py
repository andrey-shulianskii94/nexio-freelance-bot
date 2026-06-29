from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import asyncio
import time
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
PHONE = os.getenv("TG_PHONE")

client = TelegramClient("freelance_session", API_ID, API_HASH)


async def send_message(sender_id: int, text: str) -> bool:
    """
    Отправляет сообщение пользователю в Telegram.
    Возвращает True если успешно, False если ошибка.
    """
    try:
        async with client:
            await client.send_message(sender_id, text)
            # Пауза между сообщениями чтобы не словить бан
            await asyncio.sleep(3)
            return True
    except FloodWaitError as e:
        time.sleep(e.seconds)
        return False
    except Exception:
        return False


def send_message_sync(sender_id: int, text: str) -> bool:
    """Синхронная обёртка для вызова из tkinter"""
    return asyncio.run(send_message(sender_id, text))
