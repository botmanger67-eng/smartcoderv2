import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import Config
from database import Database, init_db, add_message, get_context, clear_context
from ai_handler import AIHandler
from github_manager import GitHubManager
from utils import (
    process_voice,
    process_image,
    process_sticker,
    process_document,
    sanitize_input,
    get_user_language,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Global instances (initialized lazily)
ai_handler: Optional[AIHandler] = None
github_manager: Optional[GitHubManager] = None
db: Optional[Database] = None
config: Optional[Config] = None


def initialize_services() -> Tuple[Config, Database, AIHandler, GitHubManager]:
    """Initialize configuration, database, AI handler and GitHub manager."""
    global config, db, ai_handler, github_manager
    if config is None:
        config = Config()
        db = Database(config.DATABASE_PATH)
        db.init_db()
        ai_handler = AIHandler(config)
        github_manager = GitHubManager(config)
    return config, db, ai_handler, github_manager


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message and mode selection."""
    try:
        user = update.effective_user
        await update.message.reply_text(
            f"Hello {user.first_name}! I'm a multimodal AI assistant.\n"
            "I can help you with text, voice, images, and more.\n\n"
            "Commands:\n"
            "/start - This message\n"
            "/help - Show help\n"
            "/mode - Switch between chat and project modes\n"
            "/clear - Clear conversation history\n"
            "/project - Project management commands\n"
            "/settings - Customize your experience",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("💬 Chat Mode", callback_data="mode_chat"),
            InlineKeyboardButton("📁 Project Mode", callback_data="mode_project"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - detailed help."""
    try:
        help_text = (
            "🤖 *Multimodal AI Bot Help*\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/mode - Switch between chat and project modes\n"
            "/clear - Clear conversation memory\n"
            "/project - Project management (in project mode)\n"
            "/settings - Change settings\n\n"
            "*Features:*\n"
            "• Send text, voice, images, stickers, documents\n"
            "• Memory across conversations (per user)\n"
            "• Project mode for code/development tasks\n"
            "• Voice output (optional)\n"
            "• GitHub integration for project mode\n\n"
            "*Supported input types:*\n"
            "- Text messages\n"
            "- Voice messages (via note or attachment)\n"
            "- Images and photos\n"
            "- Stickers (text extraction)\n"
            "- Documents (.txt, .pdf, .md, code files)\n\n"
            "*Usage:*\n"
            "• In chat mode, just send any message\n"
            "• In project mode, use /project commands\n"
            "• Clear memory with /clear if context gets cluttered"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again.")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mode command - switch between chat and project mode."""
    try:
        user_id = update.effective_user.id
        config, db, _, _ = initialize_services()
        current_mode = context.user_data.get("mode", "chat")
        new_mode = "project" if current_mode == "chat" else "chat"
        context.user_data["mode"] = new_mode
        mode_label = "Project" if new_mode == "project" else "Chat"
        await update.message.reply_text(
            f"✅ Switched to *{mode_label} Mode*.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error in mode handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again.")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command - clear conversation history."""
    try:
        user_id = update.effective_user.id
        db = initialize_services()[1]
        clear_context(db, user_id)
        await update.message.reply_text("🧹 Conversation history cleared.")
    except Exception as e:
        logger.error(f"Error in clear handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again.")


async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /project command - project management submenu."""
    try:
        user_id = update.effective_user.id
        mode = context.user_data.get("mode", "chat")
        if mode != "project":
            await update.message.reply_text(
                "You are not in project mode. Use /mode to switch."
            )
            return
        keyboard = [
            [InlineKeyboardButton("Create Repo", callback_data="project_create")],
            [InlineKeyboardButton("Push Code", callback_data="project_push")],
            [InlineKeyboardButton("List Issues", callback_data="project_issues")],
            [InlineKeyboardButton("Create Issue", callback_data="project_issue_create")],
            [InlineKeyboardButton("Back to Main", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📁 *Project Management*\nChoose an action:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error in project handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred.")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command - user preferences."""
    try:
        keyboard = [
            [InlineKeyboardButton("🌐 Language", callback_data="settings_language")],
            [InlineKeyboardButton("🔊 TTS Output", callback_data="settings_tts")],
            [InlineKeyboardButton("📏 Context Length", callback_data="settings_context")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ *Settings*\nCustomize your experience:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error in settings handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred.")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data
    try:
        if data == "mode_chat":
            context.user_data["mode"] = "chat"
            await query.edit_message_text("✅ Switched to *Chat Mode*.", parse_mode="Markdown")
        elif data == "mode_project":
            context.user_data["mode"] = "project"
            await query.edit_message_text("✅ Switched to *Project Mode*.", parse_mode="Markdown")
        elif data == "help":
            await help_command(update, context)
        elif data == "settings":
            await settings_command(update, context)
        elif data == "back_main":
            await query.edit_message_text(
                "Main menu:",
                reply_markup=main_menu_keyboard(),
            )
        elif data.startswith("project_"):
            await handle_project_callback(update, context, data)
        elif data.startswith("settings_"):
            await handle_settings_callback(update, context, data)
        else:
            await query.edit_message_text("Unknown action.")
    except Exception as e:
        logger.error(f"Error in callback handler: {e}", exc_info=True)
        await query.edit_message_text("An error occurred.")


async def handle_project_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    """Handle project management callbacks."""
    query = update.callback_query
    action = data.replace("project_", "")
    config, db, _, gm = initialize_services()
    user_id = update.effective_user.id
    if action == "create":
        await query.edit_message_text(
            "Enter repository name (or /cancel):",
        )
        context.user_data["awaiting_input"] = "project_repo_name"
    elif action == "push":
        await query.edit_message_text(
            "Enter repository name and file path (e.g., repo-name ./file.py):",
        )
        context.user_data["awaiting_input"] = "project_push"
    elif action == "issues":
        try:
            issues = gm.list_issues()
            if not issues:
                await query.edit_message_text("No open issues.")
            else:
                issue_list = "\n".join([f"#{i.number} {i.title}" for i in issues])
                await query.edit_message_text(f"Open issues:\n{issue_list}")
        except Exception as e:
            await query.edit_message_text(f"Error fetching issues: {e}")
    elif action == "issue_create":
        await query.edit_message_text(
            "Enter issue title (or /cancel):",
        )
        context.user_data["awaiting_input"] = "project_issue_title"
    else:
        await query.edit_message_text("Unknown project action.")


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    """Handle settings callbacks."""
    query = update.callback_query
    setting = data.replace("settings_", "")
    if setting == "language":
        keyboard = [
            [InlineKeyboardButton("English", callback_data="lang_en")],
            [InlineKeyboardButton("Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
        ]
        await query.edit_message_text("Choose language:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif setting == "tts":
        # Toggle TTS on/off
        current = context.user_data.get("tts