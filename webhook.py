import asyncio
from flask import Flask, request
from aiogram.types import Update
from bot import bot, dp
from keys import WEBHOOK_PATH, WEBHOOK_URL

app = Flask(__name__)
application = app

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route("", methods=["GET"])
def index():
    return "!", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.model_validate(json_data)
        loop.run_until_complete(dp.feed_update(bot, update))
        return "OK", 200
    except Exception as e:
        print("Webhook xatolik:", e)
        return f"Xatolik: {str(e)}", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
        loop.run_until_complete(bot.set_webhook(url=WEBHOOK_URL))
        return f"Webhook o'rnatildi: {WEBHOOK_URL}", 200
    except Exception as e:
        print("Set webhook xatolik:", e)
        return f"Webhook xatolik: {str(e)}", 500

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    try:
        loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
        return "Webhook o‘chirildi", 200
    except Exception as e:
        print("Delete webhook xatolik:", e)
        return f"Xatolik: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)