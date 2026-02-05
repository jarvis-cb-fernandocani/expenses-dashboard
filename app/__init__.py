"""
Flask application factory for the expenses dashboard.
"""

import os
from flask import Flask
from dotenv import load_dotenv


def create_app(test_config: dict = None) -> Flask:
    """Create and configure the Flask application."""
    load_dotenv()
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', os.path.join(base_dir, 'expenses.db'))
    
    # Override with test config if provided
    if test_config:
        app.config.update(test_config)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints/routes
    from app.routes import bp
    app.register_blueprint(bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_error_handlers(app: Flask) -> None:
    """Register custom error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request', 'message': str(error)}, 400
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
