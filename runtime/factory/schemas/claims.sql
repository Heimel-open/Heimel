-- claims.db schema (versioned contract)
CREATE TABLE claims(issue_id TEXT PRIMARY KEY,actor_id TEXT,run_id TEXT,claimed_at TEXT,expires_at TEXT,heartbeat_at TEXT,status TEXT)
