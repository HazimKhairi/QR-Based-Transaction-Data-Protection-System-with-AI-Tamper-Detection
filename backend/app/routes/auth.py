"""
Authentication routes for QR-Based Transaction Data Protection System
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from marshmallow import ValidationError
from flasgger import swag_from
from datetime import datetime, timedelta

from app import db, limiter
from app.models import User, UserRole
from app.schemas import (
    UserRegistrationSchema, UserLoginSchema, OTPVerificationSchema,
    PasswordResetRequestSchema, PasswordResetSchema, ChangePasswordSchema
)
from app.services.auth_service import get_auth_service
from app.services.email_service import (
    send_password_reset_email,
    send_welcome_email,
)

auth_bp = Blueprint('auth', __name__)
auth_service = get_auth_service()


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Register a new user',
    'description': 'Create a new resident or admin account',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email', 'password', 'full_name'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string', 'minLength': 8},
                    'full_name': {'type': 'string'},
                    'phone_number': {'type': 'string'},
                    'unit_number': {'type': 'string'},
                    'community_name': {'type': 'string'},
                    'role': {'type': 'string', 'enum': ['resident', 'admin']}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'User registered successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'user': {'type': 'object'}
                }
            }
        },
        '400': {'description': 'Validation error'},
        '409': {'description': 'Email already registered'}
    }
})
def register():
    """Register a new user"""
    try:
        # Validate input
        schema = UserRegistrationSchema()
        data = schema.load(request.json)

        # Check if email already exists
        if User.query.filter_by(email=data['email'].lower()).first():
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 409

        # Create user
        user = User(
            email=data['email'].lower(),
            password_hash=auth_service.hash_password(data['password']),
            full_name=data['full_name'],
            phone_number=data.get('phone_number'),
            unit_number=data.get('unit_number'),
            community_name=data.get('community_name'),
            role=UserRole(data.get('role', 'resident'))
        )

        db.session.add(user)
        db.session.commit()

        # Welcome email (non-blocking; errors logged not raised)
        send_welcome_email(user.email, user.full_name, user.role.value)

        # Create audit log
        auth_service.create_audit_log(
            user_id=user.id,
            action='user_registered',
            resource_type='user',
            resource_id=user.id,
            description=f'New user registered: {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
@swag_from({
    'tags': ['Authentication'],
    'summary': 'User login',
    'description': 'Authenticate user and return JWT tokens. If 2FA is enabled, OTP code is required.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string'},
                    'otp_code': {'type': 'string', 'minLength': 6, 'maxLength': 6}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Login successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'access_token': {'type': 'string'},
                    'refresh_token': {'type': 'string'},
                    'user': {'type': 'object'}
                }
            }
        },
        '401': {'description': 'Invalid credentials or 2FA required'},
        '423': {'description': 'Account locked'}
    }
})
def login():
    """User login with optional 2FA"""
    try:
        # Validate input
        schema = UserLoginSchema()
        data = schema.load(request.json)

        # Find user
        user = User.query.filter_by(email=data['email'].lower()).first()

        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401

        # Check account lock
        is_locked, minutes_remaining = auth_service.check_account_lock(user)
        if is_locked:
            return jsonify({
                'success': False,
                'error': f'Account locked. Try again in {minutes_remaining} minutes.',
                'locked': True,
                'minutes_remaining': minutes_remaining
            }), 423

        # Verify password
        if not auth_service.verify_password(data['password'], user.password_hash):
            auth_service.record_login_attempt(user, False, request.remote_addr)
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401

        # Check 2FA if enabled
        if user.is_2fa_enabled:
            otp_code = data.get('otp_code')
            if not otp_code:
                return jsonify({
                    'success': False,
                    'error': '2FA code required',
                    'requires_2fa': True
                }), 401

            if not auth_service.verify_user_otp(user, otp_code):
                auth_service.record_login_attempt(user, False, request.remote_addr)
                return jsonify({
                    'success': False,
                    'error': 'Invalid 2FA code'
                }), 401

        # Check if account is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Account is deactivated'
            }), 401

        # Record successful login
        auth_service.record_login_attempt(user, True, request.remote_addr)

        # Generate tokens
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'email': user.email,
                'role': user.role.value
            }
        )
        refresh_token = create_refresh_token(identity=str(user.id))

        # Create audit log
        auth_service.create_audit_log(
            user_id=user.id,
            action='user_login',
            resource_type='user',
            resource_id=user.id,
            description=f'User logged in: {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Refresh access token',
    'description': 'Get a new access token using refresh token',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'Token refreshed',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'access_token': {'type': 'string'}
                }
            }
        },
        '401': {'description': 'Invalid or expired refresh token'}
    }
})
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User not found or inactive'
            }), 401

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'email': user.email,
                'role': user.role.value
            }
        )

        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'summary': 'User logout',
    'description': 'Logout and blacklist current token',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {'description': 'Logged out successfully'}
    }
})
def logout():
    """Logout user and blacklist token"""
    try:
        jwt_data = get_jwt()
        jti = jwt_data['jti']
        user_id = get_jwt_identity()

        # Calculate expiration
        exp_timestamp = jwt_data['exp']
        expires_at = datetime.fromtimestamp(exp_timestamp)

        auth_service.blacklist_token(jti, 'access', user_id, expires_at)

        # Create audit log
        auth_service.create_audit_log(
            user_id=user_id,
            action='user_logout',
            resource_type='user',
            resource_id=user_id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/logout-all', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Logout from all devices',
    'description': 'Invalidate all tokens issued before now for the current user',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {'description': 'All sessions revoked'}
    }
})
def logout_all():
    """Logout from every device by setting the user's tokens_valid_after cutoff to now."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        user.tokens_valid_after = datetime.utcnow()
        db.session.commit()

        auth_service.create_audit_log(
            user_id=user.id,
            action='logout_all_devices',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            severity='warning',
        )

        return jsonify({
            'success': True,
            'message': 'All sessions revoked. You will need to log in again on every device.'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Get user profile',
    'description': 'Get current authenticated user profile',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'User profile',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'user': {'type': 'object'}
                }
            }
        }
    }
})
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        return jsonify({
            'success': True,
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Update user profile',
    'description': 'Update current user profile information',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'full_name': {'type': 'string'},
                    'phone_number': {'type': 'string'},
                    'unit_number': {'type': 'string'},
                    'community_name': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Profile updated'}
    }
})
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.json

        # Update allowed fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone_number' in data:
            user.phone_number = data['phone_number']
        if 'unit_number' in data:
            user.unit_number = data['unit_number']
        if 'community_name' in data:
            user.community_name = data['community_name']
        if 'notify_email_enabled' in data:
            user.notify_email_enabled = bool(data['notify_email_enabled'])
        if 'notify_fraud_alerts_enabled' in data:
            user.notify_fraud_alerts_enabled = bool(data['notify_fraud_alerts_enabled'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@auth_bp.route('/2fa/setup', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Two-Factor Authentication'],
    'summary': 'Setup 2FA',
    'description': 'Initialize 2FA setup and get provisioning URI',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': '2FA setup information',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'secret': {'type': 'string'},
                    'provisioning_uri': {'type': 'string'}
                }
            }
        }
    }
})
def setup_2fa():
    """Setup 2FA for user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if user.is_2fa_enabled:
            return jsonify({
                'success': False,
                'error': '2FA is already enabled'
            }), 400

        result = auth_service.setup_2fa(user)

        return jsonify({
            'success': True,
            **result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/2fa/verify', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Two-Factor Authentication'],
    'summary': 'Verify 2FA setup',
    'description': 'Verify and enable 2FA using OTP code',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['otp_code'],
                'properties': {
                    'otp_code': {'type': 'string', 'minLength': 6, 'maxLength': 6}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': '2FA enabled successfully'},
        '400': {'description': 'Invalid OTP code'}
    }
})
def verify_2fa():
    """Verify and enable 2FA"""
    try:
        schema = OTPVerificationSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if auth_service.verify_2fa_setup(user, data['otp_code']):
            # Create audit log
            auth_service.create_audit_log(
                user_id=user.id,
                action='2fa_enabled',
                resource_type='user',
                resource_id=user.id,
                ip_address=request.remote_addr,
                severity='warning'
            )

            return jsonify({
                'success': True,
                'message': '2FA enabled successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid OTP code'
            }), 400

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/2fa/disable', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Two-Factor Authentication'],
    'summary': 'Disable 2FA',
    'description': 'Disable 2FA (requires current OTP code)',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['otp_code'],
                'properties': {
                    'otp_code': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': '2FA disabled'},
        '400': {'description': 'Invalid OTP code'}
    }
})
def disable_2fa():
    """Disable 2FA"""
    try:
        schema = OTPVerificationSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if auth_service.disable_2fa(user, data['otp_code']):
            # Create audit log
            auth_service.create_audit_log(
                user_id=user.id,
                action='2fa_disabled',
                resource_type='user',
                resource_id=user.id,
                ip_address=request.remote_addr,
                severity='warning'
            )

            return jsonify({
                'success': True,
                'message': '2FA disabled'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid OTP code'
            }), 400

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/password/reset-request', methods=['POST'])
@limiter.limit("3 per minute")
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Request password reset',
    'description': 'Request a password reset token',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Reset token generated (in production, sent via email)'}
    }
})
def request_password_reset():
    """Request password reset"""
    try:
        schema = PasswordResetRequestSchema()
        data = schema.load(request.json)

        user = User.query.filter_by(email=data['email'].lower()).first()

        # Always return the same response to prevent email enumeration
        if user:
            token = auth_service.generate_password_reset_token(user)
            send_password_reset_email(user.email, user.full_name, token)

        return jsonify({
            'success': True,
            'message': 'Password reset instructions sent if email exists'
        }), 200

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/password/reset', methods=['POST'])
@limiter.limit("5 per minute")
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Reset password',
    'description': 'Reset password using reset token',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['token', 'new_password'],
                'properties': {
                    'token': {'type': 'string'},
                    'new_password': {'type': 'string', 'minLength': 8}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Password reset successful'},
        '400': {'description': 'Invalid or expired token'}
    }
})
def reset_password():
    """Reset password with token"""
    try:
        schema = PasswordResetSchema()
        data = schema.load(request.json)

        if auth_service.reset_password(data['token'], data['new_password']):
            return jsonify({
                'success': True,
                'message': 'Password reset successful'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired reset token'
            }), 400

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/password/change', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Change password',
    'description': 'Change password for authenticated user',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['current_password', 'new_password'],
                'properties': {
                    'current_password': {'type': 'string'},
                    'new_password': {'type': 'string', 'minLength': 8}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Password changed'},
        '401': {'description': 'Current password incorrect'}
    }
})
def change_password():
    """Change password for authenticated user"""
    try:
        schema = ChangePasswordSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Verify current password
        if not auth_service.verify_password(data['current_password'], user.password_hash):
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 401

        # If 2FA is enabled, require an OTP from the authenticator app
        if user.is_2fa_enabled:
            otp_code = (request.json or {}).get('otp_code')
            if not otp_code:
                return jsonify({
                    'success': False,
                    'error': '2FA code required',
                    'requires_2fa': True
                }), 400
            if not auth_service.verify_user_otp(user, otp_code):
                return jsonify({
                    'success': False,
                    'error': 'Invalid 2FA code'
                }), 401

        # Update password
        user.password_hash = auth_service.hash_password(data['new_password'])
        db.session.commit()

        # Create audit log
        auth_service.create_audit_log(
            user_id=user.id,
            action='password_changed',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            severity='warning'
        )

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
