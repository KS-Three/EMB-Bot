"""The small-text re-set on a line set on an arc, and the re-set's record kept
(2026-11-14, the Director's next-wave brief; all built OFF).

- `cfg.extra["small_text_arc_reset"]` (`small_text._arc_line`): the re-set
  grows horizontal lines only. A line set on an arc stands its letters at
  every slant, so the pass refuses it (`tall_enough` / `not_one_line`):
  Bridge's BAR & RESTAURANT was never raised. ON, a refused cluster whose
  letters sit on a circle is unrolled, re-set by the same pass, and rolled
  back: taller, on the same circle, in the same order, no two letters
  touching.
- `cfg.extra["small_text_reset_respine"]` (`small_text._respine`): a grown
  letter carrying dark-ink bean spines has them re-read from its grown
  polygon (Fremont's EAT | STAY | PLAY was re-set, then sewn from spines
  written at the art's size).
- `cfg.extra["small_text_reset_report"]`: the re-set's rows reach the
  job's metrics as `small_text_reset`, so a trace can name why a line was
  not raised. Metrics only.

Absent or False, every one of them is the engine as it was.
"""
from __future__ import annotations

import hashlib
import math

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, box

from digitizer_core import preflight as pf
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.regions import Region
from digitizer_core.shapefield import build_shape_field
from digitizer_core.small_text import _fit_circle, enlarge_small_text
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import _skeleton_chains_mm
from tests.test_small_text import _glyphs, _scene, _tag
from tests.test_small_text_one_baseline import SHIPS

PPM = 24.0
SIDE = 960                      # 40 x 40 mm, the circle's centre at (0, 0)
INK, GROUND = (170, 150, 120), (255, 255, 255)
RADIUS = 12.0


def _md5(regions, rep=None) -> str:
    h = hashlib.md5()
    for r in regions:
        h.update(repr((r.shape_id, r.thread_index, r.polygon.wkb.hex(), sorted(r.meta.items(), key=repr))).encode())
    h.update(repr(rep).encode())
    return h.hexdigest()


def _strip(word: str):
    """The word set straight on a strip, the art before it is bent."""
    w, h = 720, 120
    img = np.full((h, w, 3), GROUND, np.uint8)
    mask = np.zeros((h, w), np.uint8)
    (tw, th), _ = cv2.getTextSize(word, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 6)
    org = ((w - tw) // 2, (h + th) // 2)
    cv2.putText(img, word, org, cv2.FONT_HERSHEY_SIMPLEX, 2.0, INK, 6, cv2.LINE_AA)
    cv2.putText(mask, word, org, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 255, 6, cv2.LINE_8)
    return img, mask


def _arc_scene(word: str = "RESTAURANT", radius: float = RADIUS, tilt_deg: float | None = None):
    """Small tan lettering on the BOTTOM of a circle about (0, 0), feet
    outward, read left to right (Bridge's BAR & RESTAURANT), or, with
    `tilt_deg`, set straight and turned by that angle. One solid polygon per
    letter, the way a tracer that drops counters hands them over."""
    strip, smask = _strip(word)
    sh, sw = smask.shape
    ys, xs = np.mgrid[0:SIDE, 0:SIDE].astype(np.float64)
    x, y = (xs - SIDE / 2) / PPM, (ys - SIDE / 2) / PPM
    if tilt_deg is None:
        rho = np.hypot(x, y)
        d = np.arctan2(y, x) - math.pi / 2.0
        u, v = -radius * d, rho - radius
    else:
        t = math.radians(tilt_deg)
        u, v = x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t)
    mx = (u * PPM + sw / 2).astype(np.float32)
    my = (v * PPM + sh / 2).astype(np.float32)
    img = cv2.remap(strip, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=GROUND)
    mask = cv2.remap(smask, mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    regions = [Region("Sbase", box(-20, -20, 20, 20), 1, "1", 1600.0)]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    glyphs = []
    for c in contours:
        a = c.reshape(-1, 2).astype(np.float64)
        poly = Polygon([((px - SIDE / 2) / PPM, (py - SIDE / 2) / PPM) for px, py in a]).buffer(0)
        poly = max(getattr(poly, "geoms", [poly]), key=lambda q: q.area)
        if poly.area > 0.05:
            glyphs.append(poly)
    glyphs.sort(key=lambda g: math.atan2(g.centroid.y, g.centroid.x), reverse=True)  # reading order
    for i, g in enumerate(glyphs):
        regions.append(Region(f"Sg{i:02d}", g, 7, "7", float(g.area), meta={"rescued_small_shape": True}))
    p = Prep(rgb=img, bg_mask=np.zeros((SIDE, SIDE), bool), px_per_mm=PPM, art_bbox=(0, 0, SIDE, SIDE))
    _tag(regions, {r.shape_id for r in regions if r.shape_id.startswith("Sg")}, cid="TCarc")
    return regions, p


def _letters(regions):
    return [r for r in regions if r.shape_id.startswith("Sg")]


def _radial(g, cx=0.0, cy=0.0) -> float:
    xy = np.asarray(g.exterior.coords)
    rho = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy)
    return float(rho.max() - rho.min())


