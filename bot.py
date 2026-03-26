import telebot
from telebot import types

from keys import BOT_TOKEN
from handlers import register_handlers

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
)

register_handlers(bot)