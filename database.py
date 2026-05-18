import sqlite3
import threading
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH

_lock = threading.Lock()

def _get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")  # Enable foreign key enforcement
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
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
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to initialize database: {e}") from e
    finally:
        conn.close()

def save_user(user_id: int, username: Optional[str], first_name: Optional[str],
              last_name: Optional[str], language_code: Optional[str]) -> None:
    """Insert or update a user record."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, language_code, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    language_code=excluded.language_code,
                    updated_at=CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name, language_code))
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to save user: {e}") from e
    finally:
        conn.close()

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a user by ID. Returns None if not found."""
    try:
        conn = _get_connection()
        with _lock:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get user: {e}") from e
    finally:
        conn.close()

def save_message(user_id: int, role: str, content: str) -> None:
    """Save a chat message to the conversation history."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute("INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                        (user_id, role, content))
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to save message: {e}") from e
    finally:
        conn.close()

def get_conversation_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent conversation messages for a user."""
    try:
        conn = _get_connection()
        with _lock:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get conversation history: {e}") from e
    finally:
        conn.close()

def save_memory(user_id: int, memory_type: str, content: str, embedding: Optional[bytes] = None) -> None:
    """Store a memory entry for a user."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute(
                "INSERT INTO memories (user_id, memory_type, content, embedding) VALUES (?, ?, ?, ?)",
                (user_id, memory_type, content, embedding)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to save memory: {e}") from e
    finally:
        conn.close()

def get_memories(user_id: int, memory_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve memories for a user, optionally filtered by type."""
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
        raise RuntimeError(f"Failed to get memories: {e}") from e
    finally:
        conn.close()

def create_project(user_id: int, name: str, description: Optional[str] = None) -> None:
    """Create a new project for a user."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute(
                "INSERT INTO projects (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, name, description)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to create project: {e}") from e
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
        raise RuntimeError(f"Failed to get projects: {e}") from e
    finally:
        conn.close()

def update_project_status(project_id: int, status: str) -> None:
    """Update the status of a project (e.g., 'completed', 'archived')."""
    try:
        conn = _get_connection()
        with _lock:
            conn.execute(
                "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, project_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to update project status: {e}") from e
    finally:
        conn.close()