def test_the_scene_is_small_lettering_on_an_arc_the_horizontal_pass_refuses():
    regions, p = _arc_scene()
    letters = _letters(regions)
    assert len(letters) >= 8
    caps = [_radial(r.polygon) for r in letters]
    assert 1.6 < float(np.median(caps)) < 2.6, caps
    rep = enlarge_small_text(regions, p, **SHIPS)
    row = next(r for r in rep if r["cluster"] == "TCarc")
    assert row.get("skipped") in ("tall_enough", "not_one_line"), row
    assert not any(r.meta.get("small_text_enlarged") for r in _letters(regions))


def test_absent_and_false_flags_are_the_pass_as_it_was():
    for scene in (_arc_scene, lambda: _scene()):
        a, pa = scene()
        b, pb_ = scene()
        if scene is not _arc_scene:
            _tag(a, {"Sg0", "Sg1", "Sg2", "Sg3"})
            _tag(b, {"Sg0", "Sg1", "Sg2", "Sg3"})
        ra = enlarge_small_text(a, pa, **SHIPS)
        rb = enlarge_small_text(b, pb_, **SHIPS, arc=False, respine=False, cap_from_trace=False)
        assert _md5(a, ra) == _md5(b, rb)


def test_a_line_on_an_arc_is_raised_along_its_own_arc():
    regions, p = _arc_scene()
    before = {r.shape_id: r.polygon for r in _letters(regions)}
    ids0 = [(r.shape_id, r.thread_index) for r in regions]
    rep = enlarge_small_text(regions, p, **SHIPS, arc=True)
    row = next(r for r in rep if r["cluster"] == "TCarc")
    arc = row["arc"]
    assert "skipped" not in arc and arc["moved"] >= len(before), row
    assert row["flat_skipped"] in ("tall_enough", "not_one_line")
    assert abs(arc["radius_mm"] - RADIUS) < 1.0 and arc["side"] == "bottom"
    assert [(r.shape_id, r.thread_index) for r in regions] == ids0, "no shape added, dropped or rethreaded"
    letters = _letters(regions)
    # taller, measured across the arc
    cap0 = float(np.median([_radial(g) for g in before.values()]))
    cap1 = float(np.median([_radial(r.polygon) for r in letters]))
    assert cap1 >= 1.15 * cap0, (cap0, cap1)
    assert cap1 <= SHIPS["cap_mm"] * 1.15, cap1
    # on the same circle: the letters' centres as far from the art's centre
    # as one another, within what the art's own letters spread at this scale
    # (a T's centre sits high, an A's low, and the offsets grow with them)
    def spread(polys):
        rho = [math.hypot(g.centroid.x, g.centroid.y) for g in polys]
        return max(rho) - min(rho), float(np.median(rho))
    s0, r0 = spread(before.values())
    s1, r1 = spread([r.polygon for r in letters])
    assert s1 <= arc["scale"] * s0 + 0.3 and abs(r1 - r0) < 2.0, (s0, r0, s1, r1)
    fit = _fit_circle([(r.polygon.centroid.x, r.polygon.centroid.y) for r in letters])
    assert math.hypot(fit[0], fit[1]) < 1.0 and fit[3] < 0.3, fit
    # in the same order along it, no two letters touching
    order0 = sorted(before, key=lambda s: -math.atan2(before[s].centroid.y, before[s].centroid.x))
    order1 = [r.shape_id for r in sorted(letters, key=lambda r: -math.atan2(r.polygon.centroid.y, r.polygon.centroid.x))]
    assert order1 == order0
    for i, a in enumerate(letters):
        assert a.polygon.is_valid and abs(a.area_mm2 - a.polygon.area) < 1e-9
        assert a.meta["small_text_arc"] == arc["radius_mm"] or abs(a.meta["small_text_arc"] - arc["radius_mm"]) < 0.01
        assert a.meta["small_text_enlarged"] >= 1.15
        for b in letters[i + 1:]:
            assert a.polygon.intersection(b.polygon).area < 1e-6, (a.shape_id, b.shape_id)
    # inside the design
    assert all(box(-20, -20, 20, 20).contains(r.polygon) for r in letters)


