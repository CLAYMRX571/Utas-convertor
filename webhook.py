import traceback
from flask import Flask, request
from telebot import types

from bot import bot
from keys import WEBHOOK_PATH, WEBHOOK_URL

app = Flask(__name__)
application = app

@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        if request.headers.get("content-type") == "application/json":
            json_string = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "OK", 200
        return "Invalid request", 403
    except Exception as e:
        print("Webhook xatolik:", e)
        traceback.print_exc()
        return "Internal Server Error", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200
    except Exception as e:
        print("Set webhook xatolik:", e)
        traceback.print_exc()
        return f"Webhook xatolik: {str(e)}", 500

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    try:
        bot.remove_webhook()
        return "Webhook o‘chirildi", 200
    except Exception as e:
        print("Delete webhook xatolik:", e)
        traceback.print_exc()
        return f"Xatolik: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)