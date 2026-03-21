import os
import telebot
from dotenv import load_dotenv
from telebot import custom_filters
from telebot.storage import StateMemoryStorage

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage, threaded=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))