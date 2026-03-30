PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS watchlist_items;
DROP TABLE IF EXISTS watchlists;
DROP TABLE IF EXISTS market_news;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'user')) DEFAULT 'user'
);

CREATE TABLE assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    current_price REAL NOT NULL
);

CREATE TABLE portfolios (
    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    total_value REAL DEFAULT 0.0,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE holdings (
    holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 0.0,
    average_buy_price REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    UNIQUE(portfolio_id, asset_id)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('BUY', 'SELL')) NOT NULL,
    quantity REAL NOT NULL,
    price_per_unit REAL NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

CREATE TABLE watchlists (
    watchlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE watchlist_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    FOREIGN KEY(watchlist_id) REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    UNIQUE(watchlist_id, asset_id)
);

CREATE TABLE audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE market_news (
    news_id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    source TEXT NOT NULL,
    related_asset_symbols TEXT
);


-- TRIGGERS
-- Handle BUY transaction (Insert/Update Holding)
CREATE TRIGGER after_buy
AFTER INSERT ON transactions
WHEN NEW.transaction_type = 'BUY'
BEGIN
    INSERT INTO holdings (portfolio_id, asset_id, quantity, average_buy_price)
    VALUES (NEW.portfolio_id, NEW.asset_id, NEW.quantity, NEW.price_per_unit)
    ON CONFLICT(portfolio_id, asset_id) DO UPDATE SET
        average_buy_price = ((quantity * average_buy_price) + (NEW.quantity * NEW.price_per_unit)) / (quantity + NEW.quantity),
        quantity = quantity + NEW.quantity;
END;

-- Handle SELL transaction (Update Holding)
CREATE TRIGGER after_sell
AFTER INSERT ON transactions
WHEN NEW.transaction_type = 'SELL'
BEGIN
    UPDATE holdings
    SET quantity = quantity - NEW.quantity
    WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id;

    DELETE FROM holdings
    WHERE portfolio_id = NEW.portfolio_id AND asset_id = NEW.asset_id AND quantity <= 0.001;
END;

-- Update Portfolio Value on Holding Change
CREATE TRIGGER update_portfolio_val_after_holding_update
AFTER UPDATE OF quantity ON holdings
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.0)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = portfolios.portfolio_id
    )
    WHERE portfolio_id = NEW.portfolio_id;
END;

CREATE TRIGGER update_portfolio_val_after_holding_insert
AFTER INSERT ON holdings
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.0)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = portfolios.portfolio_id
    )
    WHERE portfolio_id = NEW.portfolio_id;
END;

CREATE TRIGGER update_portfolio_val_after_holding_delete
AFTER DELETE ON holdings
BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.0)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = portfolios.portfolio_id
    )
    WHERE portfolio_id = OLD.portfolio_id;
END;
