import os
import asyncio
from dotenv import load_dotenv
from flask import Flask, request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from func import router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "bot.sample.uz")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/bot")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

# Bot va dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
dp.include_router(router)

app = Flask(__name__)
application = app

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.model_validate(data)

        asyncio.run(dp.feed_update(bot, update))
        return "OK", 200

    except Exception as e:
        return f"Error: {e}", 500


@app.route("/")
def set_webhook():
    try:
        async def _set():
            await bot.delete_webhook(drop_pending_updates=True)
            await bot.set_webhook(url=WEBHOOK_URL)

        asyncio.run(_set())
        return f"Webhook o‘rnatildi: {WEBHOOK_URL}", 200

    except Exception as e:
        return f"Xatolik: {e}", 500