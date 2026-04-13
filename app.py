from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import sqlite3
import mysql.connector
import os
import random
import time
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
        # PRODUCTION HARDENING: Handle SSL CA path for cloud deployment
        ssl_ca = os.getenv("MYSQL_SSL_CA")
        verify_cert = True
        
        if ssl_ca:
            if not os.path.exists(ssl_ca):
                # Fallback to local file if absolute path fails
                ssl_ca = os.path.join(os.path.dirname(__file__), "ca.pem")
            if not os.path.exists(ssl_ca):
                # If still not found, we cannot verify cert
                verify_cert = False
                ssl_ca = None
        else:
            verify_cert = False
            
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB"),
            ssl_ca=ssl_ca,
            ssl_verify_cert=verify_cert
        )
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

import traceback
import sys

# Simple cache for market pricing
last_market_update = datetime.min

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the full traceback to Render logs for debugging
    print("!!! AXIOM CRITICAL EXCEPTION !!!", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    return f"Axiom Node Critical Error: {str(e)}", 500

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
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
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

    # System Performance Telemetry (Dynamic)
    start_lat = time.time()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    latency_ms = int((time.time() - start_lat) * 1000)
    
    is_outperforming = total_market_value >= total_investment_cost
    performance = {
        'status': 'outperforming' if is_outperforming else 'underperforming',
        'class': 'text-success' if is_outperforming else 'text-danger',
        'border': 'border-success' if is_outperforming else 'border-danger',
        'latency': latency_ms
    }

    cursor.execute("SELECT * FROM assets ORDER BY symbol")
    assets_list = [dict(row) for row in cursor.fetchall()]
        
    cursor.execute("SELECT * FROM market_news ORDER BY published_at DESC LIMIT 10")
    news = [dict(row) for row in cursor.fetchall()]
    
    wl_dict = None
    if watchlist:
        wl_dict = {'name': watchlist['name'], 'asset_details': watchlist_items}

    total_pl = total_market_value - total_investment_cost
    
    # Get Trade Requests
    q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
    cursor.execute(f"""
        SELECT r.*, a.symbol as symbol 
        FROM trade_requests r
        JOIN assets a ON r.asset_id = a.asset_id
        WHERE r.user_id = {q_mark}
        ORDER BY r.created_at DESC LIMIT 10
    """, (user_id,))
    trade_requests = [dict(row) for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    
    total_pl = total_market_value - total_investment_cost
        
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
                          total_pl=total_pl,
                          trade_requests=trade_requests)

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
        # PIVOT: Instead of direct transaction, we insert a trade request
        cursor.execute(f"""
            INSERT INTO trade_requests (user_id, portfolio_id, asset_id, transaction_type, quantity, requested_price, status) 
            VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, 'PENDING')
        """, (session['user_id'], portfolio_id, asset_id, transaction_type, quantity, price))
        conn.commit()
        flash('Surveillance Request Submitted. Pending Admin Handshake.', 'success')
    except Exception as e:
        if conn: conn.rollback()
        flash(f'Protocol Error: {str(e)}', 'danger')
        
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/admin/requests')
def admin_requests():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    
    cursor.execute("""
        SELECT r.*, u.username as operative_name, p.name as portfolio_name, a.symbol as asset_symbol
        FROM trade_requests r
        JOIN users u ON r.user_id = u.user_id
        JOIN portfolios p ON r.portfolio_id = p.portfolio_id
        JOIN assets a ON r.asset_id = a.asset_id
        WHERE r.status = 'PENDING'
        ORDER BY r.created_at DESC
    """)
    pending_requests = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return render_template('admin_requests.html', requests=pending_requests)

@app.route('/admin/requests/action/<int:request_id>/<action>')
def action_trade_request(request_id, action):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
    q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
    
    # 1. Fetch request details
    cursor.execute(f"SELECT * FROM trade_requests WHERE request_id = {q_mark}", (request_id,))
    req = cursor.fetchone()
    
    if not req or req['status'] != 'PENDING':
        flash("Invalid request code or already actioned.", "danger")
        return redirect(url_for('admin_requests'))
        
    if action == 'approve':
        try:
            # Commit to actual transaction ledger
            cursor.execute(f"""
                INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, price_per_unit, transaction_date)
                VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, CURRENT_TIMESTAMP)
            """, (req['portfolio_id'], req['asset_id'], req['transaction_type'], req['quantity'], req['requested_price']))
            
            # Update status
            cursor.execute(f"UPDATE trade_requests SET status = 'APPROVED', actioned_at = CURRENT_TIMESTAMP WHERE request_id = {q_mark}", (request_id,))
            
            # Audit log
            cursor.execute(f"INSERT INTO audit_logs (admin_id, action) VALUES ({q_mark}, {q_mark})", 
                           (session['user_id'], f"APPROVED trade request #{request_id} for user {req['user_id']}"))
            
            conn.commit()
            flash(f"Transaction protocol {request_id} APPROVED and executed.", "success")
        except Exception as e:
            if conn: conn.rollback()
            flash(f"Approval sequence failed: {str(e)}", "danger")
    else:
        # Rejected
        cursor.execute(f"UPDATE trade_requests SET status = 'REJECTED', actioned_at = CURRENT_TIMESTAMP WHERE request_id = {request_id}")
        cursor.execute(f"INSERT INTO audit_logs (admin_id, action) VALUES ({q_mark}, {q_mark})", 
                       (session['user_id'], f"REJECTED trade request #{request_id} for user {req['user_id']}"))
        conn.commit()
        flash(f"Transaction protocol {request_id} REJECTED.", "warning")

    cursor.close()
    conn.close()
    return redirect(url_for('admin_requests'))

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
        
        # Check if user exists
        q_mark = "?" if isinstance(conn, sqlite3.Connection) else "%s"
        cursor.execute(f"SELECT * FROM users WHERE username = {q_mark}", (username,))
        if cursor.fetchone():
            flash("Operative identity already registered.", "danger")
            return redirect(url_for('register'))
            
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        cursor.execute(f"INSERT INTO users (username, email, password_hash, role) VALUES ({q_mark}, {q_mark}, {q_mark}, 'user')", (username, email, password_hash))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Registration successful. You may now initiate handshake.", "success")
        return redirect(url_for('login'))
        
    return render_template('register.html')

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
                        
                        # DYNAMIC RE-FETCH: Reload tables if schema might have changed
                        if any(x in query.upper() for x in ['CREATE', 'DROP', 'ALTER', 'TRUNCATE']):
                            cursor.execute(table_query)
                            tables_raw = cursor.fetchall()
                            tables = []
                            for t in tables_raw:
                                table_name = t['name'] if isinstance(conn, sqlite3.Connection) else list(t.values())[0]
                                if table_name in ('sqlite_sequence', 'audit_logs'): continue
                                count_cursor = conn.cursor(dictionary=True) if not isinstance(conn, sqlite3.Connection) else conn.cursor()
                                try:
                                    count_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                                    row = count_cursor.fetchone()
                                    count = row['count'] if row else 0
                                    tables.append({'name': table_name, 'count': count})
                                except: pass
                                count_cursor.close()
                        else:
                            # Just refresh counts for performance
                            for t in tables:
                                count_cursor = conn.cursor()
                                try:
                                    count_cursor.execute(f"SELECT COUNT(*) as count FROM {t['name']}")
                                    row = count_cursor.fetchone()
                                    t['count'] = row['count'] if row else 0
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
