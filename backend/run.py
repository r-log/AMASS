"""
Main entry point for the refactored Electrician Log MVP application.
"""

import os
from app import create_app
from utils.tile_generator_safe import SafeTileGenerator


def main():
    """Main application entry point."""
    # Create Flask app with configuration
    config_env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_env)

    # Initialize tile generator (keeping compatibility with existing system)
    app.tile_generator = SafeTileGenerator(
        tiles_dir=app.config.get('TILES_DIR', 'tiles'),
        tile_size=app.config.get('TILE_SIZE', 512),
        overlap=app.config.get('TILE_OVERLAP', 1),
        dpi=app.config.get('TILE_DPI', 300)
    )

    print("=" * 60)
    print("🏗️  Electrician Log MVP - Refactored Architecture")
    print(f"Environment: {config_env}")
    print(f"Database: {app.config.get('DATABASE_PATH', 'database.db')}")
    print("=" * 60)
    print("Available API endpoints:")
    print("  Authentication:")
    print("    POST /api/auth/login - User login")
    print("    POST /api/auth/logout - User logout")
    print("    GET  /api/auth/verify - Verify token")
    print("    POST /api/auth/refresh - Refresh token")
    print("  Work Logs:")
    print("    GET  /api/work-logs - Get work logs")
    print("    POST /api/work-logs - Create work log")
    print("    PUT  /api/work-logs/<id> - Update work log")
    print("    DELETE /api/work-logs/<id> - Delete work log")
    print("  Critical Sectors:")
    print("    GET  /api/critical-sectors - Get critical sectors")
    print("    POST /api/critical-sectors - Create critical sector")
    print("  Tiles:")
    print("    POST /api/tiles/generate/<floor_id> - Generate tiles")
    print("    GET  /api/tiles/status/<floor_id> - Check tile status")
    print("=" * 60)
    print("🔐 Authentication enabled!")
    print("📊 Modular architecture active!")
    print("=" * 60)

    # Run the application
    app.run(
        debug=app.config.get('DEBUG', True),
        host='0.0.0.0',
        port=5000
    )


if __name__ == '__main__':
    main()
