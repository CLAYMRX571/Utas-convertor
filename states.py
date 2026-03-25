import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
PDF_DIR = MEDIA_DIR / "pdf"
DOCX_DIR = MEDIA_DIR / "docx"
OUT_DIR = MEDIA_DIR / "out"

for folder in [MEDIA_DIR, PDF_DIR, DOCX_DIR, OUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

USER_STATE: dict[int, dict] = {}

def set_state(user_id: int, **kwargs):
    USER_STATE[user_id] = kwargs

def get_state(user_id: int) -> dict:
    return USER_STATE.get(user_id, {})

def clear_state(user_id: int):
    data = USER_STATE.pop(user_id, {})
    file_path = data.get("file_path")
    if file_path:
        try:
            p = Path(file_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

def unique_path(folder: Path, ext: str) -> Path:
    return folder / f"{uuid.uuid4().hex}.{ext}"