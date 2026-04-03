import os
from pathlib import Path
import warnings
import logging
import telebot
from flask import Flask, request

warnings.filterwarnings(
    "ignore",
    message=".*pin_memory.*no accelerator is found.*"
)

telebot.logger.setLevel(logging.CRITICAL)

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

from func import register_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://claymrx.uz/bot")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
register_handlers(bot)

app = Flask(__name__)
application = app

@app.route("/bot", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")

    if json_str:
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])

    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot webhook server ishlayapti", 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    bot.remove_webhook()
    return "Webhook o'chirildi", 200

if __name__ == "__main__":
    app.run()