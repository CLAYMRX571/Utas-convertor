import os
import telebot
from dotenv import load_dotenv
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
from func import register_handlers

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

bot.add_custom_filter(custom_filters.StateFilter(bot))
register_handlers(bot)

if __name__ == "__main__":
    print("Bot ishga tushdi!")
    bot.infinity_polling(skip_pending=True)