"""
main.py — Freelance Bot
=======================
Этап 1: USE_USERBOT = False  → парсинг публичных каналов через t.me/s/
Этап 2: USE_USERBOT = True   → Pyrogram, читаем каналы где состоит пользователь
"""

import ctypes
import sys

# ─── DPI-aware: убирает размытие шрифтов на HiDPI-экранах Windows ───────────
try:
    if sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI v2
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import threading
import time
import json
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from parsers.telegram_parser import parse_telegram, send_telegram_notification
from export.excel_export import export_to_excel
from gui.window import FreelanceWindow
from gui.splash import SplashScreen
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN     = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ─── Переключатель этапов ────────────────────────────────────────────────────
# Этап 1 (по умолчанию): публичные каналы, авторизация не нужна
# Этап 2: поменяй на True после того как вступил во все каналы
USE_USERBOT = True

# Список каналов для Этапа 2 (заполни после вступления)
# Оставь пустым [] чтобы читать все диалоги автоматически
JOINED_CHANNELS = []

daily_results    = []
window           = None
_pending_results = []
_last_update_id  = 0

SEEN_CACHE_FILE = "data/seen_messages.json"

def _load_seen_cache() -> set:
    """Загружает кеш уже виденных сообщений из файла."""
    try:
        with open(SEEN_CACHE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def _save_seen_cache(seen: set):
    """Сохраняет кеш в файл."""
    os.makedirs("data", exist_ok=True)
    try:
        # Ограничиваем размер кеша — храним только последние 5000 ключей
        keys = list(seen)
        if len(keys) > 5000:
            keys = keys[-5000:]
        with open(SEEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, ensure_ascii=False)
    except Exception:
        pass


# ─── Telegram Bot API helpers ────────────────────────────────────────────────

def _tg(method: str, payload: dict) -> dict:
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload, timeout=10)
        return r.json()
    except Exception:
        return {}


def send_with_buttons(text: str, buttons: list):
    keyboard = {"inline_keyboard": [buttons]}
    _tg("sendMessage", {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
        "disable_web_page_preview": True,
    })


def answer_callback(callback_query_id: str, text: str = ""):
    _tg("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
    })


def send_results_batch(results: list, offset: int, batch_size: int):
    total = len(results)
    end   = min(offset + batch_size, total)
    chunk = results[offset:end]

    for item in chunk:
        sm    = item.get("status_match", "")
        emoji = "🟢" if sm == "MATCHED" else "🟡"
        cat   = item.get("category", "Общий запрос")
        pct   = item.get("match_percent", 0)
        text  = item.get("text", "")[:600]
        link  = item.get("link", "")

        cat_line = (f"🔍 Категория: {cat} (совпадение {pct}%)"
                    if pct > 0 else f"🔍 {cat}")

        notification = (
            f"{emoji} [TG] {item.get('channel','')}\n"
            f"{cat_line}\n\n"
            f"{text}\n\n"
            f"🔗 <a href='{link}'>Открыть объявление</a>"
        )

        if len(notification) > 4090:
            notification = notification[:4087] + "…"

        send_telegram_notification(notification)
        time.sleep(0.5)

    remaining = total - end
    if remaining > 0:
        _offer_next_batch(end, remaining, total)


def _offer_next_batch(offset: int, remaining: int, total: int):
    buttons = []
    for size in [10, 20, 30]:
        if size <= remaining:
            buttons.append({
                "text": f"Следующие {size}",
                "callback_data": f"send:{size}:{offset}"
            })
    if remaining not in [10, 20, 30]:
        buttons.append({
            "text": f"Оставшиеся {remaining}",
            "callback_data": f"send:{remaining}:{offset}"
        })
    buttons.append({
        "text": f"📋 Все {remaining}",
        "callback_data": f"send:{remaining}:{offset}"
    })
    text = f"Показано {offset} из {total}. Ещё {remaining} заявок:"
    send_with_buttons(text, buttons[:4])


