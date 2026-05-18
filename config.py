"""
Configuration module for the Multimodal AI Telegram Bot.
Loads environment variables, validates required keys,
and provides centralized settings with dataclass.
Updated: Better structure, validation, type safety.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    """Application configuration with validation."""

    # ============================================
    # REQUIRED API KEYS
    # ============================================
    TELEGRAM_BOT_TOKEN: str
    DEEPSEEK_API_KEY: str
    
    # ============================================
    # OPTIONAL API KEYS
    # ============================================
    GITHUB_TOKEN: Optional[str] = None

    # ============================================
    # DEEPSEEK API SETTINGS
    # ============================================
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_CODER_MODEL: str = "deepseek-v4-flash"      # For thinking mode & code gen
    DEEPSEEK_FLASH_MODEL: str = "deepseek-chat"          # For chat & blueprints
    DEEPSEEK_MODEL: str = "deepseek-chat"                # Default model
    
    # Token & Temperature
    MAX_TOKENS_CODER: int = 4000
    MAX_TOKENS_FLASH: int = 4000
    DEEPSEEK_MAX_TOKENS: int = 2048
    TEMPERATURE_CODER: float = 0.1
    TEMPERATURE_FLASH: float = 0.5
    DEEPSEEK_TEMPERATURE: float = 0.7

    # ============================================
    # DATABASE
    # ============================================
    DATABASE_PATH: str = "bot_sessions.db"

    # ============================================
    # FILE PATHS
    # ============================================
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    CACHE_DIR: Path = PROJECT_ROOT / "cache"

    # ============================================
    # SMART FEATURES
    # ============================================
    ENABLE_SMART_DETECTION: bool = True
    ENABLE_AUTO_ENHANCE: bool = False          # OFF - No Docker/CI-CD auto-add
    ENABLE_CACHING: bool = True
    AUTO_FIX_MISSING_FILES: bool = True
    SHOW_PROJECT_SIZE: bool = True
    ENABLE_PROGRESS_BAR: bool = True

    # ============================================
    # PROJECT SIZE LIMITS
    # ============================================
    MAX_FILES_BIG_PROJECT: int = 12
    MAX_FILES_MEDIUM_PROJECT: int = 8
    MAX_FILES_SMALL_PROJECT: int = 5
    MAX_TOTAL_CHARS: int = 500000

    # ============================================
    # AI BEHAVIOR
    # ============================================
    SELF_REVIEW_CODE: bool = True
    SELF_REVIEW_FULL_CONTENT: bool = True
    ADD_TESTS_FOR_BIG_PROJECTS: bool = False

    # ============================================
    # RATE LIMITING
    # ============================================
    MAX_PROJECTS_PER_HOUR: int = 5
    MAX_PROJECTS_PER_DAY: int = 20

    # ============================================
    # GITHUB SETTINGS
    # ============================================
    AUTO_ADD_TOPICS: bool = True
    AUTO_CREATE_LABELS: bool = True
    SMART_COMMIT_MESSAGES: bool = True
    DEFAULT_PRIVATE_REPO: bool = False

    # ============================================
    # FILE SIZE LIMITS
    # ============================================
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024
    MAX_SINGLE_FILE_LINES: int = 500

    # ============================================
    # TELEGRAM LIMITS
    # ============================================
    MAX_MESSAGE_LENGTH: int = 4096
    MAX_TEXT_LENGTH: int = 2000
    MAX_SUMMARY_LENGTH: int = 500

    # ============================================
    # TEXT-TO-SPEECH
    # ============================================
    TTS_LANG: str = "en"
    ENABLE_TTS: bool = False

    # ============================================
    # PROJECT MODE
    # ============================================
    PROJECT_MODE_ENABLED: bool = True

    # ============================================
    # OTHER
    # ============================================
    LOG_LEVEL: str = "INFO"
    ADMIN_USER_IDS: list = None
    
    def __post_init__(self):
        if self.ADMIN_USER_IDS is None:
            object.__setattr__(self, 'ADMIN_USER_IDS', [])

    @classmethod
    def from_env(cls) -> 'Config':
        """Create Config instance from environment variables with validation."""
        
        # Required variables
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_TOKEN')
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
        
        missing = []
        if not telegram_token:
            missing.append('TELEGRAM_BOT_TOKEN')
        if not deepseek_key:
            missing.append('DEEPSEEK_API_KEY')
            
        if missing:
            error_msg = f"❌ Missing required environment variables: {', '.join(missing)}"
            print(f"\n{error_msg}")
            print("Please add them to your .env file:")
            for var in missing:
                print(f"  - {var}")
            raise EnvironmentError(error_msg)

        # GitHub token (optional)
        github_token = os.environ.get('GITHUB_TOKEN')
        
        # Admin IDs
        admin_ids_str = os.environ.get('ADMIN_USER_IDS', '')
        admin_ids = [int(x) for x in admin_ids_str.split(',') if x.strip()] if admin_ids_str else []

        return cls(
            # Required
            TELEGRAM_BOT_TOKEN=telegram_token,
            DEEPSEEK_API_KEY=deepseek_key,
            
            # Optional
            GITHUB_TOKEN=github_token,
            
            # DeepSeek
            DEEPSEEK_BASE_URL=os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
            DEEPSEEK_CODER_MODEL=os.environ.get('DEEPSEEK_CODER_MODEL', 'deepseek-v4-flash'),
            DEEPSEEK_FLASH_MODEL=os.environ.get('DEEPSEEK_FLASH_MODEL', 'deepseek-chat'),
            DEEPSEEK_MODEL=os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
            MAX_TOKENS_CODER=int(os.environ.get('MAX_TOKENS_CODER', '4000')),
            MAX_TOKENS_FLASH=int(os.environ.get('MAX_TOKENS_FLASH', '4000')),
            DEEPSEEK_MAX_TOKENS=int(os.environ.get('DEEPSEEK_MAX_TOKENS', '2048')),
            TEMPERATURE_CODER=float(os.environ.get('TEMPERATURE_CODER', '0.1')),
            TEMPERATURE_FLASH=float(os.environ.get('TEMPERATURE_FLASH', '0.5')),
            DEEPSEEK_TEMPERATURE=float(os.environ.get('DEEPSEEK_TEMPERATURE', '0.7')),
            
            # Database
            DATABASE_PATH=os.environ.get('DATABASE_PATH', 'bot_sessions.db'),
            
            # Smart Features
            ENABLE_SMART_DETECTION=os.environ.get('ENABLE_SMART_DETECTION', 'true').lower() == 'true',
            ENABLE_AUTO_ENHANCE=os.environ.get('ENABLE_AUTO_ENHANCE', 'false').lower() == 'true',
            ENABLE_CACHING=os.environ.get('ENABLE_CACHING', 'true').lower() == 'true',
            AUTO_FIX_MISSING_FILES=os.environ.get('AUTO_FIX_MISSING_FILES', 'true').lower() == 'true',
            
            # Limits
            MAX_FILES_BIG_PROJECT=int(os.environ.get('MAX_FILES_BIG_PROJECT', '12')),
            MAX_FILES_MEDIUM_PROJECT=int(os.environ.get('MAX_FILES_MEDIUM_PROJECT', '8')),
            MAX_FILES_SMALL_PROJECT=int(os.environ.get('MAX_FILES_SMALL_PROJECT', '5')),
            
            # AI Behavior
            SELF_REVIEW_CODE=os.environ.get('SELF_REVIEW_CODE', 'true').lower() == 'true',
            SELF_REVIEW_FULL_CONTENT=os.environ.get('SELF_REVIEW_FULL_CONTENT', 'true').lower() == 'true',
            
            # Rate Limiting
            MAX_PROJECTS_PER_HOUR=int(os.environ.get('MAX_PROJECTS_PER_HOUR', '5')),
            MAX_PROJECTS_PER_DAY=int(os.environ.get('MAX_PROJECTS_PER_DAY', '20')),
            
            # TTS
            TTS_LANG=os.environ.get('TTS_LANG', 'en'),
            ENABLE_TTS=os.environ.get('ENABLE_TTS', 'false').lower() == 'true',
            
            # Project Mode
            PROJECT_MODE_ENABLED=os.environ.get('PROJECT_MODE_ENABLED', 'true').lower() == 'true',
            
            # Other
            LOG_LEVEL=os.environ.get('LOG_LEVEL', 'INFO'),
            ADMIN_USER_IDS=admin_ids,
        )


# ============================================
# SINGLETON CONFIG INSTANCE
# ============================================
try:
    config = Config.from_env()
    print("✅ Configuration loaded successfully!")
    print(f"🤖 Bot Token: {config.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"🧠 Coder Model: {config.DEEPSEEK_CODER_MODEL}")
    print(f"💬 Chat Model: {config.DEEPSEEK_FLASH_MODEL}")
    print(f"📊 Big Project Files: {config.MAX_FILES_BIG_PROJECT}")
    print(f"🎯 Smart Detection: {'ON' if config.ENABLE_SMART_DETECTION else 'OFF'}")
    print(f"🔧 Auto-Enhance: {'ON' if config.ENABLE_AUTO_ENHANCE else 'OFF'}")
    print(f"🔧 Auto-Fix Missing: {'ON' if config.AUTO_FIX_MISSING_FILES else 'OFF'}")
    print(f"🎤 TTS: {'ON' if config.ENABLE_TTS else 'OFF'}")
    print(f"📁 Project Mode: {'ON' if config.PROJECT_MODE_ENABLED else 'OFF'}")
    
    # Create directories
    Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
except EnvironmentError as e:
    print(f"\n❌ Configuration Error: {e}")
    print("Please set all required environment variables.")
    sys.exit(1)

# Export for easy import
__all__ = ["config", "Config", "PROJECT_ROOT"]
