PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS block_acidity_analyses (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  date        TEXT NOT NULL,
  block_id    INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  metric_name TEXT NOT NULL DEFAULT 'acid_ph',
  value       REAL NOT NULL,
  sample_no   TEXT,
  lab_name    TEXT,
  note        TEXT,
  UNIQUE(date, block_id, metric_name)
);

CREATE TABLE IF NOT EXISTS metal_analyses (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  date       TEXT NOT NULL,
  block_id   INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  well_id    INTEGER REFERENCES wells(id) ON UPDATE CASCADE ON DELETE SET NULL,
  metal_gpl  REAL NOT NULL,
  sample_no  TEXT,
  lab_name   TEXT,
  note       TEXT,
  CHECK (metal_gpl >= 0)
);

CREATE VIEW IF NOT EXISTS v_block_acidity_asof AS
SELECT
  d.date,
  b.id AS block_id,
  m.metric_name,
  (
    SELECT a.value
    FROM block_acidity_analyses a
    WHERE a.block_id = b.id
      AND a.metric_name = m.metric_name
      AND a.date <= d.date
    ORDER BY a.date DESC, a.id DESC
    LIMIT 1
  ) AS value_asof
FROM blocks b
JOIN (
  SELECT date FROM daily_readings
  UNION SELECT date FROM acid_levels
  UNION SELECT date FROM analyses
  UNION SELECT date FROM rvr_events
  UNION SELECT date FROM downtimes
  UNION SELECT date FROM block_acidity_analyses
  UNION SELECT date FROM metal_analyses
) d
JOIN (
  SELECT DISTINCT metric_name FROM block_acidity_analyses
) m;

CREATE VIEW IF NOT EXISTS v_block_metal_asof AS
SELECT
  d.date,
  b.id AS block_id,
  (
    SELECT ma.metal_gpl
    FROM metal_analyses ma
    WHERE ma.block_id = b.id
      AND ma.well_id IS NULL
      AND ma.date <= d.date
    ORDER BY ma.date DESC, ma.id DESC
    LIMIT 1
  ) AS metal_gpl_asof
FROM blocks b
JOIN (
  SELECT date FROM daily_readings
  UNION SELECT date FROM acid_levels
  UNION SELECT date FROM rvr_events
  UNION SELECT date FROM downtimes
  UNION SELECT date FROM metal_analyses
) d;

CREATE VIEW IF NOT EXISTS v_well_metal_asof AS
SELECT
  d.date,
  w.id AS well_id,
  w.block_id,
  (
    SELECT ma.metal_gpl
    FROM metal_analyses ma
    WHERE ma.well_id = w.id
      AND ma.date <= d.date
    ORDER BY ma.date DESC, ma.id DESC
    LIMIT 1
  ) AS metal_gpl_asof
FROM wells w
JOIN (
  SELECT date FROM daily_readings
  UNION SELECT date FROM rvr_events
  UNION SELECT date FROM metal_analyses
) d;

CREATE VIEW IF NOT EXISTS v_block_lab_activity AS
SELECT
  d.date,
  b.id AS block_id,
  EXISTS(SELECT 1 FROM block_acidity_analyses a WHERE a.block_id=b.id AND a.date=d.date) AS has_acidity,
  EXISTS(SELECT 1 FROM metal_analyses m WHERE m.block_id=b.id AND m.well_id IS NULL AND m.date=d.date) AS has_block_metal
FROM blocks b
JOIN (
  SELECT date FROM block_acidity_analyses
  UNION SELECT date FROM metal_analyses
) d;
