"""
telegram_parser.py
==================
Этап 1 — парсинг публичных каналов через t.me/s/ (без авторизации).
Этап 2 — чтение каналов где состоит пользователь через Pyrogram (read-only).
"""

import os
import time
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from filters.classifier import classify_message, get_reply_template
from dotenv import load_dotenv

HOURS_LIMIT = 72  # читаем только сообщения за последние 72 часа

load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TG_API_ID    = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH  = os.getenv("TG_API_HASH", "")
TG_PHONE     = os.getenv("TG_PHONE", "")

# ─── Список каналов для парсинга через t.me/s/ ───────────────────────────────
# Только проверенные RU-каналы с реальными фриланс-заказами
ALL_CHANNELS = [
    # Общий фриланс / биржи заказов
    "freelance_orders", "freelance_tg", "freelance_ru", "freelancejobs_ru",
    "kanal_freelance", "workforme_ru", "freelance_birga",

    # Python / боты / автоматизация
    "aiogram_jobs", "python_freelance", "botmakers", "django_jobs_board",
    "bot_freelance", "bot_jobs",

    # IT вакансии / удалёнка (проверенные)
    "it_remote", "it_vacancy", "it_job_talks",

    # Парсинг / данные
    "avito_jobs",

    # Маркетплейсы / контент
    "marketplace_jobs", "ozon_jobs",

    # Дизайн
    "designjobs",

    # QA
    "qa_guru",
]


# ─── Bot API helper ──────────────────────────────────────────────────────────

def send_telegram_notification(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception:
        pass


# ─── Этап 1: парсинг через t.me/s/ (публичные каналы) ───────────────────────

def parse_channel_public(channel: str) -> list:
    """Парсит один публичный канал через t.me/s/"""
    results = []
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        messages  = soup.find_all("div", class_="tgme_widget_message_text")
        msg_wraps = soup.find_all("div", class_="tgme_widget_message_wrap")

        for i, msg in enumerate(messages):
            text = msg.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue

            msg_type = classify_message(text)
            if msg_type == "SPAM":
                continue

            msg_link = ""
            if i < len(msg_wraps):
                link_tag = msg_wraps[i].find("a", class_="tgme_widget_message_date")
                if link_tag:
                    msg_link = link_tag.get("href", "")

            reply = get_reply_template(msg_type)

            results.append({
                "platform": "Telegram",
                "channel":  channel,
                "type":     msg_type,
                "text":     text,
                "reply":    reply,
                "link":     msg_link,
                "status":   "новый",
                "amount":   "",
            })

    except Exception:
        pass

    return results


def parse_telegram_public() -> list:
    """Этап 1 — парсит все каналы из ALL_CHANNELS через t.me/s/"""
    all_results = []
    for channel in ALL_CHANNELS:
        results = parse_channel_public(channel)
        all_results.extend(results)
        time.sleep(0.3)  # пауза чтобы не спамить
    return all_results


# ─── Этап 2: парсинг через Pyrogram (каналы где состоит пользователь) ────────

def parse_telegram_userbot(joined_channels: list = None) -> list:
    """
    Этап 2 — читает сообщения из каналов где состоит пользователь.
    Бот только читает, не пишет — read-only, не нарушает ToS Telegram.

    joined_channels: список username каналов. Если None — читает все диалоги.
    """
    try:
        from pyrogram import Client
        from pyrogram.enums import ChatType
    except ImportError:
        send_telegram_notification(
            "⚠️ Pyrogram не установлен. Выполни: pip install pyrogram"
        )
        return []

    results = []

    async def _fetch():
        async with Client(
            "freelance_session",
            api_id=TG_API_ID,
            api_hash=TG_API_HASH,
            phone_number=TG_PHONE,
            workdir="data",
        ) as app:
            # Если список не задан — берём все каналы/группы из диалогов
            if joined_channels:
                targets = joined_channels
            else:
                targets = []
                async for dialog in app.get_dialogs():
                    if dialog.chat.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                        targets.append(dialog.chat.username or dialog.chat.id)

            cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_LIMIT)

            for target in targets:
                try:
                    async for message in app.get_chat_history(target, limit=200):
                        if not message.text:
                            continue
                        # Фильтр по времени — пропускаем старше 72 часов
                        if message.date and message.date < cutoff:
                            break  # история отсортирована по убыванию — дальше только старее
                        text = message.text
                        if len(text) < 20:
                            continue
                        msg_type = classify_message(text)
                        if msg_type == "SPAM":
                            continue

                        link = f"https://t.me/{target}/{message.id}" if isinstance(target, str) else ""
                        reply = get_reply_template(msg_type)

                        results.append({
                            "platform": "Telegram",
                            "channel":  str(target),
                            "type":     msg_type,
                            "text":     text,
                            "reply":    reply,
                            "link":     link,
                            "status":   "новый",
                            "amount":   "",
                        })
                    await asyncio.sleep(0.5)
                except Exception:
                    continue

    asyncio.run(_fetch())
    return results


# ─── Единая точка входа ──────────────────────────────────────────────────────

def parse_telegram(use_userbot: bool = False, joined_channels: list = None) -> list:
    """
    use_userbot=False → Этап 1 (публичные каналы, без авторизации)
    use_userbot=True  → Этап 2 (Pyrogram, каналы где состоит пользователь)
    """
    if use_userbot:
        return parse_telegram_userbot(joined_channels)
    return parse_telegram_public()
