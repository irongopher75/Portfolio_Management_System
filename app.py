from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import sqlite3
import mysql.connector
import os
import random
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

DB_PATH = "portfolio.db"

def get_db_connection():
    # VIVA MODE: Hybrid connectivity to show socket handshakes vs local files
    host = os.getenv("MYSQL_HOST")
    if host:
        try:
            return mysql.connector.connect(
                host=host,
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user="root", # Aligned with student's local setup
                password="Achieve@2026",
                database=os.getenv("MYSQL_DB", "portfolio_db")
            )
        except Exception as e:
            print(f"Handshake failed: {e}. Falling back to node-local SQLite.")
            
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_cursor(conn):
    if isinstance(conn, sqlite3.Connection):
        return conn.cursor(), "?"
    return conn.cursor(dictionary=True), "%s"

import traceback
import sys

def get_telemetry(conn):
    start_time = time.time()
    # Simple handshake verification
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    latency_ms = int((time.time() - start_time) * 1000)
    
    is_mysql = not isinstance(conn, sqlite3.Connection)
    return {
        'protocol': 'TCP/IP (MySQL)' if is_mysql else 'File I/O (SQLite)',
        'host': 'localhost' if is_mysql else 'Local Node',
        'latency': latency_ms,
        'status': 'Synchronized' if is_mysql else 'Offline Node'
    }

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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    conn = get_db_connection()
    connection_meta = get_telemetry(conn)
    
    cursor, q = get_db_cursor(conn)
    cursor.execute(f"SELECT * FROM users WHERE user_id = {q}", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    # Optimized Data Fetching for Institutional High-Scale (10,000+ records)
    if user['role'] == 'admin':
        # Admin gets a summary view of all portfolios (No huge loops)
        cursor.execute("""
            SELECT p.*, u.username as owner_name 
            FROM portfolios p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.total_value DESC LIMIT 50
        """)
        portfolios = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f"SELECT * FROM holdings ORDER BY holding_id DESC LIMIT 50")
        holdings_raw = [dict(row) for row in cursor.fetchall()]
    else:
        # Standard user: Only fetch their specific holdings from the DB
        cursor.execute(f"SELECT * FROM portfolios WHERE user_id = {q}", (user_id,))
        portfolios = [dict(row) for row in cursor.fetchall()]
        
        my_p_ids = [str(p['portfolio_id']) for p in portfolios]
        if my_p_ids:
            p_id_str = ",".join(my_p_ids)
            cursor.execute(f"""
                SELECT h.*, a.symbol, a.name as asset_name, a.current_price
                FROM holdings h
                JOIN assets a ON h.asset_id = a.asset_id
                WHERE h.portfolio_id IN ({p_id_str})
            """)
            holdings_raw = [dict(row) for row in cursor.fetchall()]
        else:
            holdings_raw = []

    # Calculate Totals in SQL for efficiency
    cursor.execute(f"""
        SELECT 
            COALESCE(SUM(h.quantity * a.current_price), 0) as market_value,
            COALESCE(SUM(h.quantity * h.average_buy_price), 0) as cost_basis
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        JOIN portfolios p ON h.portfolio_id = p.portfolio_id
        WHERE {"1=1" if user['role'] == 'admin' else f"p.user_id = {user_id}"}
    """)
    totals = cursor.fetchone()
    total_market_value = float(totals['market_value'])
    total_investment_cost = float(totals['cost_basis'])

    # Map holdings to view models (Minimal processing)
    holdings = []
    for h in holdings_raw:
        qty, buy, curr = float(h['quantity']), float(h['average_buy_price']), float(h['current_price'])
        holdings.append({
            'symbol': h['symbol'],
            'name': h.get('asset_name', 'Unknown'),
            'quantity': qty,
            'average_buy_price': buy,
            'current_price': curr,
            'total_holding_value': qty * curr,
            'pl_percentage': ((curr - buy) / buy * 100) if buy > 0 else 0
        })

    # Portfolio Stats
    for p in portfolios:
        p['is_profit'] = float(p.get('total_value', 0)) >= (total_investment_cost / len(portfolios) if portfolios else 0)
        p['value_class'] = 'text-success' if p['is_profit'] else 'text-danger'

    # Market News & System Performance
    cursor.execute("SELECT * FROM assets ORDER BY symbol")
    assets_list = [dict(row) for row in cursor.fetchall()]
        
    cursor.execute("SELECT * FROM market_news ORDER BY published_at DESC LIMIT 10")
    news = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f"""
        SELECT r.*, a.symbol as symbol 
        FROM trade_requests r
        JOIN assets a ON r.asset_id = a.asset_id
        WHERE r.user_id = {q}
        ORDER BY r.created_at DESC LIMIT 10
    """, (user_id,))
    trade_requests = [dict(row) for row in cursor.fetchall()]

    performance = {
        'status': 'outperforming' if total_market_value >= total_investment_cost else 'underperforming',
        'latency': connection_meta['latency']
    }

    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                          user=user, portfolios=portfolios, holdings=holdings, 
                          transactions=transactions, assets=assets_list, 
                          news=news, performance=performance,
                          total_valuation=total_market_value,
                          total_pl=total_market_value - total_investment_cost,
                          trade_requests=trade_requests, 
                          telemetry=connection_meta)

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
    cursor = conn.cursor()
    
    cursor, q = get_db_cursor(conn)
    try:
        # PIVOT: Instead of direct transaction, we insert a trade request
        cursor.execute(f"""
            INSERT INTO trade_requests (user_id, portfolio_id, asset_id, transaction_type, quantity, requested_price, status) 
            VALUES ({q}, {q}, {q}, {q}, {q}, {q}, 'PENDING')
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
    cursor, q = get_db_cursor(conn)
    
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
    connection_meta = get_telemetry(conn)
    conn.close()
    return render_template('admin_requests.html', requests=pending_requests, telemetry=connection_meta)

@app.route('/admin/requests/action/<int:request_id>/<action>')
def action_trade_request(request_id, action):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    
    # 1. Fetch request details
    cursor.execute(f"SELECT * FROM trade_requests WHERE request_id = {q}", (request_id,))
    req = cursor.fetchone()
    
    if not req or req['status'] != 'PENDING':
        flash("Invalid request code or already actioned.", "danger")
        return redirect(url_for('admin_requests'))
        
    if action == 'approve':
        try:
            # Commit to actual transaction ledger
            cursor.execute(f"""
                INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, price_per_unit, transaction_date)
                VALUES ({q}, {q}, {q}, {q}, {q}, CURRENT_TIMESTAMP)
            """, (req['portfolio_id'], req['asset_id'], req['transaction_type'], req['quantity'], req['requested_price']))
            
            # Update status
            cursor.execute(f"UPDATE trade_requests SET status = 'APPROVED', actioned_at = CURRENT_TIMESTAMP WHERE request_id = {q}", (request_id,))
            
            # Audit log
            cursor.execute(f"INSERT INTO audit_logs (admin_id, action) VALUES ({q}, {q})", 
                           (session['user_id'], f"APPROVED trade request #{request_id} for user {req['user_id']}"))
            
            conn.commit()
            flash(f"Transaction protocol {request_id} APPROVED and executed.", "success")
        except Exception as e:
            if conn: conn.rollback()
            flash(f"Approval sequence failed: {str(e)}", "danger")
    else:
        # Rejected
        cursor.execute(f"UPDATE trade_requests SET status = 'REJECTED', actioned_at = CURRENT_TIMESTAMP WHERE request_id = {q}", (request_id,))
        cursor.execute(f"INSERT INTO audit_logs (admin_id, action) VALUES ({q}, {q})", 
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
        cursor, q = get_db_cursor(conn)
        cursor.execute(f"SELECT * FROM users WHERE username = {q}", (username,))
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
            
    conn = get_db_connection()
    connection_meta = get_telemetry(conn)
    conn.close()
    return render_template('login.html', telemetry=connection_meta)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor, q = get_db_cursor(conn)
        
        # Check if user exists
        cursor.execute(f"SELECT * FROM users WHERE username = {q}", (username,))
        if cursor.fetchone():
            flash("Operative identity already registered.", "danger")
            return redirect(url_for('register'))
            
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        cursor.execute(f"INSERT INTO users (username, email, password_hash, role) VALUES ({q}, {q}, {q}, 'user')", (username, email, password_hash))
        conn.commit()
        cursor.close()
        conn.close()
        
    conn = get_db_connection()
    connection_meta = get_telemetry(conn)
    conn.close()
    return render_template('register.html', telemetry=connection_meta)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_audit():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    cursor.execute("""
        SELECT l.*, u.username as admin_name
        FROM audit_logs l
        JOIN users u ON l.admin_id = u.user_id
        ORDER BY l.timestamp DESC
    """)
    logs = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT * FROM users WHERE user_id = {q}", (session['user_id'],))
    user = cursor.fetchone()
    
    cursor.close()
    connection_meta = get_telemetry(conn)
    conn.close()
    return render_template('admin.html', logs=logs, user=user, telemetry=connection_meta)

@app.route('/admin/sql-console', methods=['GET', 'POST'])
def sql_console():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    results = None
    columns = None
    error = None
    query = ""
    
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    is_mysql = not isinstance(conn, sqlite3.Connection)
    
    if request.method == 'POST' and not error:
        query = request.form.get('query', '').strip()
        if query:
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
                except Exception as err:
                    error = str(err)
    
    # DDL REFLECTION FIX: Fetch tables AFTER the query runs
    try:
        if is_mysql:
            table_query = "SHOW TABLES"
        else:
            table_query = "SELECT name as Tables_in_portfolio FROM sqlite_master WHERE type='table'"
            
        cursor.execute(table_query)
        tables_raw = cursor.fetchall()
        tables = []
        for t in tables_raw:
            table_name = t[next(iter(t))] # Get first column value
            if table_name in ('sqlite_sequence', 'audit_logs'): continue
            
            # Use specific connection for sub-query if needed, but here simple is better
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            cnt_row = cursor.fetchone()
            count = cnt_row['count'] if cnt_row else 0
            tables.append({'name': table_name, 'count': count})
    except Exception as e:
        tables = []
        if not error: error = f"Table refresh error: {str(e)}"
    
    cursor.close()
    conn.close()
    
    # Get user for header
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    cursor.execute(f"SELECT * FROM users WHERE user_id = {q}", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    connection_meta = get_telemetry(conn)
    conn.close()
    
    return render_template('sql_console.html', tables=tables, results=results, columns=columns, error=error, query=query, user=user, telemetry=connection_meta)

if __name__ == '__main__':
    # GLOBAL NODE MODE: Bind to 0.0.0.0 to allow incoming connections from other devices
    app.run(host='0.0.0.0', debug=True, port=5001)
