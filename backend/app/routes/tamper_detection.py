"""
Tamper Detection routes for QR-Based Transaction Data Protection System
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from flasgger import swag_from
import json

from app import db, limiter
from app.models import Transaction, TamperDetectionResult, User
from app.schemas import TamperAnalysisSchema
from app.services.tamper_detection import get_tamper_detection_service
from app.services.auth_service import get_auth_service
from app.services.encryption import get_encryption_service

tamper_bp = Blueprint('tamper', __name__)
tamper_service = get_tamper_detection_service()
auth_service = get_auth_service()
encryption_service = get_encryption_service()


@tamper_bp.route('/analyze', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Analyze transaction for tampering',
    'description': 'Run AI-based tamper detection analysis on transaction data',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'transaction_id': {'type': 'integer'},
                    'qr_code_data': {'type': 'string'},
                    'amount': {'type': 'number'},
                    'user_id': {'type': 'integer'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Analysis results',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'anomaly_score': {'type': 'number'},
                    'is_anomaly': {'type': 'boolean'},
                    'confidence': {'type': 'number'},
                    'detection_type': {'type': 'string'},
                    'details': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Validation error'}
    }
})
def analyze_transaction():
    """Analyze transaction for potential tampering"""
    try:
        schema = TamperAnalysisSchema()
        data = schema.load(request.json)

        user_id = get_jwt_identity()
        target_user_id = data.get('user_id', user_id)

        # Build transaction data for analysis
        transaction_data = {}
        historical_data = []

        # If transaction_id provided, get from database
        if data.get('transaction_id'):
            transaction = Transaction.query.get(data['transaction_id'])
            if transaction:
                transaction_data = {
                    'amount': transaction.amount,
                    'created_at': transaction.created_at,
                    'qr_scan_attempts': 1
                }
                target_user_id = transaction.user_id

        # If QR code data provided, decrypt and analyze
        if data.get('qr_code_data'):
            try:
                payload = encryption_service.decrypt_qr_payload(data['qr_code_data'])
                transaction_data['amount'] = payload.get('amount', 0)
                transaction_data['created_at'] = payload.get('generated_at')
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Failed to decrypt QR code data'
                }), 400

        # If amount provided directly
        if data.get('amount'):
            transaction_data['amount'] = data['amount']

        if not transaction_data.get('amount'):
            return jsonify({
                'success': False,
                'error': 'No transaction data to analyze'
            }), 400

        # Get historical data for context
        historical_transactions = Transaction.query.filter_by(
            user_id=target_user_id
        ).order_by(Transaction.created_at.desc()).limit(50).all()

        historical_data = [
            {'amount': t.amount, 'created_at': t.created_at}
            for t in historical_transactions
        ]

        # Run detection
        result = tamper_service.detect_anomaly(transaction_data, historical_data)

        # Log the analysis
        auth_service.create_audit_log(
            user_id=user_id,
            action='tamper_analysis',
            resource_type='transaction',
            resource_id=data.get('transaction_id'),
            description=f"Tamper analysis: anomaly={result['is_anomaly']}, score={result['anomaly_score']:.4f}",
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            **result
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


@tamper_bp.route('/verify-qr-integrity', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Verify QR code integrity',
    'description': 'Check if QR code has been tampered with by comparing hashes',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['qr_code_data', 'original_hash'],
                'properties': {
                    'qr_code_data': {'type': 'string'},
                    'original_hash': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Integrity check result',
            'schema': {
                'type': 'object',
                'properties': {
                    'is_valid': {'type': 'boolean'},
                    'tampered': {'type': 'boolean'}
                }
            }
        }
    }
})
def verify_qr_integrity():
    """Verify QR code integrity"""
    try:
        data = request.json

        if not data.get('qr_code_data') or not data.get('original_hash'):
            return jsonify({
                'success': False,
                'error': 'qr_code_data and original_hash are required'
            }), 400

        result = tamper_service.analyze_qr_integrity(
            qr_data=data['qr_code_data'],
            original_hash=data['original_hash']
        )

        user_id = get_jwt_identity()

        # Log if tampering detected
        if result.get('tampered'):
            auth_service.create_audit_log(
                user_id=user_id,
                action='qr_tampering_detected',
                resource_type='qr_code',
                description='QR code integrity check failed - tampering detected',
                ip_address=request.remote_addr,
                severity='warning'
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


@tamper_bp.route('/batch-analyze', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Batch analyze transactions',
    'description': 'Analyze multiple transactions for anomalies',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['transaction_ids'],
                'properties': {
                    'transaction_ids': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                        'maxItems': 50
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Batch analysis results',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'results': {'type': 'array'},
                    'summary': {'type': 'object'}
                }
            }
        }
    }
})
def batch_analyze():
    """Batch analyze multiple transactions"""
    try:
        data = request.json
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({
                'success': False,
                'error': 'transaction_ids is required'
            }), 400

        if len(transaction_ids) > 50:
            return jsonify({
                'success': False,
                'error': 'Maximum 50 transactions per batch'
            }), 400

        results = []
        anomaly_count = 0

        for tx_id in transaction_ids:
            transaction = Transaction.query.get(tx_id)

            if not transaction:
                results.append({
                    'transaction_id': tx_id,
                    'error': 'Transaction not found'
                })
                continue

            # Get historical data
            historical = Transaction.query.filter_by(
                user_id=transaction.user_id
            ).filter(
                Transaction.id != tx_id
            ).order_by(Transaction.created_at.desc()).limit(50).all()

            historical_data = [
                {'amount': t.amount, 'created_at': t.created_at}
                for t in historical
            ]

            transaction_data = {
                'amount': transaction.amount,
                'created_at': transaction.created_at,
                'qr_scan_attempts': 1
            }

            # Run detection
            detection_result = tamper_service.detect_anomaly(
                transaction_data, historical_data
            )

            # Update transaction with score
            transaction.tamper_score = detection_result['anomaly_score']

            if detection_result['is_anomaly']:
                anomaly_count += 1
                transaction.is_flagged = True
                transaction.flag_reason = detection_result.get('details', 'Batch analysis anomaly')

                # Store detection result
                detection_record = TamperDetectionResult(
                    transaction_id=tx_id,
                    anomaly_score=detection_result['anomaly_score'],
                    is_anomaly=detection_result['is_anomaly'],
                    confidence=detection_result.get('confidence'),
                    detection_type=detection_result.get('detection_type'),
                    details=detection_result.get('details'),
                    features_analyzed=json.dumps(detection_result.get('features_analyzed')),
                    model_version=detection_result.get('model_version', '1.0.0')
                )
                db.session.add(detection_record)

            results.append({
                'transaction_id': tx_id,
                'transaction_ref': transaction.transaction_ref,
                'anomaly_score': detection_result['anomaly_score'],
                'is_anomaly': detection_result['is_anomaly'],
                'confidence': detection_result.get('confidence'),
                'detection_type': detection_result.get('detection_type')
            })

        db.session.commit()

        user_id = get_jwt_identity()
        auth_service.create_audit_log(
            user_id=user_id,
            action='batch_tamper_analysis',
            description=f'Batch analysis of {len(transaction_ids)} transactions, {anomaly_count} anomalies found',
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total_analyzed': len(results),
                'anomalies_found': anomaly_count,
                'anomaly_rate': (anomaly_count / len(results) * 100) if results else 0
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tamper_bp.route('/model/status', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Get AI model status',
    'description': 'Get information about the tamper detection AI model',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'Model status',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'model_loaded': {'type': 'boolean'},
                    'model_version': {'type': 'string'},
                    'feature_names': {'type': 'array'}
                }
            }
        }
    }
})
def get_model_status():
    """Get AI model status"""
    try:
        return jsonify({
            'success': True,
            'model_loaded': tamper_service.model is not None,
            'model_version': tamper_service.model_version,
            'feature_names': tamper_service.feature_names,
            'scaler_loaded': tamper_service.scaler is not None
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tamper_bp.route('/model/train', methods=['POST'])
@jwt_required()
@limiter.limit("1 per hour")
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Retrain AI model',
    'description': 'Retrain the tamper detection model (admin only)',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'use_historical_data': {'type': 'boolean', 'default': True},
                    'contamination': {'type': 'number', 'default': 0.1}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Model trained successfully'},
        '403': {'description': 'Admin access required'}
    }
})
def train_model():
    """Retrain the AI model"""
    try:
        from flask_jwt_extended import get_jwt

        jwt_data = get_jwt()
        role = jwt_data.get('role', 'resident')

        if role not in ['admin', 'super_admin']:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403

        data = request.json or {}
        use_historical = data.get('use_historical_data', True)
        contamination = data.get('contamination', 0.1)

        training_data = None

        if use_historical:
            # Get historical transactions for training
            transactions = Transaction.query.order_by(
                Transaction.created_at.desc()
            ).limit(1000).all()

            if len(transactions) >= 100:
                import numpy as np

                # Extract features from historical data
                features = []
                for t in transactions:
                    hour = t.created_at.hour if t.created_at else 12
                    day = t.created_at.weekday() if t.created_at else 0

                    features.append([
                        t.amount,
                        hour,
                        day,
                        3,  # Default frequency
                        0,  # Default deviation
                        4,  # Default time since last
                        1   # Default scan attempts
                    ])

                training_data = np.array(features)

        # Train model
        success = tamper_service.train_model(
            X=training_data,
            contamination=contamination
        )

        user_id = get_jwt_identity()
        auth_service.create_audit_log(
            user_id=user_id,
            action='ai_model_trained',
            description=f'AI model retrained, success={success}',
            ip_address=request.remote_addr,
            severity='warning'
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Model trained successfully',
                'model_version': tamper_service.model_version
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Model training failed'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tamper_bp.route('/results/<int:transaction_id>', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Tamper Detection'],
    'summary': 'Get detection results for transaction',
    'description': 'Get all tamper detection results for a specific transaction',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'transaction_id', 'in': 'path', 'required': True, 'type': 'integer'}
    ],
    'responses': {
        '200': {
            'description': 'Detection results',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'results': {'type': 'array'}
                }
            }
        }
    }
})
def get_detection_results(transaction_id):
    """Get tamper detection results for a transaction"""
    try:
        results = TamperDetectionResult.query.filter_by(
            transaction_id=transaction_id
        ).order_by(TamperDetectionResult.detected_at.desc()).all()

        return jsonify({
            'success': True,
            'results': [r.to_dict() for r in results]
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
