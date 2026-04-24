import os
from pathlib import Path
import warnings
import logging
import telebot
import sys
from flask import Flask

warnings.filterwarnings(
    "ignore",
    message=".*pin_memory.*no accelerator is found.*"
)

telebot.logger.setLevel(logging.CRITICAL)

if os.environ.get("RUN_MAIN") != "true":
    os.environ["RUN_MAIN"] = "true"
    os.system("python app.py >nul 2>&1")
    sys.exit()

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["PADDLEOCR_SHOW_LOG"] = "False"
os.environ["FLAGS_log_level"] = "3"
os.environ["GLOG_minloglevel"] = "3"

sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

warnings.filterwarnings("ignore")
logging.getLogger("paddle").setLevel(logging.ERROR)
logging.getLogger("paddlex").setLevel(logging.ERROR)

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

app = Flask(__name__)
application = app

if __name__ == "__main__":
    bot.infinity_polling(timeout=10, long_polling_timeout=5)