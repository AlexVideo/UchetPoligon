-- 001_init_schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO app_meta(key, value) VALUES ('schema_version', '1')
  ON CONFLICT(key) DO UPDATE SET value=excluded.value;

CREATE TABLE IF NOT EXISTS users (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  username     TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('admin','dispatcher','engineer')),
  theme        TEXT NOT NULL DEFAULT 'dark' CHECK (theme IN ('dark','light')),
  lang         TEXT NOT NULL DEFAULT 'ru' CHECK (lang IN ('ru','kk')),
  tz           TEXT NOT NULL DEFAULT 'Asia/Almaty',
  is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  block_no      TEXT NOT NULL,
  flank         TEXT,
  vl            TEXT,
  cell          TEXT,
  area_m2       REAL,
  horizon_power REAL,
  ore_mass_t    REAL,
  regime        TEXT,
  shape_wkt     TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(block_no)
);

CREATE TABLE IF NOT EXISTS wells (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  block_id      INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  well_no       TEXT NOT NULL,
  type          TEXT NOT NULL CHECK (type IN ('PR','VR','OBS','OTHER')),
  current_mode  TEXT,
  depth_m       REAL,
  filter_type   TEXT,
  coord_x       REAL,
  coord_y       REAL,
  coord_z       REAL,
  filter_from_m REAL,
  filter_to_m   REAL,
  coord_sys     TEXT DEFAULT 'local',
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','plugged')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(block_id, well_no)
);

CREATE TABLE IF NOT EXISTS rvr_types (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  name           TEXT NOT NULL UNIQUE,
  avg_duration_h REAL,
  default_color  TEXT,
  default_cost   REAL
);

