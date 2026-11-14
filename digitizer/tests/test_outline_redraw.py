"""Outline redraw (`digitizer_core/outline_redraw.py`, behind
`PipelineConfig.outline_redraw_k`, built None = OFF 2026-11-13; 0.75 since
2026-11-14 by Kent's flip, "Set 0.75"). `_cfg` below is the OFF arm unless a
test sets k.

Geometry first: a source staircase comes back as straight lines with square
corners, a faceted circle as an arc, a triangle keeps its tips, a counter
keeps its hole, nothing moves past the cap. Then the wiring: OFF never
imports the module and leaves no trace on the regions; ON runs through the
pipeline and stamps every region with its outcome."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import outline_redraw as orw  # noqa: E402


def _turns_deg(poly: Polygon) -> np.ndarray:
    P = np.asarray(poly.exterior.coords, float)[:-1]
    a, b = np.roll(P, 1, 0), np.roll(P, -1, 0)
    d1, d2 = P - a, b - P
    return np.degrees(np.arctan2(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0], (d1 * d2).sum(1)))


def _hausdorff(a: Polygon, b: Polygon) -> float:
    return a.exterior.hausdorff_distance(b.exterior)


def _staircase_bar(px: float, w_px: int = 30, h_px: int = 6, rise_every: int = 3) -> Polygon:
    """A bar drawn in `px`-mm source pixels, sloping one pixel up every
    `rise_every` across: the mask's staircase of a thin border on a
    low-resolution upload (Becker at 102 mm: 0.70 mm a pixel)."""
    top, bot = [], []
    for i in range(w_px + 1):
        y = (i // rise_every) * px
        top.append((i * px, y + h_px * px))
        bot.append((i * px, y))
    # stairs: each column edge is a vertical riser
    ring = []
    for i in range(w_px):
        ring += [bot[i], (bot[i + 1][0], bot[i][1])]
    ring.append(bot[-1])
    ring.append(top[-1])
    for i in range(w_px, 0, -1):
        ring += [top[i], (top[i - 1][0], top[i][1])]
    ring.append(top[0])
    return Polygon(ring).simplify(0)


def test_a_source_staircase_comes_back_as_two_straight_edges_and_square_ends():
    px = 0.70
    bar = _staircase_bar(px)
    tol = orw.redraw_cap_mm(px, px / 4.0)
    assert math.isclose(tol, 0.75 * px)
    new, outcome = orw.redraw_polygon(bar, tol)
    assert outcome == "redrawn"
    t = np.abs(_turns_deg(new))
    corners = t[t > 30.0]
    # four real corners (the bar's ends), every other vertex gone or flat
    assert len(corners) == 4, (len(new.exterior.coords), sorted(t)[-8:])
    assert len(np.asarray(bar.exterior.coords)) > 40 and len(np.asarray(new.exterior.coords)) <= 9
    assert _hausdorff(new, bar) <= tol + 1e-9


def test_a_faceted_circle_comes_back_round():
    """A 24-gon of radius 2.5 mm -- stage 4's chords on a clean bowl at 22
    px/mm, 15 deg a vertex -- with the grid pixel as the cap."""
    grid = 1 / 21.9
    r = 2.5
    ang = np.linspace(0, 2 * np.pi, 25)[:-1]
    ngon = Polygon(np.c_[r * np.cos(ang), r * np.sin(ang)])
    tol = orw.redraw_cap_mm(grid, grid)
    new, outcome = orw.redraw_polygon(ngon, tol)
    assert outcome == "redrawn"
    assert np.abs(_turns_deg(ngon)).max() > 14.0
    # an arc is written back at letterform_priors' step (<= 0.25 mm): about 6
    # degrees a vertex on this bowl (one junction 6.4), against the 24-gon's 15
    assert np.abs(_turns_deg(new)).max() < 7.0
    assert _hausdorff(new, ngon) <= tol + 1e-9


def test_a_triangle_keeps_its_tips():
    """low_poly's complaint is tips rounded off: the redraw must sharpen
    corners, never round them."""
    tri = Polygon([(0, 0), (10, 0), (5, 8)])
    px = 0.13
    stair = Polygon(np.asarray(tri.buffer(0).exterior.coords)).segmentize(px)
    new, outcome = orw.redraw_polygon(stair, orw.redraw_cap_mm(px, px))
    assert outcome in ("redrawn", "unexplained")
    for tip in tri.exterior.coords[:-1]:
        d = min(math.dist(tip, q) for q in new.exterior.coords)
        assert d < 1e-6, (tip, d)


def test_a_counter_keeps_its_hole_and_the_cap_holds_both_ways():
    r_out, r_in = 4.0, 1.6
    a = np.linspace(0, 2 * np.pi, 33)[:-1]
    ring = Polygon(np.c_[r_out * np.cos(a), r_out * np.sin(a)],
                   [np.c_[r_in * np.cos(a[::-1]), r_in * np.sin(a[::-1])]])
    tol = 0.05
    new, outcome = orw.redraw_polygon(ring, tol)
    assert outcome == "redrawn"
    assert len(new.interiors) == 1
    assert ring.exterior.hausdorff_distance(new.exterior) <= tol + 1e-9
    assert ring.interiors[0].hausdorff_distance(new.interiors[0]) <= tol + 1e-9


def test_an_invalid_input_comes_back_untouched():
    bow = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    new, outcome = orw.redraw_polygon(bow, 0.1)
    assert outcome == "invalid-input" and new is bow


def test_cap_never_drops_under_the_grid_pixel():
    assert orw.redraw_cap_mm(0.70, 0.176) == 0.75 * 0.70
    assert orw.redraw_cap_mm(1 / 22.0, 1 / 22.0) == 1 / 22.0


def test_lines_are_redrawn_only_on_an_upscaled_source():
    assert orw.redraws_lines(0.70, 0.176)              # Becker, x4
    assert orw.redraws_lines(1 / 3.85, 1 / 4.0)        # MFab, x1.04
    assert not orw.redraws_lines(1 / 22.0, 1 / 22.0)   # lettering at its own resolution


def test_arcs_only_leaves_a_shape_with_no_bowl_untouched():
    """A clean upload's straight-edged letter is the SAME object back."""
    ell = Polygon([(0, 0), (1.2, 0), (1.2, 6), (4, 6), (4, 7.2), (0, 7.2)])
    new, outcome = orw.redraw_polygon(ell, 1 / 22.0, arcs_only=True)
    assert outcome == "no-arc" and new is ell


