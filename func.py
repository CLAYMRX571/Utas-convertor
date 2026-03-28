from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from aiogram.types import Message, FSInputFile
from deep_translator import GoogleTranslator
from reportlab.pdfbase.ttfonts import TTFont
from aiogram.fsm.context import FSMContext
from rapidocr_onnxruntime import RapidOCR
from aiogram.filters import CommandStart
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from states import ConvertState
from keys import menu, confirm, lang
from aiogram import Router, F
from PyPDF2 import PdfReader
from docx2pdf import convert
from docx.shared import Pt
from docx import Document
from pathlib import Path
import os
import uuid
import asyncio
import pdfplumber
import fitz  

router = Router()

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
PDF_DIR = MEDIA_DIR / "pdf"
TRANSLATE_DIR = MEDIA_DIR / "translate"
DOCX_DIR = MEDIA_DIR / "docx"
OUT_DIR = MEDIA_DIR / "out"

TRANSLATE_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
DOCX_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

ocr_engine = RapidOCR()

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

def add_styled_paragraph(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)

def set_doc_defaults(doc: Document):
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

def add_paragraph(doc: Document, text: str, bold: bool = False, center: bool = False):
    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER if center else WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    return p

def set_cell_text(cell, text: str):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    run = p.add_run("" if text is None else str(text))
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)

def add_table_to_doc(doc: Document, table_data: list[list[str]]):
    if not table_data:
        return

    max_cols = max(len(row) for row in table_data) if table_data else 0
    if max_cols == 0:
        return

    table = doc.add_table(rows=len(table_data), cols=max_cols)
    table.style = "Table Grid"

    for i, row in enumerate(table_data):
        for j in range(max_cols):
            value = row[j] if j < len(row) else ""
            set_cell_text(table.cell(i, j), value)

    doc.add_paragraph("")

def safe_extract_tables(page):
    try:
        tables = page.extract_tables()
        return tables if tables else []
    except Exception:
        return []

def safe_extract_text(page):
    try:
        txt = page.extract_text()
        return txt.strip() if txt else ""
    except Exception:
        return ""
    
def detect_pdf_type(pdf_path: str) -> str:
    """
    natija:
    - text_pdf
    - image_pdf
    - mixed_pdf
    """
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        if total_pages == 0:
            return "image_pdf"

        text_pages = 0
        empty_pages = 0

        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            if is_meaningful_text(text):
                text_pages += 1
            else:
                empty_pages += 1

        if text_pages == total_pages:
            return "text_pdf"
        elif text_pages == 0:
            return "image_pdf"
        else:
            return "mixed_pdf"

    except Exception:
        return "image_pdf"
    
def page_to_ocr_text(page_fitz: fitz.Page) -> str:
    pix = page_fitz.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    img_bytes = pix.tobytes("png")
    result, _ = ocr_engine(img_bytes)

    lines = []
    if result:
        for item in result:
            if len(item) >= 2:
                txt = str(item[1]).strip()
                if txt:
                    lines.append(txt)

    return clean_text("\n".join(lines))

def extract_text_pdf_with_tables(pdf_path: str, output_docx: str):
    doc = Document()
    set_doc_defaults(doc)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = safe_extract_text(page)
            page_tables = safe_extract_tables(page)

            has_text = is_meaningful_text(page_text)
            has_tables = len(page_tables) > 0

            if has_text:
                cleaned = clean_text(page_text)
                for line in cleaned.split("\n"):
                    line = line.strip()
                    if line:
                        add_paragraph(doc, line)

            if has_tables:
                for tbl in page_tables:
                    normalized_table = []

                    for row in tbl:
                        if row is None:
                            continue

                        normalized_row = []
                        for cell in row:
                            normalized_row.append("" if cell is None else clean_text(str(cell)))

                        normalized_table.append(normalized_row)

                    if normalized_table:
                        add_table_to_doc(doc, normalized_table)

            doc.add_paragraph("")

    doc.save(output_docx)

def extract_mixed_or_image_pdf(pdf_path: str, output_docx: str):
    doc = Document()
    set_doc_defaults(doc)

    pdf_fitz = fitz.open(pdf_path)

    with pdfplumber.open(pdf_path) as plumber_pdf:
        total_pages = len(plumber_pdf.pages)

        for idx in range(total_pages):

            plumber_page = plumber_pdf.pages[idx]
            page_text = safe_extract_text(plumber_page)
            page_tables = safe_extract_tables(plumber_page)

            if is_meaningful_text(page_text):
                cleaned = clean_text(page_text)

                for line in cleaned.split("\n"):
                    line = line.strip()
                    if line:
                        add_paragraph(doc, line)

                if page_tables:
                    for tbl in page_tables:
                        normalized_table = []

                        for row in tbl:
                            if row is None:
                                continue

                            normalized_row = []
                            for cell in row:
                                normalized_row.append(
                                    "" if cell is None else clean_text(str(cell))
                                )

                            normalized_table.append(normalized_row)

                        if normalized_table:
                            add_table_to_doc(doc, normalized_table)

            else:
                ocr_text = page_to_ocr_text(pdf_fitz.load_page(idx))

                if ocr_text:
                    for line in ocr_text.split("\n"):
                        line = line.strip()
                        if line:
                            add_paragraph(doc, line)

            doc.add_paragraph("")

    pdf_fitz.close()
    doc.save(output_docx)
    
