import os
import telebot
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN", "8677895463:AAEuIBWBcstMFN3V_3AnHC5z0TAXWjBQIn4")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://claymrx.uz/bot")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

app = Flask(__name__)
application = app 

@app.route("/bot", methods=["POST"])
def get_message():
    json_str = request.stream.read().decode("utf-8")

    if json_str:
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])

    return "OK", 200

@app.route("/", methods=["GET"])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return "Webhook installed", 200

@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    bot.remove_webhook()
    return "Webhook deleted", 200

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    bot.reply_to(message, "Bot ishlayapti")