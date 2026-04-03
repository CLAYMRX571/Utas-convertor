import os
from pathlib import Path
import warnings
import logging
import telebot

warnings.filterwarnings(
    "ignore",
    message=".*pin_memory.*no accelerator is found.*"
)

telebot.logger.setLevel(logging.CRITICAL)

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

from func import register_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
register_handlers(bot)

if __name__ == "__main__":
    print("Bot polling rejimida ishga tushdi...") 
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True, timeout=10, long_polling_timeout=5)
