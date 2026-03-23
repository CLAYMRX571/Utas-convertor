import os
from pathlib import Path
import telebot
from flask import Flask, request
from dotenv import load_dotenv
from telebot import custom_filters
from telebot.storage import StateMemoryStorage

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "").strip().rstrip("/")
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

if not TOKEN:
    raise RuntimeError(f"BOT_TOKEN topilmadi yoki bo'sh: {ENV_FILE}")

if not WEBHOOK_HOST:
    raise RuntimeError(f"WEBHOOK_HOST topilmadi yoki bo'sh: {ENV_FILE}")

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage, threaded=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))

app = Flask(__name__)
application = app

@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return f"Xatolik: {str(e)}", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200
    except Exception as e:
        return f"Webhook xatolik: {str(e)}", 500

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    try:
        bot.remove_webhook()
        return "Webhook o'chirildi", 200
    except Exception as e:
        return f"Xatolik: {str(e)}", 500

if __name__ == "__main__":
    print("Bot ishga tushdi")