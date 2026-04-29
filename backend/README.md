# QR-Based Transaction Data Protection System - Backend API

A secure backend system for protecting QR code-based payment transactions from fraud and tampering for residential communities in Malaysia.

## Features

- **AES-256 Encryption**: All sensitive transaction data is encrypted using AES-256-CBC
- **AI-Powered Tamper Detection**: Machine learning-based anomaly detection using Isolation Forest algorithm
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for secure transactions
- **JWT Authentication**: Secure API access with JSON Web Tokens
- **Admin Dashboard API**: Comprehensive monitoring and reporting endpoints
- **Rate Limiting**: Protection against abuse and DDoS attacks
- **Audit Logging**: Complete audit trail for security and debugging

## Technology Stack

- **Framework**: Python Flask 3.0
- **Database**: SQLite (development) / PostgreSQL (production-ready)
- **Authentication**: JWT (flask-jwt-extended) + TOTP (pyotp)
- **Encryption**: cryptography (AES-256)
- **ML/AI**: scikit-learn (Isolation Forest)
- **API Documentation**: Swagger/OpenAPI (flasgger)
- **Testing**: pytest

## Project Structure

```
backend/
├── app/
│   ├── __init__.py         # Application factory
│   ├── models.py           # Database models
│   ├── schemas.py          # Marshmallow validation schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── transactions.py # Transaction/QR endpoints
│   │   ├── admin.py        # Admin endpoints
│   │   └── tamper_detection.py  # AI detection endpoints
│   └── services/
│       ├── __init__.py
│       ├── encryption.py   # AES-256 encryption service
│       ├── auth_service.py # Authentication & 2FA service
│       ├── qr_service.py   # QR code management service
│       └── tamper_detection.py  # AI detection service
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── test_encryption.py  # Encryption tests
│   ├── test_auth.py        # Authentication tests
│   ├── test_transactions.py # Transaction tests
│   └── test_tamper_detection.py  # AI tests
├── logs/                   # Application logs
├── models/                 # AI model storage
├── config.py               # Configuration settings
├── run.py                  # Application entry point
├── seed_database.py        # Database seeder
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize the database and seed with sample data**
   ```bash
   python seed_database.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

   The server will start at `http://localhost:5000`

7. **Access API Documentation**

   Open `http://localhost:5000/api/docs/` in your browser

## API Endpoints

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register a new user |
| POST | `/login` | User login (with optional 2FA) |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Logout and blacklist token |
| GET | `/profile` | Get current user profile |
| PUT | `/profile` | Update user profile |
| POST | `/2fa/setup` | Initialize 2FA setup |
| POST | `/2fa/verify` | Verify and enable 2FA |
| POST | `/2fa/disable` | Disable 2FA |
| POST | `/password/reset-request` | Request password reset |
| POST | `/password/reset` | Reset password with token |
| POST | `/password/change` | Change password |

### Transactions (`/api/transactions`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate-qr` | Generate QR code for payment |
| POST | `/verify-qr` | Verify QR code integrity |
| POST | `/process` | Process transaction (with 2FA) |
| POST | `/cancel/{ref}` | Cancel pending transaction |
| GET | `/history` | Get transaction history |
| GET | `/{ref}` | Get transaction details |
| GET | `/statistics` | Get transaction statistics |

### Tamper Detection (`/api/tamper`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Analyze transaction for tampering |
| POST | `/verify-qr-integrity` | Verify QR code hash integrity |
| POST | `/batch-analyze` | Batch analyze multiple transactions |
| GET | `/model/status` | Get AI model status |
| POST | `/model/train` | Retrain AI model (admin only) |
| GET | `/results/{id}` | Get detection results |

### Admin (`/api/admin`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Get dashboard statistics |
| GET | `/users` | List all users |
| GET | `/users/{id}` | Get user details |
| PUT | `/users/{id}` | Update user |
| GET | `/transactions` | List all transactions |
| PUT | `/transactions/{id}` | Update transaction |
| GET | `/reports/transactions` | Generate transaction report |
| GET | `/reports/security` | Generate security report |
| GET | `/audit-logs` | Get audit logs |
| GET | `/tamper-detections` | Get detection results |

## Sample Credentials

After running `seed_database.py`:

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@qrtransaction.my | SuperAdmin@123 |
| Admin | admin@qrtransaction.my | Admin@123 |
| Resident | ahmad@example.com | Resident@123 |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_encryption.py

# Run with verbose output
pytest -v
```

## Security Features

### AES-256 Encryption
- All sensitive data (transaction amounts, descriptions, QR payloads) are encrypted
- Uses CBC mode with random IV for each encryption
- SHA-256 hashing for data integrity verification

### AI Tamper Detection
- Isolation Forest algorithm for anomaly detection
- Analyzes 7 features: amount, time, frequency, deviation, etc.
- Real-time detection during transaction processing
- Configurable anomaly threshold

### Two-Factor Authentication
- TOTP-based (Time-based One-Time Password)
- Compatible with Google Authenticator, Authy, etc.
- Required for all transaction processing

### Rate Limiting
- Configurable per-endpoint limits
- Protects against brute force attacks
- 429 response when limits exceeded

### JWT Security
- Short-lived access tokens (1 hour)
- Refresh tokens for session management
- Token blacklisting on logout

## Configuration

Key configuration options in `config.py`:

```python
# JWT Settings
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Rate Limiting
RATELIMIT_DEFAULT = "100 per hour"

# AI Model
ANOMALY_THRESHOLD = -0.5  # Lower = more strict

# 2FA
OTP_VALID_WINDOW = 1  # Time tolerance
```

## Production Deployment

For production deployment:

1. Update `.env` with secure keys
2. Use PostgreSQL instead of SQLite
3. Enable HTTPS
4. Set `FLASK_ENV=production`
5. Use a production WSGI server (Gunicorn, uWSGI)

Example with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## Logging

Logs are stored in the `logs/` directory:
- `app.log` - General application logs
- `security.log` - Security-related events
- `transactions.log` - Transaction-specific logs

## Support

For issues and feature requests, please contact the development team.

## License

This project is proprietary software developed for Malaysian residential communities.

---

**QR-Based Transaction Data Protection System**
Protecting community transactions with enterprise-grade security.
