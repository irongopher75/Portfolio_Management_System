import mysql.connector
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def get_db_config():
    ssl_ca = os.environ.get('MYSQL_SSL_CA')
    config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DB', 'portfolio_manager')
    }
    
    if ssl_ca and os.path.exists(ssl_ca):
        config['ssl_ca'] = ssl_ca
        config['ssl_verify_cert'] = True
        
    return config


def init_db():
    config = get_db_config()
    db_name = config.pop('database')
    
    print(f"Connecting to MySQL at {config['host']}...")
    try:
        conn = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return

    cursor = conn.cursor()
    
    # Create database if not exists
    print(f"Ensuring database '{db_name}' exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    conn.commit()
    cursor.close()
    conn.close()
    
    # Reconnect with database selected
    config['database'] = db_name
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("Executing MySQL Schema with Triggers...")
    schema_path = os.path.join(os.path.dirname(__file__), "schema_mysql.sql")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Hack to handle MySQL delimiters and multiple statements
    # We split by semicolon but ignore semicolons within triggers (BEGIN...END)
    # A simpler way is to use cursor.execute(..., multi=True) but it doesn't handle DELIMITER
    
    # Clean SQL: remove DELIMITER lines and handle //
    statements = []
    current_stmt = []
    in_trigger = False
    
    for line in schema_sql.split('\n'):
        line = line.strip()
        if not line or line.startswith('--') or line.startswith('DELIMITER'):
            continue
            
        if 'CREATE TRIGGER' in line:
            in_trigger = True
            
        current_stmt.append(line)
        
        if in_trigger:
            if 'END //' in line or 'END;' in line:
                statements.append(' '.join(current_stmt).replace('//', ';'))
                current_stmt = []
                in_trigger = False
        else:
            if line.endswith(';'):
                statements.append(' '.join(current_stmt))
                current_stmt = []
    
    for stmt in statements:
        if stmt.strip():
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as err:
                print(f"Warning in statement: {stmt[:50]}... Error: {err}")
    
    conn.commit()
    
    # Seed Basic Data
    print("Seeding initial users and assets...")
    
    # Check if admin exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                       ('admin', 'admin@axiom.com', admin_pw, 'admin'))
        
    # Seed some assets
    assets = [
        ('AAPL', 'Apple Inc.', 'stock', 185.92),
        ('MSFT', 'Microsoft Corp.', 'stock', 400.10),
        ('GOOGL', 'Alphabet Inc.', 'stock', 145.20),
        ('AMZN', 'Amazon.com', 'stock', 170.50),
        ('NVDA', 'NVIDIA Corp.', 'stock', 850.30),
        ('BTC', 'Bitcoin', 'crypto', 65000.00)
    ]
    for asset in assets:
        cursor.execute("INSERT IGNORE INTO assets (symbol, name, asset_type, current_price) VALUES (%s, %s, %s, %s)", asset)
        
    conn.commit()
    cursor.close()
    conn.close()
    print("MySQL Database initialized successfully!")

if __name__ == "__main__":
    init_db()
