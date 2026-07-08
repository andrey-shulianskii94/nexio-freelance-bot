"""
channel_finder.py
=================
Поиск Telegram-каналов по ключевым словам.
Не требует авторизации — работает через краулинг упоминаний в каналах.
Результат: единый список уникальных username каналов → сохраняется в data/found_channels.json
"""

import re
import time
import json
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

FOUND_CHANNELS_FILE = "data/found_channels.json"

# ─── Блэклист — каналы которые точно не фриланс ──────────────────────────────
BLACKLIST = {
    "telegram", "durov", "gmail", "contest", "tginfo", "botnews",
    "botfather", "telegramtips", "tgstat", "tgstatapi", "tgstatacademy",
    "tgstatagency", "tgstatacademymanager", "femalebedev", "tg_analytics",
    "aba_association", "it", "news", "sport", "music", "films", "crypto",
    "nft", "forex", "trading", "invest", "casino", "bet", "game", "games",
    "porn", "adult", "nude", "leak", "hack", "crack", "cheat",
    "botnews", "contest", "sticker", "addstickers", "share", "joinchat",
    "username", "me", "bot", "help", "support", "promo", "ads",
}

# ─── Блэклист подстрок — если любая из них есть в username → выброс ──────────
BAD_PARTS = [
    # мусор категорий
    "porn", "adult", "nude", "casino", "bet", "forex", "trading", "invest",
    "nft", "crypto", "hack", "crack", "cheat", "sticker",
    # новости и политика
    "news", "mash", "novost", "lentach", "readovka", "smi", "kommersant",
    "rbc", "ria", "solov", "skabeev", "tass", "interfax", "regnum",
    # города и локальное
    "moscow", "moskva", "msk", "piter", "spb", "spblife", "питер", "москва",
    "mytischi", "pushkino", "омск", "omsk",
    # еда, кулинария
    "food", "cook", "kitchen", "kulinar", "recipe", "eat", "кулин", "еда",
    "gastro", "coffee", "bar_",
    # спорт, игры
    "sport", "football", "soccer", "brawl", "roblox", "game", "games",
    "esport", "fifa", "nba", "nhl", "chelsea", "madrid", "barcelona",
    # мода, красота
    "fashion", "beauty", "style", "makeup", "skincare", "parfum", "ootd",
    # туризм, путешествия
    "travel", "tourism", "trip", "backpack", "island", "resort",
    # развлечения, юмор
    "meme", "humor", "joke", "fun", "юмор", "мем", "приколы",
    # личные блоги явно не фриланс
    "daily", "diary", "life", "blog", "дневник",
    # финансы (не фриланс)
    "stocks", "bonds", "economy", "econom", "банк", "bank",
    # медиа, кино
    "kino", "film", "cinema", "movie", "serial", "podkast",
    # здоровье, медицина
    "health", "medic", "doctor", "clinic",
    # недвижимость
    "estate", "realt", "flat", "квартир",
    # религия, эзотерика
    "church", "pray", "астро",
    # благотворительность
    "charity", "dobroe",
    # гифты, стикеры, розыгрыши
    "gift", "giveaway", "giftchange",
]

