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
from tests.conftest import own_thread_only

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
    monkeypatch.setattr(small_text, "enlarge_small_text", own_thread_only(
        lambda *a, **k: (calls.append(k.get("cap_mm")), real(*a, **k))[1], real))
    _, plan_off = digitize(fixture, PipelineConfig(target_width_mm=80.0))
    assert calls == [], "None is byte-identical because nothing calls the pass"
    _, plan_on = digitize(fixture, PipelineConfig(target_width_mm=80.0, small_text_cap_mm=3.7))
    assert calls == [3.7]
    assert plan_on.blocks, "a plan comes back with the flag on"


# --- True size (`cfg.small_text_restore_mm`, `cfg.bean_letter_stitch_mm`) ---
# Kent, 2026-10-13: "you can't change the font size for the final product."
# Same fixture, nothing scaled or moved: the line's untagged letters join its
# cluster and every letter gets its counters back, so bean letters can sew
# the whole line as centrelines; and bean letters take a shorter pitch.

def test_true_size_defaults_are_off():
    cfg = PipelineConfig()
    assert cfg.small_text_restore_mm is None and cfg.bean_letter_stitch_mm is None
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    assert small_text.restore_small_text(regions, p, cap_mm=None) == []
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before


def test_restore_keeps_size_and_place_brings_counters_back_and_adopts_the_8():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})          # the tagger refused the 8
    boxes0 = {r.shape_id: r.polygon.bounds for r in _glyphs(regions)}
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row.get("adopted") == 1 and "skipped" not in row, row
    one, eight, nine, five = _glyphs(regions)
    for r in (one, eight, nine, five):
        b0, b1 = boxes0[r.shape_id], r.polygon.bounds
        assert max(abs(a - b) for a, b in zip(b0, b1)) < 0.15, "nothing is scaled or moved"
        assert r.meta["text_cluster_id"] == "TCtest", "every letter of the line is a member now"
        assert "small_text_enlarged" not in r.meta
    assert len(eight.polygon.interiors) == 2 and len(nine.polygon.interiors) == 1
    assert eight.meta.get("small_text_adopted") is True and "small_text_adopted" not in one.meta
    assert eight.meta["text_cluster_stroke_mm"] == one.meta["text_cluster_stroke_mm"]


def test_restore_leaves_a_line_at_or_over_the_height_alone():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = small_text.restore_small_text(regions, p, cap_mm=_cap(regions) * 0.95)
    assert next(r for r in rep if r["cluster"] == "TCtest")["skipped"] == "tall_enough"
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before


def test_bean_letter_pitch_none_is_byte_identical_and_a_shorter_one_draws_a_small_loop():
    import math

    from digitizer_core import machine
    from digitizer_core.stage6_beanletter import bean_letter

    # The loop of a 1.9 mm "8": a ring about 0.3 mm in radius, 1.9 mm round.
    ring = [(0.3 * math.cos(2 * math.pi * k / 24), 0.3 * math.sin(2 * math.pi * k / 24)) for k in range(25)]
    stem = [(2.0, 0.0), (2.0, 1.9)]
    base, _ = bean_letter([ring, stem], "S", entry=None, trim_at_mm=3.0)
    same, _ = bean_letter([ring, stem], "S", entry=None, trim_at_mm=3.0, stitch_mm=None)
    assert [r.points for r in same] == [r.points for r in base]
    fine, _ = bean_letter([ring, stem], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45)

    def lap(runs, i):                      # stations in one pass of spine i
        return (len(runs[i].points) - 1) // machine.BEAN_PASSES + 1

    assert lap(base, 0) <= 4, "at 0.73 mm the loop is a wedge"
    assert lap(fine, 0) >= 5, "at 0.45 mm it has enough stations to be round"
    steps = [math.dist(a, b) for r in fine for a, b in zip(r.points, r.points[1:])]
    assert min(steps) >= 0.3, f"no stitch under the short-stitch floor, got {min(steps):.2f}"
    # A short arm that 0.73 refuses sews at the shorter pitch (Bridge's E).
    arm = [(0.0, 0.0), (0.6, 0.0)]
    long_stem = [(0.0, 0.0), (0.0, 3.0)]
    off, _ = bean_letter([long_stem, arm], "S", entry=None, trim_at_mm=3.0)
    on, _ = bean_letter([long_stem, arm], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45)
    assert len(off) == 1 and len(on) == 2


