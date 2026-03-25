from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from keys import BOT_TOKEN
from handlers import register_handlers

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
)

dp = Dispatcher()
register_handlers(dp, bot)