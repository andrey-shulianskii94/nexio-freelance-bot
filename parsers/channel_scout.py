"""
channel_scout.py — умный поиск каналов через Pyrogram
======================================================
Ищет каналы по ключевым словам прямо внутри Telegram (не через t.me/s/).
Работает для RU, EN, ES — находит закрытые каналы которые краулер не видит.

Фильтры:
  1. Подписчики >= MIN_MEMBERS (по умолчанию 500)
  2. Последние сообщения содержат слова-маркеры фриланса
  3. Не полная занятость (нет слов офис/оклад/трудоустройство)
"""

import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

MIN_MEMBERS = 500   # меньше — мёртвый или спам-канал

# Слова которые должны быть в последних сообщениях канала
FREELANCE_MARKERS = [
    # RU
    "ищу", "нужен", "нужна", "заказ", "бюджет", "оплата", "удалённо",
    "удаленно", "фриланс", "исполнитель", "проект", "тз", "техзадание",
    "предоплата", "срок", "кворк", "fl.ru",
    # EN
    "looking for", "hire", "hiring", "freelance", "remote", "budget",
    "job", "project", "developer needed", "need a", "payment",
    # ES
    "busco", "necesito", "freelance", "remoto", "pago", "proyecto",
]

# Слова которые говорят — это канал с полной занятостью, не фриланс
FULLTIME_MARKERS = [
    "оклад", "в офис", "офисная", "трудоустройство", "трудовой договор",
    "официальное", "испытательный срок", "full-time", "full time",
    "office", "salary", "employment contract",
]

# Ключевые слова для поиска каналов по языкам
SEARCH_QUERIES = {
    "RU": [
        "фриланс заказы", "python заказы", "бот заказы", "парсер заказы",
        "разработка заказы", "it фриланс", "удалённая работа it",
        "telegram бот заказы", "wordpress заказы", "маркетплейс заказы",
    ],
    "EN": [
        "freelance jobs", "remote python jobs", "telegram bot jobs",
        "developer jobs remote", "freelance developer", "hire python",
        "remote work developer", "bot development jobs",
    ],
    "ES": [
        "freelance trabajo", "trabajo remoto programacion",
        "busco desarrollador", "proyecto python remoto",
    ],
}

FOUND_SCOUT_FILE = "data/scout_channels.json"


def _load_scout() -> dict:
    try:
        with open(FOUND_SCOUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_scout(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(FOUND_SCOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _scout_async(on_progress=None) -> dict:
    from pyrogram import Client
    from pyrogram.enums import ChatType
    from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelPrivate

    results = {}

    async with Client(
        "freelance_session",
        api_id=API_ID,
        api_hash=API_HASH,
        workdir="data",
    ) as app:

        all_queries = []
        for lang, queries in SEARCH_QUERIES.items():
            for q in queries:
                all_queries.append((lang, q))

        for i, (lang, query) in enumerate(all_queries):
            if on_progress:
                on_progress(i + 1, len(all_queries), f"🔍 [{lang}] {query}")

            try:
                async for chat in app.search_global(query, limit=20):
                    try:
                        if not hasattr(chat, "username") or not chat.username:
                            continue
                        if chat.type not in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                            continue

                        username = chat.username.lower()
                        if username in results:
                            continue

                        members = getattr(chat, "members_count", 0) or 0
                        if members < MIN_MEMBERS:
                            continue

                        # Проверяем последние сообщения на фриланс-маркеры
                        recent_text = ""
                        msg_count = 0
                        try:
                            async for msg in app.get_chat_history(chat.username, limit=15):
                                if msg.text:
                                    recent_text += " " + msg.text.lower()
                                    msg_count += 1
                        except Exception:
                            pass

                        # Если нет сообщений — пропускаем
                        if msg_count == 0:
                            continue

                        has_freelance = any(m in recent_text for m in FREELANCE_MARKERS)
                        has_fulltime  = any(m in recent_text for m in FULLTIME_MARKERS)

                        if not has_freelance or has_fulltime:
                            continue

                        results[username] = {
                            "username": username,
                            "title":    getattr(chat, "title", ""),
                            "members":  members,
                            "lang":     lang,
                            "link":     f"https://t.me/{username}",
                            "joined":   False,
                            "verified": True,
                        }

                    except (ChatAdminRequired, ChannelPrivate):
                        continue
                    except Exception:
                        continue

                await asyncio.sleep(1.5)  # пауза между запросами

            except FloodWait as e:
                if on_progress:
                    on_progress(i + 1, len(all_queries), f"⏳ FloodWait {e.value}s...")
                await asyncio.sleep(e.value)
            except Exception:
                await asyncio.sleep(2)
                continue

    return results


def run_scout(on_progress=None) -> dict:
    """Синхронная обёртка. Возвращает словарь найденных каналов."""
    existing = _load_scout()

    loop = asyncio.new_event_loop()
    try:
        new_channels = loop.run_until_complete(_scout_async(on_progress))
    finally:
        loop.close()

    # Мержим с существующими
    existing.update(new_channels)
    _save_scout(existing)
    return existing