async def safe_edit_message(msg: Message, text: str):
    try:
        await msg.edit_text(text)
    except Exception:
        pass

async def convert_pdf_to_word(pdf_path: str, output_docx: str, progress_msg: Message) -> str:
    await safe_edit_message(progress_msg, "Jarayonda... 5%\n")

    pdf_type = await asyncio.to_thread(detect_pdf_type, pdf_path)

    if pdf_type == "text_pdf":
        await safe_edit_message(progress_msg, "Jarayonda... 25%\n")
        await asyncio.to_thread(extract_text_pdf_with_tables, pdf_path, output_docx)
        await safe_edit_message(progress_msg, "Jarayonda... 100%\n")
        return "text_pdf_with_tables"

    elif pdf_type == "mixed_pdf":
        await safe_edit_message(progress_msg, "Jarayonda... 20%\n")
        await asyncio.to_thread(extract_mixed_or_image_pdf, pdf_path, output_docx)
        await safe_edit_message(progress_msg, "Jarayonda... 100%\n")
        return "mixed_pdf"

    else:
        await safe_edit_message(progress_msg, "Jarayonda... 20%\n")
        await asyncio.to_thread(extract_mixed_or_image_pdf, pdf_path, output_docx)
        await safe_edit_message(progress_msg, "Jarayonda... 100%\n")
        return "image_pdf_ocr"
    
def convert_docx_to_pdf(docx_path: str, output_pdf: str) -> str:
    convert(docx_path, output_pdf)

    if not os.path.exists(output_pdf):
        raise FileNotFoundError("PDF fayl yaratilmadi.")

    return output_pdf

async def safe_edit_message(msg: Message, text: str):
    try:
        await msg.edit_text(text)
    except Exception:
        pass

async def progress_bar(progress_msg: Message):
    for i in range(10, 100, 10):
        await asyncio.sleep(0.35)
        await safe_edit_message(progress_msg, f"Jarayonda... {i}%")

def create_word_from_text(text: str, output_docx: str):
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)

    paragraphs = text.split("\n")

    for line in paragraphs:
        line = line.strip()
        if line:
            p = doc.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            run = p.add_run(line)
            run.font.name = "Times New Roman"
            run.font.size = Pt(14)

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

def split_text_into_chunks(text: str, max_length: int = 4000) -> list[str]:
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

    chunks = split_text_into_chunks(text, max_length=4000)
    translated_chunks = []

    translator = GoogleTranslator(source="auto", target=target_lang)

    for chunk in chunks:
        translated = translator.translate(chunk)
        translated_chunks.append(translated)

    return "\n\n".join(translated_chunks).strip()

def create_docx_from_text(text: str, output_docx: str):
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    for line in text.split("\n"):
        line = line.strip()
        if line:
            p = doc.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            run = p.add_run(line)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)

    doc.save(output_docx)

def wrap_text_for_pdf(text: str, max_chars: int = 95) -> list[str]:
    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

def create_pdf_from_text(text: str, output_pdf: str):
    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    x_margin = 45
    y = height - 50
    line_height = 16

    font_name = "Helvetica"
    font_size = 11

    c.setFont(font_name, font_size)

    paragraphs = text.split("\n")

    for para in paragraphs:
        para = para.strip()

        if not para:
            y -= line_height
            if y < 50:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - 50
            continue

        wrapped_lines = wrap_text_for_pdf(para, max_chars=95)

        for line in wrapped_lines:
            if y < 50:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - 50

            c.drawString(x_margin, y, line)
            y -= line_height

        y -= 4

    c.save()

@router.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    if user.username:
        text = f"Assalomu alaykum hurmatli foydalanuvchi @{user.username}\nTugmalardan birini tanlang 👇"
    else:
        text = f"Assalomu alaykum hurmatli foydalanuvchi {user.full_name}\nTugmalardan birini tanlang 👇"

    await message.answer(text, reply_markup=menu)

@router.message(F.text == "Pdf 📁")
async def pdf_button_handler(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_pdf)
    await message.answer("Pdf file tashlang (.pdf)", reply_markup=menu)

