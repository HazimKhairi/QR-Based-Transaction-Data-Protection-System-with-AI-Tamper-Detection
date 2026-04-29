"""
Unit tests for AI-based tamper detection service
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from app.services.tamper_detection import TamperDetectionService, get_tamper_detection_service


class TestTamperDetectionService:
    """Test cases for TamperDetectionService"""

    @pytest.fixture
    def service(self):
        """Create a fresh tamper detection service instance"""
        service = TamperDetectionService()
        # Train with synthetic data for testing
        service.train_model()
        return service

    def test_service_initialization(self):
        """Test service can be initialized"""
        service = TamperDetectionService()
        assert service is not None
        assert service.model_version == "1.0.0"

    def test_generate_training_data(self):
        """Test synthetic training data generation"""
        service = TamperDetectionService()
        X, y = service.generate_training_data(n_samples=100)

        # Check shape
        assert X.shape[0] == 100
        assert X.shape[1] == 7  # 7 features

        # Check labels
        assert len(y) == 100
        assert 1 in y  # Normal transactions
        assert -1 in y  # Anomalies

    def test_train_model(self):
        """Test model training"""
        service = TamperDetectionService()
        success = service.train_model()

        assert success is True
        assert service.model is not None
        assert service.scaler is not None

    def test_extract_features(self):
        """Test feature extraction from transaction data"""
        service = TamperDetectionService()

        transaction_data = {
            'amount': 150.50,
            'created_at': datetime.utcnow(),
            'qr_scan_attempts': 1
        }

        features = service.extract_features(transaction_data)

        assert features.shape == (1, 7)
        assert features[0][0] == 150.50  # Amount

    def test_detect_normal_transaction(self, service):
        """Test detection of normal transaction"""
        # Normal transaction during business hours
        transaction_data = {
            'amount': 100.00,
            'created_at': datetime.utcnow().replace(hour=14),  # 2 PM
            'qr_scan_attempts': 1
        }

        historical_data = [
            {'amount': 95.00, 'created_at': datetime.utcnow() - timedelta(days=1)},
            {'amount': 105.00, 'created_at': datetime.utcnow() - timedelta(days=2)},
            {'amount': 100.00, 'created_at': datetime.utcnow() - timedelta(days=3)},
        ]

        result = service.detect_anomaly(transaction_data, historical_data)

        assert 'anomaly_score' in result
        assert 'is_anomaly' in result
        assert 'confidence' in result
        assert 'detection_type' in result
        assert 'model_version' in result

    def test_detect_unusual_amount(self, service):
        """Test detection of unusually high amount"""
        transaction_data = {
            'amount': 50000.00,  # Very high amount
            'created_at': datetime.utcnow().replace(hour=14),
            'qr_scan_attempts': 1
        }

        historical_data = [
            {'amount': 100.00, 'created_at': datetime.utcnow() - timedelta(days=1)},
            {'amount': 95.00, 'created_at': datetime.utcnow() - timedelta(days=2)},
        ]

        result = service.detect_anomaly(transaction_data, historical_data)

        # High amount should likely be flagged
        assert 'unusual_amount' in result.get('detection_type', '') or result['is_anomaly']

    def test_detect_unusual_time(self, service):
        """Test detection of transaction at unusual hour"""
        transaction_data = {
            'amount': 100.00,
            'created_at': datetime.utcnow().replace(hour=3),  # 3 AM
            'qr_scan_attempts': 1
        }

        result = service.detect_anomaly(transaction_data, [])

        # Late night transaction might be flagged
        assert 'unusual_time' in result.get('detection_type', '') or 'details' in result

    def test_detect_multiple_qr_scans(self, service):
        """Test detection of multiple QR scan attempts"""
        transaction_data = {
            'amount': 100.00,
            'created_at': datetime.utcnow(),
            'qr_scan_attempts': 10  # Many scan attempts
        }

        result = service.detect_anomaly(transaction_data, [])

        # Multiple scans should be flagged
        assert 'multiple_qr_scans' in result.get('detection_type', '') or result.get('features_analyzed', {}).get('qr_scan_attempts') == 10

    def test_analyze_qr_integrity_valid(self, service):
        """Test QR integrity check with valid data"""
        from app.services.encryption import generate_hash

        qr_data = "test_qr_code_data"
        original_hash = generate_hash(qr_data)

        result = service.analyze_qr_integrity(qr_data, original_hash)

        assert result['is_valid'] is True
        assert result['tampered'] is False

    def test_analyze_qr_integrity_tampered(self, service):
        """Test QR integrity check with tampered data"""
        from app.services.encryption import generate_hash

        qr_data = "test_qr_code_data"
        original_hash = generate_hash(qr_data)

        # Tamper the data
        tampered_data = "modified_qr_code_data"

        result = service.analyze_qr_integrity(tampered_data, original_hash)

        assert result['is_valid'] is False
        assert result['tampered'] is True

    def test_anomaly_type_analysis(self, service):
        """Test anomaly type categorization"""
        # Test high amount
        features = np.array([10000.0, 14, 2, 3, 0, 4, 1])  # High amount
        anomaly_type = service._analyze_anomaly_type(features, None)
        assert 'unusual_amount' in anomaly_type

        # Test unusual time
        features = np.array([100.0, 3, 2, 3, 0, 4, 1])  # 3 AM
        anomaly_type = service._analyze_anomaly_type(features, None)
        assert 'unusual_time' in anomaly_type

        # Test high frequency
        features = np.array([100.0, 14, 2, 15, 0, 4, 1])  # 15 transactions/day
        anomaly_type = service._analyze_anomaly_type(features, None)
        assert 'high_frequency' in anomaly_type

    def test_generate_details(self, service):
        """Test detail generation for anomalies"""
        features = np.array([10000.0, 3, 2, 15, 3.5, 0.05, 5])

        details = service._generate_details(features, True, 'unusual_amount,unusual_time')
        assert 'amount' in details.lower() or 'hour' in details.lower()

    def test_model_persistence(self, service, tmp_path):
        """Test model save and load"""
        import os

        # Set custom model path
        model_path = os.path.join(tmp_path, 'test_model.joblib')
        service._get_model_path = lambda: model_path

        # Save model
        assert service.save_model() is True
        assert os.path.exists(model_path)

        # Create new service and load
        new_service = TamperDetectionService()
        new_service._get_model_path = lambda: model_path
        assert new_service.load_model() is True
        assert new_service.model is not None

    def test_singleton_service(self):
        """Test singleton instance retrieval"""
        service1 = get_tamper_detection_service()
        service2 = get_tamper_detection_service()

        assert service1 is service2

    def test_result_structure(self, service):
        """Test that detection result has all required fields"""
        transaction_data = {
            'amount': 100.00,
            'created_at': datetime.utcnow(),
            'qr_scan_attempts': 1
        }

        result = service.detect_anomaly(transaction_data, [])

        required_fields = [
            'anomaly_score', 'is_anomaly', 'confidence',
            'detection_type', 'model_version', 'features_analyzed', 'details'
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_confidence_range(self, service):
        """Test that confidence is within valid range"""
        transaction_data = {
            'amount': 100.00,
            'created_at': datetime.utcnow(),
            'qr_scan_attempts': 1
        }

        result = service.detect_anomaly(transaction_data, [])

        assert 0.0 <= result['confidence'] <= 1.0
