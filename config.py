from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"

_db_path = Path(os.getenv("DB_PATH", "").strip() or (BASE_DIR / "data" / "bot.db"))
DB_PATH = _db_path if _db_path.is_absolute() else BASE_DIR / _db_path
