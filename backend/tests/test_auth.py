"""
Unit tests for authentication service and routes
"""
import pytest
from app.services.auth_service import AuthService, get_auth_service


class TestAuthService:
    """Test cases for AuthService"""

    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        return AuthService()

    def test_password_hashing(self, auth_service):
        """Test password hashing"""
        password = "TestPassword@123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_password_verification(self, auth_service):
        """Test password verification"""
        password = "TestPassword@123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("WrongPassword", hashed) is False

    def test_totp_secret_generation(self, auth_service):
        """Test TOTP secret generation"""
        secret = auth_service.generate_totp_secret()

        assert secret is not None
        assert len(secret) == 32  # Base32 encoded

    def test_totp_uri_generation(self, auth_service):
        """Test TOTP provisioning URI generation"""
        secret = auth_service.generate_totp_secret()
        uri = auth_service.get_totp_uri("test@example.com", secret)

        assert uri.startswith("otpauth://totp/")
        assert "test@example.com" in uri

    def test_totp_verification(self, auth_service):
        """Test TOTP code verification"""
        import pyotp

        secret = auth_service.generate_totp_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        assert auth_service.verify_totp(secret, valid_code) is True
        assert auth_service.verify_totp(secret, "000000") is False

    def test_singleton_service(self):
        """Test singleton instance retrieval"""
        service1 = get_auth_service()
        service2 = get_auth_service()

        assert service1 is service2


class TestAuthRoutes:
    """Test cases for authentication routes"""

    def test_register_success(self, client, db_session):
        """Test successful user registration"""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'NewUser@123',
            'full_name': 'New User',
            'phone_number': '+60123456789',
            'unit_number': 'A-01-01',
            'community_name': 'Test Community'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['email'] == 'newuser@example.com'

    def test_register_duplicate_email(self, client, sample_user):
        """Test registration with duplicate email"""
        response = client.post('/api/auth/register', json={
            'email': 'testuser@example.com',  # Same as sample_user
            'password': 'NewUser@123',
            'full_name': 'New User'
        })

        assert response.status_code == 409
        data = response.get_json()
        assert data['success'] is False
        assert 'already registered' in data['error'].lower()

    def test_register_weak_password(self, client, db_session):
        """Test registration with weak password"""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'weak',  # Too short, no special chars
            'full_name': 'New User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_register_invalid_email(self, client, db_session):
        """Test registration with invalid email"""
        response = client.post('/api/auth/register', json={
            'email': 'invalid-email',
            'password': 'ValidPass@123',
            'full_name': 'New User'
        })

        assert response.status_code == 400

    def test_login_success(self, client, sample_user):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'email': 'testuser@example.com',
            'password': 'TestPass@123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['email'] == 'testuser@example.com'

    def test_login_wrong_password(self, client, sample_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'email': 'testuser@example.com',
            'password': 'WrongPassword@123'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user"""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'AnyPassword@123'
        })

        assert response.status_code == 401

    def test_get_profile(self, client, auth_headers):
        """Test getting user profile"""
        response = client.get('/api/auth/profile', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'user' in data

    def test_get_profile_unauthorized(self, client):
        """Test getting profile without authentication"""
        response = client.get('/api/auth/profile')

        assert response.status_code == 401

    def test_update_profile(self, client, auth_headers):
        """Test updating user profile"""
        response = client.put('/api/auth/profile', json={
            'full_name': 'Updated Name',
            'phone_number': '+60198765432'
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['full_name'] == 'Updated Name'

    def test_refresh_token(self, client, sample_user):
        """Test token refresh"""
        # First login
        login_response = client.post('/api/auth/login', json={
            'email': 'testuser@example.com',
            'password': 'TestPass@123'
        })

        refresh_token = login_response.get_json()['refresh_token']

        # Refresh
        response = client.post('/api/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data

    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post('/api/auth/logout', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_password_reset_request(self, client, sample_user):
        """Test password reset request"""
        response = client.post('/api/auth/password/reset-request', json={
            'email': 'testuser@example.com'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # In prototype, token is returned in response
        assert 'token' in data

    def test_change_password(self, client, auth_headers):
        """Test password change"""
        response = client.post('/api/auth/password/change', json={
            'current_password': 'TestPass@123',
            'new_password': 'NewTestPass@456'
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password"""
        response = client.post('/api/auth/password/change', json={
            'current_password': 'WrongPassword@123',
            'new_password': 'NewTestPass@456'
        }, headers=auth_headers)

        assert response.status_code == 401
