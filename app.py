from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import sqlite3
import mysql.connector
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from market_engine import update_market_prices

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

DB_PATH = "portfolio.db"

def get_db_connection():
    # Detect if we should use MySQL (env vars present)
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
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

# Simple cache for market pricing
last_market_update = datetime.min

def execute_query(conn, query, params=()):
    cursor = conn.cursor(dictionary=True) if hasattr(conn, 'cursor') and not isinstance(conn, sqlite3.Connection) else conn.cursor()
    
    # Convert ? to %s for MySQL if needed
    if not isinstance(conn, sqlite3.Connection):
        query = query.replace('?', '%s')
        
    cursor.execute(query, params)
    return cursor


@app.route('/')
def index():
    global last_market_update
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Refresh market prices if older than 5 minutes
    if datetime.now() - last_market_update > timedelta(minutes=5):
        try:
            update_market_prices()
            last_market_update = datetime.now()
        except Exception as e:
            print(f"Background market update failed: {e}")

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)) if not isinstance(conn, sqlite3.Connection) else \
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user['role'] == 'admin':
        # Admin visibility
        cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
        cursor.execute("""
            SELECT p.*, u.username as owner_name 
            FROM portfolios p
            JOIN users u ON p.user_id = u.user_id
        """)
        portfolios = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT t.*, a.symbol as symbol 
            FROM transactions t
            JOIN assets a ON t.asset_id = a.asset_id
            ORDER BY t.transaction_date DESC LIMIT 50
        """)
        transactions = [dict(row) for row in cursor.fetchall()]
        watchlist = None
        watchlist_items = []
    else:
        # Standard user
        cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
        q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
        cursor.execute(f"SELECT * FROM portfolios WHERE user_id = {q_mark}", (user_id,))
        portfolios = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f"""
            SELECT t.*, a.symbol as symbol 
            FROM transactions t
            JOIN assets a ON t.asset_id = a.asset_id
            JOIN portfolios p ON t.portfolio_id = p.portfolio_id
            WHERE p.user_id = {q_mark}
            ORDER BY t.transaction_date DESC LIMIT 15
        """, (user_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f"SELECT * FROM watchlists WHERE user_id = {q_mark}", (user_id,))
        watchlist = cursor.fetchone()
        watchlist_items = []
        if watchlist:
            cursor.execute(f"""
                SELECT a.* 
                FROM watchlist_items wi
                JOIN assets a ON wi.asset_id = a.asset_id
                WHERE wi.watchlist_id = {q_mark}
            """, (watchlist['watchlist_id'],))
            watchlist_items = [dict(row) for row in cursor.fetchall()]

    # Get holdings
    cursor.execute("""
        SELECT h.*, p.name as portfolio_name, a.symbol, a.name as asset_name, a.current_price
        FROM holdings h
        JOIN portfolios p ON h.portfolio_id = p.portfolio_id
        JOIN assets a ON h.asset_id = a.asset_id
    """)
    holdings_raw = [dict(row) for row in cursor.fetchall()]
    
    if user['role'] != 'admin':
        portfolio_ids = [p['portfolio_id'] for p in portfolios]
        holdings_raw = [h for h in holdings_raw if h['portfolio_id'] in portfolio_ids]
        
    # Map to track total cost per portfolio for gain/loss coloring
    portfolios_cost = {p['portfolio_id']: 0.0 for p in portfolios}
    
    # Calculate P/L for each holding
    holdings = []
    for h in holdings_raw:
        qty = float(h['quantity'])
        buy_price = float(h['average_buy_price'])
        curr_price = float(h['current_price'])
        total_value = qty * curr_price
        
        # Track cost basis for the portfolio
        if h['portfolio_id'] in portfolios_cost:
            portfolios_cost[h['portfolio_id']] += qty * buy_price
            
        # Calculate P/L %
        pl_pct = 0.0
        if buy_price > 0:
            pl_pct = ((curr_price - buy_price) / buy_price) * 100
            
        holdings.append({
            'portfolio_name': h['portfolio_name'],
            'symbol': h['symbol'],
            'name': h['asset_name'],
            'quantity': qty,
            'average_buy_price': buy_price,
            'current_price': curr_price,
            'total_holding_value': total_value,
            'pl_percentage': pl_pct,
            'pl_class': 'badge-success' if pl_pct >= 0 else 'badge-danger'
        })

    # Add simulated daily change AND real gain/loss color to portfolios
    total_market_value = 0.0
    total_investment_cost = 0.0
    
    for p in portfolios:
        total_market_value += float(p['total_value'])
        cost = portfolios_cost.get(p['portfolio_id'], 0.0)
        total_investment_cost += cost
        
        # Real gain/loss check
        p['is_profit'] = float(p['total_value']) >= cost
        p['value_class'] = 'text-success' if p['is_profit'] else 'text-danger'
        
        # Simulate a daily change
        seed = p['portfolio_id'] + 42
        random.seed(seed)
        p['daily_change'] = random.uniform(-3.5, 5.0)
        p['daily_class'] = 'text-success' if p['daily_change'] >= 0 else 'text-danger'

    # Global performance status
    is_outperforming = total_market_value >= total_investment_cost
    performance = {
        'status': 'outperforming' if is_outperforming else 'underperforming',
        'class': 'text-success' if is_outperforming else 'text-danger',
        'border': 'border-success' if is_outperforming else 'border-danger'
    }

    cursor.execute("SELECT * FROM assets ORDER BY symbol")
    assets_list = [dict(row) for row in cursor.fetchall()]
        
    cursor.execute("SELECT * FROM market_news ORDER BY published_at DESC LIMIT 10")
    news = [dict(row) for row in cursor.fetchall()]
    
    wl_dict = None
    if watchlist:
        wl_dict = {'name': watchlist['name'], 'asset_details': watchlist_items}

    total_pl = total_market_value - total_investment_cost
    
    cursor.close()
    conn.close()
        
    return render_template('index.html', 
                          user=user, 
                          portfolios=portfolios, 
                          holdings=holdings, 
                          transactions=transactions, 
                          assets=assets_list, 
                          news=news, 
                          watchlist=wl_dict, 
                          performance=performance,
                          total_valuation=total_market_value,
                          total_pl=total_pl)

@app.route('/manage_holding', methods=['POST'])
def manage_holding():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action') 
    portfolio_id = request.form.get('portfolio_id')
    asset_id = request.form.get('asset_id')
    
    try:
        quantity = float(request.form.get('quantity'))
        price = float(request.form.get('price'))
    except (ValueError, TypeError):
        flash('Invalid quantity or price.', 'danger')
        return redirect(url_for('index'))
    
    transaction_type = 'BUY' if action == 'add' else 'SELL'
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
    
    try:
        cursor.execute(f"""
            INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, price_per_unit) 
            VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark})
        """, (portfolio_id, asset_id, transaction_type, quantity, price))
        conn.commit()
        flash('Transaction recorded successfully!', 'success')
    except Exception as e:
        if conn: conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
        
    if session.get('role') == 'admin':
        cursor.execute(f"INSERT INTO audit_logs (admin_id, action) VALUES ({q_mark}, {q_mark})", 
                       (session['user_id'], f"Admin force update: {action} {quantity} of asset {asset_id}"))
        conn.commit()
        
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
        q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
        cursor.execute(f"SELECT * FROM users WHERE username = {q_mark}", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_audit():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    cursor.execute("""
        SELECT l.*, u.username as admin_name
        FROM audit_logs l
        JOIN users u ON l.admin_id = u.user_id
        ORDER BY l.timestamp DESC
    """)
    logs = [dict(row) for row in cursor.fetchall()]
    
    q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
    cursor.execute(f"SELECT * FROM users WHERE user_id = {q_mark}", (session['user_id'],))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    return render_template('admin.html', logs=logs, user=user)

@app.route('/admin/sql-console', methods=['GET', 'POST'])
def sql_console():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    results = None
    columns = None
    error = None
    query = ""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    
    # Get tables for sidebar
    try:
        table_query = "SELECT name FROM sqlite_master WHERE type='table'" if isinstance(conn, sqlite3.Connection) else \
                      "SHOW TABLES"
        cursor.execute(table_query)
        tables_raw = cursor.fetchall()
        tables = []
        for t in tables_raw:
            table_name = t['name'] if isinstance(conn, sqlite3.Connection) else list(t.values())[0]
            if table_name in ('sqlite_sequence', 'audit_logs'): continue
            # Get count for each table
            count_cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
            count_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            row = count_cursor.fetchone()
            count = row['count'] if row else 0
            count_cursor.close()
            tables.append({'name': table_name, 'count': count})
    except Exception as e:
        tables = []
        error = f"Database connectivity error: {str(e)}"
    
    if request.method == 'POST' and not error:
        query = request.form.get('query', '').strip()
        if query:
            # Basic safety check
            if any(x in query.upper() for x in ['DROP DATABASE']):
                 error = "Dangerous operations like DROP DATABASE are blocked."
            else:
                try:
                    cursor.execute(query)
                    if cursor.description: # If it's a SELECT query
                        results = [dict(row) for row in cursor.fetchall()]
                        columns = [col[0] for col in cursor.description]
                    else:
                        conn.commit()
                        results = [{"Success": f"Query executed. Rows affected: {cursor.rowcount}"}]
                        columns = ["Status"]
                        # Refresh table counts
                        for t in tables:
                            count_cursor = conn.cursor()
                            try:
                                count_cursor.execute(f"SELECT COUNT(*) as count FROM {t['name']}")
                                t['count'] = count_cursor.fetchone()['count']
                            except: pass
                            count_cursor.close()
                except Exception as err:
                    error = str(err)
    
    cursor.close()
    conn.close()
    
    # Get user for header
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
    cursor.execute(f"SELECT * FROM users WHERE user_id = {q_mark}", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('sql_console.html', tables=tables, results=results, columns=columns, error=error, query=query, user=user)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
