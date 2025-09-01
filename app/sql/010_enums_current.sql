PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS enums_current (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  type  TEXT NOT NULL CHECK (type IN ('VL','CELL','FLANK')),
  value TEXT NOT NULL,
  UNIQUE(type, value)
);
