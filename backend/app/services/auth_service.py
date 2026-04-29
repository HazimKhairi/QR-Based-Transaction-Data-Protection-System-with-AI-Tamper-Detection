"""
Authentication Service with 2FA support using TOTP
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
import bcrypt
import pyotp
from flask import current_app
from app import db
from app.models import User, TokenBlacklist, PasswordResetToken, UserRole, AuditLog
from app.services.encryption import get_encryption_service

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class AuthService:
    """
    Authentication service providing:
    - Password hashing and verification
    - TOTP-based Two-Factor Authentication
    - Token management
    - Account security features
    """

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    PASSWORD_RESET_EXPIRY_HOURS = 24

    def __init__(self):
        self.encryption = get_encryption_service()

    def _get_otp_issuer(self):
        """Get OTP issuer name from config"""
        try:
            return current_app.config.get('OTP_ISSUER_NAME', 'QR Transaction Protection')
        except RuntimeError:
            return 'QR Transaction Protection'

    def _get_otp_valid_window(self):
        """Get OTP valid window from config"""
        try:
            return current_app.config.get('OTP_VALID_WINDOW', 1)
        except RuntimeError:
            return 1

    def hash_password(self, password):
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password, password_hash):
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            password_hash: Stored hash

        Returns:
            Boolean indicating if password matches
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

    def generate_totp_secret(self):
        """
        Generate a new TOTP secret for 2FA.

        Returns:
            Base32 encoded secret
        """
        return pyotp.random_base32()

    def get_totp_uri(self, user_email, secret):
        """
        Generate a TOTP provisioning URI for authenticator apps.

        Args:
            user_email: User's email address
            secret: TOTP secret

        Returns:
            otpauth:// URI string
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self._get_otp_issuer()
        )

    def verify_totp(self, secret, otp_code):
        """
        Verify a TOTP code.

        Args:
            secret: User's TOTP secret
            otp_code: 6-digit OTP code

        Returns:
            Boolean indicating if code is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(otp_code, valid_window=self._get_otp_valid_window())
        except Exception as e:
            logger.error(f"TOTP verification error: {str(e)}")
            return False

    def setup_2fa(self, user):
        """
        Set up 2FA for a user.

        Args:
            user: User model instance

        Returns:
            Dictionary with secret and provisioning URI
        """
        try:
            # Generate new secret
            secret = self.generate_totp_secret()

            # Encrypt secret before storing
            encrypted_secret = self.encryption.encrypt(secret)

            # Update user
            user.totp_secret = encrypted_secret
            user.is_2fa_enabled = False  # Not enabled until verified
            user.is_2fa_verified = False
            db.session.commit()

            # Generate provisioning URI
            uri = self.get_totp_uri(user.email, secret)

            logger.info(f"2FA setup initiated for user {user.id}")

            return {
                'secret': secret,
                'provisioning_uri': uri,
                'message': 'Scan the QR code with your authenticator app'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"2FA setup error: {str(e)}")
            raise

    def verify_2fa_setup(self, user, otp_code):
        """
        Verify 2FA setup by checking initial OTP code.

        Args:
            user: User model instance
            otp_code: OTP code from authenticator app

        Returns:
            Boolean indicating if verification succeeded
        """
        try:
            if not user.totp_secret:
                return False

            # Decrypt secret
            secret = self.encryption.decrypt(user.totp_secret)

            # Verify OTP
            if self.verify_totp(secret, otp_code):
                user.is_2fa_enabled = True
                user.is_2fa_verified = True
                db.session.commit()

                logger.info(f"2FA enabled for user {user.id}")
                return True

            return False

        except Exception as e:
            db.session.rollback()
            logger.error(f"2FA verification error: {str(e)}")
            return False

    def disable_2fa(self, user, otp_code):
        """
        Disable 2FA for a user.

        Args:
            user: User model instance
            otp_code: Current OTP code for verification

        Returns:
            Boolean indicating if 2FA was disabled
        """
        try:
            if not user.is_2fa_enabled:
                return True

            # Decrypt and verify OTP
            secret = self.encryption.decrypt(user.totp_secret)
            if not self.verify_totp(secret, otp_code):
                return False

            user.totp_secret = None
            user.is_2fa_enabled = False
            user.is_2fa_verified = False
            db.session.commit()

            security_logger.warning(f"2FA disabled for user {user.id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"2FA disable error: {str(e)}")
            return False

    def verify_user_otp(self, user, otp_code):
        """
        Verify OTP for an authenticated user.

        Args:
            user: User model instance
            otp_code: OTP code to verify

        Returns:
            Boolean indicating if OTP is valid
        """
        if not user.is_2fa_enabled or not user.totp_secret:
            return True  # 2FA not enabled, pass through

        try:
            secret = self.encryption.decrypt(user.totp_secret)
            return self.verify_totp(secret, otp_code)
        except Exception as e:
            logger.error(f"OTP verification error for user {user.id}: {str(e)}")
            return False

    def check_account_lock(self, user):
        """
        Check if user account is locked due to failed attempts.

        Args:
            user: User model instance

        Returns:
            Tuple (is_locked, minutes_remaining)
        """
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
            return True, int(remaining)
        return False, 0

    def record_login_attempt(self, user, success, ip_address=None):
        """
        Record a login attempt and handle account locking.

        Args:
            user: User model instance
            success: Whether login was successful
            ip_address: Client IP address
        """
        try:
            if success:
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.utcnow()
                logger.info(f"Successful login for user {user.id} from {ip_address}")
            else:
                user.failed_login_attempts += 1

                if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    user.locked_until = datetime.utcnow() + timedelta(
                        minutes=self.LOCKOUT_DURATION_MINUTES
                    )
                    security_logger.warning(
                        f"Account locked for user {user.id} after {user.failed_login_attempts} "
                        f"failed attempts from {ip_address}"
                    )

                security_logger.warning(
                    f"Failed login attempt {user.failed_login_attempts} for user {user.id} "
                    f"from {ip_address}"
                )

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording login attempt: {str(e)}")

    def generate_password_reset_token(self, user):
        """
        Generate a password reset token.

        Args:
            user: User model instance

        Returns:
            Reset token string
        """
        try:
            # Generate secure token
            token = secrets.token_urlsafe(32)

            # Create reset token record
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=self.PASSWORD_RESET_EXPIRY_HOURS)
            )
            db.session.add(reset_token)
            db.session.commit()

            logger.info(f"Password reset token generated for user {user.id}")
            return token

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating reset token: {str(e)}")
            raise

    def verify_password_reset_token(self, token):
        """
        Verify a password reset token.

        Args:
            token: Reset token string

        Returns:
            User model instance if valid, None otherwise
        """
        try:
            reset_token = PasswordResetToken.query.filter_by(
                token=token,
                is_used=False
            ).first()

            if not reset_token:
                return None

            if reset_token.expires_at < datetime.utcnow():
                return None

            return User.query.get(reset_token.user_id)

        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return None

    def reset_password(self, token, new_password):
        """
        Reset user password using reset token.

        Args:
            token: Reset token string
            new_password: New password

        Returns:
            Boolean indicating success
        """
        try:
            reset_token = PasswordResetToken.query.filter_by(
                token=token,
                is_used=False
            ).first()

            if not reset_token or reset_token.expires_at < datetime.utcnow():
                return False

            user = User.query.get(reset_token.user_id)
            if not user:
                return False

            # Update password
            user.password_hash = self.hash_password(new_password)
            user.failed_login_attempts = 0
            user.locked_until = None

            # Mark token as used
            reset_token.is_used = True

            db.session.commit()

            logger.info(f"Password reset successful for user {user.id}")
            security_logger.warning(f"Password reset completed for user {user.id}")

            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting password: {str(e)}")
            return False

    def blacklist_token(self, jti, token_type, user_id, expires_at):
        """
        Add a token to the blacklist.

        Args:
            jti: JWT ID
            token_type: 'access' or 'refresh'
            user_id: User ID
            expires_at: Token expiration datetime
        """
        try:
            blacklisted = TokenBlacklist(
                jti=jti,
                token_type=token_type,
                user_id=user_id,
                expires_at=expires_at
            )
            db.session.add(blacklisted)
            db.session.commit()

            logger.info(f"Token blacklisted for user {user_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error blacklisting token: {str(e)}")

    def is_token_blacklisted(self, jti):
        """
        Check if a token is blacklisted.

        Args:
            jti: JWT ID

        Returns:
            Boolean indicating if token is blacklisted
        """
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None

    def create_audit_log(self, user_id, action, resource_type=None, resource_id=None,
                         description=None, ip_address=None, user_agent=None,
                         endpoint=None, method=None, status='success',
                         error_message=None, severity='info'):
        """
        Create an audit log entry.

        Args:
            Various audit log fields

        Returns:
            AuditLog instance
        """
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                method=method,
                status=status,
                error_message=error_message,
                severity=severity
            )
            db.session.add(log)
            db.session.commit()

            return log

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating audit log: {str(e)}")
            return None


# Singleton instance
_auth_service = None


def get_auth_service():
    """Get or create the singleton auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
