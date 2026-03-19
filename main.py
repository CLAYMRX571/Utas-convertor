import os
from dotenv import load_dotenv
from telebot import TeleBot, custom_filters
from telebot.storage import StateMemoryStorage

from func import register_handlers

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN .env faylda topilmadi!")

state_storage = StateMemoryStorage()
bot = TeleBot(TOKEN, state_storage=state_storage)

bot.add_custom_filter(custom_filters.StateFilter(bot))

register_handlers(bot)

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)