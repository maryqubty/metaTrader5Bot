import logging
import os
import re

from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
_SOURCE_RAW = os.environ["SOURCE_CHANNEL"]
_TARGET_RAW = os.environ["TARGET_GROUP"]

# Convert to int if numeric so Telethon can resolve it correctly
SOURCE_CHANNEL = int(_SOURCE_RAW) if _SOURCE_RAW.lstrip("-").isdigit() else _SOURCE_RAW
TARGET_GROUP = int(_TARGET_RAW) if _TARGET_RAW.lstrip("-").isdigit() else _TARGET_RAW

_ALERT_RE = re.compile(r"GOLD\s+(BUY|SELL)", re.IGNORECASE)

client = TelegramClient("forwarder", API_ID, API_HASH)


async def make_handler(target):
    async def handler(event):
        chat = await event.get_chat()
        chat_id = getattr(chat, "id", "?")
        chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or getattr(chat, "first_name", "?")
        logger.info("Message received — chat_id: %s | name: %s", chat_id, chat_name)

        text = event.message.text or ""
        if not _ALERT_RE.search(text):
            return
        logger.info("Alert detected — forwarding:\n%s", text)
        await client.send_message(target, text)
        logger.info("Forwarded successfully")
    return handler


async def main():
    await client.start()
    me = await client.get_me()
    logger.info("Forwarder running as: %s (@%s)", me.first_name, me.username)

    try:
        source_entity = await client.get_entity(SOURCE_CHANNEL)
        target_entity = await client.get_entity(TARGET_GROUP)
        logger.info("Watching: %s → %s",
                    getattr(source_entity, "title", None) or getattr(source_entity, "first_name", source_entity.id),
                    getattr(target_entity, "title", None) or target_entity.id)
    except Exception as e:
        logger.error("Could not resolve source/target: %s", e)
        return

    client.add_event_handler(
        await make_handler(target_entity),
        events.NewMessage(chats=source_entity, incoming=True, outgoing=True)
    )

    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
