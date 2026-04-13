# Axiom Terminal | Deployment Protocol

This document outlines the standard procedure for deploying the Axiom Terminal as a professional institutional node.

## 🚀 Recommended Stack: Render.com

We recommend **Render.com** (or Railway/DigitalOcean) for the Axiom engine. 

> [!CAUTION]
> **Avoid Netlify/Vercel**: These platforms are optimized for static frontends. The Axiom Terminal requires a persistent Python runtime and a persistent MySQL handshake, which are not supported on static hosts.

### Step 1: Repository Alignment
Ensure your repository is synchronized with the latest **Surveillance Protocol** (Request-based architecture).

### Step 2: Provision Database
The system is pre-configured for **Aiven MySQL**.
1. Log in to [Aiven Console](https://console.aiven.io).
2. Ensure your MySQL node is active.
3. Download the `ca.pem` and place it in the root directory (already included in this repo).

### Step 3: Configure Render Web Service
1. **New Web Service**: Connect your GitHub repository.
2. **Runtime**: Python 3.12+ (Render uses `requirements.txt` automatically).
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT` (Requires `pip install gunicorn`).

### 🔐 Environment Variables
Configure the following keys in the Render "Environment" tab:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MYSQL_HOST` | Aiven Hostname | `mysql-xxxx.aivencloud.com` |
| `MYSQL_PORT` | Aiven Port | `12345` |
| `MYSQL_USER` | Admin Identity | `avnadmin` |
| `MYSQL_PASSWORD` | Secure Key | `********` |
| `MYSQL_DB` | Database Hub | `defaultdb` |
| `MYSQL_SSL_CA` | Path to Root CA | `ca.pem` |
| `SECRET_KEY` | Flask Handshake Key | `[Choose a long random string]` |
| `FLASK_ENV` | Environment Type | `production` |

### Step 4: Schema Handshake (One-time)
Once the service is live, run the initialization protocol to align the database:
```bash
python3 db_init.py --mysql
```

## 🛠️ Performance Tuning
For institutional-scale deployments (40,000+ records), we recommend a Render **Starter** instance (or higher) to ensure the Python memory footprint remains stable during heavy aggregation.
