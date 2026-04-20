-- MySQL dump 10.13  Distrib 9.5.0, for macos15 (arm64)
--
-- Host: localhost    Database: portfolio
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `assets`
--

DROP TABLE IF EXISTS `assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assets` (
  `asset_id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `asset_type` varchar(50) NOT NULL,
  `current_price` decimal(15,2) NOT NULL,
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`asset_id`),
  UNIQUE KEY `symbol` (`symbol`),
  CONSTRAINT `chk_asset_price` CHECK ((`current_price` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assets`
--

LOCK TABLES `assets` WRITE;
/*!40000 ALTER TABLE `assets` DISABLE KEYS */;
INSERT INTO `assets` VALUES (1,'RELIANCE.NS','Reliance Industries','Equity',2950.45,'2026-04-20 08:34:42'),(2,'TCS.NS','Tata Consultancy Services','Equity',3912.00,'2026-04-20 08:34:42'),(3,'HDFCBANK.NS','HDFC Bank','Equity',1422.30,'2026-04-20 08:34:42'),(4,'ICICIBANK.NS','ICICI Bank','Equity',1085.60,'2026-04-20 08:34:42'),(5,'INFY.NS','Infosys','Equity',1488.90,'2026-04-20 08:34:42'),(6,'BHARTIARTL.NS','Bharti Airtel','Equity',1125.10,'2026-04-20 08:34:42'),(7,'SBIN.NS','State Bank of India','Equity',742.00,'2026-04-20 08:34:42'),(8,'LICI.NS','LIC of India','Equity',895.00,'2026-04-20 08:34:42'),(9,'LT.NS','Larsen & Toubro','Equity',3450.00,'2026-04-20 08:34:42'),(10,'ITC.NS','ITC Limited','Equity',428.15,'2026-04-20 08:34:42');
/*!40000 ALTER TABLE `assets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `admin_id` int NOT NULL,
  `action` text NOT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `admin_id` (`admin_id`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`admin_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
INSERT INTO `audit_logs` VALUES (1,1,'SYSTEM_BOOTSTRAP: Distinction node activated.','2026-04-20 14:04:42'),(2,1,'SURVEILLANCE: Normalization audit passed (BCNF).','2026-04-20 14:04:42');
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `global_config`
--

DROP TABLE IF EXISTS `global_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `global_config` (
  `config_key` varchar(50) NOT NULL,
  `config_value` varchar(255) NOT NULL,
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `global_config`
--

LOCK TABLES `global_config` WRITE;
/*!40000 ALTER TABLE `global_config` DISABLE KEYS */;
INSERT INTO `global_config` VALUES ('MARKET_STATUS','OPEN','2026-04-20 08:34:42'),('MAX_CONCENTRATION_THRESHOLD','0.50','2026-04-20 08:34:42'),('SYSTEM_NODE_ID','AXIOM-VIVA-DISTINCTION','2026-04-20 08:34:42');
/*!40000 ALTER TABLE `global_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `holdings`
--

DROP TABLE IF EXISTS `holdings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `holdings` (
  `portfolio_id` int NOT NULL,
  `asset_id` int NOT NULL,
  `quantity` decimal(15,4) NOT NULL DEFAULT '0.0000',
  `average_buy_price` decimal(15,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`portfolio_id`,`asset_id`),
  KEY `asset_id` (`asset_id`),
  CONSTRAINT `holdings_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolios` (`portfolio_id`) ON DELETE CASCADE,
  CONSTRAINT `holdings_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`asset_id`) ON DELETE CASCADE,
  CONSTRAINT `chk_quantity` CHECK ((`quantity` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `holdings`
--

LOCK TABLES `holdings` WRITE;
/*!40000 ALTER TABLE `holdings` DISABLE KEYS */;
INSERT INTO `holdings` VALUES (2,1,50.0000,2900.00),(2,3,100.0000,1400.00);
/*!40000 ALTER TABLE `holdings` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `trig_refresh_portfolio_val` AFTER UPDATE ON `holdings` FOR EACH ROW BEGIN
    UPDATE portfolios
    SET total_value = (
        SELECT COALESCE(SUM(h.quantity * a.current_price), 0.00)
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.portfolio_id = NEW.portfolio_id
    )
    WHERE portfolio_id = NEW.portfolio_id;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `market_news`
--

DROP TABLE IF EXISTS `market_news`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_news` (
  `news_id` int NOT NULL AUTO_INCREMENT,
  `headline` varchar(255) NOT NULL,
  `source` varchar(100) NOT NULL,
  `published_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`news_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_news`
--

LOCK TABLES `market_news` WRITE;
/*!40000 ALTER TABLE `market_news` DISABLE KEYS */;
INSERT INTO `market_news` VALUES (1,'Reliance Industries expands Green Energy vision.','NSE Feed','2026-04-20 14:04:42'),(2,'HDFC-ICICI Banking sector growth surges.','Institutional Intel','2026-04-20 14:04:42');
/*!40000 ALTER TABLE `market_news` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_news_assets`
--

DROP TABLE IF EXISTS `market_news_assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_news_assets` (
  `news_id` int NOT NULL,
  `asset_id` int NOT NULL,
  PRIMARY KEY (`news_id`,`asset_id`),
  KEY `asset_id` (`asset_id`),
  CONSTRAINT `market_news_assets_ibfk_1` FOREIGN KEY (`news_id`) REFERENCES `market_news` (`news_id`) ON DELETE CASCADE,
  CONSTRAINT `market_news_assets_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`asset_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_news_assets`
--

LOCK TABLES `market_news_assets` WRITE;
/*!40000 ALTER TABLE `market_news_assets` DISABLE KEYS */;
INSERT INTO `market_news_assets` VALUES (1,1),(2,3),(2,4);
/*!40000 ALTER TABLE `market_news_assets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `portfolios`
--

DROP TABLE IF EXISTS `portfolios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `portfolios` (
  `portfolio_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `total_value` decimal(15,2) DEFAULT '0.00',
  PRIMARY KEY (`portfolio_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `portfolios_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `portfolios`
--

LOCK TABLES `portfolios` WRITE;
/*!40000 ALTER TABLE `portfolios` DISABLE KEYS */;
INSERT INTO `portfolios` VALUES (1,1,'Admin Treasury',0.00),(2,2,'Strategy Alpha',250000.00);
/*!40000 ALTER TABLE `portfolios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `request_statuses`
--

DROP TABLE IF EXISTS `request_statuses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `request_statuses` (
  `status_id` int NOT NULL,
  `status_name` varchar(20) NOT NULL,
  PRIMARY KEY (`status_id`),
  UNIQUE KEY `status_name` (`status_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `request_statuses`
--

LOCK TABLES `request_statuses` WRITE;
/*!40000 ALTER TABLE `request_statuses` DISABLE KEYS */;
INSERT INTO `request_statuses` VALUES (2,'APPROVED'),(1,'PENDING'),(3,'REJECTED');
/*!40000 ALTER TABLE `request_statuses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trade_requests`
--

DROP TABLE IF EXISTS `trade_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `portfolio_id` int NOT NULL,
  `asset_id` int NOT NULL,
  `type_id` int NOT NULL,
  `quantity` decimal(15,4) NOT NULL,
  `requested_price` decimal(15,2) NOT NULL,
  `status_id` int NOT NULL DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `actioned_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`request_id`),
  KEY `user_id` (`user_id`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `asset_id` (`asset_id`),
  KEY `type_id` (`type_id`),
  KEY `status_id` (`status_id`),
  CONSTRAINT `trade_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `trade_requests_ibfk_2` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolios` (`portfolio_id`) ON DELETE CASCADE,
  CONSTRAINT `trade_requests_ibfk_3` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`asset_id`) ON DELETE CASCADE,
  CONSTRAINT `trade_requests_ibfk_4` FOREIGN KEY (`type_id`) REFERENCES `transaction_types` (`type_id`),
  CONSTRAINT `trade_requests_ibfk_5` FOREIGN KEY (`status_id`) REFERENCES `request_statuses` (`status_id`),
  CONSTRAINT `chk_req_price` CHECK ((`requested_price` > 0)),
  CONSTRAINT `chk_req_qty` CHECK ((`quantity` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trade_requests`
--

LOCK TABLES `trade_requests` WRITE;
/*!40000 ALTER TABLE `trade_requests` DISABLE KEYS */;
/*!40000 ALTER TABLE `trade_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transaction_types`
--

DROP TABLE IF EXISTS `transaction_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transaction_types` (
  `type_id` int NOT NULL,
  `type_name` varchar(10) NOT NULL,
  PRIMARY KEY (`type_id`),
  UNIQUE KEY `type_name` (`type_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transaction_types`
--

LOCK TABLES `transaction_types` WRITE;
/*!40000 ALTER TABLE `transaction_types` DISABLE KEYS */;
INSERT INTO `transaction_types` VALUES (1,'BUY'),(2,'SELL');
/*!40000 ALTER TABLE `transaction_types` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transactions` (
  `transaction_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int DEFAULT NULL,
  `portfolio_id` int NOT NULL,
  `asset_id` int NOT NULL,
  `type_id` int NOT NULL,
  `quantity` decimal(15,4) NOT NULL,
  `price_per_unit` decimal(15,2) NOT NULL,
  `transaction_date` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`transaction_id`),
  UNIQUE KEY `request_id` (`request_id`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `asset_id` (`asset_id`),
  KEY `type_id` (`type_id`),
  CONSTRAINT `transactions_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `trade_requests` (`request_id`) ON DELETE SET NULL,
  CONSTRAINT `transactions_ibfk_2` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolios` (`portfolio_id`) ON DELETE CASCADE,
  CONSTRAINT `transactions_ibfk_3` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`asset_id`) ON DELETE CASCADE,
  CONSTRAINT `transactions_ibfk_4` FOREIGN KEY (`type_id`) REFERENCES `transaction_types` (`type_id`),
  CONSTRAINT `chk_tx_qty` CHECK ((`quantity` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transactions`
--

LOCK TABLES `transactions` WRITE;
/*!40000 ALTER TABLE `transactions` DISABLE KEYS */;
/*!40000 ALTER TABLE `transactions` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `after_trade_insert` AFTER INSERT ON `transactions` FOR EACH ROW BEGIN
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
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `user_roles`
--

DROP TABLE IF EXISTS `user_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_roles` (
  `role_id` int NOT NULL,
  `role_name` varchar(20) NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_roles`
--

LOCK TABLES `user_roles` WRITE;
/*!40000 ALTER TABLE `user_roles` DISABLE KEYS */;
INSERT INTO `user_roles` VALUES (1,'admin'),(2,'user');
/*!40000 ALTER TABLE `user_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role_id` int NOT NULL DEFAULT '2',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `user_roles` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'admin','admin@axiom.institutional','pbkdf2:sha256:600000$admin_hash',1,'2026-04-20 08:34:42'),(2,'vikram_sharma','v.sharma@axiom.node','pbkdf2:sha256:600000$user_hash',2,'2026-04-20 08:34:42');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `view_operative_risk`
--

DROP TABLE IF EXISTS `view_operative_risk`;
/*!50001 DROP VIEW IF EXISTS `view_operative_risk`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `view_operative_risk` AS SELECT 
 1 AS `username`,
 1 AS `portfolio`,
 1 AS `asset`,
 1 AS `quantity`,
 1 AS `position_value`,
 1 AS `concentration_pct`,
 1 AS `risk_profile`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `view_portfolio_rankings`
--

DROP TABLE IF EXISTS `view_portfolio_rankings`;
/*!50001 DROP VIEW IF EXISTS `view_portfolio_rankings`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `view_portfolio_rankings` AS SELECT 
 1 AS `username`,
 1 AS `portfolio_name`,
 1 AS `total_value`,
 1 AS `global_rank`,
 1 AS `user_internal_rank`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `watchlist_items`
--

DROP TABLE IF EXISTS `watchlist_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `watchlist_items` (
  `watchlist_id` int NOT NULL,
  `asset_id` int NOT NULL,
  PRIMARY KEY (`watchlist_id`,`asset_id`),
  KEY `asset_id` (`asset_id`),
  CONSTRAINT `watchlist_items_ibfk_1` FOREIGN KEY (`watchlist_id`) REFERENCES `watchlists` (`watchlist_id`) ON DELETE CASCADE,
  CONSTRAINT `watchlist_items_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`asset_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watchlist_items`
--

LOCK TABLES `watchlist_items` WRITE;
/*!40000 ALTER TABLE `watchlist_items` DISABLE KEYS */;
/*!40000 ALTER TABLE `watchlist_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `watchlists`
--

DROP TABLE IF EXISTS `watchlists`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `watchlists` (
  `watchlist_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`watchlist_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `watchlists_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watchlists`
--

LOCK TABLES `watchlists` WRITE;
/*!40000 ALTER TABLE `watchlists` DISABLE KEYS */;
/*!40000 ALTER TABLE `watchlists` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Final view structure for view `view_operative_risk`
--

/*!50001 DROP VIEW IF EXISTS `view_operative_risk`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = latin1 */;
/*!50001 SET character_set_results     = latin1 */;
/*!50001 SET collation_connection      = latin1_swedish_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `view_operative_risk` AS select `u`.`username` AS `username`,`p`.`name` AS `portfolio`,`a`.`symbol` AS `asset`,`h`.`quantity` AS `quantity`,(`h`.`quantity` * `a`.`current_price`) AS `position_value`,((`h`.`quantity` * `a`.`current_price`) / nullif(`p`.`total_value`,0)) AS `concentration_pct`,(case when (((`h`.`quantity` * `a`.`current_price`) / nullif(`p`.`total_value`,0)) > 0.40) then 'CRITICAL' else 'STABLE' end) AS `risk_profile` from (((`holdings` `h` join `assets` `a` on((`h`.`asset_id` = `a`.`asset_id`))) join `portfolios` `p` on((`h`.`portfolio_id` = `p`.`portfolio_id`))) join `users` `u` on((`p`.`user_id` = `u`.`user_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `view_portfolio_rankings`
--

/*!50001 DROP VIEW IF EXISTS `view_portfolio_rankings`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = latin1 */;
/*!50001 SET character_set_results     = latin1 */;
/*!50001 SET collation_connection      = latin1_swedish_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `view_portfolio_rankings` AS select `u`.`username` AS `username`,`p`.`name` AS `portfolio_name`,`p`.`total_value` AS `total_value`,rank() OVER (ORDER BY `p`.`total_value` desc )  AS `global_rank`,dense_rank() OVER (PARTITION BY `u`.`user_id` ORDER BY `p`.`total_value` desc )  AS `user_internal_rank` from (`portfolios` `p` join `users` `u` on((`p`.`user_id` = `u`.`user_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-20 14:08:58
