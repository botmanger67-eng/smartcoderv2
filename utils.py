import io
import os
import logging
from typing import Optional, BinaryIO
from telegram import File, Update
from telegram.ext import ContextTypes

from config import Config
from database import Database
from ai_handler import AIHandler

logger = logging.getLogger(__name__)

async def download_file(
    file_id: str,
    context: ContextTypes.DEFAULT_TYPE,
    output_path: Optional[str] = None
) -> Optional[bytes]:
    """
    Download a file from Telegram by its file_id.
    Returns the file content as bytes, or None on failure.
    If output_path is given, also saves to disk.
    """
    try:
        file: File = await context.bot.get_file(file_id)
        if output_path:
            await file.download_to_drive(output_path)
            with open(output_path, "rb") as f:
                return f.read()
        else:
            return await file.download_as_bytearray()
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        return None

async def process_voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ai_handler: AIHandler
) -> str:
    """
    Process a voice message: download, transcribe, and return text.
    Falls back to a placeholder if transcription is unavailable.
    """
    try:
        voice = update.message.voice
        if not voice:
            return "No voice data found."

        # Download voice as OGG file
        file_bytes = await download_file(voice.file_id, context)
        if not file_bytes:
            return "Failed to download voice message."

        # Attempt transcription via AIHandler (if it supports audio)
        text = await ai_handler.transcribe_audio(file_bytes)
        if text:
            return text

        # Fallback: return placeholder
        return "Voice message received (transcription not implemented)."
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        return "Error processing voice."

async def process_image_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ai_handler: AIHandler
) -> Optional[str]:
    """
    Process an image message: download and extract text/description.
    Returns a string description or None.
    """
    try:
        photo = update.message.photo
        if not photo:
            return None

        # Get the largest photo
        file_id = photo[-1].file_id
        file_bytes = await download_file(file_id, context)
        if not file_bytes:
            return None

        # Use AIHandler to analyze image (if supported)
        description = await ai_handler.analyze_image(file_bytes)
        return description or "Image received, but analysis not available."
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return None

def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """Check if the file extension is in the allowed set."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions

def read_file_as_bytes(file_path: str) -> Optional[bytes]:
    """Read a file and return its content as bytes."""
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None