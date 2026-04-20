-- =============================================================================
-- AXIOM TERMINAL | DISTINCTION-GRADE DBMS SCHEMA (MySQL)
-- Designed for Academic Distinction & Institutional Precision
-- =============================================================================

-- PRE-PROCESSING: Drop in strict reverse dependency order
DROP VIEW IF EXISTS view_portfolio_rankings;
DROP VIEW IF EXISTS view_operative_risk;
DROP PROCEDURE IF EXISTS sp_ApproveTradeRequest;
DROP TABLE IF EXISTS market_news_assets;
DROP TABLE IF EXISTS market_news;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS trade_requests;
DROP TABLE IF EXISTS watchlist_items;
DROP TABLE IF EXISTS watchlists;
DROP TABLE IF EXISTS request_statuses;
DROP TABLE IF EXISTS transaction_types;
DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS global_config;

-- 1. LOOKUP TABLES (Normalization: Replacing ENUMs for Scalability)
CREATE TABLE user_roles (
    role_id INT PRIMARY KEY,
    role_name VARCHAR(20) UNIQUE NOT NULL
);
INSERT INTO user_roles VALUES (1, 'admin'), (2, 'user');

CREATE TABLE transaction_types (
    type_id INT PRIMARY KEY,
    type_name VARCHAR(10) UNIQUE NOT NULL
);
INSERT INTO transaction_types VALUES (1, 'BUY'), (2, 'SELL');

CREATE TABLE request_statuses (
    status_id INT PRIMARY KEY,
    status_name VARCHAR(20) UNIQUE NOT NULL
);
INSERT INTO request_statuses VALUES (1, 'PENDING'), (2, 'APPROVED'), (3, 'REJECTED');

-- 2. USER AUTHENTICATION & RBAC
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES user_roles(role_id)
);

-- 3. ASSETS (STOCKS/CRYPTO)
CREATE TABLE assets (
    asset_id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    current_price DECIMAL(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_asset_price CHECK (current_price >= 0)
);

-- 4. PORTFOLIOS
CREATE TABLE portfolios (
    portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    total_value DECIMAL(15, 2) DEFAULT 0.00,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 5. HOLDINGS (Weak Entity modeled via Composite PK)
CREATE TABLE holdings (
    portfolio_id INT NOT NULL,
    asset_id INT NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL DEFAULT 0.0000,
    average_buy_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (portfolio_id, asset_id),
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    CONSTRAINT chk_quantity CHECK (quantity >= 0)
);

-- 6. SURVEILLANCE PROTOCOL (Intent Layer)
CREATE TABLE trade_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    portfolio_id INT NOT NULL,
    asset_id INT NOT NULL,
    type_id INT NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    requested_price DECIMAL(15, 2) NOT NULL,
    status_id INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actioned_at TIMESTAMP NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    FOREIGN KEY(type_id) REFERENCES transaction_types(type_id),
    FOREIGN KEY(status_id) REFERENCES request_statuses(status_id),
    CONSTRAINT chk_req_qty CHECK (quantity > 0),
    CONSTRAINT chk_req_price CHECK (requested_price > 0)
);

-- 7. TRANSACTIONS (Immutable Ledger)
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT UNIQUE,
    portfolio_id INT NOT NULL,
    asset_id INT NOT NULL,
    type_id INT NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    price_per_unit DECIMAL(15, 2) NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(request_id) REFERENCES trade_requests(request_id) ON DELETE SET NULL,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    FOREIGN KEY(type_id) REFERENCES transaction_types(type_id),
    CONSTRAINT chk_tx_qty CHECK (quantity > 0)
);

