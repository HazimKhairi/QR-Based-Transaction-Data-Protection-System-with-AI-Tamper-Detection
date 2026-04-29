"""
Transaction routes for QR-Based Transaction Data Protection System
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from flasgger import swag_from

from app import db, limiter
from app.models import Transaction, TransactionStatus, User
from app.schemas import (
    TransactionCreateSchema, TransactionProcessSchema,
    TransactionVerifySchema, PaginationSchema
)
from app.services.qr_service import get_qr_service
from app.services.auth_service import get_auth_service
from app.services.tamper_detection import get_tamper_detection_service

transactions_bp = Blueprint('transactions', __name__)
qr_service = get_qr_service()
auth_service = get_auth_service()
tamper_service = get_tamper_detection_service()


@transactions_bp.route('/generate-qr', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Generate QR code for payment',
    'description': 'Create a new transaction and generate encrypted QR code',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['amount'],
                'properties': {
                    'amount': {'type': 'number', 'minimum': 0.01, 'maximum': 100000},
                    'description': {'type': 'string', 'maxLength': 255},
                    'transaction_type': {
                        'type': 'string',
                        'enum': ['maintenance_fee', 'security_payment', 'event_fee',
                                 'pasar_malam', 'facility_booking', 'other']
                    },
                    'recipient_id': {'type': 'integer'},
                    'expires_in_minutes': {'type': 'integer', 'minimum': 5, 'maximum': 1440}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'QR code generated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'transaction_ref': {'type': 'string'},
                    'qr_code_data': {'type': 'string'},
                    'qr_code_hash': {'type': 'string'},
                    'expires_at': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Validation error'}
    }
})
def generate_qr():
    """Generate QR code for a new transaction"""
    try:
        schema = TransactionCreateSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Verify recipient if specified
        if data.get('recipient_id'):
            recipient = User.query.get(data['recipient_id'])
            if not recipient:
                return jsonify({
                    'success': False,
                    'error': 'Recipient not found'
                }), 404

        result = qr_service.create_qr_transaction(
            user_id=user_id,
            amount=data['amount'],
            description=data.get('description'),
            transaction_type=data.get('transaction_type', 'other'),
            recipient_id=data.get('recipient_id'),
            expires_in_minutes=data.get('expires_in_minutes', 30),
            ip_address=request.remote_addr,
            device_info=request.headers.get('User-Agent')
        )

        # Create audit log
        auth_service.create_audit_log(
            user_id=user_id,
            action='qr_generated',
            resource_type='transaction',
            resource_id=result['transaction_id'],
            description=f"QR generated for RM{data['amount']:.2f}",
            ip_address=request.remote_addr
        )

        return jsonify(result), 201

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


@transactions_bp.route('/verify-qr', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Verify QR code integrity',
    'description': 'Verify a QR code for tampering and validity',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['qr_code_data'],
                'properties': {
                    'qr_code_data': {'type': 'string'},
                    'qr_code_hash': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Verification result',
            'schema': {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'payload': {'type': 'object'},
                    'transaction': {'type': 'object'}
                }
            }
        }
    }
})
def verify_qr():
    """Verify QR code integrity"""
    try:
        schema = TransactionVerifySchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()

        result = qr_service.verify_qr_code(
            qr_code_data=data['qr_code_data'],
            expected_hash=data.get('qr_code_hash')
        )

        # Log verification attempt
        auth_service.create_audit_log(
            user_id=user_id,
            action='qr_verified',
            resource_type='transaction',
            description=f"QR verification: {'valid' if result.get('valid') else 'invalid'}",
            ip_address=request.remote_addr
        )

        if result.get('tampered'):
            # Log security warning
            auth_service.create_audit_log(
                user_id=user_id,
                action='qr_tamper_detected',
                resource_type='transaction',
                description="Tampered QR code detected",
                ip_address=request.remote_addr,
                severity='warning'
            )

        return jsonify(result), 200

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


@transactions_bp.route('/process', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Process QR transaction',
    'description': 'Process and complete a QR-based payment (requires 2FA)',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['qr_code_data', 'otp_code'],
                'properties': {
                    'qr_code_data': {'type': 'string'},
                    'otp_code': {'type': 'string', 'minLength': 6, 'maxLength': 6},
                    'device_info': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Transaction processed',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'transaction_ref': {'type': 'string'},
                    'amount': {'type': 'number'},
                    'completed_at': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Invalid QR or OTP'},
        '403': {'description': 'Transaction flagged'}
    }
})
def process_transaction():
    """Process a QR-based transaction"""
    try:
        schema = TransactionProcessSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Verify 2FA
        if user.is_2fa_enabled:
            if not auth_service.verify_user_otp(user, data['otp_code']):
                return jsonify({
                    'success': False,
                    'error': 'Invalid 2FA code'
                }), 401
        else:
            # If 2FA not enabled, still require a placeholder code for security
            # In production, you might enforce 2FA for all transactions
            pass

        # First verify the QR code
        verification = qr_service.verify_qr_code(data['qr_code_data'])

        if not verification.get('valid'):
            return jsonify({
                'success': False,
                'error': verification.get('error', 'Invalid QR code'),
                'verification': verification
            }), 400

        # Run tamper detection on the transaction
        transaction_data = {
            'amount': verification['payload'].get('amount'),
            'created_at': verification['payload'].get('generated_at'),
            'qr_scan_attempts': 1
        }

        # Get user's historical transactions for context
        historical = Transaction.query.filter_by(user_id=user_id).order_by(
            Transaction.created_at.desc()
        ).limit(50).all()

        historical_data = [
            {'amount': t.amount, 'created_at': t.created_at}
            for t in historical
        ]

        detection_result = tamper_service.detect_anomaly(
            transaction_data, historical_data
        )

        # Get the transaction
        transaction = Transaction.query.filter_by(
            transaction_ref=verification['payload']['transaction_ref']
        ).first()

        if transaction:
            # Store tamper detection score
            transaction.tamper_score = detection_result['anomaly_score']

            # If anomaly detected, flag but still process (configurable)
            if detection_result['is_anomaly']:
                transaction.is_flagged = True
                transaction.flag_reason = detection_result.get('details', 'AI detected anomaly')

                # Log security warning
                auth_service.create_audit_log(
                    user_id=user_id,
                    action='transaction_anomaly_detected',
                    resource_type='transaction',
                    resource_id=transaction.id,
                    description=detection_result.get('details'),
                    ip_address=request.remote_addr,
                    severity='warning'
                )

                # Store detection result
                from app.models import TamperDetectionResult
                import json
                detection_record = TamperDetectionResult(
                    transaction_id=transaction.id,
                    anomaly_score=detection_result['anomaly_score'],
                    is_anomaly=detection_result['is_anomaly'],
                    confidence=detection_result.get('confidence'),
                    detection_type=detection_result.get('detection_type'),
                    details=detection_result.get('details'),
                    features_analyzed=json.dumps(detection_result.get('features_analyzed')),
                    model_version=detection_result.get('model_version', '1.0.0')
                )
                db.session.add(detection_record)

        # Process the transaction
        result = qr_service.process_transaction(
            qr_code_data=data['qr_code_data'],
            processor_user_id=user_id,
            ip_address=request.remote_addr,
            device_info=data.get('device_info', request.headers.get('User-Agent'))
        )

        if result['success']:
            # Create audit log
            auth_service.create_audit_log(
                user_id=user_id,
                action='transaction_completed',
                resource_type='transaction',
                resource_id=transaction.id if transaction else None,
                description=f"Transaction completed: {result['transaction_ref']}",
                ip_address=request.remote_addr
            )

            # Add tamper detection info to response
            result['tamper_detection'] = {
                'analyzed': True,
                'anomaly_score': detection_result['anomaly_score'],
                'is_anomaly': detection_result['is_anomaly']
            }

        return jsonify(result), 200 if result['success'] else 400

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


@transactions_bp.route('/cancel/<transaction_ref>', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Cancel transaction',
    'description': 'Cancel a pending transaction',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'transaction_ref',
            'in': 'path',
            'required': True,
            'type': 'string'
        },
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'reason': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Transaction cancelled'},
        '400': {'description': 'Cannot cancel transaction'},
        '403': {'description': 'Not authorized'}
    }
})
def cancel_transaction(transaction_ref):
    """Cancel a pending transaction"""
    try:
        user_id = get_jwt_identity()
        reason = request.json.get('reason') if request.json else None

        result = qr_service.cancel_transaction(
            transaction_ref=transaction_ref,
            user_id=user_id,
            reason=reason
        )

        if result['success']:
            auth_service.create_audit_log(
                user_id=user_id,
                action='transaction_cancelled',
                resource_type='transaction',
                description=f"Cancelled: {transaction_ref}",
                ip_address=request.remote_addr
            )

        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@transactions_bp.route('/history', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Get transaction history',
    'description': 'Get paginated transaction history for current user',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'page', 'in': 'query', 'type': 'integer', 'default': 1},
        {'name': 'per_page', 'in': 'query', 'type': 'integer', 'default': 20},
        {'name': 'status', 'in': 'query', 'type': 'string'},
        {'name': 'include_received', 'in': 'query', 'type': 'boolean', 'default': True}
    ],
    'responses': {
        '200': {
            'description': 'Transaction list',
            'schema': {
                'type': 'object',
                'properties': {
                    'transactions': {'type': 'array'},
                    'total': {'type': 'integer'},
                    'pages': {'type': 'integer'},
                    'current_page': {'type': 'integer'}
                }
            }
        }
    }
})
def get_history():
    """Get user's transaction history"""
    try:
        user_id = get_jwt_identity()

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        include_received = request.args.get('include_received', 'true').lower() == 'true'

        result = qr_service.get_user_transactions(
            user_id=user_id,
            page=page,
            per_page=per_page,
            status=status,
            include_received=include_received
        )

        return jsonify({
            'success': True,
            **result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@transactions_bp.route('/<transaction_ref>', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Get transaction details',
    'description': 'Get details of a specific transaction',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'transaction_ref', 'in': 'path', 'required': True, 'type': 'string'}
    ],
    'responses': {
        '200': {
            'description': 'Transaction details',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'transaction': {'type': 'object'}
                }
            }
        },
        '404': {'description': 'Transaction not found'},
        '403': {'description': 'Not authorized'}
    }
})
def get_transaction(transaction_ref):
    """Get transaction details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        transaction = Transaction.query.filter_by(
            transaction_ref=transaction_ref
        ).first()

        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404

        # Check authorization (user is creator, recipient, or admin)
        is_authorized = (
            transaction.user_id == user_id or
            transaction.recipient_id == user_id or
            user.role.value in ['admin', 'super_admin']
        )

        if not is_authorized:
            return jsonify({
                'success': False,
                'error': 'Not authorized to view this transaction'
            }), 403

        # Get tamper detection results if any
        detection_results = [r.to_dict() for r in transaction.tamper_results]

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(include_sensitive=True),
            'tamper_detection_results': detection_results
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@transactions_bp.route('/statistics', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Transactions'],
    'summary': 'Get transaction statistics',
    'description': 'Get transaction statistics for current user',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'days', 'in': 'query', 'type': 'integer', 'default': 30}
    ],
    'responses': {
        '200': {
            'description': 'Statistics',
            'schema': {
                'type': 'object',
                'properties': {
                    'period_days': {'type': 'integer'},
                    'total_transactions': {'type': 'integer'},
                    'completed_transactions': {'type': 'integer'},
                    'total_amount': {'type': 'number'}
                }
            }
        }
    }
})
def get_statistics():
    """Get user's transaction statistics"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)

        stats = qr_service.get_transaction_statistics(
            user_id=user_id,
            days=days
        )

        return jsonify({
            'success': True,
            **stats
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# DEMO ENDPOINTS (No Authentication Required)
# These endpoints are for demonstration purposes only
# =============================================================================

@transactions_bp.route('/demo/generate-qr', methods=['POST'])
@limiter.limit("30 per minute")
def demo_generate_qr():
    """Generate QR code for demo (no auth required)"""
    try:
        data = request.json or {}
        amount = data.get('amount', 25.50)
        description = data.get('description', 'Demo Payment')
        transaction_type = data.get('transaction_type', 'event_fee')
        expires_in_minutes = data.get('expires_in_minutes', 30)

        # Use demo user (first admin user or create anonymous demo)
        demo_user = User.query.filter_by(email='admin@qrtransaction.my').first()
        if not demo_user:
            demo_user = User.query.first()
        
        if not demo_user:
            return jsonify({
                'success': False,
                'error': 'No users available. Please seed the database first.'
            }), 400

        result = qr_service.create_qr_transaction(
            user_id=demo_user.id,
            amount=amount,
            description=description,
            transaction_type=transaction_type,
            expires_in_minutes=expires_in_minutes,
            ip_address=request.remote_addr,
            device_info=request.headers.get('User-Agent')
        )

        return jsonify(result), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@transactions_bp.route('/demo/verify-qr', methods=['POST'])
@limiter.limit("60 per minute")
def demo_verify_qr():
    """Verify QR code for demo (no auth required)"""
    try:
        data = request.json or {}
        qr_code_data = data.get('qr_code_data')
        qr_code_hash = data.get('qr_code_hash')

        if not qr_code_data:
            return jsonify({
                'success': False,
                'error': 'qr_code_data is required'
            }), 400

        result = qr_service.verify_qr_code(
            qr_code_data=qr_code_data,
            expected_hash=qr_code_hash
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@transactions_bp.route('/demo/process', methods=['POST'])
@limiter.limit("20 per minute")
def demo_process_transaction():
    """Process transaction for demo (no auth required, simulated success)"""
    try:
        data = request.json or {}
        qr_code_data = data.get('qr_code_data')
        otp_code = data.get('otp_code', '123456')

        if not qr_code_data:
            return jsonify({
                'success': False,
                'error': 'qr_code_data is required'
            }), 400

        # Verify the QR code first
        verification = qr_service.verify_qr_code(qr_code_data)

        if not verification.get('valid'):
            return jsonify({
                'success': False,
                'error': verification.get('error', 'Invalid QR code'),
                'verification': verification
            }), 400

        # For demo, accept any 6-digit OTP
        if len(otp_code) != 6:
            return jsonify({
                'success': False,
                'error': 'Invalid OTP code. Please enter a 6-digit code.'
            }), 400

        # Use demo user to process
        demo_user = User.query.filter_by(email='admin@qrtransaction.my').first()
        if not demo_user:
            demo_user = User.query.first()

        # Run tamper detection
        transaction_data = {
            'amount': verification['payload'].get('amount'),
            'created_at': verification['payload'].get('generated_at'),
            'qr_scan_attempts': 1
        }

        detection_result = tamper_service.detect_anomaly(transaction_data, [])

        # Process the transaction
        result = qr_service.process_transaction(
            qr_code_data=qr_code_data,
            processor_user_id=demo_user.id if demo_user else None,
            ip_address=request.remote_addr,
            device_info=data.get('device_info', request.headers.get('User-Agent'))
        )

        if result['success']:
            result['tamper_detection'] = {
                'analyzed': True,
                'anomaly_score': detection_result['anomaly_score'],
                'is_anomaly': detection_result['is_anomaly']
            }

        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

