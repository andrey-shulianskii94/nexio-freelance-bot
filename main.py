import threading
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from parsers.telegram_parser import parse_telegram, send_telegram_notification
from parsers.vk_parser import parse_vk
from export.excel_export import export_to_excel
from gui.window import FreelanceWindow

daily_results = []
window = None

def run_parsers():
    global daily_results, window
    
    send_telegram_notification("⏳ Запускаю парсинг каналов...")
    
    if window:
        window.set_status("⏳ Парсинг Telegram...")
    
    tg_results = parse_telegram()
    
    if window:
        window.set_status("⏳ Парсинг VKontakte...")
    
    vk_results = parse_vk()
    
    new_results = tg_results + vk_results
    
    existing = {(r.get("channel","") + str(r.get("text","")[:50])) for r in daily_results}
    added = 0
    for item in new_results:
        key = item.get("channel","") + str(item.get("text","")[:50])
        if key not in existing:
            daily_results.append(item)
            existing.add(key)
            added += 1
    
    hot = sum(1 for r in daily_results if r.get("type") == "HOT")
    cold = sum(1 for r in daily_results if r.get("type") == "COLD")
    
    summary = (
        f"✅ Парсинг завершён\n"
        f"Новых: {added} | Всего за день: {len(daily_results)}\n"
        f"🟢 Горячих: {hot} | 🔵 Холодных: {cold}"
    )
    send_telegram_notification(summary)
    
    if window:
        window.update_results(daily_results)
        window.set_status(f"✅ Новых: {added} | Всего: {len(daily_results)}")

def export_daily():
    global daily_results
    export_to_excel(daily_results)
    send_telegram_notification("📊 Excel выгрузка за день сохранена")
    daily_results = []

def on_send(item: dict):
    pass

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_parsers, 'interval', minutes=30)
    scheduler.add_job(export_daily, 'cron', hour=0, minute=0)
    scheduler.start()
    return scheduler

def main():
    global window
    parse_thread = threading.Thread(target=run_parsers, daemon=True)
    parse_thread.start()
    scheduler = start_scheduler()
    window = FreelanceWindow(on_send_callback=on_send)
    window.run()
    scheduler.shutdown()

if __name__ == "__main__":
    main()