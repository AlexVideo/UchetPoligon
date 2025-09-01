PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS block_mode_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  block_id   INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE CASCADE,
  mode       TEXT NOT NULL,
  date_from  TEXT NOT NULL,
  date_to    TEXT,
  note       TEXT,
  UNIQUE(block_id, date_from)
);

CREATE VIEW IF NOT EXISTS v_block_mode_on_date AS
SELECT
  b.id AS block_id,
  d.date,
  (
    SELECT h.mode
    FROM block_mode_history h
    WHERE h.block_id = b.id
      AND h.date_from <= d.date
      AND (h.date_to IS NULL OR d.date <= h.date_to)
    ORDER BY h.date_from DESC
    LIMIT 1
  ) AS mode
FROM blocks b
JOIN (
  SELECT date FROM daily_readings
  UNION SELECT date FROM acid_levels
  UNION SELECT date FROM rvr_events
  UNION SELECT date FROM analyses
  UNION SELECT date FROM block_acidity_analyses
  UNION SELECT date FROM metal_analyses
) d;
