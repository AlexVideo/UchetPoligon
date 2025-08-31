from __future__ import annotations
import os
import sqlite3

# -------------------------------------------------------------------
# Пути и базовые настройки
# -------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB = os.path.join(ROOT, "data", "uchet.db")

def _row_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# -------------------------------------------------------------------
# Ошибки DAO
# -------------------------------------------------------------------
class DaoError(Exception):
    """Базовая ошибка DAO."""

class ValidationError(DaoError):
    """Неверные входные данные."""

class UniqueConstraintError(DaoError):
    """Нарушение уникального ограничения."""

class ForeignKeyError(DaoError):
    """Нарушение внешнего ключа."""

class MissingTableError(DaoError):
    """Таблица/представление не существует (нет миграции)."""

def _map_integrity_error(e: sqlite3.IntegrityError) -> DaoError:
    msg = str(e)
    if "UNIQUE constraint failed" in msg:
        return UniqueConstraintError(msg)
    if "FOREIGN KEY constraint failed" in msg or "foreign key constraint failed" in msg:
        return ForeignKeyError(msg)
    return DaoError(msg)

def _map_operational_error(e: sqlite3.OperationalError) -> DaoError:
    msg = str(e)
    if "no such table" in msg or "no such view" in msg:
        return MissingTableError(msg)
    return DaoError(msg)

def _require_non_empty(name: str, value: str) -> str:
    s = (value or "").strip()
    if not s:
        raise ValidationError(f"{name} is required and cannot be empty.")
    return s

def _require_positive_int(name: str, value: int) -> int:
    try:
        iv = int(value)
    except Exception:
        raise ValidationError(f"{name} must be an integer.")
    if iv <= 0:
        raise ValidationError(f"{name} must be > 0.")
    return iv

