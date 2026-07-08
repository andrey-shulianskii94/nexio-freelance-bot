"""
sender.py — отправка ответа заказчику через Pyrogram userbot
=============================================================
Вызывается из GUI по кнопке «Отправить».
Извлекает username канала из ссылки и отправляет туда сообщение.
"""

import os
import asyncio
import re
from dotenv import load_dotenv

load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")


def _extract_target(link: str) -> str | None:
    """
    Из ссылки вида:
      https://t.me/channel_name/123
      https://t.me/channel_name
    возвращает '@channel_name' или None если не удалось.
    """
    m = re.search(r"t\.me/([A-Za-z0-9_]+)", link)
    if m:
        return "@" + m.group(1)
    return None


async def _send_async(link: str, text: str) -> str:
    """Отправляет text в канал/чат из link. Возвращает строку-результат."""
    from pyrogram import Client

    target = _extract_target(link)
    if not target:
        return f"❌ Не удалось определить канал из ссылки: {link}"

    try:
        async with Client(
            "freelance_session",
            api_id=API_ID,
            api_hash=API_HASH,
            workdir="data",
        ) as app:
            await app.send_message(target, text)
            return f"✅ Отправлено в {target}"
    except Exception as e:
        return f"❌ Ошибка отправки в {target}: {e}"


def send_reply(link: str, text: str) -> str:
    """
    Синхронная обёртка для вызова из tkinter.
    Возвращает строку с результатом.
    """
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_send_async(link, text))
        loop.close()
        return result
    except Exception as e:
        return f"❌ Критическая ошибка: {e}"
