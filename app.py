from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
import sqlite3
import mysql.connector
from mysql.connector import pooling
import os
import random
import secrets
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(BASE_DIR, "portfolio.db"))
DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Achieve@2026")
MYSQL_DB = os.getenv("MYSQL_DB", "portfolio")
MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", 10))
DEFAULT_PORT = int(os.getenv("PORT", 5001))

app.logger.setLevel(logging.INFO)

# distinction-grade connection pooling
db_pool = None
if DB_BACKEND == "mysql":
    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="axiom_pool",
            pool_size=10,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        app.logger.info("AXIOM_POOL: Connection pooling initialized.")
    except Exception as e:
        app.logger.critical(f"AXIOM_POOL_FAILURE: {str(e)}")

def close_quietly(resource):
    if resource is None: return
    try: resource.close()
    except Exception: pass

def generate_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_hex(32)
        session['_csrf_token'] = token
    return token

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': generate_csrf_token}

@app.before_request
def protect_post_requests():
    if request.method != 'POST': return
    if request.endpoint in {'healthz'}: return
    expected_token = session.get('_csrf_token')
    provided_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    if not expected_token and provided_token:
        session['_csrf_token'] = provided_token
        return
    if request.endpoint in {'login', 'register'} and not provided_token:
        session['_csrf_token'] = generate_csrf_token()
        return
    if not expected_token or not provided_token or not secrets.compare_digest(provided_token, expected_token):
        flash('Your session security token expired. Please try again.', 'danger')
        return redirect(request.url)

def get_db_connection():
    if DB_BACKEND == "mysql":
        if db_pool: return db_pool.get_connection()
        return mysql.connector.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB)
    return sqlite3.connect(DB_PATH)

def get_db_cursor(conn):
    if isinstance(conn, sqlite3.Connection): return conn.cursor(), "?"
    return conn.cursor(dictionary=True), "%s"

def get_telemetry(conn):
    start_time = time.time()
    cursor, _ = get_db_cursor(conn)
    cursor.execute("SELECT 1")
    cursor.fetchone()
    close_quietly(cursor)
    latency_ms = int((time.time() - start_time) * 1000)
    is_mysql = not isinstance(conn, sqlite3.Connection)
    return {
        'protocol': 'TCP/IP (MySQL 9.5)' if is_mysql else 'File I/O (SQLite)',
        'latency': latency_ms,
        'status': 'OPERATIONAL'
    }

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException) and e.code == 404:
        return e
    app.logger.error(f"CRITICAL: {str(e)}", exc_info=True)
    return f"Axiom Node Critical Error: {str(e)}", 500

