import os
import io
import re
import cv2
import uuid
import time
import easyocr
import contextlib
import pdfplumber
import aspose.words as aw
from docx import Document
from deep_translator import GoogleTranslator
from keys import menu, confirm, translate
from states import ConvertState

BASE_DIR = "media"
PDF_DIR = os.path.join(BASE_DIR, "pdf")
WORD_DIR = os.path.join(BASE_DIR, "word")
OUT_DIR = os.path.join(BASE_DIR, "out")
IMG_DIR = os.path.join(BASE_DIR, "image")

for folder in [PDF_DIR, WORD_DIR, OUT_DIR, IMG_DIR]:
    os.makedirs(folder, exist_ok=True)

_READER = None

def get_ocr():
    global _READER
    if _READER is None:
        fake_out = io.StringIO()
        fake_err = io.StringIO()
        with contextlib.redirect_stdout(fake_out), contextlib.redirect_stderr(fake_err):
            _READER = easyocr.Reader(["en", "ru"], gpu=False)
    return _READER

def make_file_path(folder: str, ext: str):
    return os.path.join(folder, f"{uuid.uuid4().hex}.{ext}")

def progress_bar(bot, chat_id, text="Jarayonda!"):
    msg = bot.send_message(chat_id, f"{text}\n0%")
    for i in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        time.sleep(0.2)
        try:
            bot.edit_message_text(
                f"{text}\n{i}%",
                chat_id=chat_id,
                message_id=msg.message_id
            )
        except Exception:
            pass
    return msg

def download_file(bot, file_id: str, save_path: str):
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(save_path, "wb") as f:
        f.write(downloaded_file)
    return save_path

def pdf_to_word_convert(pdf_path: str) -> str:
    from pdf2docx import Converter

    output_path = make_file_path(OUT_DIR, "docx")
    cv = Converter(pdf_path)
    try:
        cv.convert(output_path, start=0, end=None)
    finally:
        cv.close()
    return output_path

def word_to_pdf_convert(docx_path: str) -> str:
    output_path = make_file_path(OUT_DIR, "pdf")
    doc = aw.Document(docx_path)
    doc.save(output_path)
    return output_path

def get_lang_code(lang_text: str) -> str:
    mapping = {
        "en 🏴": "en",
        "ru 🇷🇺": "ru",
        "uz 🇺🇿": "uz",
        "tr 🇹🇷": "tr",
    }
    return mapping.get(lang_text, "")

def clean_ocr_text(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9А-Яа-яЁёЎўҚқҒғҲҳ.,!?():;%\"'\- \n]", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) < 3:
            continue

        letters = sum(ch.isalpha() for ch in line)
        digits = sum(ch.isdigit() for ch in line)

        if letters + digits < 2:
            continue

        lines.append(line)

    return "\n".join(lines).strip()

def image_to_text_ocr(image_path: str) -> str:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Rasm ochilmadi")

    img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    processed = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15
    )

    reader = get_ocr()
    result = reader.readtext(processed, detail=1, paragraph=False)

    if not result:
        return ""

    items = []
    for item in result:
        box, text, conf = item
        if conf < 0.35:
            continue

        x = min(point[0] for point in box)
        y = min(point[1] for point in box)
        items.append((y, x, text))

    if not items:
        return ""

    items.sort(key=lambda t: (round(t[0] / 20), t[1]))

    lines = []
    current_line = []
    current_y = None
    line_threshold = 25

    for y, x, text in items:
        if current_y is None:
            current_y = y
            current_line.append((x, text))
            continue

        if abs(y - current_y) <= line_threshold:
            current_line.append((x, text))
        else:
            current_line.sort(key=lambda z: z[0])
            lines.append(" ".join(t for _, t in current_line))
            current_line = [(x, text)]
            current_y = y

    if current_line:
        current_line.sort(key=lambda z: z[0])
        lines.append(" ".join(t for _, t in current_line))

    final_text = "\n".join(lines)
    return clean_ocr_text(final_text).strip()

def extract_text_from_pdf(pdf_path: str) -> str:
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                texts.append(txt)
    return "\n\n".join(texts).strip()

def extract_text_from_docx(docx_path: str) -> str:
    doc = Document(docx_path)
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(texts).strip()

def translate_big_text(text: str, target_lang: str) -> str:
    if not text.strip():
        return ""

    translator = GoogleTranslator(source="auto", target=target_lang)
    chunks = []
    step = 3000

    for i in range(0, len(text), step):
        part = text[i:i + step]
        translated = translator.translate(part)
        chunks.append(translated)

    return "\n".join(chunks).strip()

def clear_user_state(bot, message):
    try:
        bot.delete_state(message.from_user.id, message.chat.id)
    except Exception:
        pass