# --- Serif hooks (`cfg.bean_letter_serif_mm`) -------------------------------
# At 1.9 mm Fremont's slab serifs read as hooks on the ends of a letter's
# centrelines; laid in thread they close the E into a B, and 60 wt thread
# did not open it. A sharp turn within `serif_mm` of a free end is cut.

def test_serif_trim_none_is_byte_identical():
    from digitizer_core.stage6_beanletter import bean_letter, trim_serif_hooks

    spines = [[(2.0, 0.35), (2.0, 0.0), (0.0, 0.0)], [(0.0, 0.0), (0.0, 1.9)]]
    assert trim_serif_hooks(spines, None) is spines
    assert trim_serif_hooks(spines, 0) is spines
    a, _ = bean_letter(spines, "S", entry=None, trim_at_mm=3.0)
    b, _ = bean_letter(spines, "S", entry=None, trim_at_mm=3.0, serif_mm=None)
    assert [r.points for r in a] == [r.points for r in b]


def test_serif_hook_is_cut_at_both_ends_and_the_arm_is_kept():
    import math

    from digitizer_core.stage6_beanletter import trim_serif_hooks

    # An E's top arm with a slab serif dropping 0.35 mm at its right end, and
    # a T's bar with one at each end.
    arm = [(2.0, 0.35), (2.0, 0.0), (0.0, 0.0)]
    bar = [(0.0, 0.35), (0.0, 0.0), (2.4, 0.0), (2.4, 0.35)]
    (arm2,), (bar2,) = trim_serif_hooks([arm], 0.45), trim_serif_hooks([bar], 0.45)
    assert arm2[-1] == (0.0, 0.0), "the free end with no hook is untouched"
    assert abs(arm2[0][1]) < 0.05 and abs(arm2[0][0] - 2.0) < 0.1, f"hook cut at the corner, got {arm2[0]}"
    assert all(abs(p[1]) < 0.05 for p in bar2), f"both of the bar's hooks cut: {bar2}"
    assert math.dist(bar2[0], bar2[-1]) > 2.2, "the bar itself is kept"


def test_serif_trim_leaves_a_curve_and_a_short_stroke_alone():
    import math

    from digitizer_core.stage6_beanletter import trim_serif_hooks

    # The tail of a 9: a quarter arc of 1 mm radius turns gently.
    arc = [(math.cos(t), math.sin(t)) for t in [k * (math.pi / 2) / 30 for k in range(31)]]
    assert trim_serif_hooks([arc], 0.45)[0] == arc
    # A stroke that would be left under twice its hook is never cut: there is
    # no letter left. One that keeps enough is (Fremont's E at 81 mm: arms
    # about 1 mm, which a fixed three-serif floor refused, and it read as B).
    short = [(0.0, 0.3), (0.0, 0.0), (0.4, 0.0)]
    assert trim_serif_hooks([short], 0.45)[0] == short
    arm81 = [(1.0, 0.3), (1.0, 0.0), (0.0, 0.0)]
    cut = trim_serif_hooks([arm81], 0.45)[0]
    assert abs(cut[0][1]) < 0.05 and cut[-1] == (0.0, 0.0), f"the 1 mm arm loses its hook: {cut}"


# --- The ink reader on a cutout (`ink_path.read_cluster_ink`) --------------
# A letter's counter on a transparent PNG is transparency stage 1 files under
# `enclosed_mask`, not `bg_mask`. Read as ink it filled every counter, and the
# bean centreline of Enthusiast's P lost its bowl and read as an "r".

