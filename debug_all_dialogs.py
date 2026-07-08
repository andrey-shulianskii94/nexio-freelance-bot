"""
debug_all_dialogs.py — полный список каналов с последним сообщением
Сохраняет в data/dialogs_report.txt для просмотра
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

async def main():
    from pyrogram import Client
    from pyrogram.enums import ChatType

    lines = []

    async with Client(
        "freelance_session",
        api_id=API_ID, api_hash=API_HASH,
        workdir="data",
    ) as app:
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            if chat.type not in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                continue

            uname   = getattr(chat, "username", None) or f"id:{chat.id}"
            title   = getattr(chat, "title", "") or ""
            members = getattr(chat, "members_count", 0) or 0

            # Последнее сообщение из диалога
            last_msg = ""
            try:
                async for msg in app.get_chat_history(uname if "@" not in uname else uname, limit=1):
                    if msg.text:
                        last_msg = msg.text[:120].replace("\n", " ")
            except Exception:
                pass

            line = (f"@{uname:<30} | {members:>7} подп. | "
                    f"{title[:30]:<30} | {last_msg[:80]}")
            lines.append((members, line))
            print(line)

    # Сортируем по подписчикам убыванию
    lines.sort(key=lambda x: x[0], reverse=True)

    os.makedirs("data", exist_ok=True)
    with open("data/dialogs_report.txt", "w", encoding="utf-8") as f:
        f.write("username                         | подписчики | название                       | последнее сообщение\n")
        f.write("-" * 120 + "\n")
        for _, line in lines:
            f.write(line + "\n")

    print(f"\n✅ Сохранено в data/dialogs_report.txt ({len(lines)} каналов)")

asyncio.run(main())
