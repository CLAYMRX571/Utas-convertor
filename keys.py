from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def get_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="Tugmalardan birini tanlang 👇")
    markup.row(
        KeyboardButton("Pdf 📁"),
        KeyboardButton("Word 📁")
    )
    markup.row(
        KeyboardButton("Text ✉️"),
        KeyboardButton("Tarjima 🌐")
    )
    markup.row(
        KeyboardButton("Adminga murojaat 👨‍💻")
    )
    return markup

def get_confirm():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Ha ✅", "Yo'q ❌")
    return markup

def get_lang():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("🇺🇿 O'zbek"),
        KeyboardButton("🇷🇺 Rus")
    )
    markup.row(
        KeyboardButton("🇬🇧 English"),
        KeyboardButton("🇹🇷 Turk")
    )
    return markup