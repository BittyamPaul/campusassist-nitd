"""
CampusAssist Database Connection Manager.
Handles SQLite connection lifecycle, schema initialization, and row factory setup.
"""

import sqlite3
import os
from pathlib import Path
from flask import g, current_app
from config import Config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _configure_sqlite_pragmas(conn, is_memory: bool = False):
    """Apply high-performance, robust SQLite pragmas."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    if not is_memory:
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        except Exception:
            pass
    try:
        conn.execute("PRAGMA cache_size = -2000;")  # 2MB cache
        conn.execute("PRAGMA temp_store = MEMORY;")
    except Exception:
        pass


def get_db(db_path=None):
    """
    Get a database connection.
    If within a Flask request context, reuse connection in `g`.
    Otherwise, open a direct standalone connection.
    """
    target_path = db_path
    if target_path is None:
        try:
            target_path = current_app.config.get("DB_PATH", Config.DB_PATH)
        except RuntimeError:
            target_path = Config.DB_PATH

    is_memory = target_path == ":memory:"

    # If within Flask context
    try:
        db_conn = getattr(g, "db", None)
        is_closed = False
        if db_conn is not None:
            try:
                # Simple check if connection is active
                db_conn.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                is_closed = True

        if db_conn is None or is_closed or getattr(g, "db_path", None) != target_path:
            # Ensure parent directory exists for file-based databases
            if not is_memory:
                os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

            conn = sqlite3.connect(target_path)
            conn.row_factory = sqlite3.Row
            _configure_sqlite_pragmas(conn, is_memory=is_memory)
            g.db = conn
            g.db_path = target_path
        return g.db
    except RuntimeError:
        # Outside Flask context
        if not is_memory:
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        _configure_sqlite_pragmas(conn, is_memory=is_memory)
        return conn


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = getattr(g, "db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
        g.pop("db", None)
        g.pop("db_path", None)


def _migrate_unresolved_queries(conn):
    """Ensure newly added columns exist in existing database instances."""
    try:
        cursor = conn.execute("PRAGMA table_info(unresolved_queries);")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        if not existing_cols:
            return

        migrations = [
            ("conversation_id", "TEXT"),
            ("classification_confidence", "REAL DEFAULT 0.0"),
            ("retrieval_confidence", "REAL DEFAULT 0.0"),
            ("status", "TEXT NOT NULL DEFAULT 'unresolved'"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE unresolved_queries ADD COLUMN {col_name} {col_def};")
        conn.commit()
    except Exception:
        pass


def _ensure_performance_indexes(conn):
    """Ensure performance indexes exist on existing database instances."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_knowledge_updated ON knowledge_items(updated_at DESC, id DESC);",
        "CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC, id DESC);",
        "CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at DESC, id DESC);",
        "CREATE INDEX IF NOT EXISTS idx_messages_role_verified ON messages(role, is_verified);",
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);",
    ]
    for idx_sql in indexes:
        try:
            conn.execute(idx_sql)
        except Exception:
            pass
    try:
        conn.commit()
    except Exception:
        pass


def init_db(db_path=None):
    """Initialize database tables using schema.sql and apply migrations."""
    conn = get_db(db_path)
    _migrate_unresolved_queries(conn)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    _migrate_unresolved_queries(conn)
    _ensure_performance_indexes(conn)
    conn.commit()
    return conn

