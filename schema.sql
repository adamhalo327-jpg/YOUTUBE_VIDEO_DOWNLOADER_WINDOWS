CREATE TABLE IF NOT EXISTS licenses (
  id TEXT PRIMARY KEY,
  code_hash TEXT UNIQUE NOT NULL,
  owner TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT,
  revoked INTEGER NOT NULL DEFAULT 0,
  device TEXT,
  token_hash TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS licenses_expiry ON licenses(expires_at);
