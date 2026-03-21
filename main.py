import os
import telebot
from dotenv import load_dotenv
from flask import Flask, request
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
from func import register_handlers

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://bot.sample.uz").rstrip("/")
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage, threaded=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))

app = Flask(__name__)
application = app

register_handlers(bot)

@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti!", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
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
        return f"Webhook o‘rnatildi: {WEBHOOK_URL}", 200
    except Exception as e:
        return f"Webhook xatolik: {str(e)}", 500

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    try:
        bot.remove_webhook()
        return "Webhook o‘chirildi", 200
    except Exception as e:
        return f"Delete webhook xatolik: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)