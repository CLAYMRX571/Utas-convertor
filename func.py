import os
import io
import uuid
import asyncio
import re
import cv2
import easyocr
import contextlib
import aspose.words as aw
import numpy as np
import pdfplumber
from docx import Document
from deep_translator import GoogleTranslator
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from keys import menu, confirm, translate
from states import ConvertState

router = Router()

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

async def progress_bar(message: Message, text: str = "Jarayonda!"):
    msg = await message.answer(f"{text}\n0%")
    for i in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        await asyncio.sleep(0.2)
        try:
            await msg.edit_text(f"{text}\n{i}%")
        except Exception:
            pass
    return msg

async def download_file(bot, file_id: str, save_path: str):
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, destination=save_path)
    return save_path

async def pdf_to_word_convert(pdf_path: str) -> str:
    from pdf2docx import Converter

    output_path = make_file_path(OUT_DIR, "docx")

    def run():
        cv = Converter(pdf_path)
        try:
            cv.convert(output_path, start=0, end=None)
        finally:
            cv.close()

    await asyncio.to_thread(run)
    return output_path

async def word_to_pdf_convert(docx_path: str) -> str:
    output_path = make_file_path(OUT_DIR, "pdf")

    def run():
        doc = aw.Document(docx_path)
        doc.save(output_path)

    await asyncio.to_thread(run)
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

async def image_to_text_ocr(image_path: str) -> str:
    def run():
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Rasm ochilmadi")

        img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

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
        final_text = clean_ocr_text(final_text)
        return final_text.strip()

    return await asyncio.to_thread(run)

async def extract_text_from_pdf(pdf_path: str) -> str:
    def run():
        texts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    texts.append(txt)

        return "\n\n".join(texts).strip()

    return await asyncio.to_thread(run)

async def extract_text_from_docx(docx_path: str) -> str:
    def run():
        doc = Document(docx_path)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(texts).strip()

    return await asyncio.to_thread(run)

async def translate_big_text(text: str, target_lang: str) -> str:
    def run():
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

    return await asyncio.to_thread(run)

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    username = message.from_user.username
    if username:
        text = f"Assalomu alaykum hurmatli @{username} 🙍‍♂️"
    else:
        text = f"Assalomu alaykum hurmatli {message.from_user.full_name} 🙍‍♂️"

    await message.answer(
        f"{text}\n\nQuyidagi tugmalardan birini tanlang 👇",
        reply_markup=menu
    )

@router.message(F.text == "Pdf 📁")
async def pdf_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ConvertState.ask_pdf)
    await message.answer("PDF ni Word ga o'girmoqchimisiz? 🔄", reply_markup=confirm)

@router.message(ConvertState.ask_pdf, F.text == "Ha ✅")
async def pdf_yes(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_pdf_file)
    await message.answer("Pdf file tashlang 📁", reply_markup=menu)

@router.message(ConvertState.ask_pdf, F.text == "Yo'q ❌")
async def pdf_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Orqaga qaytdi 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_pdf_file, F.document)
async def get_pdf_file(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".pdf"):
        await message.answer("Faqat PDF file tashlang 📁")
        return

    pdf_path = make_file_path(PDF_DIR, "pdf")
    await download_file(message.bot, doc.file_id, pdf_path)
    prog = await progress_bar(message, "PDF Word ga o'girilmoqda 🔄")

    try:
        docx_path = await pdf_to_word_convert(pdf_path)
        await prog.edit_text("Tayyor ✅")
        await message.answer_document(
            FSInputFile(docx_path),
            caption="Mana Word faylingiz 📁",
            reply_markup=menu
        )
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
    finally:
        await state.clear()

@router.message(F.text == "Word 📁")
async def word_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ConvertState.ask_word)
    await message.answer("Word ni PDF ga o'girmoqchimisiz? 🔄", reply_markup=confirm)

@router.message(ConvertState.ask_word, F.text == "Ha ✅")
async def word_yes(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_word_file)
    await message.answer("Word file tashlang (.docx) 📁", reply_markup=menu)

@router.message(ConvertState.ask_word, F.text == "Yo'q ❌")
async def word_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Orqaga qaytdi 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_word_file, F.document)
async def get_word_file(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".docx"):
        await message.answer("Faqat .docx formatdagi Word file tashlang 📁")
        return

    word_path = make_file_path(WORD_DIR, "docx")
    await download_file(message.bot, doc.file_id, word_path)
    prog = await progress_bar(message, "Word PDF ga o'girilmoqda 🔄")

    try:
        pdf_path = await word_to_pdf_convert(word_path)
        await prog.edit_text("Tayyor ✅")
        await message.answer_document(
            FSInputFile(pdf_path),
            caption="Mana PDF faylingiz 📁",
            reply_markup=menu
        )
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
    finally:
        await state.clear()

@router.message(F.text == "Rasm 📸")
async def rasm_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ConvertState.waiting_image)
    await message.answer(
        "Rasm tashlang. Faqat JPG, JPEG yoki PNG tiniq formatda bo'lsin 📸",
        reply_markup=menu
    )

