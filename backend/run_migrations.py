#!/usr/bin/env python3
"""
Run database migrations to create missing tables
"""

from app.database.migrations import run_migrations, get_database_info
from app import create_app
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main migration function"""
    print("=" * 60)
    print("Database Migration Script")
    print("=" * 60)

    # Create Flask app context
    app = create_app('development')

    with app.app_context():
        # Show current database state
        print("\nCurrent database state:")
        info = get_database_info()
        print(f"Migration version: {info['migration_version']}")
        print(f"Total records: {info['total_records']}")
        print(f"\nExisting tables:")
        for table_name, table_info in info['tables'].items():
            print(f"  - {table_name}: {table_info['record_count']} records")

        # Run migrations
        print("\n" + "=" * 60)
        run_migrations()
        print("=" * 60)

        # Show updated database state
        print("\nUpdated database state:")
        info = get_database_info()
        print(f"Migration version: {info['migration_version']}")
        print(f"Total records: {info['total_records']}")
        print(f"\nAll tables:")
        for table_name, table_info in info['tables'].items():
            print(f"  - {table_name}: {table_info['record_count']} records")

        print("\n✅ Migrations completed successfully!")


if __name__ == "__main__":
    main()
