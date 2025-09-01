from __future__ import annotations
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
