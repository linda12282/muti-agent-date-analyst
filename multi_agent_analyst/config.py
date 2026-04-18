import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_SESSIONS = ROOT / "output" / "sessions"


def public_base_url() -> str:
    return os.getenv("ANALYST_PUBLIC_BASE_URL", "http://127.0.0.1:8765").rstrip("/")


def server_port() -> int:
    try:
        return int(os.getenv("PORT", "8765"))
    except ValueError:
        return 8765
