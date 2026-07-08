import vk_api, os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
token = os.getenv('VK_OAUTH_TOKEN')
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

cutoff = int((datetime.now() - timedelta(hours=48)).timestamp())

# Ищем группы
result = vk.groups.search(q='фриланс заказы', count=3, type='group')
groups = []
for g in result.get('items', []):
    if not g.get('is_closed', 1):
        groups.append(g.get('screen_name') or str(g.get('id')))

print('Открытых групп найдено:', len(groups), groups)

# Берём первую группу и смотрим посты
if groups:
    g = groups[0]
    posts = vk.wall.get(domain=g, count=10, offset=0, filter='owner')
    items = posts.get('items', [])
    print(f'Группа {g}: всего постов в выдаче = {len(items)}')
    now = datetime.now().timestamp()
    for p in items:
        age_hours = (now - p.get('date', 0)) / 3600
        text = p.get('text', '')[:60]
        print(f'  возраст={age_hours:.1f}ч | cutoff={48}ч | проходит={age_hours<=48} | {text}')