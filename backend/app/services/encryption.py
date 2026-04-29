"""
AES-256 Encryption Service for QR-Based Transaction Data Protection System
"""
import os
import base64
import hashlib
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    AES-256 encryption service for protecting sensitive transaction data.
    Uses CBC mode with PKCS7 padding for secure encryption.
    """

    def __init__(self, key=None):
        """
        Initialize the encryption service with AES-256 key.

        Args:
            key: 32-byte key for AES-256. If None, uses config key.
        """
        self._key = None
        self._provided_key = key

    @property
    def key(self):
        """Get the encryption key, deriving from config if needed"""
        if self._key is None:
            if self._provided_key:
                key_source = self._provided_key
            else:
                try:
                    key_source = current_app.config.get('AES_KEY', 'default-key-change-in-production')
                except RuntimeError:
                    key_source = 'default-key-change-in-production'

            # Ensure key is exactly 32 bytes for AES-256
            if isinstance(key_source, str):
                key_source = key_source.encode('utf-8')
            self._key = hashlib.sha256(key_source).digest()
        return self._key

    def _generate_iv(self):
        """Generate a random 16-byte IV for CBC mode"""
        return os.urandom(16)

    def encrypt(self, plaintext):
        """
        Encrypt plaintext data using AES-256-CBC.

        Args:
            plaintext: String or bytes to encrypt

        Returns:
            Base64 encoded string containing IV + ciphertext
        """
        try:
            # Convert string to bytes if necessary
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')

            # Generate random IV
            iv = self._generate_iv()

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Apply PKCS7 padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext) + padder.finalize()

            # Encrypt
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # Combine IV and ciphertext, encode as base64
            encrypted_data = base64.b64encode(iv + ciphertext).decode('utf-8')

            logger.debug("Data encrypted successfully")
            return encrypted_data

        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")

    def decrypt(self, encrypted_data):
        """
        Decrypt AES-256-CBC encrypted data.

        Args:
            encrypted_data: Base64 encoded string containing IV + ciphertext

        Returns:
            Decrypted string
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data)

            # Extract IV (first 16 bytes) and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()

            # Remove PKCS7 padding
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_data) + unpadder.finalize()

            logger.debug("Data decrypted successfully")
            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")

    def encrypt_dict(self, data_dict):
        """
        Encrypt a dictionary by converting to JSON first.

        Args:
            data_dict: Dictionary to encrypt

        Returns:
            Encrypted base64 string
        """
        json_string = json.dumps(data_dict, default=str)
        return self.encrypt(json_string)

    def decrypt_dict(self, encrypted_data):
        """
        Decrypt data and parse as JSON dictionary.

        Args:
            encrypted_data: Encrypted base64 string

        Returns:
            Decrypted dictionary
        """
        json_string = self.decrypt(encrypted_data)
        return json.loads(json_string)

    def generate_hash(self, data):
        """
        Generate SHA-256 hash for data integrity verification.

        Args:
            data: String or bytes to hash

        Returns:
            Hexadecimal hash string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    def verify_hash(self, data, expected_hash):
        """
        Verify data integrity using SHA-256 hash.

        Args:
            data: String or bytes to verify
            expected_hash: Expected hash value

        Returns:
            Boolean indicating if hash matches
        """
        actual_hash = self.generate_hash(data)
        return actual_hash == expected_hash

    def encrypt_qr_payload(self, transaction_data):
        """
        Encrypt QR code transaction payload with additional metadata.

        Args:
            transaction_data: Dictionary containing transaction details

        Returns:
            Dictionary with encrypted payload and hash
        """
        # Add timestamp for freshness
        import time
        transaction_data['encrypted_at'] = int(time.time())

        # Encrypt the payload
        encrypted_payload = self.encrypt_dict(transaction_data)

        # Generate hash for integrity verification
        payload_hash = self.generate_hash(encrypted_payload)

        return {
            'encrypted_payload': encrypted_payload,
            'payload_hash': payload_hash
        }

    def decrypt_qr_payload(self, encrypted_payload, expected_hash=None):
        """
        Decrypt and verify QR code transaction payload.

        Args:
            encrypted_payload: Encrypted base64 string
            expected_hash: Optional hash for integrity verification

        Returns:
            Decrypted transaction data dictionary

        Raises:
            EncryptionError: If decryption fails or hash doesn't match
        """
        # Verify integrity if hash provided
        if expected_hash:
            if not self.verify_hash(encrypted_payload, expected_hash):
                raise EncryptionError("QR code integrity check failed - possible tampering detected")

        # Decrypt payload
        return self.decrypt_dict(encrypted_payload)


class EncryptionError(Exception):
    """Custom exception for encryption-related errors"""
    pass


# Singleton instance for convenience
_encryption_service = None


def get_encryption_service():
    """Get or create the singleton encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_data(plaintext):
    """Encrypt plaintext data"""
    return get_encryption_service().encrypt(plaintext)


def decrypt_data(encrypted_data):
    """Decrypt encrypted data"""
    return get_encryption_service().decrypt(encrypted_data)


def generate_hash(data):
    """Generate SHA-256 hash"""
    return get_encryption_service().generate_hash(data)


def verify_hash(data, expected_hash):
    """Verify data hash"""
    return get_encryption_service().verify_hash(data, expected_hash)
