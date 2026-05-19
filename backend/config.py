"""
Configuration settings for QR-Based Transaction Data Protection System
"""
import os
from datetime import timedelta

# Load .env before any os.environ.get() calls below
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    """Base configuration class"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'qr-transaction-protection-secret-key-2024')

    # Database settings - MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'mysql+pymysql://root:@localhost:3306/qr_transaction'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-for-qr-protection-2024')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # AES-256 Encryption settings
    AES_KEY = os.environ.get('AES_KEY', 'QRTransactionProtection2024SecureKey!')  # 32 bytes for AES-256

    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # 2FA settings
    OTP_ISSUER_NAME = "QR Transaction Protection"
    # Window=2 accepts the current 30s step plus 60s on either side.
    # Compensates for small client/server clock drift, common on fresh
    # Windows boxes that haven't synced NTP yet.
    OTP_VALID_WINDOW = int(os.environ.get('OTP_VALID_WINDOW', '2'))

    # Demo 2FA — fixed TOTP secret used by /api/transactions/demo/* endpoints.
    # Pinned by default so pairing an authenticator once survives every
    # backend restart. Override via env for a fresh secret per deploy.
    DEMO_TOTP_SECRET = os.environ.get(
        'DEMO_TOTP_SECRET',
        'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
    )
    DEMO_TOTP_ACCOUNT = os.environ.get('DEMO_TOTP_ACCOUNT', 'demo@qrtransaction.my')

    # AI Model settings
    AI_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'tamper_detection_model.joblib')
    ANOMALY_THRESHOLD = -0.5  # Isolation Forest anomaly threshold

    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'

    # CORS settings
    CORS_ORIGINS = ['*']  # In production, specify exact origins

    # Email (SMTP) settings — used by app.services.email_service
    MAIL_ENABLED = _env_bool('MAIL_ENABLED', False)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = _env_bool('MAIL_USE_TLS', True)
    MAIL_USE_SSL = _env_bool('MAIL_USE_SSL', False)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'QR Transaction Protection')
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', '15'))

    # Frontend base URL for links inside emails (password reset, etc.)
    APP_FRONTEND_URL = os.environ.get('APP_FRONTEND_URL', 'http://localhost:3000')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, use environment variables for sensitive data
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    AES_KEY = os.environ.get('AES_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_qr_transaction.db'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    RATELIMIT_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
