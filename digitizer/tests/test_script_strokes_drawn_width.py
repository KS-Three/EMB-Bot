"""Script strokes sewn at the art's drawn width where they crowd
(`cfg.script_strokes_drawn_width`, built OFF 2026-10-27; Kent: "Build it OFF
(Recommended)").

With `script_strokes` a cross reaches the traced POLYGON on both sides, plus
the garment's pull. Where the trace fused two strokes the art draws apart
(Bridge's touching letters), each stroke's cross runs on into the other's ink
and the two threads lie on top of each other. With this flag a cross side
whose thread would run more than `CROWD_DEPTH_MM` into another stroke's stops
at the art's DRAWN half-width at the station; every other side is untouched.

The fixtures: BARS, two 1.2 mm strokes drawn 0.4 mm apart whose trace fused
them into one slab (the ink shows the gap); BAR, one of them alone; LOOPS,
`test_script_strokes`' joined cursive line, a word whose strokes do not crowd.
OFF is byte-identical (md5 pinned on the 2026-10-27 engine).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from shapely.geometry import LineString, box

from digitizer_core import PipelineConfig
from digitizer_core import script_strokes as SS
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_hairline import InkSource
from digitizer_core.stage7_sequence import sequence
from tests.conftest import frozen_cfg
from tests.test_script_strokes import LOOPS, _md5, _region

A = LineString([(0, 0), (12, 0)]).buffer(0.6, cap_style=2)
B = LineString([(0, 1.6), (12, 1.6)]).buffer(0.6, cap_style=2)
BARS_TRACE = box(0, -0.6, 12, 2.2)          # the gap between them traced shut
PULL = 0.4

#: md5s of `_word_runs(...)` / `_runs(LOOPS, ...)` on the 2026-10-27 engine;
#: the two OFF ones read the same on main (8341d1f7). LOOPS does not crowd,
#: so it sews the same ON
MD5 = {"bars_off": "ac5a08af949e8d728c6a255e829689a9", "bars_on": "89d46aba7a321619fdea8642fbcad82e",
       "loops_off": "326fa5bafba821f03680bb0fec7ddbf3", "loops_on": "326fa5bafba821f03680bb0fec7ddbf3"}


def _ink(drawn, frame, px_per_mm=12.0) -> InkSource:
    """`drawn` red on yellow, on a canvas round `frame` (the trace)."""
    import cv2
    x0, y0, x1, y1 = frame.bounds
    W, H = int((x1 - x0 + 6) * px_per_mm), int((y1 - y0 + 6) * px_per_mm)
    rgb = np.zeros((H, W, 3), np.uint8)
    rgb[:] = (230, 240, 90)
    origin = (W / 2.0 - (x0 + x1) / 2 * px_per_mm, H / 2.0 - (y0 + y1) / 2 * px_per_mm)
    for g in getattr(drawn, "geoms", [drawn]):
        cv2.fillPoly(rgb, [np.array([[x * px_per_mm + origin[0], y * px_per_mm + origin[1]]
                                     for x, y in g.exterior.coords], np.int32)], (230, 30, 40))
    return InkSource(rgb=rgb, alpha=None, bg=None, upscale=(1.0, 1.0),
                     px_per_mm=px_per_mm, origin_px=origin)


BARS_INK = _ink(A.union(B), BARS_TRACE)


def _columns(crowd: bool, trace=BARS_TRACE, ink=BARS_INK):
    return SS.script_columns(trace, 0.4, ink, crowd_pull_mm=PULL if crowd else None)[0]


def _word_runs(drawn_width: bool):
    runs, _report = SS.script_strokes_shape(BARS_TRACE, "Sword", trim_at_mm=3.0, spacing_mm=0.4,
                                            pull_mm=PULL, ink=BARS_INK, drawn_width=drawn_width)
    return runs


def _runs(poly, **cfg_kw):
    cfg = frozen_cfg(script_strokes=True, **cfg_kw)
    blocks, _ = sequence([PlannedRegion(region=_region(poly), polygon=poly, sew_index=0)],
                         fabric_for_garment("hat_front"), cfg)
    return [r for b in blocks for r in b.runs if r.shape_id == "Sword"]


def _stations_md5(cols) -> str:
    h = hashlib.md5()
    for c in cols:
        h.update(repr([((round(a[0], 6), round(a[1], 6)), (round(b[0], 6), round(b[1], 6)))
                       for a, b in c.stations]).encode())
    return h.hexdigest()


# ------------------------------------------------------------------- default
def test_default_off():
    assert PipelineConfig().script_strokes_drawn_width is False


def test_off_is_byte_identical():
    assert _md5(_word_runs(False)) == MD5["bars_off"]
    assert _md5(_runs(LOOPS)) == MD5["loops_off"]
    assert _md5(_runs(LOOPS, script_strokes_drawn_width=False)) == MD5["loops_off"]


def test_on_is_pinned():
    assert _md5(_word_runs(True)) == MD5["bars_on"]
    assert _md5(_runs(LOOPS, script_strokes_drawn_width=True)) == MD5["loops_on"]


# ------------------------------------------------------------------ the rule
def _sides(cols):
    """Per bar (A low, B high): the (lowest, highest) y its crosses reach, middle crosses."""
    out = []
    for c in sorted(cols, key=lambda c: np.mean([a[1] + b[1] for a, b in c.stations])):
        ys = [(min(a[1], b[1]), max(a[1], b[1])) for a, b in c.stations[4:-4]]
        out.append((float(np.median([y[0] for y in ys])), float(np.median([y[1] for y in ys]))))
    return out


def test_crowded_sides_stop_at_the_drawn_width():
    (a_lo, a_hi), (b_lo, b_hi) = _sides(_columns(False))
    assert a_hi > 1.1 and b_lo < 0.5            # OFF: each runs on into the other's ink
    (a_lo, a_hi), (b_lo, b_hi) = _sides(_columns(True))
    assert abs(a_hi - 0.6) < 0.1 and abs(b_lo - 1.0) < 0.1     # ON: at the drawn edge


def test_sides_that_do_not_crowd_still_reach_the_polygon():
    (a_lo, _), (_, b_hi) = _sides(_columns(True))
    assert abs(a_lo - -0.6) < 0.02 and abs(b_hi - 2.2) < 0.02
    # a stroke with nothing to crowd sews exactly as before
    alone = _ink(A, A)
    assert _stations_md5(_columns(True, A, alone)) == _stations_md5(_columns(False, A, alone))


def test_the_thread_laid_twice_halves_and_the_pull_covers_the_gap():
    off = SS.crowd_share([SS.sewn_ribbon(c.stations, PULL) for c in _columns(False)])
    on = SS.crowd_share([SS.sewn_ribbon(c.stations, PULL) for c in _columns(True)])
    assert off > 0.3 and on < 0.6 * off
    # the traced-shut gap between the drawn edges is wider than half a thread
    # but the pull lays thread over it: a patch there would sew it twice
    cols = _columns(True)
    assert sum(p.area for p in SS.uncovered(BARS_TRACE, cols)) > 0.2
    assert not SS.uncovered(BARS_TRACE, cols, PULL)
    _runs_, report = SS.script_strokes_shape(BARS_TRACE, "Sword", trim_at_mm=3.0, spacing_mm=0.4,
                                             pull_mm=PULL, ink=BARS_INK, drawn_width=True)
    assert report["script_patches"] == 0
    # and nothing of the trace is left bare once the pull is counted
    sewn = [SS.sewn_ribbon(c.stations, PULL) for c in cols]
    from shapely.ops import unary_union
    assert BARS_TRACE.difference(unary_union(sewn)).area < 0.05


def test_only_a_word_that_crowds_is_cut():
    """The word gate: BARS lay over a third of their thread twice, so they are
    cut; LOOPS (one pen line, its crossings the only overlap) are under the
    pro's 10.5 % and sew byte for byte as before."""
    loops = SS.script_columns(LOOPS, 0.4)[0]
    assert SS.crowd_share([SS.sewn_ribbon(c.stations, PULL) for c in loops]) < SS.CROWD_WORD_SHARE
    _r, on = SS.script_strokes_shape(BARS_TRACE, "Sword", trim_at_mm=3.0, spacing_mm=0.4,
                                     pull_mm=PULL, ink=BARS_INK, drawn_width=True)
    _r, off = SS.script_strokes_shape(BARS_TRACE, "Sword", trim_at_mm=3.0, spacing_mm=0.4,
                                      pull_mm=PULL, ink=BARS_INK)
    assert on["script_crowded"] == 1 and "script_crowded" not in off


def test_the_thresholds_are_the_pros():
    # his median overlap depth on Bridge hat / LC / To a T: 0.99 / 1.11 / 1.03 mm
    assert SS.CROWD_DEPTH_MM == 1.0
    # his most thread laid twice on any script word (Bridge hat)
    assert SS.CROWD_WORD_SHARE == 0.105
    assert math.isclose(SS._THREAD_HALF_MM, 0.2)
