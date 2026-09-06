#!/usr/bin/env python
"""Do `STITCHES_TOO_SHORT` and `LETTERING_TOO_SMALL` report the same defect?

They measure the SAME quantity at the SAME threshold: `MIN_COLUMN_MM` IS
`machine.MIN_STITCH_MM`, and both read the consecutive-step distance inside a
SATIN run, which crosses the column. They differ only in how they aggregate —
lettering takes a per-shape MEDIAN, the short-stitch check takes a global
FRACTION — so the question is not whether they correlate but whether the second
one says anything the first did not.

Measured 2026-09-06, 26 fixtures at 80 mm / left_chest:

  * as a design-level SIGNAL it is redundant — 10 fixtures fired both, 1 fired
    lettering only, and **0 fired this one alone**, so its 12 points always
    land on a design already warned;
  * as a LOCATION report it is not — only **66%** of the short steps sit inside
    a shape lettering named. The residue is not small lettering. Uncovered
    carriers run **1.1 to 3.2 mm median column**, and `logo_bridge_bar`'s worst
    has a 2.65 mm median with 205 of its 1,597 steps under the needle minimum:
    sewable columns with a narrow WAIST, which lettering's median test cannot
    see and should not.

That split is why the finding now emits `shapes` / `uncovered_shapes` instead
of a bare fraction, and why neither check should be deleted to "dedupe" them.

Re-run this after per-stroke satin routing lands
(`docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`) — that is the
documented root cause of the short columns, so both numbers should move.

    .venv/bin/python -m tools.short_satin_overlap
"""
from __future__ import annotations

import math
import sys

from digitizer_core import machine, preflight as pf, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize


def _satin_steps(plan) -> dict[str, list[float]]:
    """Consecutive-step distances per shape, SATIN runs only.

    Same loop `_stitch_length_findings` runs, kept here rather than imported so
    this tool measures the geometry independently of the check it is auditing.
    """
    out: dict[str, list[float]] = {}
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN:
            continue
        for a, b in zip(run.points, run.points[1:]):
            out.setdefault(run.shape_id, []).append(math.dist(a, b))
    return out


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    print(f"MIN_COLUMN_MM={pf.MIN_COLUMN_MM} "
          f"MIN_STITCH_MM={machine.MIN_STITCH_MM} "
          f"same object={pf.MIN_COLUMN_MM is machine.MIN_STITCH_MM}\n")
    hdr = (f"{'fixture':42} {'satin':>6} {'short':>6} {'frac':>5} "
           f"{'LTS':>4} {'STS':>4} {'covered':>8} {'uncov':>6}")
    print(hdr)
    print("-" * len(hdr))

    tot = cov = 0
    both = only_lts = only_sts = neither = 0
    worst: list[tuple[float, str, str, int, int]] = []
    for fx in FIXTURES:
        art = TESTDATA / fx
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
        try:
            result, plan = digitize(art, cfg)
            rep = pf.run_preflight(result, plan, cfg, image=art)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        by = {f["code"]: f for f in rep["findings"]}
        lts, sts = by.get(pf.LETTERING_TOO_SMALL), by.get(pf.STITCHES_TOO_SHORT)
        named = ({s["shape_id"] for s in lts["extra"]["shapes"]} if lts
                 else set())

        steps = _satin_steps(plan)
        satin = sum(len(v) for v in steps.values())
        short = inside = 0
        uncovered = 0
        for sid, ds in steps.items():
            n = sum(1 for d in ds if d < machine.MIN_STITCH_MM)
            short += n
            if sid in named:
                inside += n
            elif n:
                uncovered += 1
                med = sorted(ds)[len(ds) // 2]
                worst.append((med, fx, sid, n, len(ds)))
        frac = short / satin if satin else 0.0
        pct = f"{100.0 * inside / short:7.1f}%" if short else "      --"
        print(f"{fx:42} {satin:6} {short:6} {frac:5.2f} "
              f"{'yes' if lts else '  -':>4} {'yes' if sts else '  -':>4} "
              f"{pct:>8} {uncovered:6}")
        tot += short
        cov += inside
        if lts and sts:
            both += 1
        elif lts:
            only_lts += 1
        elif sts:
            only_sts += 1
        else:
            neither += 1

    print(f"\nboth={both}  lettering only={only_lts}  "
          f"short-stitch ALONE={only_sts}  neither={neither}")
    if only_sts:
        print("  ^ a fixture fired the short-stitch check with no size warning:"
              " the redundancy claim above no longer holds as stated")
    if tot:
        print(f"{cov}/{tot} short satin steps ({100.0 * cov / tot:.1f}%) lie "
              f"inside a shape LETTERING_TOO_SMALL already named")

    if worst:
        print("\nWidest uncovered carriers — a sewable column with a waist is "
              "NOT small lettering:")
        for med, fx, sid, n, t in sorted(worst, reverse=True)[:8]:
            print(f"  {med:5.2f} mm median  {n:5}/{t:<5} short  {sid:12} {fx}")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
