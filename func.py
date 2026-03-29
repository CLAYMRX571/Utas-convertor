import os
import uuid
from pathlib import Path
import telebot
import pdfplumber
from PyPDF2 import PdfReader
from deep_translator import GoogleTranslator
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from telebot.types import Message

from keys import get_menu, get_confirm, get_lang
from states import user_states, user_data, State

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
PDF_DIR = MEDIA_DIR / "pdf"
DOCX_DIR = MEDIA_DIR / "docx"
TRANSLATE_DIR = MEDIA_DIR / "translate"
OUT_DIR = MEDIA_DIR / "out"

for folder in [MEDIA_DIR, PDF_DIR, DOCX_DIR, TRANSLATE_DIR, OUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


def make_file_path(folder: Path, suffix: str) -> Path:
    return folder / f"{uuid.uuid4().hex}{suffix}"

def clean_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "|": "I",
        "¥": "Y",
        "§": "S",
        "\xa0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def is_meaningful_text(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    if len(text) < 20:
        return False
    alnum_count = sum(ch.isalnum() for ch in text)
    return alnum_count >= 10


def set_doc_defaults(doc: Document):
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)


def add_paragraph(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)


def extract_text_pdf_with_tables(pdf_path: str, output_docx: str):
    doc = Document()
    set_doc_defaults(doc)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            cleaned = clean_text(page_text)

            if cleaned:
                for line in cleaned.split("\n"):
                    line = line.strip()
                    if line:
                        add_paragraph(doc, line)

            doc.add_paragraph("")

    doc.save(output_docx)


def create_word_from_text(text: str, output_docx: str):
    doc = Document()
    set_doc_defaults(doc)

    for line in text.split("\n"):
        line = line.strip()
        if line:
            add_paragraph(doc, line)

    doc.save(output_docx)


def extract_text_from_docx(docx_path: str) -> str:
    doc = Document(docx_path)
    texts = []

    for para in doc.paragraphs:
        txt = para.text.strip()
        if txt:
            texts.append(txt)

    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                value = cell.text.strip()
                row_text.append(value)
            if any(row_text):
                texts.append(" | ".join(row_text))

    return "\n".join(texts).strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texts = []

    for page in reader.pages:
        try:
            txt = page.extract_text()
            if txt:
                texts.append(txt.strip())
        except Exception:
            continue

    return clean_text("\n".join(texts))


def split_text_into_chunks(text: str, max_length: int = 4000):
    if not text:
        return []

    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 1 <= max_length:
            if current_chunk:
                current_chunk += "\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def translate_text(text: str, target_lang: str) -> str:
    if not text.strip():
        return ""

    translator = GoogleTranslator(source="auto", target=target_lang)
    chunks = split_text_into_chunks(text, 4000)
    translated_chunks = []

    for chunk in chunks:
        translated_chunks.append(translator.translate(chunk))

    return "\n\n".join(translated_chunks).strip()


def create_docx_from_text(text: str, output_docx: str):
    doc = Document()
    set_doc_defaults(doc)

    for line in text.split("\n"):
        line = line.strip()
        if line:
            add_paragraph(doc, line)

    doc.save(output_docx)


def remove_file(path_str):
    try:
        if path_str and os.path.exists(path_str):
            os.remove(path_str)
    except Exception:
        pass


def set_state(user_id, state):
    user_states[user_id] = state


def get_state(user_id):
    return user_states.get(user_id, State.NONE)


def clear_state(user_id):
    user_states[user_id] = State.NONE
    user_data.pop(user_id, None)


