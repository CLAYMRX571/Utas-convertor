import os
from pathlib import Path

import telebot
from flask import Flask, request
from dotenv import load_dotenv

from bot import bot
from func import register_handlers

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://claymrx.uz").strip().rstrip("/")
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

if not WEBHOOK_HOST:
    raise RuntimeError(f"WEBHOOK_HOST topilmadi yoki bo'sh: {ENV_FILE}")

if not WEBHOOK_HOST.startswith("https://"):
    raise RuntimeError("WEBHOOK_HOST https:// bilan boshlanishi kerak")

app = Flask(__name__)
application = app

register_handlers(bot)

@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti", 200

@app.route("/bot", methods=["POST"])
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
        result = bot.set_webhook(url=WEBHOOK_URL)
        return f"Webhook o'rnatildi: {WEBHOOK_URL} | result={result}", 200
    except Exception as e:
        return f"Webhook xatolik: {str(e)}", 500

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    try:
        result = bot.remove_webhook()
        return f"Webhook o'chirildi | result={result}", 200
    except Exception as e:
        return f"Xatolik: {str(e)}", 500

if __name__ == "__main__":
    print("Bot ishga tushdi")