@router.message(ConvertState.waiting_pdf, F.document)
async def get_pdf_file(message: Message, state: FSMContext):
    document = message.document

    if not document.file_name.lower().endswith(".pdf"):
        await message.answer("Faqat .pdf formatdagi fayl yuboring.")
        return

    file_path = make_file_path(PDF_DIR, ".pdf")

    try:
        await message.bot.download(document, destination=file_path)
    except Exception as e:
        await message.answer(f"Fayl yuklashda xatolik: {e}")
        return

    await state.update_data(
        pdf_path=str(file_path),
        pdf_name=document.file_name
    )
    await state.set_state(ConvertState.waiting_pdf_confirm)

    await message.answer(
        "PDF'ni Word'ga o'girmoqchimisiz?",
        reply_markup=confirm
    )

@router.message(ConvertState.waiting_pdf, ~F.document)
async def waiting_pdf_invalid(message: Message):
    await message.answer("Iltimos, .pdf fayl yuboring.")

@router.message(ConvertState.waiting_pdf_confirm, F.text == "Ha ✅")
async def pdf_confirm_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    pdf_path = data.get("pdf_path")
    pdf_name = data.get("pdf_name", "file.pdf")

    if not pdf_path or not os.path.exists(pdf_path):
        await state.clear()
        await message.answer("PDF topilmadi. Qaytadan yuboring.", reply_markup=menu)
        return

    output_docx = make_file_path(OUT_DIR, ".docx")
    progress_msg = await message.answer("Jarayonda... 0%")

    try:
        result_type = await convert_pdf_to_word(
            pdf_path=pdf_path,
            output_docx=str(output_docx),
            progress_msg=progress_msg
        )

        docx_file = FSInputFile(str(output_docx))

        await message.answer_document(document=docx_file)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    finally:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass

        await state.clear()
        await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_pdf_confirm, F.text == "Yo'q ❌")
async def pdf_confirm_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(F.text == "Word 📁")
async def word_handler(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_docx)
    await message.answer("Word file tashlang (.docx)", reply_markup=menu)

@router.message(ConvertState.waiting_docx, F.document)
async def get_docx_file(message: Message, state: FSMContext):
    document = message.document

    if not document.file_name.lower().endswith(".docx"):
        await message.answer("Faqat .docx formatdagi fayl yuboring.")
        return

    file_path = make_file_path(DOCX_DIR, ".docx")

    try:
        await message.bot.download(document, destination=file_path)
    except Exception as e:
        await message.answer(f"Fayl yuklashda xatolik: {e}")
        return

    await state.update_data(
        docx_path=str(file_path),
        docx_name=document.file_name
    )
    await state.set_state(ConvertState.waiting_docx_confirm)

    await message.answer(
        "Word'ni PDF'ga o'girmoqchimisiz?",
        reply_markup=confirm
    )

@router.message(ConvertState.waiting_docx, ~F.document)
async def waiting_docx_invalid(message: Message):
    await message.answer("Iltimos, .docx fayl yuboring.")

@router.message(ConvertState.waiting_docx_confirm, F.text == "Ha ✅")
async def docx_confirm_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    docx_path = data.get("docx_path")
    docx_name = data.get("docx_name", ".docx")

    if not docx_path or not os.path.exists(docx_path):
        await state.clear()
        await message.answer("Word fayl topilmadi. Qaytadan yuboring.", reply_markup=menu)
        return

    progress_msg = await message.answer("Jarayonda... 0%")
    output_pdf = str(make_file_path(OUT_DIR, ".pdf"))

    try:
        for i in range(10, 60, 10):
            await asyncio.sleep(0.3)
            try:
                await progress_msg.edit_text(f"Jarayonda... {i}%")
            except:
                pass

        await asyncio.to_thread(convert_docx_to_pdf, docx_path, output_pdf)

        for i in range(60, 101, 10):
            await asyncio.sleep(0.2)
            try:
                await progress_msg.edit_text(f"Jarayonda... {i}%")
            except:
                pass

        pdf_file = FSInputFile(output_pdf)
        await message.answer_document(document=pdf_file)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    finally:
        try:
            if docx_path and os.path.exists(docx_path):
                os.remove(docx_path)
        except:
            pass

        try:
            if output_pdf and os.path.exists(output_pdf):
                os.remove(output_pdf)
        except:
            pass

        await state.clear()
        await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_docx_confirm, F.text == "Yo'q ❌")
async def docx_confirm_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(F.text == "Text ✉️")
async def text_handler(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_text)
    await message.answer("Matn yuboring!", reply_markup=menu)

