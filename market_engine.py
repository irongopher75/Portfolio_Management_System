import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import sqlite3
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    if os.getenv("MYSQL_HOST"):
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB"),
            ssl_ca=os.getenv("MYSQL_SSL_CA"),
            ssl_verify_cert=True
        )
    return sqlite3.connect("portfolio.db")

def update_market_prices():
    """Fetches latest prices and updates the database."""
    print(f"[{datetime.now()}] Refreshing market prices...")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection) else conn.cursor()
    
    # Get all assets
    cursor.execute("SELECT asset_id, symbol FROM assets")
    assets = cursor.fetchall() if isinstance(conn, sqlite3.Connection) else cursor.fetchall()
    
    if not assets:
        print("No assets found in database.")
        conn.close()
        return

    # Extract symbols
    symbols = [a['symbol'] if not isinstance(a, tuple) else a[1] for a in assets]
    symbol_to_id = {a['symbol'] if not isinstance(a, tuple) else a[1]: (a['asset_id'] if not isinstance(a, tuple) else a[0]) for a in assets}
    
    # Map crypto symbols to Yahoo Finance format if needed
    mapped_symbols = []
    for s in symbols:
        if s in ('BTC', 'ETH', 'SOL', 'ADA'):
            mapped_symbols.append(f"{s}-USD")
        else:
            mapped_symbols.append(s)

    try:
        # Use auto_adjust=True to avoid FutureWarning and ensure correct price handling
        data = yf.download(mapped_symbols, period="1d", interval="1m", progress=False, auto_adjust=True)
        
        for i, s in enumerate(symbols):
            mapped_s = mapped_symbols[i]
            asset_id = symbol_to_id[s]
            
            try:
                # Handle single vs multi-asset download structure
                if len(symbols) > 1:
                    price = data['Close'][mapped_s].iloc[-1]
                else:
                    price = data['Close'].iloc[-1]
                
                if pd.isna(price): continue
                
                # Update DB
                q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
                cursor.execute(f"UPDATE assets SET current_price = {q_mark} WHERE asset_id = {q_mark}", (float(price), asset_id))
                print(f"Updated {s}: ₹{price:.2f}")
            except Exception as e:
                print(f"Could not update {s}: {e}")
                
        conn.commit()
    except Exception as e:
        print(f"Market update failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_market_prices()
