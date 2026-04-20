# Portfolio Management System

A Flask + MySQL portfolio management application built for a DBMS project. The system supports two roles:

- `user`: can register, log in, view holdings and transaction history, and submit buy/sell trade requests
- `admin`: can review pending trade requests, approve or reject them, inspect audit logs, and use the SQL console

The project uses a local MySQL database as the central data store, so multiple clients can reflect the same shared state without any external API layer.

## Project Overview

This application models a small portfolio surveillance platform with these core entities:

- `users`
- `assets`
- `portfolios`
- `holdings`
- `transactions`
- `watchlists`
- `watchlist_items`
- `trade_requests`
- `audit_logs`
- `market_news`

Important implementation details:

- Flask powers the web application
- MySQL is the primary database
- `mysql-connector-python` is used for database connectivity
- Gunicorn is included for production-style serving
- Trigger logic in MySQL keeps `holdings` and `portfolios.total_value` synchronized
- Role-based access is enforced for admin/user actions
- CSRF protection is enabled for state-changing POST actions

## Main Features

### User features

- Register and log in
- View portfolio holdings and transaction history
- Track asset prices and market signals
- Submit trade requests for buy/sell operations
- Monitor request status

### Admin features

- View pending trade requests
- Approve or reject trade requests
- Review audit logs
- Inspect data via the SQL console
- Monitor basic telemetry

## Project Structure

```text
app.py                 Main Flask application
db_init.py             MySQL database initialization and seed script
populate_data.py       Optional bulk/stress data generator
query_db.py            Simple database query helper
schema_mysql.sql       MySQL schema and trigger definitions
start_axiom.sh         Startup script for MySQL + Gunicorn + LocalTunnel
gunicorn.conf.py       Gunicorn server configuration
Procfile               Platform deployment entrypoint
templates/             Jinja HTML templates
static/                CSS assets
institutional_seed.sql Optional MySQL dump / reference seed data
```

## Requirements

Install the following on your system:

- Python 3
- MySQL Server
- Node.js and `npx` if you want to use LocalTunnel
- `pip`

Python packages used by the project:

- `flask`
- `mysql-connector-python`
- `python-dotenv`
- `werkzeug`
- `gunicorn`
- `faker`
- `pandas`

## Exact Setup Procedure On Another System

Follow these steps in order.

### 1. Clone the project

```bash
git clone <your-repository-url>
cd Portfolio_Management_System
```

### 2. Create and activate a Python virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Make sure MySQL is installed and running

You need a local MySQL server before starting the app.

Examples:

macOS with Homebrew:

```bash
brew services start mysql
```

Linux:

```bash
sudo systemctl start mysql
```

Windows:

- Start the MySQL service from Services, XAMPP, or MySQL Workbench environment

### 5. Create your local environment file

Copy the example file:

```bash
cp .env.example .env
```

Then edit `.env` and set the real values for your machine:

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=portfolio
SECRET_KEY=replace-this-with-a-long-random-string
PORT=5001
FLASK_DEBUG=false
```

### 6. Initialize the MySQL database

There are two ways to initialize the database:

#### Option A: Quick Restore from Institutional Seed (Recommended for Viva)
Use this if you want an exact copy of the 10,000+ records currently used in the demo. This is the fastest way to get a production-ready environment.

```bash
# On macOS/Linux:
mysql -u root -p portfolio < institutional_seed.sql
```

#### Option B: Fresh Initialization
Use this if you want a blank database that only contains the base template data (Admin user + Asset list).

```bash
python3 db_init.py
```

### 7. Start the application

For normal local development:

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:5001
```

### 8. Optional: Start with Gunicorn

For a production-style local run:

```bash
gunicorn -c gunicorn.conf.py app:app
```

### 9. Optional: Start with the bundled startup script

This script attempts to:

- ensure MySQL is reachable
- launch Gunicorn
- verify `/healthz`
- optionally open a LocalTunnel URL

Run:

```bash
bash start_axiom.sh
```

If LocalTunnel is unstable on your machine, ignore the public URL and use the local URL instead.

## Default Seeded Login

After running `python3 db_init.py`, the app seeds a default admin account:

- Username: `admin`
- Password: `admin123`

You can also register a normal user from the app interface.

## Optional Data Population

To generate additional demo/stress data:

```bash
python3 populate_data.py
```

Use this only if your local MySQL database has already been initialized.

## Health Check

The project exposes a health endpoint:

```text
/healthz
```

Example:

```bash
curl http://127.0.0.1:5001/healthz
```

Expected healthy response:

```json
{
  "database": "TCP/IP (MySQL)",
  "host": "127.0.0.1",
  "latency_ms": 5,
  "status": "ok"
}
```

## How Shared Reflection Works

This project uses a centralized database design:

- your laptop runs MySQL
- the Flask app connects to that MySQL instance
- all users interact with the same central database

Because all reads and writes happen against the same MySQL server, changes made by one client are visible to others when they reload or poll the latest data.

## Troubleshooting

### MySQL connection error

If you see errors like:

```text
Can't connect to MySQL server on '127.0.0.1:3306'
```

check:

- MySQL is running
- the username and password in `.env` are correct
- MySQL is listening on port `3306`

### Health check returns 503

This means the Flask app cannot connect to MySQL yet. Fix the MySQL connection first, then retry.

### Tunnel URL returns 503

This usually means LocalTunnel is unstable or the backend was not healthy when the tunnel started. The application itself can still be fine locally. Always verify:

```bash
curl http://127.0.0.1:5001/healthz
```

before trusting the public URL.

## Notes

- `.env` should stay local and should not be committed with real credentials
- generated logs, PID files, runtime files, and cache files are intentionally ignored
- the project is designed around local MySQL, not external APIs or cloud database services
