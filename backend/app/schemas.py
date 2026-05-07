"""
Marshmallow schemas for input validation and serialization
"""
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from app.models import UserRole, TransactionStatus, TransactionType
import re


class UserRegistrationSchema(Schema):
    """Schema for user registration"""
    email = fields.Email(required=True, error_messages={'required': 'Email is required'})
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    phone_number = fields.Str(validate=validate.Length(max=20))
    unit_number = fields.Str(validate=validate.Length(max=20))
    community_name = fields.Str(validate=validate.Length(max=100))
    role = fields.Str(validate=validate.OneOf(['resident', 'admin']))

    @validates('password')
    def validate_password(self, value):
        """Validate password strength"""
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', value):
            raise ValidationError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError('Password must contain at least one special character')

    @validates('phone_number')
    def validate_phone(self, value):
        """Validate Malaysian phone number format"""
        if value:
            # Remove spaces and dashes
            cleaned = re.sub(r'[\s-]', '', value)
            # Malaysian phone format: +60xxxxxxxxx or 0xxxxxxxxx
            if not re.match(r'^(\+60|0)[0-9]{9,10}$', cleaned):
                raise ValidationError('Invalid Malaysian phone number format')


class UserLoginSchema(Schema):
    """Schema for user login"""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    otp_code = fields.Str(validate=validate.Length(equal=6))


class OTPVerificationSchema(Schema):
    """Schema for OTP verification"""
    otp_code = fields.Str(required=True, validate=validate.Length(equal=6))


class PasswordResetRequestSchema(Schema):
    """Schema for password reset request"""
    email = fields.Email(required=True)


class PasswordResetSchema(Schema):
    """Schema for password reset"""
    token = fields.Str(required=True)
    new_password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))

    @validates('new_password')
    def validate_password(self, value):
        """Validate password strength"""
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', value):
            raise ValidationError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError('Password must contain at least one special character')


class ChangePasswordSchema(Schema):
    """Schema for changing password"""
    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    otp_code = fields.Str(required=False, load_only=True, validate=validate.Length(min=6, max=6))

    @validates('new_password')
    def validate_password(self, value):
        """Validate password strength"""
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', value):
            raise ValidationError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError('Password must contain at least one special character')


class TransactionCreateSchema(Schema):
    """Schema for creating a transaction"""
    amount = fields.Float(required=True, validate=validate.Range(min=0.01, max=100000))
    currency = fields.Str(validate=validate.OneOf(['MYR']), load_default='MYR')
    description = fields.Str(validate=validate.Length(max=255))
    transaction_type = fields.Str(
        validate=validate.OneOf([t.value for t in TransactionType]),
        load_default='other'
    )
    recipient_id = fields.Int()
    expires_in_minutes = fields.Int(validate=validate.Range(min=5, max=1440), load_default=30)


class TransactionProcessSchema(Schema):
    """Schema for processing a transaction"""
    qr_code_data = fields.Str(required=True)
    otp_code = fields.Str(required=True, validate=validate.Length(equal=6))
    device_info = fields.Str(validate=validate.Length(max=255))


class TransactionVerifySchema(Schema):
    """Schema for verifying QR code integrity"""
    qr_code_data = fields.Str(required=True)
    qr_code_hash = fields.Str(validate=validate.Length(equal=64))


class TamperAnalysisSchema(Schema):
    """Schema for tamper detection analysis"""
    transaction_id = fields.Int()
    qr_code_data = fields.Str()
    amount = fields.Float()
    user_id = fields.Int()

    @post_load
    def check_required(self, data, **kwargs):
        """Ensure at least one field is provided"""
        if not any([data.get('transaction_id'), data.get('qr_code_data'),
                    data.get('amount'), data.get('user_id')]):
            raise ValidationError('At least one analysis parameter is required')
        return data


class AdminUserUpdateSchema(Schema):
    """Schema for admin user updates"""
    is_active = fields.Bool()
    is_verified = fields.Bool()
    role = fields.Str(validate=validate.OneOf([r.value for r in UserRole]))
    failed_login_attempts = fields.Int(validate=validate.Range(min=0))


class AdminTransactionUpdateSchema(Schema):
    """Schema for admin transaction updates"""
    status = fields.Str(validate=validate.OneOf([s.value for s in TransactionStatus]))
    is_flagged = fields.Bool()
    flag_reason = fields.Str(validate=validate.Length(max=255))


class ReportQuerySchema(Schema):
    """Schema for report generation queries"""
    start_date = fields.DateTime(format='%Y-%m-%d')
    end_date = fields.DateTime(format='%Y-%m-%d')
    status = fields.Str(validate=validate.OneOf([s.value for s in TransactionStatus]))
    transaction_type = fields.Str(validate=validate.OneOf([t.value for t in TransactionType]))
    format = fields.Str(validate=validate.OneOf(['json', 'csv']), load_default='json')
    include_flagged_only = fields.Bool(load_default=False)


class PaginationSchema(Schema):
    """Schema for pagination parameters"""
    page = fields.Int(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Int(validate=validate.Range(min=1, max=100), load_default=20)
    sort_by = fields.Str()
    sort_order = fields.Str(validate=validate.OneOf(['asc', 'desc']), load_default='desc')


class UserSchema(Schema):
    """Schema for user output"""
    id = fields.Int(dump_only=True)
    email = fields.Email()
    full_name = fields.Str()
    phone_number = fields.Str()
    unit_number = fields.Str()
    community_name = fields.Str()
    role = fields.Str()
    is_2fa_enabled = fields.Bool()
    is_active = fields.Bool()
    is_verified = fields.Bool()
    created_at = fields.DateTime()
    last_login = fields.DateTime()


class TransactionSchema(Schema):
    """Schema for transaction output"""
    id = fields.Int(dump_only=True)
    transaction_ref = fields.Str()
    user_id = fields.Int()
    recipient_id = fields.Int()
    amount = fields.Float()
    currency = fields.Str()
    description = fields.Str()
    transaction_type = fields.Str()
    status = fields.Str()
    is_verified = fields.Bool()
    is_flagged = fields.Bool()
    flag_reason = fields.Str()
    tamper_score = fields.Float()
    created_at = fields.DateTime()
    completed_at = fields.DateTime()
    qr_expires_at = fields.DateTime()


class TamperDetectionResultSchema(Schema):
    """Schema for tamper detection result output"""
    id = fields.Int(dump_only=True)
    transaction_id = fields.Int()
    anomaly_score = fields.Float()
    is_anomaly = fields.Bool()
    confidence = fields.Float()
    detection_type = fields.Str()
    details = fields.Str()
    model_version = fields.Str()
    detected_at = fields.DateTime()


class AuditLogSchema(Schema):
    """Schema for audit log output"""
    id = fields.Int(dump_only=True)
    user_id = fields.Int()
    action = fields.Str()
    resource_type = fields.Str()
    resource_id = fields.Int()
    description = fields.Str()
    ip_address = fields.Str()
    endpoint = fields.Str()
    method = fields.Str()
    status = fields.Str()
    error_message = fields.Str()
    severity = fields.Str()
    created_at = fields.DateTime()
