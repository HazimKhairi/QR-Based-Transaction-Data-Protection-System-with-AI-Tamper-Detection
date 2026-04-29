"""
QR-Based Transaction Data Protection System
Main application factory
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flasgger import Swagger

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
ma = Marshmallow()


def create_app(config_name=None):
    """Application factory pattern"""
    from config import config

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    ma.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # Swagger configuration for API documentation
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/"
    }

    swagger_template = {
        "info": {
            "title": "QR-Based Transaction Data Protection System API",
            "description": "API documentation for the QR Transaction Protection System. "
                           "This system provides secure QR code payment processing with AES-256 encryption, "
                           "AI-powered tamper detection, and two-factor authentication.",
            "version": "1.0.0",
            "contact": {
                "name": "API Support",
                "email": "support@qrtransaction.my"
            }
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using Bearer scheme. Example: 'Bearer {token}'"
            }
        },
        "security": [{"Bearer": []}]
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # Setup logging
    setup_logging(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.transactions import transactions_bp
    from app.routes.admin import admin_bp
    from app.routes.tamper_detection import tamper_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(tamper_bp, url_prefix='/api/tamper')

    # Register error handlers
    register_error_handlers(app)

    # JWT error handlers
    register_jwt_handlers(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def setup_logging(app):
    """Configure application logging for audit trails and bug tracking"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # File handler for audit logs
    file_handler = RotatingFileHandler(
        f'logs/{app.config.get("LOG_FILE", "app.log")}',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)

    # Security-specific log handler
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=10240000,
        backupCount=10
    )
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s SECURITY [%(name)s] - %(message)s'
    ))
    security_handler.setLevel(logging.WARNING)

    # Transaction log handler
    transaction_handler = RotatingFileHandler(
        'logs/transactions.log',
        maxBytes=10240000,
        backupCount=10
    )
    transaction_handler.setFormatter(logging.Formatter(
        '%(asctime)s TRANSACTION - %(message)s'
    ))
    transaction_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(security_handler)
    app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))

    # Create specialized loggers
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)

    transaction_logger = logging.getLogger('transactions')
    transaction_logger.addHandler(transaction_handler)
    transaction_logger.setLevel(logging.INFO)


def register_error_handlers(app):
    """Register custom error handlers"""
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'Bad request: {error}')
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f'Unauthorized access attempt: {error}')
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f'Forbidden access: {error}')
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'Resource not found'
        }), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        app.logger.warning(f'Rate limit exceeded: {error}')
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500


def register_jwt_handlers(app):
    """Register JWT error handlers"""
    from flask import jsonify

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'error': 'Token Expired',
            'message': 'The token has expired. Please log in again.'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Invalid Token',
            'message': 'Invalid token provided'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Authorization Required',
            'message': 'Request does not contain an access token'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'error': 'Token Revoked',
            'message': 'Token has been revoked'
        }), 401
