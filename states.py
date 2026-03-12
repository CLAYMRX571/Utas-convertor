from aiogram.fsm.state import State, StatesGroup

class ConvertState(StatesGroup):
    ask_pdf = State()
    ask_word = State()
    waiting_pdf_file = State()
    waiting_word_file = State()
    waiting_image = State()
    waiting_translate_file = State()
    waiting_translate_lang = State()