# Deployment Guide

This project uses a local MySQL database as the primary data store. Cloud-database and Aiven-specific certificate setup are not required.

## Recommended start command

If your host supports a `Procfile`, it will automatically use:

```bash
gunicorn -c gunicorn.conf.py app:app
```

If you need to enter the command manually, use the same command above.

## Environment variables

Set these in your deployment platform:

```env
SECRET_KEY=replace-this-with-a-long-random-value
DB_BACKEND=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-local-mysql-password
MYSQL_DB=portfolio
PORT=10000
```

Optional:

```env
SESSION_COOKIE_SECURE=true
FLASK_DEBUG=false
WEB_CONCURRENCY=2
GUNICORN_THREADS=4
```

## Health check

Point your platform health check to:

```text
/healthz
```

## Why this is more stable

- Gunicorn runs the app instead of the Flask development server.
- Worker recycling is enabled to reduce long-running process instability.
- `SECRET_KEY` stays stable across restarts when set in the environment.
- The app now uses local MySQL consistently instead of drifting between engines.

## Local run

```bash
pip install -r requirements.txt
python3 db_init.py
python3 app.py
```

For a production-like local run:

```bash
gunicorn -c gunicorn.conf.py app:app
```
