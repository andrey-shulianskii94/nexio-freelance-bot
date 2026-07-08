import requests

groups = ['freelance', 'python_vk', 'web_freelance_ru', 'smm_freelance',
          'rabota_freelance', 'frilans_rabota', 'it_freelance', 'freelance_jobs',
          'webdev_freelance', 'kontent_freelance', 'smm_rabota', 'fl_python']

token = 'c971365dc971365dc971365dfcca333d3bcc971c971365da3328acbfde660b16d12e153'

for g in groups:
    r = requests.get(f'https://api.vk.com/method/wall.get?domain={g}&count=1&v=5.131&access_token={token}')
    data = r.json()
    if 'response' in data:
        print(f'{g}: OK, постов всего {data["response"]["count"]}')
    else:
        err = data.get('error', {}).get('error_msg', 'неизвестно')
        print(f'{g}: ОШИБКА — {err}')