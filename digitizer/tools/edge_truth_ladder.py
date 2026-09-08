#!/usr/bin/env python
"""Edge truth ladder: stage 4's polygons against the VECTOR truth, by resolution.

PR 1 of `docs/superpowers/plans/2026-09-08-subpixel-edges.md` (item 3 of
`docs/quality-review-2026-09-08.md`, Kent's pick). No engine change.

Every edge instrument this repo has measures against a RASTER —
`edge_smoothness.ragged_mm` against the artwork's own staircase,
`curve_fidelity.roughness_deg` against nothing but the path's turn
statistics. The synthetic fixtures carry their own vector truth:
`make_test_logo.py` draws a disc at (200, 250) radius 120, a ring at
(450, 250) radii 110/60, rectangles at known corners and a stroked polyline
for the ribbon, at 4x supersample, downscaled with INTER_AREA. This tool
regenerates `logo_whitebg` and `ribbon_curve` at 200, 400, 800, 1600 and
3200 px with the generator's own drawing code at the same 4x (the 800 rung
IS the committed fixture — a test pins that), runs stages 0-4 at 80 mm on
the flat lane, and measures each shape's polygon against the analytic edge
in the same frame.

No registration search and no rasterised truth. The truth is mapped into
the prepped raster's pixel frame analytically — output px = supersampled
px / 4, times stage 1's Lanczos upscale on a rung under the resolution
floor — and the polygon is mapped back from plan millimetres by inverting
stage 4's own `_to_mm`. cv2 names pixel CENTRES with its integer
coordinates and fills a drawn shape's covering pixels, so in edge
coordinates a disc of radius r sits at r + 0.5 about (cx + 0.5, cy + 0.5),
a rectangle includes both corners, and a thick polyline has ROUND caps of
half the thickness (measured on cv2 4.x, 2026-09-08; the generator's
docstring says square — the ribbon's caps are excluded from the measure
either way, because a cap is not the curve).

Per shape, in millimetres:

    offset_mm     signed mean distance of the polygon boundary from the
                  truth boundary, + where the polygon has material the truth
                  does not. `findContours` traces pixel centres, so the
                  trace of a filled shape sits half a pixel INSIDE its edge:
                  a small negative offset is expected, and shrinks with
                  resolution.
    spread_mm     standard deviation of that distance along the boundary —
                  the staircase and the chord sag, the number the plan is
                  about. Flag OFF today it is bounded below by the pixel and
                  falls with resolution; the plan's acceptance criterion for
                  `cfg.subpixel_edges` is that it comes out close to flat
                  across the ladder. Stated here before any engine code.
    rms_mm        root mean square of the signed distance (offset and spread
                  together).
    hausdorff_mm  the largest deviation anywhere on the boundary.
    roughness_deg `curve_fidelity`'s turn-change statistic read on the
                  polygon's vertices; n/a on a rectangle (no curve to read).

Deviation is sampled every half a prepped pixel along every ring of the
polygon, shell and holes, so a chord is measured at its sag and not only at
its ends, which lie on the curve for any decent fit.

Two floors show in the baseline (scope-history 09-08), and the second is
the one the plan had not priced: below ~15 px/mm the spread is the PIXEL
and falls with resolution; above it the spread is the 0.2 mm
Douglas-Peucker tolerance's chord sag, and does not fall — the ribbon keeps
the same 37 vertices and the same 0.065 mm spread from 400 to 1600 px. A
sub-pixel vertex fed to the same simplifier lands on the same floor, which
is why the plan's step 5 keys the refinement floor to acceptance. The
existing refinement (`curve_turn_deg`, ON by default at 15 degrees, gated at
20 px/mm) touches only the 3200 rung here; `--flag curve_turn_deg=0` shows
what it does there, and `--flag` takes any other `PipelineConfig` field the
same way, `cfg.subpixel_edges` included once PR 2 exists.

Gate 4: distances, not agreement rates; no chance floor is claimed.
Gate 1: nothing here is a sewing constant.

    .venv/bin/python tools/edge_truth_ladder.py                       # both fixtures, all rungs
    .venv/bin/python tools/edge_truth_ladder.py whitebg --rungs 400 1600
    .venv/bin/python tools/edge_truth_ladder.py --flag curve_turn_deg=15    # any PipelineConfig field ON
    .venv/bin/python tools/edge_truth_ladder.py --tiers [case ...] [--flag NAME[=VALUE]] [--all]

`--tiers` runs `curve_tiers.py`'s cases on the real fixtures and prints the
per-shape tier diff for any `PipelineConfig` field OFF vs ON, paired by id
and then by centroid — the flip evidence DOCTRINE requires of every stage-4
geometry change, from one command. Without `--flag` it lists the baseline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import curve_fidelity as cf                                            # noqa: E402
import make_test_logo as mtl                                           # noqa: E402
from digitizer_core import PipelineConfig                              # noqa: E402
from digitizer_core.pipeline import build_generation                   # noqa: E402
from thin_strokes import _plan_frame, parse_flag                       # noqa: E402

SUPER = 4                                  # the generator's supersample, relative to its output
RUNGS = (200, 400, 800, 1600, 3200)        # output widths; 800 is the committed fixture
TARGET_MM = 80.0
FIXTURES = ("whitebg", "ribbon")
SAMPLE_STEP_PX = 0.5                       # along the polygon boundary, prepped px
MATCH_IOU_MIN = 0.5                        # a region is a truth shape's when it overlaps it this well
PIXEL_HALF = 0.5                           # cv2 integer coordinate -> pixel centre, in edge coordinates


# --- regeneration -----------------------------------------------------------

def scale_for(width_px: int) -> int:
    """The supersample the generator's canvas needs for an output this wide:
    the canvas is `mtl.W * S` px and comes down 4x, so S = 4 * width / W."""
    s = width_px * SUPER / mtl.W
    if s < 1 or abs(s - round(s)) > 1e-9:
        raise ValueError(f"{width_px} px is not a whole 4x supersample of the {mtl.W}-px frame")
    return int(round(s))


@contextmanager
def _supersample(s: int):
    """`make_test_logo.draw_art` and `punch_hole` read the module's `S` at
    call time; set it for the duration of one drawing."""
    old = mtl.S
    mtl.S = s
    try:
        yield
    finally:
        mtl.S = old


def _down(canvas: np.ndarray, width_px: int) -> np.ndarray:
    return cv2.resize(canvas, (width_px, width_px * mtl.H // mtl.W), interpolation=cv2.INTER_AREA)


def ribbon_curve_px(s: int) -> np.ndarray:
    """The generator's own polyline, in supersampled px: 200 points along an
    S through the frame, coordinates truncated to integers as `cv2.polylines`
    received them. Replicated from `make_test_logo.main`; the 800 rung is
    pinned byte-identical to the committed fixture."""
    return np.array(
        [[int((60 + t / 199 * 680) * s),
          int((250 + 120 * math.sin(t / 199 * math.pi * 1.6)) * s)]
         for t in range(200)], np.int32)


def ribbon_thickness_px(s: int) -> int:
    return int(2.2 * s * mtl.W / 80)


def render(fixture: str, width_px: int) -> np.ndarray:
    """`logo_whitebg` or `ribbon_curve` drawn at `width_px`, BGR."""
    s = scale_for(width_px)
    with _supersample(s):
        canvas = np.full((mtl.H * s, mtl.W * s, 3), 255, np.uint8)
        if fixture == "whitebg":
            mtl.draw_art(canvas)
            mtl.punch_hole(canvas, mtl.WHITE)
        elif fixture == "ribbon":
            cv2.polylines(canvas, [ribbon_curve_px(s)], False, mtl.RED, ribbon_thickness_px(s))
        else:
            raise ValueError(f"unknown fixture {fixture!r}; one of {FIXTURES}")
    return _down(canvas, width_px)


# --- the truth, in supersampled px, edge coordinates ------------------------

def _disc(cx: float, cy: float, r: float, s: int) -> Polygon:
    return Point(cx * s + PIXEL_HALF, cy * s + PIXEL_HALF).buffer(r * s + PIXEL_HALF, quad_segs=256)


def _rect(x0: int, y0: int, x1: int, y1: int, s: int, right_inclusive: bool = True) -> Polygon:
    """`cv2.rectangle` fills both corners: (x0, y0)-(x1, y1) covers
    [x0, x1 + 1) x [y0, y1 + 1) in edge coordinates."""
    return box(x0 * s, y0 * s, x1 * s + (1 if right_inclusive else 0), y1 * s + 1)


def truth(fixture: str, s: int) -> dict[str, dict]:
    """name -> {geom, exclude}: the analytic shapes `make_test_logo` drew, in
    supersampled px. `exclude` is [(Point, radius)] of boundary the measure
    must skip (the ribbon's round caps)."""
    if fixture == "whitebg":
        disc = _disc(200, 250, 120, s)
        teal = _rect(315, 245, 325, 255, s)              # absorbed into the circle by stage 3
        ring = _disc(450, 250, 110, s).difference(_disc(450, 250, 60, s))
        return {
            "circle": {"geom": disc.union(teal), "exclude": []},
            "ring": {"geom": ring, "exclude": []},
            "bar": {"geom": _rect(560, 120, 750, 139, s), "exclude": []},
            # orange is drawn after purple and overwrites the shared column x = 650
            "purple": {"geom": _rect(560, 300, 650, 380, s, right_inclusive=False), "exclude": []},
            "orange": {"geom": _rect(650, 300, 740, 380, s), "exclude": []},
            "dot": {"geom": _disc(700, 180, 5, s), "exclude": []},
        }
    if fixture == "ribbon":
        curve = ribbon_curve_px(s).astype(float) + PIXEL_HALF
        half = ribbon_thickness_px(s) / 2.0 + PIXEL_HALF
        body = LineString(curve).buffer(half, quad_segs=64)     # round caps, as cv2 draws them
        ends = [(Point(*curve[0]), 2.0 * half), (Point(*curve[-1]), 2.0 * half)]
        return {"ribbon": {"geom": body, "exclude": ends}}
    raise ValueError(f"unknown fixture {fixture!r}")


# --- the measure ------------------------------------------------------------

def region_to_px(poly: Polygon, cx: float, cy: float, px_per_mm: float) -> Polygon:
    """Plan millimetres -> prepped-raster EDGE coordinates: invert stage 4's
    `_to_mm` (px_index = mm * px_per_mm + centre) and move from the pixel
    index to the pixel centre."""
    return affinity.affine_transform(poly, [px_per_mm, 0.0, 0.0, px_per_mm,
                                            cx + PIXEL_HALF, cy + PIXEL_HALF])


def deviation(poly: Polygon, target: Polygon, step_px: float = SAMPLE_STEP_PX,
              exclude=()) -> np.ndarray:
    """Signed distance, in the polygons' units, from samples along every ring
    of `poly` (shell and holes) to `target`'s boundary: - where the sample
    lies inside the target's material, + where it lies outside. The one rule
    serves both ring kinds: a shell inside the material is a deficit, and so
    is a hole ring inside the material (the hole is too big); a hole ring
    out in the target's hole is an excess (the hole is too small), as a
    shell out past the edge is. A first draft read holes the other way and
    a synthetic square-with-a-hole caught it; the test keeps it caught."""
    boundary = target.boundary
    out = []
    for ring in [poly.exterior, *poly.interiors]:
        n = max(8, int(math.ceil(ring.length / step_px)))
        for i in range(n):
            pt = ring.interpolate(i / n, normalized=True)
            if any(pt.distance(e) < r for e, r in exclude):
                continue
            d = boundary.distance(pt)
            out.append(-d if target.contains(pt) else d)
    return np.asarray(out, float)


def roughness(poly: Polygon) -> float | None:
    """`curve_fidelity.measure` on the polygon's rings as open polylines
    (the closing vertex repeated, so the wrap turn is read too)."""
    rings = []
    for ring in [poly.exterior, *poly.interiors]:
        pts = np.asarray(ring.coords, float)
        rings.append(np.vstack([pts[:-1], pts[:2]]))
    m = cf.measure(rings)
    return None if m.get("refusal") else float(m["roughness_deg"])


def _largest_polygon(geom) -> Polygon:
    if geom.geom_type == "Polygon":
        return geom
    return max(geom.geoms, key=lambda g: g.area)


def measure_rung(fixture: str, width_px: int, forced_class: str | None = "flat",
                 workdir: Path | None = None, flag: str | None = None) -> dict:
    """One rung: draw, run stages 0-4, measure every truth shape. `flag` is
    a `PipelineConfig` field to turn on, NAME or NAME=VALUE (`parse_flag`)."""
    s = scale_for(width_px)
    workdir = workdir or Path(tempfile.mkdtemp(prefix="edge_ladder_"))
    path = workdir / f"{fixture}_{width_px}.png"
    cv2.imwrite(str(path), render(fixture, width_px))
    extra = dict([parse_flag(flag)]) if flag else {}
    cfg = PipelineConfig(target_width_mm=TARGET_MM, forced_class=forced_class, **extra)
    gen = build_generation(str(path), cfg)
    p = gen.p
    upscale = p.px_per_mm / p.input_px_per_mm if p.input_px_per_mm else 1.0
    to_prepped = upscale / SUPER                       # supersampled px -> prepped px
    cx, cy, ppm = _plan_frame(p)
    polys = [(r, region_to_px(_largest_polygon(r.polygon), cx, cy, ppm)) for r in gen.regions]
    rows = []
    for name, t in truth(fixture, s).items():
        target = affinity.scale(t["geom"], to_prepped, to_prepped, origin=(0, 0))
        exclude = [(affinity.scale(e, to_prepped, to_prepped, origin=(0, 0)), r * to_prepped)
                   for e, r in t["exclude"]]
        best, best_iou = None, 0.0
        for r, poly in polys:
            inter = poly.intersection(target).area
            iou = inter / (poly.area + target.area - inter) if inter > 0 else 0.0
            if iou > best_iou:
                best, best_iou = (r, poly), iou
        row = {"shape": name, "truth_area_mm2": round(target.area / ppm ** 2, 3)}
        if best is None or best_iou < MATCH_IOU_MIN:
            rows.append({**row, "produced": False, "iou": round(best_iou, 3)})
            continue
        r, poly = best
        d = deviation(poly, target, exclude=exclude) / ppm
        rows.append({
            **row, "produced": True, "shape_id": r.shape_id, "iou": round(best_iou, 4),
            "vertices": len(poly.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in poly.interiors),
            "samples": int(d.size),
            "offset_mm": round(float(d.mean()), 4),
            "spread_mm": round(float(d.std()), 4),
            "rms_mm": round(float(np.sqrt((d ** 2).mean())), 4),
            "hausdorff_mm": round(float(np.abs(d).max()), 4),
            "roughness_deg": roughness(poly),
        })
    return {"fixture": fixture, "width_px": width_px, "supersample": s, "flag": flag,
            "input_px_per_mm": round(p.input_px_per_mm, 3), "px_per_mm": round(p.px_per_mm, 3),
            "upscale": round(upscale, 3), "design_class": gen.classification_class,
            "regions": len(gen.regions), "rows": rows}


# --- the tier diff, from one command -----------------------------------------

def tiers(cases: list[str], flag: str | None, show_all: bool = False) -> None:
    import curve_tiers as ct
    from digitizer_core import digitize

    name, value = parse_flag(flag) if flag else (None, None)
    for case in cases or list(ct.CASES):
        rel, kw = ct.CASES.get(case, (case, {}))
        rows = {}
        for tag in (("off", "on") if name else ("off",)):
            cfg = dict(target_width_mm=TARGET_MM)
            cfg.update(kw)
            if tag == "on":
                cfg[name] = value
            result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
            m = cf.measure([pts for _k, _s, pts in cf.traces(plan)])
            rows[tag] = (ct.shapes(result, plan), plan.stats.stitch_count, plan.stats.trims,
                         m.get("roughness_deg", float("nan")))
        off = rows["off"][0]
        if not name:
            counts = {}
            for tier, *_rest in off.values():
                counts[tier] = counts.get(tier, 0) + 1
            print(f"## {case}  st {rows['off'][1]}  trims {rows['off'][2]}  "
                  f"verts {sum(v[2] for v in off.values())}  roughness {rows['off'][3]:.2f}  "
                  f"tiers " + " ".join(f"{t}:{n}" for t, n in sorted(counts.items())))
            if show_all:
                for sid, (tier, pen, verts, (x, y), area) in sorted(off.items()):
                    print(f"  {sid:24s} {tier:>7} pen {pen:5d} verts {verts:4d} area {area:6.1f} at ({x:.1f},{y:.1f})")
            continue
        on = rows["on"][0]
        counts = {t: (sum(1 for v in off.values() if v[0] == t), sum(1 for v in on.values() if v[0] == t))
                  for t in ("satin", "fill", "run", "other", "dropped")}
        print(f"## {case}  {name}={value!r}  st {rows['off'][1]} -> {rows['on'][1]}  "
              f"trims {rows['off'][2]} -> {rows['on'][2]}  "
              f"verts {sum(v[2] for v in off.values())} -> {sum(v[2] for v in on.values())}  "
              f"roughness {rows['off'][3]:.2f} -> {rows['on'][3]:.2f}  "
              f"tiers " + " ".join(f"{t}:{a}->{b}" for t, (a, b) in counts.items() if a or b))
        moved = 0
        absent = ("absent", 0, 0, (0.0, 0.0), 0.0)
        for sid, oid in sorted(ct.pair(off, on), key=lambda t: t[0] or t[1]):
            a, b = off.get(sid, absent), on.get(oid, absent)
            changed = "TIER" if a[0] != b[0] else ("" if a[1] == b[1] else "pen")
            if changed == "TIER" or show_all:
                moved += changed == "TIER"
                label = sid if sid == oid else f"{sid} -> {oid}"
                print(f"  {label:24s} {a[0]:>7} -> {b[0]:<7} pen {a[1]:5d} -> {b[1]:<5d} "
                      f"verts {a[2]:4d} -> {b[2]:<4d} area {a[4]:6.1f} -> {b[4]:<6.1f} {changed}")
        if not moved and not show_all:
            print("  (no tier change on any shape)")


# --- CLI --------------------------------------------------------------------

def _fmt(v, width: int = 7, digits: int = 3) -> str:
    return f"{'n/a':>{width}}" if v is None else f"{v:{width}.{digits}f}"


def _print_rung(r: dict) -> None:
    print(f"  {r['width_px']:5d} px  input {r['input_px_per_mm']:6.2f} px/mm  prepped {r['px_per_mm']:6.2f} "
          f"(x{r['upscale']:.2f})  {r['design_class']:8}  regions {r['regions']:3d}")
    for row in r["rows"]:
        if not row["produced"]:
            print(f"      {row['shape']:8} not produced (best iou {row['iou']:.2f}, "
                  f"truth {row['truth_area_mm2']:.2f} mm2)")
            continue
        print(f"      {row['shape']:8} verts {row['vertices']:4d}  offset {_fmt(row['offset_mm'])}  "
              f"spread {_fmt(row['spread_mm'])}  rms {_fmt(row['rms_mm'])}  "
              f"hausdorff {_fmt(row['hausdorff_mm'])}  roughness {_fmt(row['roughness_deg'], 6, 2)} deg  "
              f"iou {row['iou']:.3f}")


def _print_matrix(results: list[dict], key: str) -> None:
    """`key` by rung, one line per shape — the ladder itself."""
    rungs = sorted({r["width_px"] for r in results})
    shapes = []
    for r in results:
        for row in r["rows"]:
            if row["shape"] not in shapes:
                shapes.append(row["shape"])
    print(f"    {key:>12}  " + "  ".join(f"{w:>7d}" for w in rungs))
    for shape in shapes:
        cells = []
        for w in rungs:
            row = next((x for r in results if r["width_px"] == w for x in r["rows"] if x["shape"] == shape), None)
            cells.append(_fmt(row.get(key) if row and row["produced"] else None))
        print(f"    {shape:>12}  " + "  ".join(cells))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help=f"any of {FIXTURES} (ladder) or curve_tiers cases (--tiers)")
    ap.add_argument("--rungs", type=int, nargs="+", default=list(RUNGS))
    ap.add_argument("--routed", action="store_true", help="let stage 0 route instead of forcing the flat lane")
    ap.add_argument("--tiers", action="store_true", help="per-shape tier diff on the real fixtures")
    ap.add_argument("--flag", default=None,
                    help="PipelineConfig field to turn on for the ladder or the tier diff, NAME or NAME=VALUE")
    ap.add_argument("--all", action="store_true", help="--tiers: print every shape")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.tiers:
        try:
            tiers(a.fixtures, a.flag, a.all)
        except ValueError as e:          # an unknown --flag: a message, not a traceback
            ap.error(str(e))
        return 0
    fixtures = a.fixtures or list(FIXTURES)
    forced = None if a.routed else "flat"
    workdir = Path(tempfile.mkdtemp(prefix="edge_ladder_"))
    if a.flag:
        try:
            parse_flag(a.flag)
        except ValueError as e:
            ap.error(str(e))
    print(f"edge truth ladder — {TARGET_MM:g} mm, {'routed' if a.routed else 'flat lane forced'}, "
          f"samples every {SAMPLE_STEP_PX} px, truth matched at iou >= {MATCH_IOU_MIN}"
          + (f", {a.flag} ON" if a.flag else ""))
    results = []
    for fixture in fixtures:
        print(f"== {fixture}")
        per = []
        for w in a.rungs:
            r = measure_rung(fixture, w, forced, workdir, a.flag)
            _print_rung(r)
            per.append(r)
        for key in ("spread_mm", "offset_mm", "hausdorff_mm"):
            _print_matrix(per, key)
        results.extend(per)
    if a.json:
        print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
