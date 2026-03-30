from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import mysql.connector
import os
import random
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

def get_db_connection():
    ssl_ca = os.environ.get('MYSQL_SSL_CA')
    db_config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DB', 'portfolio_manager')
    }
    
    # PlanetScale requires SSL
    if ssl_ca and os.path.exists(ssl_ca):
        db_config['ssl_ca'] = ssl_ca
        db_config['ssl_verify_cert'] = True
        
    return mysql.connector.connect(**db_config)


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if user['role'] == 'admin':
        # Admin visibility
        cursor.execute("""
            SELECT p.*, u.username as owner_name 
            FROM portfolios p
            JOIN users u ON p.user_id = u.user_id
        """)
        portfolios = cursor.fetchall()
        
        cursor.execute("""
            SELECT t.*, a.symbol as symbol 
            FROM transactions t
            JOIN assets a ON t.asset_id = a.asset_id
            ORDER BY t.transaction_date DESC LIMIT 50
        """)
        transactions = cursor.fetchall()
        watchlist = None
        watchlist_items = []
    else:
        # Standard user
        cursor.execute("SELECT * FROM portfolios WHERE user_id = %s", (user_id,))
        portfolios = cursor.fetchall()
        
        cursor.execute("""
            SELECT t.*, a.symbol as symbol 
            FROM transactions t
            JOIN assets a ON t.asset_id = a.asset_id
            JOIN portfolios p ON t.portfolio_id = p.portfolio_id
            WHERE p.user_id = %s
            ORDER BY t.transaction_date DESC LIMIT 15
        """, (user_id,))
        transactions = cursor.fetchall()
        
        cursor.execute("SELECT * FROM watchlists WHERE user_id = %s", (user_id,))
        watchlist = cursor.fetchone()
        watchlist_items = []
        if watchlist:
            cursor.execute("""
                SELECT a.* 
                FROM watchlist_items wi
                JOIN assets a ON wi.asset_id = a.asset_id
                WHERE wi.watchlist_id = %s
            """, (watchlist['watchlist_id'],))
            watchlist_items = cursor.fetchall()

    # Get holdings
    cursor.execute("""
        SELECT h.*, p.name as portfolio_name, a.symbol, a.name as asset_name, a.current_price
        FROM holdings h
        JOIN portfolios p ON h.portfolio_id = p.portfolio_id
        JOIN assets a ON h.asset_id = a.asset_id
    """)
    holdings_raw = cursor.fetchall()
    
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
    assets_list = cursor.fetchall()
    for a in assets_list:
        a['asset_id'] = a['asset_id'] # MySQL IDs are ints
        
    cursor.execute("SELECT * FROM market_news LIMIT 5")
    news = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    wl_dict = None
    if watchlist:
        wl_dict = {'name': watchlist['name'], 'asset_details': watchlist_items}
        
    return render_template('index.html', user=user, portfolios=portfolios, holdings=holdings, transactions=transactions, assets=assets_list, news=news, watchlist=wl_dict, performance=performance)

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
    
    try:
        cursor.execute("""
            INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, price_per_unit) 
            VALUES (%s, %s, %s, %s, %s)
        """, (portfolio_id, asset_id, transaction_type, quantity, price))
        conn.commit()
        flash('Transaction recorded successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
        
    if session.get('role') == 'admin':
        cursor.execute("INSERT INTO audit_logs (admin_id, action) VALUES (%s, %s)", 
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
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
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
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.*, u.username as admin_name
        FROM audit_logs l
        JOIN users u ON l.admin_id = u.user_id
        ORDER BY l.timestamp DESC
    """)
    logs = cursor.fetchall()
    
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
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
    cursor = conn.cursor(dictionary=True)
    
    # Get tables for sidebar
    try:
        cursor.execute("SHOW TABLES")
        tables_raw = cursor.fetchall()
        tables = []
        for t in tables_raw:
            table_name = list(t.values())[0]
            # Get count for each table
            count_cursor = conn.cursor()
            count_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = count_cursor.fetchone()
            count = row[0] if row else 0
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
                        results = cursor.fetchall()
                        columns = cursor.column_names
                    else:
                        conn.commit()
                        results = [{"Success": f"Query executed. Rows affected: {cursor.rowcount}"}]
                        columns = ["Status"]
                        # Refresh table counts
                        for t in tables:
                            count_cursor = conn.cursor()
                            try:
                                count_cursor.execute(f"SELECT COUNT(*) FROM {t['name']}")
                                t['count'] = count_cursor.fetchone()[0]
                            except: pass
                            count_cursor.close()
                except Exception as err:
                    error = str(err)
    
    cursor.close()
    conn.close()
    
    # Get user for header
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('sql_console.html', tables=tables, results=results, columns=columns, error=error, query=query, user=user)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
