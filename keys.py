from telebot.types import ReplyKeyboardMarkup, KeyboardButton

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row(KeyboardButton("Pdf 📁"), KeyboardButton("Word 📁"))
menu.row(KeyboardButton("Rasm 📸"), KeyboardButton("Tarjima 🇺🇿"))

confirm = ReplyKeyboardMarkup(resize_keyboard=True)
confirm.row(KeyboardButton("Ha ✅"), KeyboardButton("Yo'q ❌"))

translate = ReplyKeyboardMarkup(resize_keyboard=True)
translate.row(KeyboardButton("en 🏴"), KeyboardButton("ru 🇷🇺"))
translate.row(KeyboardButton("uz 🇺🇿"), KeyboardButton("tr 🇹🇷"))
translate.row(KeyboardButton("Orqaga 🔙"))