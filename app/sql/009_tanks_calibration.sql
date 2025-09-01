PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tank_calibration (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  tank_id   INTEGER NOT NULL REFERENCES acid_tanks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  cm        INTEGER NOT NULL,
  tons      REAL NOT NULL,
  UNIQUE(tank_id, cm)
);
