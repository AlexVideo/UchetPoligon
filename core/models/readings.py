from __future__ import annotations
from dataclasses import dataclass
from .common import DateStr

@dataclass
class DailyReading:
    date: DateStr
    block_id: int
    well_id: int
    pr_counter_prev_eff: float = 0.0
    pr_counter_curr: float = 0.0
    pr_hours: float = 0.0
    pr_downtime_h: float = 0.0
    vr_volume_m3: float = 0.0
    vr_hours: float = 0.0
    vr_downtime_h: float = 0.0
    rvr_type_id: int | None = None
    comment: str | None = None
    status: str = "draft"  # 'draft'|'validated'|'reconciled'|'approved'

@dataclass
class Downtime:
    date: DateStr
    block_id: int
    well_id: int | None
    hours: float
    reason: str | None = None
