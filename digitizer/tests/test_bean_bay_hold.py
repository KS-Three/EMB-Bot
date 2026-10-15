"""`cfg.bean_letter_bay_hold` (built OFF 2026-10-15): a bean letter's STATIONS
held off the letter's open bays, inside their own spine's ink
(`stage6_beanletter.hold_off_bays`).

Under the true-size switch Fremont's 1895 at 81 mm sews 0.19 mm strokes on
their centreline under a 0.40 mm thread: the 5's upper bay sewed 64% covered
and the 5 read A; at 92.5 mm THE's E sewed the 0.26 mm slit between its top
arm's tick and its middle arm shut, a false counter (#953). Pinned here on a
synthetic 5 and E of those proportions: the hold opens the 5's bay past
#905's 50%-bare rule and leaves the E with no thread hole; no station leaves
its own spine's ink; a station already clear of every bay stays put; a
station between two bays stays on the ridge; a closed counter is not a bay
(that is #952's hold); None (and ON with no stroke) lays every station
exactly as before; and OFF the flat-lane goldens are byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import math

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, digitize
from digitizer_core.stage6_beanletter import (BAY_CLOSE_MM, _letter_ink, bean_letter,
                                              hold_off_bays, letter_bays, letter_counters)

from .conftest import TESTDATA

THREAD_MM = 0.40    # 40 wt laid width
STROKE_MM = 0.19    # Fremont's 1895 at 81 mm (#953: 0.19 mm stroke)
HOLD_MM = 0.25
KW = dict(entry=None, trim_at_mm=3.0, stitch_mm=0.45, serif_mm=0.45, min_arm_mm=0.3,
          corner_deg=50.0)


def test_flag_defaults_off_and_is_not_in_the_switch():
    assert PipelineConfig().bean_letter_bay_hold is None
    assert PipelineConfig(small_text_true_size=True).bean_letter_bay_hold is None


# --- synthetic letters (design mm, y down) ----------------------------------------

def _arc(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def _five():
    """A 1.65 mm 5: bar, stem, bowl. The upper bay is between the bar and the
    bowl's top, right of the stem, open to the right."""
    bar = [(1.10, 0.0), (0.10, 0.0)]
    stem = [(0.10, 0.0), (0.10, 0.62)]
    bowl = [(0.10, 0.62)] + _arc(0.55, 1.07, 0.48, -135, 150)[1:]
    return [bar, stem, bowl]


def _e():
    """THE's E at 92.5 mm: the top arm's right serif tick ends 0.26 mm of ink
    above the middle arm (#953: tick bottom y -7.73, middle arm top -7.47)."""
    tick_end = 0.66                                        # ink end of the tick
    mid = tick_end + 0.26 + STROKE_MM / 2                  # middle arm centreline
    return [[(1.40, tick_end), (1.40, 0.0), (0.0, 0.0)],   # tick + top arm
            [(0.0, 0.0), (0.0, mid)],                      # stem, top half
            [(0.0, mid), (1.30, mid)],                     # middle arm
            [(0.0, mid), (0.0, 2.2)],                      # stem, bottom half
            [(0.0, 2.2), (1.40, 2.2)]]                     # bottom arm


def _sew(spines, hold=None, stroke=STROKE_MM):
    runs, rep = bean_letter(spines, "S", bay_hold_mm=hold, stroke_mm=stroke, **KW)
    assert not rep["empty"]
    return runs


PPM = 60.0
_BOX = (-1.0, -1.0, 3.0, 3.5)


def _px(q):
    return (int(round((q[0] - _BOX[0]) * PPM)), int(round((q[1] - _BOX[1]) * PPM)))


