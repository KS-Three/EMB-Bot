#!/usr/bin/env python
"""Every EXPOSED fill-phase bridge, one row each, with what would have fixed it.

Quality review 2026-09-08 item 12. `tools/fill_exposure.py` already reports the
TOTAL — Becker 55.8 mm of 148, Bridge Bar 75.8 of 194, Fremont 59.6 of 185 —
and the review's own words about the third that is left are *"the cause is not
established"*. A total cannot establish a cause: it cannot say whether the
remaining runs are one pathological shape or fifty unavoidable millimetres, and
it cannot say which of the three proposed remedies would touch them.

So this walks the same plan and, for each bridge that still lies over finished
fill, re-asks `stage6_fill.travel_path` the SAME question under relaxed
conditions, and records which relaxation (if any) produces a clean route:

  budget   the detour cap (`_TRAVEL_DETOUR_FACTOR` 4x / `_TRAVEL_DETOUR_FLOOR_MM`
           20 mm) refused a clean route that exists. A tunable.
  probes   the ring-candidate cap (`_TRAVEL_RING_CANDIDATES` = 3) stopped
           before reaching a clean ring. A work cap, not a quality knob —
           raising it can only cost time.
  neither  no clean route exists at any budget over any ring. The shape is
           sewn through; the thread has to cross itself or be lifted.

and three facts that decide what to do about the `neither` rows:

  covered  how much of the bridge lies under a LATER colour's artwork
           (stage 5's `covered_by`). Thread that a later cone buries is not
           exposed to anyone, whatever the footprint arithmetic says.
  gap      the straight-line distance between the two ends — what a JUMP
           would cost. Under `trim_at` the machine lifts without cutting, so
           the review's third remedy is free of a trim exactly there.
  unsewn   how much of the shape was still unsewn at that moment. Near zero
           means this is the last bridge of a shape that is simply finished,
           and no routing rule can help it.
  corridor whether the two ends lie in the SAME connected piece of that
           unsewn ground. This is the question that separates a router
           limitation from a physical one: with no corridor, no rule about
           WHERE to route can help, because there is nowhere to route
           through — only the column ORDER could have avoided it.

    .venv/bin/python tools/fill_bridges.py [fixture ...] [--rows] [--width MM]

`--rows` prints every bridge; the default prints the per-fixture summary and
the worst five. Fixture names are `fill_exposure.SHORT`'s, so the two
instruments always read the same designs the same way.

## What it found, and the two fixes it killed (2026-09-11, 9 fixtures)

92 exposed bridges, 912.6 mm: **88% (801 mm) have no corridor**, 6% (55 mm)
have one the router cannot use, 4% (36 mm) are the `budget` bucket, and 2%
(20 mm) are already buried. The review proposed three remedies and this
prices all three OUT:

  * *route under the covering colour* reaches the 2%. `covered_by` simply
    does not overlap these bridges.
  * *lift when shorter than `trim_at`* reaches 8 bridges / 26 mm corpus-wide
    at pique knit's 3.0 mm, and NONE on Becker, Fremont, Bridge Bar or drone.
  * *route along the shape's edge run* is what the ring route already is.
    Raising its detour budget was built and measured: a **perfect no-op on
    all nine fixtures**. The `budget` bucket above does not survive contact
    with the real engine — see `_clean_under`'s note on the start point.

A fourth idea, not in the review, was built and measured too and is WORSE:
preferring a next column that still shares unsewn ground (a second greedy
tier in `_reorder_for_cover`) raises exposure on six of nine fixtures —
`logo_gaulke_roofing` 3.1 -> 84.0 mm, Hotel Fremont 23.9 -> 99.9 — because
it finds orders with fewer CUTS and `_score` buys those at 25 stitches a
trim against 2 an exposed stitch. Adding a per-shape ratchet (never keep an
order that scores more exposed) did not stop it, which is its own finding:
`_order_cost` and `emit` can disagree, because `emit` keeps a `route_cache`
across a shape's bridges and the scorer builds a fresh one. Both arms were
reverted; DOCTRINE carries the verdict.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString, Point  # noqa: E402

from digitizer_core import PipelineConfig, digitize, machine  # noqa: E402
from digitizer_core import stage6_fill  # noqa: E402
from digitizer_core.pipeline import fabric_for  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from digitizer_core.stage6_fill import (  # noqa: E402
    _EXPOSED_TOLERANCE_MM, _inset_ring, travel_path,
)

from fill_exposure import SHORT  # noqa: E402


def _exposed(points, sewn) -> float:
    if sewn is None or sewn.is_empty or len(points) < 2:
        return 0.0
    return float(LineString(points).intersection(sewn).length)


def _clean_under(poly, ring, a, b, slack, sewn, *, factor, floor, probes,
                 want_length: bool = False):
    """Would `travel_path` find an unexposed route with these caps raised?

    The constants are module-level in `stage6_fill` and read at call time, so
    an instrument can lift them for one question and put them back. Nothing
    here writes to the engine's behaviour outside this function.
    """
    keep = (stage6_fill._TRAVEL_DETOUR_FACTOR,
            stage6_fill._TRAVEL_DETOUR_FLOOR_MM,
            stage6_fill._TRAVEL_RING_CANDIDATES)
    stage6_fill._TRAVEL_DETOUR_FACTOR = factor
    stage6_fill._TRAVEL_DETOUR_FLOOR_MM = floor
    stage6_fill._TRAVEL_RING_CANDIDATES = probes
    try:
        route = travel_path(poly, ring, a, b, slack, sewn, {})
    finally:
        (stage6_fill._TRAVEL_DETOUR_FACTOR,
         stage6_fill._TRAVEL_DETOUR_FLOOR_MM,
         stage6_fill._TRAVEL_RING_CANDIDATES) = keep
    if route is None:              # a lift, which is not exposed at all
        return 0.0 if want_length else True
    # `travel_path` returns its route with the START EXCLUDED (`_densify` is
    # a-exclusive), and the first step is exactly the part lying inside the
    # column just finished. Measuring without it made every short bridge read
    # clean and reported a budget fix that does not exist — found 2026-09-11
    # by a 0.5x detour ratio, which is geometrically impossible for a route
    # between the same two points. `travel_path` scores `[a] + pts + [b]`
    # internally; this has to do the same.
    full = [a] + list(route)
    clean = _exposed(full, sewn) <= _EXPOSED_TOLERANCE_MM
    if not want_length:
        return clean
    if not clean or len(full) < 2:
        return None
    return float(LineString(full).length)


def bridges(result, plan, cfg) -> list[dict]:
    """One dict per exposed fill-phase travel run, in sew order."""
    row = machine.FILL_ROW_MM
    fabric = fabric_for(cfg)
    trim_at = fabric.trim_at_mm          # stage 7's own source for this number
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    planned, _w = resolve_overlaps(stitched, fabric, cfg,
                                   design_class=result.design_class)
    by_id = {p.shape_id: p for p in planned}

    sewn: dict = {}
    geom: dict = {}
    out: list[dict] = []
    for block, run in plan.iter_runs():
        sid = run.shape_id
        if run.kind == "fill":
            if len(run.points) > 1:
                fp = LineString(run.points).simplify(row / 2.0).buffer(row)
                sewn[sid] = fp if sid not in sewn else sewn[sid].union(fp)
            continue
        if run.kind != "travel" or sid not in sewn or len(run.points) < 2:
            continue
        over = _exposed(run.points, sewn[sid])
        if over <= _EXPOSED_TOLERANCE_MM:
            continue
        p = by_id.get(sid)
        if p is None:                       # a tier that plans its own shapes
            continue
        if sid not in geom:
            poly = p.polygon
            geom[sid] = (poly, _inset_ring(poly, machine.TRAVEL_INSET_MM),
                         poly.buffer(0.01))
        poly, ring, slack = geom[sid]
        a, b = run.points[0], run.points[-1]
        line = LineString(run.points)
        cov = p.covered_by
        under = float(line.intersection(cov).length) if cov is not None else 0.0
        unsewn = slack.difference(sewn[sid])
        # A corridor is unsewn ground touching BOTH ends. `a` is the last
        # penetration of the column just sewn, so it sits inside `sewn` by
        # construction — hence the one-travel-stitch allowance, the same one
        # `travel_path` gives itself.
        tol = _EXPOSED_TOLERANCE_MM
        parts = list(getattr(unsewn, "geoms", [unsewn]))
        touch_a = {i for i, g in enumerate(parts) if g.intersects(Point(a).buffer(tol))}
        touch_b = {i for i, g in enumerate(parts) if g.intersects(Point(b).buffer(tol))}
        out.append(dict(
            corridor=bool(touch_a & touch_b),
            shape=sid,
            thread=block.thread_index,
            len_mm=run.length_mm,
            exposed_mm=over,
            gap_mm=float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5),
            covered_mm=under,
            unsewn_mm2=float(unsewn.area),
            jumpable=float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5) <= trim_at,
            fixed_by_budget=_clean_under(poly, ring, a, b, slack, sewn[sid],
                                         factor=1e6, floor=1e6, probes=3),
            fixed_by_probes=_clean_under(poly, ring, a, b, slack, sewn[sid],
                                         factor=4.0, floor=20.0, probes=50),
            fixed_by_both=_clean_under(poly, ring, a, b, slack, sewn[sid],
                                       factor=1e6, floor=1e6, probes=50),
            # For the `budget` rows: how long the clean route the budget
            # refused actually is. The cap is 4x the straight distance or
            # 20 mm, so this says what factor would have been needed — and
            # whether it is a detour or a lap of the shape.
            clean_mm=_clean_under(poly, ring, a, b, slack, sewn[sid],
                                  factor=1e6, floor=1e6, probes=3,
                                  want_length=True),
        ))
    return out


def _cause(b: dict) -> str:
    if b["covered_mm"] >= b["exposed_mm"] - _EXPOSED_TOLERANCE_MM:
        return "buried"                     # a later cone covers it anyway
    if b["fixed_by_budget"]:
        return "budget"
    if b["fixed_by_probes"]:
        return "probes"
    if b["fixed_by_both"]:
        return "both"
    return "no-corridor" if not b["corridor"] else "router"


def report(name: str, rows: list[dict], *, show_rows: bool) -> None:
    total = sum(r["exposed_mm"] for r in rows)
    print(f"\n{name}: {len(rows)} exposed bridges, {total:.1f} mm exposed")
    if not rows:
        return
    buckets: dict = {}
    for r in rows:
        c = _cause(r)
        n, mm = buckets.get(c, (0, 0.0))
        buckets[c] = (n + 1, mm + r["exposed_mm"])
    for c in ("buried", "budget", "probes", "both", "router", "no-corridor"):
        if c in buckets:
            n, mm = buckets[c]
            print(f"    {c:8s} {n:3d} bridges {mm:7.1f} mm  ({100 * mm / total:4.0f}% of exposed)")
    budgeted = [r for r in rows if _cause(r) == "budget" and r.get("clean_mm")]
    if budgeted:
        need = sorted(r["clean_mm"] / max(r["gap_mm"], 1e-9) for r in budgeted)
        print(f"    the budget rows need a detour of {need[0]:.1f}x to {need[-1]:.1f}x "
              f"the straight gap (median {need[len(need) // 2]:.1f}x); the cap is 4x or 20 mm")
    jump = [r for r in rows if _cause(r) in ("router", "no-corridor") and r["jumpable"]]
    print(f"    of the unfixable: {len(jump)} are shorter than trim_at "
          f"({sum(r['exposed_mm'] for r in jump):.1f} mm) so a lift costs no trim")
    worst = sorted(rows, key=lambda r: -r["exposed_mm"])
    for r in (rows if show_rows else worst[:5]):
        print(f"      {r['shape']:>14s} th{r['thread']:<3d} len={r['len_mm']:6.1f} "
              f"exposed={r['exposed_mm']:6.1f} gap={r['gap_mm']:5.1f} "
              f"covered={r['covered_mm']:5.1f} unsewn={r['unsewn_mm2']:7.1f}mm2 "
              f"{_cause(r)}")


def main(argv: list[str]) -> None:
    show_rows = "--rows" in argv
    width = 80.0
    if "--width" in argv:
        width = float(argv[argv.index("--width") + 1])
    names = [a for a in argv if not a.startswith("--")
             and not a.replace(".", "").isdigit()] or list(SHORT)
    for name in names:
        rel, kw = SHORT.get(name, (name, {}))
        cfg = PipelineConfig(target_width_mm=width, **kw)
        t0 = time.time()
        result, plan = digitize(ROOT / "testdata" / rel, cfg)
        rows = bridges(result, plan, cfg)
        print(f"--- {name} ({rel}, {width:.0f} mm, {time.time() - t0:.1f}s) ---", end="")
        report(name, rows, show_rows=show_rows)


if __name__ == "__main__":
    main(sys.argv[1:])
