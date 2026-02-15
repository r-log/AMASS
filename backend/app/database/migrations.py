"""
Database migrations and initialization for the Electrician Log MVP.
Handles table creation and data seeding.
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import current_app

from app.database.connection import get_db, table_exists
from app.models import (
    User, Floor, WorkLog, CriticalSector, Assignment,
    Notification, CableRoute, WorkTemplate
)


def get_migration_version() -> int:
    """Get the current migration version from the database."""
    try:
        db = get_db()
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        if cursor.fetchone() is None:
            # Migrations table doesn't exist, create it
            db.execute("""
                CREATE TABLE migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
            return 0

        # Get the latest migration version
        cursor = db.execute("SELECT MAX(version) as version FROM migrations")
        result = cursor.fetchone()
        return result['version'] if result and result['version'] else 0

    except Exception as e:
        print(f"Error getting migration version: {e}")
        return 0


def record_migration(version: int, name: str) -> None:
    """Record that a migration has been applied."""
    db = get_db()
    db.execute(
        "INSERT INTO migrations (version, name) VALUES (?, ?)",
        (version, name)
    )
    db.commit()


def backup_database() -> str:
    """Create a backup of the database before migrations."""
    try:
        database_path = current_app.config.get('DATABASE_PATH')
        if not database_path or not os.path.exists(database_path):
            return ""

        backup_path = f"{database_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(database_path, backup_path)
        print(f"Database backup created: {backup_path}")
        return backup_path

    except Exception as e:
        print(f"Error creating database backup: {e}")
        return ""


def initialize_database() -> None:
    """Initialize the database with all tables and default data."""
    print("Initializing database...")

    # Create tables in dependency order
    tables_to_create = [
        ('users', User),
        ('floors', Floor),
        ('work_logs', WorkLog),
        ('critical_sectors', CriticalSector),
        ('work_assignments', Assignment),
        ('notifications', Notification),
        ('cable_routes', CableRoute),
        ('work_templates', WorkTemplate)
    ]

    db = get_db()

    for table_name, model_class in tables_to_create:
        if not table_exists(table_name):
            print(f"Creating table: {table_name}")
            db.execute(model_class.create_table())
            db.commit()
        else:
            print(f"Table {table_name} already exists")

    # Seed default data
    seed_default_data()

    # Record initialization as migration version 1
    current_version = get_migration_version()
    if current_version == 0:
        record_migration(1, "Initial database setup")

    print("Database initialization completed!")


def seed_default_data() -> None:
    """Seed the database with default data."""
    print("Seeding default data...")

    try:
        # Add default floors if none exist
        floors = Floor.find_all()
        if not floors:
            print("Adding default floors...")
            default_floors = [
                Floor(name='Ground Floor', image_path='floor-1.pdf',
                      width=1920, height=1080),
                Floor(name='1st Floor', image_path='floor-2.pdf',
                      width=1920, height=1080),
                Floor(name='2nd Floor', image_path='floor-3.pdf',
                      width=1920, height=1080),
                Floor(name='3rd Floor', image_path='floor-4.pdf',
                      width=1920, height=1080),
                Floor(name='4th Floor', image_path='floor-5.pdf',
                      width=1920, height=1080),
                Floor(name='5th Floor', image_path='floor-6.pdf',
                      width=1920, height=1080),
                Floor(name='6th Floor', image_path='ZK-450.01-GR-E1X-Mp07-SW.pdf',
                      width=1920, height=1080),
            ]

            for floor in default_floors:
                floor.save()

            print(f"Added {len(default_floors)} default floors")

        # Add default work templates if none exist
        templates = WorkTemplate.find_all_active()
        if not templates:
            print("Creating default work templates...")
            WorkTemplate.create_default_templates()
            print("Added default work templates")

        # Create default admin user if no users exist
        users = User.find_all_active()
        if not users:
            print("Creating default admin user...")
            from werkzeug.security import generate_password_hash

            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                is_active=True
            )
            admin_user.save()
            print("Default admin user created (username: admin, password: admin123)")
            print("⚠️  Please change the default password after first login!")

    except Exception as e:
        print(f"Error seeding default data: {e}")


