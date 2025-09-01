from __future__ import annotations
from dataclasses import dataclass
from .common import DateStr

@dataclass
class AcidTank:
    id: int | None
    name: str
    capacity_t: float | None = None
    location: str | None = None
    height_cm: int | None = None
    is_active: int = 1

@dataclass
class TankCalibration:
    tank_id: int
    cm: int
    tons: float

@dataclass
class AcidLevel:
    date: DateStr
    tank_id: int
    level_begin_t: float
    level_end_t: float
    level_begin_cm: int | None = None
    level_end_cm: int | None = None
    receipts_t: float = 0.0
    transfers_in_t: float = 0.0
    transfers_out_t: float = 0.0
    adjustments_t: float = 0.0
    note: str | None = None

@dataclass
class AcidDistribution:
    date: DateStr
    block_id: int
    acid_tons: float
    method: str = "VR-share"
    note: str | None = None