@router.message(ConvertState.waiting_image, F.photo)
async def get_image_photo(message: Message, state: FSMContext):
    try:
        photo = message.photo[-1]
        image_path = make_file_path(IMG_DIR, "jpg")
        await download_file(message.bot, photo.file_id, image_path)
        prog = await progress_bar(message, "Rasm textga o'girilmoqda 🔄")
        text = await image_to_text_ocr(image_path)
        await prog.edit_text("Tayyor ✅")

        if not text or not text.strip():
            await message.answer("Rasm ichidan aniq text topilmadi ❌", reply_markup=menu)
            return

        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.answer(text[i:i + 4000], reply_markup=menu)
        else:
            await message.answer(text, reply_markup=menu)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
    finally:
        await state.clear()

@router.message(ConvertState.waiting_image, F.document)
async def get_image_document(message: Message, state: FSMContext):
    try:
        doc = message.document
        file_name = (doc.file_name or "").lower()

        if not file_name.endswith((".jpg", ".jpeg", ".png")):
            await message.answer("Faqat JPG, JPEG yoki PNG formatdagi rasm tashlang 📸", reply_markup=menu)
            return

        ext = file_name.split(".")[-1]
        image_path = make_file_path(IMG_DIR, ext)
        await download_file(message.bot, doc.file_id, image_path)
        prog = await progress_bar(message, "Rasm textga o'girilmoqda 🔄")
        text = await image_to_text_ocr(image_path)
        await prog.edit_text("Tayyor ✅")

        if not text or not text.strip():
            await message.answer("Rasm ichidan aniq text topilmadi ❌", reply_markup=menu)
            return

        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.answer(text[i:i + 4000], reply_markup=menu)
        else:
            await message.answer(text, reply_markup=menu)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
    finally:
        await state.clear()

@router.message(F.text == "Tarjima 🇺🇿")
async def translate_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ConvertState.waiting_translate_file)
    await message.answer("Pdf yoki docx file tashlang 📁\n\nRasm uchun: JPG, JPEG, PNG tiniq formatda tashlang 📸", reply_markup=menu)

@router.message(ConvertState.waiting_translate_file, F.document)
async def get_translate_file(message: Message, state: FSMContext):
    doc = message.document
    file_name = (doc.file_name or "").lower()

    if file_name.endswith(".pdf"):
        file_path = make_file_path(PDF_DIR, "pdf")
        file_type = "pdf"
    elif file_name.endswith(".docx"):
        file_path = make_file_path(WORD_DIR, "docx")
        file_type = "docx"
    elif file_name.endswith(".jpg"):
        file_path = make_file_path(IMG_DIR, "jpg")
        file_type = "image"
    elif file_name.endswith(".jpeg"):
        file_path = make_file_path(IMG_DIR, "jpeg")
        file_type = "image"
    elif file_name.endswith(".png"):
        file_path = make_file_path(IMG_DIR, "png")
        file_type = "image"
    else:
        await message.answer("Faqat pdf, docx, jpg, jpeg yoki png file tashlang 📁", reply_markup=menu)
        return

    await download_file(message.bot, doc.file_id, file_path)
    await state.update_data(translate_file=file_path, translate_type=file_type)
    await state.set_state(ConvertState.waiting_translate_lang)
    await message.answer("Tilni tanlang 👇", reply_markup=translate)

@router.message(ConvertState.waiting_translate_file, F.photo)
async def get_translate_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_path = make_file_path(IMG_DIR, "jpg")

    await download_file(message.bot, photo.file_id, file_path)
    await state.update_data(translate_file=file_path, translate_type="image")
    await state.set_state(ConvertState.waiting_translate_lang)
    await message.answer("Tilni tanlang 👇", reply_markup=translate)

@router.message(ConvertState.waiting_translate_lang, F.text.in_(["en 🏴", "ru 🇷🇺", "uz 🇺🇿", "tr 🇹🇷"]))
async def choose_translate_lang(message: Message, state: FSMContext):
    lang_text = message.text
    lang_code = get_lang_code(lang_text)
    data = await state.get_data()
    file_path = data.get("translate_file")
    file_type = data.get("translate_type")
    prog = await progress_bar(message, f"{lang_code} tiliga tarjima qilinmoqda 🔄")

    try:
        if file_type == "pdf":
            original_text = await extract_text_from_pdf(file_path)
        elif file_type == "docx":
            original_text = await extract_text_from_docx(file_path)
        elif file_type == "image":
            original_text = await image_to_text_ocr(file_path)
        else:
            await prog.edit_text("Noma'lum file turi ❌")
            await message.answer("File turi aniqlanmadi ❌", reply_markup=menu)
            return

        if not original_text.strip():
            await prog.edit_text("File ichidan text topilmadi ❌")
            await message.answer("File ichida tarjima qilinadigan text yo'q ❌", reply_markup=menu)
            await state.clear()
            return

        translated_text = await translate_big_text(original_text, lang_code)
        await prog.edit_text("Tayyor ✅")

        if not translated_text.strip():
            await message.answer("Tarjima qilinmadi ❌", reply_markup=menu)
        elif len(translated_text) > 4000:
            for i in range(0, len(translated_text), 4000):
                await message.answer(translated_text[i:i + 4000], reply_markup=menu)
        else:
            await message.answer(translated_text, reply_markup=menu)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=menu)
    finally:
        await state.clear()

@router.message(ConvertState.waiting_translate_lang, F.text == "Orqaga 🔙")
async def back_translate(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Orqaga qaytdi 🔙", reply_markup=menu)