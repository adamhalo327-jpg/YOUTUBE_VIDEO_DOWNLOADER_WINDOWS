-- TOKEN SHOP 14.0: add-only migration. Run ONCE on the SAME D1 database as 12.1.
-- No DROP or ALTER of token_wallets, token_ledger, token_purchases or licenses.
CREATE TABLE IF NOT EXISTS token_mission_claims14 (
  id TEXT PRIMARY KEY,
  wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
  mission TEXT NOT NULL CHECK(mission IN ('DAILY_3','WEEKLY_15')),
  period TEXT NOT NULL,
  reward INTEGER NOT NULL CHECK(reward IN (20,80)),
  created_at TEXT NOT NULL,
  UNIQUE(wallet_id,mission,period)
);
CREATE INDEX IF NOT EXISTS idx_missions14_wallet ON token_mission_claims14(wallet_id,period);
CREATE TABLE IF NOT EXISTS token_purchases14 (
  id TEXT PRIMARY KEY,
  wallet_id TEXT NOT NULL REFERENCES token_wallets(id),
  package TEXT NOT NULL CHECK(package IN ('PLUS','LEGEND')),
  price INTEGER NOT NULL CHECK(price IN (250,3000)),
  expires_at_s INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_purchases14_wallet ON token_purchases14(wallet_id,expires_at_s);