@router.message(ConvertState.waiting_text, F.text)
async def get_text_and_convert_to_word(message: Message, state: FSMContext):
    text = message.text.strip()

    if not text:
        await message.answer("Matn yuboring!")
        return

    output_docx = make_file_path(OUT_DIR, ".docx")

    try:
        create_word_from_text(text, str(output_docx))

        docx_file = FSInputFile(str(output_docx), filename="matn.docx")
        await message.answer_document(document=docx_file)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    finally:
        try:
            if output_docx.exists():
                os.remove(output_docx)
        except Exception:
            pass

        await state.clear()
        await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_text)
async def invalid_text_input(message: Message):
    await message.answer("Iltimos, oddiy matn yuboring.")

@router.message(F.text == "Tarjima 🌐")
async def tarjima_handler(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_translate_file)
    await message.answer("docx yoki pdf file tashlang", reply_markup=menu)

@router.message(ConvertState.waiting_translate_file, F.document)
async def get_translate_file(message: Message, state: FSMContext):
    document = message.document
    file_name = document.file_name.lower()

    if not (file_name.endswith(".docx") or file_name.endswith(".pdf")):
        await message.answer("Faqat .docx yoki .pdf formatdagi fayl yuboring.")
        return

    suffix = ".docx" if file_name.endswith(".docx") else ".pdf"
    file_path = make_file_path(TRANSLATE_DIR, suffix)

    try:
        await message.bot.download(document, destination=file_path)
    except Exception as e:
        await message.answer(f"Fayl yuklashda xatolik: {e}")
        return

    await state.update_data(
        translate_file_path=str(file_path),
        translate_file_name=document.file_name,
        translate_file_type=suffix
    )
    await state.set_state(ConvertState.waiting_translate_lang)

    await message.answer("Tarjima tilini tanlang", reply_markup=lang)


@router.message(ConvertState.waiting_translate_file)
async def invalid_translate_file(message: Message):
    await message.answer("Iltimos, .docx yoki .pdf fayl yuboring.")


@router.message(ConvertState.waiting_translate_lang)
async def translate_file_by_lang(message: Message, state: FSMContext):
    data = await state.get_data()
    file_path = data.get("translate_file_path")
    file_name = data.get("translate_file_name", "file")
    file_type = data.get("translate_file_type")

    if message.text == "Orqaga 🔙":
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        await state.clear()
        await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)
        return

    # 🔥 TILNI TUGMADAN ANIQLASH
    if message.text == "🇺🇿 O'zbek":
        target_lang = "uz"
    elif message.text == "🇷🇺 Rus":
        target_lang = "ru"
    elif message.text == "🇬🇧 English":
        target_lang = "en"
    elif message.text == "🇹🇷 Turk":
        target_lang = "tr"
    else:
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return

    if not file_path or not os.path.exists(file_path):
        await state.clear()
        await message.answer("Fayl topilmadi. Qaytadan yuboring.", reply_markup=menu)
        return

    progress_msg = await message.answer("Jarayonda... 0%")
    output_file = None

    try:
        await safe_edit_message(progress_msg, "Jarayonda... 10%")

        if file_type == ".docx":
            extracted_text = await asyncio.to_thread(extract_text_from_docx, file_path)
        else:
            extracted_text = await asyncio.to_thread(extract_text_from_pdf, file_path)

        if not extracted_text.strip():
            await message.answer("Fayldan matn ajratilmadi.")
            return

        await safe_edit_message(progress_msg, "Jarayonda... 45%")

        translated_text = await asyncio.to_thread(
            translate_text,
            extracted_text,
            target_lang
        )

        await safe_edit_message(progress_msg, "Jarayonda... 75%")

        output_file = str(make_file_path(OUT_DIR, file_type))

        if file_type == ".docx":
            await asyncio.to_thread(create_docx_from_text, translated_text, output_file)
        else:
            await asyncio.to_thread(create_pdf_from_text, translated_text, output_file)

        await safe_edit_message(progress_msg, "Jarayonda... 100%")

        send_file = FSInputFile(
            output_file,
            filename=f"translated_{Path(file_name).stem}{file_type}"
        )

        await message.answer_document(document=send_file)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        try:
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
        except:
            pass

        await state.clear()
        await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_translate_lang, F.text == "Orqaga 🔙")
async def translate_back(message: Message, state: FSMContext):
    data = await state.get_data()
    file_path = data.get("translate_file_path")

    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    await state.clear()
    await message.answer("Orqaga qaytdingiz 🔙", reply_markup=menu)

@router.message(ConvertState.waiting_translate_lang)
async def invalid_translate_lang(message: Message):
    await message.answer("Iltimos, berilgan tillardan birini tanlang.")

@router.message(F.text == "Adminga murojaat 👨‍💻")
async def admin_handler(message: Message):
    await message.answer(f"Lichka: @{"musulmon_0319"}\nTelefon raqam: +998712000540")