def _send_initial_buttons(results: list):
    total = len(results)
    if total == 0:
        return
    sizes   = [s for s in [10, 20, 30] if s < total]
    buttons = [{"text": str(s), "callback_data": f"send:{s}:0"} for s in sizes]
    buttons.append({"text": f"📋 Все {total}", "callback_data": f"send:{total}:0"})
    text = (
        f"✅ <b>Поиск завершён</b>\n"
        f"Найдено заявок: <b>{total}</b>\n"
        f"Сколько показать прямо сейчас?"
    )
    send_with_buttons(text, buttons[:4])


# ─── Polling inline-кнопок ───────────────────────────────────────────────────

def _poll_callbacks():
    global _last_update_id, _pending_results
    while True:
        try:
            data = _tg("getUpdates", {
                "offset": _last_update_id + 1,
                "timeout": 2,
                "allowed_updates": ["callback_query"],
            })
            updates = data.get("result", [])
            for upd in updates:
                _last_update_id = upd["update_id"]
                cq = upd.get("callback_query")
                if not cq:
                    continue
                answer_callback(cq["id"])
                cd = cq.get("data", "")
                if cd.startswith("send:"):
                    parts = cd.split(":")
                    if len(parts) == 3:
                        batch_size = int(parts[1])
                        offset     = int(parts[2])
                        if _pending_results:
                            send_results_batch(_pending_results, offset, batch_size)
        except Exception:
            pass
        time.sleep(2)


# ─── Основная логика ─────────────────────────────────────────────────────────

def run_search():
    global daily_results, window, _pending_results

    mode = "Pyrogram (твои каналы)" if USE_USERBOT else "публичные каналы"
    send_telegram_notification(f"🔎 Запускаю поиск заданий... [{mode}]")

    if window:
        window.set_status(f"🔎 Поиск в Telegram [{mode}]...")

    new_results = parse_telegram(
        use_userbot=USE_USERBOT,
        joined_channels=JOINED_CHANNELS if JOINED_CHANNELS else None,
    )

    seen = _load_seen_cache()
    # также добавляем ключи из текущей сессии (на случай двойного запуска)
    for r in daily_results:
        seen.add(r.get("channel", "") + str(r.get("text", "")[:80]))

    added = 0
    for item in new_results:
        key = item.get("channel", "") + str(item.get("text", "")[:80])
        if key not in seen:
            daily_results.append(item)
            seen.add(key)
            added += 1

    _save_seen_cache(seen)

    _pending_results = list(daily_results)

    hot  = sum(1 for r in daily_results
               if r.get("status_match") == "MATCHED" or r.get("type") == "HOT")
    cold = sum(1 for r in daily_results
               if r.get("status_match") == "UNCERTAIN" or r.get("type") == "COLD")

    if window:
        window.update_results(daily_results)
        window.set_status(f"✅ Новых: {added} | Всего: {len(daily_results)}")

    if added > 0:
        _send_initial_buttons(_pending_results)
    else:
        send_telegram_notification(
            f"✅ Поиск завершён\n"
            f"Новых: {added} | Всего за день: {len(daily_results)}\n"
            f"🟢 Точных: {hot} | 🟡 Похожих: {cold}"
        )


def export_daily():
    global daily_results
    export_to_excel(daily_results)
    send_telegram_notification("📊 Excel выгрузка за день сохранена")

    try:
        from gui.window import load_daily_results, save_daily_results
        data = load_daily_results()
        cleaned = {k: v for k, v in data.items()
                   if not any(s in v.get("status", "")
                              for s in ("Выполнено", "Отказ", "Отклонили"))}
        completed = len(data) - len(cleaned)
        save_daily_results(cleaned)
        if completed:
            send_telegram_notification(
                f"🧹 Ночная очистка: убрано {completed} завершённых проектов")
    except Exception:
        pass

    daily_results = []


def on_send(item: dict):
    pass


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_search, 'interval', hours=1)
    scheduler.add_job(export_daily, 'cron', hour=0, minute=0)
    scheduler.start()
    return scheduler