def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_cmd(message):
        clear_user_state(bot, message)
        username = message.from_user.username
        if username:
            text = f"Assalomu alaykum hurmatli @{username} 🙍‍♂️"
        else:
            text = f"Assalomu alaykum hurmatli {message.from_user.full_name} 🙍‍♂️"

        bot.send_message(
            message.chat.id,
            f"{text}\n\nQuyidagi tugmalardan birini tanlang 👇",
            reply_markup=menu
        )

    @bot.message_handler(func=lambda m: m.text == "Pdf 📁")
    def pdf_menu(message):
        clear_user_state(bot, message)
        bot.set_state(message.from_user.id, ConvertState.ask_pdf, message.chat.id)
        bot.send_message(
            message.chat.id,
            "PDF ni Word ga o'girmoqchimisiz? 🔄",
            reply_markup=confirm
        )

    @bot.message_handler(state=ConvertState.ask_pdf, func=lambda m: m.text == "Ha ✅")
    def pdf_yes(message):
        bot.set_state(message.from_user.id, ConvertState.waiting_pdf_file, message.chat.id)
        bot.send_message(message.chat.id, "Pdf file tashlang 📁", reply_markup=menu)

    @bot.message_handler(state=ConvertState.ask_pdf, func=lambda m: m.text == "Yo'q ❌")
    def pdf_no(message):
        clear_user_state(bot, message)
        bot.send_message(message.chat.id, "Orqaga qaytdi 🔙", reply_markup=menu)

    @bot.message_handler(state=ConvertState.waiting_pdf_file, content_types=["document"])
    def get_pdf_file(message):
        doc = message.document

        if not doc.file_name or not doc.file_name.lower().endswith(".pdf"):
            bot.send_message(message.chat.id, "Faqat PDF file tashlang 📁")
            return

        pdf_path = make_file_path(PDF_DIR, "pdf")
        download_file(bot, doc.file_id, pdf_path)
        prog = progress_bar(bot, message.chat.id, "PDF Word ga o'girilmoqda 🔄")

        try:
            docx_path = pdf_to_word_convert(pdf_path)
            bot.edit_message_text("Tayyor ✅", message.chat.id, prog.message_id)

            with open(docx_path, "rb") as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption="Mana Word faylingiz 📁",
                    reply_markup=menu
                )
        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
        finally:
            clear_user_state(bot, message)

    @bot.message_handler(func=lambda m: m.text == "Word 📁")
    def word_menu(message):
        clear_user_state(bot, message)
        bot.set_state(message.from_user.id, ConvertState.ask_word, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Word ni PDF ga o'girmoqchimisiz? 🔄",
            reply_markup=confirm
        )

    @bot.message_handler(state=ConvertState.ask_word, func=lambda m: m.text == "Ha ✅")
    def word_yes(message):
        bot.set_state(message.from_user.id, ConvertState.waiting_word_file, message.chat.id)
        bot.send_message(message.chat.id, "Word file tashlang (.docx) 📁", reply_markup=menu)

    @bot.message_handler(state=ConvertState.ask_word, func=lambda m: m.text == "Yo'q ❌")
    def word_no(message):
        clear_user_state(bot, message)
        bot.send_message(message.chat.id, "Orqaga qaytdi 🔙", reply_markup=menu)

    @bot.message_handler(state=ConvertState.waiting_word_file, content_types=["document"])
    def get_word_file(message):
        doc = message.document

        if not doc.file_name or not doc.file_name.lower().endswith(".docx"):
            bot.send_message(message.chat.id, "Faqat .docx formatdagi Word file tashlang 📁")
            return

        word_path = make_file_path(WORD_DIR, "docx")
        download_file(bot, doc.file_id, word_path)
        prog = progress_bar(bot, message.chat.id, "Word PDF ga o'girilmoqda 🔄")

        try:
            pdf_path = word_to_pdf_convert(word_path)
            bot.edit_message_text("Tayyor ✅", message.chat.id, prog.message_id)

            with open(pdf_path, "rb") as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption="Mana PDF faylingiz 📁",
                    reply_markup=menu
                )
        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
        finally:
            clear_user_state(bot, message)

    @bot.message_handler(func=lambda m: m.text == "Rasm 📸")
    def rasm_menu(message):
        clear_user_state(bot, message)
        bot.set_state(message.from_user.id, ConvertState.waiting_image, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Rasm tashlang. Faqat JPG, JPEG yoki PNG tiniq formatda bo'lsin 📸",
            reply_markup=menu
        )

    @bot.message_handler(state=ConvertState.waiting_image, content_types=["photo"])
    def get_image_photo(message):
        try:
            photo = message.photo[-1]
            image_path = make_file_path(IMG_DIR, "jpg")
            download_file(bot, photo.file_id, image_path)

            prog = progress_bar(bot, message.chat.id, "Rasm textga o'girilmoqda 🔄")
            text = image_to_text_ocr(image_path)

            bot.edit_message_text("Tayyor ✅", message.chat.id, prog.message_id)

            if not text.strip():
                bot.send_message(message.chat.id, "Rasm ichidan aniq text topilmadi ❌", reply_markup=menu)
                return

            for i in range(0, len(text), 4000):
                bot.send_message(message.chat.id, text[i:i + 4000], reply_markup=menu)

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
        finally:
            clear_user_state(bot, message)

    @bot.message_handler(state=ConvertState.waiting_image, content_types=["document"])
    def get_image_document(message):
        try:
            doc = message.document
            file_name = (doc.file_name or "").lower()

            if not file_name.endswith((".jpg", ".jpeg", ".png")):
                bot.send_message(
                    message.chat.id,
                    "Faqat JPG, JPEG yoki PNG formatdagi rasm tashlang 📸",
                    reply_markup=menu
                )
                return

            ext = file_name.split(".")[-1]
            image_path = make_file_path(IMG_DIR, ext)
            download_file(bot, doc.file_id, image_path)

            prog = progress_bar(bot, message.chat.id, "Rasm textga o'girilmoqda 🔄")
            text = image_to_text_ocr(image_path)

            bot.edit_message_text("Tayyor ✅", message.chat.id, prog.message_id)

            if not text.strip():
                bot.send_message(message.chat.id, "Rasm ichidan aniq text topilmadi ❌", reply_markup=menu)
                return

            for i in range(0, len(text), 4000):
                bot.send_message(message.chat.id, text[i:i + 4000], reply_markup=menu)

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
        finally:
            clear_user_state(bot, message)

    @bot.message_handler(func=lambda m: m.text == "Tarjima 🇺🇿")
    def translate_menu(message):
        clear_user_state(bot, message)
        bot.set_state(message.from_user.id, ConvertState.waiting_translate_file, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Pdf yoki docx file tashlang 📁\n\nRasm uchun: JPG, JPEG, PNG tiniq formatda tashlang 📸",
            reply_markup=menu
        )

    @bot.message_handler(state=ConvertState.waiting_translate_file, content_types=["document"])
    def get_translate_file(message):
        doc = message.document
        file_name = (doc.file_name or "").lower()

        if file_name.endswith(".pdf"):
            file_path = make_file_path(PDF_DIR, "pdf")
            file_type = "pdf"
        elif file_name.endswith(".docx"):
            file_path = make_file_path(WORD_DIR, "docx")
            file_type = "docx"
        elif file_name.endswith((".jpg", ".jpeg", ".png")):
            ext = file_name.split(".")[-1]
            file_path = make_file_path(IMG_DIR, ext)
            file_type = "image"
        else:
            bot.send_message(
                message.chat.id,
                "Faqat pdf, docx, jpg, jpeg yoki png file tashlang 📁",
                reply_markup=menu
            )
            return

        download_file(bot, doc.file_id, file_path)

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["translate_file"] = file_path
            data["translate_type"] = file_type

        bot.set_state(message.from_user.id, ConvertState.waiting_translate_lang, message.chat.id)
        bot.send_message(message.chat.id, "Tilni tanlang 👇", reply_markup=translate)

    @bot.message_handler(state=ConvertState.waiting_translate_file, content_types=["photo"])
    def get_translate_photo(message):
        photo = message.photo[-1]
        file_path = make_file_path(IMG_DIR, "jpg")
        download_file(bot, photo.file_id, file_path)

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["translate_file"] = file_path
            data["translate_type"] = "image"

        bot.set_state(message.from_user.id, ConvertState.waiting_translate_lang, message.chat.id)
        bot.send_message(message.chat.id, "Tilni tanlang 👇", reply_markup=translate)

    @bot.message_handler(
        state=ConvertState.waiting_translate_lang,
        func=lambda m: m.text in ["en 🏴", "ru 🇷🇺", "uz 🇺🇿", "tr 🇹🇷"]
    )
    def choose_translate_lang(message):
        lang_code = get_lang_code(message.text)

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            file_path = data.get("translate_file")
            file_type = data.get("translate_type")

        prog = progress_bar(bot, message.chat.id, f"{lang_code} tiliga tarjima qilinmoqda 🔄")

        try:
            if file_type == "pdf":
                original_text = extract_text_from_pdf(file_path)
            elif file_type == "docx":
                original_text = extract_text_from_docx(file_path)
            elif file_type == "image":
                original_text = image_to_text_ocr(file_path)
            else:
                bot.edit_message_text("Noma'lum file turi ❌", message.chat.id, prog.message_id)
                bot.send_message(message.chat.id, "File turi aniqlanmadi ❌", reply_markup=menu)
                return

            if not original_text.strip():
                bot.edit_message_text("File ichidan text topilmadi ❌", message.chat.id, prog.message_id)
                bot.send_message(message.chat.id, "File ichida tarjima qilinadigan text yo'q ❌", reply_markup=menu)
                clear_user_state(bot, message)
                return

            translated_text = translate_big_text(original_text, lang_code)
            bot.edit_message_text("Tayyor ✅", message.chat.id, prog.message_id)

            if not translated_text.strip():
                bot.send_message(message.chat.id, "Tarjima qilinmadi ❌", reply_markup=menu)
                return

            for i in range(0, len(translated_text), 4000):
                bot.send_message(message.chat.id, translated_text[i:i + 4000], reply_markup=menu)

        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
        finally:
            clear_user_state(bot, message)

    @bot.message_handler(state=ConvertState.waiting_translate_lang, func=lambda m: m.text == "Orqaga 🔙")
    def back_translate(message):
        clear_user_state(bot, message)
        bot.send_message(message.chat.id, "Orqaga qaytdi 🔙", reply_markup=menu)