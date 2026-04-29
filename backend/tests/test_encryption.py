"""
Unit tests for AES-256 encryption service
"""
import pytest
import json
from app.services.encryption import (
    EncryptionService, EncryptionError,
    encrypt_data, decrypt_data, generate_hash, verify_hash
)


class TestEncryptionService:
    """Test cases for EncryptionService"""

    def test_encryption_service_initialization(self):
        """Test encryption service can be initialized"""
        service = EncryptionService(key='test-key-12345678901234567890')
        assert service is not None

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string"""
        service = EncryptionService(key='test-key-12345678901234567890')

        original = "Hello, this is a test message!"
        encrypted = service.encrypt(original)

        # Encrypted data should be different from original
        assert encrypted != original

        # Decrypt should return original
        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_unicode(self):
        """Test encrypting and decrypting Unicode strings (Malaysian context)"""
        service = EncryptionService(key='test-key-12345678901234567890')

        original = "Selamat datang ke Taman Harmoni!"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_decrypt_special_characters(self):
        """Test encrypting and decrypting special characters"""
        service = EncryptionService(key='test-key-12345678901234567890')

        original = "Amount: RM 100.50 @#$%^&*()"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_decrypt_dict(self):
        """Test encrypting and decrypting dictionaries"""
        service = EncryptionService(key='test-key-12345678901234567890')

        original = {
            'transaction_ref': 'QRT-20240101-ABC12345',
            'amount': 150.50,
            'user_id': 123,
            'description': 'Maintenance fee'
        }

        encrypted = service.encrypt_dict(original)
        decrypted = service.decrypt_dict(encrypted)

        assert decrypted == original

    def test_generate_hash(self):
        """Test SHA-256 hash generation"""
        service = EncryptionService(key='test-key-12345678901234567890')

        data = "test data for hashing"
        hash1 = service.generate_hash(data)
        hash2 = service.generate_hash(data)

        # Same data should produce same hash
        assert hash1 == hash2

        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    def test_verify_hash(self):
        """Test hash verification"""
        service = EncryptionService(key='test-key-12345678901234567890')

        data = "test data"
        correct_hash = service.generate_hash(data)

        assert service.verify_hash(data, correct_hash) is True
        assert service.verify_hash(data, "wrong_hash") is False

    def test_encrypt_qr_payload(self):
        """Test QR code payload encryption"""
        service = EncryptionService(key='test-key-12345678901234567890')

        transaction_data = {
            'transaction_ref': 'QRT-TEST-001',
            'amount': 100.00,
            'user_id': 1
        }

        result = service.encrypt_qr_payload(transaction_data)

        assert 'encrypted_payload' in result
        assert 'payload_hash' in result
        assert len(result['payload_hash']) == 64

    def test_decrypt_qr_payload(self):
        """Test QR code payload decryption"""
        service = EncryptionService(key='test-key-12345678901234567890')

        transaction_data = {
            'transaction_ref': 'QRT-TEST-001',
            'amount': 100.00,
            'user_id': 1
        }

        encrypted = service.encrypt_qr_payload(transaction_data)
        decrypted = service.decrypt_qr_payload(
            encrypted['encrypted_payload'],
            encrypted['payload_hash']
        )

        assert decrypted['transaction_ref'] == transaction_data['transaction_ref']
        assert decrypted['amount'] == transaction_data['amount']
        assert 'encrypted_at' in decrypted  # Added by encrypt_qr_payload

    def test_decrypt_qr_payload_tampered(self):
        """Test detection of tampered QR payload"""
        service = EncryptionService(key='test-key-12345678901234567890')

        transaction_data = {
            'transaction_ref': 'QRT-TEST-001',
            'amount': 100.00
        }

        encrypted = service.encrypt_qr_payload(transaction_data)

        # Tamper with the payload
        tampered_payload = encrypted['encrypted_payload'][:-5] + "XXXXX"

        with pytest.raises(EncryptionError):
            service.decrypt_qr_payload(tampered_payload, encrypted['payload_hash'])

    def test_different_keys_produce_different_ciphertext(self):
        """Test that different keys produce different encrypted data"""
        service1 = EncryptionService(key='key-one-1234567890123456')
        service2 = EncryptionService(key='key-two-1234567890123456')

        original = "Test message"

        encrypted1 = service1.encrypt(original)
        encrypted2 = service2.encrypt(original)

        assert encrypted1 != encrypted2

    def test_convenience_functions(self):
        """Test module-level convenience functions"""
        original = "Test data"

        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)

        assert decrypted == original

        hash_value = generate_hash(original)
        assert verify_hash(original, hash_value) is True
        assert verify_hash(original, "wrong") is False

    def test_empty_string_encryption(self):
        """Test encrypting empty string"""
        service = EncryptionService(key='test-key-12345678901234567890')

        original = ""
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_large_data_encryption(self):
        """Test encrypting large data"""
        service = EncryptionService(key='test-key-12345678901234567890')

        # Create large string (1MB)
        original = "A" * (1024 * 1024)
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
