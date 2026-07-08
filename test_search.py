import vk_api
import time

VK_TOKEN = 'c971365dc971365dc971365dfcca333d3bcc971c971365da3328acbfde660b16d12e153'

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

keywords = ["фриланс заказы", "ищу разработчика", "python работа удаленно", "нужен бот telegram"]

for kw in keywords:
    try:
        result = vk.groups.search(q=kw, count=5, type="group")
        print(f"\n--- {kw} ---")
        for g in result.get("items", []):
            print(g.get("screen_name"), "| closed:", g.get("is_closed"))
        time.sleep(0.5)
    except Exception as e:
        print(f"ОШИБКА на '{kw}': {e}")