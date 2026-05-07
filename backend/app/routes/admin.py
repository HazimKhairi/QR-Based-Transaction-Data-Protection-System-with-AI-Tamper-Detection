"""
Admin routes for QR-Based Transaction Data Protection System
"""
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError
from flasgger import swag_from
from functools import wraps

from app import db, limiter
from app.models import (
    User, UserRole, Transaction, TransactionStatus, TransactionType,
    AuditLog, TamperDetectionResult
)
from app.schemas import (
    AdminUserUpdateSchema, AdminTransactionUpdateSchema,
    ReportQuerySchema, PaginationSchema
)
from app.services.auth_service import get_auth_service
from app.services.qr_service import get_qr_service
from app.services.email_service import send_email

admin_bp = Blueprint('admin', __name__)
auth_service = get_auth_service()
qr_service = get_qr_service()


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        role = jwt_data.get('role', 'resident')

        if role not in ['admin', 'super_admin']:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def super_admin_required(f):
    """Decorator to require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        role = jwt_data.get('role', 'resident')

        if role != 'super_admin':
            return jsonify({
                'success': False,
                'error': 'Super admin access required'
            }), 403

        return f(*args, **kwargs)

    return decorated_function


# ============== Dashboard ==============

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin'],
    'summary': 'Get admin dashboard data',
    'description': 'Get overview statistics for admin dashboard',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'Dashboard statistics',
            'schema': {
                'type': 'object',
                'properties': {
                    'users': {'type': 'object'},
                    'transactions': {'type': 'object'},
                    'security': {'type': 'object'}
                }
            }
        }
    }
})
def get_dashboard():
    """Get admin dashboard data"""
    try:
        today = datetime.utcnow().date()
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)

        # User statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        new_users_week = User.query.filter(User.created_at >= week_ago).count()

        # Transaction statistics
        total_transactions = Transaction.query.count()
        completed_transactions = Transaction.query.filter_by(
            status=TransactionStatus.COMPLETED
        ).count()
        pending_transactions = Transaction.query.filter_by(
            status=TransactionStatus.PENDING
        ).count()
        flagged_transactions = Transaction.query.filter_by(is_flagged=True).count()

        # Today's transactions
        today_start = datetime.combine(today, datetime.min.time())
        today_transactions = Transaction.query.filter(
            Transaction.created_at >= today_start
        ).count()

        # Total transaction value
        from sqlalchemy import func
        total_value = db.session.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.status == TransactionStatus.COMPLETED
        ).scalar() or 0

        # Security metrics
        recent_security_events = AuditLog.query.filter(
            AuditLog.severity.in_(['warning', 'error', 'critical']),
            AuditLog.created_at >= week_ago
        ).count()

        anomalies_detected = TamperDetectionResult.query.filter(
            TamperDetectionResult.is_anomaly == True,
            TamperDetectionResult.detected_at >= month_ago
        ).count()

        return jsonify({
            'success': True,
            'dashboard': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'new_this_week': new_users_week
                },
                'transactions': {
                    'total': total_transactions,
                    'completed': completed_transactions,
                    'pending': pending_transactions,
                    'flagged': flagged_transactions,
                    'today': today_transactions,
                    'total_value': float(total_value)
                },
                'security': {
                    'recent_events': recent_security_events,
                    'anomalies_month': anomalies_detected
                },
                'generated_at': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============== User Management ==============

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Users'],
    'summary': 'List all users',
    'description': 'Get paginated list of all users',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'page', 'in': 'query', 'type': 'integer', 'default': 1},
        {'name': 'per_page', 'in': 'query', 'type': 'integer', 'default': 20},
        {'name': 'role', 'in': 'query', 'type': 'string'},
        {'name': 'is_active', 'in': 'query', 'type': 'boolean'},
        {'name': 'search', 'in': 'query', 'type': 'string'}
    ],
    'responses': {
        '200': {'description': 'User list'}
    }
})
def list_users():
    """List all users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        role = request.args.get('role')
        is_active = request.args.get('is_active')
        search = request.args.get('search')

        query = User.query

        if role:
            try:
                query = query.filter(User.role == UserRole(role))
            except ValueError:
                pass

        if is_active is not None:
            query = query.filter(User.is_active == (is_active.lower() == 'true'))

        if search:
            query = query.filter(
                db.or_(
                    User.email.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%'),
                    User.unit_number.ilike(f'%{search}%')
                )
            )

        # Exclude soft-deleted users (those with email starting with 'deleted_')
        query = query.filter(~User.email.like('deleted_%'))

        query = query.order_by(User.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'users': [u.to_dict(include_sensitive=True) for u in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Users'],
    'summary': 'Get user details',
    'description': 'Get detailed information about a user',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'required': True, 'type': 'integer'}
    ],
    'responses': {
        '200': {'description': 'User details'},
        '404': {'description': 'User not found'}
    }
})
def get_user(user_id):
    """Get user details"""
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Get user's transaction statistics
        stats = qr_service.get_transaction_statistics(user_id=user_id)

        # Get recent activity
        recent_logs = AuditLog.query.filter_by(user_id=user_id).order_by(
            AuditLog.created_at.desc()
        ).limit(10).all()

        return jsonify({
            'success': True,
            'user': user.to_dict(include_sensitive=True),
            'statistics': stats,
            'recent_activity': [log.to_dict() for log in recent_logs]
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Users'],
    'summary': 'Update user',
    'description': 'Update user details (admin only)',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'required': True, 'type': 'integer'},
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'is_active': {'type': 'boolean'},
                    'is_verified': {'type': 'boolean'},
                    'role': {'type': 'string'},
                    'failed_login_attempts': {'type': 'integer'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'User updated'},
        '404': {'description': 'User not found'}
    }
})
def update_user(user_id):
    """Update user details"""
    try:
        schema = AdminUserUpdateSchema()
        data = schema.load(request.json)

        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        admin_id = get_jwt_identity()

        # Update fields
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
        if 'role' in data:
            user.role = UserRole(data['role'])
        if 'failed_login_attempts' in data:
            user.failed_login_attempts = data['failed_login_attempts']
            if data['failed_login_attempts'] == 0:
                user.locked_until = None

        db.session.commit()

        # Audit log
        auth_service.create_audit_log(
            user_id=admin_id,
            action='admin_user_update',
            resource_type='user',
            resource_id=user_id,
            description=f'Admin updated user {user.email}',
            ip_address=request.remote_addr,
            severity='warning'
        )

        return jsonify({
            'success': True,
            'message': 'User updated',
            'user': user.to_dict(include_sensitive=True)
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


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Users'],
    'summary': 'Delete user',
    'description': 'Delete a user account (admin only). Uses soft delete to preserve transaction history.',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'required': True, 'type': 'integer'}
    ],
    'responses': {
        '200': {'description': 'User deleted'},
        '404': {'description': 'User not found'},
        '403': {'description': 'Cannot delete this user'}
    }
})
def delete_user(user_id):
    """Delete a user (soft delete to preserve referential integrity)"""
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        admin_id = get_jwt_identity()
        
        # Prevent self-deletion
        if str(user_id) == str(admin_id):
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 403

        # Prevent deletion of super admins by regular admins
        jwt_data = get_jwt()
        current_role = jwt_data.get('role', 'resident')
        if user.role == UserRole.SUPER_ADMIN and current_role != 'super_admin':
            return jsonify({
                'success': False,
                'error': 'Only super admins can delete super admin accounts'
            }), 403

        user_email = user.email
        
        # Soft delete: mark as inactive and anonymize email
        user.is_active = False
        user.email = f"deleted_{user_id}_{user.email}"
        user.full_name = f"Deleted User #{user_id}"
        
        db.session.commit()

        # Audit log
        auth_service.create_audit_log(
            user_id=admin_id,
            action='admin_user_delete',
            resource_type='user',
            resource_id=user_id,
            description=f'Admin deleted user {user_email}',
            ip_address=request.remote_addr,
            severity='critical'
        )

        return jsonify({
            'success': True,
            'message': f'User {user_email} deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>/profile', methods=['PUT'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Users'],
    'summary': 'Update user profile',
    'description': 'Update user profile details (admin only)',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'required': True, 'type': 'integer'},
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
        '200': {'description': 'User profile updated'},
        '404': {'description': 'User not found'}
    }
})
def update_user_profile(user_id):
    """Update user profile details"""
    try:
        data = request.json or {}

        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        admin_id = get_jwt_identity()

        # Update profile fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone_number' in data:
            user.phone_number = data['phone_number']
        if 'unit_number' in data:
            user.unit_number = data['unit_number']
        if 'community_name' in data:
            user.community_name = data['community_name']

        db.session.commit()

        # Audit log
        auth_service.create_audit_log(
            user_id=admin_id,
            action='admin_user_profile_update',
            resource_type='user',
            resource_id=user_id,
            description=f'Admin updated profile for {user.email}',
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'User profile updated',
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@admin_bp.route('/transactions', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Transactions'],
    'summary': 'List all transactions',
    'description': 'Get paginated list of all transactions',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'page', 'in': 'query', 'type': 'integer'},
        {'name': 'per_page', 'in': 'query', 'type': 'integer'},
        {'name': 'status', 'in': 'query', 'type': 'string'},
        {'name': 'flagged_only', 'in': 'query', 'type': 'boolean'},
        {'name': 'start_date', 'in': 'query', 'type': 'string', 'format': 'date'},
        {'name': 'end_date', 'in': 'query', 'type': 'string', 'format': 'date'}
    ],
    'responses': {
        '200': {'description': 'Transaction list'}
    }
})
def list_transactions():
    """List all transactions"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        flagged_only = request.args.get('flagged_only', 'false').lower() == 'true'
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = Transaction.query

        if status:
            try:
                query = query.filter(Transaction.status == TransactionStatus(status))
            except ValueError:
                pass

        if flagged_only:
            query = query.filter(Transaction.is_flagged == True)

        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start)

        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at <= end)

        query = query.order_by(Transaction.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'transactions': [t.to_dict(include_sensitive=True) for t in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Transactions'],
    'summary': 'Update transaction',
    'description': 'Update transaction status or flags',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'transaction_id', 'in': 'path', 'required': True, 'type': 'integer'},
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'is_flagged': {'type': 'boolean'},
                    'flag_reason': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Transaction updated'},
        '404': {'description': 'Transaction not found'}
    }
})
def update_transaction(transaction_id):
    """Update transaction"""
    try:
        schema = AdminTransactionUpdateSchema()
        data = schema.load(request.json)

        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404

        admin_id = get_jwt_identity()

        # Update fields
        if 'status' in data:
            transaction.status = TransactionStatus(data['status'])
            if data['status'] == 'completed':
                transaction.completed_at = datetime.utcnow()
        if 'is_flagged' in data:
            transaction.is_flagged = data['is_flagged']
        if 'flag_reason' in data:
            transaction.flag_reason = data['flag_reason']

        db.session.commit()

        # Audit log
        auth_service.create_audit_log(
            user_id=admin_id,
            action='admin_transaction_update',
            resource_type='transaction',
            resource_id=transaction_id,
            description=f'Admin updated transaction {transaction.transaction_ref}',
            ip_address=request.remote_addr,
            severity='warning'
        )

        return jsonify({
            'success': True,
            'message': 'Transaction updated',
            'transaction': transaction.to_dict(include_sensitive=True)
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


# ============== Reports ==============

@admin_bp.route('/reports/transactions', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Reports'],
    'summary': 'Generate transaction report',
    'description': 'Generate transaction report in JSON or CSV format',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'start_date', 'in': 'query', 'type': 'string', 'format': 'date'},
        {'name': 'end_date', 'in': 'query', 'type': 'string', 'format': 'date'},
        {'name': 'status', 'in': 'query', 'type': 'string'},
        {'name': 'transaction_type', 'in': 'query', 'type': 'string'},
        {'name': 'format', 'in': 'query', 'type': 'string', 'enum': ['json', 'csv']},
        {'name': 'include_flagged_only', 'in': 'query', 'type': 'boolean'}
    ],
    'responses': {
        '200': {'description': 'Report data'}
    }
})
def generate_transaction_report():
    """Generate transaction report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        transaction_type = request.args.get('transaction_type')
        output_format = request.args.get('format', 'json')
        flagged_only = request.args.get('include_flagged_only', 'false').lower() == 'true'

        query = Transaction.query

        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start)

        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at <= end)

        if status:
            try:
                query = query.filter(Transaction.status == TransactionStatus(status))
            except ValueError:
                pass

        if transaction_type:
            try:
                query = query.filter(Transaction.transaction_type == TransactionType(transaction_type))
            except ValueError:
                pass

        if flagged_only:
            query = query.filter(Transaction.is_flagged == True)

        transactions = query.order_by(Transaction.created_at.desc()).all()

        # Calculate summary
        from sqlalchemy import func
        total_amount = sum(t.amount for t in transactions if t.status == TransactionStatus.COMPLETED)
        total_count = len(transactions)
        completed_count = sum(1 for t in transactions if t.status == TransactionStatus.COMPLETED)
        flagged_count = sum(1 for t in transactions if t.is_flagged)

        if output_format == 'csv':
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                'Transaction Ref', 'User ID', 'Amount', 'Currency', 'Type',
                'Status', 'Flagged', 'Flag Reason', 'Created At', 'Completed At'
            ])

            # Data
            for t in transactions:
                writer.writerow([
                    t.transaction_ref,
                    t.user_id,
                    t.amount,
                    t.currency,
                    t.transaction_type.value if t.transaction_type else '',
                    t.status.value if t.status else '',
                    'Yes' if t.is_flagged else 'No',
                    t.flag_reason or '',
                    t.created_at.isoformat() if t.created_at else '',
                    t.completed_at.isoformat() if t.completed_at else ''
                ])

            output.seek(0)

            # Audit log
            admin_id = get_jwt_identity()
            auth_service.create_audit_log(
                user_id=admin_id,
                action='report_generated',
                resource_type='transaction',
                description=f'Transaction report generated (CSV, {total_count} records)',
                ip_address=request.remote_addr
            )

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=transactions_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
                }
            )

        else:
            # JSON format
            admin_id = get_jwt_identity()
            auth_service.create_audit_log(
                user_id=admin_id,
                action='report_generated',
                resource_type='transaction',
                description=f'Transaction report generated (JSON, {total_count} records)',
                ip_address=request.remote_addr
            )

            return jsonify({
                'success': True,
                'report': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'filters': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'status': status,
                        'transaction_type': transaction_type,
                        'flagged_only': flagged_only
                    },
                    'summary': {
                        'total_count': total_count,
                        'completed_count': completed_count,
                        'flagged_count': flagged_count,
                        'total_amount': float(total_amount)
                    },
                    'transactions': [t.to_dict(include_sensitive=True) for t in transactions]
                }
            }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/reports/security', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Reports'],
    'summary': 'Generate security report',
    'description': 'Generate security audit report',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'start_date', 'in': 'query', 'type': 'string', 'format': 'date'},
        {'name': 'end_date', 'in': 'query', 'type': 'string', 'format': 'date'},
        {'name': 'severity', 'in': 'query', 'type': 'string'}
    ],
    'responses': {
        '200': {'description': 'Security report'}
    }
})
def generate_security_report():
    """Generate security audit report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        severity = request.args.get('severity')

        query = AuditLog.query

        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start)

        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at <= end)

        if severity:
            query = query.filter(AuditLog.severity == severity)

        logs = query.order_by(AuditLog.created_at.desc()).all()

        # Group by severity
        severity_counts = {}
        for log in logs:
            sev = log.severity or 'info'
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Group by action
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        return jsonify({
            'success': True,
            'report': {
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_events': len(logs),
                    'by_severity': severity_counts,
                    'by_action': action_counts
                },
                'events': [log.to_dict() for log in logs[:500]]  # Limit to 500 records
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============== Audit Logs ==============

@admin_bp.route('/audit-logs', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Audit'],
    'summary': 'Get audit logs',
    'description': 'Get paginated audit logs',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'page', 'in': 'query', 'type': 'integer'},
        {'name': 'per_page', 'in': 'query', 'type': 'integer'},
        {'name': 'user_id', 'in': 'query', 'type': 'integer'},
        {'name': 'action', 'in': 'query', 'type': 'string'},
        {'name': 'severity', 'in': 'query', 'type': 'string'}
    ],
    'responses': {
        '200': {'description': 'Audit logs'}
    }
})
def get_audit_logs():
    """Get audit logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        severity = request.args.get('severity')

        query = AuditLog.query

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action.ilike(f'%{action}%'))

        if severity:
            query = query.filter(AuditLog.severity == severity)

        query = query.order_by(AuditLog.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============== Tamper Detection Management ==============

@admin_bp.route('/tamper-detections', methods=['GET'])
@jwt_required()
@admin_required
@swag_from({
    'tags': ['Admin - Security'],
    'summary': 'Get tamper detection results',
    'description': 'Get all tamper detection results',
    'security': [{'Bearer': []}],
    'parameters': [
        {'name': 'page', 'in': 'query', 'type': 'integer'},
        {'name': 'per_page', 'in': 'query', 'type': 'integer'},
        {'name': 'anomalies_only', 'in': 'query', 'type': 'boolean'}
    ],
    'responses': {
        '200': {'description': 'Tamper detection results'}
    }
})
def get_tamper_detections():
    """Get tamper detection results"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        anomalies_only = request.args.get('anomalies_only', 'false').lower() == 'true'

        query = TamperDetectionResult.query

        if anomalies_only:
            query = query.filter(TamperDetectionResult.is_anomaly == True)

        query = query.order_by(TamperDetectionResult.detected_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'detections': [d.to_dict() for d in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============== Email smoke test ==============

@admin_bp.route('/email/test', methods=['POST'])
@jwt_required()
@admin_required
@limiter.limit("5 per minute")
@swag_from({
    'tags': ['Admin'],
    'summary': 'Send a test email',
    'description': 'Sends a test email synchronously to verify SMTP config. Body: {"to": "addr@example.com"} (optional, defaults to current admin).',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {'description': 'Test email dispatched'},
        '400': {'description': 'Mail not configured or send failed'}
    }
})
def email_test():
    """Send a test email to verify SMTP credentials."""
    try:
        body = request.get_json(silent=True) or {}
        target = body.get('to')
        if not target:
            user = User.query.get(get_jwt_identity())
            target = user.email if user else None
        if not target:
            return jsonify({'success': False, 'error': 'No recipient'}), 400

        send_email(
            to=target,
            subject='[Test] QR Transaction email is working',
            text_body='This is a test email from QR Transaction Protection. SMTP is configured correctly.',
            html_body='<p>This is a test email from <strong>QR Transaction Protection</strong>. SMTP is configured correctly.</p>',
            sync=True,
        )
        return jsonify({'success': True, 'message': f'Test email sent to {target}'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