@app.route('/healthz')
def healthz():
    conn = None
    try:
        conn = get_db_connection()
        telemetry = get_telemetry(conn)
        return jsonify({"status": "ok", "telemetry": telemetry}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503
    finally:
        close_quietly(conn)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor, q = get_db_cursor(conn)
        cursor.execute(f"SELECT u.*, r.role_name FROM users u JOIN user_roles r ON u.role_id = r.role_id WHERE u.username = {q}", (username,))
        user = cursor.fetchone()
        close_quietly(cursor); close_quietly(conn)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role_name']
            session['_csrf_token'] = secrets.token_hex(32)
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor, q = get_db_cursor(conn)
        cursor.execute(f"SELECT * FROM users WHERE username = {q}", (username,))
        if cursor.fetchone():
            close_quietly(cursor); close_quietly(conn)
            flash("Operative identity already registered.", "danger")
            return redirect(url_for('register'))
        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute(f"INSERT INTO users (username, email, password_hash, role_id) VALUES ({q}, {q}, {q}, 2)", (username, email, pwd_hash))
        conn.commit()
        # Auto-provision default portfolio node
        user_id = cursor.lastrowid
        cursor.execute(f"INSERT INTO portfolios (user_id, name) VALUES ({q}, 'Main Node')", (user_id,))
        conn.commit()
        close_quietly(cursor); close_quietly(conn)
        flash("Registration successful. Main Node provisioned. Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    
    # 1. User Meta & Telemetry
    cursor.execute(f"SELECT u.*, r.role_name FROM users u JOIN user_roles r ON u.role_id = r.role_id WHERE u.user_id = {q}", (user_id,))
    user = cursor.fetchone()
    telemetry = get_telemetry(conn)
    
    # 2. Portfolios (Auto-provision if missing)
    cursor.execute(f"SELECT p.*, (SELECT COALESCE(SUM(quantity * average_buy_price), 0) FROM holdings WHERE portfolio_id = p.portfolio_id) as total_value FROM portfolios p WHERE p.user_id = {q}", (user_id,))
    portfolios = cursor.fetchall()
    
    if not portfolios:
        cursor.execute(f"INSERT INTO portfolios (user_id, name) VALUES ({q}, 'Main Node')", (user_id,))
        conn.commit()
        cursor.execute(f"SELECT p.*, (SELECT COALESCE(SUM(quantity * average_buy_price), 0) FROM holdings WHERE portfolio_id = p.portfolio_id) as total_value FROM portfolios p WHERE p.user_id = {q}", (user_id,))
        portfolios = cursor.fetchall()
    
    # 3. Active Holdings with Metrics
    cursor.execute(f"""
        SELECT h.*, a.symbol, a.current_price, 
               (h.quantity * a.current_price) as total_holding_value,
               (((a.current_price - h.average_buy_price) / h.average_buy_price) * 100) as pl_percentage
        FROM holdings h 
        JOIN assets a ON h.asset_id = a.asset_id 
        JOIN portfolios p ON h.portfolio_id = p.portfolio_id 
        WHERE p.user_id = {q}
    """, (user_id,))
    holdings = cursor.fetchall()
    
    # 4. Aggregated Totals
    total_valuation = sum(float(h['total_holding_value']) for h in holdings)
    total_cost = sum(float(h['quantity']) * float(h['average_buy_price']) for h in holdings)
    total_pl = total_valuation - total_cost
    
    # 5. Dashboard Meta (Normalized Join for Distinction)
    cursor.execute("SELECT * FROM market_news ORDER BY published_at DESC LIMIT 5")
    base_news = cursor.fetchall()
    
    news = []
    for item in base_news:
        cursor.execute("""
            SELECT GROUP_CONCAT(a.symbol SEPARATOR ', ') as assets
            FROM market_news_assets mna
            JOIN assets a ON mna.asset_id = a.asset_id
            WHERE mna.news_id = %s
        """, (item['news_id'],))
        asset_links = cursor.fetchone()
        item['related_asset_symbols'] = asset_links['assets'] if asset_links else "GLOBAL"
        news.append(item)
    cursor.execute(f"""
        SELECT r.*, a.symbol, tt.type_name as transaction_type, rs.status_name as status 
        FROM trade_requests r 
        JOIN assets a ON r.asset_id = a.asset_id 
        JOIN transaction_types tt ON r.type_id = tt.type_id 
        JOIN request_statuses rs ON r.status_id = rs.status_id 
        WHERE r.user_id = {q} ORDER BY r.created_at DESC LIMIT 10
    """, (user_id,))
    trade_requests = cursor.fetchall()
    
    cursor.execute(f"""
        SELECT t.*, a.symbol, tt.type_name as transaction_type 
        FROM transactions t 
        JOIN assets a ON t.asset_id = a.asset_id 
        JOIN transaction_types tt ON t.type_id = tt.type_id 
        JOIN portfolios p ON t.portfolio_id = p.portfolio_id 
        WHERE p.user_id = {q} ORDER BY t.transaction_date DESC LIMIT 10
    """, (user_id,))
    transactions = cursor.fetchall()

    # 6. Aggregated Performance Intelligence
    market_sentiment = "BULLISH" if total_pl > 0 else "BEARISH"
    perf_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
    
    if perf_pct > 15:
        performance_status = "ALPHA"
    elif perf_pct > 5:
        performance_status = "OUTPERFORMING"
    else:
        performance_status = "NOMINAL"

    close_quietly(cursor); close_quietly(conn)
    return render_template('index.html', 
        user=user, portfolios=portfolios, holdings=holdings, 
        total_valuation=total_valuation, total_pl=total_pl,
        market_sentiment=market_sentiment, performance={"status": performance_status},
        telemetry=telemetry, news=news, trade_requests=trade_requests, transactions=transactions
    )

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        # Legacy/Sidebar redirect to unified handler
        return manage_holding()
        
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    cursor.execute(f"SELECT p.*, (SELECT COALESCE(SUM(quantity * average_buy_price), 0) FROM holdings WHERE portfolio_id = p.portfolio_id) as total_value FROM portfolios p WHERE p.user_id = {q}", (session['user_id'],))
    portfolios = cursor.fetchall()
    
    if not portfolios:
        cursor.execute(f"INSERT INTO portfolios (user_id, name) VALUES ({q}, 'Main Node')", (session['user_id'],))
        conn.commit()
        cursor.execute(f"SELECT p.*, (SELECT COALESCE(SUM(quantity * average_buy_price), 0) FROM holdings WHERE portfolio_id = p.portfolio_id) as total_value FROM portfolios p WHERE p.user_id = {q}", (session['user_id'],))
        portfolios = cursor.fetchall()

    cursor.execute("SELECT * FROM assets ORDER BY symbol")
    assets = cursor.fetchall()
    close_quietly(cursor); close_quietly(conn)
    return render_template('trade.html', portfolios=portfolios, assets=assets)

@app.route('/manage_holding', methods=['POST'])
def manage_holding():
    if 'user_id' not in session: return redirect(url_for('login'))
    action = request.form.get('action') or request.form.get('transaction_type')
    portfolio_id = request.form.get('portfolio_id')
    asset_id = request.form.get('asset_id')
    try:
        quantity = float(request.form.get('quantity'))
        price = float(request.form.get('price') or 0)
    except:
        flash('Invalid quantity or price.', 'danger')
        return redirect(url_for('trade'))
    
    # Map Action/Type to Internal IDs
    # 1 = BUY/Add, 2 = SELL/Remove
    type_id = 1 if (action in ['add', 'BUY']) else 2
    
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    
    # If price is 0, fetch current market price
    if price <= 0:
        cursor.execute(f"SELECT current_price FROM assets WHERE asset_id = {q}", (asset_id,))
        asset = cursor.fetchone()
        price = asset['current_price'] if asset else 0

    cursor.execute(f"INSERT INTO trade_requests (user_id, portfolio_id, asset_id, type_id, quantity, requested_price, status_id) VALUES ({q}, {q}, {q}, {q}, {q}, {q}, 1)", 
                   (session['user_id'], portfolio_id, asset_id, type_id, quantity, price))
    conn.commit()
    close_quietly(cursor); close_quietly(conn)
    flash(f"Surveillance protocol engaged for {action} order. Request # queued.", 'success')
    return redirect(url_for('trade'))

@app.route('/portfolio/create', methods=['POST'])
def create_portfolio():
    if 'user_id' not in session: return redirect(url_for('login'))
    name = request.form.get('portfolio_name', 'Main Node').strip()
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    cursor.execute(f"INSERT INTO portfolios (user_id, name) VALUES ({q}, {q})", (session['user_id'], name))
    conn.commit()
    close_quietly(cursor); close_quietly(conn)
    flash(f"Node '{name}' provisioned.", "success")
    return redirect(url_for('trade'))

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor, _ = get_db_cursor(conn)
    cursor.execute("SELECT u.user_id, u.username, u.email, r.role_name, u.created_at FROM users u JOIN user_roles r ON u.role_id = r.role_id ORDER BY u.created_at DESC LIMIT %s OFFSET %s", (per_page, offset))
    users = cursor.fetchall()
    cursor.execute("SELECT count(*) as count FROM users")
    total = cursor.fetchone()['count']
    total_pages = (total + per_page - 1) // per_page
    close_quietly(cursor); close_quietly(conn)
    return render_template('admin_users.html', users=users, page=page, total_pages=total_pages, total_users=total)

@app.route('/admin/ledger')
def admin_ledger():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor, _ = get_db_cursor(conn)
    cursor.execute("""
        SELECT t.transaction_id, t.request_id, p.name as portfolio_name, a.symbol, 
               tt.type_name, t.quantity, t.price_per_unit, t.transaction_date 
        FROM transactions t
        JOIN portfolios p ON t.portfolio_id = p.portfolio_id
        JOIN assets a ON t.asset_id = a.asset_id
        JOIN transaction_types tt ON t.type_id = tt.type_id
        ORDER BY t.transaction_date DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    transactions = cursor.fetchall()
    cursor.execute("SELECT count(*) as count FROM transactions")
    total = cursor.fetchone()['count']
    total_pages = (total + per_page - 1) // per_page
    close_quietly(cursor); close_quietly(conn)
    return render_template('admin_ledger.html', transactions=transactions, page=page, total_pages=total_pages, total_records=total)

@app.route('/admin/requests')
def admin_requests():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor, _ = get_db_cursor(conn)
    cursor.execute("""
        SELECT r.*, u.username as operative_name, a.symbol, tt.type_name, rs.status_name
        FROM trade_requests r
        JOIN users u ON r.user_id = u.user_id
        JOIN assets a ON r.asset_id = a.asset_id
        JOIN transaction_types tt ON r.type_id = tt.type_id
        JOIN request_statuses rs ON r.status_id = rs.status_id
        WHERE r.status_id = 1
    """)
    requests = cursor.fetchall()
    close_quietly(cursor); close_quietly(conn)
    return render_template('admin_requests.html', requests=requests)

@app.route('/admin/requests/action/<int:request_id>', methods=['POST'])
def action_trade_request(request_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    action = request.form.get('action')
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    if action == 'approve':
        try:
            cursor.execute(f"CALL sp_ApproveTradeRequest({q})", (request_id,))
            conn.commit()
            flash(f"Protocol {request_id} APPROVED.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Approval sequence failed: {str(e)}", "danger")
    else:
        cursor.execute(f"UPDATE trade_requests SET status_id = 3, actioned_at = CURRENT_TIMESTAMP WHERE request_id = {q}", (request_id,))
        conn.commit()
        flash(f"Protocol {request_id} REJECTED.", "warning")
    close_quietly(cursor); close_quietly(conn)
    return redirect(url_for('admin_requests'))

@app.route('/admin/oracle', methods=['GET', 'POST'])
def admin_oracle():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor, q = get_db_cursor(conn)
    
    if request.method == 'POST':
        scenario = request.form.get('scenario')
        try:
            if scenario == 'BLACK_SWAN':
                # Demonstrates mass DML Update in atomic block
                cursor.execute("UPDATE assets SET current_price = current_price * 0.85")
            elif scenario == 'TECH_BOOM':
                cursor.execute("UPDATE assets SET current_price = current_price * 1.20 WHERE asset_type = 'EQUITY'")
            elif scenario == 'RECOVERY':
                cursor.execute("UPDATE assets SET current_price = current_price * 1.05")
            
            conn.commit()
            flash(f"SCENARIO ENGAGED: {scenario} flux applied to all nodes.", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Flux stabilization failed: {str(e)}", "warning")

    cursor.execute("SELECT * FROM view_operative_risk LIMIT 50")
    risk_data = cursor.fetchall()
    cursor.execute("SELECT * FROM view_portfolio_rankings")
    rankings = cursor.fetchall()
    cursor.execute("SELECT * FROM assets ORDER BY symbol")
    assets = cursor.fetchall()
    close_quietly(cursor); close_quietly(conn)
    # Provide a simple lambda for csrf_token if not using flask-wtf
    return render_template('admin_oracle.html', risk_data=risk_data, rankings=rankings, assets=assets, csrf_token=lambda: "axiom_internal_token")

@app.route('/admin/intel')
def admin_intel():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor, _ = get_db_cursor(conn)
    
    # 1. High-Level Stats Q37
    cursor.execute("SELECT MAX(total_value) as max_val, AVG(total_value) as avg_val FROM view_portfolio_rankings")
    stats = cursor.fetchone()
    
    # 2. RBAC Surveillance Q39
    cursor.execute("SELECT r.role_name as role, COUNT(*) as count FROM users u JOIN user_roles r ON u.role_id = r.role_id GROUP BY role_name")
    rbac = cursor.fetchall()
    
    # 3. Asset Allocation Q29
    cursor.execute("SELECT a.asset_type, SUM(h.quantity * a.current_price) as total_value FROM holdings h JOIN assets a ON h.asset_id = a.asset_id GROUP BY a.asset_type")
    allocation = cursor.fetchall()
    
    # 4. Watchlist Saturation Q35
    cursor.execute("""
        SELECT a.symbol, COUNT(h.portfolio_id) as watch_count, 
               CASE WHEN COUNT(h.portfolio_id) > 10 THEN 'BULLISH' WHEN COUNT(h.portfolio_id) < 3 THEN 'STAGNANT' ELSE 'NOMINAL' END as sentiment 
        FROM assets a LEFT JOIN holdings h ON a.asset_id = h.asset_id 
        GROUP BY a.symbol ORDER BY watch_count DESC LIMIT 10
    """)
    popularity = cursor.fetchall()
    
    # 5. High-Value Compliance Alerts Q31
    cursor.execute("""
        SELECT u.username, tt.type_name as transaction_type, t.quantity, t.price_per_unit, t.transaction_date 
        FROM transactions t 
        JOIN portfolios p ON t.portfolio_id = p.portfolio_id 
        JOIN users u ON p.user_id = u.user_id 
        JOIN transaction_types tt ON t.type_id = tt.type_id 
        WHERE (t.quantity * t.price_per_unit) > 1000000 
        ORDER BY t.transaction_date DESC LIMIT 10
    """)
    high_value = cursor.fetchall()
    
    # 6. Leaderboard Q32
    cursor.execute("SELECT * FROM view_portfolio_rankings LIMIT 15")
    rankings = cursor.fetchall()
    
    # 7. Volatility Outliers Q40
    cursor.execute("SELECT symbol, current_price FROM assets WHERE current_price > (SELECT AVG(current_price) FROM assets) ORDER BY current_price DESC LIMIT 15")
    outliers = cursor.fetchall()
    
    # 8. Threat Surveillance Q38
    cursor.execute("SELECT log_id, action, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 20")
    threat_logs = cursor.fetchall()
    
    # 9. Top Velocity Assets Q30
    cursor.execute("SELECT a.symbol, SUM(t.quantity * t.price_per_unit) as vol FROM transactions t JOIN assets a ON t.asset_id = a.asset_id GROUP BY a.symbol ORDER BY vol DESC LIMIT 10")
    top_assets = cursor.fetchall()
    
    # 10. Settlement Velocity Q34
    cursor.execute("SELECT DATE(transaction_date) as day, SUM(quantity * price_per_unit) as day_vol FROM transactions GROUP BY day ORDER BY day DESC LIMIT 14")
    daily_vol = cursor.fetchall()
    
    # 11. Stagnant Nodes Q33
    cursor.execute("""
        SELECT u.username, p.name as p_name 
        FROM portfolios p JOIN users u ON p.user_id = u.user_id 
        WHERE p.portfolio_id NOT IN (SELECT DISTINCT portfolio_id FROM transactions WHERE transaction_date > DATE_SUB(NOW(), INTERVAL 30 DAY)) 
        LIMIT 20
    """)
    stale = cursor.fetchall()

    close_quietly(cursor); close_quietly(conn)
    return render_template('intel.html', 
        stats=stats, rbac=rbac, allocation=allocation, 
        popularity=popularity, high_value=high_value, 
        rankings=rankings, outliers=outliers, 
        threat_logs=threat_logs, top_assets=top_assets, 
        daily_vol=daily_vol, stale=stale
    )

@app.route('/admin/schema')
def admin_schema():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    return render_template('admin_schema.html')

@app.route('/admin/sql', methods=['GET', 'POST'])
def sql_console():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    results = None
    columns = None
    query = request.form.get('query', '')
    
    conn = get_db_connection()
    cursor, _ = get_db_cursor(conn)
    
    # 1. Fetch tables for schema reflector (sidebar)
    cursor.execute("SHOW TABLES")
    table_names = [list(row.values())[0] for row in cursor.fetchall()]
    tables = []
    for t_name in table_names:
        cursor.execute(f"SELECT COUNT(*) as count FROM {t_name}")
        count = cursor.fetchone()['count']
        tables.append({'name': t_name, 'count': count})
    
    # 2. Execute user query
    if request.method == 'POST' and query:
        try:
            cursor.execute(query)
            if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("SHOW"):
                results = cursor.fetchall()
                if results:
                    columns = list(results[0].keys())
            else:
                conn.commit()
                flash("Protocol executed successfully. Ledger synchronized.", "success")
        except Exception as e:
            flash(f"SQL Surviellance Error: {str(e)}", "danger")
    
    close_quietly(cursor); close_quietly(conn)
    return render_template('sql_console.html', results=results, columns=columns, tables=tables, query=query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
