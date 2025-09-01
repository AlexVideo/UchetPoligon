import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), "data", "uchet.db")
DATE = "2025-07-15"

con = sqlite3.connect(DB)
cur = con.cursor()

# Чистим данные на тестовую дату, чтобы суммарный VR был ровно 100 (30+70)
cur.execute("DELETE FROM acid_distribution WHERE date=?", (DATE,))
cur.execute("DELETE FROM daily_readings   WHERE date=?", (DATE,))
cur.execute("DELETE FROM acid_levels      WHERE date=?", (DATE,))

# На всякий случай уберём тестовый бак, чтобы не было коллизий имён
cur.execute("DELETE FROM acid_tanks WHERE name='ССК-1'")

con.commit()
con.close()
print("OK: cleaned test day", DATE)
