#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Connection Management
Provides unified database access interface
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional


# Database path (absolute, resolved from project root)
DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "subtitle_manager.db")

_local = threading.local()

class _CachedConnectionProxy:
    """A proxy wrapper that prevents the DAOs from actually closing the persistent thread-local connection."""
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        # Intercept the close() method and do nothing
        if name == 'close':
            return lambda: None
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def get_db_connection() -> sqlite3.Connection:
    """
    Get a persistent thread-local database connection safely wrapped in a proxy.
    This drastically reduces overhead from repeatedly connecting/closing in DAOs.
    """
    if not hasattr(_local, 'conn'):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        conn.execute('PRAGMA journal_mode=WAL')
        _local.conn = _CachedConnectionProxy(conn)
    return getattr(_local, 'conn')  # type: ignore


def init_database():
    """
    Initialize database table structure
    Create tables if they don't exist
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create media_files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                subtitles_json TEXT DEFAULT '[]',
                has_translated INTEGER DEFAULT 0,
                embedded_tracks_json TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add 'embedded_tracks_json' column to existing media_files table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE media_files ADD COLUMN embedded_tracks_json TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass # Column already exists
        
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                log TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add 'params' column to existing tasks table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN params TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
        
        # Add 'hidden' column — hidden tasks are kept for dedup but not shown in queue
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN hidden INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists
        
        # Create config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        print("[Database] Tables initialized successfully")
        
    except Exception as e:
        print(f"[Database] Initialization failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def check_database_health() -> bool:
    """
    Check database health status
    
    Returns:
        bool: Whether database is usable
    """
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1 FROM config LIMIT 1")
        conn.close()
        return True
    except Exception as e:
        print(f"[Database] Health check failed: {e}")
        return False


def wait_for_database(max_retries: int = 30, retry_interval: float = 1.0) -> bool:
    """
    Wait for database to be ready (used on container startup)
    
    Args:
        max_retries: Maximum number of retries
        retry_interval: Retry interval in seconds
    
    Returns:
        bool: Whether database is ready
    """
    import time
    
    for i in range(max_retries):
        if check_database_health():
            if i > 0:
                print(f"[Database] Ready after {i+1} attempts")
            return True
        
        if i == 0:
            print("[Database] Waiting for database to be ready...")
        
        time.sleep(retry_interval)
    
    print(f"[Database] Timeout after {max_retries} attempts")
    return False


class DatabaseConnection:
    """
    Database connection context manager
    Usage:
        with DatabaseConnection() as conn:
            cursor = conn.execute("SELECT * FROM tasks")
    """
    
    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None
    
    def __enter__(self) -> sqlite3.Connection:
        self.conn = get_db_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
        return False  # Do not suppress exception


# ============================================================================
# Database utility functions
# ============================================================================

def execute_query(query: str, params: tuple = ()) -> list:
    """
    Execute a query statement
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        raise e
    finally:
        conn.close()


def execute_update(query: str, params: tuple = ()) -> int:
    """
    Execute an update statement (INSERT/UPDATE/DELETE)
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def execute_many(query: str, params_list: list) -> int:
    """
    Batch execute statements
    """
    conn = get_db_connection()
    try:
        cursor = conn.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()