CREATE TABLE IF NOT EXISTS acid_tanks (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL UNIQUE,
  capacity_t REAL,
  location   TEXT,
  height_cm  INTEGER,
  is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS daily_readings (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  date                 TEXT NOT NULL,
  block_id             INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  well_id              INTEGER NOT NULL REFERENCES wells(id)  ON UPDATE CASCADE ON DELETE RESTRICT,
  pr_counter_prev_eff  REAL DEFAULT 0.0 CHECK (pr_counter_prev_eff >= 0),
  pr_counter_curr      REAL DEFAULT 0.0 CHECK (pr_counter_curr      >= 0),
  pr_hours             REAL DEFAULT 0.0 CHECK (pr_hours >= 0 AND pr_hours <= 24),
  pr_downtime_h        REAL DEFAULT 0.0 CHECK (pr_downtime_h >= 0 AND pr_downtime_h <= 24),
  vr_volume_m3         REAL DEFAULT 0.0 CHECK (vr_volume_m3 >= 0),
  vr_hours             REAL DEFAULT 0.0 CHECK (vr_hours >= 0 AND vr_hours <= 24),
  vr_downtime_h        REAL DEFAULT 0.0 CHECK (vr_downtime_h >= 0 AND vr_downtime_h <= 24),
  rvr_type_id          INTEGER REFERENCES rvr_types(id) ON UPDATE CASCADE ON DELETE SET NULL,
  comment              TEXT,
  status               TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','validated','reconciled','approved')),
  created_at           TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(date, well_id)
);

CREATE TABLE IF NOT EXISTS acid_levels (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  date             TEXT NOT NULL,
  tank_id          INTEGER NOT NULL REFERENCES acid_tanks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  level_begin_t    REAL NOT NULL CHECK (level_begin_t >= 0),
  level_end_t      REAL NOT NULL CHECK (level_end_t   >= 0),
  level_begin_cm   INTEGER,
  level_end_cm     INTEGER,
  receipts_t       REAL NOT NULL DEFAULT 0 CHECK (receipts_t      >= 0),
  transfers_in_t   REAL NOT NULL DEFAULT 0 CHECK (transfers_in_t   >= 0),
  transfers_out_t  REAL NOT NULL DEFAULT 0 CHECK (transfers_out_t  >= 0),
  adjustments_t    REAL NOT NULL DEFAULT 0,
  note             TEXT,
  UNIQUE(date, tank_id)
);

CREATE TABLE IF NOT EXISTS acid_distribution (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  date      TEXT NOT NULL,
  block_id  INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  acid_tons REAL NOT NULL DEFAULT 0 CHECK (acid_tons >= 0),
  method    TEXT NOT NULL DEFAULT 'VR-share',
  note      TEXT,
  UNIQUE(date, block_id)
);

CREATE TABLE IF NOT EXISTS rvr_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  date        TEXT NOT NULL,
  well_id     INTEGER NOT NULL REFERENCES wells(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  rvr_type_id INTEGER NOT NULL REFERENCES rvr_types(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  duration_h  REAL NOT NULL CHECK (duration_h >= 0),
  cost        REAL DEFAULT 0 CHECK (cost >= 0),
  note        TEXT
);

CREATE TABLE IF NOT EXISTS analyses (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  date       TEXT NOT NULL,
  block_id   INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  well_id    INTEGER REFERENCES wells(id) ON UPDATE CASCADE ON DELETE SET NULL,
  metal_gpl  REAL,
  sample_no  TEXT,
  lab_name   TEXT
);

CREATE TABLE IF NOT EXISTS downtimes (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  date      TEXT NOT NULL,
  block_id  INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  well_id   INTEGER REFERENCES wells(id) ON UPDATE CASCADE ON DELETE SET NULL,
  hours     REAL NOT NULL CHECK (hours >= 0 AND hours <= 24),
  reason    TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        TEXT NOT NULL DEFAULT (datetime('now')),
  user_id   INTEGER REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
  action    TEXT NOT NULL,
  entity    TEXT NOT NULL,
  entity_id INTEGER,
  payload   TEXT
);

CREATE INDEX IF NOT EXISTS idx_daily_readings_block_date ON daily_readings(block_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_readings_well_date  ON daily_readings(well_id,  date);
CREATE INDEX IF NOT EXISTS idx_acid_levels_date_tank     ON acid_levels(date, tank_id);
CREATE INDEX IF NOT EXISTS idx_acid_distribution_date    ON acid_distribution(date, block_id);
CREATE INDEX IF NOT EXISTS idx_rvr_events_date           ON rvr_events(date, well_id);
CREATE INDEX IF NOT EXISTS idx_analyses_block_date       ON analyses(block_id, date);
CREATE INDEX IF NOT EXISTS idx_downtimes_block_date      ON downtimes(block_id, date);

CREATE VIEW IF NOT EXISTS v_daily_block_summary AS
SELECT
  dr.date,
  dr.block_id,
  COUNT(DISTINCT dr.well_id) AS wells_count,
  SUM(MAX(0, dr.pr_counter_curr - dr.pr_counter_prev_eff)) AS pr_m3,
  SUM(dr.pr_hours) AS pr_hours,
  CASE WHEN SUM(dr.pr_hours) > 0
       THEN SUM(MAX(0, dr.pr_counter_curr - dr.pr_counter_prev_eff)) / SUM(dr.pr_hours)
       ELSE NULL END AS pr_rate_m3ph,
  SUM(dr.vr_volume_m3) AS vr_m3,
  SUM(dr.vr_hours) AS vr_hours,
  CASE WHEN SUM(dr.vr_hours) > 0
       THEN SUM(dr.vr_volume_m3) / SUM(dr.vr_hours)
       ELSE NULL END AS injectivity_m3ph,
  SUM(dr.pr_downtime_h) AS pr_downtime_h,
  SUM(dr.vr_downtime_h) AS vr_downtime_h
FROM daily_readings dr
GROUP BY dr.date, dr.block_id;

-- Примечание: этот VIEW ссылается на tank_calibration, которая создаётся в 009_tanks_calibration.sql.
-- Для SQLite это ок — таблица может появиться позже.
CREATE VIEW IF NOT EXISTS v_acid_levels_with_calc AS
SELECT
  al.id,
  al.date,
  al.tank_id,
  al.level_begin_t,
  al.level_end_t,
  al.level_begin_cm,
  al.level_end_cm,
  (SELECT tc.tons FROM tank_calibration tc WHERE tc.tank_id=al.tank_id AND tc.cm=al.level_begin_cm) AS level_begin_t_calc,
  (SELECT tc.tons FROM tank_calibration tc WHERE tc.tank_id=al.tank_id AND tc.cm=al.level_end_cm)   AS level_end_t_calc,
  al.receipts_t, al.transfers_in_t, al.transfers_out_t, al.adjustments_t, al.note
FROM acid_levels al;

CREATE VIEW IF NOT EXISTS v_acid_reconciliation AS
WITH tank_day AS (
  SELECT
    al.date,
    SUM(al.level_begin_t - al.level_end_t + al.transfers_out_t - al.transfers_in_t - al.receipts_t + al.adjustments_t) AS tank_delta_t
  FROM acid_levels al
  GROUP BY al.date
),
dist_day AS (
  SELECT ad.date, SUM(ad.acid_tons) AS dist_t
  FROM acid_distribution ad
  GROUP BY ad.date
)
SELECT
  t.date,
  t.tank_delta_t AS warehouse_consumption_t,
  d.dist_t       AS distributed_t,
  (t.tank_delta_t - d.dist_t) AS delta_t
FROM tank_day t
LEFT JOIN dist_day d ON d.date = t.date;

INSERT INTO users(username, display_name, role)
VALUES ('admin', 'Администратор', 'admin')
ON CONFLICT(username) DO NOTHING;

INSERT INTO settings(key, value) VALUES
  ('acid_distribution_method', 'VR-share'),
  ('validation.pr.max_hours_per_day', '24'),
  ('validation.vr.max_hours_per_day', '24')
ON CONFLICT(key) DO NOTHING;
