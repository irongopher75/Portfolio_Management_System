import os
import random
import time
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
fake = Faker()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        ssl_ca=os.getenv("MYSQL_SSL_CA"),
        ssl_verify_cert=True
    )

def populate():
    print("AXIOM EXTREME DATA ENGINE: Starting population (40,000+ Transaction Stress Test)...")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get Assets
    cursor.execute("SELECT asset_id, symbol, current_price FROM assets WHERE symbol LIKE '%.NS'")
    assets = cursor.fetchall()
    if not assets:
        print("Error: No NSE assets found. Run db_init.py --mysql first.")
        return
    
    # 2. Generate 500 Users
    print("Generating 500 institutional operatives...")
    password_hash = generate_password_hash('axiom123', method='pbkdf2:sha256')
    users_data = []
    usernames = set()
    while len(users_data) < 500:
        uname = fake.name().replace(" ", "").lower() + str(random.randint(10, 99))
        if uname not in usernames:
            usernames.add(uname)
            users_data.append((uname, f"{uname}@institutional.axiom", password_hash, 'user'))
    cursor.executemany("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)", users_data)
    conn.commit()
    
    cursor.execute("SELECT user_id FROM users WHERE role = 'user' ORDER BY user_id DESC LIMIT 500")
    user_ids = [u['user_id'] for u in cursor.fetchall()]
    
    # 3. Create Portfolios
    print("Initializing 500 portfolios...")
    portfolio_styles = ["Equity Alpha", "Momentum Strategy", "Long-Term Yield", "NSE Bluechip Sector", "Diversified Growth", "Risk Adjusted"]
    portfolios_data = [(uid, f"{random.choice(portfolio_styles)} Portfolio") for uid in user_ids]
    cursor.executemany("INSERT INTO portfolios (user_id, name) VALUES (%s, %s)", portfolios_data)
    conn.commit()
    
    cursor.execute("SELECT portfolio_id, user_id FROM portfolios WHERE user_id IN (%s)" % ",".join(map(str, user_ids)))
    portfolios = cursor.fetchall()
    
    # 4. Generate 1 Year of Historical News (20 items/day = 7,300 items)
    print("Generating 7,300 historical market signals (20/day for 1 year)...")
    news_data = []
    sources = ["Bloomberg Terminal", "Reuters Institutional", "NSE Surveillance", "Axiom Intel", "Market Alpha"]
    headlines = [
        "Earnings Beat: {symbol} reports 15% revenue growth.",
        "{symbol} targeted by institutional accumulation.",
        "Regulatory shift impacts {symbol} sector outlook.",
        "Axiom Analysis: {symbol} testing key resistance levels.",
        "Market Signal: Increased volume detected in {symbol}.",
        "Geopolitical volatility impacts NSE broad index.",
        "Corporate Governance Audit: {symbol} passes compliance.",
        "Capital Expenditure Plan: {symbol} announces new production node.",
        "Sentiment Pivot: Analysts upgrade {symbol} to Overweight.",
        "Portfolio Rebalancing detected across major institutional nodes."
    ]
    
    for i in range(365):
        pub_date = datetime.now() - timedelta(days=i)
        for _ in range(20):
            asset = random.choice(assets)
            headline = random.choice(headlines).format(symbol=asset['symbol'])
            news_data.append((headline, random.choice(sources), asset['symbol'], pub_date))
    
    cursor.executemany("INSERT INTO market_news (headline, source, related_asset_symbols, published_at) VALUES (%s, %s, %s, %s)", news_data)
    conn.commit()

    # 5. Generate 40,000+ Transactions (80+ per Portfolio)
    print("Generating ~40,000 transactions (Institutional Ledger Flood)...")
    transactions_data = []
    
    for p in portfolios:
        pid = p['portfolio_id']
        # Each portfolio gets 80-100 trades
        num_trades = random.randint(80, 95)
        
        # Pick 20 assets for this user's active universe
        user_assets = random.sample(assets, 20)
        
        for _ in range(num_trades):
            asset = random.choice(user_assets)
            aid = asset['asset_id']
            # Scattering trades across 365 days
            act_date = datetime.now() - timedelta(days=random.randint(1, 365))
            price = float(asset['current_price']) * random.uniform(0.75, 1.25)
            qty = random.randint(1, 500)
            t_type = random.choice(['BUY', 'SELL'])
            
            transactions_data.append((pid, aid, t_type, qty, price, act_date))

    print(f"Executing deep batch insert of {len(transactions_data)} ledger entries...")
    batch_size = 2000
    for i in range(0, len(transactions_data), batch_size):
        batch = transactions_data[i:i + batch_size]
        cursor.executemany(
            "INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, price_per_unit, transaction_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)", batch
        )
        conn.commit()
        print(f"  Processed {i + len(batch)} ledger updates (State: Agitation)...")

    conn.close()
    print("AXIOM EXTREME DATA ENGINE: Stress Test Population Complete!")

if __name__ == "__main__":
    populate()