def test_a_cutout_letters_counter_is_not_ink():
    from digitizer_core.ink_path import read_cluster_ink

    ppm = 20.0
    h = w = 200
    rgb = np.zeros((h, w, 3), np.uint8)                 # exporter's black under alpha
    opaque = np.zeros((h, w), np.uint8)
    cv2.circle(opaque, (100, 100), 30, 255, 6)          # an "O": 3 mm round, 0.3 mm stroke
    enclosed = np.zeros((h, w), np.uint8)
    cv2.circle(enclosed, (100, 100), 27, 255, -1)
    enclosed = (enclosed > 0) & (opaque == 0)
    bg = (opaque == 0) & ~enclosed
    rgb[opaque > 0] = (60, 60, 60)
    p = Prep(rgb=rgb, bg_mask=bg, px_per_mm=ppm, art_bbox=(0, 0, w, h),
             bg_from_alpha=True, enclosed_mask=enclosed)
    outer = Polygon([(((100 + 33 * np.cos(t)) - w / 2) / ppm, ((100 + 33 * np.sin(t)) - h / 2) / ppm)
                     for t in np.linspace(0, 2 * np.pi, 48, endpoint=False)])
    ring = Region("Sring", outer, 3, "3", float(outer.area))   # the traced blob: counter lost
    (reading,) = read_cluster_ink(p, [ring])
    assert reading.spines, "the letter has ink"
    pts = np.array([q for s in reading.spines for q in s])
    radius = np.hypot(pts[:, 0], pts[:, 1])
    assert radius.min() > 1.0, f"the centreline runs round the counter, not through it (min r {radius.min():.2f} mm)"
    assert abs(float(np.median(radius)) - 1.5) < 0.2, "on the stroke, 1.5 mm out"


def test_restore_drops_the_taggers_strays_from_the_line():
    # Fremont's tagline cluster holds its two black separator bars and a
    # twist of the rope. Bean letters reads a cluster's ink as one colour, so
    # with them in it the tagline was never read. They leave the cluster.
    regions, p = _scene()
    bar = Region("Sbar", box(4.0, -1.0, 4.2, 1.5), 9, "9", 0.5)       # another ink, in the line
    rope = Region("Srope", box(-6.0, 4.0, -5.0, 6.0), 7, "7", 2.0)    # same ink, far off the line
    regions += [bar, rope]
    _tag(regions, {"Sg0", "Sg2", "Sg3", "Sbar", "Srope"})
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row.get("strays") == 2, row
    for r in (bar, rope):
        assert "text_cluster_id" not in r.meta and "text_candidate" not in r.meta
        assert r.meta.get("small_text_stray") is True
    assert all(r.meta.get("text_cluster_id") == "TCtest" for r in _glyphs(regions)), "the four digits stay"


def test_serif_trim_never_cuts_where_strokes_meet():
    # The 8 at 81 mm: two loop arcs meeting at the waist turn sharply there,
    # and were cut open as if the turn were a serif. A junction is not a
    # free end.
    from digitizer_core.stage6_beanletter import trim_serif_hooks

    waist_l, waist_r = (0.0, 0.0), (0.6, 0.0)
    top = [waist_l, (-0.1, -0.3), (0.0, -0.6), (0.3, -0.7), (0.6, -0.6), (0.7, -0.3), waist_r]
    bottom = [waist_l, (-0.15, 0.35), (0.0, 0.7), (0.3, 0.8), (0.6, 0.7), (0.75, 0.35), waist_r]
    bar = [waist_l, (0.3, 0.0), waist_r]
    assert trim_serif_hooks([top, bottom, bar], 0.45) == [top, bottom, bar]
    # ...while a free end on the same spine set is still trimmed.
    hooked = [(1.5, 0.3), (1.5, 0.0), waist_r]
    out = trim_serif_hooks([top, bottom, bar, hooked], 0.45)
    assert out[:3] == [top, bottom, bar] and out[3][0] != hooked[0]


def test_one_switch_fills_the_four_values_and_explicit_ones_win():
    from dataclasses import replace

    from digitizer_core.config import SMALL_TEXT_TRUE_SIZE

    off = PipelineConfig()
    assert off.small_text_true_size is False
    assert all(getattr(off, k) is None for k in SMALL_TEXT_TRUE_SIZE)
    on = PipelineConfig(small_text_true_size=True)
    assert {k: getattr(on, k) for k in SMALL_TEXT_TRUE_SIZE} == SMALL_TEXT_TRUE_SIZE
    mixed = PipelineConfig(small_text_true_size=True, bean_letter_max_stroke_mm=0.4)
    assert mixed.bean_letter_max_stroke_mm == 0.4 and mixed.small_text_restore_mm == 3.0
    # replace() re-runs __post_init__ and keeps what is already set
    assert replace(on, target_width_mm=81.0).bean_letter_stitch_mm == 0.45


