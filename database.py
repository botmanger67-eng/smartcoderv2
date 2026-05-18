"""
Database module for SmartBot - AI Companion.
Handles users, conversations, memories, and projects.
Fixed: All function names match, added aliases, better error handling.
"""

import sqlite3
import threading
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot_sessions.db")

_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    mode TEXT DEFAULT 'chat',
                    tts_enabled INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_user_id 
                ON conversations(user_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'general',
                    content TEXT NOT NULL,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    repo_url TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER UNIQUE,
                    name TEXT NOT NULL,
                    full_name TEXT,
                    html_url TEXT,
                    clone_url TEXT,
                    private INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise RuntimeError(f"Failed to initialize database: {e}") from e
    finally:
        conn.close()


# ============================================
# USER FUNCTIONS
# ============================================

def save_user(user_id: int, username: Optional[str] = None, 
              first_name: Optional[str] = None,
              last_name: Optional[str] = None, 
              language_code: Optional[str] = None) -> None:
    """Insert or update a user record."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, language_code, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=COALESCE(excluded.username, users.username),
                    first_name=COALESCE(excluded.first_name, users.first_name),
                    last_name=COALESCE(excluded.last_name, users.last_name),
                    language_code=COALESCE(excluded.language_code, users.language_code),
                    updated_at=CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name, language_code))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save user {user_id}: {e}")
        raise
    finally:
        conn.close()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a user by ID."""
    try:
        conn = _get_connection()
        with _lock:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None
    finally:
        conn.close()


def get_user_mode(user_id: int) -> str:
    """Get user's current mode."""
    user = get_user(user_id)
    return user.get("mode", "chat") if user else "chat"


def set_user_mode(user_id: int, mode: str) -> None:
    """Set user's mode."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("UPDATE users SET mode = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (mode, user_id))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to set mode for user {user_id}: {e}")
    finally:
        conn.close()


# ============================================
# CONVERSATION FUNCTIONS
# ============================================

def save_message(user_id: int, role: str, content: str) -> None:
    """Save a chat message to conversation history."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                        (user_id, role, content))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save message: {e}")
        raise
    finally:
        conn.close()


def get_conversation_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent conversation messages for a user."""
    try:
        conn = _get_connection()
        with _lock:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]
    except sqlite3.Error as e:
        logger.error(f"Failed to get history: {e}")
        return []
    finally:
        conn.close()


def clear_user_history(user_id: int) -> None:
    """Clear all conversation history for a user."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to clear history: {e}")
    finally:
        conn.close()


# ============================================
# MEMORY FUNCTIONS
# ============================================

def save_memory(user_id: int, memory_type: str, content: str, 
                embedding: Optional[bytes] = None) -> None:
    """Store a memory entry."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute(
                "INSERT INTO memories (user_id, memory_type, content, embedding) VALUES (?, ?, ?, ?)",
                (user_id, memory_type, content, embedding)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save memory: {e}")
    finally:
        conn.close()


def get_memories(user_id: int, memory_type: Optional[str] = None, 
                 limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve memories for a user."""
    try:
        conn = _get_connection()
        with _lock:
            if memory_type:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id = ? AND memory_type = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, memory_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit)
                ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Failed to get memories: {e}")
        return []
    finally:
        conn.close()


# ============================================
# PROJECT FUNCTIONS
# ============================================

def create_project(user_id: int, name: str, description: Optional[str] = None) -> int:
    """Create a new project. Returns project ID."""
    try:
        conn = _get_connection()
        with _lock:
            cursor = conn.execute(
                "INSERT INTO projects (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, name, description)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Failed to create project: {e}")
        return -1
    finally:
        conn.close()


def get_projects(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active projects for a user."""
    try:
        conn = _get_connection()
        with _lock:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_id = ? AND status = 'active' ORDER BY updated_at DESC",
                (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Failed to get projects: {e}")
        return []
    finally:
        conn.close()


def update_project_status(project_id: int, status: str) -> None:
    """Update project status."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute(
                "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, project_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update project: {e}")
    finally:
        conn.close()


# ============================================
# REPO FUNCTIONS
# ============================================

def save_repo(repo_id: int, name: str, full_name: str, html_url: str, 
              clone_url: str, private: bool = False) -> None:
    """Save a GitHub repo record."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("""
                INSERT OR REPLACE INTO repos (repo_id, name, full_name, html_url, clone_url, private)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (repo_id, name, full_name, html_url, clone_url, int(private)))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save repo: {e}")
    finally:
        conn.close()


def get_repo_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a repo by name."""
    try:
        conn = _get_connection()
        with _lock:
            row = conn.execute("SELECT * FROM repos WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Failed to get repo: {e}")
        return None
    finally:
        conn.close()


def delete_repo_by_name(name: str) -> None:
    """Delete a repo record."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("DELETE FROM repos WHERE name = ?", (name,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to delete repo: {e}")
    finally:
        conn.close()


# ============================================
# ALIASES - For backward compatibility
# ============================================

# These match the function names used in ai_handler.py and bot.py
get_history = get_conversation_history
add_message = save_message
clear_history = clear_user_history
get_or_create_user = save_user  # Auto-creates if not exists
get_user_mode_from_db = get_user_mode
save_project = create_project

# Database class wrapper for bot.py compatibility
class Database:
    """Database class wrapper for easy import."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        init_db()
    
    def init_db(self):
        init_db()
    
    def save_user(self, *args, **kwargs):
        return save_user(*args, **kwargs)
    
    def get_user(self, *args, **kwargs):
        return get_user(*args, **kwargs)
    
    def save_message(self, *args, **kwargs):
        return save_message(*args, **kwargs)
    
    def get_history(self, *args, **kwargs):
        return get_conversation_history(*args, **kwargs)
    
    def clear_history(self, *args, **kwargs):
        return clear_user_history(*args, **kwargs)
    
    def get_user_mode(self, *args, **kwargs):
        return get_user_mode(*args, **kwargs)
    
    def set_user_mode(self, *args, **kwargs):
        return set_user_mode(*args, **kwargs)


# Initialize on import
import os
init_db()
