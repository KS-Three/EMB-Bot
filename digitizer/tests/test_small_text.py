"""Enlarge lettering too small to sew (`cfg.small_text_cap_mm`, 2026-10-13,
default OFF; `digitizer_core/small_text.py`).

Hotel Fremont's "EST 1895" at 92.5 mm is 1.9 mm tall and sews as a running
stitch that reads "1095"; the professional's file for the same patch sews the
date 3.6-3.9 mm tall in satin. These pin the pass that does the same, on a
synthetic line small enough to run in milliseconds:

- OFF is the default and the pass does nothing when asked for nothing;
- a small line is grown to the cap asked for, ids and thread kept;
- the counters stage 4 dropped come back from the source raster, and the
  untagged digit that lost them is adopted into the line;
- two clusters on one baseline keep one baseline and one scale;
- the grown line clears every other shape, and a line with no room -- or
  one already tall enough -- is left exactly as it was.

The cap is a candidate (ROADMAP gate 1): nothing here says 3.7 mm sews.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core import small_text  # noqa: E402
from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.small_text import enlarge_small_text  # noqa: E402
from digitizer_core.stage1_prep import Prep  # noqa: E402

PPM = 24.0
W, H = 960, 480                    # 40 x 20 mm
INK, GROUND, OTHER = (170, 150, 120), (255, 255, 255), (20, 20, 20)


def _mm(px_pts) -> list[tuple[float, float]]:
    return [((x - W / 2) / PPM, (y - H / 2) / PPM) for x, y in px_pts]


def _scene(text_at=((300, 262),), words=("1895",), blocker_px=None):
    """A raster with small tan lettering, and the regions a tracer that drops
    small counters would hand over: one solid polygon per glyph (no holes)."""
    img = np.full((H, W, 3), GROUND, np.uint8)
    glyph_mask = np.zeros((H, W), np.uint8)
    for (x, y), word in zip(text_at, words):
        # ~2 mm cap, ~0.25 mm stroke
        cv2.putText(img, word, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2.0, INK, 6, cv2.LINE_AA)
        cv2.putText(glyph_mask, word, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 255, 6, cv2.LINE_8)
    regions = [Region("Sbase", box(-20, -10, 20, 10), 1, "1", 800.0)]
    if blocker_px is not None:
        x0, y0, x1, y1 = blocker_px
        cv2.rectangle(img, (x0, y0), (x1, y1), OTHER, -1)
        regions.append(Region("Sblock", Polygon(_mm([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])), 2, "2", 1.0))
    contours, _ = cv2.findContours(glyph_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    glyphs = []
    for c in contours:
        poly = Polygon(_mm(c.reshape(-1, 2))).buffer(0)
        if poly.area > 0.05:
            glyphs.append(poly)
    glyphs.sort(key=lambda g: g.bounds[0])
    for i, g in enumerate(glyphs):
        regions.append(Region(f"Sg{i}", g, 7, "7", float(g.area), meta={"rescued_small_shape": True}))
    p = Prep(rgb=img, bg_mask=np.zeros((H, W), bool), px_per_mm=PPM, art_bbox=(0, 0, W, H))
    return regions, p


def _tag(regions, ids, cid="TCtest", stroke_half_mm=0.125):
    for r in regions:
        if r.shape_id in ids:
            r.meta.update(text_candidate=True, text_cluster_id=cid,
                          text_cluster_stroke_mm=stroke_half_mm, text_cluster_all_rescued=True)


def _glyphs(regions):
    return sorted((r for r in regions if r.shape_id.startswith("Sg")), key=lambda r: r.polygon.bounds[0])


def _cap(regions) -> float:
    return float(np.median([r.polygon.bounds[3] - r.polygon.bounds[1] for r in _glyphs(regions)]))


def test_off_is_the_default_and_nothing_is_asked_for_nothing():
    assert PipelineConfig().small_text_cap_mm is None
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    assert enlarge_small_text(regions, p, cap_mm=None) == []
    assert enlarge_small_text(regions, p, cap_mm=0) == []
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before


def test_a_small_line_is_grown_to_the_cap_and_keeps_its_identity():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    cap0 = _cap(regions)
    assert 1.5 < cap0 < 2.6, f"the fixture should be small lettering, got {cap0:.2f} mm"
    ids0 = [(r.shape_id, r.thread_index) for r in regions]
    rep = enlarge_small_text(regions, p, cap_mm=3.7)
    assert [(r.shape_id, r.thread_index) for r in regions] == ids0, "no shape added, dropped or rethreaded"
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row, row
    assert abs(_cap(regions) - 3.7) < 0.35, f"cap {cap0:.2f} -> {_cap(regions):.2f} mm, asked 3.7"
    assert row["scale"] <= small_text.MAX_SCALE + 1e-9
    for r in _glyphs(regions):
        assert r.polygon.is_valid and r.meta["small_text_enlarged"] == row["scale"]
        assert abs(r.area_mm2 - r.polygon.area) < 1e-9
    # the stroke the later stages read is the grown one
    assert _glyphs(regions)[0].meta["text_cluster_stroke_mm"] > 0.125 * row["scale"] - 1e-9


def test_counters_come_back_from_the_raster_and_the_untagged_digit_is_adopted():
    regions, p = _scene()
    # The tagger refuses the 8 (a solid blob, like Fremont's): 1, 9, 5 only.
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    assert all(len(r.polygon.interiors) == 0 for r in _glyphs(regions)), "the fixture's tracer dropped every counter"
    rep = enlarge_small_text(regions, p, cap_mm=3.7)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row.get("adopted") == 1, row
    one, eight, nine, five = _glyphs(regions)
    assert len(eight.polygon.interiors) == 2, "the 8 has both loops again"
    assert len(nine.polygon.interiors) == 1, "the 9 has its loop again"
    assert len(one.polygon.interiors) == 0 and len(five.polygon.interiors) == 0
    assert eight.meta.get("small_text_enlarged") == row["scale"], "the adopted digit grew with the line"
    heights = [r.polygon.bounds[3] - r.polygon.bounds[1] for r in (one, eight, nine, five)]
    assert max(heights) - min(heights) < 0.5, "one line, one size"


def test_two_halves_of_one_line_keep_one_baseline_and_one_scale():
    # "EST" and "1895" either side of an emblem, as on Fremont.
    regions, p = _scene(text_at=((150, 262), (560, 262)), words=("EST", "1895"),
                        blocker_px=(400, 150, 500, 330))
    g = _glyphs(regions)
    left = {r.shape_id for r in g if r.polygon.bounds[2] < 0}
    right = {r.shape_id for r in g} - left
    assert len(left) == 3 and len(right) == 4
    _tag(regions, left, cid="TCleft")
    _tag(regions, right, cid="TCright")
    rep = {r["cluster"]: r for r in enlarge_small_text(regions, p, cap_mm=3.7)}
    assert "skipped" not in rep["TCleft"] and "skipped" not in rep["TCright"], rep
    assert rep["TCleft"]["scale"] == rep["TCright"]["scale"]
    assert rep["TCleft"]["shift_mm"][1] == rep["TCright"]["shift_mm"][1], "one vertical move for the line"
    bottoms = [r.polygon.bounds[3] for r in _glyphs(regions) if r.shape_id != "Sg1"]  # S overshoots
    assert max(bottoms) - min(bottoms) < 0.25, "the two halves still share a baseline"
    block = next(r for r in regions if r.shape_id == "Sblock").polygon
    for r in _glyphs(regions):
        assert r.polygon.distance(block) >= small_text.CLEAR_MM - 1e-6, "clear of the emblem"


def test_a_line_with_no_room_and_a_line_tall_enough_are_left_alone():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    # Wall the line in on every side, closer than it could ever move.
    x0 = min(r.polygon.bounds[0] for r in _glyphs(regions)) - 0.6
    x1 = max(r.polygon.bounds[2] for r in _glyphs(regions)) + 0.6
    y0 = min(r.polygon.bounds[1] for r in _glyphs(regions)) - 0.6
    y1 = max(r.polygon.bounds[3] for r in _glyphs(regions)) + 0.6
    wall = box(x0 - 9, y0 - 9, x1 + 9, y1 + 9).difference(box(x0, y0, x1, y1))
    regions.append(Region("Swall", Polygon(wall.exterior, [list(i.coords) for i in wall.interiors]), 2, "2", wall.area))
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = enlarge_small_text(regions, p, cap_mm=3.7)
    assert next(r for r in rep if r["cluster"] == "TCtest")["skipped"] == "no_room"
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before

    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = enlarge_small_text(regions, p, cap_mm=_cap(regions) * 1.05)
    assert next(r for r in rep if r["cluster"] == "TCtest")["skipped"] == "tall_enough"
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before


def test_the_flag_runs_end_to_end_and_none_never_calls_the_pass(monkeypatch):
    from digitizer_core.pipeline import digitize

    fixture = Path(__file__).resolve().parent.parent / "testdata" / "logo_whitebg.png"
    calls = []
    real = small_text.enlarge_small_text
    monkeypatch.setattr(small_text, "enlarge_small_text",
                        lambda *a, **k: (calls.append(k.get("cap_mm")), real(*a, **k))[1])
    _, plan_off = digitize(fixture, PipelineConfig(target_width_mm=80.0))
    assert calls == [], "None is byte-identical because nothing calls the pass"
    _, plan_on = digitize(fixture, PipelineConfig(target_width_mm=80.0, small_text_cap_mm=3.7))
    assert calls == [3.7]
    assert plan_on.blocks, "a plan comes back with the flag on"
