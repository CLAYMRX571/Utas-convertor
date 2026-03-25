import os
from pathlib import Path
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8677895463:AAEbTAhOtgYNd6hkA7CAldOiahHGoAmojEo").strip()
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://claymrx.uz").strip().rstrip("/")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/bot").strip()

WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

ILOVEPDF_PUBLIC_KEY = os.getenv("ILOVEPDF_PUBLIC_KEY", "project_public_5a4cb02d6664728a50de78d58f757635_Dzpu605408894a222f77d98ad0c6207a1ce6b").strip()
ILOVEPDF_SECRET_KEY = os.getenv("ILOVEPDF_SECRET_KEY", "secret_key_d05d10c747c59ea4ed5d4bb859555583_1mAT9e7da624be3ca7c16dafb2c29f8c18d84").strip()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip().lstrip("@")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998000000000").strip()

LANG_MAP = {
    "en 🇬🇧": "en",
    "uz 🇺🇿": "uz",
    "ru 🇷🇺": "ru",
    "tr 🇹🇷": "tr",
}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Pdf 📁"), KeyboardButton(text="Word 📁")],
        [KeyboardButton(text="Text ✉️"), KeyboardButton(text="Tarjima 🌐")],
        [KeyboardButton(text="Adminga murojaat 👨‍💻")],
    ],
    resize_keyboard=True,
)

confirm_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ha ✅"), KeyboardButton(text="Yo'q ❌")],
        [KeyboardButton(text="Orqaga 🔙")],
    ],
    resize_keyboard=True,
)

translate_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="en 🇬🇧"), KeyboardButton(text="uz 🇺🇿")],
        [KeyboardButton(text="ru 🇷🇺"), KeyboardButton(text="tr 🇹🇷")],
        [KeyboardButton(text="Orqaga 🔙")],
    ],
    resize_keyboard=True,
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST topilmadi")

if not WEBHOOK_HOST.startswith("https://"):
    raise RuntimeError("WEBHOOK_HOST https:// bilan boshlanishi kerak")