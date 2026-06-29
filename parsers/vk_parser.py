import vk_api
import os
from dotenv import load_dotenv
from config import VK_GROUPS, HOT_KEYWORDS, COLD_KEYWORDS
from filters.classifier import classify_message, get_reply_template

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")


def parse_vk() -> list:
    """
    Парсит посты из групп VK.
    Возвращает список словарей с результатами.
    """
    results = []

    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()

        for group in VK_GROUPS:
            try:
                posts = vk.wall.get(domain=group, count=50, filter="all")

                for post in posts.get("items", []):
                    text = post.get("text", "")
                    if not text:
                        continue

                    msg_type = classify_message(text)

                    if msg_type == "SPAM":
                        continue

                    reply = get_reply_template(msg_type)
                    post_id = post.get("id")
                    owner_id = post.get("owner_id")
                    link = f"https://vk.com/wall{owner_id}_{post_id}"

                    results.append(
                        {
                            "platform": "VKontakte",
                            "channel": group,
                            "type": msg_type,
                            "text": text[:200],
                            "reply": reply,
                            "msg_id": post_id,
                            "sender_id": owner_id,
                            "link": link,
                            "status": "новый",
                            "amount": "",
                        }
                    )
            except Exception:
                continue

    except Exception:
        pass

    return results
