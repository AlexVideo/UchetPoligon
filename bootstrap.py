# -*- coding: utf-8 -*-
# Создаёт структуру проекта, SQL-миграции, migrate.py, тест и Makefile.
from __future__ import annotations
import os

ROOT = os.path.abspath(os.path.dirname(__file__))

FILES: dict[str, str] = {
    # ---------- Makefile ----------
    "Makefile": r""".PHONY: migrate test clean
PY?=python
migrate:
	$(PY) core/db/migrate.py
test:
	$(PY) -m pytest -q
clean:
	-del /q data\\uchet.db 2>nul || true
""",

    # ---------- requirements.txt ----------
    "requirements.txt": "pytest>=8.0.0\n",

    # ---------- core/db/migrate.py ----------
    os.path.join("core","db","migrate.py"): r"""from __future__ import annotations
import os, sqlite3, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SQL_DIR = os.path.join(ROOT, "app", "sql")
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "uchet.db")

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def run_sql(conn: sqlite3.Connection, sql_path: str):
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    print(f"[migrate] applying {os.path.basename(sql_path)}")
    conn.executescript(sql)

def main():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    try:
        files = sorted(glob.glob(os.path.join(SQL_DIR, "*.sql")))
        for path in files:
            run_sql(conn, path)
        conn.commit()
        cur = conn.execute("SELECT value FROM app_meta WHERE key='schema_version'")
        ver = cur.fetchone()
        print(f"[migrate] schema_version = {ver[0] if ver else 'unknown'}")
    finally:
        conn.close()
    print(f"[migrate] done. DB at {DB_PATH}")

if __name__ == "__main__":
    main()
""",

    # ---------- tests/test_schema_smoke.py ----------
    os.path.join("tests","test_schema_smoke.py"): r"""from __future__ import annotations
import os, sqlite3, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable

def test_migrate_and_schema():
    migrate = os.path.join(ROOT, "core", "db", "migrate.py")
    res = subprocess.run([PY, migrate], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr

    db_path = os.path.join(ROOT, "data", "uchet.db")
    assert os.path.exists(db_path), "DB not created"

    conn = sqlite3.connect(db_path)
    try:
        def exists(name, type_="table"):
            cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type=? AND name=?", (type_, name))
            return cur.fetchone() is not None

        for t in [
            "blocks","wells","daily_readings","acid_levels","acid_distribution",
            "rvr_types","rvr_events","analyses","users","settings","audit_log",
            "block_acidity_analyses","metal_analyses","well_mode_history",
            "block_mode_history","acid_tanks","tank_calibration","enums_current",
            "downtimes",
        ]:
            assert exists(t, "table"), f"missing table {t}"

        for v in [
            "v_daily_block_summary","v_acid_reconciliation","v_acid_levels_with_calc",
            "v_block_acidity_asof","v_block_metal_asof","v_well_metal_asof",
            "v_well_mode_on_date","v_block_mode_on_date",
        ]:
            assert exists(v, "view"), f"missing view {v}"
    finally:
        conn.close()
""",

    # ---------- app/sql/001_init_schema.sql ----------
    os.path.join("app","sql","001_init_schema.sql"): r"""-- 001_init_schema.sql
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
""",

    # ---------- app/sql/004_mode_history.sql ----------
    os.path.join("app","sql","004_mode_history.sql"): r"""PRAGMA foreign_keys = ON;

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
""",

    # ---------- app/sql/006_seed_mode_history.sql ----------
    os.path.join("app","sql","006_seed_mode_history.sql"): r"""PRAGMA foreign_keys = ON;

INSERT INTO well_mode_history(well_id, mode, date_from, date_to, note)
SELECT w.id, w.type, '1970-01-01', NULL, 'initial from design type'
FROM wells w
WHERE NOT EXISTS (SELECT 1 FROM well_mode_history h WHERE h.well_id = w.id);
""",

    # ---------- app/sql/007_analyses.sql ----------
    os.path.join("app","sql","007_analyses.sql"): r"""PRAGMA foreign_keys = ON;

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
""",

    # ---------- app/sql/008_block_mode_history.sql ----------
    os.path.join("app","sql","008_block_mode_history.sql"): r"""PRAGMA foreign_keys = ON;

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
""",

    # ---------- app/sql/009_tanks_calibration.sql ----------
    os.path.join("app","sql","009_tanks_calibration.sql"): r"""PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tank_calibration (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  tank_id   INTEGER NOT NULL REFERENCES acid_tanks(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  cm        INTEGER NOT NULL,
  tons      REAL NOT NULL,
  UNIQUE(tank_id, cm)
);
""",

    # ---------- app/sql/010_enums_current.sql ----------
    os.path.join("app","sql","010_enums_current.sql"): r"""PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS enums_current (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  type  TEXT NOT NULL CHECK (type IN ('VL','CELL','FLANK')),
  value TEXT NOT NULL,
  UNIQUE(type, value)
);
""",
}

def main():
    # create dirs
    for d in ["app/sql", "core/db", "data", "tests"]:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    # write files
    for rel_path, content in FILES.items():
        path = os.path.join(ROOT, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[write] {rel_path}")

    print("\nBootstrap complete. Next steps:")
    print("  pip install -r requirements.txt")
    print("  make migrate   (или: python core\\db\\migrate.py)")
    print("  make test")

if __name__ == "__main__":
    main()