def migrate_add_missing_columns() -> None:
    """Migration to add missing columns to existing tables."""
    print("Running migration: Add missing columns...")

    db = get_db()

    # Add columns that might be missing from older versions
    missing_columns = [
        # work_logs table additions
        ('work_logs', 'worker_id', 'INTEGER'),
        ('work_logs', 'job_type', 'TEXT'),
        ('work_logs', 'cable_type', 'TEXT'),
        ('work_logs', 'cable_meters', 'REAL'),
        ('work_logs', 'start_x', 'REAL'),
        ('work_logs', 'start_y', 'REAL'),
        ('work_logs', 'end_x', 'REAL'),
        ('work_logs', 'end_y', 'REAL'),
        ('work_logs', 'hours_worked', 'REAL'),
        ('work_logs', 'status', 'TEXT DEFAULT "completed"'),
        ('work_logs', 'priority', 'TEXT DEFAULT "medium"'),
        ('work_logs', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),

        # critical_sectors table additions
        ('critical_sectors', 'width', 'REAL DEFAULT 0.1'),
        ('critical_sectors', 'height', 'REAL DEFAULT 0.1'),
        ('critical_sectors', 'type', 'TEXT DEFAULT "rectangle"'),
        ('critical_sectors', 'priority', 'TEXT DEFAULT "standard"'),
        ('critical_sectors', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),

        # floors table additions
        ('floors', 'is_active', 'BOOLEAN DEFAULT 1'),

        # users table additions (if any were missing)
        ('users', 'is_active', 'BOOLEAN DEFAULT 1'),
    ]

    for table_name, column_name, column_definition in missing_columns:
        try:
            if table_exists(table_name):
                # Check if column exists
                cursor = db.execute(f"PRAGMA table_info({table_name})")
                existing_columns = [col[1] for col in cursor.fetchall()]

                if column_name not in existing_columns:
                    print(f"Adding column {column_name} to {table_name}")
                    db.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
                    db.commit()

        except Exception as e:
            print(f"Error adding column {column_name} to {table_name}: {e}")

    print("Migration completed: Add missing columns")


def migrate_update_foreign_keys() -> None:
    """Migration to ensure foreign key constraints are properly set up."""
    print("Running migration: Update foreign keys...")

    db = get_db()

    # Enable foreign key constraints
    db.execute("PRAGMA foreign_keys = ON")
    db.commit()

    # Add foreign key constraints by recreating tables if needed
    # This is a complex operation in SQLite, so we'll just ensure they're enabled
    print("Foreign key constraints enabled")

    print("Migration completed: Update foreign keys")


def migrate_add_indexes() -> None:
    """Migration to add database indexes for better performance."""
    print("Running migration: Add database indexes...")

    db = get_db()

    indexes_to_create = [
        # work_logs indexes
        ("idx_work_logs_floor_id", "work_logs", "floor_id"),
        ("idx_work_logs_worker_id", "work_logs", "worker_id"),
        ("idx_work_logs_work_date", "work_logs", "work_date"),
        ("idx_work_logs_created_at", "work_logs", "created_at"),

        # critical_sectors indexes
        ("idx_critical_sectors_floor_id", "critical_sectors", "floor_id"),
        ("idx_critical_sectors_active", "critical_sectors", "is_active"),

        # notifications indexes
        ("idx_notifications_user_id", "notifications", "user_id"),
        ("idx_notifications_is_read", "notifications", "is_read"),
        ("idx_notifications_created_at", "notifications", "created_at"),

        # assignments indexes
        ("idx_assignments_assigned_to", "work_assignments", "assigned_to"),
        ("idx_assignments_status", "work_assignments", "status"),
        ("idx_assignments_due_date", "work_assignments", "due_date"),

        # cable_routes indexes
        ("idx_cable_routes_work_log_id", "cable_routes", "work_log_id"),

        # work_templates indexes
        ("idx_work_templates_work_type", "work_templates", "work_type"),
        ("idx_work_templates_active", "work_templates", "is_active"),

        # users indexes
        ("idx_users_username", "users", "username"),
        ("idx_users_role", "users", "role"),
        ("idx_users_active", "users", "is_active"),
    ]

    for index_name, table_name, column_name in indexes_to_create:
        try:
            if table_exists(table_name):
                db.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                db.commit()
                print(f"Created index: {index_name}")

        except Exception as e:
            print(f"Error creating index {index_name}: {e}")

    print("Migration completed: Add database indexes")


