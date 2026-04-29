"""
AI-Based Tamper Detection Service using Isolation Forest
for anomaly detection in QR transaction patterns
"""
import os
import json
import logging
import numpy as np
from datetime import datetime, timedelta
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from flask import current_app

logger = logging.getLogger(__name__)


class TamperDetectionService:
    """
    AI-powered tamper detection service using Isolation Forest algorithm
    for detecting anomalies in transaction patterns.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_version = "1.0.0"
        self.feature_names = [
            'amount',
            'hour_of_day',
            'day_of_week',
            'transaction_frequency',
            'amount_deviation',
            'time_since_last_transaction',
            'qr_scan_attempts'
        ]

    def _get_model_path(self):
        """Get the model file path"""
        try:
            return current_app.config.get('AI_MODEL_PATH', 'models/tamper_detection_model.joblib')
        except RuntimeError:
            return 'models/tamper_detection_model.joblib'

    def _get_anomaly_threshold(self):
        """Get the anomaly threshold from config"""
        try:
            return current_app.config.get('ANOMALY_THRESHOLD', -0.5)
        except RuntimeError:
            return -0.5

    def load_model(self):
        """Load the trained model from disk"""
        model_path = self._get_model_path()
        scaler_path = model_path.replace('.joblib', '_scaler.joblib')

        try:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                if os.path.exists(scaler_path):
                    self.scaler = joblib.load(scaler_path)
                logger.info(f"Loaded tamper detection model from {model_path}")
                return True
            else:
                logger.warning("No saved model found, will train new model on first use")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False

    def save_model(self):
        """Save the trained model to disk"""
        model_path = self._get_model_path()
        scaler_path = model_path.replace('.joblib', '_scaler.joblib')

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            joblib.dump(self.model, model_path)
            if self.scaler:
                joblib.dump(self.scaler, scaler_path)
            logger.info(f"Saved tamper detection model to {model_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False

    def generate_training_data(self, n_samples=1000):
        """
        Generate synthetic training data for the model.
        In production, this would use real historical transaction data.
        """
        np.random.seed(42)

        # Normal transactions (90%)
        n_normal = int(n_samples * 0.9)
        normal_data = {
            'amount': np.random.lognormal(4, 1, n_normal),  # Log-normal distribution for amounts
            'hour_of_day': np.random.normal(14, 4, n_normal) % 24,  # Peak around 2 PM
            'day_of_week': np.random.randint(0, 7, n_normal),
            'transaction_frequency': np.random.poisson(3, n_normal),  # Average 3 transactions/day
            'amount_deviation': np.random.normal(0, 0.2, n_normal),
            'time_since_last_transaction': np.random.exponential(4, n_normal),  # Hours
            'qr_scan_attempts': np.ones(n_normal)  # Normal: single scan
        }

        # Anomalous transactions (10%)
        n_anomaly = n_samples - n_normal
        third = n_anomaly // 3
        half = n_anomaly // 2
        anomaly_data = {
            'amount': np.concatenate([
                np.random.lognormal(7, 0.5, third),  # Unusually high amounts
                np.random.uniform(0.01, 1, third),  # Unusually low amounts
                np.random.lognormal(4, 1, n_anomaly - 2 * third)  # Normal amounts, other anomalies
            ])[:n_anomaly],
            'hour_of_day': np.concatenate([
                np.random.uniform(0, 5, half),  # Late night transactions
                np.random.normal(14, 4, n_anomaly - half) % 24
            ])[:n_anomaly],
            'day_of_week': np.random.randint(0, 7, n_anomaly),
            'transaction_frequency': np.concatenate([
                np.random.poisson(15, half).astype(float),  # High frequency
                np.zeros(n_anomaly - half)  # Or very low
            ])[:n_anomaly],
            'amount_deviation': np.random.normal(0, 1.5, n_anomaly),  # Higher deviation
            'time_since_last_transaction': np.concatenate([
                np.random.exponential(0.1, half),  # Very quick succession
                np.random.exponential(48, n_anomaly - half)  # Or very long gaps
            ])[:n_anomaly],
            'qr_scan_attempts': np.random.choice(np.array([1, 3, 5, 10]), n_anomaly)
        }

        # Combine data
        X = np.column_stack([
            np.concatenate([normal_data[f], anomaly_data[f]]) for f in self.feature_names
        ])

        # Labels (1 for normal, -1 for anomaly) - for evaluation purposes
        y = np.concatenate([np.ones(n_normal), -np.ones(n_anomaly)])

        return X, y

    def train_model(self, X=None, contamination=0.1):
        """
        Train the Isolation Forest model.

        Args:
            X: Training data (if None, generates synthetic data)
            contamination: Expected proportion of anomalies
        """
        try:
            if X is None:
                X, _ = self.generate_training_data()

            # Initialize and fit scaler
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Train Isolation Forest
            self.model = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                max_samples='auto',
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_scaled)

            # Save the model
            self.save_model()

            logger.info("Tamper detection model trained successfully")
            return True

        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    def extract_features(self, transaction_data, historical_data=None):
        """
        Extract features from transaction data for anomaly detection.

        Args:
            transaction_data: Dictionary with transaction details
            historical_data: Optional list of recent transactions for context

        Returns:
            Numpy array of features
        """
        now = datetime.utcnow()

        # Extract basic features
        amount = float(transaction_data.get('amount', 0))
        created_at = transaction_data.get('created_at', now)
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        hour_of_day = created_at.hour
        day_of_week = created_at.weekday()

        # Calculate contextual features
        transaction_frequency = 0
        amount_deviation = 0
        time_since_last = 24  # Default: 24 hours

        if historical_data and len(historical_data) > 0:
            # Count transactions in last 24 hours
            yesterday = now - timedelta(hours=24)
            recent_transactions = [
                t for t in historical_data
                if t.get('created_at', now) > yesterday
            ]
            transaction_frequency = len(recent_transactions)

            # Calculate amount deviation from user's average
            amounts = [t.get('amount', 0) for t in historical_data]
            if amounts:
                avg_amount = np.mean(amounts)
                std_amount = np.std(amounts) if len(amounts) > 1 else avg_amount * 0.2
                amount_deviation = (amount - avg_amount) / (std_amount + 1e-6)

            # Time since last transaction
            if historical_data:
                last_transaction_time = max(
                    t.get('created_at', now) for t in historical_data
                )
                if isinstance(last_transaction_time, str):
                    last_transaction_time = datetime.fromisoformat(
                        last_transaction_time.replace('Z', '+00:00')
                    )
                time_since_last = (now - last_transaction_time).total_seconds() / 3600

        # QR scan attempts (from transaction metadata)
        qr_scan_attempts = transaction_data.get('qr_scan_attempts', 1)

        features = np.array([
            amount,
            hour_of_day,
            day_of_week,
            transaction_frequency,
            amount_deviation,
            time_since_last,
            qr_scan_attempts
        ]).reshape(1, -1)

        return features

    def detect_anomaly(self, transaction_data, historical_data=None):
        """
        Detect if a transaction is potentially fraudulent or tampered.

        Args:
            transaction_data: Dictionary with transaction details
            historical_data: Optional list of recent transactions for context

        Returns:
            Dictionary with detection results
        """
        try:
            # Ensure model is loaded
            if self.model is None:
                if not self.load_model():
                    # Train new model if none exists
                    self.train_model()

            # Extract features
            features = self.extract_features(transaction_data, historical_data)

            # Scale features
            if self.scaler:
                features_scaled = self.scaler.transform(features)
            else:
                features_scaled = features

            # Get anomaly score
            anomaly_score = self.model.score_samples(features_scaled)[0]
            prediction = self.model.predict(features_scaled)[0]

            # Determine if anomaly (prediction = -1)
            is_anomaly = prediction == -1
            threshold = self._get_anomaly_threshold()

            # Calculate confidence (normalized score)
            confidence = min(1.0, max(0.0, (anomaly_score - threshold) / abs(threshold) + 0.5))
            if is_anomaly:
                confidence = 1 - confidence

            # Determine detection type based on feature analysis
            detection_type = self._analyze_anomaly_type(features[0], historical_data)

            result = {
                'anomaly_score': float(anomaly_score),
                'is_anomaly': bool(is_anomaly),
                'confidence': float(confidence),
                'detection_type': detection_type,
                'model_version': self.model_version,
                'features_analyzed': {
                    name: float(features[0][i])
                    for i, name in enumerate(self.feature_names)
                },
                'threshold': threshold,
                'details': self._generate_details(features[0], is_anomaly, detection_type)
            }

            if is_anomaly:
                logger.warning(
                    f"Anomaly detected in transaction: score={anomaly_score:.4f}, "
                    f"type={detection_type}"
                )

            return result

        except Exception as e:
            logger.error(f"Error in anomaly detection: {str(e)}")
            return {
                'anomaly_score': 0.0,
                'is_anomaly': False,
                'confidence': 0.0,
                'detection_type': 'error',
                'model_version': self.model_version,
                'details': f"Detection error: {str(e)}",
                'error': str(e)
            }

    def _analyze_anomaly_type(self, features, historical_data):
        """Analyze what type of anomaly was detected"""
        amount, hour, day, freq, deviation, time_since, scans = features

        anomaly_types = []

        # Check for unusual amount
        if amount > 5000 or amount < 1:
            anomaly_types.append('unusual_amount')

        # Check for unusual time
        if hour < 5 or hour > 23:
            anomaly_types.append('unusual_time')

        # Check for high frequency
        if freq > 10:
            anomaly_types.append('high_frequency')

        # Check for amount deviation
        if abs(deviation) > 2:
            anomaly_types.append('amount_deviation')

        # Check for rapid succession
        if time_since < 0.1:  # Less than 6 minutes
            anomaly_types.append('rapid_succession')

        # Check for multiple QR scans
        if scans > 2:
            anomaly_types.append('multiple_qr_scans')

        return ','.join(anomaly_types) if anomaly_types else 'pattern_anomaly'

    def _generate_details(self, features, is_anomaly, detection_type):
        """Generate human-readable details about the detection"""
        amount, hour, day, freq, deviation, time_since, scans = features

        details = []

        if is_anomaly:
            if 'unusual_amount' in detection_type:
                details.append(f"Transaction amount (RM{amount:.2f}) is outside normal range")
            if 'unusual_time' in detection_type:
                details.append(f"Transaction at unusual hour ({int(hour):02d}:00)")
            if 'high_frequency' in detection_type:
                details.append(f"High transaction frequency ({int(freq)} in 24h)")
            if 'amount_deviation' in detection_type:
                details.append(f"Amount deviates significantly from user's pattern (z-score: {deviation:.2f})")
            if 'rapid_succession' in detection_type:
                details.append(f"Transaction in rapid succession ({time_since:.2f}h since last)")
            if 'multiple_qr_scans' in detection_type:
                details.append(f"Multiple QR scan attempts detected ({int(scans)})")
            if not details:
                details.append("Transaction pattern does not match typical behavior")
        else:
            details.append("Transaction appears normal")

        return '; '.join(details)

    def analyze_qr_integrity(self, qr_data, original_hash):
        """
        Analyze QR code data integrity by comparing hashes.

        Args:
            qr_data: The QR code data to verify
            original_hash: The original hash of the QR code

        Returns:
            Dictionary with integrity analysis results
        """
        from app.services.encryption import generate_hash

        try:
            current_hash = generate_hash(qr_data)
            is_valid = current_hash == original_hash

            result = {
                'is_valid': is_valid,
                'original_hash': original_hash,
                'current_hash': current_hash,
                'tampered': not is_valid,
                'analysis_time': datetime.utcnow().isoformat()
            }

            if not is_valid:
                logger.warning(
                    f"QR code integrity check failed. "
                    f"Original: {original_hash[:16]}..., Current: {current_hash[:16]}..."
                )
                result['details'] = "QR code has been modified since generation"

            return result

        except Exception as e:
            logger.error(f"Error in QR integrity analysis: {str(e)}")
            return {
                'is_valid': False,
                'tampered': True,
                'error': str(e),
                'details': "Error analyzing QR code integrity"
            }


# Singleton instance
_tamper_detection_service = None


def get_tamper_detection_service():
    """Get or create the singleton tamper detection service instance"""
    global _tamper_detection_service
    if _tamper_detection_service is None:
        _tamper_detection_service = TamperDetectionService()
        _tamper_detection_service.load_model()
    return _tamper_detection_service
