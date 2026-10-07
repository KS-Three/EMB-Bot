"""Letterform priors (`digitizer_core/letterform_priors.py`, behind
`PipelineConfig.letterform_priors_k`, default None).

The pure-geometry half: the tolerance cap, the grid gate's byte-identical
pass-through, line and arc fits on synthetic stems and bowls, per-letter
refusal, a pinched counter kept open. Then the wiring: OFF never imports
the module and is byte-identical; ON refits a synthetic low-resolution
letter through `digitize()` and leaves a clean synthetic one byte-identical;
a compound letter is refused untouched. The real-fixture identity check
(drone / enthusiast / fremont ON == OFF) runs only under
`EMB_SLOW_TESTS=1`: it is three to four minutes of engine time."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import letterform_priors as fit  # noqa: E402

PX = 0.66          # Becker's source pixel at 95.7 mm
GRID = 1 / 6.06    # the working grid that run traced it on
K = 0.75
TOL = K * PX


def _prior(widths=(4.8,), baseline=None, cap=None, px=PX, grid=GRID, k=K):
    return fit.WordPrior(line_deg=0.0, slant_deg=0.0, stem_deg=90.0, baseline_v=baseline,
                         cap_v=cap, widths_mm=list(widths), tol_mm=k * px, src_px_mm=px,
                         grid_px_mm=grid, k=k)


def _staircase(ring: np.ndarray, px: float, seed: int, amp: float = 0.35) -> np.ndarray:
    """A clean ring made raster-like: resampled every px along it, each
    vertex pushed along the normal by up to `amp` px, as a thresholded
    pixel edge would be. Deterministic."""
    rng = np.random.default_rng(seed)
    line = LineString(np.vstack([ring, ring[:1]]))
    n = max(8, int(line.length / px))
    pts = np.array([line.interpolate(i / n, normalized=True).coords[0] for i in range(n)])
    out = []
    for i in range(n):
        a, b = pts[i - 1], pts[(i + 1) % n]
        t = b - a
        t = t / max(np.hypot(*t), 1e-9)
        nrm = np.array([-t[1], t[0]])
        out.append(pts[i] + nrm * rng.uniform(-amp, amp) * px)
    return np.array(out)


def _two_way_max(a: Polygon, b: Polygon, step: float = 0.05) -> float:
    """Max distance between the two outlines, sampled both ways."""
    worst = 0.0
    for ra, rb in zip([a.exterior, *a.interiors], [b.exterior, *b.interiors]):
        la, lb = LineString(ra.coords), LineString(rb.coords)
        for src, dst in ((la, lb), (lb, la)):
            n = max(4, int(src.length / step))
            for i in range(n):
                worst = max(worst, dst.distance(src.interpolate(i / n, normalized=True)))
    return worst


def test_tolerance_cap_holds_both_ways():
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, PX, seed=1))
    res = fit.fit_letter(poly, _prior())
    assert res.status == "refit", (res.status, res.reason)
    assert res.moved_max_mm <= TOL + 1e-6
    assert _two_way_max(poly, res.polygon) <= TOL + 1e-3


def test_grid_gate_is_byte_identical():
    """A clean upload: the cap is under the working grid's pixel, so the
    word passes through untouched -- the SAME object, same WKB."""
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, 0.068, seed=2))
    prior = _prior(px=0.068, grid=1 / 13.64)
    assert prior.gated
    res = fit.fit_letter(poly, prior)
    assert res.status == "pass" and res.reason == "grid"
    assert res.polygon is poly
    assert res.polygon.wkb == poly.wkb
    before = fit.polygon_wkb_hash({"a": poly})
    assert fit.polygon_wkb_hash({"a": res.polygon}) == before


def test_stem_becomes_four_snapped_lines():
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, PX, seed=3))
    res = fit.fit_letter(poly, _prior(widths=(4.8,)))
    assert res.status == "refit", (res.status, res.reason)
    assert res.n_arc == 0 and res.n_pass == 0
    assert res.n_line == 4
    prims = res.rings[0].prims
    stems = [p for p in prims if p.snapped == "stem"]
    bars = [p for p in prims if p.snapped == "line"]
    assert len(stems) == 2 and len(bars) == 2
    for p in stems:
        d = p.p1 - p.p0
        assert abs(d[0]) < 1e-6          # exactly vertical in the frame
    # the two stem edges sit exactly the word's width apart
    xs = sorted(float(p.p0[0]) for p in stems)
    assert xs[1] - xs[0] == pytest.approx(4.8, abs=1e-6)
    # and the structure statistic sees no spread
    assert all(abs(a) < 1e-6 for a, _w in res.stem_angles)


def test_bowl_becomes_arcs_and_keeps_its_hole():
    t = np.linspace(0, 2 * math.pi, 200, endpoint=False)
    outer = np.column_stack([8 * np.cos(t), 8 * np.sin(t)])
    inner = np.column_stack([4 * np.cos(-t), 4 * np.sin(-t)])
    poly = Polygon(_staircase(outer, PX, seed=4), [_staircase(inner, PX, seed=5)])
    assert poly.is_valid
    res = fit.fit_letter(poly, _prior(widths=(4.0,)))
    assert res.status == "refit", (res.status, res.reason)
    assert len(res.polygon.interiors) == 1
    assert res.n_arc >= 2
    radii = [p.r for rf in res.rings for p in rf.prims if p.kind == "arc"]
    assert any(abs(r - 8.0) < TOL for r in radii), radii
    assert any(abs(r - 4.0) < TOL for r in radii), radii
    # far fewer pieces than the trace needed
    assert res.n_prims < res.before_n_prims


def test_blob_is_refused_and_left_alone():
    """Radial noise far over the cap at every vertex: no line or arc holds
    a run, the residue passes the share, the letter is refused untouched."""
    rng = np.random.default_rng(6)
    t = np.linspace(0, 2 * math.pi, 60, endpoint=False)
    r = 6.0 + rng.uniform(-3 * TOL, 3 * TOL, len(t))
    poly = Polygon(np.column_stack([r * np.cos(t), r * np.sin(t)]))
    poly = poly.buffer(0) if not poly.is_valid else poly
    res = fit.fit_letter(poly, _prior(widths=(4.0,)))
    assert res.status != "refit" or res.n_pass > 0
    if res.status == "refused":
        assert res.polygon is poly
        assert res.reason in ("unexplained", "cap", "invalid")


def test_pinched_notch_keeps_its_opening():
    """A foot notch whose roof sits within the cap of the word's baseline:
    the baseline snap would pinch it shut and the ring would cross itself.
    The repair reverts the primitives round the crossing; the result is a
    valid polygon that still has the notch."""
    depth = 1.2 * TOL
    ring = np.array([[0.0, 0.0], [12.0, 0.0], [12.0, 16.0], [7.0, 16.0], [7.0, 16.0 - depth],
                     [5.0, 16.0 - depth], [5.0, 16.0], [0.0, 16.0]])
    poly = Polygon(ring)
    res = fit.fit_letter(poly, _prior(widths=(5.0,), baseline=16.0, cap=0.0))
    assert res.status in ("refit", "refused"), res.reason
    assert res.polygon.is_valid
    if res.status == "refit":
        notch = Polygon([[5.0, 16.0 - depth], [7.0, 16.0 - depth], [7.0, 16.0], [5.0, 16.0]])
        # the notch's centre is still outside the letter
        assert not res.polygon.contains(Point(6.0, 16.0 - depth / 2))
        assert res.polygon.intersection(notch).area < 0.5 * notch.area


def test_refusal_reports_share_of_outline():
    """Half a letter clean, half a mess: the unexplained share is read
    against the whole outline, and the refusal names it."""
    rng = np.random.default_rng(7)
    clean = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 16.0]])
    t = np.linspace(0, 1, 40)
    messy_x = 10.0 - 10.0 * t
    messy_y = 16.0 + rng.uniform(-3 * TOL, 3 * TOL, len(t))
    ring = np.vstack([clean, np.column_stack([messy_x, messy_y])[1:-1]])
    poly = Polygon(ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    res = fit.fit_letter(poly, _prior(widths=(5.0,)))
    assert 0.0 <= res.unexplained_share <= 1.0
    if res.status == "refused":
        assert res.polygon is poly


def test_wkb_hash_is_deterministic_and_sensitive():
    a = Polygon([[0, 0], [1, 0], [1, 1], [0, 1]])
    b = Polygon([[0, 0], [1, 0], [1, 1.001], [0, 1]])
    assert fit.polygon_wkb_hash({"x": a, "y": b}) == fit.polygon_wkb_hash({"y": b, "x": a})
    assert fit.polygon_wkb_hash({"x": a}) != fit.polygon_wkb_hash({"x": b})


# ---------------------------------------------------------------- wiring
def _regions_hash(result) -> str:
    return fit.polygon_wkb_hash({r.shape_id: r.polygon for r in result.regions})


def _letters_png(tmp_path: Path, px_per_letter: int, name: str) -> Path:
    """A line of four block letters (I, L, T and an O with a counter) drawn
    at `px_per_letter` pixels of cap height and anti-aliased: at 24 px the
    engine upscales it (a low-resolution upload), at 160 px it does not."""
    from PIL import Image, ImageDraw
    s = px_per_letter / 16.0                      # 16 "units" of cap height
    w = int(80 * s) + 16
    h = int(28 * s) + 16
    im = Image.new("RGB", (w * 4, h * 4), "white")
    dr = ImageDraw.Draw(im)

    def rect(x0, y0, x1, y1):
        dr.rectangle([8 * 4 + x0 * s * 4, 8 * 4 + y0 * s * 4, 8 * 4 + x1 * s * 4, 8 * 4 + y1 * s * 4],
                     fill="black")
    rect(2, 4, 6, 20)                           # I
    rect(12, 4, 16, 20); rect(12, 16, 24, 20)   # L
    rect(30, 4, 44, 8); rect(35, 4, 39, 20)     # T
    cx, cy, r = 60 * s * 4 + 32, 12 * s * 4 + 32, 8 * s * 4
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill="black")
    dr.ellipse([cx - r / 2, cy - r / 2, cx + r / 2, cy + r / 2], fill="white")   # O
    im = im.resize((w, h), Image.LANCZOS)       # the anti-aliased edge a real file has
    out = tmp_path / f"{name}.png"
    im.save(out)
    return out


def _cfg(**kw):
    from digitizer_core import PipelineConfig
    return PipelineConfig(target_width_mm=60.0, garment_id="left_chest", max_colors=6, **kw)


def test_off_is_the_default_and_never_imports_the_module(tmp_path):
    """OFF is the shipped engine: the pipeline imports `letterform_priors`
    inside the flag's branch only, and an OFF run leaves it out of
    `sys.modules`."""
    import ast
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import run_stages

    assert PipelineConfig().letterform_priors_k is None
    src = HERE.parent / "digitizer_core" / "pipeline.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    top = [n for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom) and n.module == "letterform_priors" and n.col_offset == 0]
    assert not top, "letterform_priors must be imported inside the flag's branch, not at module level"
    sys.modules.pop("digitizer_core.letterform_priors", None)
    result = run_stages(str(_letters_png(tmp_path, 24, "lowres")), _cfg())
    assert "digitizer_core.letterform_priors" not in sys.modules
    assert not any("letterform_prior" in r.meta for r in result.regions)
    sys.modules["digitizer_core.letterform_priors"] = fit     # this module's own import


def test_on_refits_a_low_resolution_letter_through_the_pipeline(tmp_path):
    """A 24 px cap height at 60 mm is a 1.6 mm source pixel: the engine
    upscales it, the cap (1.2 mm) is over the grid pixel, and the tagged
    letters come out refit with the outcome on their meta and their ids kept."""
    from digitizer_core.pipeline import run_stages
    png = str(_letters_png(tmp_path, 24, "lowres"))
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(letterform_priors_k=0.75))
    tagged = [r for r in on.regions if r.meta.get("text_candidate")]
    assert len(tagged) >= 3, "the synthetic line was not tagged as lettering"
    outcomes = {r.shape_id: r.meta.get("letterform_prior") for r in tagged}
    assert all(v for v in outcomes.values()), outcomes
    assert any(v == "refit" for v in outcomes.values()), outcomes
    assert {r.shape_id for r in on.regions} == {r.shape_id for r in off.regions}
    assert _regions_hash(on) != _regions_hash(off)
    off_by_id = {r.shape_id: r for r in off.regions}
    for r in tagged:
        before = off_by_id[r.shape_id].polygon
        if r.meta["letterform_prior"] == "refit":
            assert r.polygon.wkb != before.wkb
            assert len(r.polygon.interiors) == len(before.interiors)
            # the same ink, and nowhere further from the trace than the cap
            # (the ink spans ~99 px at 60 mm: a 0.6 mm source px, cap 0.45;
            # 1.2 mm is a loose bound on it. An arc written at 0.02 mm chord
            # error has MORE vertices than a coarse trace, so vertex counts
            # say nothing.)
            assert abs(r.polygon.area - before.area) < 0.15 * before.area
            assert _two_way_max(before, r.polygon, step=0.1) <= 1.2
        else:
            assert r.polygon.wkb == before.wkb


def test_on_leaves_a_clean_upload_byte_identical(tmp_path):
    """160 px of cap height at 60 mm is a 0.24 mm source pixel, finer than
    the engine's grid: the gate passes the word through and the whole region
    list hashes the same with the flag on and off."""
    from digitizer_core.pipeline import run_stages
    png = str(_letters_png(tmp_path, 160, "clean"))
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(letterform_priors_k=0.75))
    assert any(r.meta.get("text_candidate") for r in on.regions)
    assert _regions_hash(on) == _regions_hash(off)
    assert {r.meta.get("letterform_prior") for r in on.regions if r.meta.get("text_candidate")} == {"pass:grid"}


def test_a_compound_blob_is_refused_and_left_as_traced():
    """Two letters fused into one wobbly region: no line or arc explains it
    within the cap, the fit refuses, and `apply` leaves the polygon alone
    while still naming the outcome."""
    from digitizer_core.regions import Region
    rng = np.random.default_rng(11)
    t = np.linspace(0, 2 * math.pi, 90, endpoint=False)
    r = 6.0 + 2.0 * np.cos(3 * t) + rng.uniform(-3 * TOL, 3 * TOL, len(t))
    blob = Polygon(np.column_stack([r * np.cos(t), r * np.sin(t)]))
    if not blob.is_valid:
        blob = blob.buffer(0)
    regions = []
    for i, dx in enumerate((0.0, 18.0, 36.0)):
        poly = Polygon([[dx, 0], [dx + 4.8, 0], [dx + 4.8, 16], [dx, 16]])
        regions.append(Region(shape_id=f"S{i}", polygon=poly, thread_index=0, thread_number="",
                              area_mm2=poly.area,
                              meta={"text_candidate": True, "text_cluster_id": "T1"}))
    from shapely.affinity import translate
    blob = translate(blob, 54.0, 8.0)
    regions.append(Region(shape_id="Sblob", polygon=blob, thread_index=0, thread_number="",
                          area_mm2=blob.area, meta={"text_candidate": True, "text_cluster_id": "T1"}))
    before = blob.wkb
    fit.apply_letterform_priors(regions, src_px_mm=PX, grid_px_mm=GRID, k=K)
    blob_region = next(r for r in regions if r.shape_id == "Sblob")
    assert blob_region.meta["letterform_prior"].startswith(("refused:", "refit"))
    if blob_region.meta["letterform_prior"].startswith("refused:"):
        assert blob_region.polygon.wkb == before
    assert all(r.meta.get("letterform_prior") for r in regions)


@pytest.mark.skipif(not os.environ.get("EMB_SLOW_TESTS"),
                    reason="three to four minutes of engine time; EMB_SLOW_TESTS=1 runs it")
@pytest.mark.parametrize("rel,width,garment", [
    ("photo/drone_render.png", 80.0, "left_chest"),
    ("photo/enthusiast_logo.png", 100.0, "left_chest"),
    ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
])
def test_clean_real_uploads_are_byte_identical_on(rel, width, garment):
    """Go/no-go 1 on the real fixtures: a source finer than the working grid
    is gated, so ON equals OFF to the byte on every region."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import run_stages
    src = str(HERE.parent / "testdata" / rel)
    kw = dict(target_width_mm=width, garment_id=garment, max_colors=6)
    off = run_stages(src, PipelineConfig(**kw))
    on = run_stages(src, PipelineConfig(letterform_priors_k=0.75, **kw))
    assert _regions_hash(on) == _regions_hash(off)
    tagged = {r.meta.get("letterform_prior") for r in on.regions if r.meta.get("letterform_prior")}
    assert tagged <= {"pass:grid"}, tagged
