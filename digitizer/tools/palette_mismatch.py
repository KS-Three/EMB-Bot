#!/usr/bin/env python
"""Which palette is wrong when `PALETTE_THREAD_MISMATCH` fires — and which is not.

`PALETTE_THREAD_MISMATCH` (warnings_codes.py) fires when a region sews in a
thread its LAYER's palette entry does not name. `rehome_resnapped_regions`
closed most of it on 2026-08-31 by moving a re-snapped region to the layer
DECLARING its new cone; what survives is the re-snap whose target NO layer
declares.

## Read the contract before the numbers, because there are TWO palettes

    result.palette   per LAYER.  What the REVIEW SCREEN edits against
                     (service `review.palette`). This is the one that goes
                     wrong.
    plan.palette     per BLOCK, in sew order. `palette[i]` describes
                     `blocks[i]`; the service ships it as `stats.blocks` and
                     the download's own thread list is `design.colors`.
                     **This is what the operator threads from, and it is
                     right by construction** — `StitchPlan.palette`'s own
                     comment says reading the LAYER list positionally against
                     blocks is what shipped `golf_hat`'s black block labelled
                     "0020 Tangerine" until 2026-08-14.

**This tool overstated its finding TWICE before it said anything true**, and
both are recorded rather than quietly deleted, because the whole subject here
is an instrument reporting more than it knows.

1. **It compared `result.palette` against what sews and printed
   "RACK-WRONG" — the operator loads a cone that never runs.** That is the
   REVIEW list, not the rack. The operator threads from `plan.palette`, and
   the verdict was wrong on all six fixtures. The "by construction" claim is
   now CHECKED per fixture (`_operator_list_is_consistent`) so it cannot rot
   back into an assumption.
2. **It then reported "threads that sew but are absent from the review
   list", which is BY DESIGN and not this defect.** A blend or tonal region
   sews several shades inside one layer (`shade_thread_index` blocks); the
   layer list names the layer, and the shades ride in the service's
   `stats.blocks` — `StitchPlan.palette` and `_stats_payload` both say so.
   `gradient_ramp_linear` made it obvious: **one** mismatched shape beside
   **four** "missing" threads. A layer whose regions all went unstitched
   (`SHAPES_LEFT_UNSEWN`, 10 of 26 fixtures) confounds the other direction
   the same way.

**What is left is not confounded.** `mismatched` is computed over REGIONS and
each region's own `thread_number`, so blend bands never enter it. The one
extra question worth asking of it — and the one the payload cannot answer on
its own — is whether the thread a mismatched shape ACTUALLY sews appears
anywhere in the review list, or nowhere in it.

## What is actually at stake

The review screen labels a layer with a cone the layer does not sew, and a
sewn thread can be absent from that list entirely — so a user reordering or
recolouring by those labels is acting on a wrong one. A labelling defect on
the editing surface, not a wasted cone at the machine.

    .venv/bin/python -m tools.palette_mismatch
"""
from __future__ import annotations

import collections
import sys

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize


def _operator_list_is_consistent(plan) -> bool:
    """`plan.palette[i]` must name `plan.blocks[i]`'s own thread.

    The claim that the operator's list cannot be wrong rests entirely on
    this, so it is asserted per fixture rather than believed.
    """
    return (len(plan.palette) == len(plan.blocks)
            and all(str(c.get("number")) == str(b.thread_number)
                    for c, b in zip(plan.palette, plan.blocks)))


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    fired = 0
    operator_ok = 0
    rows: list[tuple] = []
    for fx in FIXTURES:
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
        try:
            result, plan = digitize(TESTDATA / fx, cfg)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        operator_ok += 1 if _operator_list_is_consistent(plan) else 0

        hit = next((w for w in (getattr(plan, "warnings", None) or [])
                    if w.get("code") == "PALETTE_THREAD_MISMATCH"), None)
        if hit is None:
            continue
        fired += 1

        review = {str(c.get("number")) for c in (result.palette or [])}
        listed = sorted(str(x) for x in (hit.get("listed") or []))
        actual = sorted(str(x) for x in (hit.get("actual") or []))
        rows.append((fx, hit.get("count", 0), sorted(hit.get("layers") or []),
                     listed, actual, sorted(set(actual) - review)))

    orphans = 0
    print(f"{'fixture':40} {'shapes':>6}  layers")
    print("-" * 88)
    for fx, n, layers, listed, actual, off_list in rows:
        print(f"{fx:40} {n:6}  {layers}")
        print(f"{'':40}   the layer lists {listed}, the shapes sew {actual}")
        if off_list:
            orphans += 1
            print(f"{'':40}   and {off_list} is on NO review layer at all")

    print(f"\n{fired} of {len(FIXTURES)} fixtures fire PALETTE_THREAD_MISMATCH, "
          f"and on {orphans} of them the thread those shapes sew is on NO "
          f"review layer at all — so the review screen cannot show it, not "
          f"merely show it in the wrong place.")
    print(f"The OPERATOR list (plan.palette against plan.blocks) is consistent "
          f"on {operator_ok} of {len(FIXTURES)} — checked, not assumed. "
          f"Everything above is the REVIEW screen's per-layer list, which is "
          f"what a user reorders and recolours by.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