-- 8. WATCHLISTS
CREATE TABLE watchlists (
    watchlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE watchlist_items (
    watchlist_id INT NOT NULL,
    asset_id INT NOT NULL,
    PRIMARY KEY (watchlist_id, asset_id),
    FOREIGN KEY(watchlist_id) REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

-- 9. AUDIT & NEWS
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE market_news (
    news_id INT AUTO_INCREMENT PRIMARY KEY,
    headline VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE market_news_assets (
    news_id INT NOT NULL,
    asset_id INT NOT NULL,
    PRIMARY KEY (news_id, asset_id),
    FOREIGN KEY(news_id) REFERENCES market_news(news_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

-- 10. GLOBAL SYSTEM CONFIGURATION
CREATE TABLE global_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value VARCHAR(255) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT INTO global_config (config_key, config_value) VALUES 
('MARKET_STATUS', 'OPEN'), 
('MAX_CONCENTRATION_THRESHOLD', '0.50'), 
('SYSTEM_NODE_ID', 'AXIOM-VIVA-DISTINCTION');

-- =============================================================================
-- PROCEDURAL LOGIC
-- =============================================================================

DELIMITER //

CREATE PROCEDURE sp_ApproveTradeRequest(IN in_request_id INT, IN in_admin_id INT)
BEGIN
    DECLARE v_uid, v_pid, v_aid, v_tid INT;
    DECLARE v_qty, v_price DECIMAL(15,4);
    
    START TRANSACTION;
    
    SELECT user_id, portfolio_id, asset_id, type_id, quantity, requested_price 
    INTO v_uid, v_pid, v_aid, v_tid, v_qty, v_price
    FROM trade_requests 
    WHERE request_id = in_request_id AND status_id = 1
    FOR UPDATE;
    
    IF v_uid IS NULL THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid or already processed request.';
    END IF;
    
    INSERT INTO transactions (request_id, portfolio_id, asset_id, type_id, quantity, price_per_unit)
    VALUES (in_request_id, v_pid, v_aid, v_tid, v_qty, v_price);
    
    UPDATE trade_requests SET status_id = 2, actioned_at = CURRENT_TIMESTAMP WHERE request_id = in_request_id;
    
    INSERT INTO audit_logs (admin_id, action) 
    VALUES (in_admin_id, CONCAT('Approved trade request #', in_request_id));
    
    COMMIT;
END //

DELIMITER ;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

DELIMITER //

CREATE TRIGGER after_trade_insert
AFTER INSERT ON transactions
FOR EACH ROW
BEGIN
    IF NEW.type_id = 1 THEN -- BUY
        INSERT INTO holdings (portfolio_id, asset_id, quantity, average_buy_price)
        VALUES (NEW.portfolio_id, NEW.asset_id, NEW.quantity, NEW.price_per_unit)
        ON DUPLICATE KEY UPDATE
            average_buy_price = ((holdings.quantity * holdings.average_buy_price) + (NEW.quantity * NEW.price_per_unit)) / (holdings.quantity + NEW.quantity),
            quantity = holdings.quantity + NEW.quantity;
    ELSEIF NEW.type_id = 2 THEN -- SELL
        UPDATE holdings
        SET quantity = quantity - NEW.quantity
        WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id;

        DELETE FROM holdings
        WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id AND quantity <= 0.0001;
    END IF;
END //

CREATE TRIGGER trig_refresh_portfolio_val
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

DELIMITER ;

-- =============================================================================
-- ANALYTICS (VIEWS)
-- =============================================================================

CREATE OR REPLACE VIEW view_portfolio_rankings AS
SELECT 
    u.username,
    p.name as portfolio_name,
    p.total_value,
    RANK() OVER (ORDER BY p.total_value DESC) as global_rank,
    DENSE_RANK() OVER (PARTITION BY u.user_id ORDER BY p.total_value DESC) as user_internal_rank
FROM portfolios p
JOIN users u ON p.user_id = u.user_id;

CREATE OR REPLACE VIEW view_operative_risk AS
SELECT 
    u.username,
    p.name as portfolio,
    a.symbol as asset,
    h.quantity,
    (h.quantity * a.current_price) as position_value,
    ((h.quantity * a.current_price) / NULLIF(p.total_value, 0)) as concentration_pct,
    CASE 
        WHEN ((h.quantity * a.current_price) / NULLIF(p.total_value, 0)) > 0.40 THEN 'CRITICAL'
        ELSE 'STABLE'
    END as risk_profile
FROM holdings h
JOIN assets a ON h.asset_id = a.asset_id
JOIN portfolios p ON h.portfolio_id = p.portfolio_id
JOIN users u ON p.user_id = u.user_id;
