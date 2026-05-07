"""
Database models for QR-Based Transaction Data Protection System
"""
from datetime import datetime
from app import db
import enum


class UserRole(enum.Enum):
    """User role enumeration"""
    RESIDENT = 'resident'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'


class TransactionStatus(enum.Enum):
    """Transaction status enumeration"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    FLAGGED = 'flagged'  # Flagged for potential fraud


class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    MAINTENANCE_FEE = 'maintenance_fee'
    SECURITY_PAYMENT = 'security_payment'
    EVENT_FEE = 'event_fee'
    PASAR_MALAM = 'pasar_malam'
    FACILITY_BOOKING = 'facility_booking'
    OTHER = 'other'


class User(db.Model):
    """User model for residents and admins"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    unit_number = db.Column(db.String(20), nullable=True)  # For residents
    community_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.RESIDENT, nullable=False)

    # 2FA fields
    # Stores AES-encrypted TOTP secret (base64 of IV + ciphertext) — needs ample room
    totp_secret = db.Column(db.String(255), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    is_2fa_verified = db.Column(db.Boolean, default=False)

    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Notification preferences
    notify_email_enabled = db.Column(db.Boolean, default=True, nullable=False)
    notify_fraud_alerts_enabled = db.Column(db.Boolean, default=True, nullable=False)

    # "Logout from all devices" cutoff — any token issued before this time is rejected
    tokens_valid_after = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic',
                                   foreign_keys='Transaction.user_id')
    received_transactions = db.relationship('Transaction', backref='recipient',
                                             lazy='dynamic', foreign_keys='Transaction.recipient_id')
    logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'unit_number': self.unit_number,
            'community_name': self.community_name,
            'role': self.role.value,
            'is_2fa_enabled': self.is_2fa_enabled,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'notify_email_enabled': self.notify_email_enabled,
            'notify_fraud_alerts_enabled': self.notify_fraud_alerts_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        if include_sensitive:
            data['is_2fa_verified'] = self.is_2fa_verified
            data['failed_login_attempts'] = self.failed_login_attempts
        return data


class Transaction(db.Model):
    """Transaction model for QR code payments"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    transaction_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # User references
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Transaction details (encrypted fields marked)
    amount = db.Column(db.Float, nullable=False)  # Stored encrypted
    amount_encrypted = db.Column(db.Text, nullable=True)  # Encrypted amount
    currency = db.Column(db.String(3), default='MYR')
    description = db.Column(db.String(255), nullable=True)
    description_encrypted = db.Column(db.Text, nullable=True)  # Encrypted description

    # QR Code data
    qr_code_data = db.Column(db.Text, nullable=False)  # Encrypted QR payload
    qr_code_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hash for integrity
    qr_generated_at = db.Column(db.DateTime, nullable=False)
    qr_expires_at = db.Column(db.DateTime, nullable=True)

    # Transaction metadata
    transaction_type = db.Column(db.Enum(TransactionType), default=TransactionType.OTHER)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING, index=True)

    # Security and verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    device_info = db.Column(db.String(255), nullable=True)

    # Tamper detection
    tamper_score = db.Column(db.Float, default=0.0)  # AI detection score
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(255), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    tamper_results = db.relationship('TamperDetectionResult', backref='transaction', lazy='dynamic')

    def __repr__(self):
        return f'<Transaction {self.transaction_ref}>'

    def to_dict(self, include_sensitive=False):
        """Convert transaction to dictionary"""
        data = {
            'id': self.id,
            'transaction_ref': self.transaction_ref,
            'user_id': self.user_id,
            'recipient_id': self.recipient_id,
            'amount': self.amount,
            'currency': self.currency,
            'description': self.description,
            'transaction_type': self.transaction_type.value if self.transaction_type else None,
            'status': self.status.value if self.status else None,
            'is_verified': self.is_verified,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'tamper_score': self.tamper_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'qr_expires_at': self.qr_expires_at.isoformat() if self.qr_expires_at else None
        }
        if include_sensitive:
            data['ip_address'] = self.ip_address
            data['device_info'] = self.device_info
            data['qr_code_hash'] = self.qr_code_hash
        return data


class TamperDetectionResult(db.Model):
    """AI tamper detection results"""
    __tablename__ = 'tamper_detection_results'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False, index=True)

    # Detection results
    anomaly_score = db.Column(db.Float, nullable=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    confidence = db.Column(db.Float, nullable=True)

    # Detection details
    detection_type = db.Column(db.String(50), nullable=True)  # amount, frequency, qr_modification, etc.
    details = db.Column(db.Text, nullable=True)  # JSON string with detailed analysis
    features_analyzed = db.Column(db.Text, nullable=True)  # JSON string of features used

    # Model information
    model_version = db.Column(db.String(20), default='1.0.0')

    # Timestamps
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TamperDetectionResult {self.id} - Transaction {self.transaction_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'anomaly_score': self.anomaly_score,
            'is_anomaly': self.is_anomaly,
            'confidence': self.confidence,
            'detection_type': self.detection_type,
            'details': self.details,
            'model_version': self.model_version,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }


class AuditLog(db.Model):
    """Audit log for security tracking and bug tracking"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    # Log details
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)  # user, transaction, etc.
    resource_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Request information
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    method = db.Column(db.String(10), nullable=True)

    # Status
    status = db.Column(db.String(20), default='success')  # success, failure, error
    error_message = db.Column(db.Text, nullable=True)

    # Severity level for bug tracking
    severity = db.Column(db.String(20), default='info')  # debug, info, warning, error, critical

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'endpoint': self.endpoint,
            'method': self.method,
            'status': self.status,
            'error_message': self.error_message,
            'severity': self.severity,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TokenBlacklist(db.Model):
    """Blacklisted JWT tokens for logout functionality"""
    __tablename__ = 'token_blacklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)  # JWT ID
    token_type = db.Column(db.String(10), nullable=False)  # access or refresh
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<TokenBlacklist {self.jti}>'


class PasswordResetToken(db.Model):
    """Password reset tokens"""
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<PasswordResetToken {self.token[:10]}...>'
