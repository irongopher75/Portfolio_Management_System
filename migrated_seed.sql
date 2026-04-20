-- =============================================================================
-- AXIOM TERMINAL | MIGRATED DISTINCTION SEED DATA
-- =============================================================================

USE `portfolio`;

-- 1. SEED ASSETS (Institutional Baseline)
INSERT INTO `assets` (asset_id, symbol, name, asset_type, current_price) VALUES 
(1,'RELIANCE.NS','Reliance Industries','Equity',2950.45),
(2,'TCS.NS','Tata Consultancy Services','Equity',3912.00),
(3,'HDFCBANK.NS','HDFC Bank','Equity',1422.30),
(4,'ICICIBANK.NS','ICICI Bank','Equity',1085.60),
(5,'INFY.NS','Infosys','Equity',1488.90),
(6,'BHARTIARTL.NS','Bharti Airtel','Equity',1125.10),
(7,'SBIN.NS','State Bank of India','Equity',742.00),
(8,'LICI.NS','LIC of India','Equity',895.00),
(9,'LT.NS','Larsen & Toubro','Equity',3450.00),
(10,'ITC.NS','ITC Limited','Equity',428.15);

-- 2. SEED USERS & ROLES
-- Role mapping: 1=admin, 2=user
INSERT INTO `users` (user_id, username, email, password_hash, role_id) VALUES 
(1, 'admin', 'admin@axiom.institutional', 'pbkdf2:sha256:600000$admin_hash', 1),
(2, 'vikram_sharma', 'v.sharma@axiom.node', 'pbkdf2:sha256:600000$user_hash', 2);

-- 3. SEED PORTFOLIOS
INSERT INTO `portfolios` (portfolio_id, user_id, name, total_value) VALUES 
(1, 1, 'Admin Treasury', 0.00),
(2, 2, 'Strategy Alpha', 250000.00);

-- 4. SEED INITIAL HOLDINGS
INSERT INTO `holdings` (portfolio_id, asset_id, quantity, average_buy_price) VALUES 
(2, 1, 50.00, 2900.00),
(2, 3, 100.00, 1400.00);

-- 5. SEED DATA FOR LOOKUPS (Types & Statuses)
-- Already handled in schema, but ensuring dependencies.

-- 6. SEED MARKET NEWS & JUNCTION (Resolving 1NF)
INSERT INTO `market_news` (news_id, headline, source) VALUES 
(1, 'Reliance Industries expands Green Energy vision.', 'NSE Feed'),
(2, 'HDFC-ICICI Banking sector growth surges.', 'Institutional Intel');

INSERT INTO `market_news_assets` (news_id, asset_id) VALUES 
(1, 1), -- Reliance
(2, 3), -- HDFC
(2, 4); -- ICICI

-- 7. SEED INITIAL AUDIT LOGS
INSERT INTO `audit_logs` (admin_id, action) VALUES 
(1, 'SYSTEM_BOOTSTRAP: Distinction node activated.'),
(1, 'SURVEILLANCE: Normalization audit passed (BCNF).');
