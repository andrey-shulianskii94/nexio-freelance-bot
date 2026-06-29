from config import HOT_KEYWORDS, COLD_KEYWORDS, SPAM_KEYWORDS
import random
from config import HOT_TEMPLATES, COLD_TEMPLATES


def classify_message(text: str) -> str:
    """
    Классифицирует сообщение.
    Возвращает строго одно из трёх значений: 'HOT', 'COLD', 'SPAM'
    """
    text_lower = text.lower()

    # Сначала проверяем спам
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return "SPAM"

    # Потом горячие заказы
    for keyword in HOT_KEYWORDS:
        if keyword in text_lower:
            return "HOT"

    # Потом холодные клиенты
    for keyword in COLD_KEYWORDS:
        if keyword in text_lower:
            return "COLD"

    # Если ничего не подошло
    return "SPAM"


def get_reply_template(message_type: str) -> str:
    """
    Возвращает случайный шаблон ответа по типу сообщения.
    message_type: 'HOT' или 'COLD'
    """
    if message_type == "HOT":
        return random.choice(HOT_TEMPLATES)
    elif message_type == "COLD":
        return random.choice(COLD_TEMPLATES)
    return ""
