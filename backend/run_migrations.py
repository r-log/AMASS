#!/usr/bin/env python3
"""
Run database migrations.

Designed to be safe for automated deployment:
  - Respects FLASK_ENV (defaults to production)
  - Uses the structured logger configured by create_app()
  - Exits 0 on success (including no-op), 1 on any failure
  - Safe to run on every container start (idempotent fast path)
"""

import os
import sys

# Ensure the backend directory is on sys.path so `app` imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.database.migrations import run_migrations, get_database_info


def main() -> int:
    """Run migrations under the configured Flask environment. Returns exit code."""
    config_env = os.environ.get('FLASK_ENV', 'production')
    app = create_app(config_env)
    logger = app.logger

    try:
        with app.app_context():
            info_before = get_database_info()
            version_before = info_before['migration_version']
            logger.info(
                "Migration check — env=%s, current version=%d, tables=%d, records=%d",
                config_env,
                version_before,
                len(info_before['tables']),
                info_before['total_records'],
            )

            run_migrations()

            info_after = get_database_info()
            version_after = info_after['migration_version']
            if version_after == version_before:
                logger.info("Migrations up to date at version %d — no changes", version_after)
            else:
                logger.info(
                    "Migrations complete — advanced from version %d to %d",
                    version_before,
                    version_after,
                )
        return 0
    except Exception:
        logger.exception("Migration failed — aborting startup")
        return 1


if __name__ == "__main__":
    sys.exit(main())
