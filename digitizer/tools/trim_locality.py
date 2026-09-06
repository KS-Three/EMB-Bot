#!/usr/bin/env python
"""Where do the trims actually happen — between shapes, or inside one?

`TRIM_HEAVY`'s remedy read *"consider merging or removing the smallest
shapes"* from the day it was written. That is right only for a cut BETWEEN
shapes. A cut INSIDE one shape is that shape failing to sew in a single pass,
and merging shapes cannot touch it: `satin_shape` may travel over UNSEWN
strokes only, and the 2026-09-06 Becker investigation logged the walk
succeeding up to 40% sewn and **never again after**, so a big multi-stroke
shape spends nearly all of its life unable to reach anywhere. Five other
remedies were measured and refuted there (stroke order, `TRIM_AT_MM`, spur
pruning, the Eulerian floor, end-to-end chaining).

Measured 2026-09-06, 26 fixtures at 80 mm / left_chest:

  * **866 trims: 456 inside a shape (53%), 410 between shapes (47%)** — so a
    single remedy sentence was only ever right about half the time;
  * **in-shape dominates on 11 fixtures, between-shape on 11, one ties.** The
    extremes are opposite designs: `photo_grass_macro` 14 of 15 IN-shape
    (93%), `logo_alpha` and `logo_whitebg` 5 of 5 BETWEEN (100%);
  * `becker_marine_logo` reproduces the hand-instrumented figure exactly —
    **28 trims, 19 in-shape**, worst carrier `Sead76620` at 16. (scope-history
    reads "19 of our 28 pen-ups stay inside ONE shape"; 19 is the in-shape
    TOTAL and 16 of them are in that one shape. Same conclusion, one number
    tightened.)

Two structural facts this also settled, both of which the shipped check now
relies on:

  * **no run in the corpus carries an empty `shape_id`** (0 of 26 fixtures),
    so the guard against an unattributed run matching its unattributed
    neighbour is defensive, not load-bearing — but it stays, because
    `StitchRun.shape_id` defaults to `""` and a synthetic plan does hit it;
  * **no plan has an empty leading run**, so redefining "the run whose trim the
    file does not contain" as the first run WITH POINTS (matching
    `iter_machine_commands`, which skips empty runs entirely) is a no-op here.
    It is still the correct definition, and the old one would have silently
    lost a real cut.

    .venv/bin/python -m tools.trim_locality
"""
from __future__ import annotations

import sys

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize


def split(plan) -> dict:
    """-> the in/between split, walked independently of `_trim_findings`.

    Re-implemented rather than imported on purpose: an auditor that calls the
    thing it audits proves nothing. A test pins the two properties this copy
    has to keep.
    """
    s = plan.stats
    sewn = [r for _b, r in plan.iter_runs() if r.points]
    trims = s.trims - (1 if sewn and sewn[0].trim else 0)
    in_shape = between = noid = 0
    by: dict[str, int] = {}
    prev: str | None = None
    for i, run in enumerate(sewn):
        if run.trim and i > 0:
            if run.shape_id:
                by[run.shape_id] = by.get(run.shape_id, 0) + 1
            else:
                noid += 1
            if run.shape_id and run.shape_id == prev:
                in_shape += 1
            else:
                between += 1
        prev = run.shape_id
    worst = max(by.items(), key=lambda kv: (kv[1], kv[0])) if by else ("-", 0)
    return {"trims": trims, "in_shape": in_shape, "between": between,
            "worst": worst[0], "worst_n": worst[1], "noid_trims": noid,
            "noid_runs": sum(1 for r in sewn if not r.shape_id),
            "empty_lead": bool(plan.blocks and plan.blocks[0].runs
                               and not plan.blocks[0].runs[0].points)}


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    hdr = (f"{'fixture':42} {'trims':>6} {'in':>5} {'btwn':>5} {'worst':>16} "
           f"{'n':>4} {'noid':>5} {'lead':>5}")
    print(hdr)
    print("-" * len(hdr))
    tot = ins = btw = 0
    in_wins = btw_wins = ties = 0
    flags = []
    for fx in FIXTURES:
        art = TESTDATA / fx
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
        try:
            _result, plan = digitize(art, cfg)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        d = split(plan)
        assert d["in_shape"] + d["between"] == d["trims"], (fx, d)
        print(f"{fx:42} {d['trims']:6} {d['in_shape']:5} {d['between']:5} "
              f"{d['worst'][:16]:>16} {d['worst_n']:4} {d['noid_trims']:5} "
              f"{'YES' if d['empty_lead'] else '-':>5}")
        sys.stdout.flush()
        tot += d["trims"]
        ins += d["in_shape"]
        btw += d["between"]
        if d["trims"]:
            if d["in_shape"] > d["between"]:
                in_wins += 1
            elif d["between"] > d["in_shape"]:
                btw_wins += 1
            else:
                ties += 1
        if d["noid_runs"] or d["empty_lead"]:
            flags.append(fx)

    if tot:
        print(f"\n{tot} trims = {ins} inside a shape ({100.0 * ins / tot:.0f}%) "
              f"+ {btw} between shapes ({100.0 * btw / tot:.0f}%)")
    print(f"in-shape dominates {in_wins} fixtures, between-shape {btw_wins}, "
          f"{ties} tie — which is why one remedy sentence could not serve both")
    if flags:
        print("\nfixtures with an unattributed run or an empty leading run — "
              "the two defensive cases in `_trim_findings` are LIVE here:")
        for f in flags:
            print(f"  {f}")
    else:
        print("no unattributed runs and no empty leading runs anywhere — both "
              "guards in `_trim_findings` are defensive, not load-bearing")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
