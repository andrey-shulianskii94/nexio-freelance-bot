import requests

token = "vk1.a.eAJX-0uC2pjJKFCDyAVW5Oi11I-s-QBzRpJpgbk7y3GfoN6hypy5TFQuRoFB2v6tf6tFFiMqm1youCrPoswR_J_K8jkzYmJxC1bSBsm9ufMhbwTd59WjHZ3qLwG0vJaYPU4h-_78UJDbCbqE6yPguuUNRzlPCM85icgHtsnzuqosbQhc23y8DjG8IeKylLo8v6hDgmstP9DZRyzbZJXlLA"

r = requests.get(f"https://api.vk.com/method/groups.search?q=фриланс заказы&count=5&v=5.131&access_token={token}")
data = r.json()

if "response" in data:
    print("OK, найдено групп:", data["response"]["count"])
    for g in data["response"]["items"][:5]:
        print("-", g.get("screen_name"), "|", g.get("name"))
else:
    print("ОШИБКА:", data.get("error", {}).get("error_msg"))