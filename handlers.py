import asyncio
from pathlib import Path
import pdfplumber
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message
from deep_translator import GoogleTranslator
from docx import Document
from keys import (
    ADMIN_PHONE,
    ADMIN_USERNAME,
    ILOVEPDF_PUBLIC_KEY,
    ILOVEPDF_SECRET_KEY,
    LANG_MAP,
    confirm_menu,
    main_menu,
    translate_menu,
)
from states import (
    DOCX_DIR,
    OUT_DIR,
    PDF_DIR,
    clear_state,
    get_state,
    set_state,
    unique_path,
)

async def send_progress(message: Message, title: str):
    msg = await message.answer(f"{title}\n0%")
    for percent in range(10, 101, 10):
        await asyncio.sleep(0.15)
        try:
            await msg.edit_text(f"{title}\n{percent}%")
        except Exception:
            pass
    return msg

async def download_telegram_file(bot: Bot, file_id: str, dest: Path) -> Path:
    tg_file = await bot.get_file(file_id)
    await bot.download(tg_file.file_path, destination=dest)
    return dest

def ilovepdf_auth() -> str:
    if not ILOVEPDF_PUBLIC_KEY or not ILOVEPDF_SECRET_KEY:
        raise RuntimeError("ILOVEPDF kalitlari topilmadi")

    response = requests.post(
        "https://api.ilovepdf.com/v1/auth",
        json={
            "public_key": ILOVEPDF_PUBLIC_KEY,
            "secret_key": ILOVEPDF_SECRET_KEY,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(f"iLovePDF auth xatolik: {data}")
    return token

def ilovepdf_start(tool: str, headers: dict) -> tuple[str, str]:
    response = requests.get(
        f"https://api.ilovepdf.com/v1/start/{tool}",
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    server = data.get("server")
    task = data.get("task")

    if not server or not task:
        raise RuntimeError(f"iLovePDF start xatolik: {data}")

    return server, task

def ilovepdf_upload(server: str, task: str, headers: dict, file_path: Path) -> str:
    with file_path.open("rb") as f:
        response = requests.post(
            f"https://{server}/v1/upload",
            headers=headers,
            data={"task": task},
            files={"file": (file_path.name, f)},
            timeout=180,
        )
    response.raise_for_status()
    data = response.json()

    server_filename = data.get("server_filename")
    if not server_filename:
        raise RuntimeError(f"Upload xatolik: {data}")

    return server_filename

def ilovepdf_download(server: str, task: str, headers: dict, output_path: Path) -> Path:
    response = requests.get(
        f"https://{server}/v1/download/{task}",
        headers=headers,
        timeout=180,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Natija fayl bo'sh chiqdi")

    return output_path

def pdf_to_word_convert(pdf_path: Path) -> Path:
    token = ilovepdf_auth()
    headers = {"Authorization": f"Bearer {token}"}
    server, task = ilovepdf_start("pdfword", headers)
    server_filename = ilovepdf_upload(server, task, headers, pdf_path)

    process_response = requests.post(
        f"https://{server}/v1/process",
        headers=headers,
        json={
            "task": task,
            "tool": "pdfword",
            "files": [
                {
                    "server_filename": server_filename,
                    "filename": pdf_path.name,
                }
            ],
        },
        timeout=180,
    )
    process_response.raise_for_status()

    output_path = unique_path(OUT_DIR, "docx")
    return ilovepdf_download(server, task, headers, output_path)

def word_to_pdf_convert(docx_path: Path) -> Path:
    token = ilovepdf_auth()
    headers = {"Authorization": f"Bearer {token}"}
    server, task = ilovepdf_start("officepdf", headers)
    server_filename = ilovepdf_upload(server, task, headers, docx_path)

    process_response = requests.post(
        f"https://{server}/v1/process",
        headers=headers,
        json={
            "task": task,
            "tool": "officepdf",
            "files": [
                {
                    "server_filename": server_filename,
                    "filename": docx_path.name,
                }
            ],
        },
        timeout=180,
    )
    process_response.raise_for_status()

    output_path = unique_path(OUT_DIR, "pdf")
    return ilovepdf_download(server, task, headers, output_path)

def extract_text_from_docx(docx_path: Path) -> str:
    doc = Document(str(docx_path))
    parts = []
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            parts.append(txt)
    return "\n".join(parts).strip()

def extract_text_from_pdf(pdf_path: Path) -> str:
    texts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            if txt and txt.strip():
                texts.append(txt.strip())
    return "\n\n".join(texts).strip()

def translate_big_text(text: str, target_lang: str) -> str:
    if not text.strip():
        return ""

    translator = GoogleTranslator(source="auto", target=target_lang)
    chunks = []
    step = 3000

    for i in range(0, len(text), step):
        part = text[i:i + step]
        translated = translator.translate(part)
        if translated:
            chunks.append(translated)

    return "\n".join(chunks).strip()

def text_to_word_file(text: str) -> Path:
    output_path = unique_path(OUT_DIR, "docx")
    doc = Document()
    doc.add_heading("Foydalanuvchi matni", level=1)
    doc.add_paragraph(text)
    doc.save(str(output_path))
    return output_path

async def send_file_and_remove(message: Message, path: Path, caption: str):
    try:
        await message.answer_document(
            FSInputFile(path=str(path), filename=path.name),
            caption=caption,
            reply_markup=main_menu,
        )
    finally:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass

def register_handlers(dp: Dispatcher, bot: Bot):
    @dp.message(CommandStart())
    async def start_handler(message: Message):
        clear_state(message.from_user.id)
        username = message.from_user.full_name if message.from_user else "Foydalanuvchi"
        await message.answer(
            f"Assalomu alaykum, {username}\n\nKerakli bo'limni tanlang 👇",
            reply_markup=main_menu,
        )

    @dp.message(F.text == "Orqaga 🔙")
    async def back_handler(message: Message):
        clear_state(message.from_user.id)
        await message.answer("Orqaga qaytdi 🔙", reply_markup=main_menu)

    @dp.message(F.text == "Pdf 📁")
    async def pdf_start(message: Message):
        clear_state(message.from_user.id)
        set_state(message.from_user.id, step="waiting_pdf")
        await message.answer("PDF file tashlang 📁", reply_markup=main_menu)

    @dp.message(F.text == "Word 📁")
    async def word_start(message: Message):
        clear_state(message.from_user.id)
        set_state(message.from_user.id, step="waiting_word")
        await message.answer("Word file tashlang (.docx) 📁", reply_markup=main_menu)

    @dp.message(F.text == "Text ✉️")
    async def text_start(message: Message):
        clear_state(message.from_user.id)
        set_state(message.from_user.id, step="waiting_text")
        await message.answer("Matn yuboring ✍️", reply_markup=main_menu)

    @dp.message(F.text == "Tarjima 🌐")
    async def translate_start(message: Message):
        clear_state(message.from_user.id)
        set_state(message.from_user.id, step="waiting_translate_file")
        await message.answer("Word yoki PDF formatida tashlang 📁", reply_markup=main_menu)

    @dp.message(F.text == "Adminga murojaat 👨‍💻")
    async def admin_contact(message: Message):
        text = (
            "👨‍💻 Admin bilan bog'lanish:\n\n"
            f"📩 Lichka: @{ADMIN_USERNAME}\n"
            f"📞 Telefon: {ADMIN_PHONE}"
        )
        await message.answer(text, reply_markup=main_menu)

    @dp.message(F.document)
    async def document_handler(message: Message):
        data = get_state(message.from_user.id)
        step = data.get("step")
        document = message.document

        if not document or not document.file_name:
            await message.answer("Fayl topilmadi ❌", reply_markup=main_menu)
            return

        filename = document.file_name.lower()

        if step == "waiting_pdf":
            if not filename.endswith(".pdf"):
                await message.answer("Faqat PDF file tashlang 📁")
                return

            pdf_path = unique_path(PDF_DIR, "pdf")
            await download_telegram_file(bot, document.file_id, pdf_path)
            set_state(
                message.from_user.id,
                step="confirm_pdf_to_word",
                file_path=str(pdf_path),
                file_type="pdf",
            )
            await message.answer("Word ga o'girmoqchimisiz?", reply_markup=confirm_menu)
            return

        if step == "waiting_word":
            if not filename.endswith(".docx"):
                await message.answer("Faqat .docx formatdagi Word file tashlang 📁")
                return

            docx_path = unique_path(DOCX_DIR, "docx")
            await download_telegram_file(bot, document.file_id, docx_path)
            set_state(
                message.from_user.id,
                step="confirm_word_to_pdf",
                file_path=str(docx_path),
                file_type="docx",
            )
            await message.answer("PDF ga o'girmoqchimisiz?", reply_markup=confirm_menu)
            return

        if step == "waiting_translate_file":
            if filename.endswith(".pdf"):
                file_path = unique_path(PDF_DIR, "pdf")
                file_type = "pdf"
            elif filename.endswith(".docx"):
                file_path = unique_path(DOCX_DIR, "docx")
                file_type = "docx"
            else:
                await message.answer("Faqat PDF yoki DOCX file tashlang 📁")
                return

            await download_telegram_file(bot, document.file_id, file_path)
            set_state(
                message.from_user.id,
                step="waiting_translate_lang",
                file_path=str(file_path),
                file_type=file_type,
            )
            await message.answer("Tilni tanlang 👇", reply_markup=translate_menu)
            return

        await message.answer("Avval kerakli menyuni tanlang 👇", reply_markup=main_menu)

    @dp.message(F.text == "Ha ✅")
    async def confirm_yes(message: Message):
        data = get_state(message.from_user.id)
        step = data.get("step")
        file_path = data.get("file_path")

        if not file_path:
            await message.answer("Jarayon topilmadi. Qaytadan boshlang.", reply_markup=main_menu)
            clear_state(message.from_user.id)
            return

        src = Path(file_path)
        out = None

        try:
            if step == "confirm_pdf_to_word":
                prog = await send_progress(message, "PDF Word ga o'girilmoqda 🔄")
                out = pdf_to_word_convert(src)
                await prog.edit_text("Tayyor ✅")
                await send_file_and_remove(message, out, "Mana Word faylingiz 📁")
                clear_state(message.from_user.id)
                return

            if step == "confirm_word_to_pdf":
                prog = await send_progress(message, "Word PDF ga o'girilmoqda 🔄")
                out = word_to_pdf_convert(src)
                await prog.edit_text("Tayyor ✅")
                await send_file_and_remove(message, out, "Mana PDF faylingiz 📁")
                clear_state(message.from_user.id)
                return

            await message.answer("Tasdiqlash uchun jarayon yo'q.", reply_markup=main_menu)

        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=main_menu)
            clear_state(message.from_user.id)
        finally:
            try:
                if src.exists():
                    src.unlink()
            except Exception:
                pass

    @dp.message(F.text == "Yo'q ❌")
    async def confirm_no(message: Message):
        clear_state(message.from_user.id)
        await message.answer("Orqaga qaytdi 🔙", reply_markup=main_menu)

    @dp.message(F.text.in_(list(LANG_MAP.keys())))
    async def translate_lang(message: Message):
        data = get_state(message.from_user.id)
        if data.get("step") != "waiting_translate_lang":
            await message.answer("Avval fayl yuboring 📁", reply_markup=main_menu)
            return

        file_path = Path(data["file_path"])
        file_type = data["file_type"]
        lang_code = LANG_MAP[message.text]

        try:
            prog = await send_progress(message, f"{lang_code} tiliga tarjima qilinmoqda 🔄")

            if file_type == "pdf":
                original_text = extract_text_from_pdf(file_path)
            else:
                original_text = extract_text_from_docx(file_path)

            if not original_text.strip():
                await prog.edit_text("File ichidan text topilmadi ❌")
                await message.answer("File ichida tarjima qilinadigan text yo'q ❌", reply_markup=main_menu)
                clear_state(message.from_user.id)
                return

            translated_text = translate_big_text(original_text, lang_code)

            await prog.edit_text("Tayyor ✅")

            if not translated_text.strip():
                await message.answer("Tarjima qilinmadi ❌", reply_markup=main_menu)
                clear_state(message.from_user.id)
                return

            for i in range(0, len(translated_text), 4000):
                part = translated_text[i:i + 4000]
                if i + 4000 >= len(translated_text):
                    await message.answer(part, reply_markup=main_menu)
                else:
                    await message.answer(part)

        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=main_menu)
        finally:
            clear_state(message.from_user.id)

    @dp.message(F.text)
    async def text_handler(message: Message):
        data = get_state(message.from_user.id)

        if data.get("step") == "waiting_text":
            text = (message.text or "").strip()
            if not text:
                await message.answer("Matn bo'sh bo'lmasligi kerak")
                return

            try:
                out = text_to_word_file(text)
                await send_file_and_remove(message, out, "Word faylingiz tayyor ✅")
            except Exception as e:
                await message.answer(f"Xatolik yuz berdi: {e} ❌", reply_markup=main_menu)
            finally:
                clear_state(message.from_user.id)
            return

        await message.answer("Kerakli tugmani tanlang 👇", reply_markup=main_menu)