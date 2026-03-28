from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

menu = ReplyKeyboardMarkup(
    keyboard=[
        [ KeyboardButton(text="Pdf 📁"), KeyboardButton(text="Word 📁")],
        [ KeyboardButton(text="Text ✉️"), KeyboardButton(text="Tarjima 🌐")],
        [ KeyboardButton(text="Adminga murojaat 👨‍💻")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Tugmalardan birini tanlang 👇"
)

confirm = ReplyKeyboardMarkup(
    keyboard=[
        [ KeyboardButton(text="Ha ✅"), KeyboardButton(text="Yo'q ❌")],
    ],
    resize_keyboard=True
)

lang = ReplyKeyboardMarkup(
    keyboard=[
        [ KeyboardButton(text="🇺🇿 O'zbek"), KeyboardButton(text="🇷🇺 Rus") ],
        [ KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇹🇷 Turk") ],
    ],
    resize_keyboard=True
)