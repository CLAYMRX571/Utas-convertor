import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"

from dotenv import load_dotenv
import telebot
from func import register_handlers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

register_handlers(bot)

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)