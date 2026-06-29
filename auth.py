from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
)
import asyncio

API_ID = 37027628
API_HASH = "565adb07d89a27309a9816563c78749f"
PHONE = "+79952196337"


async def main():
    client = TelegramClient("freelance_session", API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Уже авторизован как пользователь: {me.first_name}")
        await client.disconnect()
        return

    try:
        sent = await client.send_code_request(PHONE)
        print(f"=== ТИП КОДА: {sent.type} ===")  # вот главная диагностика
        code = input("Введи код: ")
        await client.sign_in(PHONE, code, phone_code_hash=sent.phone_code_hash)
        me = await client.get_me()
        print(f"Авторизован: {me.first_name}")
    except FloodWaitError as e:
        h = e.seconds // 3600
        m = (e.seconds % 3600) // 60
        print(f"!!! ФЛУД-БЛОКИРОВКА: ждать {e.seconds} сек (~{h} ч {m} мин)")
    except PhoneNumberBannedError:
        print("!!! Номер заблокирован Telegram")
    except PhoneCodeInvalidError:
        print("Код неверный")

    await client.disconnect()


asyncio.run(main())
