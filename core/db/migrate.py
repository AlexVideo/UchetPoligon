from __future__ import annotations
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
