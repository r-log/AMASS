"""
Flask application factory for the Electrician Log MVP.
"""

from flask import Flask
from flask_cors import CORS

from app.config import get_config
from app.database.connection import init_db_commands


def create_app(config_name: str = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_name: Configuration environment name ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Disable strict slashes to prevent redirect issues with CORS preflight
    app.url_map.strict_slashes = False

    # Initialize CORS with proper configuration
    CORS(app,
         origins=app.config.get('CORS_ORIGINS', ['*']),
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

    # Initialize database commands
    init_db_commands(app)

    # Register API blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    return app


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints with the Flask app."""

    # Import blueprints
    from app.api.auth import auth_bp
    from app.api.floors import floors_bp
    from app.api.work_logs import work_logs_bp
    from app.api.critical_sectors import critical_sectors_bp
    from app.api.assignments import assignments_bp
    from app.api.notifications import notifications_bp
    from app.api.tiles import tiles_bp

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(floors_bp, url_prefix='/api/floors')
    app.register_blueprint(work_logs_bp, url_prefix='/api/work-logs')
    app.register_blueprint(critical_sectors_bp,
                           url_prefix='/api/critical-sectors')
    app.register_blueprint(assignments_bp, url_prefix='/api/assignments')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(tiles_bp, url_prefix='/api/tiles')


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""

    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request', 'message': str(error)}, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Unauthorized', 'message': 'Authentication required'}, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Forbidden', 'message': 'Insufficient permissions'}, 403

    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found', 'message': 'Resource not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error', 'message': 'Something went wrong'}, 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f"Unhandled exception: {error}")
        return {'error': 'Internal server error', 'message': 'An unexpected error occurred'}, 500
