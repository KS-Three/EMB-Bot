"""Pins the 2026-10-08 measured negative on stage 5's `_largest_polygon`.

`resolve_overlaps` keeps only the largest piece of each grown shape. Measured
on five real logos at 80 and 120 mm (`tools/stage5_split_loss.py`): every
dropped ARTWORK piece sat under the `min_detail_mm` floor (largest 1.77 mm²
against 2.25), and almost all of it is covered by another colour's grown
polygon -- 0.43 mm² bare at worst. So no cure was built. If this starts
failing, the drop has begun to cost real artwork and the cure (keep pieces at
or over the floor) is back on the table.
"""
from pathlib import Path

import pytest

from tools.stage5_split_loss import measure

ART = Path(__file__).resolve().parents[1] / "testdata" / "art"


# One logo, ~12 s: logo_mfab_lc splits the most at 80 mm (10 pieces). The
# other four measured the same way and cost 45 s apiece (logo_toat_beanie).
@pytest.mark.parametrize("name,width", [("logo_mfab_lc.png", 80.0)])
def test_largest_polygon_drops_no_piece_over_floor(name, width):
    r = measure(str(ART / name), width)
    assert r["pieces_over_floor"] == 0, r
    assert r["largest_piece_mm2"] < r["floor_mm2"], r
    assert r["bare_mm2"] < 1.0, r