# -------------------------------------------------------------------
# Класс доступа к БД
# -------------------------------------------------------------------
class Database:
    """Простой DAO поверх SQLite. Без внешних зависимостей."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = _row_factory
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    # Унифицированный запуск запросов с аккуратной обработкой ошибок
    def _exec(self, con: sqlite3.Connection, sql: str, params=()):
        try:
            return con.execute(sql, params)
        except sqlite3.IntegrityError as e:
            raise _map_integrity_error(e)
        except sqlite3.OperationalError as e:
            raise _map_operational_error(e)
        except sqlite3.Error as e:
            raise DaoError(str(e))

    # ----------------------------------------------------------------
    # Blocks
    # ----------------------------------------------------------------
    def create_block(self, block_no: str, **kw) -> int:
        """
        Создаёт блок.
        Обязателен только block_no; остальные поля получают безопасные НЕ-NULL дефолты,
        чтобы не падать на схемах, где стоят NOT NULL или где тесты ругаются на NULL.
        """
        block_no = _require_non_empty("block_no", block_no)

        sql = """
        INSERT INTO blocks(block_no, flank, vl, cell, area_m2, horizon_power, ore_mass_t, regime, shape_wkt)
        VALUES(:block_no, :flank, :vl, :cell, :area_m2, :horizon_power, :ore_mass_t, :regime, :shape_wkt)
        """
        try:
            params = {
                "block_no": block_no,
                "flank": kw.get("flank", ""),                 # НЕ-NULL текст
                "vl": kw.get("vl", ""),                       # НЕ-NULL текст
                "cell": kw.get("cell", ""),                   # НЕ-NULL текст
                "area_m2": kw.get("area_m2", 0.0),            # НЕ-NULL число
                "horizon_power": kw.get("horizon_power", 0.0),
                "ore_mass_t": kw.get("ore_mass_t", 0.0),
                "regime": kw.get("regime", ""),               # НЕ-NULL текст
                "shape_wkt": kw.get("shape_wkt", ""),         # НЕ-NULL текст (пусть будет пустая строка)
            }
        except Exception as e:
            raise ValidationError(f"Invalid block parameters: {e}")

        with self.connect() as con:
            cur = self._exec(con, sql, params)
            return cur.lastrowid


    def get_block_by_no(self, block_no: str) -> dict | None:
        with self.connect() as con:
            cur = con.execute("SELECT * FROM blocks WHERE block_no = ?", (block_no,))
            return cur.fetchone()

    def list_blocks(self) -> list[dict]:
        with self.connect() as con:
            return list(con.execute("SELECT * FROM blocks ORDER BY id"))

    # ----------------------------------------------------------------
    # Wells
    # ----------------------------------------------------------------
    def create_well(self, block_id: int, well_no: str, well_type: str | None = None, **kw) -> int:
        """
        Создаёт скважину.
        Минимально: block_id, well_no, well_type (совместимо с legacy 'type' через **kw).
        Все плейсхолдеры получают НЕ-NULL значения по умолчанию.
        """
        if well_type is None and "type" in kw:
            well_type = kw.pop("type")

        block_id = _require_positive_int("block_id", block_id)
        well_no = _require_non_empty("well_no", well_no)
        well_type = _require_non_empty("well_type", well_type)

        sql = """
        INSERT INTO wells(block_id, well_no, type, current_mode, depth_m, filter_type, coord_x, coord_y, coord_z,
                        filter_from_m, filter_to_m, coord_sys, status)
        VALUES(:block_id, :well_no, :type, :current_mode, :depth_m, :filter_type, :coord_x, :coord_y, :coord_z,
            :filter_from_m, :filter_to_m, :coord_sys, :status)
        """
        try:
            params = {
                "block_id": block_id,
                "well_no": well_no,
                "type": well_type,                      # столбец в БД называется 'type'
                "current_mode": kw.get("current_mode", ""),   # НЕ-NULL текст
                "depth_m": kw.get("depth_m", 0.0),            # НЕ-NULL число
                "filter_type": kw.get("filter_type", ""),     # НЕ-NULL текст
                "coord_x": kw.get("coord_x", 0.0),
                "coord_y": kw.get("coord_y", 0.0),
                "coord_z": kw.get("coord_z", 0.0),
                "filter_from_m": kw.get("filter_from_m", 0.0),
                "filter_to_m": kw.get("filter_to_m", 0.0),
                "coord_sys": kw.get("coord_sys", "local"),    # уже НЕ-NULL
                "status": kw.get("status", "active"),         # уже НЕ-NULL
            }
        except Exception as e:
            raise ValidationError(f"Invalid well parameters: {e}")

        with self.connect() as con:
            cur = self._exec(con, sql, params)
            return cur.lastrowid


    def list_wells_by_block(self, block_id: int) -> list[dict]:
        with self.connect() as con:
            return list(con.execute("SELECT * FROM wells WHERE block_id=? ORDER BY id", (block_id,)))

    # ----------------------------------------------------------------
    # Modes (well / block)
    # ----------------------------------------------------------------
    def add_well_mode_interval(self, well_id: int, mode: str, date_from: str,
                               date_to: str | None = None, note: str | None = None):
        sql = "INSERT INTO well_mode_history(well_id, mode, date_from, date_to, note) VALUES(?,?,?,?,?)"
        with self.connect() as con:
            self._exec(con, sql, (well_id, mode, date_from, date_to, note))

    def mode_of_well_on(self, well_id: int, date: str) -> str | None:
        """
        Режим скважины на дату (включительно) без view.
        Сравниваем даты как ISO-текст; поддерживает значения с временем.
        """
        sql = """
        SELECT mode
        FROM well_mode_history
        WHERE well_id = ?
        AND substr(date_from,1,10) <= ?
        AND (date_to IS NULL OR substr(date_to,1,10) >= ?)
        ORDER BY substr(date_from,1,10) DESC, id DESC
        LIMIT 1
        """
        with self.connect() as con:
            row = con.execute(sql, (well_id, date, date)).fetchone()
            return row["mode"] if row else None






    def add_block_mode_interval(self, block_id: int, mode: str, date_from: str,
                                date_to: str | None = None, note: str | None = None):
        sql = "INSERT INTO block_mode_history(block_id, mode, date_from, date_to, note) VALUES(?,?,?,?,?)"
        with self.connect() as con:
            self._exec(con, sql, (block_id, mode, date_from, date_to, note))

    def mode_of_block_on(self, block_id: int, date: str) -> str | None:
        sql = """
        SELECT mode
        FROM block_mode_history
        WHERE block_id = ?
        AND substr(date_from,1,10) <= ?
        AND (date_to IS NULL OR substr(date_to,1,10) >= ?)
        ORDER BY substr(date_from,1,10) DESC, id DESC
        LIMIT 1
        """
        with self.connect() as con:
            row = con.execute(sql, (block_id, date, date)).fetchone()
            return row["mode"] if row else None





    # ----------------------------------------------------------------
    # Daily readings
    # ----------------------------------------------------------------
    def insert_daily_reading(self, dr: dict) -> int:
        """
        Вставка суточных показаний по скважине.
        Часть полей имеет дефолт 0.0, чтобы упрощать ввод.
        """
        fields = ("date, block_id, well_id, pr_counter_prev_eff, pr_counter_curr, pr_hours, pr_downtime_h, "
                  "vr_volume_m3, vr_hours, vr_downtime_h, rvr_type_id, comment, status")
        placeholders = ",".join("?" for _ in fields.split(","))
        sql = f"INSERT INTO daily_readings({fields}) VALUES({placeholders})"
        values = (
            dr.get("date"), dr.get("block_id"), dr.get("well_id"),
            dr.get("pr_counter_prev_eff", 0.0), dr.get("pr_counter_curr", 0.0),
            dr.get("pr_hours", 0.0), dr.get("pr_downtime_h", 0.0),
            dr.get("vr_volume_m3", 0.0), dr.get("vr_hours", 0.0), dr.get("vr_downtime_h", 0.0),
            dr.get("rvr_type_id"), dr.get("comment"), dr.get("status", "draft"),
        )
        with self.connect() as con:
            cur = self._exec(con, sql, values)
            return cur.lastrowid

    def daily_block_summary(self, date: str, block_id: int) -> dict | None:
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM v_daily_block_summary WHERE date=? AND block_id=?",
                (date, block_id),
            )
            return cur.fetchone()

    # ----------------------------------------------------------------
    # Analyses
    # ----------------------------------------------------------------
    def insert_block_acidity(self, date: str, block_id: int, metric_name: str, value: float,
                             sample_no=None, lab_name=None, note=None) -> None:
        sql = """
        INSERT INTO block_acidity_analyses(date, block_id, metric_name, value, sample_no, lab_name, note)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(date, block_id, metric_name) DO UPDATE SET
          value=excluded.value, sample_no=excluded.sample_no, lab_name=excluded.lab_name, note=excluded.note
        """
        with self.connect() as con:
            self._exec(con, sql, (date, block_id, metric_name, value, sample_no, lab_name, note))

    def insert_metal_analysis(self, date: str, block_id: int, metal_gpl: float,
                              well_id: int | None = None, sample_no=None, lab_name=None, note=None) -> None:
        sql = """
        INSERT INTO metal_analyses(date, block_id, well_id, metal_gpl, sample_no, lab_name, note)
        VALUES(?,?,?,?,?,?,?)
        """
        with self.connect() as con:
            self._exec(con, sql, (date, block_id, well_id, metal_gpl, sample_no, lab_name, note))

    def block_acidity_asof(self, date: str, block_id: int, metric_name: str) -> float | None:
        """
        Возвращает «as of» кислотность: последняя запись ≤ date для блока+метрики.
        Без view, сравнение по ISO-дате (работает и если в БД есть время).
        """
        sql = """
        SELECT value
        FROM block_acidity_analyses
        WHERE block_id = ?
        AND metric_name = ?
        AND substr(date,1,10) <= ?
        ORDER BY substr(date,1,10) DESC, id DESC
        LIMIT 1
        """
        with self.connect() as con:
            row = con.execute(sql, (block_id, metric_name, date)).fetchone()
            return row["value"] if row else None


    def block_metal_asof(self, date: str, block_id: int) -> float | None:
        """
        «As of» металл по блоку: берём последнюю запись ≤ date.
        Сначала пытаемся взять блочную запись (well_id IS NULL),
        если её нет — берём последнюю среди любых скважин блока.
        """
        sql_block = """
        SELECT metal_gpl
        FROM metal_analyses
        WHERE block_id = ?
        AND well_id IS NULL
        AND substr(date,1,10) <= ?
        ORDER BY substr(date,1,10) DESC, id DESC
        LIMIT 1
        """
        sql_any = """
        SELECT metal_gpl
        FROM metal_analyses
        WHERE block_id = ?
        AND substr(date,1,10) <= ?
        ORDER BY substr(date,1,10) DESC, id DESC
        LIMIT 1
        """
        with self.connect() as con:
            r = con.execute(sql_block, (block_id, date)).fetchone()
            if r:
                return r["metal_gpl"]
            r = con.execute(sql_any, (block_id, date)).fetchone()
            return r["metal_gpl"] if r else None


    def well_metal_asof(self, date: str, well_id: int) -> float | None:
        """
        «As of» металл по скважине: последняя запись ≤ date.
        """
        sql = """
        SELECT metal_gpl
        FROM metal_analyses
        WHERE well_id = ?
        AND substr(date,1,10) <= ?
        ORDER BY substr(date,1,10) DESC, id DESC
        LIMIT 1
        """
        with self.connect() as con:
            row = con.execute(sql, (well_id, date)).fetchone()
            return row["metal_gpl"] if row else None


    # ----------------------------------------------------------------
    # Tanks & Levels (ССК)
    # ----------------------------------------------------------------
    def insert_tank(self, name: str, capacity_t: float | None = None, location: str | None = None,
                    height_cm: int | None = None, is_active: int = 1) -> int:
        """
        Идемпотентная вставка бака: если name уже есть — обновляем поля (где не None) и возвращаем id.
        Это устраняет падение на UNIQUE при повторных прогонах тестов.
        """
        upsert_sql = """
        INSERT INTO acid_tanks(name, capacity_t, location, height_cm, is_active)
        VALUES(?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
            capacity_t = COALESCE(excluded.capacity_t, acid_tanks.capacity_t),
            location   = COALESCE(excluded.location,   acid_tanks.location),
            height_cm  = COALESCE(excluded.height_cm,  acid_tanks.height_cm),
            is_active  = excluded.is_active
        """
        with self.connect() as con:
            try:
                # пробуем UPSERT
                self._exec(con, upsert_sql, (name, capacity_t, location, height_cm, is_active))
            except UniqueConstraintError:
                # на старых SQLite без UPSERT это не должно понадобиться, но оставим как страховку
                pass
            # в любом случае возвращаем id существующей/вставленной записи
            row = con.execute("SELECT id FROM acid_tanks WHERE name=?", (name,)).fetchone()
            return row["id"]


    def add_tank_calib(self, tank_id: int, cm: int, tons: float) -> None:
        sql = """
        INSERT INTO tank_calibration(tank_id, cm, tons)
        VALUES(?,?,?)
        ON CONFLICT(tank_id, cm) DO UPDATE SET tons=excluded.tons
        """
        with self.connect() as con:
            self._exec(con, sql, (tank_id, cm, tons))

    def insert_acid_level(self, al: dict) -> int:
        """
        Идемпотентная запись уровней ССК на дату: если (date, tank_id) уже есть —
        обновляем значения. Возвращаем id строки.
        """
        sql = """
        INSERT INTO acid_levels(
            date, tank_id,
            level_begin_t, level_end_t, level_begin_cm, level_end_cm,
            receipts_t, transfers_in_t, transfers_out_t, adjustments_t, note
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(date, tank_id) DO UPDATE SET
            level_begin_t   = excluded.level_begin_t,
            level_end_t     = excluded.level_end_t,
            level_begin_cm  = excluded.level_begin_cm,
            level_end_cm    = excluded.level_end_cm,
            receipts_t      = excluded.receipts_t,
            transfers_in_t  = excluded.transfers_in_t,
            transfers_out_t = excluded.transfers_out_t,
            adjustments_t   = excluded.adjustments_t,
            note            = excluded.note
        """
        values = (
            al.get("date"),
            al.get("tank_id"),
            al.get("level_begin_t"),
            al.get("level_end_t"),
            al.get("level_begin_cm"),
            al.get("level_end_cm"),
            al.get("receipts_t", 0.0),
            al.get("transfers_in_t", 0.0),
            al.get("transfers_out_t", 0.0),
            al.get("adjustments_t", 0.0),
            al.get("note"),
        )
        with self.connect() as con:
            self._exec(con, sql, values)
            row = con.execute(
                "SELECT id FROM acid_levels WHERE date=? AND tank_id=?",
                (al.get("date"), al.get("tank_id")),
            ).fetchone()
            return row["id"]


    # ----------------------------------------------------------------
    # Acid distribution (VR-share)
    # ----------------------------------------------------------------
    def compute_and_store_acid_distribution_vr_share(self, date: str) -> list[dict]:
        """
        Распределяем расход склада кислоты за указанный день пропорционально VR по блокам.
        Расход считаем НАПРЯМУЮ из acid_levels за эту дату:
        consumption_t = SUM(level_begin_t + receipts_t + transfers_in_t
                            - transfers_out_t + adjustments_t - level_end_t)
        Если total_t <= 0 или total_vr <= 0 — удаляем записи на эту дату и возвращаем [].
        """
        with self.connect() as con:
            # 1) посчитать расход по баку(ам) на эту дату
            row = con.execute(
                """
                SELECT
                COALESCE(SUM(
                    COALESCE(level_begin_t,0) + COALESCE(receipts_t,0) + COALESCE(transfers_in_t,0)
                    - COALESCE(transfers_out_t,0) + COALESCE(adjustments_t,0)
                    - COALESCE(level_end_t,0)
                ), 0) AS consumption_t
                FROM acid_levels
                WHERE date = ?
                """,
                (date,),
            ).fetchone()
            total_t = float(row["consumption_t"] or 0.0)

            # 2) VR по блокам за эту же дату
            vr_rows = list(con.execute(
                "SELECT block_id, SUM(vr_volume_m3) AS vr_m3 FROM daily_readings WHERE date=? GROUP BY block_id",
                (date,),
            ))
            total_vr = sum((r["vr_m3"] or 0.0) for r in vr_rows)

            results: list[dict] = []
            if total_t > 0 and total_vr > 0:
                for r in vr_rows:
                    share = (r["vr_m3"] or 0.0) / total_vr
                    acid_tons = total_t * share
                    self._exec(con, """
                        INSERT INTO acid_distribution(date, block_id, acid_tons, method, note)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(date, block_id) DO UPDATE SET
                        acid_tons=excluded.acid_tons, method=excluded.method, note=excluded.note
                    """, (date, r["block_id"], acid_tons, "VR-share", None))
                    results.append({"block_id": r["block_id"], "acid_tons": acid_tons})
            else:
                # нечего распределять — очистим записи на эту дату, чтобы не было мусора
                self._exec(con, "DELETE FROM acid_distribution WHERE date=?", (date,))
            return results






