"""Pins the 2026-10-08 measured negative on stage 5's `_largest_polygon`.

`resolve_overlaps` keeps only the largest piece of each grown shape. Measured
on five real logos at 80 and 120 mm (`tools/stage5_split_loss.py`): every
dropped ARTWORK piece sat under the `min_detail_mm` floor (largest 1.77 mm²
against 2.25), and almost all of it is covered by another colour's grown
polygon -- 0.43 mm² bare at worst. So no cure was built. If this starts
failing, the drop has begun to cost real artwork and the cure (keep pieces at
or over the floor) is back on the table.

Since 2026-10-12 the shipped path keeps the piece carrying the most artwork
(`cfg.clip_parent_keeps_ink`, default ON) rather than the largest, through
`_split_clip` instead of `_largest_polygon`; extra pieces over the floor are
kept since 2026-10-20 (`cfg.clip_keep_pieces`, ON). `tools/stage5_split_loss.measure`
spies on BOTH, so this still reads the default path -- and the test asserts
the spy saw pieces, because a spy on a function the engine no longer calls
reads zero and passes.

Since 2026-10-20 `cfg.subpixel_corner_runs` is ON (Kent's ruling), and with it
logo_mfab_lc at 80 mm splits NOTHING -- the repaired corners leave no sliver
for the clip to cut off. So the reach is read on the engine the 10 pieces
were measured on (`PRE_FLIP`), and the property on both.
"""
from pathlib import Path

import pytest

from tests.conftest import PRE_FLIP
from tools.stage5_split_loss import measure

ART = Path(__file__).resolve().parents[1] / "testdata" / "art"


# One logo, ~12 s: logo_mfab_lc splits the most at 80 mm (10 pieces). The
# other four measured the same way and cost 45 s apiece (logo_toat_beanie).
@pytest.mark.parametrize("name,width", [("logo_mfab_lc.png", 80.0)])
def test_largest_polygon_drops_no_piece_over_floor(name, width):
    pre = measure(str(ART / name), width, subpixel_corner_runs=PRE_FLIP["subpixel_corner_runs"])
    # Reach: the spy must see the splits at all (10 pieces measured 2026-10-08).
    assert pre["pieces"] > 0, pre
    for r in (pre, measure(str(ART / name), width)):
        assert r["pieces_over_floor"] == 0, r
        assert r["largest_piece_mm2"] < r["floor_mm2"], r
        assert r["bare_mm2"] < 1.0, r
