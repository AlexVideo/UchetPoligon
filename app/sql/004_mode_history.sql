PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS well_mode_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id    INTEGER NOT NULL REFERENCES wells(id) ON UPDATE CASCADE ON DELETE CASCADE,
  mode       TEXT NOT NULL CHECK (mode IN ('PR','VR','OBS','OTHER')),
  date_from  TEXT NOT NULL,
  date_to    TEXT,
  note       TEXT,
  UNIQUE (well_id, date_from)
);

CREATE VIEW IF NOT EXISTS v_well_mode_on_date AS
SELECT
  w.id   AS well_id,
  d.date AS date,
  COALESCE(
    (SELECT h.mode
     FROM well_mode_history h
     WHERE h.well_id = w.id
       AND h.date_from <= d.date
       AND (h.date_to IS NULL OR d.date <= h.date_to)
     ORDER BY h.date_from DESC
     LIMIT 1),
    w.type
  ) AS mode
FROM wells w
JOIN (
  SELECT date FROM daily_readings
  UNION SELECT date FROM acid_levels
  UNION SELECT date FROM rvr_events
  UNION SELECT date FROM analyses
  UNION SELECT date FROM downtimes
) d;
