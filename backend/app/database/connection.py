"""
Database connection utilities and management.
Provides centralized database connection handling for the application.
"""

import sqlite3
import threading
from contextlib import contextmanager
from flask import current_app, g
from typing import Optional


class DatabaseManager:
    """Manages database connections and provides utility methods."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self._local = threading.local()

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory enabled."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.database_path)
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self._local.connection.execute('PRAGMA foreign_keys = ON')

        return self._local.connection

    def close_connection(self):
        """Close the current thread's database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @contextmanager
    def get_db_context(self):
        """Context manager for database operations with automatic cleanup."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            # Don't close here as we want to reuse connections
            pass


# Flask integration functions
def dict_factory(cursor, row):
    """Convert sqlite3.Row to a dict with .get() method support."""
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


def get_db() -> sqlite3.Connection:
    """Get database connection for Flask request context."""
    if 'db' not in g:
        database_path = current_app.config.get('DATABASE_PATH')
        if not database_path:
            raise ValueError("DATABASE_PATH not configured")

        g.db = sqlite3.connect(database_path)
        g.db.row_factory = dict_factory  # Use dict instead of sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')

    return g.db


def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db_commands(app):
    """Initialize database-related CLI commands."""

    @app.cli.command()
    def init_db():
        """Initialize the database with tables."""
        from app.database.migrations import initialize_database
        initialize_database()
        print("Database initialized successfully!")

    @app.cli.command()
    def migrate_db():
        """Run database migrations."""
        from app.database.migrations import run_migrations
        run_migrations()
        print("Database migrations completed!")

    # Register teardown handler
    app.teardown_appcontext(close_db)


# Utility functions for common database operations
def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True):
    """Execute a query and return results."""
    db = get_db()
    cursor = db.execute(query, params)

    if fetch_one:
        return cursor.fetchone()
    elif fetch_all:
        return cursor.fetchall()
    else:
        return cursor


def insert_and_get_id(query: str, params: tuple = ()) -> int:
    """Insert a record and return the last insert ID."""
    db = get_db()
    cursor = db.execute(query, params)
    db.commit()
    return cursor.lastrowid


def update_record(query: str, params: tuple = ()) -> int:
    """Update record(s) and return the number of affected rows."""
    db = get_db()
    cursor = db.execute(query, params)
    db.commit()
    return cursor.rowcount


def delete_record(query: str, params: tuple = ()) -> int:
    """Delete record(s) and return the number of affected rows."""
    db = get_db()
    cursor = db.execute(query, params)
    db.commit()
    return cursor.rowcount


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    db = get_db()
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def get_table_columns(table_name: str) -> list:
    """Get column information for a table."""
    db = get_db()
    cursor = db.execute(f"PRAGMA table_info({table_name})")
    return [column[1] for column in cursor.fetchall()]


def add_column_if_not_exists(table_name: str, column_definition: str):
    """Add a column to a table if it doesn't already exist."""
    column_name = column_definition.split()[0]
    existing_columns = get_table_columns(table_name)

    if column_name not in existing_columns:
        db = get_db()
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
        db.commit()
        return True
    return False


@contextmanager
def database_transaction():
    """Context manager for database transactions."""
    db = get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
