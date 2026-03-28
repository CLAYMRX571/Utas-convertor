from aiogram.fsm.state import State, StatesGroup

class ConvertState(StatesGroup):
    waiting_pdf = State()
    waiting_pdf_confirm = State()
    waiting_docx = State()
    waiting_docx_confirm = State()
    waiting_text = State()
    waiting_translate_file = State()
    waiting_translate_lang = State()