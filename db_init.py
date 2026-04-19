import sqlite3
import mysql.connector
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "portfolio.db"
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "portfolio")


def get_mysql_connection(with_database=True):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
    }
    if with_database:
        config["database"] = MYSQL_DB
    return mysql.connector.connect(**config)

def init_sqlite():
    print(f"Initializing SQLite database at {DB_PATH}...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing portfolio.db.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())
    
    seed_data(cursor, conn, is_sqlite=True)
    conn.close()
    print("SQLite Database initialized successfully!")


def ensure_mysql_database():
    conn = get_mysql_connection(with_database=False)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`")
    conn.commit()
    cursor.close()
    conn.close()


def split_mysql_script(script_text):
    delimiter = ';'
    buffer = []
    statements = []

    for raw_line in script_text.splitlines():
        stripped = raw_line.strip()
        if stripped.upper().startswith('DELIMITER '):
            delimiter = stripped.split(None, 1)[1]
            continue

        buffer.append(raw_line)
        current = "\n".join(buffer).rstrip()
        if current.endswith(delimiter):
            statement = current[:-len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []

    trailing = "\n".join(buffer).strip()
    if trailing:
        statements.append(trailing)

    return statements


def init_mysql():
    print(f"Initializing MySQL database '{MYSQL_DB}' on {MYSQL_HOST}:{MYSQL_PORT}...")
    ensure_mysql_database()
    conn = get_mysql_connection()
    cursor = conn.cursor()

    schema_path = os.path.join(os.path.dirname(__file__), "schema_mysql.sql")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    statements = split_mysql_script(schema_sql)

    for stmt in statements:
        try:
            cursor.execute(stmt)
        except Exception as exc:
            cursor.close()
            conn.close()
            raise RuntimeError(f"MySQL schema initialization failed: {exc}\nContext: {stmt[:200]}...") from exc

    conn.commit()
    seed_data(cursor, conn, is_sqlite=False)
    cursor.close()
    conn.close()
    print("MySQL database initialized successfully!")

def seed_data(cursor, conn, is_sqlite=True):
    print("Seeding initial users and assets...")
    admin_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
    
    user_query = "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)" if not is_sqlite else \
                 "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)"
    
    try:
        cursor.execute(user_query, ('admin', 'admin@axiom.com', admin_pw, 'admin'))
    except:
        print("Admin user already exists or error seeding user.")

    # Assets: Indian NSE Stocks (Realistic 2024-2025 Price Targets)
    assets = [
        ('RELIANCE.NS', 'Reliance Industries', 'Equity', 2950.45),
        ('TCS.NS', 'Tata Consultancy Services', 'Equity', 3912.00),
        ('HDFCBANK.NS', 'HDFC Bank', 'Equity', 1422.30),
        ('ICICIBANK.NS', 'ICICI Bank', 'Equity', 1085.60),
        ('INFY.NS', 'Infosys', 'Equity', 1488.90),
        ('BHARTIARTL.NS', 'Bharti Airtel', 'Equity', 1125.10),
        ('SBIN.NS', 'State Bank of India', 'Equity', 742.00),
        ('LICI.NS', 'LIC of India', 'Equity', 895.00),
        ('LT.NS', 'Larsen & Toubro', 'Equity', 3450.00),
        ('ITC.NS', 'ITC Limited', 'Equity', 428.15),
        ('HINDUNILVR.NS', 'Hindustan Unilever', 'Equity', 2315.00),
        ('AXISBANK.NS', 'Axis Bank', 'Equity', 1060.00),
        ('KOTAKBANK.NS', 'Kotak Mahindra Bank', 'Equity', 1720.00),
        ('ADANIENT.NS', 'Adani Enterprises', 'Equity', 3088.00),
        ('BAJFINANCE.NS', 'Bajaj Finance', 'Equity', 6450.00),
        ('MARUTI.NS', 'Maruti Suzuki', 'Equity', 11420.00),
        ('SUNPHARMA.NS', 'Sun Pharmaceutical', 'Equity', 1545.00),
        ('TITAN.NS', 'Titan Company', 'Equity', 3588.00),
        ('ULTRACEMCO.NS', 'UltraTech Cement', 'Equity', 9750.00),
        ('WIPRO.NS', 'Wipro Limited', 'Equity', 472.00),
        ('NESTLEIND.NS', 'Nestle India', 'Equity', 2480.00),
        ('HCLTECH.NS', 'HCL Technologies', 'Equity', 1590.00),
        ('JSWSTEEL.NS', 'JSW Steel', 'Equity', 842.00),
        ('ADANIPORTS.NS', 'Adani Ports', 'Equity', 1295.00),
        ('GRASIM.NS', 'Grasim Industries', 'Equity', 2188.00)
    ]
    
    asset_query = "INSERT INTO assets (symbol, name, asset_type, current_price) VALUES (%s, %s, %s, %s)" if not is_sqlite else \
                  "INSERT INTO assets (symbol, name, asset_type, current_price) VALUES (?, ?, ?, ?)"
    
    cursor.executemany(asset_query, assets)
    print(f"Successfully seeded {len(assets)} NSE assets.")
            
    conn.commit()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--sqlite":
        init_sqlite()
    else:
        init_mysql()
