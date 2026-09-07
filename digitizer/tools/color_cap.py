#!/usr/bin/env python
"""Does "Colors (max N)" mean anything on the artwork customers actually upload?

The Studio ships `max_colors: 6` and labels the slider **"Colors (max 6)"**.
Thread count is the cost driver in embroidery — every distinct cone is a spool
to buy and, on a single-needle machine, a manual re-thread mid-job — so this
is a pricing promise, not a preference.

**It is enforced on one of the two lanes.** `stage2_quantize` (the FLAT lane)
caps hard: past `cfg.max_colors` it merges the smallest areas into their
closest match and says so with `COLOR_CAP_APPLIED`. The SLIC+RAG lane that
gradient- and photo-classified art takes passes `max_k=cfg.max_colors` into
k-medoids, which is a clustering parameter and not a cap — and downstream
steps can then ADD cones past it.

Which matters because of a number already in MASTER_SCOPE: **stage 0 routes
six of seven real customer logos to GRADIENT**, because real logo art carries
JPEG ringing and anti-aliased edges the synthetics lack. So the control is
enforced on the artwork type customers do not have.

Driven in the live app 2026-09-07 on `logo_bridge_bar.jpg` at the shipped
default: the slider read **"Colors (max 6)"** and the design came back
**13 distinct cones, 12 colour stops**, with `COLOR_CAP_APPLIED` never firing.

This counts that gap over the whole corpus. It changes nothing.

    .venv/bin/python -m tools.color_cap            # as shipped
    .venv/bin/python -m tools.color_cap --enforce  # with cfg.enforce_color_cap
"""
from __future__ import annotations

import sys

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

STUDIO_DEFAULT_MAX_COLORS = 6      # app/src/lib/project.js DEFAULT_DIGITIZE_PARAMS


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    args = [a for a in argv if not a.startswith("--")]
    enforce = "--enforce" in argv
    cap = int(args[0]) if args else STUDIO_DEFAULT_MAX_COLORS
    rows, over = [], 0
    for fx in FIXTURES:
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                             max_colors=cap, enforce_color_cap=enforce)
        try:
            result, plan = digitize(TESTDATA / fx, cfg)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        cones = len({b.thread_number for b in plan.blocks
                     if any(len(r.points) for r in b.runs)})
        stops = sum(1 for _ in plan.blocks) - 1
        codes = {w.get("code") for w in (plan.warnings or [])}
        lane = result.design_class
        capped = "COLOR_CAP_APPLIED" in codes
        if cones > cap:
            over += 1
        rows.append((fx, lane, cones, stops, capped))

    print(f'Studio slider: "Colors (max {cap})"   '
          f'cfg.enforce_color_cap={enforce}\n')
    print(f"{'fixture':40} {'class':14} {'cones':>5} {'stops':>5}  cap fired")
    print("-" * 82)
    for fx, lane, cones, stops, capped in sorted(rows, key=lambda r: -r[2]):
        flag = "  <-- OVER" if cones > cap else ""
        print(f"{fx:40} {lane:14} {cones:5} {stops:5}  "
              f"{'yes' if capped else '-':>9}{flag}")

    by_lane: dict[str, list[int]] = {}
    for _fx, lane, cones, _s, _c in rows:
        by_lane.setdefault(lane, []).append(cones)
    print(f"\n{over} of {len(rows)} designs sew MORE cones than the slider "
          f"promises.")
    for lane, cs in sorted(by_lane.items()):
        n_over = sum(1 for c in cs if c > cap)
        print(f"  {lane:14} {n_over}/{len(cs)} over, worst {max(cs)}")
    print("\nEvery distinct cone is a spool to buy and, on a single-needle "
          "machine, a manual re-thread mid-job. This is the number a quote is "
          "built from.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
