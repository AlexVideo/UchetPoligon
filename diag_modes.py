from core.db.dao import Database

db = Database()
# Воспроизводим ровно то, что делает тест:
b1 = db.create_block("B_TMP1", area_m2=1.0, horizon_power=1.0)
b2 = db.create_block("B_TMP2", area_m2=2.0, horizon_power=2.0)
w1 = db.create_well(b1, "PR-1", "PR", coord_x=100.0, coord_y=200.0)
w2 = db.create_well(b2, "VR-1", "VR", coord_x=110.0, coord_y=210.0)

db.add_well_mode_interval(w2, "VR", "2025-06-01", "2025-06-30")
db.add_well_mode_interval(w2, "PR", "2025-07-01", None)

print("w2 =", w2)
with db.connect() as con:
    print("\n-- rows in well_mode_history for w2 --")
    for r in con.execute("SELECT well_id, mode, date_from, date_to FROM well_mode_history WHERE well_id=? ORDER BY date_from", (w2,)):
        print(r)

    # Попробуем тем же SQL, что в функции
    row = con.execute("""
        SELECT mode
        FROM well_mode_history
        WHERE well_id = ?
          AND substr(date_from,1,10) <= ?
          AND (date_to IS NULL OR substr(date_to,1,10) >= ?)
        ORDER BY substr(date_from,1,10) DESC
        LIMIT 1
    """, (w2, "2025-06-25", "2025-06-25")).fetchone()
    print("\nselected mode for 2025-06-25 =", None if not row else row.get("mode"))

print("\nmode_of_well_on(...) ->", db.mode_of_well_on(w2, "2025-06-25"))
