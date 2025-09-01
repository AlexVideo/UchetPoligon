from __future__ import annotations
import os, random, string
from core.db.dao import Database

def _rnd_suffix(n=4) -> str:
    return "".join(random.choice(string.ascii_uppercase) for _ in range(n))

def test_dao_end_to_end():
    db = Database()  # использует data/uchet.db

    # 1) Блоки и скважины
    bno1 = f"B_TEST_{_rnd_suffix()}"
    bno2 = f"B_TEST_{_rnd_suffix()}"
    b1 = db.create_block(bno1, area_m2=1000.0, horizon_power=5.5)
    b2 = db.create_block(bno2, area_m2=2000.0, horizon_power=6.0)

    w1 = db.create_well(b1, "PR-1", "PR", coord_x=100.0, coord_y=200.0)
    w2 = db.create_well(b2, "VR-1", "VR", coord_x=110.0, coord_y=210.0)

    # 2) История режимов скважины: w2 был VR, с 2025-07-01 стал PR
    db.add_well_mode_interval(w2, "VR", "2025-06-01", "2025-06-30")
    db.add_well_mode_interval(w2, "PR", "2025-07-01", None)
    assert db.mode_of_well_on(w2, "2025-06-25") == "VR"
    assert db.mode_of_well_on(w2, "2025-07-05") == "PR"

    # 3) Анализы: кислотность по блоку (as-of), металл по блоку и скважине
    db.insert_block_acidity("2025-07-10", b1, "acid_ph", 2.8)
    db.insert_block_acidity("2025-07-12", b1, "acid_ph", 3.0)   # более свежая
    assert db.block_acidity_asof("2025-07-11", b1, "acid_ph") == 2.8
    assert db.block_acidity_asof("2025-07-12", b1, "acid_ph") == 3.0
    assert db.block_acidity_asof("2025-07-15", b1, "acid_ph") == 3.0

    db.insert_metal_analysis("2025-07-01", b1, 0.9, None)  # блоковая
    db.insert_metal_analysis("2025-07-05", b1, 1.1, None)
    db.insert_metal_analysis("2025-07-03", b1, 1.5, w1)    # по скважине
    assert db.block_metal_asof("2025-07-02", b1) == 0.9
    assert db.block_metal_asof("2025-07-06", b1) == 1.1
    assert db.well_metal_asof("2025-07-04", w1) == 1.5

    # 4) Суточные данные: VR суммарно 30 (b1) и 70 (b2); PR по w1 — по счётчикам
    #    Дата 2025-07-15
    db.insert_daily_reading({
        "date": "2025-07-15", "block_id": b1, "well_id": w1,
        "pr_counter_prev_eff": 120.0, "pr_counter_curr": 150.0, "pr_hours": 10.0,
        "vr_volume_m3": 30.0, "vr_hours": 5.0
    })
    db.insert_daily_reading({
        "date": "2025-07-15", "block_id": b2, "well_id": w2,
        "pr_counter_prev_eff":  50.0, "pr_counter_curr":  50.0, "pr_hours": 0.0,
        "vr_volume_m3": 70.0, "vr_hours": 7.0
    })
    summary1 = db.daily_block_summary("2025-07-15", b1)
    assert round(summary1["pr_m3"], 3) == 30.0  # 150-120
    assert round(summary1["vr_m3"], 3) == 30.0

    # 5) ССК: один бак, расход 10 т за день → распределим 3/7
    tank_id = db.insert_tank("ССК-1", capacity_t=100.0, location="Полигон-1")
    # уровни: было 100 → стало 90, приходов нет, переливов нет, расход = 10 т
    db.insert_acid_level({
        "date": "2025-07-15", "tank_id": tank_id,
        "level_begin_t": 100.0, "level_end_t": 90.0,
        "receipts_t": 0.0, "transfers_in_t": 0.0, "transfers_out_t": 0.0, "adjustments_t": 0.0
    })
    res = db.compute_and_store_acid_distribution_vr_share("2025-07-15")
    # ожидаем распределение 10 т пропорционально 30/70
    by_block = {r["block_id"]: r["acid_tons"] for r in res}
    assert round(by_block[b1], 3) == 3.0
    assert round(by_block[b2], 3) == 7.0