def test_min_arm_none_is_byte_identical_and_a_shorter_floor_keeps_a_1s_flag_and_foot():
    from digitizer_core.stage6_beanletter import bean_letter

    # Fremont's 1 at 81 mm: stem 1.24, flag 0.44, foot halves 0.41 and 0.39,
    # each short arm meeting the stem.
    stem = [(0.0, 0.0), (0.0, 1.24)]
    flag = [(0.0, 0.0), (-0.31, 0.31)]
    foot_l = [(0.0, 1.24), (-0.41, 1.24)]
    foot_r = [(0.0, 1.24), (0.39, 1.24)]
    spines = [stem, flag, foot_l, foot_r]
    a, ra = bean_letter(spines, "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45)
    b, _ = bean_letter(spines, "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, min_arm_mm=None)
    assert [r.points for r in a] == [r.points for r in b]
    assert ra["strokes"] == 1, "at the 0.45 pitch only the stem sews: a bare stick"
    _, rc = bean_letter(spines, "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, min_arm_mm=0.3)
    assert rc["strokes"] == 4
    # ...but a short link between two junctions (an 8's waist) still needs the pitch.
    top = [(0.0, 0.0), (-0.2, -0.6), (0.2, -1.0), (0.6, -0.6), (0.35, 0.0)]
    bottom = [(0.0, 0.0), (-0.3, 0.6), (0.2, 1.0), (0.7, 0.6), (0.35, 0.0)]
    waist = [(0.0, 0.0), (0.35, 0.0)]
    _, rw = bean_letter([top, bottom, waist], "S", entry=None, trim_at_mm=3.0,
                        stitch_mm=0.45, min_arm_mm=0.3)
    assert rw["strokes"] == 2


def test_corner_none_is_byte_identical_and_a_corner_gets_its_own_station():
    import math

    from digitizer_core.stage6_beanletter import bean_letter

    # The top of Fremont's 5: a stem rising 0.55 mm into a bar running 0.8
    # mm right, sampled like a skeleton (0.05 mm steps).
    stem = [(0.0, 0.55 - 0.05 * i) for i in range(12)]
    bar = [(0.05 * i, 0.0) for i in range(1, 17)]
    spine = stem + bar
    a, _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45)
    b, _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, corner_deg=None)
    assert [r.points for r in a] == [r.points for r in b]
    gap = min(math.dist(p, (0.0, 0.0)) for p in a[0].points)
    assert gap > 0.05, f"even pitch cuts the corner (nearest station {gap:.2f} mm)"
    c, _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, corner_deg=50.0)
    assert min(math.dist(p, (0.0, 0.0)) for p in c[0].points) < 0.03


def test_corner_leaves_a_round_bowl_alone():
    import math

    from digitizer_core.stage6_beanletter import _corners

    # a 0.5 mm radius arc, the bowl of a 1.9 mm digit
    arc = [(0.5 * math.cos(t / 40 * math.pi), 0.5 * math.sin(t / 40 * math.pi)) for t in range(41)]
    assert _corners(arc, 50.0) == []


def test_passes_none_is_three_and_one_or_two_lap_the_spine():
    from digitizer_core.stage6_beanletter import bean_letter

    spine = [(0.0, 0.0), (1.8, 0.0)]                # 4 stations at 0.45
    a, _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45)
    b, _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, passes=None)
    assert [r.points for r in a] == [r.points for r in b]
    three = a[0].points
    assert len(three) == 5 + 4 + 4 and three[-1] == (1.8, 0.0)
    (one,), _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, passes=1)
    assert len(one.points) == 5 and one.points[-1] == (1.8, 0.0)
    (two,), _ = bean_letter([spine], "S", entry=None, trim_at_mm=3.0, stitch_mm=0.45, passes=2)
    assert len(two.points) == 9 and two.points[-1] == (0.0, 0.0), "an even count ends where it began"
    # with corners on, the count still holds
    (c1,), _ = bean_letter([[(0.0, 0.6), (0.0, 0.0), (0.9, 0.0)]], "S", entry=None, trim_at_mm=3.0,
                           stitch_mm=0.45, corner_deg=50.0, passes=1)
    assert c1.points[0] in ((0.0, 0.6), (0.9, 0.0)) and c1.points[-1] in ((0.0, 0.6), (0.9, 0.0))
