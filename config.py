"""
Temka Bot Configuration
Loading and managing environment variables from .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# ==================== Telegram Configuration ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BOT_PUBLIC = os.getenv("BOT_PUBLIC", "false").strip().lower() in ("1", "true", "yes", "on")
ALLOWED_CHAT_IDS = [
    int(chat_id.strip())
    for chat_id in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
    if chat_id.strip().isdigit()
]

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")

ADMIN_CHAT_ID = None
if TELEGRAM_CHAT_ID:
    try:
        ADMIN_CHAT_ID = int(TELEGRAM_CHAT_ID)
    except ValueError:
        raise ValueError("TELEGRAM_CHAT_ID must be a valid integer")

AUTHORIZED_CHAT_IDS = set(ALLOWED_CHAT_IDS)
if ADMIN_CHAT_ID is not None:
    AUTHORIZED_CHAT_IDS.add(ADMIN_CHAT_ID)

if not BOT_PUBLIC and not AUTHORIZED_CHAT_IDS:
    raise ValueError("TELEGRAM_CHAT_ID or ALLOWED_CHAT_IDS is required unless BOT_PUBLIC is enabled.")

# ==================== Optional API Keys and endpoints ====================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "whisper-1")
GROQ_API_URL = os.getenv("GROQ_API_URL", f"https://api.groq.io/v1/whisper?model={GROQ_MODEL}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "text-bison-001")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    f"https://gemini.googleapis.com/v1/models/{GEMINI_MODEL}:generate",
)
GEMINI_IMAGEN_API_URL = os.getenv(
    "GEMINI_IMAGEN_API_URL",
    "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:generateImage"
)

# ==================== Configuration helpers ====================
def set_env_var(key: str, value: str):
    """Write or update a variable in .env file and apply it to the current process."""
    lines = []
    found = False

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break

    if not found:
        lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


def reload_groq_key():
    """Reload GROQ_API_KEY from .env into module-level variable."""
    global GROQ_API_KEY
    load_dotenv(ENV_PATH, override=True)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def reload_gemini_key():
    """Reload GEMINI_API_KEY from .env into module-level variable."""
    global GEMINI_API_KEY
    load_dotenv(ENV_PATH, override=True)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
