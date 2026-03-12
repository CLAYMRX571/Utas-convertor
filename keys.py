from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Pdf 📁"),
            KeyboardButton(text="Word 📁")
        ],
        [
            KeyboardButton(text="Rasm 📸"),
            KeyboardButton(text="Tarjima 🇺🇿")
        ],
    ],
    resize_keyboard=True
)

confirm = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ha ✅"), KeyboardButton(text="Yo'q ❌")]
    ],
    resize_keyboard=True
)

translate = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="en 🏴"), KeyboardButton(text="ru 🇷🇺")],
        [KeyboardButton(text="uz 🇺🇿"), KeyboardButton(text="tr 🇹🇷")],
        [KeyboardButton(text="Orqaga 🔙")]
    ],
    resize_keyboard=True
)