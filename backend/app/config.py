"""
Configuration management for the Electrician Log MVP application.
Handles different environment configurations (development, production, testing).
"""

import os
from pathlib import Path


class Config:
    """Base configuration class with common settings."""

    # Application settings
    SECRET_KEY = os.environ.get(
        'SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False

    # Database settings
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH') or str(BASE_DIR / 'database.db')

    # Tile generation settings
    TILES_DIR = os.environ.get('TILES_DIR') or 'tiles'
    TILE_SIZE = int(os.environ.get('TILE_SIZE', '512'))
    TILE_OVERLAP = int(os.environ.get('TILE_OVERLAP', '1'))
    TILE_DPI = int(os.environ.get('TILE_DPI', '300'))

    # Floor plans directory
    FLOOR_PLANS_DIR = os.environ.get('FLOOR_PLANS_DIR') or str(
        BASE_DIR.parent / 'floor-plans')

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

    DATABASE_PATH = os.environ.get('DATABASE_PATH') or '/app/data/database.db'

    # More secure settings for production
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '8'))
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:3000').split(',')


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

    return config.get(environment, config['default'])
