from __future__ import annotations
from dataclasses import dataclass
from .common import DateStr

@dataclass
class BlockAcidity:
    date: DateStr
    block_id: int
    metric_name: str  # 'acid_ph' | 'acid_gpl' ...
    value: float
    sample_no: str | None = None
    lab_name: str | None = None
    note: str | None = None

@dataclass
class MetalAnalysis:
    date: DateStr
    block_id: int
    well_id: int | None  # None = блоковая проба
    metal_gpl: float
    sample_no: str | None = None
    lab_name: str | None = None
    note: str | None = None
