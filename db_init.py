import sqlite3
import mysql.connector
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "portfolio.db"

def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        ssl_ca=os.getenv("MYSQL_SSL_CA"),
        ssl_verify_cert=True
    )

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

def init_mysql():
    print("Initializing Aiven MySQL database...")
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    schema_path = os.path.join(os.path.dirname(__file__), "schema_mysql.sql")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Advanced parsing to handle triggers and blocks
    print("Executing MySQL Schema (Axiom Production Mode)...")
    
    # 1. Strip out DELIMITER lines
    lines = [l for l in schema_sql.splitlines() if not l.strip().upper().startswith('DELIMITER')]
    
    # 2. Join lines back and split by ';' for regular statements, 
    # but be careful NOT to split inside triggers (END //)
    full_sql = "\n".join(lines)
    
    # We substitute '//' with a unique marker to avoid splitting trigger contents
    # Then we split by ';' first, then handle the trigger blocks
    parts = full_sql.split(';')
    final_statements = []
    
    current_block = []
    in_trigger = False
    
    for part in parts:
        clean_part = part.strip()
        if not clean_part: continue
        
        # If we see // it means we are in the trigger section
        if '//' in clean_part:
            # Clean up the // markers and add as a single statement
            stmt = clean_part.replace('//', '').strip()
            if stmt: final_statements.append(stmt)
        else:
            final_statements.append(clean_part)

    for stmt in final_statements:
        try:
            cursor.execute(stmt)
        except Exception as e:
            # Report but don't crash on 'already exists' for drop statements
            if "already exists" not in str(e).lower() and "unknown table" not in str(e).lower():
                print(f"Statement Warning: {e}")
                print(f"Context: {stmt[:100]}...")
    
    conn.commit()
    seed_data(cursor, conn, is_sqlite=False)
    conn.close()
    print("MySQL Database initialized successfully!")

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
    if len(sys.argv) > 1 and sys.argv[1] == "--mysql":
        init_mysql()
    else:
        init_sqlite()
