"""
Main application entry point for QR-Based Transaction Data Protection System
Run with: python run.py
Or: flask run
"""
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.tamper_detection import get_tamper_detection_service


def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'models', 'instance']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def initialize_ai_model(app):
    """Initialize the AI tamper detection model"""
    with app.app_context():
        print("Initializing AI tamper detection model...")
        tamper_service = get_tamper_detection_service()

        # Load existing model or train new one
        if not tamper_service.load_model():
            print("No existing model found. Training new model...")
            tamper_service.train_model()
            print("AI model trained and saved.")
        else:
            print("AI model loaded successfully.")


def get_app():
    """Get or create the application instance"""
    global _app
    if '_app' not in globals() or _app is None:
        env = os.environ.get('FLASK_ENV', 'development')
        _app = create_app(env)
    return _app


_app = None


def main():
    """Main entry point"""
    # Create necessary directories
    create_directories()

    # Get environment
    env = os.environ.get('FLASK_ENV', 'development')
    print(f"\nStarting QR-Based Transaction Data Protection System")
    print(f"Environment: {env}")
    print("-" * 50)

    # Create application (using singleton)
    app = get_app()

    # Initialize database
    with app.app_context():
        db.create_all()
        print("Database initialized.")

    # Initialize AI model
    initialize_ai_model(app)

    # Get host and port from environment or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = env == 'development'

    print(f"\nServer starting on http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/api/docs/")
    print("-" * 50)
    print("\nEndpoints:")
    print("  POST /api/auth/register     - Register new user")
    print("  POST /api/auth/login        - User login")
    print("  POST /api/transactions/generate-qr  - Generate QR code")
    print("  POST /api/transactions/verify-qr    - Verify QR code")
    print("  POST /api/transactions/process      - Process transaction")
    print("  GET  /api/admin/dashboard   - Admin dashboard")
    print("  POST /api/tamper/analyze    - Analyze for tampering")
    print("-" * 50)

    # Run the application (use_reloader=False to avoid multi-process JWT issues)
    app.run(host=host, port=port, debug=debug, use_reloader=False)


# Flask CLI support - use the same app instance
app = get_app()


@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    db.create_all()
    print('Database initialized.')


@app.cli.command('seed-db')
def seed_db_command():
    """Seed the database with sample data."""
    from seed_database import seed_database
    seed_database()


@app.cli.command('train-model')
def train_model_command():
    """Train the AI tamper detection model."""
    initialize_ai_model(app)


if __name__ == '__main__':
    main()
