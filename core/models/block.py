from __future__ import annotations
from dataclasses import dataclass
from .common import DateStr

@dataclass
class Block:
    id: int | None
    block_no: str
    flank: str | None = None
    vl: str | None = None
    cell: str | None = None
    area_m2: float | None = None
    horizon_power: float | None = None
    ore_mass_t: float | None = None
    regime: str | None = None
    shape_wkt: str | None = None

@dataclass
class BlockModeInterval:
    block_id: int
    mode: str
    date_from: DateStr
    date_to: DateStr | None = None
    note: str | None = None
