"""
QR Code Service for generating and managing secure transaction QR codes
"""
import uuid
import json
import logging
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Transaction, TransactionStatus, TransactionType
from app.services.encryption import get_encryption_service

logger = logging.getLogger(__name__)
transaction_logger = logging.getLogger('transactions')


class QRService:
    """
    QR Code service for:
    - Generating secure encrypted QR codes for transactions
    - Verifying QR code integrity
    - Processing QR-based payments
    """

    def __init__(self):
        self.encryption = get_encryption_service()

    def generate_transaction_ref(self):
        """Generate a unique transaction reference"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"QRT-{timestamp}-{unique_id}"

    def create_qr_transaction(self, user_id, amount, description=None,
                              transaction_type='other', recipient_id=None,
                              expires_in_minutes=30, ip_address=None,
                              device_info=None):
        """
        Create a new QR-based transaction.

        Args:
            user_id: ID of the user initiating the transaction
            amount: Transaction amount
            description: Optional description
            transaction_type: Type of transaction
            recipient_id: Optional recipient user ID
            expires_in_minutes: QR code expiry time
            ip_address: Client IP address
            device_info: Device information

        Returns:
            Dictionary with transaction details and QR code data
        """
        try:
            # Generate unique transaction reference
            transaction_ref = self.generate_transaction_ref()

            # Create QR payload
            now = datetime.utcnow()
            qr_payload = {
                'transaction_ref': transaction_ref,
                'user_id': user_id,
                'recipient_id': recipient_id,
                'amount': amount,
                'currency': 'MYR',
                'description': description,
                'transaction_type': transaction_type,
                'generated_at': now.isoformat(),
                'expires_at': (now + timedelta(minutes=expires_in_minutes)).isoformat(),
                'version': '1.0'
            }

            # Encrypt QR payload
            encrypted_result = self.encryption.encrypt_qr_payload(qr_payload)

            # Encrypt sensitive data for storage
            encrypted_amount = self.encryption.encrypt(str(amount))
            encrypted_description = self.encryption.encrypt(description) if description else None

            # Convert transaction type string to enum
            try:
                tx_type = TransactionType(transaction_type)
            except ValueError:
                tx_type = TransactionType.OTHER

            # Create transaction record
            transaction = Transaction(
                transaction_ref=transaction_ref,
                user_id=user_id,
                recipient_id=recipient_id,
                amount=amount,
                amount_encrypted=encrypted_amount,
                description=description,
                description_encrypted=encrypted_description,
                transaction_type=tx_type,
                status=TransactionStatus.PENDING,
                qr_code_data=encrypted_result['encrypted_payload'],
                qr_code_hash=encrypted_result['payload_hash'],
                qr_generated_at=now,
                qr_expires_at=now + timedelta(minutes=expires_in_minutes),
                ip_address=ip_address,
                device_info=device_info
            )

            db.session.add(transaction)
            db.session.commit()

            transaction_logger.info(
                f"QR Transaction created: ref={transaction_ref}, "
                f"amount={amount}, user={user_id}"
            )

            return {
                'success': True,
                'transaction_ref': transaction_ref,
                'transaction_id': transaction.id,
                'qr_code_data': encrypted_result['encrypted_payload'],
                'qr_code_hash': encrypted_result['payload_hash'],
                'expires_at': transaction.qr_expires_at.isoformat(),
                'amount': amount,
                'currency': 'MYR'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating QR transaction: {str(e)}")
            raise

    def verify_qr_code(self, qr_code_data, expected_hash=None):
        """
        Verify QR code integrity and validity.

        Args:
            qr_code_data: Encrypted QR code data
            expected_hash: Optional expected hash for verification

        Returns:
            Dictionary with verification results
        """
        try:
            # Verify hash if provided
            if expected_hash:
                current_hash = self.encryption.generate_hash(qr_code_data)
                if current_hash != expected_hash:
                    return {
                        'valid': False,
                        'error': 'QR code integrity check failed',
                        'tampered': True
                    }

            # Decrypt and parse payload
            try:
                payload = self.encryption.decrypt_qr_payload(qr_code_data, expected_hash)
            except Exception as e:
                return {
                    'valid': False,
                    'error': 'Failed to decrypt QR code',
                    'tampered': True
                }

            # Check expiration
            expires_at = datetime.fromisoformat(payload.get('expires_at', ''))
            if datetime.utcnow() > expires_at:
                return {
                    'valid': False,
                    'error': 'QR code has expired',
                    'expired': True,
                    'payload': payload
                }

            # Look up transaction
            transaction = Transaction.query.filter_by(
                transaction_ref=payload.get('transaction_ref')
            ).first()

            if not transaction:
                return {
                    'valid': False,
                    'error': 'Transaction not found',
                    'payload': payload
                }

            # Check transaction status
            if transaction.status != TransactionStatus.PENDING:
                return {
                    'valid': False,
                    'error': f'Transaction already {transaction.status.value}',
                    'status': transaction.status.value,
                    'payload': payload
                }

            return {
                'valid': True,
                'payload': payload,
                'transaction': transaction.to_dict(),
                'expires_at': expires_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error verifying QR code: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }

    def process_transaction(self, qr_code_data, processor_user_id, ip_address=None,
                            device_info=None):
        """
        Process a QR-based transaction.

        Args:
            qr_code_data: Encrypted QR code data
            processor_user_id: ID of user processing (paying)
            ip_address: Client IP
            device_info: Device info

        Returns:
            Dictionary with processing results
        """
        try:
            # First verify the QR code
            verification = self.verify_qr_code(qr_code_data)

            if not verification.get('valid'):
                return {
                    'success': False,
                    'error': verification.get('error', 'Invalid QR code'),
                    'verification': verification
                }

            payload = verification['payload']
            transaction_ref = payload['transaction_ref']

            # Get the transaction
            transaction = Transaction.query.filter_by(
                transaction_ref=transaction_ref
            ).first()

            if not transaction:
                return {
                    'success': False,
                    'error': 'Transaction not found'
                }

            # Check if transaction is flagged
            if transaction.is_flagged:
                logger.warning(
                    f"Attempted to process flagged transaction: {transaction_ref}"
                )
                return {
                    'success': False,
                    'error': 'Transaction has been flagged for review',
                    'flagged': True,
                    'flag_reason': transaction.flag_reason
                }

            # Update transaction
            transaction.status = TransactionStatus.COMPLETED
            transaction.is_verified = True
            transaction.completed_at = datetime.utcnow()

            # Update device info if processing from different device
            if device_info and device_info != transaction.device_info:
                transaction.device_info = f"{transaction.device_info}; Processed: {device_info}"

            db.session.commit()

            transaction_logger.info(
                f"Transaction completed: ref={transaction_ref}, "
                f"amount={transaction.amount}, processor={processor_user_id}"
            )

            return {
                'success': True,
                'message': 'Transaction completed successfully',
                'transaction_ref': transaction_ref,
                'amount': transaction.amount,
                'currency': transaction.currency,
                'completed_at': transaction.completed_at.isoformat()
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing transaction: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_transaction(self, transaction_ref, user_id, reason=None):
        """
        Cancel a pending transaction.

        Args:
            transaction_ref: Transaction reference
            user_id: ID of user cancelling
            reason: Optional cancellation reason

        Returns:
            Dictionary with cancellation result
        """
        try:
            transaction = Transaction.query.filter_by(
                transaction_ref=transaction_ref
            ).first()

            if not transaction:
                return {
                    'success': False,
                    'error': 'Transaction not found'
                }

            # Only the creator can cancel
            if transaction.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Not authorized to cancel this transaction'
                }

            if transaction.status != TransactionStatus.PENDING:
                return {
                    'success': False,
                    'error': f'Cannot cancel {transaction.status.value} transaction'
                }

            transaction.status = TransactionStatus.CANCELLED
            if reason:
                transaction.flag_reason = f"Cancelled: {reason}"

            db.session.commit()

            transaction_logger.info(
                f"Transaction cancelled: ref={transaction_ref}, user={user_id}"
            )

            return {
                'success': True,
                'message': 'Transaction cancelled',
                'transaction_ref': transaction_ref
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cancelling transaction: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def flag_transaction(self, transaction_id, reason, flagged_by=None):
        """
        Flag a transaction for potential fraud.

        Args:
            transaction_id: Transaction ID
            reason: Flag reason
            flagged_by: User/system that flagged

        Returns:
            Boolean indicating success
        """
        try:
            transaction = Transaction.query.get(transaction_id)

            if not transaction:
                return False

            transaction.is_flagged = True
            transaction.flag_reason = reason
            transaction.status = TransactionStatus.FLAGGED

            db.session.commit()

            security_logger = logging.getLogger('security')
            security_logger.warning(
                f"Transaction flagged: id={transaction_id}, "
                f"ref={transaction.transaction_ref}, reason={reason}, "
                f"flagged_by={flagged_by}"
            )

            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error flagging transaction: {str(e)}")
            return False

    def get_user_transactions(self, user_id, page=1, per_page=20,
                              status=None, include_received=True):
        """
        Get transactions for a user.

        Args:
            user_id: User ID
            page: Page number
            per_page: Items per page
            status: Optional status filter
            include_received: Include transactions where user is recipient

        Returns:
            Paginated transaction list
        """
        from sqlalchemy import or_

        query = Transaction.query

        if include_received:
            query = query.filter(
                or_(
                    Transaction.user_id == user_id,
                    Transaction.recipient_id == user_id
                )
            )
        else:
            query = query.filter(Transaction.user_id == user_id)

        if status:
            try:
                status_enum = TransactionStatus(status)
                query = query.filter(Transaction.status == status_enum)
            except ValueError:
                pass

        query = query.order_by(Transaction.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'transactions': [t.to_dict() for t in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }

    def get_transaction_statistics(self, user_id=None, days=30):
        """
        Get transaction statistics.

        Args:
            user_id: Optional user ID for user-specific stats
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = Transaction.query.filter(Transaction.created_at >= cutoff_date)

        if user_id:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Transaction.user_id == user_id,
                    Transaction.recipient_id == user_id
                )
            )

        total_count = query.count()
        completed_count = query.filter(
            Transaction.status == TransactionStatus.COMPLETED
        ).count()
        flagged_count = query.filter(Transaction.is_flagged == True).count()

        total_amount = db.session.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.created_at >= cutoff_date
        )

        if user_id:
            total_amount = total_amount.filter(Transaction.user_id == user_id)

        total_amount = total_amount.scalar() or 0

        return {
            'period_days': days,
            'total_transactions': total_count,
            'completed_transactions': completed_count,
            'flagged_transactions': flagged_count,
            'total_amount': float(total_amount),
            'completion_rate': (completed_count / total_count * 100) if total_count > 0 else 0,
            'flag_rate': (flagged_count / total_count * 100) if total_count > 0 else 0
        }


# Singleton instance
_qr_service = None


def get_qr_service():
    """Get or create the singleton QR service instance"""
    global _qr_service
    if _qr_service is None:
        _qr_service = QRService()
    return _qr_service