def _thread(runs, ppm=PPM):
    w, h = int((_BOX[2] - _BOX[0]) * ppm), int((_BOX[3] - _BOX[1]) * ppm)
    m = np.zeros((h, w), np.uint8)
    P = lambda q: (int(round((q[0] - _BOX[0]) * ppm)), int(round((q[1] - _BOX[1]) * ppm)))  # noqa: E731
    for r in runs:
        for a, b in zip(r.points, r.points[1:]):
            cv2.line(m, P(a), P(b), 1, max(1, int(round(THREAD_MM * ppm))))
    return m


def _bare_share(runs, region):
    sewn = _thread(runs)
    cm = np.zeros_like(sewn)
    cv2.fillPoly(cm, [np.array([_px(q) for q in region.exterior.coords], np.int32)], 1)
    return float((cm & (1 - sewn)).sum()) / float(cm.sum())


def _holes(runs, ppm=20.0):
    """Closed not-thread pockets at the legibility instrument's 20 px/mm."""
    sewn = _thread(runs, ppm)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((1 - sewn).astype(np.uint8), connectivity=4)
    h, w = sewn.shape
    return sum(1 for k in range(1, n)
               if not (stats[k][0] <= 0 or stats[k][1] <= 0
                       or stats[k][0] + stats[k][2] >= w or stats[k][1] + stats[k][3] >= h))


def _upper_bay(spines):
    _own, ink = _letter_ink(spines, STROKE_MM)
    return min(letter_bays(ink), key=lambda g: g.centroid.y)        # the topmost bay


# --- the 5 and the E -------------------------------------------------------------

def test_the_fives_upper_bay_is_shut_centred_and_open_held():
    sp = _five()
    bay = _upper_bay(sp)
    assert 0.1 < bay.area < 0.5                           # Fremont's: 0.231 mm2
    off = _bare_share(_sew(sp), bay)
    on = _bare_share(_sew(sp, HOLD_MM), bay)
    assert off < 0.5, off                                 # #905's rule: FILLED
    assert on >= 0.5, on                                  # open
    assert on > off


def test_the_es_slit_closes_into_a_false_counter_centred_and_stays_open_held():
    sp = _e()
    assert _holes(_sew(sp)) >= 1                          # the false counter
    assert _holes(_sew(sp, HOLD_MM)) == 0


def test_no_held_station_leaves_its_own_spines_ink():
    for sp in (_five(), _e()):
        own, _ink = _letter_ink(sp, STROKE_MM)
        held = _sew(sp, HOLD_MM)
        for r in held:
            for q in r.points:
                assert any(g is not None and g.buffer(1e-6).covers(Point(q)) for g in own), q


def test_a_station_clear_of_every_bay_stays_put():
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    bay = Point(0, 5).buffer(0.3)
    pts = [(0.5, 0.0), (1.0, 0.0)]
    assert hold_off_bays(pts, own, bay, HOLD_MM) == pts


def test_a_station_moves_away_from_the_bay_on_its_ink():
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    bay = Polygon([(0, 0.2), (2, 0.2), (2, 0.6), (0, 0.6)])     # just below the stroke
    (q,) = hold_off_bays([(1.0, 0.0)], own, bay, HOLD_MM)
    assert q[1] < 0.0 and own.buffer(1e-9).covers(Point(q))
    assert abs(q[0] - 1.0) < 1e-9                                # straight away, nearest of equals


def test_a_station_between_two_bays_stays_on_the_ridge():
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    below = Polygon([(0, 0.2), (2, 0.2), (2, 0.6), (0, 0.6)])
    above = Polygon([(0, -0.2), (2, -0.2), (2, -0.6), (0, -0.6)])
    bays = below.union(above)
    assert hold_off_bays([(1.0, 0.0)], own, bays, HOLD_MM) == [(1.0, 0.0)]


def test_a_closed_counter_is_not_a_bay():
    ring = _arc(0.0, 0.0, 0.4, 0, 360, 48)
    _own, ink = _letter_ink([ring], STROKE_MM)
    assert ink.geom_type == "Polygon" and len(ink.interiors) == 1     # the counter
    assert letter_bays(ink) == []
    assert len(letter_counters(ink)) == 1


