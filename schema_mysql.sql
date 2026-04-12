-- =============================================================================
-- AXIOM TERMINAL | DATABASE SCHEMA (MySQL)
-- Designed for Academic Evaluation & Institutional Portfolio Management
-- =============================================================================

-- PRE-PROCESSING: Drop tables in reverse order of dependency to maintain referential integrity
DROP TABLE IF EXISTS watchlist_items;
DROP TABLE IF EXISTS watchlists;
DROP TABLE IF EXISTS market_news;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS users;

-- 1. USER AUTHENTICATION & RBAC
-- Stores verified users with hashed credentials and role-based access control
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ASSETS (STOCKS/CRYPTO)
-- Catalog of tradeable instruments with live price synchronization
CREATE TABLE assets (
    asset_id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    current_price DECIMAL(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 3. PORTFOLIOS
-- Logical containers for holdings, owned by users
CREATE TABLE portfolios (
    portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    total_value DECIMAL(15, 2) DEFAULT 0.00,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. HOLDINGS (Aggregated State)
-- Tracks the current quantity and average cost basis per asset per portfolio
-- Normalized via uniqueness constraint on (portfolio_id, asset_id)
CREATE TABLE holdings (
    holding_id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    asset_id INT NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL DEFAULT 0.0000,
    average_buy_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, asset_id)
);

-- 5. TRANSACTIONS (Immutable Ledger)
-- Event-sourced record of all trades. Triggers react to these inserts.
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    asset_id INT NOT NULL,
    transaction_type ENUM('BUY', 'SELL') NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    price_per_unit DECIMAL(15, 2) NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

-- 6. WATCHLISTS (Feature Layer)
CREATE TABLE watchlists (
    watchlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE watchlist_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    watchlist_id INT NOT NULL,
    asset_id INT NOT NULL,
    FOREIGN KEY(watchlist_id) REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    UNIQUE(watchlist_id, asset_id)
);

-- 7. AUDIT & SURVEILLANCE
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 8. MARKET TELEMETRY
CREATE TABLE market_news (
    news_id INT AUTO_INCREMENT PRIMARY KEY,
    headline VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    related_asset_symbols VARCHAR(255),
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- DATABASE LOGIC (TRIGGERS)
-- Automated data integrity and aggregated calculations implemented at the DB level
-- =============================================================================

DELIMITER //

-- TRIGGER: Synchronize Holdings on BUY
-- Implements moving average cost basis calculation automatically.
CREATE TRIGGER after_buy_insert
AFTER INSERT ON transactions
FOR EACH ROW
BEGIN
    IF NEW.transaction_type = 'BUY' THEN
        INSERT INTO holdings (portfolio_id, asset_id, quantity, average_buy_price)
        VALUES (NEW.portfolio_id, NEW.asset_id, NEW.quantity, NEW.price_per_unit)
        ON DUPLICATE KEY UPDATE
            average_buy_price = ((holdings.quantity * holdings.average_buy_price) + (NEW.quantity * NEW.price_per_unit)) / (holdings.quantity + NEW.quantity),
            quantity = holdings.quantity + NEW.quantity;
    END IF;
END //

-- TRIGGER: Synchronize Holdings on SELL
-- Reduces inventory and prunes empty holdings to keep the table clean.
CREATE TRIGGER after_sell_insert
AFTER INSERT ON transactions
FOR EACH ROW
BEGIN
    IF NEW.transaction_type = 'SELL' THEN
        UPDATE holdings
        SET quantity = quantity - NEW.quantity
        WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id;

        -- Automatic cleanup of zero/negligible positions
        DELETE FROM holdings
        WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id AND quantity <= 0.0001;
    END IF;
END //

-- TRIGGER: Aggregate Portfolio Value (Update)
-- Ensures portfolios table always reflects the real-time sum of holdings * prices.
CREATE TRIGGER update_portfolio_val_after_holding_update
AFTER UPDATE ON holdings
FOR EACH ROW
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.00)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = NEW.portfolio_id
    )
    WHERE portfolio_id = NEW.portfolio_id;
END //

CREATE TRIGGER update_portfolio_val_after_holding_insert
AFTER INSERT ON holdings
FOR EACH ROW
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.00)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = NEW.portfolio_id
    )
    WHERE portfolio_id = NEW.portfolio_id;
END //

CREATE TRIGGER update_portfolio_val_after_holding_delete
AFTER DELETE ON holdings
FOR EACH ROW
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.00)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = OLD.portfolio_id
    )
    WHERE portfolio_id = OLD.portfolio_id;
END //

DELIMITER ;
