-- Wykonaj RAZ przed wdrożeniem nowego Workera. Zachowuje istniejące salda/licencje.
CREATE TABLE IF NOT EXISTS token_admin_grants (
 id TEXT PRIMARY KEY,
 wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
 amount INTEGER NOT NULL CHECK(amount BETWEEN 1 AND 10000),
 reason TEXT NOT NULL CHECK(length(reason) BETWEEN 1 AND 180),
 actor_fingerprint TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_admin_grants_wallet
 ON token_admin_grants(wallet_id,created_at);