def test_a_stroke_between_two_bays_leans_toward_the_wider_one():
    """The bowl top of a 5: its upper bay is narrow, its bowl wide. Leaning
    into the wide pocket costs it a smaller share than the narrow one gains."""
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    narrow = Polygon([(0, 0.15), (2, 0.15), (2, 0.45), (0, 0.45)])
    wide = Polygon([(0, -0.15), (2, -0.15), (2, -1.15), (0, -1.15)])
    (q,) = hold_off_bays([(1.0, 0.0)], own, [narrow, wide], HOLD_MM)
    assert q[1] < 0.0, q                                         # toward the wide pocket


def test_a_stroke_between_a_bay_and_a_counter_is_not_pushed_into_the_counter():
    """An A's leg: a bay outside, the counter inside. Held off the bay alone
    the thread would close the counter (Fremont's tagline A's, first build)."""
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    bay = Polygon([(0, 0.15), (2, 0.15), (2, 0.55), (0, 0.55)])
    counter = Polygon([(0, -0.15), (2, -0.15), (2, -0.55), (0, -0.55)])
    assert hold_off_bays([(1.0, 0.0)], own, [bay], HOLD_MM)[0][1] < 0.0      # bay alone: pushed in
    assert hold_off_bays([(1.0, 0.0)], own, [bay], HOLD_MM, [counter]) == [(1.0, 0.0)]


def test_a_station_only_a_counter_crowds_is_not_moved():
    own = LineString([(0, 0), (2, 0)]).buffer(STROKE_MM / 2)
    far_bay = Point(0, 5).buffer(0.3)
    counter = Polygon([(0, -0.15), (2, -0.15), (2, -0.55), (0, -0.55)])
    assert hold_off_bays([(1.0, 0.0)], own, [far_bay], HOLD_MM, [counter]) == [(1.0, 0.0)]


def test_a_junction_fillet_is_not_a_bay():
    _own, ink = _letter_ink([[(0.0, 0.0), (1.5, 0.0)], [(0.75, 0.0), (0.75, 1.5)]], STROKE_MM)   # a T
    assert letter_bays(ink) == []


def test_the_bay_is_the_instruments_closing():
    assert BAY_CLOSE_MM == 0.45
    from tools import bean_glyph_trace as bgt
    assert bgt.BAY_CLOSE_MM == BAY_CLOSE_MM


def test_none_or_no_stroke_lays_every_station_as_before():
    for sp in (_five(), _e()):
        base = [r.points for r in bean_letter(sp, "S", **KW)[0]]
        assert [r.points for r in _sew(sp, None)] == base
        assert [r.points for r in _sew(sp, HOLD_MM, stroke=None)] == base
        assert [r.points for r in _sew(sp, 0.0)] == base


def test_the_hold_keeps_every_run_and_station_count():
    for sp in (_five(), _e()):
        off, on = _sew(sp), _sew(sp, HOLD_MM)
        assert len(off) == len(on)
        assert [len(r.points) for r in off] == [len(r.points) for r in on]
        assert [(r.jump, r.trim) for r in off] == [(r.jump, r.trim) for r in on]


def test_the_stage7_call_passes_the_hold_only_when_set():
    """OFF, stage 7 calls `bean_letter` with exactly the arguments it always
    did, so anything spying on that call (`tools/bean_glyph_trace.py`) sees
    the same call."""
    import inspect

    from digitizer_core import stage7_sequence as s7
    src = inspect.getsource(s7)
    assert '"bay_hold_mm": cfg.bean_letter_bay_hold' in src
    assert "if cfg.bean_letter_bay_hold else {}" in src


# --- the tool's pure helpers ---------------------------------------------------------

