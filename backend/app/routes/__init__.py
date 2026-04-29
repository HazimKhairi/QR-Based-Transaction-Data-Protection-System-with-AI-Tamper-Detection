"""
Routes package for QR-Based Transaction Data Protection System
"""
from app.routes.auth import auth_bp
from app.routes.transactions import transactions_bp
from app.routes.admin import admin_bp
from app.routes.tamper_detection import tamper_bp

__all__ = ['auth_bp', 'transactions_bp', 'admin_bp', 'tamper_bp']
