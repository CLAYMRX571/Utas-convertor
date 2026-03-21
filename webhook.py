import os
from pathlib import Path
import telebot
from flask import Flask, request
from dotenv import load_dotenv
from bot import bot

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "").strip()
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

app = Flask(__name__)
application = app

@app.route("/", methods=["GET"])
def index():
    return "Bot webhook ishlayapti!", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200