def test_the_tools_arms_are_valid_config_and_change_only_the_hold():
    from tools import bean_bay_hold as bbh
    assert bbh.ARMS["switch"][0] == {}                   # main's defaults: the switch is ON
    for name, (overrides, _label) in bbh.ARMS.items():
        PipelineConfig(**overrides)
        assert set(overrides) <= {"bean_letter_bay_hold"}, name
    assert bbh.ARMS[bbh.CORPUS_ARM][0] == {"bean_letter_bay_hold": bbh.HOLD_HALF_THREAD_MM}


def _trace(bays, holes, glyph="5"):
    return {"glyph": glyph, "tier": "bean letter",
            "bays": [{"where": "top-centre", "mm2": 0.231, "bare_share": b} for b in bays],
            "thread_holes": holes}


def test_glyph_summary_counts_filled_bays_and_only_spurious_holes():
    from tools import bean_bay_hold as bbh
    holes = [{"source_counter": True, "reading": "strict"},
             {"source_counter": False, "reading": "strict"},
             {"source_counter": False, "reading": "bridged"}]
    row = bbh.glyph_summary(_trace([0.36, 0.5, 0.49], holes),
                            {"legibility": 1.0, "counters": 0.0, "sewn_counters_spurious": 1,
                             "ocr_src": "5", "ocr_sewn": "A"})
    assert row["bays_filled"] == 2                        # 0.5 is open: #905's rule
    assert (row["holes_strict"], row["holes_bridged"]) == (1, 1)
    assert row["spurious"] == 1 and row["ocr"] == "5->A"
    assert bbh.glyph_summary(_trace([], []), None)["ocr"] is None


def test_the_glyph_table_lists_only_glyphs_an_arm_changed():
    from tools import bean_bay_hold as bbh
    same = bbh.glyph_summary(_trace([0.6], [], "1"), None)
    off = bbh.glyph_summary(_trace([0.36], [], "5"), None)
    on = bbh.glyph_summary(_trace([0.55], [], "5"), None)

    def cell(g):
        return {"words": {w: {"glyphs": g if w == "1895" else []} for w in bbh.WORDS}}
    table = bbh.glyph_table({"hat81__switch": cell([same, off]), "hat81__bay": cell([same, on])})
    assert "| 81 | 1895 | 5 | switch |" in table and "| 81 | 1895 | 5 | bay |" in table
    assert "| 1895 | 1 |" not in table


def test_corpus_rows_flag_a_new_uncovered_shape_and_the_changes():
    from tools import bean_bay_hold as bbh

    def cell(md5, au, shapes, digests, leg):
        return {"md5": md5, "stitches": 10, "trims": 4, "shape_digests": digests, "bare_mm2": 1.0,
                "uncovered_total_mm2": au, "uncovered_shapes": shapes, "bean_shapes": 1,
                "words": {"w": {"legibility": leg}}}
    cells = {"becker": {"switch": cell("a", 0.0, [], {"S1": "x"}, 0.5),
                        "bay": cell("a", 0.0, [], {"S1": "x"}, 0.5)},
             "fremont": {"switch": cell("a", 1.0, ["S1"], {"S1": "x"}, 0.5),
                         "bay": cell("b", 2.0, ["S1", "S2"], {"S1": "y"}, 0.6)}}
    rows = {r["design"]: r for r in bbh.corpus_rows(cells)}
    assert rows["becker"]["identical"] and rows["becker"]["changed"] == 0 and not rows["becker"]["au_up"]
    assert rows["fremont"]["changed"] == 1 and rows["fremont"]["au_up"] and rows["fremont"]["new_au"]
    assert rows["fremont"]["d_leg"] == {"w": 0.1}
    assert "| fremont |" in bbh.corpus_table(cells)


# --- OFF is byte-identical ----------------------------------------------------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("hold", [None, HOLD_MM])
def test_goldens_are_byte_identical_off_and_on_without_bean_letters(fixture, hold):
    """OFF is the engine as it was. ON too: the three flat goldens carry no
    bean letter, so the hold has nothing to hold."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            bean_letter_bay_hold=hold))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
