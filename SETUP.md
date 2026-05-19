# Setup Guide — Secure QR Transaction System

End-to-end setup from a fresh project zip. Tested on macOS + XAMPP, but the steps translate 1:1 to Windows (XAMPP control panel) and Linux (`apt install mariadb-server`).

---

## 1. Prerequisites

Install these before anything else:

| Tool                | Version            | Notes                                                 |
|---------------------|--------------------|-------------------------------------------------------|
| **Node.js**         | 20 LTS or 22 LTS   | Includes `npm`. Get from https://nodejs.org           |
| **Python**          | 3.11+              | `python3 --version` to check                          |
| **MySQL / MariaDB** | 8.x / 10.x         | Easiest via **XAMPP** (https://www.apachefriends.org) |
| **Git** (optional)  | latest             | Only if cloning instead of unzipping                  |

---

## 2. Unpack the Project

```bash
unzip qr-transaction-system.zip -d ~/projects
cd ~/projects/web-admin
```

The folder structure:

```
web-admin/
├── backend/          ← Flask API (Python)
├── src/              ← Next.js frontend
├── public/
├── package.json
├── SETUP.md          ← you are here
└── README.md
```

---

## 3. Start MySQL

Open **XAMPP Control Panel** → click **Start** next to *MySQL Database*.

Verify it's running:

```bash
# macOS / Linux
nc -z localhost 3306 && echo "MySQL up"

# Windows
netstat -an | findstr 3306
```

Then create the database:

```bash
# macOS XAMPP path
/Applications/XAMPP/xamppfiles/bin/mysql -u root -e "CREATE DATABASE IF NOT EXISTS qr_transaction;"

# Windows XAMPP path
C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE IF NOT EXISTS qr_transaction;"

# Linux
mysql -u root -e "CREATE DATABASE IF NOT EXISTS qr_transaction;"
```

Default XAMPP setup: user `root`, **no password**. If your MySQL has a password, edit `backend/.env` (see step 4).

---

## 4. Backend Setup (Flask)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Create `backend/.env`

`.env` is **gitignored** so the zip may not include it. Create it manually:

```bash
cat > .env <<'EOF'
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

SECRET_KEY=qr-transaction-protection-secret-key-2024
JWT_SECRET_KEY=jwt-secret-key-for-qr-protection-2024
AES_KEY=QRTransactionProtection2024SecureKey!

# Default XAMPP: root / no password
DATABASE_URL=mysql+pymysql://root:@localhost:3306/qr_transaction

RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=100 per hour
OTP_ISSUER_NAME=QR Transaction Protection
OTP_VALID_WINDOW=1
ANOMALY_THRESHOLD=-0.5

LOG_LEVEL=INFO
LOG_FILE=app.log
CORS_ORIGINS=*

# Optional — leave MAIL_ENABLED=False if you don't need real emails
MAIL_ENABLED=False
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
MAIL_DEFAULT_SENDER_NAME=QR Transaction Protection

APP_FRONTEND_URL=http://localhost:3000
EOF
```

### Seed sample data (optional but recommended)

```bash
python seed_database.py
```

Default accounts created:

| Role         | Email                              | Password         |
|--------------|------------------------------------|------------------|
| Super Admin  | `superadmin@qrtransaction.my`      | `SuperAdmin@123` |
| Admin        | `admin@qrtransaction.my`           | `Admin@123`      |
| Resident     | (see seed output)                  | `Resident@123`   |

### Start the backend

```bash
python run.py
```

You should see:

```
Server starting on http://0.0.0.0:5000
```

Test it:

```bash
curl http://localhost:5000/api/transactions/demo/2fa-info
# → JSON with otpauth_uri + secret
```

Leave this terminal running.

---

## 5. Frontend Setup (Next.js)

Open a **second terminal**:

```bash
cd web-admin            # back to project root, NOT inside backend/
npm install
```

### Create `.env.local` at project root

```bash
cat > .env.local <<'EOF'
NEXT_PUBLIC_BACKEND_URL=http://localhost:5000
EOF
```

### Start the dev server

```bash
npm run dev
```

If port 3000 is taken:

```bash
npm run dev -- -p 3001
```

Open http://localhost:3000 (or 3001).

---

## 6. Smoke Test

| Page                          | What to check                                                     |
|-------------------------------|-------------------------------------------------------------------|
| `/login`                      | Login with `admin@qrtransaction.my` / `Admin@123`                 |
| `/demo`                       | Click *Show Authenticator Setup* → QR appears, scan with Google Authenticator |
| `/resident/payment`           | QR pairs with same authenticator → enter 6-digit code → Confirm   |
| `/admin/dashboard`            | Loads real stats from backend                                     |

---

## 7. Common Issues

### `Failed to fetch` on `/demo`
Backend not running, or running an older version. Stop it (Ctrl+C) and rerun `python run.py`.

### `Can't connect to MySQL server on 'localhost'`
MySQL not started. Open XAMPP Control Panel → Start MySQL.

### `Port 5000 already in use`
Another process owns the port. Find and kill it:

```bash
# macOS / Linux
lsof -i :5000
kill <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### `Port 3000 already in use`
Run the frontend on another port: `npm run dev -- -p 3001`.

### Stale code after `git pull`
Clear caches and reinstall:

```bash
# Frontend
rm -rf .next node_modules
npm install
npm run dev

# Backend
find backend -name __pycache__ -type d -exec rm -rf {} +
# then restart python run.py
```

### MySQL on macOS: `Permission denied` writing to `var/mysql/...err`
Start MySQL with sudo:

```bash
sudo /Applications/XAMPP/xamppfiles/bin/mysql.server start
```

Or use the XAMPP Manager GUI (it prompts for password automatically).

---

## 8. Production / Demo URLs

After everything is up, share these with the audience:

- **Login**: http://localhost:3000/login
- **Live demo (no login)**: http://localhost:3000/demo
- **Admin dashboard**: http://localhost:3000/admin/dashboard (after admin login)
- **Resident payment**: http://localhost:3000/resident/payment (after resident login)

---

## 9. Stopping Everything

```bash
# Frontend terminal: Ctrl+C
# Backend terminal:  Ctrl+C
# MySQL: XAMPP Control Panel → Stop
```