# ─── Белый список подстрок — канал берём ТОЛЬКО если есть хотя бы одно ───────
# Логика: username должен намекать на работу / фриланс / IT / контент
GOOD_PARTS = [
    # фриланс явно
    "freelance", "фриланс", "заказ", "zakaz", "order",
    # вакансии / работа
    "job", "jobs", "вакансия", "vacancy", "hire", "hiring", "work", "worker",
    "rabota", "удалён", "remote", "удаленн",
    # IT-разработка
    "python", "django", "flask", "fastapi", "aiogram", "telegram_bot",
    "java", "kotlin", "android", "ios", "swift", "golang", "go_dev",
    "ruby", "rails", "nodejs", "node_js", "react", "vue", "angular",
    "frontend", "backend", "fullstack", "devops", "developer", "dev_",
    "_dev", "разработ", "программ", "coder", "coding",
    # данные и парсинг
    "parse", "парсер", "parser", "scraping", "data_", "_data", "data_sci",
    "excel", "sheets", "tableau",
    # QA и тестирование
    "qa_", "_qa", "tester", "testing", "qc_", "autotest",
    # дизайн
    "design", "дизайн", "ux_", "ui_", "figma",
    # контент / копирайт
    "copywr", "копирайт", "content_job", "content_work", "smm_job",
    "smm_work", "seo_job", "seo_work", "marketing_job",
    "text_order", "wb_content", "описани", "copywriting",
    # маркетплейсы
    "wb_job", "wb_work", "ozon_job", "avito_job", "marketplace_job",
    "ecom_job", "wildberr", "seller_job", "seller_work",
    "маркетплейс", "ozon_free", "wb_free",
    # общие IT вакансии
    "it_job", "it_vacanc", "it_remote", "it_work",
    # боты Telegram конкретно
    "tgbot", "bot_job", "bot_order", "bot_free", "botmaker",
    "telegram_bot", "bot_work", "бот_заказ",
    # автоматизация
    "automat", "автоматиз", "script_job", "скрипт",
    # WordPress / сайты / лендинги
    "wordpress", "landing", "webdev", "landingpage", "web_free",
    # Excel / Google Sheets
    "excel_job", "sheets_job", "google_sheet",
    # Android / QA
    "android_job", "qa_job",
    # общий фриланс (workzavr и подобные)
    "workzavr", "workasap", "worknow", "fl_job",
    "подработ", "исполнит",
    # биржи
    "биржа", "birja", "exchange_",
]

# ─── Стартовые каналы-доноры ──────────────────────────────────────────────────
SEED_CHANNELS = [
    # RU — фриланс биржи и заказы
    "freelance_ru", "freelance_hayr", "workforme_ru", "tg_jobs",
    "it_jobs_ru", "botmakers", "python_jobs", "smm_jobs_ru",
    "content_jobs_ru", "remote_jobs_ru", "web_python_jobs",
    "freelance_python", "django_jobs", "it_remote", "kanal_freelance",
    "freelancejobs_ru", "aiogram_jobs", "bot_jobs_ru", "webdev_jobs",
    "design_jobs_ru", "copywrite_jobs", "seo_jobs_ru", "marketing_jobs_ru",
    "freelance_orders", "freelance_tg", "jobs_tg_ru", "worknow_ru",
    "zakazchiki_ru", "zakaz_it", "parsing_jobs", "data_jobs_ru",
    "excel_jobs_ru", "wordpress_jobs_ru", "avito_jobs", "ecom_jobs_ru",
    "wb_jobs", "ozon_jobs", "marketplace_jobs", "landingpage_jobs",
    "tgfrelance", "python_freelance",
    # RU — IT вакансии и разработка
    "devjobs_ru", "it_vacancy", "python_job", "django_job",
    "ruby_jobs", "golang_jobs", "java_jobs_ru", "ios_jobs_ru",
    "android_jobs_ru", "qa_jobs_ru", "devops_jobs_feed", "django_jobs_board",
    "fullstack_jobs", "backend_jobs_ru", "frontend_jobs_ru",
    # EN — international
    "freelance_en", "remotejobs_en", "dev_jobs_global",
    "scraping_jobs", "telegram_bot_jobs", "automation_jobs",
    "no_code_jobs", "python_jobs_en", "backend_jobs_en",
    # RU — смежные (контент, маркетинг, дизайн)
    "copywriters_ru", "smm_ru", "targetolog_ru", "designjobs",
    "ux_jobs_ru", "video_jobs_ru", "photo_jobs_ru",
    # Боты Telegram
    "tgbot_jobs", "bot_jobs", "telegram_bot_jobs", "botmakers",
    "aiogram_jobs", "bot_freelance", "tgbotwork",
    # Маркетплейсы (WB, Ozon, Avito)
    "wb_jobs", "wb_freelance", "wildberries_work", "ozon_freelance",
    "avito_freelance", "ecom_jobs_ru", "seller_jobs", "mp_jobs_ru",
    "marketplace_freelance", "wb_content_jobs",
    # Парсеры и автоматизация
    "parsing_jobs", "scraping_jobs", "automation_jobs", "parser_jobs",
    "python_scripts", "excel_jobs_ru", "sheets_jobs",
    # WordPress и сайты
    "wordpress_jobs_ru", "landing_jobs", "webdev_jobs", "web_freelance_ru",
    "landingpage_jobs", "site_jobs_ru",
    # Контент и тексты
    "content_jobs_ru", "copywriting_jobs", "smm_jobs_ru", "text_jobs_ru",
    "wb_content", "ozon_content", "opisanie_tovarov",
    # Общий фриланс
    "workzavr", "workasap", "worknow_ru", "fl_jobs_ru",
    "freelance_chat_ru", "freelance_board",
]

