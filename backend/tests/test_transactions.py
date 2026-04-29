"""
Unit tests for transaction and QR code services
"""
import pytest
from datetime import datetime, timedelta
from app.models import Transaction, TransactionStatus
from app.services.qr_service import QRService, get_qr_service


class TestQRService:
    """Test cases for QRService"""

    @pytest.fixture
    def qr_service(self):
        """Create QR service instance"""
        return QRService()

    def test_generate_transaction_ref(self, qr_service):
        """Test transaction reference generation"""
        ref = qr_service.generate_transaction_ref()

        assert ref.startswith('QRT-')
        assert len(ref) > 20

    def test_unique_transaction_refs(self, qr_service):
        """Test that transaction references are unique"""
        refs = [qr_service.generate_transaction_ref() for _ in range(100)]
        assert len(refs) == len(set(refs))


class TestTransactionRoutes:
    """Test cases for transaction routes"""

    def test_generate_qr(self, client, auth_headers, db_session):
        """Test QR code generation"""
        response = client.post('/api/transactions/generate-qr', json={
            'amount': 100.50,
            'description': 'Test transaction',
            'transaction_type': 'maintenance_fee'
        }, headers=auth_headers)

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'transaction_ref' in data
        assert 'qr_code_data' in data
        assert 'qr_code_hash' in data
        assert data['amount'] == 100.50

    def test_generate_qr_invalid_amount(self, client, auth_headers, db_session):
        """Test QR generation with invalid amount"""
        response = client.post('/api/transactions/generate-qr', json={
            'amount': -50,
            'description': 'Invalid amount'
        }, headers=auth_headers)

        assert response.status_code == 400

    def test_generate_qr_exceeds_max_amount(self, client, auth_headers, db_session):
        """Test QR generation exceeding max amount"""
        response = client.post('/api/transactions/generate-qr', json={
            'amount': 200000,  # Exceeds 100000 limit
            'description': 'Too much'
        }, headers=auth_headers)

        assert response.status_code == 400

    def test_generate_qr_unauthorized(self, client, db_session):
        """Test QR generation without authentication"""
        response = client.post('/api/transactions/generate-qr', json={
            'amount': 100
        })

        assert response.status_code == 401

    def test_verify_qr(self, client, auth_headers, db_session):
        """Test QR code verification"""
        # First generate a QR
        gen_response = client.post('/api/transactions/generate-qr', json={
            'amount': 50.00,
            'description': 'Test'
        }, headers=auth_headers)

        qr_data = gen_response.get_json()

        # Now verify
        response = client.post('/api/transactions/verify-qr', json={
            'qr_code_data': qr_data['qr_code_data'],
            'qr_code_hash': qr_data['qr_code_hash']
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_verify_qr_tampered(self, client, auth_headers, db_session):
        """Test verification of tampered QR code"""
        # First generate a QR
        gen_response = client.post('/api/transactions/generate-qr', json={
            'amount': 50.00
        }, headers=auth_headers)

        qr_data = gen_response.get_json()

        # Tamper with the data
        tampered = qr_data['qr_code_data'][:-10] + 'XXXXXXXXXX'

        response = client.post('/api/transactions/verify-qr', json={
            'qr_code_data': tampered,
            'qr_code_hash': qr_data['qr_code_hash']
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False

    def test_transaction_history(self, client, auth_headers, db_session):
        """Test getting transaction history"""
        # Generate some transactions first
        for i in range(3):
            client.post('/api/transactions/generate-qr', json={
                'amount': 50.00 + i,
                'description': f'Test transaction {i}'
            }, headers=auth_headers)

        response = client.get('/api/transactions/history', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'transactions' in data
        assert 'total' in data

    def test_transaction_history_pagination(self, client, auth_headers, db_session):
        """Test transaction history pagination"""
        response = client.get('/api/transactions/history?page=1&per_page=5',
                              headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert 'current_page' in data
        assert 'per_page' in data
        assert data['per_page'] == 5

    def test_transaction_statistics(self, client, auth_headers, db_session):
        """Test getting transaction statistics"""
        response = client.get('/api/transactions/statistics?days=30',
                              headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'period_days' in data
        assert 'total_transactions' in data
        assert 'total_amount' in data

    def test_cancel_transaction(self, client, auth_headers, db_session):
        """Test cancelling a transaction"""
        # Generate a transaction
        gen_response = client.post('/api/transactions/generate-qr', json={
            'amount': 75.00,
            'description': 'To be cancelled'
        }, headers=auth_headers)

        tx_ref = gen_response.get_json()['transaction_ref']

        # Cancel it
        response = client.post(f'/api/transactions/cancel/{tx_ref}', json={
            'reason': 'User requested cancellation'
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_transaction_details(self, client, auth_headers, db_session):
        """Test getting transaction details"""
        # Generate a transaction
        gen_response = client.post('/api/transactions/generate-qr', json={
            'amount': 100.00
        }, headers=auth_headers)

        tx_ref = gen_response.get_json()['transaction_ref']

        # Get details
        response = client.get(f'/api/transactions/{tx_ref}',
                              headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'transaction' in data


class TestTransactionProcessing:
    """Test cases for transaction processing"""

    def test_process_transaction_without_2fa(self, client, auth_headers, db_session):
        """Test processing transaction (2FA not enabled)"""
        # Generate a transaction
        gen_response = client.post('/api/transactions/generate-qr', json={
            'amount': 50.00,
            'description': 'Test payment'
        }, headers=auth_headers)

        qr_data = gen_response.get_json()

        # Process it (with placeholder OTP since 2FA not enabled)
        response = client.post('/api/transactions/process', json={
            'qr_code_data': qr_data['qr_code_data'],
            'otp_code': '123456'
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'completed_at' in data

    def test_process_invalid_qr(self, client, auth_headers, db_session):
        """Test processing invalid QR code"""
        response = client.post('/api/transactions/process', json={
            'qr_code_data': 'invalid_qr_data',
            'otp_code': '123456'
        }, headers=auth_headers)

        assert response.status_code == 400
