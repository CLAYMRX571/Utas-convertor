import os
import telebot
from dotenv import load_dotenv
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
from flask import Flask, request

from func import register_handlers

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

if not TOKEN:
    raise ValueError("BOT_TOKEN .env faylda topilmadi!")

if not WEBHOOK_HOST:
    raise ValueError("WEBHOOK_HOST .env faylda topilmadi!")

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage, threaded=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))

register_handlers(bot)

app = Flask(__name__)
application = app 

@app.route("/", methods=["GET"])
def index():
    return "Bot webhook ishlayapti!", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def get_message():
    if request.headers.get("content-type") == "application/json":
        json_str = request.stream.read().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return f"Webhook installed: {WEBHOOK_URL}", 200