# Регулярки для извлечения username из текста
RE_USERNAME = re.compile(r'@([a-zA-Z][a-zA-Z0-9_]{3,31})')
RE_TG_LINK  = re.compile(r't\.me/([a-zA-Z][a-zA-Z0-9_]{3,31})')

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Ключевые слова — для проверки текста канала
RELEVANCE_KEYWORDS = [
    "фриланс", "freelance", "заказ", "вакансия", "работа", "удалённо",
    "удаленно", "разработчик", "программист", "исполнитель", "нужен",
    "ищу", "remote", "job", "hire", "developer", "python", "бот", "парсер",
    "сайт", "верстка", "дизайн", "копирайт", "smm", "маркетинг", "seo",
    "автоматизация", "скрипт", "telegram", "авито", "wildberries", "ozon",
]


def _is_relevant_name(username: str) -> bool:
    """
    Двухэтапная фильтрация по username:
    1. Блэклист точных совпадений и подстрок → сразу выброс
    2. Белый список — если ни одного хорошего слова нет → выброс

    Зачем так: краулинг собирает всё подряд (новости, еду, спорт).
    Белый список оставляет только каналы, чьё имя намекает на работу/IT/фриланс.
    """
    u = username.lower()

    # ── Шаг 1: блэклист ─────────────────────────────────────────────────────
    if u in BLACKLIST:
        return False
    if any(b in u for b in BAD_PARTS):
        return False

    # ── Шаг 2: белый список ─────────────────────────────────────────────────
    # Каналы из SEED всегда проходят — мы сами их отобрали
    if u in {s.lower() for s in SEED_CHANNELS}:
        return True
    # Все остальные — только если есть хотя бы одно хорошее слово в username
    if any(g in u for g in GOOD_PARTS):
        return True

    return False  # ничего хорошего в имени нет → пропускаем


def _extract_usernames_from_text(text: str) -> set:
    """Вытаскивает @username и t.me/username из текста, фильтрует мусор."""
    found = set()
    found.update(RE_USERNAME.findall(text))
    found.update(RE_TG_LINK.findall(text))
    return {u.lower() for u in found if _is_relevant_name(u) and len(u) >= 4}


MIN_MEMBERS = 500  # минимум подписчиков — меньше не берём