def register_handlers(bot: telebot.TeleBot):
    @bot.message_handler(commands=["start"])
    def start_handler(message: Message):
        user = message.from_user
        if user.username:
            text = f"Assalomu alaykum hurmatli foydalanuvchi @{user.username}\nTugmalardan birini tanlang 👇"
        else:
            text = f"Assalomu alaykum hurmatli foydalanuvchi {user.full_name}\nTugmalardan birini tanlang 👇"

        clear_state(message.chat.id)
        bot.send_message(message.chat.id, text, reply_markup=get_menu())

    @bot.message_handler(func=lambda m: m.text == "Pdf 📁")
    def pdf_button_handler(message: Message):
        set_state(message.chat.id, State.WAITING_PDF)
        bot.send_message(message.chat.id, "Pdf file tashlang (.pdf)", reply_markup=get_menu())

    @bot.message_handler(content_types=["document"], func=lambda m: get_state(m.chat.id) == State.WAITING_PDF)
    def get_pdf_file(message: Message):
        document = message.document

        if not document.file_name.lower().endswith(".pdf"):
            bot.send_message(message.chat.id, "Faqat .pdf formatdagi fayl yuboring.")
            return

        file_path = make_file_path(PDF_DIR, ".pdf")

        try:
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            with open(file_path, "wb") as new_file:
                new_file.write(downloaded_file)
        except Exception as e:
            bot.send_message(message.chat.id, f"Fayl yuklashda xatolik: {e}")
            return

        user_data[message.chat.id] = {
            "pdf_path": str(file_path),
            "pdf_name": document.file_name
        }
        set_state(message.chat.id, State.WAITING_PDF_CONFIRM)

        bot.send_message(
            message.chat.id,
            "PDF'ni Word'ga o'girmoqchimisiz?",
            reply_markup=get_confirm()
        )

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_PDF and m.content_type != "document")
    def waiting_pdf_invalid(message: Message):
        bot.send_message(message.chat.id, "Iltimos, .pdf fayl yuboring.")

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_PDF_CONFIRM and m.text == "Ha ✅")
    def pdf_confirm_yes(message: Message):
        data = user_data.get(message.chat.id, {})
        pdf_path = data.get("pdf_path")

        if not pdf_path or not os.path.exists(pdf_path):
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, "PDF topilmadi. Qaytadan yuboring.", reply_markup=get_menu())
            return

        output_docx = make_file_path(OUT_DIR, ".docx")
        progress_msg = bot.send_message(message.chat.id, "Jarayonda... 0%")

        try:
            bot.edit_message_text("Jarayonda... 30%", message.chat.id, progress_msg.message_id)
            extract_text_pdf_with_tables(pdf_path, str(output_docx))
            bot.edit_message_text("Jarayonda... 100%", message.chat.id, progress_msg.message_id)

            with open(output_docx, "rb") as f:
                bot.send_document(message.chat.id, f, visible_file_name="converted.docx")

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")

        finally:
            remove_file(pdf_path)
            remove_file(str(output_docx))
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, "Orqaga qaytdingiz 🔙", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_PDF_CONFIRM and m.text == "Yo'q ❌")
    def pdf_confirm_no(message: Message):
        data = user_data.get(message.chat.id, {})
        remove_file(data.get("pdf_path"))
        clear_state(message.chat.id)
        bot.send_message(message.chat.id, "Orqaga qaytdingiz 🔙", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: m.text == "Word 📁")
    def word_handler(message: Message):
        set_state(message.chat.id, State.WAITING_DOCX)
        bot.send_message(message.chat.id, "Word file tashlang (.docx)", reply_markup=get_menu())

    @bot.message_handler(content_types=["document"], func=lambda m: get_state(m.chat.id) == State.WAITING_DOCX)
    def get_docx_file(message: Message):
        document = message.document

        if not document.file_name.lower().endswith(".docx"):
            bot.send_message(message.chat.id, "Faqat .docx formatdagi fayl yuboring.")
            return

        file_path = make_file_path(DOCX_DIR, ".docx")

        try:
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            with open(file_path, "wb") as new_file:
                new_file.write(downloaded_file)
        except Exception as e:
            bot.send_message(message.chat.id, f"Fayl yuklashda xatolik: {e}")
            return

        user_data[message.chat.id] = {
            "docx_path": str(file_path),
            "docx_name": document.file_name
        }

        clear_state(message.chat.id)
        bot.send_message(
            message.chat.id,
            "Ahost Linux hostingda Word → PDF ishonchsiz ishlaydi.\nHozircha bu funksiya o‘chirildi.",
            reply_markup=get_menu()
        )

    @bot.message_handler(func=lambda m: m.text == "Text ✉️")
    def text_handler(message: Message):
        set_state(message.chat.id, State.WAITING_TEXT)
        bot.send_message(message.chat.id, "Matn yuboring!", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_TEXT and m.content_type == "text")
    def get_text_and_convert_to_word(message: Message):
        text = message.text.strip()

        if not text:
            bot.send_message(message.chat.id, "Matn yuboring!")
            return

        output_docx = make_file_path(OUT_DIR, ".docx")

        try:
            create_word_from_text(text, str(output_docx))
            with open(output_docx, "rb") as f:
                bot.send_document(message.chat.id, f, visible_file_name="matn.docx")

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")

        finally:
            remove_file(str(output_docx))
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, "Orqaga qaytdingiz 🔙", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: m.text == "Tarjima 🌐")
    def tarjima_handler(message: Message):
        set_state(message.chat.id, State.WAITING_TRANSLATE_FILE)
        bot.send_message(message.chat.id, "docx yoki pdf file tashlang", reply_markup=get_menu())

    @bot.message_handler(content_types=["document"], func=lambda m: get_state(m.chat.id) == State.WAITING_TRANSLATE_FILE)
    def get_translate_file(message: Message):
        document = message.document
        file_name = document.file_name.lower()

        if not (file_name.endswith(".docx") or file_name.endswith(".pdf")):
            bot.send_message(message.chat.id, "Faqat .docx yoki .pdf formatdagi fayl yuboring.")
            return

        suffix = ".docx" if file_name.endswith(".docx") else ".pdf"
        file_path = make_file_path(TRANSLATE_DIR, suffix)

        try:
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            with open(file_path, "wb") as new_file:
                new_file.write(downloaded_file)
        except Exception as e:
            bot.send_message(message.chat.id, f"Fayl yuklashda xatolik: {e}")
            return

        user_data[message.chat.id] = {
            "translate_file_path": str(file_path),
            "translate_file_name": document.file_name,
            "translate_file_type": suffix
        }
        set_state(message.chat.id, State.WAITING_TRANSLATE_LANG)

        bot.send_message(message.chat.id, "Tarjima tilini tanlang", reply_markup=get_lang())

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_TRANSLATE_LANG and m.text == "Orqaga 🔙")
    def translate_back(message: Message):
        data = user_data.get(message.chat.id, {})
        remove_file(data.get("translate_file_path"))
        clear_state(message.chat.id)
        bot.send_message(message.chat.id, "Orqaga qaytdingiz 🔙", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: get_state(m.chat.id) == State.WAITING_TRANSLATE_LANG)
    def translate_file_by_lang(message: Message):
        data = user_data.get(message.chat.id, {})
        file_path = data.get("translate_file_path")
        file_name = data.get("translate_file_name", "file")
        file_type = data.get("translate_file_type")

        lang_map = {
            "🇺🇿 O'zbek": "uz",
            "🇷🇺 Rus": "ru",
            "🇬🇧 English": "en",
            "🇹🇷 Turk": "tr"
        }

        target_lang = lang_map.get(message.text)
        if not target_lang:
            bot.send_message(message.chat.id, "Iltimos, tugmalardan birini tanlang.")
            return

        if not file_path or not os.path.exists(file_path):
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, "Fayl topilmadi. Qaytadan yuboring.", reply_markup=get_menu())
            return

        progress_msg = bot.send_message(message.chat.id, "Jarayonda... 0%")
        output_file = None

        try:
            bot.edit_message_text("Jarayonda... 20%", message.chat.id, progress_msg.message_id)

            if file_type == ".docx":
                extracted_text = extract_text_from_docx(file_path)
            else:
                extracted_text = extract_text_from_pdf(file_path)

            if not extracted_text.strip():
                bot.send_message(message.chat.id, "Fayldan matn ajratilmadi.")
                return

            bot.edit_message_text("Jarayonda... 60%", message.chat.id, progress_msg.message_id)

            translated_text = translate_text(extracted_text, target_lang)

            output_file = str(make_file_path(OUT_DIR, ".docx"))
            create_docx_from_text(translated_text, output_file)

            bot.edit_message_text("Jarayonda... 100%", message.chat.id, progress_msg.message_id)

            with open(output_file, "rb") as f:
                safe_name = f"translated_{Path(file_name).stem}.docx"
                bot.send_document(message.chat.id, f, visible_file_name=safe_name)

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")

        finally:
            remove_file(file_path)
            if output_file:
                remove_file(output_file)
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, "Orqaga qaytdingiz 🔙", reply_markup=get_menu())

    @bot.message_handler(func=lambda m: m.text == "Adminga murojaat 👨‍💻")
    def admin_handler(message: Message):
        clear_state(message.chat.id)
        bot.send_message(message.chat.id, "Lichka: @musulmon_0319\nTelefon raqam: +998712000540")