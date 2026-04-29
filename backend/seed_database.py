"""
Database seeder for QR-Based Transaction Data Protection System
Creates sample users, transactions, and QR data for testing
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, UserRole, Transaction, TransactionStatus, TransactionType,
    TamperDetectionResult, AuditLog
)
from app.services.auth_service import get_auth_service
from app.services.qr_service import get_qr_service
from app.services.tamper_detection import get_tamper_detection_service


def seed_database():
    """Seed the database with sample data"""
    app = create_app('development')

    with app.app_context():
        print("Starting database seeding...")

        # Clear existing data
        print("Clearing existing data...")
        TamperDetectionResult.query.delete()
        AuditLog.query.delete()
        Transaction.query.delete()
        User.query.delete()
        db.session.commit()

        auth_service = get_auth_service()
        qr_service = get_qr_service()
        tamper_service = get_tamper_detection_service()

        # Create sample users
        print("Creating sample users...")
        users = []

        # Super Admin
        super_admin = User(
            email='superadmin@qrtransaction.my',
            password_hash=auth_service.hash_password('SuperAdmin@123'),
            full_name='Super Administrator',
            phone_number='+60123456789',
            community_name='System Administration',
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )
        users.append(super_admin)

        # Admin
        admin = User(
            email='admin@qrtransaction.my',
            password_hash=auth_service.hash_password('Admin@123'),
            full_name='Community Admin',
            phone_number='+60123456790',
            unit_number='Management Office',
            community_name='Taman Harmoni Residence',
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        users.append(admin)

        # Sample residents
        resident_data = [
            {
                'email': 'ahmad@example.com',
                'full_name': 'Ahmad bin Abdullah',
                'phone_number': '+60123456791',
                'unit_number': 'A-12-01',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'siti@example.com',
                'full_name': 'Siti Aminah binti Hassan',
                'phone_number': '+60123456792',
                'unit_number': 'B-05-03',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'raj@example.com',
                'full_name': 'Rajesh Kumar',
                'phone_number': '+60123456793',
                'unit_number': 'C-08-15',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'mei.ling@example.com',
                'full_name': 'Tan Mei Ling',
                'phone_number': '+60123456794',
                'unit_number': 'A-03-07',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'farah@example.com',
                'full_name': 'Farah Hanim binti Ismail',
                'phone_number': '+60123456795',
                'unit_number': 'B-10-02',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'kumar@example.com',
                'full_name': 'Kumar a/l Rajan',
                'phone_number': '+60123456796',
                'unit_number': 'C-02-11',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'wong@example.com',
                'full_name': 'Wong Chee Keong',
                'phone_number': '+60123456797',
                'unit_number': 'A-15-05',
                'community_name': 'Taman Harmoni Residence'
            },
            {
                'email': 'aisyah@example.com',
                'full_name': 'Aisyah binti Mohd',
                'phone_number': '+60123456798',
                'unit_number': 'B-07-09',
                'community_name': 'Taman Harmoni Residence'
            }
        ]

        for data in resident_data:
            resident = User(
                email=data['email'],
                password_hash=auth_service.hash_password('Resident@123'),
                full_name=data['full_name'],
                phone_number=data['phone_number'],
                unit_number=data['unit_number'],
                community_name=data['community_name'],
                role=UserRole.RESIDENT,
                is_active=True,
                is_verified=True
            )
            users.append(resident)

        # Add all users
        for user in users:
            db.session.add(user)
        db.session.commit()

        print(f"Created {len(users)} users")

        # Get residents for transaction creation
        residents = User.query.filter_by(role=UserRole.RESIDENT).all()

        # Create sample transactions
        print("Creating sample transactions...")
        transactions = []

        transaction_descriptions = {
            TransactionType.MAINTENANCE_FEE: [
                'Monthly maintenance fee - January 2024',
                'Monthly maintenance fee - February 2024',
                'Quarterly maintenance fee Q1 2024',
                'Annual maintenance fee 2024'
            ],
            TransactionType.SECURITY_PAYMENT: [
                'Security guard tip',
                'Guard duty payment',
                'Night patrol contribution',
                'Security enhancement fund'
            ],
            TransactionType.EVENT_FEE: [
                'CNY celebration contribution',
                'Hari Raya event fee',
                'Deepavali celebration',
                'Community BBQ event',
                'Year-end party contribution'
            ],
            TransactionType.PASAR_MALAM: [
                'Nasi Lemak stall',
                'Satay purchase',
                'Fresh fruits',
                'Kuih-muih',
                'Rojak stall payment'
            ],
            TransactionType.FACILITY_BOOKING: [
                'Badminton court booking',
                'Swimming pool access',
                'BBQ pit reservation',
                'Function hall booking',
                'Tennis court rental'
            ],
            TransactionType.OTHER: [
                'Parking fine payment',
                'Key card replacement',
                'Visitor pass',
                'General contribution'
            ]
        }

        amounts = {
            TransactionType.MAINTENANCE_FEE: (150, 500),
            TransactionType.SECURITY_PAYMENT: (10, 50),
            TransactionType.EVENT_FEE: (20, 100),
            TransactionType.PASAR_MALAM: (5, 50),
            TransactionType.FACILITY_BOOKING: (30, 150),
            TransactionType.OTHER: (10, 100)
        }

        statuses = [
            TransactionStatus.COMPLETED,
            TransactionStatus.COMPLETED,
            TransactionStatus.COMPLETED,
            TransactionStatus.PENDING,
            TransactionStatus.CANCELLED,
            TransactionStatus.FAILED
        ]

        # Generate transactions over the past 90 days
        for i in range(100):
            user = random.choice(residents)
            tx_type = random.choice(list(TransactionType))
            status = random.choice(statuses)

            min_amount, max_amount = amounts[tx_type]
            amount = round(random.uniform(min_amount, max_amount), 2)

            description = random.choice(transaction_descriptions[tx_type])

            # Random date in the past 90 days
            days_ago = random.randint(0, 90)
            created_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))

            # Create QR transaction data
            result = qr_service.create_qr_transaction(
                user_id=user.id,
                amount=amount,
                description=description,
                transaction_type=tx_type.value,
                recipient_id=admin.id if tx_type in [TransactionType.MAINTENANCE_FEE, TransactionType.FACILITY_BOOKING] else None,
                expires_in_minutes=30,
                ip_address='192.168.1.' + str(random.randint(1, 254)),
                device_info='Sample Device'
            )

            # Get the created transaction and update its details
            transaction = Transaction.query.get(result['transaction_id'])
            transaction.status = status
            transaction.created_at = created_at
            transaction.qr_generated_at = created_at

            if status == TransactionStatus.COMPLETED:
                transaction.completed_at = created_at + timedelta(minutes=random.randint(1, 30))
                transaction.is_verified = True

            # Flag some transactions for testing
            if random.random() < 0.05:  # 5% flagged
                transaction.is_flagged = True
                transaction.flag_reason = random.choice([
                    'Unusual transaction pattern detected',
                    'Multiple rapid transactions',
                    'Amount exceeds normal range',
                    'Suspicious timing'
                ])
                transaction.tamper_score = random.uniform(-0.8, -0.3)

            transactions.append(transaction)

        db.session.commit()
        print(f"Created {len(transactions)} transactions")

        # Create sample tamper detection results for flagged transactions
        print("Creating sample tamper detection results...")
        flagged_transactions = Transaction.query.filter_by(is_flagged=True).all()

        for tx in flagged_transactions:
            detection = TamperDetectionResult(
                transaction_id=tx.id,
                anomaly_score=tx.tamper_score or random.uniform(-0.8, -0.3),
                is_anomaly=True,
                confidence=random.uniform(0.7, 0.95),
                detection_type=random.choice(['unusual_amount', 'high_frequency', 'unusual_time', 'pattern_anomaly']),
                details='Automated detection during transaction processing',
                features_analyzed='{"amount": 500.0, "hour_of_day": 3, "day_of_week": 6}',
                model_version='1.0.0',
                detected_at=tx.created_at
            )
            db.session.add(detection)

        db.session.commit()
        print(f"Created {len(flagged_transactions)} tamper detection results")

        # Create sample audit logs
        print("Creating sample audit logs...")
        audit_actions = [
            ('user_login', 'User logged in successfully', 'info'),
            ('qr_generated', 'QR code generated for transaction', 'info'),
            ('transaction_completed', 'Transaction completed successfully', 'info'),
            ('2fa_enabled', 'Two-factor authentication enabled', 'warning'),
            ('password_changed', 'User password changed', 'warning'),
            ('qr_tamper_detected', 'Potential QR code tampering detected', 'warning'),
            ('failed_login', 'Failed login attempt', 'warning')
        ]

        for _ in range(50):
            user = random.choice(users)
            action, description, severity = random.choice(audit_actions)

            log = AuditLog(
                user_id=user.id,
                action=action,
                resource_type='user' if 'login' in action or 'password' in action else 'transaction',
                description=description,
                ip_address='192.168.1.' + str(random.randint(1, 254)),
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                status='success' if 'failed' not in action else 'failure',
                severity=severity,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            db.session.add(log)

        db.session.commit()
        print("Created 50 audit log entries")

        # Train the AI model with generated data
        print("Training AI tamper detection model...")
        tamper_service.train_model()
        print("AI model trained successfully")

        print("\n" + "=" * 50)
        print("Database seeding completed successfully!")
        print("=" * 50)
        print("\nSample Login Credentials:")
        print("-" * 50)
        print("Super Admin:")
        print("  Email: superadmin@qrtransaction.my")
        print("  Password: SuperAdmin@123")
        print("\nAdmin:")
        print("  Email: admin@qrtransaction.my")
        print("  Password: Admin@123")
        print("\nResident (sample):")
        print("  Email: ahmad@example.com")
        print("  Password: Resident@123")
        print("-" * 50)


if __name__ == '__main__':
    seed_database()
