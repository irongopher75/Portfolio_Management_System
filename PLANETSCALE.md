# PlanetScale Cloud Setup Guide

Follow these steps to migrate your local database to the cloud (PlanetScale) for real-time synchronization.

## 1. Create a PlanetScale Database
1.  Log in to [PlanetScale](https://planetscale.com/).
2.  Create a new database (e.g., `portfolio_manager`).
3.  Click **Connect** in the top right.
4.  Select **Python** from the "Connect with" dropdown.
5.  Copy the credentials shown (`Host`, `Username`, `Password`, `Database`).

## 2. Update your `.env` File
Open your `.env` file and fill in the placeholders with the credentials from Step 1:
```env
MYSQL_HOST="your-aws-region.connect.psdb.cloud"
MYSQL_USER="your-username"
MYSQL_PASSWORD="your-password"
MYSQL_DB="your-database-name"

# SSL Certificate path (Required)
# macOS: /etc/ssl/cert.pem
# Linux: /etc/ssl/certs/ca-certificates.crt
MYSQL_SSL_CA="/etc/ssl/cert.pem"
```

## 3. Initialize the Cloud Database
Once the `.env` is updated, push the schema and initial data (assets/admin) to the cloud by running:
```bash
python3 db_init.py
```

## 4. Verify Connectivity
Run a test query via the terminal to confirm the cloud connection is active:
```bash
python3 query_db.py "SELECT * FROM assets;"
```

## 5. Sharing with Collaborators
Anyone you want to sync with simply needs to:
1.  Download the repository.
2.  Create a `.env` file with the **exact same** PlanetScale credentials you used.
3.  Run the app (`python3 app.py`). They will instantly see all the data you have entered!
