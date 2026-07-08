import random
from config import (
    SPAM_KEYWORDS,
    FULLTIME_KEYWORDS,
    SMM_EXCLUDE_KEYWORDS,
    CATEGORY_KEYWORDS,
    REPLY_TEMPLATES_BY_CATEGORY,
    CATEGORY_MATCH_THRESHOLD_HIGH,
    CATEGORY_MATCH_THRESHOLD_LOW,
)
from filters.smart_filter import analyze as smart_analyze

MIN_REPLY_VARIANTS = 3  # минимум вариантов ответа, которые нужно вернуть


def classify_message(text: str) -> str:
    """
    Классифицирует сообщение через трёхуровневый smart_filter.
    Возвращает: 'SPAM', 'FULLTIME', 'SMM', 'URGENT', или 'OK'

    Порядок:
    1. SMM — по словарю (быстро)
    2. Спам — по словарю
    3. smart_filter → FULLTIME → "FULLTIME"
    4. smart_filter → relevant=False → "SPAM" (мусор для нас)
    5. Остальное → "OK"
    """
    text_lower = text.lower()

    for keyword in SMM_EXCLUDE_KEYWORDS:
        if keyword in text_lower:
            return "SMM"

    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return "SPAM"

    # Трёхуровневый умный анализ
    result = smart_analyze(text)

    if result["job_type"] == "FULLTIME":
        return "FULLTIME"

    if not result["relevant"]:
        return "SPAM"

    return "OK"


def analyze_category(text: str) -> dict:
    """
    Анализирует текст на предмет соответствия каждой из 15 категорий.
    Возвращает словарь: {категория: процент_схожести}

    Процент считается по количеству независимых совпадений ключевых фраз,
    а не от общего размера списка категории: 1 совпадение = 30% (базовая
    уверенность), далее растёт до 100% на 4+ совпадениях.
    """
    text_lower = text.lower()
    scores = {}

    FULL_CONFIDENCE_MATCHES = 4  # столько совпадений = 100% уверенность

    for category, keywords in CATEGORY_KEYWORDS.items():
        if not keywords:
            continue
        matched = sum(1 for kw in keywords if kw in text_lower)
        if matched > 0:
            percent = round(min(matched / FULL_CONFIDENCE_MATCHES, 1.0) * 100)
            percent = max(percent, 30)
            scores[category] = percent

    return scores


def classify_and_match(text: str) -> dict:
    """
    Главная функция анализа задания.
    Возвращает структуру:
    {
        "status": "SPAM" | "FULLTIME" | "SMM" | "MATCHED" | "UNCERTAIN" | "NO_MATCH",
        "categories": [(категория, процент), ...] — отсортировано по убыванию процента,
        "top_category": лучшая категория или None,
        "top_percent": процент лучшей категории или 0,
        "replies": список из MIN_REPLY_VARIANTS+ готовых вариантов ответа (или [])
    }
    """
    base_status = classify_message(text)

    if base_status in ("SPAM", "FULLTIME", "SMM"):
        return {
            "status": base_status,
            "categories": [],
            "top_category": None,
            "top_percent": 0,
            "replies": [],
        }

    scores = analyze_category(text)

    if not scores:
        return {
            "status": "NO_MATCH",
            "categories": [],
            "top_category": None,
            "top_percent": 0,
            "replies": [],
        }

    # Сортируем категории по убыванию процента схожести
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_category, top_percent = sorted_categories[0]

    if top_percent < CATEGORY_MATCH_THRESHOLD_LOW:
        return {
            "status": "NO_MATCH",
            "categories": sorted_categories,
            "top_category": None,
            "top_percent": top_percent,
            "replies": [],
        }

    # Собираем варианты ответа — из топовой категории, и если есть близкая
    # по проценту вторая категория (в пределах 15 п.п.) — добавляем и её как альтернативу
    replies = get_reply_variants(top_category, count=MIN_REPLY_VARIANTS)

    status = "MATCHED" if top_percent >= CATEGORY_MATCH_THRESHOLD_HIGH else "UNCERTAIN"

    return {
        "status": status,
        "categories": sorted_categories[:3],  # топ-3 категории для показа "похоже на..."
        "top_category": top_category,
        "top_percent": top_percent,
        "replies": replies,
    }


def get_reply_variants(category: str, count: int = MIN_REPLY_VARIANTS) -> list:
    """
    Возвращает `count` случайных уникальных вариантов ответа для указанной категории.
    Если категории нет в словаре — возвращает пустой список.
    """
    templates = REPLY_TEMPLATES_BY_CATEGORY.get(category, [])
    if not templates:
        return []
    count = min(count, len(templates))
    return random.sample(templates, count)


def get_all_categories() -> list:
    """Возвращает список всех 15 категорий — для ручного выбора в GUI"""
    return list(REPLY_TEMPLATES_BY_CATEGORY.keys())


def get_templates_for_category(category: str) -> list:
    """Возвращает все 20 шаблонов конкретной категории — для ручного выбора в GUI"""
    return REPLY_TEMPLATES_BY_CATEGORY.get(category, [])


# ---------- Обратная совместимость со старым кодом ----------
# На случай, если где-то в проекте ещё вызывается старая функция get_reply_template()

def get_reply_template(message_type: str) -> str:
    """
    УСТАРЕВШАЯ функция, оставлена для совместимости.
    Новый код должен использовать classify_and_match() и get_reply_variants().
    """
    from config import HOT_TEMPLATES, COLD_TEMPLATES
    if message_type == "HOT":
        return random.choice(HOT_TEMPLATES)
    elif message_type == "COLD":
        return random.choice(COLD_TEMPLATES)
    return ""