"""
Configuration management for the Electrician Log MVP application.
Handles different environment configurations (development, production, testing).
"""

import os
import secrets
from pathlib import Path


class Config:
    """Base configuration class with common settings."""

    # Application settings
    # In dev, use a stable key so tokens survive server restarts.
    # In production, SECRET_KEY is enforced via get_config().
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-not-for-production-use'
    DEBUG = False
    TESTING = False

    # Database settings
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH') or str(BASE_DIR / 'database.db')

    # Tile generation settings
    TILES_DIR = os.environ.get('TILES_DIR') or 'tiles'
    TILES_DIRECTORY = os.environ.get('TILES_DIRECTORY') or str(BASE_DIR / 'tiles')
    TILE_SIZE = int(os.environ.get('TILE_SIZE', '512'))
    TILE_OVERLAP = int(os.environ.get('TILE_OVERLAP', '1'))
    TILE_DPI = int(os.environ.get('TILE_DPI', '300'))
    TILE_PNG_COMPRESS_LEVEL = int(os.environ.get('TILE_PNG_COMPRESS_LEVEL', '9'))
    TILE_MAX_LEVEL = int(os.environ.get('TILE_MAX_LEVEL', '0'))  # 0 = no cap (full resolution)
    TILE_FORMAT = os.environ.get('TILE_FORMAT', 'webp')  # 'webp', 'png', or 'jpeg'
    TILE_QUALITY = int(os.environ.get('TILE_QUALITY', '85'))  # Quality for WebP/JPEG (0-100)

    # Floor plans directory
    FLOOR_PLANS_DIR = os.environ.get('FLOOR_PLANS_DIR') or str(
        BASE_DIR.parent / 'floor-plans')

    # Project backup directory (compressed backups before delete)
    PROJECT_BACKUPS_DIR = os.environ.get('PROJECT_BACKUPS_DIR') or str(
        BASE_DIR.parent / 'project-backups')

    # JWT settings
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

    # Pagination settings
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', '50'))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', '200'))


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    DATABASE_PATH = os.environ.get('DEV_DATABASE_PATH') or str(
        Config.BASE_DIR / 'database.db')


class ProductionConfig(Config):
    """Production environment configuration."""

    # Set at class definition; validated in get_config() when production is active
    # (Do not raise in the class body — that runs on every import of this module.)
    SECRET_KEY = os.environ.get('SECRET_KEY')

    DATABASE_PATH = os.environ.get('DATABASE_PATH') or '/app/data/database.db'

    # More secure settings for production
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '8'))
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:3000').split(',')

    # Enforce request size limit
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DATABASE_PATH = ':memory:'  # In-memory database for tests

    # Faster settings for tests
    TILE_SIZE = 256
    TILE_DPI = 150


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(environment=None):
    """Get configuration class for the specified environment."""
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')

    config_class = config.get(environment, config['default'])

    if config_class is ProductionConfig:
        if not os.environ.get('SECRET_KEY'):
            raise ValueError(
                "SECRET_KEY environment variable must be set when FLASK_ENV=production. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

    return config_class
