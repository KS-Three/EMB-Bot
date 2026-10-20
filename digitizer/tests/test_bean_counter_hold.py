"""`cfg.bean_letter_counter_hold_mm` (built OFF 2026-10-14): a bean letter's
needle points held off its small counters, inside the ink
(`ink_path.hold_off_counters`, `beanletters.hold_bean_counters`).

Fremont's 81 mm 8 under `small_text_true_size` sews its 0.22 mm strokes on
their centreline under a 0.40 mm thread and both counters shut (0.33 / 0.28
bare). Pinned here, on a synthetic 8 of the same proportions: the hold opens
both counters past #905's 50%-bare rule; no needle point leaves the ink;
the waist between the counters stays on its ridge; a counter wider than
`COUNTER_HOLD_MAX_MM` is left alone; None reads the spines exactly as before;
and OFF (and ON without bean letters) the flat-lane goldens are byte-identical.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize
from digitizer_core.beanletters import (BEAN_LETTER_KEY, COUNTER_HOLD_MAX_MM,
                                        hold_bean_counters)
from digitizer_core.ink_path import hold_off_counters, read_cluster_ink, small_counters
from digitizer_core.stage6_beanletter import bean_letter

from .conftest import TESTDATA

PPM = 30.0          # Fremont's 81 mm prep is 30.9 px/mm
THREAD_MM = 0.40    # 40 wt laid width
STROKE_MM = 0.22    # Fremont's 1895 at 81 mm
HOLD_MM = 0.2


def test_flag_defaults_on_since_kents_flip_and_none_is_off():
    """ON at 0.25 since 2026-10-15 (Kent: "flip both holds ON"). A plain default,
    not a switch value: the switch neither fills nor clears it, an explicit None
    is OFF (what the sew-out cards' OFF arms pass), and the pre-flip engine pins
    None (`conftest.PRE_FLIP`)."""
    from .conftest import PRE_FLIP
    assert PipelineConfig().bean_letter_counter_hold_mm == 0.25
    assert PipelineConfig(small_text_true_size=True).bean_letter_counter_hold_mm == 0.25
    assert PipelineConfig(small_text_true_size=False).bean_letter_counter_hold_mm == 0.25
    assert PipelineConfig(bean_letter_counter_hold_mm=None).bean_letter_counter_hold_mm is None
    assert PRE_FLIP["bean_letter_counter_hold_mm"] is None


# --- a synthetic 8 ---------------------------------------------------------------

def _eight(counter_r: float = 0.3, stroke: float = STROKE_MM, at=(0.0, 0.0)):
    """Two stacked rings sharing a waist: (ink polygon, [counters]) in mm."""
    x, y = at
    lo, hi = Point(x, y + counter_r + stroke / 2), Point(x, y - counter_r - stroke / 2)
    holes = [lo.buffer(counter_r, 64), hi.buffer(counter_r, 64)]
    ink = unary_union([h.buffer(stroke) for h in holes]).difference(unary_union(holes))
    return ink, holes


def _prep(geoms, size_mm=(8.0, 8.0)):
    """A white page holding black `geoms` (mm, origin at the page centre)."""
    w, h = int(size_mm[0] * PPM), int(size_mm[1] * PPM)
    rgb = np.full((h, w, 3), 255, np.uint8)
    mask = np.zeros((h, w), np.uint8)
    for g in geoms:
        for part in getattr(g, "geoms", [g]):
            ext = np.round([((px * PPM + w / 2), (py * PPM + h / 2)) for px, py in part.exterior.coords]).astype(np.int32)
            cv2.fillPoly(mask, [ext], 1)
            for ring in part.interiors:
                cv2.fillPoly(mask, [np.round([((px * PPM + w / 2), (py * PPM + h / 2))
                                              for px, py in ring.coords]).astype(np.int32)], 0)
    rgb[mask > 0] = 0
    return SimpleNamespace(rgb=rgb, bg_mask=np.zeros((h, w), bool), px_per_mm=PPM,
                           art_bbox=(0, 0, w, h), bg_from_alpha=False, enclosed_mask=None)


def _bare_shares(runs, counters, ppm=60.0):
    x0, y0 = -4.0, -4.0
    n = int(8.0 * ppm)
    sewn = np.zeros((n, n), np.uint8)
    P = lambda q: (int(round((q[0] - x0) * ppm)), int(round((q[1] - y0) * ppm)))  # noqa: E731
    for r in runs:
        for a, b in zip(r.points, r.points[1:]):
            cv2.line(sewn, P(a), P(b), 1, max(1, int(round(THREAD_MM * ppm))))
    out = []
    for c in counters:
        cm = np.zeros_like(sewn)
        cv2.fillPoly(cm, [np.array([P(q) for q in c.exterior.coords], np.int32)], 1)
        out.append(float((cm & (1 - sewn)).sum()) / float(cm.sum()))
    return out


def _sew(spines):
    runs, rep = bean_letter(spines, "S8", entry=None, trim_at_mm=3.0, stitch_mm=0.45,
                            serif_mm=0.45, min_arm_mm=0.3)
    assert not rep["empty"]
    return runs


def _member(poly):
    return SimpleNamespace(polygon=poly, meta={})


def test_the_eight_is_what_the_docstring_says():
    ink, holes = _eight()
    assert len(holes) == 2 and ink.is_valid
    for h in holes:
        assert 2 * 0.3 < COUNTER_HOLD_MAX_MM          # small counters, both served
        assert 0.25 < h.area < 0.35                     # Fremont's: 0.31 and 0.41 mm2


def test_none_reads_the_spines_exactly_as_before():
    ink, _holes = _eight()
    p = _prep([ink])
    base = read_cluster_ink(p, [_member(ink.buffer(0.05))])
    again = read_cluster_ink(p, [_member(ink.buffer(0.05))], counter_hold_mm=None,
                             counter_max_mm=COUNTER_HOLD_MAX_MM)
    assert base[0].spines == again[0].spines and base[0].stroke_mm == again[0].stroke_mm


def test_held_the_eights_two_counters_open_and_centred_they_shut():
    ink, holes = _eight()
    p = _prep([ink])
    m = [_member(ink.buffer(0.05))]
    bare_off = _bare_shares(_sew(read_cluster_ink(p, m)[0].spines), holes)
    held = read_cluster_ink(p, m, counter_hold_mm=HOLD_MM, counter_max_mm=COUNTER_HOLD_MAX_MM)[0]
    bare_on = _bare_shares(_sew(held.spines), holes)
    assert all(b < 0.5 for b in bare_off), bare_off        # #905's rule: both SHUT
    assert all(b >= 0.5 for b in bare_on), bare_on         # both open
    assert all(on > off for on, off in zip(bare_on, bare_off))


def test_no_held_point_leaves_the_ink():
    ink, holes = _eight()
    p = _prep([ink])
    held = read_cluster_ink(p, [_member(ink.buffer(0.05))], counter_hold_mm=HOLD_MM,
                            counter_max_mm=COUNTER_HOLD_MAX_MM)[0]
    # The needle goes down on the INK READ's pixels; that raster sits within
    # one source pixel of the drawn polygon (measured 0.024 mm here).
    pix = 1.0 / PPM
    for s in held.spines:
        for q in s:
            assert ink.buffer(pix).covers(Point(q)), q
            assert not any(h.buffer(-pix).contains(Point(q)) for h in holes), q


# --- hold_off_counters on a raster --------------------------------------------------

def _ring_raster(counter_px: int, stroke_px: int, size=120):
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.hypot(xx - size / 2, yy - size / 2)
    return (d >= counter_px) & (d < counter_px + stroke_px)


def test_a_point_on_the_centreline_moves_outward_on_the_ink():
    ink = _ring_raster(10, 8)
    pt = (60.0 + 14.0, 60.0)                           # centreline, 4 px off the counter
    (moved,), = hold_off_counters([[pt]], ink, hold_px=6.0, max_counter_px=40.0)
    assert moved != pt
    assert ink[int(moved[1]), int(moved[0])]
    assert np.hypot(moved[0] - 60, moved[1] - 60) > np.hypot(pt[0] - 60, pt[1] - 60)


def test_a_point_already_far_enough_stays_put():
    ink = _ring_raster(10, 20)
    pt = (60.0 + 25.0, 60.0)                           # 15 px off the counter
    assert hold_off_counters([[pt]], ink, hold_px=6.0, max_counter_px=40.0) == [[pt]]


def test_a_counter_wider_than_the_cap_is_not_served():
    ink = _ring_raster(30, 8)                          # 60 px across
    assert not small_counters(ink, 40.0).any()
    pt = (60.0 + 34.0, 60.0)
    assert hold_off_counters([[pt]], ink, hold_px=6.0, max_counter_px=40.0) == [[pt]]


def test_the_ground_round_the_letters_is_not_a_counter():
    ink = _ring_raster(10, 8)
    small = small_counters(ink, 1000.0)
    assert small[60, 60] and not small[0, 0]


def test_the_waist_between_two_counters_stays_on_its_ridge():
    """A bar between two counters has no side further from both: the hold
    leaves its middle where it is."""
    ink = np.ones((60, 120), bool)
    ink[20:40, 20:56] = False                          # left counter
    ink[20:40, 64:100] = False                         # right counter (8 px bar between)
    pt = (60.0, 30.0)                                  # the bar's centre
    assert hold_off_counters([[pt]], ink, hold_px=6.0, max_counter_px=40.0) == [[pt]]


# --- the post-pass ------------------------------------------------------------------

def test_hold_bean_counters_is_inert_off_and_moves_only_bean_members():
    ink, _holes = _eight()
    p = _prep([ink])
    r = SimpleNamespace(polygon=ink.buffer(0.05), meta={"text_cluster_id": "T1"}, shape_id="S1")
    assert hold_bean_counters([r], p, PipelineConfig()) == 0
    cfg = PipelineConfig(bean_letter_counter_hold_mm=HOLD_MM)
    assert hold_bean_counters([r], p, cfg) == 0        # not a bean letter: untouched
    assert BEAN_LETTER_KEY not in r.meta
    r.meta[BEAN_LETTER_KEY] = read_cluster_ink(p, [r])[0].spines
    before = r.meta[BEAN_LETTER_KEY]
    assert hold_bean_counters([r], p, cfg) == 1
    after = r.meta[BEAN_LETTER_KEY]
    assert after != before and len(after) == len(before)
    assert [len(s) for s in after] == [len(s) for s in before]
    assert r.meta["bean_counter_held"] is True


# --- the tool's pure helpers ---------------------------------------------------------

def test_the_tools_arms_are_valid_config_and_change_only_the_hold():
    from tools import bean_counter_hold as bch
    for name, (overrides, _label) in bch.ARMS.items():
        PipelineConfig(**overrides)
        extra = set(overrides) - {"small_text_true_size", "bean_letter_counter_hold_mm"}
        assert not extra, (name, extra)
    assert bch.ARMS["switch_hold"][0] == {**bch.ARMS["switch"][0], "bean_letter_counter_hold_mm": bch.HOLD_MM}
    assert bch.ARMS["main_hold"][0] == {"small_text_true_size": False,
                                        "bean_letter_counter_hold_mm": bch.HOLD_MM}
    assert bch.ARMS["main"][0] == {"small_text_true_size": False}       # the pre-flip engine


def test_open_counters_is_905s_fifty_percent_rule():
    from tools import bean_counter_hold as bch
    rows = [{"bare": []}, {"bare": [0.619, 0.5]}, {"bare": [0.499]}]
    assert bch.open_counters(rows) == (2, 3)


def test_corpus_rows_flag_a_new_uncovered_shape_and_the_changes():
    from tools import bean_counter_hold as bch

    def cell(md5, st, au, shapes, digests, leg):
        return {"md5": md5, "stitches": st, "trims": 4, "shape_digests": digests,
                "uncovered_fires": au, "uncovered_total_mm2": 1.0 if au else 0.0,
                "uncovered_shapes": shapes, "words": {"w": {"legibility": leg}}}
    same = {"switch": cell("a", 10, False, [], {"S1": "x"}, 0.5),
            "switch_hold": cell("a", 10, False, [], {"S1": "x"}, 0.5)}
    moved = {"switch": cell("a", 10, True, ["S1"], {"S1": "x", "S2": "y"}, 0.5),
             "switch_hold": cell("b", 12, True, ["S1", "S2"], {"S1": "x", "S2": "z"}, 0.6)}
    rows = {r["design"]: r for r in bch.corpus_rows({"same": same, "moved": moved, "half": {"switch": same["switch"]}})}
    assert set(rows) == {"same", "moved"}
    assert rows["same"]["identical"] and rows["same"]["changed"] == 0 and not rows["same"]["new_au"]
    assert not rows["moved"]["identical"] and rows["moved"]["changed"] == 1 and rows["moved"]["new_au"]
    assert rows["moved"]["d_leg"] == {"w": 0.1}
    assert "| moved |" in bch.corpus_table({"moved": moved})


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
    """OFF is the engine as it was. ON alone too: with no bean letters
    (`bean_letter_max_stroke_mm` None) the hold has nothing to hold."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            bean_letter_counter_hold_mm=hold))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
