import os
import telebot
from flask import Flask, request
from dotenv import load_dotenv
from bot import bot
from func import register_handlers

load_dotenv()

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://yourdomain.uz").rstrip("/")
WEBHOOK_PATH = "/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

app = Flask(__name__)
application = app 

register_handlers(bot)

@app.route("/", methods=["GET"])
def index():
    return "Bot webhook ishlayapti!", 200

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
        return f"Delete webhook xatolik: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)