#!/usr/bin/env python
"""Is a design's bare satin artwork a HOLE, or a field of hairlines?

`tools/rail_edge.py --bare` answers "how much of the satin artwork carries no
thread" with one number. That number cannot tell a 0.5 mm2 gap at a junction —
which shows on cloth — from three hundred 0.03 mm2 slivers between adjacent
threads, which is the hard-edged coverage model meeting a rail that advanced
0.05 mm further than its neighbour. **Both move the same headline, and they
want opposite responses.** This splits it.

Two axes, both read off the same geometry `bare_area` uses (each satin cross
buffered to `machine.COVERAGE_THREAD_W_MM`, unioned per shape, subtracted from
the shape's artwork polygon), so a total printed here reconciles with that
tool's percentage:

- **WHERE** — a component touching a disc at a run's first or last cross is an
  `end` gap (a cap that did not reach, a stroke that stopped short); anything
  else is a `side` gap, along the rails.
- **HOW THICK** — each component's maximum inscribed radius, by bisection on a
  negative buffer. A hairline between two 0.4 mm threads whose penetrations sat
  0.05 mm apart reads ~0.02 mm; a real hole reads a tenth of a millimetre and
  up. The thickness is what separates the two populations, and the area alone
  never does: 311 slivers and one hole can total the same square millimetres.

## IT COUNTS SATIN CROSSES AND NOTHING ELSE, so it OVER-REPORTS

The subtraction above is satin only. Underlay, run, travel and fill lay real
thread on the same cloth and none of it is subtracted, so every number here is
an upper bound on what a customer could see. **Measured 2026-09-30 on
ENTHUSIAST's worst component, the A's apex: 3.61 mm2 satin-only, 2.17 mm2
against EVERY thread kind** -- underlay covers 38.4% of it and travel 4.7%, so
the default reading is 1.66x the hole. That is 40% on the one component this
tool was built to explain, which is large enough to change a build decision.

`--all-thread` subtracts every run the plan emits and is the number to quote
when the claim is *"a customer would see this"*. The default stays satin-only
because the end/side split, the thickness populations and every figure pinned
against this tool were measured that way, and because satin-only is the right
reading for *"did the COLUMN cover its own artwork"* -- underlay filling a gap
is thread on cloth, not a satin column doing its job.

Written 2026-09-29 for Kent's pick on `satin_rail_comp`'s two unexplained
costs. The ENTHUSIAST half of that question — "mid-rail bare 2.06 -> 4.12%,
cause not yet isolated" (`docs/kent-review-2026-09-28.md`) — is answered by
the thickness column and by nothing else on any instrument in this repo: the
flip trades a THICK tail for MORE THIN slivers, so the headline rises while
the worst gap on the fixture gets smaller. Read `p90 thick` and `worst`
before reading `total`.

    .venv/bin/python tools/bare_anatomy.py enthusiast
    .venv/bin/python tools/bare_anatomy.py --corpus > anatomy.txt
    .venv/bin/python tools/bare_anatomy.py becker --arms off     # one arm only
    .venv/bin/python tools/bare_anatomy.py enthusiast --all-thread  # vs ALL thread

Arms are `satin_rail_comp` OFF and ON; the default runs both and prints the
pair. Cases are `tools.thin_strokes.REAL_ART` names, at each fixture's own
census width and garment.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from shapely.geometry import LineString  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig, machine  # noqa: E402
from digitizer_core.pipeline import (build_generation, finish_generation,  # noqa: E402
                                     plan_stitches)
from digitizer_core.stage6_satin import strip_splits  # noqa: E402
from digitizer_core.stitches import strip_ties  # noqa: E402

from tools._console import utf8_console  # noqa: E402
from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

# A component this thin is the coverage model's own edge, not a gap anyone
# sees: two 0.4 mm threads whose penetrations sat a rail-step apart leave a
# wedge of about this half-width. Used only to SPLIT the report — no engine
# code reads it, and no claim here rests on the exact value.
HAIRLINE_HALF_MM = 0.10
# Above this a component is thick enough to be worth looking at on a render.
THICK_HALF_MM = 0.20


def _max_inscribed_half(geom, hi: float = 2.0, steps: int = 18) -> float:
    """-> the largest r with a disc of radius r inside `geom`, by bisection.

    Shapely's own `maximum_inscribed_circle` is 2.1+; this is the same answer
    to 2 um over the range that matters here and runs on any version the repo
    pins. `hi` bounds the search: a satin gap wider than 2 mm half-width is a
    missing column, and reads as 2.0 either way.
    """
    lo = 0.0
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        if geom.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return lo


def other_thread(plan, exclude: str = "satin"):
    """-> every non-satin run the plan emits, buffered to a thread width.

    Underlay, run, travel and fill are thread on the same cloth. `components`
    ignores them by default (see the module docstring); this is what
    `all_thread=True` subtracts as well.

    ANOTHER shape's satin is deliberately not included: the question stays
    per-shape, and a shape buried under its neighbour's column should still
    read as unsewn. On ENTHUSIAST it makes no difference either way — the A's
    apex reads 1.932 mm2 with the other 978 satin segments in and out
    (measured 2026-09-30) — but on overlapping art it would.
    """
    thread = machine.COVERAGE_THREAD_W_MM
    segs = []
    for _b, r in plan.iter_runs():
        if r.kind == exclude:
            continue
        pts = strip_splits(strip_ties(list(r.points)))
        segs += [LineString([pts[i], pts[i + 1]]) for i in range(len(pts) - 1)
                 if math.dist(pts[i], pts[i + 1]) > 1e-6]
    if not segs:
        return None
    return unary_union([s.buffer(thread / 2.0, cap_style=2) for s in segs])


def components(polys: dict, plan, all_thread: bool = False,
               ) -> list[tuple[float, float, bool, str]]:
    """-> [(area_mm2, half_thickness_mm, is_end_gap, shape_id)] for every bare
    component of every satin shape.

    Crosses are grouped BY RUN so a run's first and last cross are knowable —
    that is what makes the end/side split possible, and it is the one thing
    `rail_edge.bare_area` throws away by unioning per shape.

    `all_thread` also subtracts underlay, run, travel and fill. The default is
    False and the module docstring says why, and by how much it over-reports.
    """
    thread = machine.COVERAGE_THREAD_W_MM
    other = other_thread(plan) if all_thread else None
    runs: dict[str, list[list]] = {}
    for _b, r in plan.iter_runs():
        if r.kind != "satin" or r.shape_id not in polys:
            continue
        pts = strip_splits(strip_ties(list(r.points)))
        cr = [LineString([pts[i], pts[i + 1]]) for i in range(0, len(pts) - 1, 2)
              if math.dist(pts[i], pts[i + 1]) > 1e-6]
        if cr:
            runs.setdefault(r.shape_id, []).append(cr)

    out: list[tuple[float, float, bool, str]] = []
    for sid, groups in runs.items():
        crosses = [c for grp in groups for c in grp]
        sewn = unary_union([c.buffer(thread / 2.0, cap_style=2) for c in crosses])
        if other is not None:
            sewn = sewn.union(other)
        bare = polys[sid].difference(sewn)
        if bare.is_empty:
            continue
        # The end zone is a disc at each run's terminal cross, sized to that
        # cross: a cap gap is at most a half-column across, and a fixed radius
        # would call a wide column's cap gap a side gap and a narrow one's
        # side gap an end gap.
        discs = [c.centroid.buffer(max(c.length / 2.0, thread))
                 for grp in groups for c in (grp[0], grp[-1])]
        ends = unary_union(discs) if discs else None
        for part in getattr(bare, "geoms", [bare]):
            if part.area <= 0:
                continue
            is_end = ends is not None and part.intersects(ends)
            out.append((part.area, _max_inscribed_half(part), is_end, sid))
    return out


def measure(name: str, rail_comp: bool) -> dict:
    rel, width_mm, garment = REAL_ART[name]
    return measure_path(ROOT / "testdata" / rel, width_mm, garment, rail_comp, name)


def measure_path(path, width_mm: float, garment: str, rail_comp: bool,
                 name: str = "", render_to: Path | None = None,
                 only: set | None = None, all_thread: bool = False) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS, satin_rail_comp=rail_comp)
    gen = build_generation(str(path), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    polys = {r.shape_id: r.polygon for r in result.regions}
    comps = components(polys, plan, all_thread=all_thread)
    if render_to is not None:
        render(polys, plan, render_to, f"{name or 'case'}_{'on' if rail_comp else 'off'}", only)
    satin_art = sum(polys[sid].area for sid in
                    {c[3] for c in comps} | _satin_ids(plan, polys))
    return dict(name=name, on=rail_comp, comps=comps, art=satin_art,
                st=plan.stats.stitch_count, trims=plan.stats.trims,
                all_thread=all_thread)


def _satin_ids(plan, polys) -> set:
    return {r.shape_id for _b, r in plan.iter_runs()
            if r.kind == "satin" and r.shape_id in polys}


def report(d: dict) -> str:
    comps = d["comps"]
    arm = ("ON " if d["on"] else "OFF") + ("*" if d.get("all_thread") else " ")
    if not comps:
        return f"  {arm} no bare satin artwork"
    area = np.asarray([c[0] for c in comps])
    half = np.asarray([c[1] for c in comps])
    side = np.asarray([not c[2] for c in comps])
    tot = area.sum()
    lines = [
        f"  {arm} st={d['st']:>6d} trims={d['trims']:>3d}  "
        f"bare={tot:7.2f} mm2 of {d['art']:8.1f} ({100 * tot / max(d['art'], 1e-9):.2f}%)  "
        f"n={len(comps)}",
        f"      ends {area[~side].sum():6.2f} mm2 (n={int((~side).sum()):>4d})   "
        f"sides {area[side].sum():6.2f} mm2 (n={int(side.sum()):>4d})",
        f"      half-thickness p50={np.median(half):.3f} p90={np.percentile(half, 90):.3f} "
        f"max={half.max():.3f} mm   "
        f"area under {HAIRLINE_HALF_MM:.2f} mm: {100 * area[half < HAIRLINE_HALF_MM].sum() / tot:.0f}%   "
        f"over {THICK_HALF_MM:.2f} mm: {100 * area[half > THICK_HALF_MM].sum() / tot:.0f}%",
    ]
    worst = sorted(comps, reverse=True)[:4]
    lines.append("      worst: " + "  ".join(
        f"{a:.2f}mm2 @{h:.2f}mm {'end' if e else 'side'} {s}" for a, h, e, s in worst))
    return "\n".join(lines)


def render(polys: dict, plan, out_dir: Path, tag: str, only: set | None = None,
           px_per_mm: float = 40.0) -> list[Path]:
    """One PNG per satin shape: artwork pale grey, sewn crosses blue, `end`
    gaps amber, `side` gaps red. The split is the report's, drawn -- a claim
    about where thread does not land is a claim about geometry, and this repo
    settles those with a picture (DOCTRINE 2026-09-07)."""
    import cv2  # local: the report itself needs no image stack

    thread = machine.COVERAGE_THREAD_W_MM
    runs: dict[str, list[list]] = {}
    for _b, r in plan.iter_runs():
        if r.kind != "satin" or r.shape_id not in polys:
            continue
        pts = strip_splits(strip_ties(list(r.points)))
        cr = [LineString([pts[i], pts[i + 1]]) for i in range(0, len(pts) - 1, 2)
              if math.dist(pts[i], pts[i + 1]) > 1e-6]
        if cr:
            runs.setdefault(r.shape_id, []).append(cr)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for sid, groups in runs.items():
        if only and sid not in only:
            continue
        poly = polys[sid]
        crosses = [c for grp in groups for c in grp]
        sewn = unary_union([c.buffer(thread / 2.0, cap_style=2) for c in crosses])
        bare = poly.difference(sewn)
        discs = [c.centroid.buffer(max(c.length / 2.0, thread))
                 for grp in groups for c in (grp[0], grp[-1])]
        ends = unary_union(discs) if discs else None

        x0, y0, x1, y1 = poly.bounds
        ox, oy = x0 - 1.0, y0 - 1.0

        def px(geom):
            return [np.array([[(x - ox) * px_per_mm, (y - oy) * px_per_mm]
                              for x, y in ring.coords], dtype=np.int32)
                    for ring in [geom.exterior, *geom.interiors]]

        img = np.full((int((y1 - y0 + 2) * px_per_mm) + 2,
                       int((x1 - x0 + 2) * px_per_mm) + 2, 3), 255, np.uint8)
        rings = px(poly)
        cv2.fillPoly(img, rings[:1], (228, 228, 228))
        for ring in rings[1:]:
            cv2.fillPoly(img, [ring], (255, 255, 255))
        for c in crosses:
            (ax, ay), (bx, by) = list(c.coords)
            cv2.line(img, (int((ax - ox) * px_per_mm), int((ay - oy) * px_per_mm)),
                     (int((bx - ox) * px_per_mm), int((by - oy) * px_per_mm)),
                     (150, 70, 20), max(1, int(thread * px_per_mm)))
        for part in (getattr(bare, "geoms", [bare]) if not bare.is_empty else []):
            if part.area <= 0 or part.geom_type != "Polygon":
                continue
            is_end = ends is not None and part.intersects(ends)
            cv2.fillPoly(img, px(part), (30, 170, 235) if is_end else (40, 40, 230))
        path = out_dir / f"{tag}_{sid}.png"
        cv2.imwrite(str(path), img)
        written.append(path)
    return written


def main(argv: list[str]) -> None:
    utf8_console()
    arms = [False, True]
    all_thread = "--all-thread" in argv
    if all_thread:
        argv = [a for a in argv if a != "--all-thread"]
    out_dir = None
    if "--render" in argv:
        i = argv.index("--render")
        out_dir = Path(argv[i + 1])
        del argv[i:i + 2]
    only = None
    if "--shape" in argv:
        i = argv.index("--shape")
        only = {argv[i + 1]}
        del argv[i:i + 2]
    if "--arms" in argv:
        i = argv.index("--arms")
        arms = [argv[i + 1] == "on"]
        del argv[i:i + 2]
    if "--corpus" in argv:
        cases = [(n, p, w, g) for n, p, w, g in corpus_cases(ROOT)]
    else:
        names = [a for a in argv if not a.startswith("--")] or ["enthusiast"]
        cases = []
        for n in names:
            rel, w, g = REAL_ART[n]
            cases.append((n, ROOT / "testdata" / rel, w, g))
    print(f"thread {machine.COVERAGE_THREAD_W_MM} mm, satin pitch "
          f"{machine.SATIN_SPACING_MM} mm -- adjacent threads just touch at the pitch, "
          f"so every step over it leaves a sliver the model counts as bare.")
    if all_thread:
        print("--all-thread: underlay, run, travel and fill subtracted too "
              "(rows marked *). The default counts SATIN ONLY and over-reports.")
    for name, path, w, g in cases:
        print(f"### {name} {w:g} mm {g}")
        for on in arms:
            d = measure_path(path, w, g, on, name, render_to=out_dir, only=only,
                             all_thread=all_thread)
            print(report(d))


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main(sys.argv[1:])