def run_migrations() -> None:
    """Run all necessary database migrations."""
    print("Starting database migrations...")

    # Create backup
    backup_path = backup_database()
    if backup_path:
        print(f"Database backed up to: {backup_path}")

    current_version = get_migration_version()
    print(f"Current migration version: {current_version}")

    # Run migrations based on version
    migrations = [
        (1, "Initial database setup", initialize_database),
        (2, "Add missing columns", migrate_add_missing_columns),
        (3, "Update foreign keys", migrate_update_foreign_keys),
        (4, "Add database indexes", migrate_add_indexes),
    ]

    for version, name, migration_func in migrations:
        if current_version < version:
            print(f"Running migration {version}: {name}")
            try:
                migration_func()
                record_migration(version, name)
                print(f"Migration {version} completed successfully")
            except Exception as e:
                print(f"Migration {version} failed: {e}")
                if backup_path:
                    print(f"Consider restoring from backup: {backup_path}")
                raise

    if current_version >= len(migrations):
        print("All migrations are up to date")

    print("Database migrations completed!")


def reset_database() -> None:
    """Reset the database by dropping all tables and recreating them."""
    print("⚠️  WARNING: This will delete all data!")

    # Create backup first
    backup_path = backup_database()
    if backup_path:
        print(f"Backup created: {backup_path}")

    db = get_db()

    # Get all tables
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row['name'] for row in cursor.fetchall()]

    # Drop all tables
    for table in tables:
        print(f"Dropping table: {table}")
        db.execute(f"DROP TABLE IF EXISTS {table}")

    db.commit()

    # Reinitialize database
    initialize_database()

    print("Database reset completed!")


def export_database_schema() -> str:
    """Export the current database schema to SQL."""
    db = get_db()

    schema_sql = []

    # Get all table creation statements
    cursor = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )

    for row in cursor.fetchall():
        if row['sql']:
            schema_sql.append(row['sql'] + ';')

    # Get all index creation statements
    cursor = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )

    for row in cursor.fetchall():
        if row['sql']:
            schema_sql.append(row['sql'] + ';')

    schema = '\n\n'.join(schema_sql)

    # Save to file
    schema_file = Path(current_app.config.get(
        'DATABASE_PATH', 'database.db')).parent / 'schema.sql'
    with open(schema_file, 'w') as f:
        f.write(
            f"-- Database Schema Export\n-- Generated: {datetime.now().isoformat()}\n\n")
        f.write(schema)

    print(f"Database schema exported to: {schema_file}")
    return str(schema_file)


def get_database_info() -> dict:
    """Get information about the current database state."""
    db = get_db()

    info = {
        'migration_version': get_migration_version(),
        'tables': {},
        'total_records': 0
    }

    # Get table information
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )

    for row in cursor.fetchall():
        table_name = row['name']

        # Get record count
        count_cursor = db.execute(
            f"SELECT COUNT(*) as count FROM {table_name}")
        count = count_cursor.fetchone()['count']

        info['tables'][table_name] = {
            'record_count': count
        }
        info['total_records'] += count

    return info
