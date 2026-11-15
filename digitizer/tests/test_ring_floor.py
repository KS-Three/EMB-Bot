"""`cfg.extra["lettering_columns_ring_floor"]` (built OFF 2026-11-14): a small
letter's closed bowl keeps its thin crosses, widened to the floor, instead of
dropping them and opening the ring.

The eye sweep's fault 5: Bukit Asam's tagline "beyondcoal" sewed "b-y-n-d
cual" at 85.1 mm. Stages 4 and 5 kept every bowl. In the Column lane, under
`small_bold` (a letter under 5 mm), the o's ring column had 21 crosses of
0.47-0.63 mm. After the 0.11 mm rail inset and small_bold's 0.08 mm pull,
its thin top and bottom came out under the 0.5 mm floor and were dropped
while its sides kept twelve, so the bowl sewed as two brackets. Read on the
lane's own input (`testdata/bukit_tagline_lane_small_bowls.json`, from the
tracked art).
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, Polygon

from digitizer_core import columns, stitches
from digitizer_core.columns import _RING_FLOOR, ring_floor_scope

FIX = Path(__file__).resolve().parent.parent / "testdata" / "bukit_tagline_lane_small_bowls.json"


def _glyph(key: str):
    v = json.loads(FIX.read_text(encoding="utf-8"))[key]
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in v["kw"].items()}
    return Polygon(v["exterior"], v["holes"]), v["shape_id"], kw


def _sew(key: str, on: bool):
    poly, sid, kw = _glyph(key)
    with ring_floor_scope(on):
        runs, report = columns.lettering_columns_shape(poly, sid, **kw)
    return poly, runs, report


def _counter_needles(poly, runs) -> int:
    """satin needle points more than 0.1 mm inside a counter. A cross widened
    to the floor about its middle reaches up to 0.07 mm past the counter's
    edge on this tagline (the e's eye had one at 0.066 mm OFF already); the
    counter stays open, ~1 mm across."""
    holes = [Polygon(h).buffer(-0.1) for h in poly.interiors]
    return sum(1 for r in runs if r.kind == stitches.SATIN for p in r.points
               if any(h.contains(Point(p)) for h in holes))


def test_scope_off_is_the_lane_as_it_was():
    for key in ("o", "e", "a", "n"):
        poly, sid, kw = _glyph(key)
        plain, _ = columns.lettering_columns_shape(poly, sid, **kw)
        _p, off, _r = _sew(key, False)
        assert [(r.points, r.kind) for r in off] == [(r.points, r.kind) for r in plain]
    assert _RING_FLOOR.get() is False


def test_the_o_sews_closed_with_its_counter_open():
    poly, off, _ = _sew("o", False)
    _p, on, rep = _sew("o", True)
    assert columns.satin_cover(off, poly) < 0.8          # the bowl open: its top and bottom unsewn
    assert columns.satin_cover(on, poly) > 0.95
    assert rep.get("ring_floored") == 1 and rep["thin_crosses"] == 0
    assert _counter_needles(poly, on) == 0


def test_the_e_and_a_bowls_close():
    for key, floor in (("e", 0.85), ("a", 0.95)):
        poly, off, _ = _sew(key, False)
        _p, on, _r = _sew(key, True)
        assert columns.satin_cover(on, poly) > max(floor, columns.satin_cover(off, poly) + 0.05), key
        assert _counter_needles(poly, on) == 0, key


def test_a_letter_with_no_counter_does_not_move():
    _p, off, _ = _sew("n", False)
    _q, on, _r = _sew("n", True)
    assert [(r.points, r.kind) for r in on] == [(r.points, r.kind) for r in off]
