"""
Configuration settings for QR-Based Transaction Data Protection System
"""
import os
from datetime import timedelta

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
    OTP_VALID_WINDOW = 1  # Allow 1 step tolerance for time sync issues

    # AI Model settings
    AI_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'tamper_detection_model.joblib')
    ANOMALY_THRESHOLD = -0.5  # Isolation Forest anomaly threshold

    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'

    # CORS settings
    CORS_ORIGINS = ['*']  # In production, specify exact origins


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
