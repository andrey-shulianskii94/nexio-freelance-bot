import vk_api
import os
import json
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import SEARCH_KEYWORDS_VK, VK_GROUPS_STATIC, SENT_IDS_FILE, MAX_POST_AGE_HOURS
from filters.classifier import classify_and_match

load_dotenv()

VK_OAUTH_TOKEN = os.getenv("VK_OAUTH_TOKEN")

# Только явный мусор — спам, накрутки, мошенники
SPAM_HARD = [
    "лайкать фото", "ставить лайки за деньги", "заработок на лайках",
    "заработок на подписках", "казино", "ставки на спорт",
    "крипто сигналы", "заработок без вложений от",
]

MIN_TASK_LENGTH = 20
MAX_TASK_LENGTH = 5000


def load_sent_ids() -> set:
    try:
        with open(SENT_IDS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_sent_ids(ids: set):
    try:
        os.makedirs(os.path.dirname(SENT_IDS_FILE), exist_ok=True)
        with open(SENT_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ids), f)
    except Exception:
        pass


def is_hard_spam(text: str) -> bool:
    """Только явный мусор — накрутки и казино"""
    text_lower = text.lower()
    return any(marker in text_lower for marker in SPAM_HARD)


def normalize_for_dedup(text: str) -> str:
    text_lower = text.lower()
    text_no_links = re.sub(r"https?://\S+", "", text_lower)
    text_no_spaces = re.sub(r"\s+", " ", text_no_links).strip()
    return text_no_spaces[:200]


def find_groups(vk, query: str, count: int = 10) -> list:
    """Ищет группы VK по ключевому слову (открытые)"""
    found = []
    try:
        result = vk.groups.search(q=query, count=count, type="group")
        for group in result.get("items", []):
            if not group.get("is_closed", 1):
                found.append(group.get("screen_name") or str(group.get("id")))
    except Exception:
        pass
    return found


def fetch_group_posts(vk, group: str, cutoff_timestamp: int) -> list:
    """Загружает посты группы за последние MAX_POST_AGE_HOURS с пагинацией"""
    all_posts = []
    offset = 0
    max_requests = 3

    for _ in range(max_requests):
        try:
            response = vk.wall.get(
                domain=group,
                count=50,
                offset=offset,
            )
            items = response.get("items", [])
            if not items:
                break

            for post in items:
                post_date = post.get("date", 0)
                if post_date < cutoff_timestamp:
                    return all_posts
                all_posts.append(post)

            offset += 50
            time.sleep(0.3)

        except Exception:
            break

    return all_posts


def parse_vk() -> list:
    """
    Парсит посты из VK-групп. Для портфолио — широкая выдача,
    отсекается только явный спам (казино, лайки за деньги).
    """
    results = []
    sent_ids = load_sent_ids()
    seen_text_hashes = set()
    cutoff_time = datetime.now() - timedelta(hours=MAX_POST_AGE_HOURS)
    cutoff_timestamp = int(cutoff_time.timestamp())

    try:
        vk_session = vk_api.VkApi(token=VK_OAUTH_TOKEN)
        vk = vk_session.get_api()

        # Собираем группы: статичный список + автопоиск
        all_groups = set(VK_GROUPS_STATIC)
        for keyword in SEARCH_KEYWORDS_VK:
            found = find_groups(vk, keyword, count=8)
            all_groups.update(found)
            time.sleep(0.4)

        for group in all_groups:
            try:
                time.sleep(0.4)
                posts = fetch_group_posts(vk, group, cutoff_timestamp)

                for post in posts:
                    text = post.get("text", "")
                    if not text or len(text) < MIN_TASK_LENGTH:
                        continue
                    if len(text) > MAX_TASK_LENGTH:
                        continue

                    post_id = post.get("id")
                    owner_id = post.get("owner_id")
                    unique_id = f"{owner_id}_{post_id}"

                    if unique_id in sent_ids:
                        continue

                    text_hash = normalize_for_dedup(text)
                    if text_hash in seen_text_hashes:
                        sent_ids.add(unique_id)
                        continue

                    # Отсекаем только явный мусор
                    if is_hard_spam(text):
                        sent_ids.add(unique_id)
                        continue

                    # Классификация — для отображения категории и ответов
                    match = classify_and_match(text)

                    # Отсекаем только SPAM из классификатора
                    # FULLTIME, SMM, NO_MATCH теперь ПРОХОДЯТ — нужны для демо
                    if match["status"] == "SPAM":
                        sent_ids.add(unique_id)
                        continue

                    link = f"https://vk.com/wall{owner_id}_{post_id}"

                    # Для FULLTIME/SMM/NO_MATCH даём общий ответ
                    category = match["top_category"] or "Общий запрос"
                    replies = match["replies"]
                    if not replies:
                        from config import HOT_TEMPLATES
                        import random
                        replies = random.sample(HOT_TEMPLATES, min(3, len(HOT_TEMPLATES)))

                    results.append({
                        "platform": "VKontakte",
                        "channel": group,
                        "status_match": match["status"],
                        "category": category,
                        "match_percent": match["top_percent"],
                        "all_categories": match["categories"],
                        "text": text,
                        "replies": replies,
                        "reply": replies[0] if replies else "",
                        "msg_id": post_id,
                        "sender_id": owner_id,
                        "link": link,
                        "status": "новый",
                        "amount": "",
                        "post_date": post.get("date", 0),
                    })

                    seen_text_hashes.add(text_hash)
                    sent_ids.add(unique_id)

            except Exception:
                continue

    except Exception:
        pass

    save_sent_ids(sent_ids)
    return results