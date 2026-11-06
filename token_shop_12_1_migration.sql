-- YVD Token Shop 12.1: migracja dodająca tabele, nie usuwa licenses i admin_audit.
CREATE TABLE IF NOT EXISTS token_wallets (
 id TEXT PRIMARY KEY, secret_hash TEXT NOT NULL UNIQUE, device TEXT NOT NULL,
 created_at TEXT NOT NULL, ip_hash TEXT NOT NULL, day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_wallets_ip_day ON token_wallets(ip_hash,day);
CREATE TABLE IF NOT EXISTS token_sessions (
 id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
 day TEXT NOT NULL, url_hash TEXT NOT NULL, started_at_s INTEGER NOT NULL,
 UNIQUE(wallet_id,day,url_hash)
);
CREATE TABLE IF NOT EXISTS token_ledger (
 id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
 delta INTEGER NOT NULL CHECK(delta IN (10,-100,-500,-1500)),
 kind TEXT NOT NULL CHECK(kind IN ('reward','purchase')), day TEXT NOT NULL,
 url_hash TEXT, ip_hash TEXT, created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_token_reward_once ON token_ledger(wallet_id,day,url_hash) WHERE kind='reward';
CREATE INDEX IF NOT EXISTS idx_token_ledger_wallet ON token_ledger(wallet_id);
CREATE INDEX IF NOT EXISTS idx_token_ledger_caps ON token_ledger(day,ip_hash,kind);
CREATE TABLE IF NOT EXISTS token_purchases (
 id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
 package TEXT NOT NULL CHECK(package IN ('STARTER','PRO','ULTRA')),
 price INTEGER NOT NULL, expires_at_s INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_purchase_wallet ON token_purchases(wallet_id,expires_at_s);
