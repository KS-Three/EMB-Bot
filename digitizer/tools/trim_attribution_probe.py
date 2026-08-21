#!/usr/bin/env python
"""Where do one design's trims actually come from, and what is gate-clear?

Built for live defect 6 (satin border fragmentation) against the target Kent
ruled first on 2026-08-21: `logo_hotel_fremont.webp` at 92.5 mm / patch, whose
worst single shape carries over 40% of the whole design's cuts.

Three passes, each answering a different question:

  shapes      Which shape carries the trims? Area, hole count, run kinds.
  boundaries  Why does that shape cut? Every run-to-run gap, split by whether
              it cut, so the deciding rule shows itself rather than being
              assumed.
  reorder     How much could better ORDERING win? Greedy nearest-endpoint over
              the same fill runs, flipping allowed, scored by the same rule.

MEASURED 2026-08-21 (`S78e6cd01`, 2095.8 mm2, 46 holes, 280 fill runs):

  - 57 of the design's 132 trims -- 43% -- inside that one shape.
  - The cut rule is a clean step function with nothing else in play: gaps that
    did NOT cut top out at 2.92 mm, gaps that DID cut start at 3.02 mm. That is
    `trim_at_mm = 3.0` and only that.
  - 48 of 56 cuts (86%) are moves under 11.8 mm -- the band
    `docs/fragmentation-attribution-2026-08-18.md` measured the professional as
    floating uncut. `trim_at_mm` is gate-1 territory, so this is NOT retunable
    on this evidence.

READ THE `reorder` PASS WITH ITS CAVEAT -- it is why this tool exists rather
than a one-off. It compares fill-run endpoints ONLY, skipping the travel runs
the planner interleaves (63 of them on this shape), so its "as shipped" count
(100) is NOT the real trim count (57) and the two are not commensurable. A
first pass at this read them as like-for-like and concluded ordering was worth
a 56% cut reduction. It is not: `_fill_paths` ALREADY orders columns greedily
nearest-first, considering both traversal directions
(`stage6_fill.py:594-676`), so "add nearest-neighbour ordering" is not a
missing fix and should not be re-proposed. The reorder pass is kept because it
bounds what pure ordering can do -- not as a claim about trims.

What that leaves as gate-clear on this shape is travel COVERAGE: every 3-11.8
mm gap a travel run could bridge is a cut removed without touching a constant.
That points at `_graph_travel` never returning a path, which no test in the
repo exercises. Not measured here.

Usage:
    .venv/bin/python tools/trim_attribution_probe.py            # all passes
    .venv/bin/python tools/trim_attribution_probe.py --pass boundaries
    .venv/bin/python tools/trim_attribution_probe.py --shape S78e6cd01
(`.venv/Scripts/python` on Windows.)
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402

DEFAULT_IMAGE = "testdata/photo/logo_hotel_fremont.webp"
# The pro's measured floor: it never cut for a move shorter than this.
# docs/fragmentation-attribution-2026-08-18.md, "The pro's actual cut rule".
PRO_FLOAT_FLOOR_MM = 11.8
BANDS = ((0.0, 3.0), (3.0, 6.0), (6.0, PRO_FLOAT_FLOOR_MM), (PRO_FLOAT_FLOOR_MM, math.inf))


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bands(gaps: list[float], label: str) -> None:
    n = len(gaps)
    if not n:
        print(f"  {label}: none")
        return
    xs = sorted(gaps)
    q = lambda p: xs[min(n - 1, int(p * n))]  # noqa: E731
    print(f"  {label}: n={n}  min={xs[0]:.2f}  median={q(.5):.2f}  max={xs[-1]:.2f} mm")
    for lo, hi in BANDS:
        c = sum(1 for x in xs if lo <= x < hi)
        hi_s = "inf" if hi == math.inf else f"{hi:g}"
        print(f"      {lo:>5g} - {hi_s:>5} mm : {c:4d} ({100.0 * c / n:5.1f}%)")


def pass_shapes(result, plan) -> str:
    """-> shape_id carrying the most trims."""
    runs, trims, kinds = Counter(), Counter(), defaultdict(Counter)
    for _b, r in plan.iter_runs():
        sid = r.shape_id or "(none)"
        runs[sid] += 1
        kinds[sid][r.kind] += 1
        if r.trim:
            trims[sid] += 1
    meta = {reg.shape_id: reg for reg in (getattr(result, "regions", None) or [])}

    st = plan.stats
    print(f"design: stitches={st.stitch_count} trims={st.trims} jumps={st.jumps} "
          f"colors={st.color_changes}")
    print(f"\n{'shape':>12} {'trims':>6} {'runs':>6} {'area_mm2':>10} {'holes':>6}  kinds")
    for sid, n in sorted(trims.items(), key=lambda kv: -kv[1])[:8]:
        reg = meta.get(sid)
        area = f"{reg.area_mm2:10.1f}" if reg else f"{'?':>10}"
        try:
            holes = f"{len(reg.polygon.interiors):6d}"
        except Exception:
            holes = f"{'?':>6}"
        print(f"{sid:>12} {n:6d} {runs[sid]:6d} {area} {holes}  {dict(kinds[sid])}")

    worst, wn = max(trims.items(), key=lambda kv: kv[1])
    print(f"\nworst shape {worst}: {wn}/{sum(trims.values())} trims "
          f"= {100.0 * wn / max(1, sum(trims.values())):.1f}% of the design")
    return worst


def pass_boundaries(plan, shape: str) -> None:
    seq = [r for _b, r in plan.iter_runs() if r.shape_id == shape and r.points]
    print(f"{shape}: {len(seq)} runs in plan order")
    transitions = Counter()
    cut, nocut = [], []
    for cur, nxt in zip(seq, seq[1:]):
        g = _dist(cur.points[-1], nxt.points[0])
        transitions[("TRIM" if nxt.trim else "jump" if nxt.jump else "-", nxt.kind)] += 1
        (cut if nxt.trim else nocut).append(g)

    print("\ntransitions (flag -> next kind):")
    for (flag, kind), n in sorted(transitions.items(), key=lambda kv: -kv[1]):
        print(f"    {flag:>5} -> {kind:<9} {n:4d}")
    print()
    _bands(cut, "gaps that DID cut")
    _bands(nocut, "gaps that did NOT cut")
    if cut:
        under = sum(1 for g in cut if g < PRO_FLOAT_FLOOR_MM)
        print(f"\n  cuts for a move the pro would have floated "
              f"(<{PRO_FLOAT_FLOOR_MM} mm): {under}/{len(cut)}")
    if nocut and cut:
        print(f"  step function: nothing cut below {max(nocut):.2f} mm, "
              f"everything cut above {min(cut):.2f} mm")


def pass_reorder(plan, shape: str, trim_at_mm: float) -> None:
    fills = [r for _b, r in plan.iter_runs()
             if r.shape_id == shape and r.kind == "fill" and r.points]
    print(f"{shape}: {len(fills)} fill runs")
    print("CAVEAT: fill-to-fill endpoints only, ignoring interleaved travel runs.")
    print("        The 'as shipped' number here is NOT the plan's trim count.\n")
    ends = [(r.points[0], r.points[-1]) for r in fills]

    def score(seq):
        gaps = [_dist(seq[i][1], seq[i + 1][0]) for i in range(len(seq) - 1)]
        return sum(1 for g in gaps if g >= trim_at_mm), gaps

    now, gaps_now = score(ends)
    unused, cur, order = set(range(1, len(ends))), ends[0][1], [ends[0]]
    while unused:
        best, flip, bd = None, False, math.inf
        for i in unused:
            s, e = ends[i]
            if (ds := _dist(cur, s)) < bd:
                best, flip, bd = i, False, ds
            if (de := _dist(cur, e)) < bd:
                best, flip, bd = i, True, de
        s, e = ends[best]
        order.append((e, s) if flip else (s, e))
        cur = order[-1][1]
        unused.discard(best)
    opt, gaps_opt = score(order)

    _bands(gaps_now, "as shipped")
    _bands(gaps_opt, "greedy reorder")
    print(f"\n  boundaries >= {trim_at_mm} mm: {now} -> {opt}")
    print(f"  total inter-run travel: {sum(gaps_now):.0f} mm -> {sum(gaps_opt):.0f} mm")
    print("  Ordering is NOT a missing fix: _fill_paths already orders columns")
    print("  greedily nearest-first, both directions (stage6_fill.py:594-676).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--width-mm", type=float, default=92.5)
    ap.add_argument("--garment", default="patch")
    ap.add_argument("--max-colors", type=int, default=6)
    ap.add_argument("--shape", default=None,
                    help="shape_id to dissect; default is whichever carries the most trims")
    ap.add_argument("--pass", dest="which", default="all",
                    choices=("all", "shapes", "boundaries", "reorder"))
    ap.add_argument("--trim-at-mm", type=float, default=3.0,
                    help="cut rule the reorder pass scores against (gate 1: do not retune)")
    args = ap.parse_args()

    cfg = PipelineConfig(target_width_mm=args.width_mm, garment_id=args.garment,
                         max_colors=args.max_colors)
    result, plan = digitize(args.image, cfg)

    shape = args.shape
    if args.which in ("all", "shapes") or shape is None:
        print("=== shapes ===")
        worst = pass_shapes(result, plan)
        shape = shape or worst
    for name, fn in (("boundaries", lambda: pass_boundaries(plan, shape)),
                     ("reorder", lambda: pass_reorder(plan, shape, args.trim_at_mm))):
        if args.which in ("all", name):
            print(f"\n=== {name} ===")
            fn()


if __name__ == "__main__":
    main()
