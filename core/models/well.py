from __future__ import annotations
from dataclasses import dataclass
from .common import DateStr

@dataclass
class Well:
    id: int | None
    block_id: int
    well_no: str
    type: str  # 'PR' | 'VR' | 'OBS' | 'OTHER'  (design type)
    current_mode: str | None = None
    depth_m: float | None = None
    filter_type: str | None = None
    coord_x: float | None = None
    coord_y: float | None = None
    coord_z: float | None = None
    filter_from_m: float | None = None
    filter_to_m: float | None = None
    coord_sys: str | None = "local"
    status: str | None = "active"

@dataclass
class WellModeInterval:
    well_id: int
    mode: str        # 'PR' | 'VR' | 'OBS' | 'OTHER'
    date_from: DateStr
    date_to: DateStr | None = None
    note: str | None = None
