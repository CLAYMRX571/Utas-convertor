import os
from dotenv import load_dotenv
from flask import Flask, request
import telebot
from telebot.types import Update
from func import register_handlers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/bot")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

if not WEBHOOK_DOMAIN:
    raise ValueError("WEBHOOK_DOMAIN topilmadi")

WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
register_handlers(bot)

app = Flask(__name__)
application = app


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 500


@app.route("/", methods=["GET"])
def set_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200
    except Exception as e:
        return f"Xatolik: {e}", 500