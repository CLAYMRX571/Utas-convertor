import os
from pathlib import Path
import telebot
from dotenv import load_dotenv
from telebot import custom_filters
from telebot.storage import StateMemoryStorage

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError(f"BOT_TOKEN topilmadi yoki bo'sh: {ENV_FILE}")

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage, threaded=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == "__main__":
    print("bot ishga tushdi")