def _get_members_count(username: str) -> int:
    """Парсит количество подписчиков канала через t.me/s/"""
    try:
        resp = requests.get(f"https://t.me/s/{username}",
                            headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return 0
        soup = BeautifulSoup(resp.text, "html.parser")
        # <div class="tgme_channel_info_counter"><span class="counter_value">1.2K</span>
        counter = soup.find("span", class_="counter_value")
        if not counter:
            return 0
        val = counter.get_text(strip=True).replace(" ", "").upper()
        if "K" in val:
            return int(float(val.replace("K", "")) * 1000)
        if "M" in val:
            return int(float(val.replace("M", "")) * 1_000_000)
        return int(val) if val.isdigit() else 0
    except Exception:
        return 0

def _is_real_channel(username: str) -> bool:
    """Проверяет что канал существует и имеет достаточно подписчиков."""
    try:
        resp = requests.get(f"https://t.me/s/{username}",
                            headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return False
        if 'tgme_widget_message' not in resp.text:
            return False
        members = _get_members_count(username)
        return members >= MIN_MEMBERS
    except Exception:
        return False


def _parse_channel_for_mentions(username: str) -> set:
    """Парсит канал и собирает упоминания других каналов."""
    found = set()
    try:
        resp = requests.get(f"https://t.me/s/{username}",
                            headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return found
        soup = BeautifulSoup(resp.text, "html.parser")
        for msg in soup.find_all("div", class_="tgme_widget_message_text"):
            found.update(_extract_usernames_from_text(msg.get_text()))
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "t.me/" in href:
                found.update(_extract_usernames_from_text(href))
    except Exception:
        pass
    return found


def load_found_channels() -> dict:
    """Загружает ранее найденные каналы"""
    try:
        with open(FOUND_CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_found_channels(data: dict):
    """Сохраняет найденные каналы в JSON"""
    os.makedirs(os.path.dirname(FOUND_CHANNELS_FILE), exist_ok=True)
    with open(FOUND_CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_all_channels(
    on_progress=None,
    verify: bool = False,
    max_depth: int = 2,
) -> dict:
    """
    Главная функция поиска каналов.

    Алгоритм:
    1. Краулим все SEED_CHANNELS — собираем упоминания других каналов
    2. Рекурсивно (до max_depth) краулим найденные каналы
    3. Фильтруем: блэклист + белый список по username
    4. (опционально) Проверяем каждый канал на существование
    5. Сохраняем и возвращаем словарь

    Почему белый список: краулинг без него собирает 800+ каналов
    из которых 80% — новости, еда, спорт, личные блоги.
    Белый список оставляет только то, что реально связано с работой/IT.
    """
    found: set = set(SEED_CHANNELS)
    visited: set = set()

    def _crawl(username: str, depth: int):
        if username in visited or depth > max_depth:
            return
        visited.add(username)
        if not _is_relevant_name(username):
            return
        mentions = _parse_channel_for_mentions(username)
        clean = {m for m in mentions if _is_relevant_name(m)}
        found.update(clean)
        time.sleep(0.3)
        if depth < max_depth:
            for m in list(clean):
                if m not in visited:
                    _crawl(m, depth + 1)

    # Краулим seed
    seeds = list(SEED_CHANNELS)
    for i, username in enumerate(seeds):
        if on_progress:
            on_progress(i + 1, len(seeds), f"🌱 Seed: @{username}")
        _crawl(username, depth=1)
        time.sleep(0.2)

    # Краулим найденные
    discovered = [u for u in found if u not in set(seeds)]
    for i, username in enumerate(discovered):
        if on_progress:
            on_progress(i + 1, len(discovered), f"🕸 Краулинг: @{username}")
        _crawl(username, depth=2)
        time.sleep(0.2)

    # Верификация и сборка результата
    verified   = {}
    unverified = {}

    all_candidates = sorted(found)
    for i, username in enumerate(all_candidates):
        if not _is_relevant_name(username):
            continue
        if on_progress:
            on_progress(i + 1, len(all_candidates),
                        f"{'✅ Проверяем' if verify else '📋 Сохраняем'}: @{username}")
        if verify:
            is_real = _is_real_channel(username)
            time.sleep(0.3)
        else:
            is_real = None

        entry = {
            "username": username,
            "link":     f"https://t.me/{username}",
            "verified": is_real,
            "joined":   False,
        }
        if is_real or is_real is None:
            verified[username] = entry
        else:
            unverified[username] = entry

    result = {
        "total":      len(verified),
        "channels":   verified,
        "unverified": unverified,
    }
    save_found_channels(result)
    return result


def get_channel_list_for_parser() -> list:
    """Возвращает список username для парсера объявлений."""
    data = load_found_channels()
    channels = data.get("channels", {})
    if not channels:
        return SEED_CHANNELS

    joined = [v["username"] for v in channels.values() if v.get("joined")]
    if joined:
        return joined
    return [v["username"] for v in channels.values()]


def export_channel_list_txt(path: str = "data/channels_to_join.txt"):
    """Экспортирует список каналов в текстовый файл."""
    data     = load_found_channels()
    channels = data.get("channels", {})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Найдено каналов: {len(channels)}\n")
        f.write("# Вступи в каждый канал через @avto_biznes_andrey\n\n")
        for username, info in sorted(channels.items()):
            f.write(f"https://t.me/{username}\n")
    return path
