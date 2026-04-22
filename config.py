"""Gemini Bot configuration — loaded from .env."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# ==================== Telegram Configuration ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0")) if os.getenv("TELEGRAM_CHAT_ID") else 0

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

# ==================== Gemini Configuration ====================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemma-3-1b-it")
GEMINI_MAX_TURNS = int(os.getenv("GEMINI_MAX_TURNS", "15"))
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "600"))

# Working directory for sessions
WORK_DIR = Path(os.getenv("WORK_DIR", str(PROJECT_ROOT / "workspace")))

# Groq Whisper API (optional, for voice messages)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Database
DB_PATH = PROJECT_ROOT / "data" / "bot.db"

# Limits
MESSAGE_QUEUE_MAX = 5
SESSION_IDLE_TIMEOUT_HOURS = 48


def set_env_var(key: str, value: str):
    """Write or update a variable in .env file and apply to current process."""
    lines = []
    found = False

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break

def set_env_var(key: str, value: str):
    """Write or update a variable in .env file and apply to current process."""
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

