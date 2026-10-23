"""`cfg.small_text_cap_letter_gap_mm` and `cfg.small_text_cap_bold_scale`
(2026-10-21, built OFF): grown small words RE-SET the way the professional
sets them (`docs/pro-digitizer-rules-2026-10-21.md`, R4) -- letters grown to
the cap, the gaps between them closed to a visible gap, each letter widened
into what that frees, the line as wide as room allows, bars of the line
moved to the middle of their room.

Measured at 92.5 mm Hat with `lettering_columns_small_bold`
(`tools/small_text_columns.py`, both machine files read the same way, each in
its own frame): condensed growth sewed Fremont's EAT, STAY, PLAY and 1895
letter into letter (visible gap 0) and left Drone's AND DRONE at 2.2 mm (no
room); re-set, the gaps read 0.2-0.35 mm against the pro's 0.15-0.6.

The synthetic scene is `tests/test_small_text.py`'s: tan 2 mm lettering on a
white raster, one solid polygon per glyph as the tracer hands them over.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, small_text
from digitizer_core.regions import Region
from digitizer_core.small_text import enlarge_small_text
from digitizer_core.stage1_prep import Prep
from tests.test_small_text import H, INK, GROUND, PPM, W, _glyphs, _mm, _scene, _tag

GAP = 0.25
KW = dict(cap_mm=3.7, min_stroke_mm=0.85, letter_gap_mm=GAP, bold_scale=1.45)


def _heights(regions):
    return [r.polygon.bounds[3] - r.polygon.bounds[1] for r in _glyphs(regions)]


# --- OFF -------------------------------------------------------------------------

def test_both_flags_are_off_by_default():
    cfg = PipelineConfig()
    assert cfg.small_text_cap_letter_gap_mm is None
    assert cfg.small_text_cap_bold_scale is None


def test_none_is_byte_identical_and_never_reaches_the_re_set(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("re-set code reached with the flag off")
    a, p = _scene()
    _tag(a, {"Sg0", "Sg1", "Sg2", "Sg3"})
    rep_a = enlarge_small_text(a, p, cap_mm=3.7, min_stroke_mm=0.85)
    for name in ("_place_line_reset", "_reset_line", "_reset_word", "_join_line_ends", "_reset_apply"):
        monkeypatch.setattr(small_text, name, boom)
    b, p = _scene()
    _tag(b, {"Sg0", "Sg1", "Sg2", "Sg3"})
    rep_b = enlarge_small_text(b, p, cap_mm=3.7, min_stroke_mm=0.85,
                               letter_gap_mm=None, bold_scale=1.45)
    assert rep_a == rep_b
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in a] == \
        [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in b]


# --- ON --------------------------------------------------------------------------

def test_re_set_grows_to_the_cap_and_closes_the_gaps_to_the_asked_visible_gap():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    rep = enlarge_small_text(regions, p, **KW)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row, row
    assert row["letters"] == 4
    hs = _heights(regions)
    assert max(hs) - min(hs) < 0.5 and abs(float(np.median(hs)) - 3.7) < 0.4, hs
    g = _glyphs(regions)
    # each pair: the polygon gap that sews `GAP` of visible fabric
    want = GAP + 2 * small_text.SEWN_EDGE_MM
    for a, b in zip(g, g[1:]):
        assert a.polygon.distance(b.polygon) == pytest.approx(want, abs=0.04)


def test_the_stroke_target_is_the_floor_or_the_bolded_grown_stroke():
    it = {"stroke": 0.4}
    assert small_text._stroke_target(it, 2.0, 0.85, None) == 0.85
    assert small_text._stroke_target(it, 2.0, 0.85, 1.45) == pytest.approx(1.16)   # 1.45 x 2.0 x 0.4
    assert small_text._stroke_target(it, 1.2, 0.85, 1.45) == 0.85                  # the floor wins
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"}, stroke_half_mm=0.2)
    thin = next(r for r in enlarge_small_text(regions, p, **{**KW, "bold_scale": None}) if r["cluster"] == "TCtest")
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"}, stroke_half_mm=0.2)
    bold = next(r for r in enlarge_small_text(regions, p, **KW) if r["cluster"] == "TCtest")
    assert bold["widened_mm"] > thin["widened_mm"]


def test_a_space_between_words_is_kept_as_drawn():
    img = np.full((H, W, 3), GROUND, np.uint8)
    mask = np.zeros((H, W), np.uint8)
    for t, (x, y) in (("AB", (250, 262)), ("CD", (520, 262))):
        cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2.0, INK, 6, cv2.LINE_AA)
        cv2.putText(mask, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 255, 6, cv2.LINE_8)
    regions = [Region("Sbase", box(-20, -10, 20, 10), 1, "1", 800.0)]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    glyphs = sorted((Polygon(_mm(c.reshape(-1, 2))).buffer(0) for c in contours), key=lambda q: q.bounds[0])
    for i, gl in enumerate(glyphs):
        regions.append(Region(f"Sg{i}", gl, 7, "7", float(gl.area), meta={"rescued_small_shape": True}))
    p = Prep(rgb=img, bg_mask=np.zeros((H, W), bool), px_per_mm=PPM, art_bbox=(0, 0, W, H))
    art_space = glyphs[2].bounds[0] - glyphs[1].bounds[2]
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    rep = enlarge_small_text(regions, p, **KW)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row, row
    g = _glyphs(regions)
    assert g[2].polygon.bounds[0] - g[1].polygon.bounds[2] >= art_space - 1e-6, "the space did not close"
    assert g[1].polygon.distance(g[0].polygon) < 1.0, "the letters of a word did"


def test_a_bar_between_words_goes_to_the_middle_of_its_room():
    regions, p = _scene(text_at=((180, 262), (560, 262)), words=("EAT", "STAY"))
    g = _glyphs(regions)
    left = {r.shape_id for r in g if r.polygon.bounds[2] < 0}
    _tag(regions, left, cid="TCleft")
    _tag(regions, {r.shape_id for r in g} - left, cid="TCright")
    # the tagline's "|", drawn nearer the left word than the right
    bar = Region("Sbar", box(-2.0, -1.2, -1.75, 3.2), 3, "3", 1.1)
    regions.append(bar)
    rep = {r["cluster"]: r for r in enlarge_small_text(regions, p, **KW)}
    assert "skipped" not in rep["TCleft"] and "skipped" not in rep["TCright"], rep
    lo = max(r.polygon.bounds[2] for r in _glyphs(regions) if r.polygon.bounds[2] < bar.polygon.bounds[0] + 0.5)
    hi = min(r.polygon.bounds[0] for r in _glyphs(regions) if r.polygon.bounds[0] > bar.polygon.bounds[2] - 0.5)
    mid = (bar.polygon.bounds[0] + bar.polygon.bounds[2]) / 2
    assert mid == pytest.approx((lo + hi) / 2, abs=0.05)
    assert bar.meta.get("small_text_bar_moved_mm") is not None
    assert bar.polygon.bounds[3] - bar.polygon.bounds[1] == pytest.approx(4.4), "moved, never resized"


def test_a_letter_of_another_thread_at_the_line_end_joins_it():
    regions, p = _scene()
    g = _glyphs(regions)
    _tag(regions, {"Sg1", "Sg2", "Sg3"})
    g[0].thread_index, g[0].thread_id = 9, "9"          # the tracer's own thread for the 1
    rep = enlarge_small_text(regions, p, **KW)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row.get("joined") == 1 and row["letters"] == 4, row
    assert g[0].meta.get("small_text_enlarged") == row["scale"] and g[0].thread_index == 9
    hs = _heights(regions)
    assert max(hs) - min(hs) < 0.5


def test_the_regularizer_leaves_a_re_set_letter_as_set():
    from digitizer_core.textcluster import regularize_text_clusters
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    enlarge_small_text(regions, p, **KW)
    before = {r.shape_id: r.polygon.wkb for r in _glyphs(regions)}
    regularize_text_clusters(regions, p, pull_mm=0.4)
    for r in _glyphs(regions):
        assert r.polygon.wkb == before[r.shape_id], r.shape_id
        assert r.meta["text_cluster_regularize_skip_reason"] in ("small_text_reset", "has_interior_hole")


def test_widening_keeps_a_small_counter_open():
    ring = Polygon([(0, 0), (2, 0), (2, 3), (0, 3)], [[(0.85, 1.2), (1.15, 1.2), (1.15, 1.8), (0.85, 1.8)]])
    out = small_text._widen_keep_counters(ring, 0.3)
    assert len(out.interiors) == 1, "the counter survived"
    x0, y0, x1, y1 = out.bounds
    assert (x0, y0, x1, y1) == pytest.approx((-0.3, -0.3, 2.3, 3.3), abs=0.01), "the outline got the whole widening"
    # the growth's own rule would have fallen back to half (it closes the 0.3 mm counter)
    assert len([q for q in small_text._polys(ring.buffer(0.3)) if q.area > 0][0].interiors) == 0
    assert small_text._widen_keep_counters(ring, 0.0) is ring


def test_a_lone_line_never_slides_far_sideways():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    # a post hard against the line's left end: only a slide would fit it at full height
    x0 = min(r.polygon.bounds[0] for r in _glyphs(regions))
    regions.append(Region("Spost", box(x0 - 1.6, -6, x0 - 1.0, 6), 2, "2", 7.2))
    rep = enlarge_small_text(regions, p, **KW)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    if "skipped" not in row:
        assert abs(row["shift_mm"][0]) <= small_text.RESET_MAX_SIDE_CAPS * KW["cap_mm"] + 1e-9


# --- the Column lane under small_bold -------------------------------------------

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "fremont92_reset_letters.json"


def _lane_letters():
    out = {}
    for sid, v in json.loads(LETTERS.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        if v.get("counter_holes"):
            kw["counter_holes"] = [Polygon(h) for h in v["counter_holes"]]
        out[sid] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def test_the_coverage_retry_changes_only_a_letter_it_covers_more_of(monkeypatch):
    """On #1025's 21 condensed grown letters the retry
    (`columns.SMALL_BOLD_COVER_MIN`) fires on EST's E alone -- small_bold
    left two of its arms as travel -- and the plain cut it keeps sews more
    of it; every other letter is sewn exactly as before."""
    from digitizer_core import columns
    from tests.test_column_small_bold import _letters
    small = {k: v for k, v in _letters().items() if not k.startswith("BIG_")}

    def sew():
        out = {}
        for name, (poly, kw) in small.items():
            runs, _rep = columns.lettering_columns_shape(poly, name, **kw, small_bold=True)
            out[name] = ([(round(x, 4), round(y, 4), r.kind) for r in runs for x, y in r.points],
                         columns.satin_cover(runs, poly))
        return out
    floor = columns.SMALL_BOLD_COVER_MIN
    now = sew()
    monkeypatch.setattr(columns, "SMALL_BOLD_COVER_MIN", 0.0)
    before = sew()
    changed = sorted(k for k in now if now[k][0] != before[k][0])
    assert changed == ["EST_E"], changed
    assert before["EST_E"][1] < floor <= now["EST_E"][1]


def test_every_re_set_letter_is_sewn_over_most_of_it():
    from digitizer_core import columns
    worst = 1.0
    for sid, (poly, kw) in _lane_letters().items():
        runs, rep = columns.lettering_columns_shape(poly, sid, **kw)
        assert rep["columns_unsewn"] == 0 or columns.satin_cover(runs, poly) >= 0.9, sid
        worst = min(worst, columns.satin_cover(runs, poly))
    assert worst >= 0.83, worst