def test_arcs_only_keeps_straight_runs_and_corners_vertex_for_vertex():
    """A 'D' at its own resolution: the stem and its two corners keep the
    trace's own vertices exactly; only the bowl's chords become an arc."""
    grid = 1 / 22.0
    a = np.linspace(-np.pi / 2, np.pi / 2, 13)
    bowl = np.c_[2.0 + 3.0 * np.cos(a), 3.0 + 3.0 * np.sin(a)]
    d = Polygon([(0, 0), (2.0, 0)] + [tuple(p) for p in bowl[1:-1]] + [(2.0, 6.0), (0, 6.0)])
    new, outcome = orw.redraw_polygon(d, orw.redraw_cap_mm(grid, grid), arcs_only=True)
    assert outcome == "redrawn"
    out = {tuple(np.round(p, 9)) for p in np.asarray(new.exterior.coords)}
    for corner in ((0.0, 0.0), (0.0, 6.0)):
        assert corner in out
    assert np.abs(_turns_deg(new)).max() < 91.0
    bow_turns = [abs(t) for t, p in zip(_turns_deg(new), np.asarray(new.exterior.coords)[:-1])
                 if p[0] > 2.3]
    assert max(bow_turns) < 8.0 < np.abs(_turns_deg(d))[3]


def _cfg(**kw):
    """OFF (k None, the engine before Kent's 2026-11-14 flip) unless `kw` sets k."""
    from digitizer_core import PipelineConfig
    kw.setdefault("outline_redraw_k", None)
    return PipelineConfig(target_width_mm=60.0, garment_id="left_chest", max_colors=6, **kw)


def test_off_path_never_imports_the_module():
    import ast
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import run_stages

    assert PipelineConfig().outline_redraw_k == 0.75     # Kent's flip 2026-11-14
    src = HERE.parent / "digitizer_core" / "pipeline.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    top = [n for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom) and n.module == "outline_redraw" and n.col_offset == 0]
    assert not top, "outline_redraw must be imported inside the flag's branch"
    saved = sys.modules.pop("digitizer_core.outline_redraw", None)
    try:
        result = run_stages(str(HERE.parent / "testdata" / "ribbon_curve.png"), _cfg())
        assert "digitizer_core.outline_redraw" not in sys.modules
        assert not any("outline_redraw" in r.meta for r in result.regions)
    finally:
        if saved is not None:
            sys.modules["digitizer_core.outline_redraw"] = saved


def _lowres_png(tmp_path) -> str:
    """A ring and a bar drawn 90 px wide: at 60 mm that is 1.5 px/mm, so
    stage 1 upscales it and the redraw's line-and-arc regime applies."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (90, 50), "white")
    dr = ImageDraw.Draw(im)
    dr.ellipse([4, 4, 44, 44], fill="black")
    dr.ellipse([16, 16, 32, 32], fill="white")
    dr.polygon([(52, 10), (86, 16), (84, 40), (54, 36)], fill="black")
    out = tmp_path / "lowres.png"
    im.save(out)
    return str(out)


def test_on_redraws_an_upscaled_source_and_keeps_its_ids(tmp_path):
    from digitizer_core.pipeline import run_stages
    png = _lowres_png(tmp_path)
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(outline_redraw_k=0.75))
    assert {r.shape_id for r in on.regions} == {r.shape_id for r in off.regions}
    assert all("outline_redraw" in r.meta for r in on.regions)
    assert any(r.meta["outline_redraw"] == "redrawn" for r in on.regions)


def test_a_source_at_its_own_resolution_is_untouched_unless_native_is_set(tmp_path):
    """The same drawing at 20 px/mm: stage 1 keeps it, and without
    `outline_redraw_native` the flag changes no polygon and stamps nothing."""
    from PIL import Image
    from digitizer_core.pipeline import run_stages
    src = Image.open(_lowres_png(tmp_path)).resize((1200, 667), Image.LANCZOS)
    png = tmp_path / "hires.png"
    src.save(png)
    png = str(png)
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(outline_redraw_k=0.75))
    assert [r.polygon.wkb for r in on.regions] == [r.polygon.wkb for r in off.regions]
    assert not any("outline_redraw" in r.meta for r in on.regions)
    nat = run_stages(png, _cfg(outline_redraw_k=0.75, outline_redraw_native=True))
    assert all("outline_redraw" in r.meta for r in nat.regions)
