"""Is a curve sewn as a curve, or as a polygon? Read from the STITCH PATH.

The second of Kent's two smoothness complaints, and the one
`tools/edge_smoothness.py` could not answer. Reviewing fourteen stitch-outs on
2026-08-27 he raised smoothness on eight of them, and his notes hold two
distinct faults that he confirmed matter about equally:

  * **edge noise** — *"the edges around BECKER... they are jaged"*,
    *"it's sawtoothed and jaged"*. `edge_smoothness.ragged_mm` owns this.
  * **curve fidelity** — *"Lines/circles are not smooth like the photo"*. A
    curve sewn as a polygon. That is this file, and it needed a different
    INPUT, not a different threshold.

## Why this cannot come from a raster — settled, not re-litigated

`edge_smoothness.py`'s docstring records a turning-concentration measure built
and REJECTED on 2026-08-27. The idea was right — a circle spreads its 360
degrees evenly, a 20-gon concentrates them in 20 corners — but measured on a
rasterised mask it is not even monotonic, because a raster boundary is itself a
staircase of 45 and 90 degree steps. Its table, kept here so nobody rebuilds it:

    step mm   circle   60-gon   40-gon   20-gon   12-gon   monotonic?
        0.5    0.320    0.222    0.231    0.414    0.554   no
        1.0    0.314    0.236    0.217    0.296    0.373   no
        2.0    0.211    0.126    0.121    0.154    0.230   no
        3.0    0.177    0.100    0.108    0.100    0.163   no

The rasterised CIRCLE reads more angular than a 40-gon at every step. So the
measure was pointed at `plan.iter_runs()` instead — the vertices the machine
actually sews, floats in mm, no raster, no registration, no alignment quantum.
The same table on the same shapes, from path geometry (`test_curve_fidelity.py`
holds this as an executable test, not a remembered number):

    step mm   circle   60-gon   40-gon   20-gon   12-gon   monotonic?
        0.5   0.0002   0.3612   0.5791   0.7933   0.8786   YES
        1.0   0.0001   0.0015   0.1658   0.5793   0.7566   YES
        2.0   0.0000   0.0015   0.0284   0.1639   0.4936   YES
        3.0   0.0000   0.0015   0.0012   0.0002   0.2353   no

The idea was sound and the raster was the problem. The 3.0 mm row is not a
defect in the measure but its physical floor, and it is printed rather than
trimmed: a 20-gon this size has 3.13 mm edges, so sampling every 3.0 mm lands
about one vertex per edge and every vertex then turns alike — the polygon goes
invisible because the needle is as coarse as it is. Every value in that row
bar the 12-gon is noise on a near-zero. Read this instrument at the stitch
length the design really sews, and never compare arms across different ones.

## Two numbers, because one is not enough

`turn_gini` alone would be a bad instrument, and the reason is worth stating
rather than discovering later. It asks "is the turning spread evenly around
the outline", which conflates polygonisation with a shape that legitimately
mixes straight sides and true arcs. A rounded rectangle — flat sides, exact
quarter-circle corners, nothing wrong with it — reads 0.65, about what a
20-gon reads. Real logos are almost all mixed geometry, so on its own this
number would flag everything.

So the turning sequence is also read LOCALLY. A true curve holds a
near-constant turn per stitch whatever its radius; a polygonised one alternates
flat-flat-flat-CORNER. Measured 2026-08-27 at 0.5 mm sampling:

    shape                    turn_gini   roughness_deg
    circle                      0.0002          0.001
    rounded rect (smooth)       0.6556          0.348     <- gini fooled
    20-gon                      0.7933          4.147
    12-gon                      0.8786          4.008
    square (4 real corners)     refused        refused    <- corners excluded,
                                                             nothing curved left

    turn_gini        how COARSE the polygon is. Monotonic across the n-gon
                     ladder above, so it ranks severity — but a rounded
                     rectangle reads like a 20-gon.
    roughness_deg    whether the path is polygonised AT ALL, in degrees of
                     turn change per vertex. Separates the rounded rect
                     (0.37) from the n-gons (4.2) by an order of magnitude,
                     and refuses a square outright. But it SATURATES and then
                     REVERSES — 40-gon 4.28, 20-gon 4.15, 12-gon 4.01 — so it
                     detects and cannot rank.

They are deliberately two views of one thing and they fail differently, the
same way `edge_smoothness`'s `ragged_mm` and `perimeter_ratio` do. A design
where they disagree is worth looking at rather than averaging.

## What this instrument cannot do

* **It cannot read intent.** A logo that IS a 20-gon and a circle polygonised
  to one are the same path. Nothing here can separate them, so the absolute
  number is not a grade — it is a PAIRED measure. Run two engine arms over the
  same artwork and read the delta, exactly as the 2026-08-17 tol ladder did.
  A many-pointed star is the standing false positive: its vertices sit below
  `CORNER_DEG` and read as polygonisation.
* **Its resolution is bounded by stitch length, which is physical.** At 2 mm
  sampling the smooth rounded rect climbs to 5.97 and overlaps the n-gons,
  (0.35 at 0.5 mm, 1.41 at 1.0, 5.90 at 2.0) because a 4 mm-radius arc
  genuinely CANNOT be sewn smoothly with 2 mm stitches. That is the machine's
  limit showing through, not an artifact — but it means arms must be compared
  at matched stitch length.
* **Sagitta was tried and cut.** The obvious physical alternative — millimetres
  of bow between the sewn chord and the curve it samples, s = (L/2)tan(t/4),
  which is exact for a regular sampling — is NOT monotonic, because dense
  resampling makes a polygon's straight edges look like a finely-sampled curve:

      step mm   circle   60-gon   40-gon   20-gon   12-gon   monotonic?
          0.5   0.0031   0.0031   0.0031   0.0030   0.0030   no
          3.0   0.1117   0.1116   0.1115   0.1107   0.1100   no

  (arc-length-weighted mean; the p95 and max variants are monotonic only
  below 3 mm sampling and break there.) It measures how finely the path was
  sampled, not how faithfully it follows a curve. Recorded so it is not
  rebuilt as the "obvious" fix.

## Reading a paired arm without fooling yourself

The lever this was built for is `simplify_tol_mm`, which the 2026-08-17 tol
ladder could not measure at all: every delta it saw was an order of magnitude
inside the raster instrument's 0.35 mm floor. Re-run on the stitch path
(2026-08-27, arms 0.2 / 0.1 / 0.05):

    fixture                tol 0.2          tol 0.1          tol 0.05
                        gini  rough      gini  rough      gini  rough
    logo_whitebg      0.9559  1.613    0.9559  1.613    0.9559  1.613
    ribbon_curve      0.5732  9.446    0.5881  8.832    0.5244 11.535
    becker_marine     0.5026 13.153    0.5865 11.034    0.5865 11.034

Two things in that table matter more than the numbers.

`logo_whitebg` does not move at all, and should not: stage 4 floors realized
epsilon at 0.5 px, so its plan is byte-identical across all three arms — the
same effect that made 9 of 14 designs identical in the 2026-08-17 ladder. An
instrument that invented a delta there would be broken. This one reports zero.

And `becker_marine`'s apparent improvement is NOT clean. Its trace count goes
50 -> 77 and its curve vertices 1991 -> 2556 between 0.2 and 0.1: the shape
population itself changed, so part of that gini move is the denominator, not
the geometry. `ribbon_curve` does the same more quietly — its corner count
triples, 6 -> 26, as finer RDP preserves sharper vertices that then fall out
of the measured set. This is ROADMAP hard gate 4's failure mode wearing a
different hat: the mix moved, so the "gain" is partly the floor shifting.

**So: read `traces`, `curve_vertices` and `corner_vertices` alongside every
delta, and distrust any comparison where they moved.** They are reported for
exactly that reason. No engine default should be changed on this table — it
demonstrates that the instrument resolves a lever the raster could not, and
nothing more.

## What the two numbers turn out to measure on REAL artwork

Measured 2026-08-27 over 12 fixtures, both instruments computed from ONE
`digitize()` per design so the comparison is exact. Two results, and the second
one demotes a column.

**`roughness_deg` is not edge noise.** The worry was that it might simply be
re-reading `edge_smoothness.ragged_mm` — the sawtoothing complaint — rather than
curve coarseness. It does not: Spearman 0.028, Pearson 0.153 against `ragged_mm`
(95% CI [-0.55, 0.59]). The rankings are near-inverted at the ends —
`becker_marine_logo` tops roughness and sits 8th of 12 on raggedness;
`summit_badge` tops raggedness and sits 8th on roughness. On n = 12 that
interval is wide, so this rules out the two being REDUNDANT; it does not prove
them independent.

**`turn_gini` is substantially a complexity statistic, and must not be ranked
down a column.** Against log(trace count) it reads Pearson -0.763 / Spearman
-0.676. The two 2-trace designs pin the top of the ranking at 0.95 while every
design with 5+ traces collapses into a 0.50-0.72 band:

    fixture                traces   gini   rough
    logo_alpha                  2  0.946    0.48
    logo_whitebg                2  0.956    1.61
    ribbon_curve                2  0.573    9.45
    logo_gaulke_roofing         5  0.723    9.32
    becker_marine_logo         50  0.503   13.15
    logo_bridge_bar           137  0.529   11.11

That is also why the two columns read Pearson -0.832 against EACH OTHER on real
artwork while they move together on the synthetic n-gon ladder: gini is being
pulled down by complexity as roughness drifts up with it. The docstring above
calls them "two views of one thing that fail differently" — on synthetic shapes
that is exactly right, and on a real corpus their disagreement is mostly
structural rather than informative. `roughness_deg` is the number to read per
design; `turn_gini` earns its keep on the ladder and inside a paired arm, where
the design is held fixed. The CLI marks any design under
`TRACE_FLOOR_FOR_RANKING` as `thin` for this reason.

Usage:
    python -m tools.curve_fidelity <image> [<image> ...]
    python -m tools.curve_fidelity --all
    python -m tools.curve_fidelity --all --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.config import PipelineConfig  # noqa: E402
# The measurement itself: `digitizer_core/curve_fidelity.py` since 2026-10-03,
# so preflight can report it. Re-exported because this module is how the tests
# and the tools that quote a reading reach it.
from digitizer_core.curve_fidelity import (  # noqa: E402,F401
    CORNER_DEG, MIN_TOTAL_TURN_DEG, MIN_TURNS, VISIBLE_KINDS, _rails, gini,
    measure, traces, turns)
from digitizer_core.pipeline import digitize  # noqa: E402
from tools.artfidelity_self import FIXTURES  # noqa: E402


# A design carrying fewer traces than this has its `turn_gini` marked `thin` in
# the CLI, because on the real corpus that column turns out to be substantially
# a COMPLEXITY statistic: measured 2026-08-27 over 12 fixtures, `turn_gini` vs
# log(trace count) is Pearson -0.763 / Spearman -0.676. The two 2-trace designs
# (`logo_whitebg`, `logo_alpha`) pin the top of the ranking at 0.95 while every
# design with 5+ traces collapses into a 0.50-0.72 band. The number is not
# wrong; reading it DOWN a column of mixed designs is.
TRACE_FLOOR_FOR_RANKING = 5


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None) -> dict:
    """Digitize `image_path` and read curve fidelity off the stitch path."""
    image_path = Path(image_path)
    result, plan = digitize(image_path, cfg or PipelineConfig())
    tr = traces(plan)
    row = {"fixture": image_path.name, "route": result.design_class}
    row.update(measure([p for _k, _s, p in tr]))
    return row


def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure whether curves are sewn as curves or as polygons, "
                    "from plan.iter_runs() — the vertices the machine sews. "
                    "Paired measure: compare arms over one design, not designs.")
    ap.add_argument("images", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args(argv)

    names = list(FIXTURES) if args.all else args.images
    if not names:
        ap.error("give image paths or --all")

    rows = []
    paths = _resolve(names)
    for i, p in enumerate(paths, 1):
        if not p.exists():
            print(f"skip (missing): {p}", file=sys.stderr)
            continue
        print(f"[{i}/{len(paths)}] {p.name} ...", file=sys.stderr, flush=True)
        rows.append(analyse(p))

    if not rows:
        print("nothing analysed", file=sys.stderr)
        return 1

    head = (f"{'fixture':26s} {'route':12s} {'gini':>8s} {'rough deg':>10s} "
            f"{'verts':>7s} {'corners':>8s}")
    print(head)
    print("-" * len(head))
    for r in sorted(rows, key=lambda r: -(r["turn_gini"] if r["turn_gini"] == r["turn_gini"] else -1)):
        g = r["turn_gini"]
        rg = r["roughness_deg"]
        gs = f"{g:>8.4f}" if g == g else f"{'--':>8s}"
        rs = f"{rg:>10.3f}" if rg == rg else f"{'--':>10s}"
        thin = (not r["refusal"]
                and r["traces"] < TRACE_FLOOR_FOR_RANKING)
        print(f"{r['fixture']:26s} {r['route']:12s} {gs} {rs} "
              f"{r['curve_vertices']:>7d} {r['corner_vertices']:>8d}"
              + (f"   REFUSED: {r['refusal']}" if r["refusal"]
                 else (f"   thin ({r['traces']} traces) — gini not rankable"
                       if thin else "")))

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
