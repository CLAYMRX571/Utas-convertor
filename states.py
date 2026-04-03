user_states = {}
user_data = {}

class State:
    NONE = "none"
    WAITING_PDF = "waiting_pdf"
    WAITING_PDF_CONFIRM = "waiting_pdf_confirm"
    WAITING_DOCX = "waiting_docx"
    WAITING_DOCX_CONFIRM = "waiting_docx_confirm"
    WAITING_TEXT = "waiting_text"
    WAITING_TRANSLATE_FILE = "waiting_translate_file"
    WAITING_TRANSLATE_LANG = "waiting_translate_lang"