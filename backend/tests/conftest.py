"""
Pytest configuration and fixtures for QR-Based Transaction Data Protection System
"""
import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, UserRole
from app.services.auth_service import get_auth_service


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


@pytest.fixture(scope='function')
def sample_user(app, db_session):
    """Create a sample resident user"""
    auth_service = get_auth_service()

    user = User(
        email='testuser@example.com',
        password_hash=auth_service.hash_password('TestPass@123'),
        full_name='Test User',
        phone_number='+60123456789',
        unit_number='A-01-01',
        community_name='Test Community',
        role=UserRole.RESIDENT,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture(scope='function')
def admin_user(app, db_session):
    """Create a sample admin user"""
    auth_service = get_auth_service()

    user = User(
        email='admin@example.com',
        password_hash=auth_service.hash_password('AdminPass@123'),
        full_name='Admin User',
        phone_number='+60123456790',
        community_name='Test Community',
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture(scope='function')
def auth_headers(client, sample_user):
    """Get authentication headers for sample user"""
    response = client.post('/api/auth/login', json={
        'email': 'testuser@example.com',
        'password': 'TestPass@123'
    })

    data = response.get_json()
    token = data.get('access_token')

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='function')
def admin_auth_headers(client, admin_user):
    """Get authentication headers for admin user"""
    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com',
        'password': 'AdminPass@123'
    })

    data = response.get_json()
    token = data.get('access_token')

    return {'Authorization': f'Bearer {token}'}
