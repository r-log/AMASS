"""
Database migrations and initialization for the Electrician Log MVP.
Handles table creation and data seeding.
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import current_app

from app.database.connection import get_db, table_exists, add_column_if_not_exists, _ALLOWED_TABLE_NAMES
from app.models import (
    User, Floor, Project, ProjectUserAssignment, WorkLog, CriticalSector,
    Assignment, Notification, CableRoute, WorkTemplate
)

logger = logging.getLogger(__name__)


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
        logger.error("Error getting migration version: %s", e)
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
        logger.info("Database backup created: %s", backup_path)
        return backup_path

    except Exception as e:
        logger.error("Error creating database backup: %s", e)
        return ""


def initialize_database() -> None:
    """Initialize the database with all tables and default data."""
    logger.info("Initializing database...")

    # Create tables in dependency order (projects before floors)
    tables_to_create = [
        ('users', User),
        ('projects', Project),
        ('project_user_assignments', ProjectUserAssignment),
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
            logger.info("Creating table: %s", table_name)
            db.execute(model_class.create_table())
            db.commit()
        else:
            logger.debug("Table %s already exists", table_name)

    # Seed default data
    seed_default_data()

    # Note: migration version is recorded by run_migrations(), not here.
    # This function can also be called from reset_database() where the
    # caller handles versioning separately.

    logger.info("Database initialization completed")


def seed_default_data() -> None:
    """Seed the database with default data."""
    logger.info("Seeding default data...")

    try:
        # Add default project if none exist
        projects = Project.find_all()
        default_project_id = None
        if not projects:
            logger.info("Adding default project...")
            default_project = Project(
                name='Default Project',
                description='Default project for initial setup',
                is_active=True
            )
            default_project.save()
            default_project_id = default_project.id
            logger.info("Added default project (id=%d)", default_project_id)
        else:
            default_project_id = projects[0].id

        # Add default floors if none exist
        floors = Floor.find_all()
        if not floors and default_project_id:
            logger.info("Adding default floors...")
            default_floors = [
                Floor(project_id=default_project_id, name='Ground Floor', image_path='floor-1.pdf',
                      width=1920, height=1080, sort_order=0),
                Floor(project_id=default_project_id, name='1st Floor', image_path='floor-2.pdf',
                      width=1920, height=1080, sort_order=1),
                Floor(project_id=default_project_id, name='2nd Floor', image_path='floor-3.pdf',
                      width=1920, height=1080, sort_order=2),
                Floor(project_id=default_project_id, name='3rd Floor', image_path='floor-4.pdf',
                      width=1920, height=1080, sort_order=3),
                Floor(project_id=default_project_id, name='4th Floor', image_path='floor-5.pdf',
                      width=1920, height=1080, sort_order=4),
                Floor(project_id=default_project_id, name='5th Floor', image_path='floor-6.pdf',
                      width=1920, height=1080, sort_order=5),
                Floor(project_id=default_project_id, name='6th Floor', image_path='ZK-450.01-GR-E1X-Mp07-SW.pdf',
                      width=1920, height=1080, sort_order=6),
            ]

            for floor in default_floors:
                floor.save()

            logger.info("Added %d default floors", len(default_floors))

            # Assign all workers to default project
            workers = User.find_by_role('worker')
            for worker in workers:
                ProjectUserAssignment.assign(default_project_id, worker.id)
            if workers:
                logger.info("Assigned %d workers to default project", len(workers))

        # Add default work templates if none exist
        templates = WorkTemplate.find_all_active()
        if not templates:
            logger.info("Creating default work templates...")
            WorkTemplate.create_default_templates()
            logger.info("Added default work templates")

        # Create default admin user if no users exist
        users = User.find_all_active()
        if not users:
            logger.info("Creating default admin user...")
            from werkzeug.security import generate_password_hash
            import secrets as _secrets

            # Generate a secure random password instead of using a hardcoded one
            generated_password = _secrets.token_urlsafe(12)

            admin_user = User(
                username='admin',
                password_hash=generate_password_hash(generated_password),
                full_name='System Administrator',
                role='admin',
                is_active=True
            )
            admin_user.save()
            # Write password to a file instead of logging to stdout
            from pathlib import Path
            pw_file = Path(__file__).resolve().parent.parent / 'admin_password.txt'
            pw_file.write_text(f"admin:{generated_password}\n")
            pw_file.chmod(0o600)
            logger.warning(
                "Default admin user created (username: admin). "
                "Generated password written to %s — read, delete, then change it on first login.",
                pw_file,
            )

    except Exception as e:
        logger.error("Error seeding default data: %s", e)


def migrate_add_missing_columns() -> None:
    """Migration to add missing columns to existing tables."""
    logger.info("Running migration: Add missing columns...")

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
                full_col_def = f"{column_name} {column_definition}"
                if add_column_if_not_exists(table_name, full_col_def):
                    logger.info("Adding column %s to %s", column_name, table_name)

        except Exception as e:
            logger.error("Error adding column %s to %s: %s", column_name, table_name, e)

    logger.info("Migration completed: Add missing columns")


def migrate_update_foreign_keys() -> None:
    """Migration to ensure foreign key constraints are properly set up."""
    logger.info("Running migration: Update foreign keys...")

    db = get_db()

    # Enable foreign key constraints
    db.execute("PRAGMA foreign_keys = ON")
    db.commit()

    # Add foreign key constraints by recreating tables if needed
    # This is a complex operation in SQLite, so we'll just ensure they're enabled
    logger.info("Migration completed: Update foreign keys")


def migrate_add_indexes() -> None:
    """Migration to add database indexes for better performance."""
    logger.info("Running migration: Add database indexes...")

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

    import re
    _ident_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    for index_name, table_name, column_name in indexes_to_create:
        try:
            if table_name not in _ALLOWED_TABLE_NAMES:
                logger.warning("Skipping index for unknown table: %s", table_name)
                continue
            if not _ident_re.match(index_name) or not _ident_re.match(column_name):
                logger.warning("Skipping index with invalid identifier: %s", index_name)
                continue
            if table_exists(table_name):
                db.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                db.commit()
                logger.debug("Created index: %s", index_name)

        except Exception as e:
            logger.error("Error creating index %s: %s", index_name, e)

    logger.info("Migration completed: Add database indexes")


def migrate_add_projects() -> None:
    """Migration to add projects, project_user_assignments, and project_id on floors."""
    logger.info("Running migration: Add projects and project assignments...")

    db = get_db()

    # 1. Create projects table
    if not table_exists('projects'):
        logger.info("Creating projects table")
        db.execute(Project.create_table())
        db.commit()

    # 2. Create project_user_assignments table
    if not table_exists('project_user_assignments'):
        logger.info("Creating project_user_assignments table")
        db.execute(ProjectUserAssignment.create_table())
        db.commit()

    # 3. Add project_id and sort_order to floors
    add_column_if_not_exists('floors', 'project_id INTEGER')
    add_column_if_not_exists('floors', 'sort_order INTEGER DEFAULT 0')

    # 4. Create default project if no projects exist
    cursor = db.execute("SELECT COUNT(*) as count FROM projects")
    count = cursor.fetchone()['count']
    if count == 0:
        logger.info("Creating default project")
        default_project = Project(
            name='Default Project',
            description='Migration default - all existing floors assigned here',
            is_active=True
        )
        default_project.save()
        default_project_id = default_project.id

        # 5. Assign all existing floors to default project
        db.execute("UPDATE floors SET project_id = ? WHERE project_id IS NULL", (default_project_id,))
        db.commit()
        logger.info("Assigned floors to default project (id=%d)", default_project_id)

        # 6. Assign all workers to default project
        workers = User.find_by_role('worker')
        for worker in workers:
            try:
                ProjectUserAssignment.assign(default_project_id, worker.id, assigned_by=None)
            except Exception as e:
                logger.warning("Could not assign worker %d to project: %s", worker.id, e)
        logger.info("Assigned %d workers to default project", len(workers))
    else:
        # Backfill floors that have no project_id
        cursor = db.execute("SELECT id FROM projects WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            default_project_id = row['id']
            db.execute("UPDATE floors SET project_id = ? WHERE project_id IS NULL", (default_project_id,))
            db.commit()

    logger.info("Migration completed: Add projects")


def _acquire_migration_lock():
    """
    Acquire an exclusive advisory lock on a file next to the database.

    Returns an open file handle whose lifetime holds the lock — the caller
    must keep it open until migrations finish. Uses fcntl on Unix (the
    production target); on other platforms (dev / Windows) the lock is a
    no-op and concurrent runs fall back to the in-DB version check.
    """
    database_path = current_app.config.get('DATABASE_PATH')
    if not database_path or database_path == ':memory:':
        return None

    lock_path = f"{database_path}.migration.lock"
    try:
        Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    try:
        import fcntl  # Unix only
    except ImportError:
        logger.debug("fcntl unavailable — skipping cross-process migration lock")
        return None

    lock_file = open(lock_path, 'w')
    logger.debug("Acquiring migration lock: %s", lock_path)
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # blocks until granted
    return lock_file


def _release_migration_lock(lock_file) -> None:
    """Release the advisory lock acquired by _acquire_migration_lock()."""
    if lock_file is None:
        return
    try:
        import fcntl
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        lock_file.close()
    except Exception:
        pass


def run_migrations() -> None:
    """
    Run all necessary database migrations.

    Safe to call on every container start:
      - Fast path: if the DB is already at the latest version, returns
        immediately without taking a backup or acquiring a lock.
      - Concurrency: holds an advisory file lock (fcntl.flock) for the full
        migration sequence so rolling deploys sharing the same volume can't
        race each other into duplicate version rows. A SQLite transaction
        wouldn't work here because initialize_database() and model.save()
        call db.commit() internally.
    """
    migrations = [
        (1, "Initial database setup", initialize_database),
        (2, "Add missing columns", migrate_add_missing_columns),
        (3, "Update foreign keys", migrate_update_foreign_keys),
        (4, "Add database indexes", migrate_add_indexes),
        (5, "Add projects and project assignments", migrate_add_projects),
    ]
    latest_version = max(v for v, _, _ in migrations)

    db = get_db()
    # Ensure the migrations table exists before reading version
    get_migration_version()
    # Let concurrent writers wait briefly rather than fail-fast on SQLITE_BUSY
    try:
        db.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass

    # Fast path — no lock, no backup, no work
    if get_migration_version() >= latest_version:
        logger.info(
            "Database already at latest version (%d) — no migrations to run",
            latest_version,
        )
        return

    logger.info("Starting database migrations...")
    lock = _acquire_migration_lock()
    try:
        # Re-check under the lock: another container may have just finished
        current_version = get_migration_version()
        if current_version >= latest_version:
            logger.info(
                "Another process already migrated to version %d — nothing to do",
                current_version,
            )
            return

        logger.info(
            "Current migration version: %d (target: %d)",
            current_version,
            latest_version,
        )

        # Backup only when we're actually going to run something
        backup_path = backup_database()

        for version, name, migration_func in migrations:
            if current_version < version:
                logger.info("Running migration %d: %s", version, name)
                try:
                    migration_func()
                    record_migration(version, name)
                    logger.info("Migration %d completed successfully", version)
                except Exception as e:
                    logger.error("Migration %d failed: %s", version, e)
                    if backup_path:
                        logger.error("Consider restoring from backup: %s", backup_path)
                    raise

        logger.info("Database migrations completed")
    finally:
        _release_migration_lock(lock)


def reset_database() -> None:
    """Reset the database by dropping all tables and recreating them."""
    logger.warning("Resetting database — all data will be deleted")

    # Create backup first
    backup_path = backup_database()
    if backup_path:
        logger.info("Backup created: %s", backup_path)

    db = get_db()

    # Get all tables
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row['name'] for row in cursor.fetchall()]

    # Drop all tables (only known tables to prevent injection)
    for table in tables:
        if table in _ALLOWED_TABLE_NAMES:
            logger.info("Dropping table: %s", table)
            db.execute(f"DROP TABLE IF EXISTS {table}")
        else:
            logger.warning("Skipping unknown table: %s", table)

    db.commit()

    # Reinitialize database
    initialize_database()

    logger.info("Database reset completed")


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

    logger.info("Database schema exported to: %s", schema_file)
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

        # Get record count (only for known tables)
        if table_name not in _ALLOWED_TABLE_NAMES:
            continue
        count_cursor = db.execute(
            f"SELECT COUNT(*) as count FROM {table_name}")
        count = count_cursor.fetchone()['count']

        info['tables'][table_name] = {
            'record_count': count
        }
        info['total_records'] += count

    return info
