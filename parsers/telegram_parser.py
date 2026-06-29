import requests
from bs4 import BeautifulSoup
from filters.classifier import classify_message, get_reply_template
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

TG_CHANNELS = [
    "freelance_ru", "python_jobs", "tg_jobs", "freelance_hayr",
    "workforme_ru", "it_jobs_ru", "botmakers", "django_jobs",
    "web_python_jobs", "freelance_python", "smm_jobs_ru", "content_jobs_ru"
]

def send_telegram_notification(text: str):
    """Отправляет уведомление боту в личку"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def parse_channel(channel: str) -> list:
    """Парсит один канал через t.me/s/"""
    results = []
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return results
        
        soup = BeautifulSoup(resp.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        msg_wraps = soup.find_all("div", class_="tgme_widget_message_wrap")
        
        for i, msg in enumerate(messages):
            text = msg.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue
            
            msg_type = classify_message(text)
            if msg_type == "SPAM":
                continue
            
            # Получаем ссылку на сообщение
            msg_link = ""
            if i < len(msg_wraps):
                link_tag = msg_wraps[i].find("a", class_="tgme_widget_message_date")
                if link_tag:
                    msg_link = link_tag.get("href", "")
            
            reply = get_reply_template(msg_type)
            emoji = "🟢" if msg_type == "HOT" else "🔵"
            label = "ГОРЯЧИЙ" if msg_type == "HOT" else "ХОЛОДНЫЙ"
            
            results.append({
                "platform": "Telegram",
                "channel": channel,
                "type": msg_type,
                "text": text[:300],
                "reply": reply,
                "link": msg_link,
                "status": "новый",
                "amount": ""
            })
            
            # Отправляем уведомление в Telegram
            notification = (
                f"{emoji} <b>{label}</b> | @{channel}\n\n"
                f"{text[:200]}\n\n"
                f"📋 <b>Готовый отклик:</b>\n"
                f"{reply}\n\n"
                f"🔗 <a href='{msg_link}'>Открыть сообщение</a>"
            )
            send_telegram_notification(notification)
            
    except Exception:
        pass
    
    return results

def parse_telegram() -> list:
    """Парсит все каналы из списка"""
    all_results = []
    for channel in TG_CHANNELS:
        results = parse_channel(channel)
        all_results.extend(results)
    return all_results