def test_a_straight_line_is_the_horizontal_pass_byte_for_byte():
    a, pa = _scene()
    b, pb_ = _scene()
    _tag(a, {"Sg0", "Sg1", "Sg2", "Sg3"})
    _tag(b, {"Sg0", "Sg1", "Sg2", "Sg3"})
    ra = enlarge_small_text(a, pa, **SHIPS)
    rb = enlarge_small_text(b, pb_, **SHIPS, arc=True)
    assert any(r.meta.get("small_text_enlarged") for r in _glyphs(b)), "the fixture grows"
    assert _md5(a, ra) == _md5(b, rb)


def test_a_turned_straight_line_is_no_arc_and_is_left_as_drawn():
    regions, p = _arc_scene(word="TAVERN", tilt_deg=35.0)
    before = _md5(regions)
    rep = enlarge_small_text(regions, p, **SHIPS, arc=True)
    row = next(r for r in rep if r["cluster"] == "TCarc")
    assert row.get("skipped") in ("tall_enough", "not_one_line"), row
    assert row["arc"]["skipped"] in ("straight", "off_circle", "no_circle"), row["arc"]
    assert _md5(regions) == before


def test_respine_rereads_bean_spines_from_the_grown_letter():
    def scene():
        regions, p = _scene()
        _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
        for r in _glyphs(regions):
            r.meta[BEAN_LETTER_KEY] = _skeleton_chains_mm(build_shape_field(r.polygon))
        return regions, p

    def spine_box(r):
        pts = np.array([q for chain in r.meta[BEAN_LETTER_KEY] for q in chain])
        return pts[:, 1].min(), pts[:, 1].max()

    off, p_off = scene()
    art = {r.shape_id: spine_box(r) for r in _glyphs(off)}
    enlarge_small_text(off, p_off, **SHIPS)
    on, p_on = scene()
    enlarge_small_text(on, p_on, **SHIPS, respine=True)
    grown = [r for r in _glyphs(on) if r.meta.get("small_text_enlarged")]
    assert grown, "the fixture grows"
    for r in _glyphs(off):          # OFF: the spines stay where the art drew them
        assert spine_box(r) == art[r.shape_id]
    for r in grown:                 # ON: they span the grown letter
        lo, hi = spine_box(r)
        b = r.polygon.bounds
        assert r.meta["small_text_respined"] is True
        assert hi - lo > 0.6 * (b[3] - b[1]) and b[1] - 0.05 <= lo and hi <= b[3] + 0.05, (lo, hi, b)
        a0, a1 = art[r.shape_id]
        assert hi - lo > 1.15 * (a1 - a0)


def test_the_report_reaches_metrics_only_under_its_flag():
    from types import SimpleNamespace

    from digitizer_core.stitches import StitchBlock, StitchPlan
    from tests.conftest import cfg

    plan = StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="1704", rgb=(230, 60, 60), runs=[])],
                      palette=[])
    rows = [{"cluster": "TCa", "members": 4, "skipped": "no_room", "blocked_by": [[3, (1.0, 2.0)]],
             "shift_mm": (np.float64(0.5), 1), "arc": {"radius_mm": np.float64(15.05)}}]
    result = SimpleNamespace(small_text_reset=rows, regions=[], design_class="flat")
    off = pf.run_preflight(result, plan, cfg())
    assert "small_text_reset" not in off["metrics"]
    on = pf.run_preflight(result, plan, cfg(extra={"small_text_reset_report": True}))
    got = on["metrics"]["small_text_reset"]
    assert got == [{"cluster": "TCa", "members": 4, "skipped": "no_room", "blocked_by": [[3, [1.0, 2.0]]],
                    "shift_mm": [0.5, 1], "arc": {"radius_mm": 15.05}}]
    assert type(got[0]["arc"]["radius_mm"]) is float
    none = pf.run_preflight(None, plan, cfg(extra={"small_text_reset_report": True}))
    assert none["metrics"]["small_text_reset"] is None


def test_the_generation_carries_the_rows_through_a_fork():
    from digitizer_core.pipeline import Generation
    import dataclasses
    fields = {f.name for f in dataclasses.fields(Generation)}
    assert "small_text_reset" in fields
    from digitizer_core.pipeline import PipelineResult
    assert "small_text_reset" in {f.name for f in dataclasses.fields(PipelineResult)}
    g = Generation.__new__(Generation)
    for f in dataclasses.fields(Generation):
        setattr(g, f.name, f.default if f.default is not dataclasses.MISSING else None)
    g.classification_warnings, g.quant_thread_indices, g.quant_warnings = [], [], []
    g.regions, g.dropped_areas, g.prep_warnings, g.small_warnings, g.resnap_warnings = [], [], [], [], []
    g.small_text_reset = [{"cluster": "TCa", "skipped": "tall_enough"}]
    f = g.fork()
    assert f.small_text_reset == g.small_text_reset and f.small_text_reset is not g.small_text_reset
