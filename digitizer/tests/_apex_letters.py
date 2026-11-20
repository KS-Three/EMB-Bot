"""Shared fixtures of the apex-family letter tests (`apex_pro`, `apex_pro_joints`, the flat A's cap,
`fold_cap_flared`): the captured MARINE / MFab letters and the Column lane's call arguments.

Kept from `tests/test_column_apex_cut.py`, deleted 2026-11-19 with the `lettering_columns_apex_cut` flag
(docs/flag-history/tier-d.md).

`testdata/apex_letters.json`: MARINE's M and N at 76.5 mm Hat (Becker hat small) and MFab's W and N at
104.9 mm Hat, each as stage 7 handed it to the lane (polygon and keyword arguments, `corner_fold` on, as
#1057 flips it), captured 2026-10-25 from main at 82b0bf28; MARINE's M at 95.7 mm (LC large) and A at
101.9 mm (hat large) likewise; and MARINE's M at 101.9 mm, its region polygon only (`cut_only`).
"""
from __future__ import annotations

import math
from pathlib import Path

from shapely.geometry import Polygon

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "apex_letters.json"
LANE = dict(fold_cuts=True, mitre_ends=True, rail_axis=True)


def _v(half_deg: float = 20.0, w: float = 1.2, h: float = 8.0) -> Polygon:
    """A V: two `w`-wide strokes `2 * half_deg` apart, meeting at a point
    (0, h) at the bottom (y down), the crotch on the axis above it."""
    a = math.radians(half_deg)
    xo = h * math.tan(a)
    xi = xo - w / math.cos(a)
    yc = h - (w / math.cos(a)) / math.tan(a)
    return Polygon([(-xo, 0), (-xi, 0), (0, yc), (xi, 0), (xo, 0), (0, h)])
