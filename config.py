import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

"""
Configuration module for the Multimodal AI Telegram Bot.
Loads environment variables and provides centralized settings.
"""

# Load environment variables from .env file (if present)
load_dotenv()

def _get_env(key: str, default: Optional[str] = None) -> str:
    """Retrieve an environment variable, raising an error if required and missing."""
    value = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value

# --- Telegram Bot ---
TELEGRAM_TOKEN: str = _get_env("TELEGRAM_TOKEN")

# --- DeepSeek AI ---
DEEPSEEK_API_KEY: str = _get_env("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

# --- GitHub Integration ---
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
GITHUB_REPO: Optional[str] = os.getenv("GITHUB_REPO")  # e.g., "username/repo"

# --- Database ---
DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join("data", "bot.db"))

# --- File Paths ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
CACHE_DIR: Path = PROJECT_ROOT / "cache"

# Ensure output and cache directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- Project Mode ---
PROJECT_MODE_ENABLED: bool = os.getenv("PROJECT_MODE_ENABLED", "false").lower() in ("true", "1", "yes")

# --- Telegram Message Limits ---
MAX_MESSAGE_LENGTH: int = 4096
MAX_TEXT_LENGTH: int = 2000  # For summarization
MAX_SUMMARY_LENGTH: int = 500

# --- Text-to-Speech (gTTS) ---
TTS_LANG: str = os.getenv("TTS_LANG", "en")

# --- Other ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
ADMIN_USER_IDS: list[int] = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()]