def _ask_start_mode():
    """
    Диалог выбора режима при запуске.
    Возвращает: 'search' | 'channels' | 'manual'
    """
    import tkinter as tk
    from tkinter import ttk

    result = {"mode": "manual"}

    # ── Nexio — Violet Midnight ───────────────────────────────────────────
    BG      = "#0f0f1a"
    BG2     = "#16162a"
    ACCENT  = "#6c63ff"
    ACCENT2 = "#4FAE4E"
    BORDER  = "#2a2a45"
    TEXT    = "#e2e2f0"
    MUTED   = "#7070a0"

    root = tk.Tk()
    root.title("Nexio · Андрей")
    root.resizable(False, False)
    root.configure(bg=BG)
    # Чёткость шрифтов на HiDPI
    try:
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72)
    except Exception:
        pass

    root.update_idletasks()
    w, h = 380, 320
    x = (root.winfo_screenwidth()  - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    # Тонкая рамка-акцент сверху
    tk.Frame(root, bg=ACCENT, height=2).pack(fill=tk.X)

    # Логотип-орбита через Canvas
    c = tk.Canvas(root, width=60, height=60, bg=BG, highlightthickness=0)
    c.pack(pady=(20, 0))
    c.create_rectangle(6, 6, 54, 54, fill="#1e1e38", outline=BORDER, width=1)
    c.create_oval(12, 12, 48, 48, outline=ACCENT, width=1, dash=(4, 3))
    c.create_oval(20, 20, 40, 40, outline="#a78bfa", width=1)
    c.create_oval(28, 28, 32, 32, fill=ACCENT, outline="")
    c.create_oval(44, 28, 50, 34, fill="#a78bfa", outline="")

    tk.Label(root, text="Nexio", font=("Segoe UI", 18, "bold"),
             bg=BG, fg=TEXT).pack(pady=(8, 2))
    tk.Label(root, text="Выберите режим запуска",
             font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(pady=(0, 16))

    # Разделитель
    tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X, padx=30, pady=(0, 16))

    def _lighten(h):
        r,g,b_ = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
        return "#{:02x}{:02x}{:02x}".format(
            min(255,int(r+(255-r)*.20)), min(255,int(g+(255-g)*.20)),
            min(255,int(b_+(255-b_)*.20)))

    def _make_btn(text, color, mode):
        # Используем tk.Canvas для кнопки с закруглёнными углами
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=5, padx=36, fill=tk.X)

        cv = tk.Canvas(btn_frame, height=44, bg=BG,
                       highlightthickness=0, cursor="hand2")
        cv.pack(fill=tk.X)

        r = 10  # радиус скругления

        def _draw(bg_color):
            cv.delete("all")
            w = cv.winfo_width() or 320
            h = 44
            # Закруглённый прямоугольник через полигон + овалы
            cv.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg_color, outline="")
            cv.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=bg_color, outline="")
            cv.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=bg_color, outline="")
            cv.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=bg_color, outline="")
            cv.create_rectangle(r, 0, w-r, h, fill=bg_color, outline="")
            cv.create_rectangle(0, r, w, h-r, fill=bg_color, outline="")
            cv.create_text(w//2, h//2, text=text,
                           font=("Segoe UI", 10, "bold"),
                           fill="white", anchor="center")

        cv.bind("<Configure>", lambda e: _draw(color))
        cv.bind("<Enter>",     lambda e: _draw(_lighten(color)))
        cv.bind("<Leave>",     lambda e: _draw(color))
        cv.bind("<Button-1>",  lambda e: (result.__setitem__("mode", mode), root.destroy()))

    _make_btn("⊹  Поиск объявлений",  ACCENT,    "search")
    _make_btn("⊚  Найти каналы",      "#5048e5", "channels")
    _make_btn("Просто открыть",        "#1e1e35", "manual")

    root.mainloop()
    return result["mode"]


def main():
    global window

    poll_thread = threading.Thread(target=_poll_callbacks, daemon=True)
    poll_thread.start()

    # Диалог выбора режима при старте
    mode = _ask_start_mode()

    scheduler = start_scheduler()
    window    = FreelanceWindow(on_send_callback=on_send, on_search_callback=run_search)

    # ── Сплэш-экран Nexio ─────────────────────────────────────────────────
    SplashScreen(window.root)

    if mode == "search":
        window.switch_to_search_tab()
        search_thread = threading.Thread(target=run_search, daemon=True)
        search_thread.start()
    elif mode == "channels":
        window.switch_to_channels_tab()
    else:
        # manual — просто показываем поиск заявок
        window.switch_to_search_tab()

    window.run()
    scheduler.shutdown()


if __name__ == "__main__":
    main()
