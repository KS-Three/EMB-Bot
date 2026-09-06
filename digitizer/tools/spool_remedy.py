#!/usr/bin/env python
"""When `THREAD_MATCH_POOR` blocks, is a better spool ALREADY on the machine?

`_thread_match_findings` computes the best already-loaded spool only on the
PHOTO route, because that route is also SCORED on excess over it (2026-08-24).
Off that route `better_spool` is None, so the finding's remedy reads *"pick a
closer thread"* without ever checking the design's own cone list — and all
seven F-grade fixtures are `gradient`, which is where real logo art routes.

This counts the two cases the operator cannot currently tell apart:

  ACTIONABLE NOW    a spool the design already loads is meaningfully closer,
                    so the fix is a re-assignment, not a purchase.
  NEEDS A NEW CONE  nothing loaded is closer; the artwork colour is outside
                    what this cone list can reach at all.

It does NOT change severity, and neither does the fix it argues for: excess
is REPORTED, raw distance still JUDGES off the photo route. Whether the
gradient lane should also be judged on excess is a separate product call
(a logo's palette can be changed, a photograph's cannot) — recorded as
disagreement 4 in `docs/yardstick-disagreements-2026-09-06.md`.

    .venv/bin/python -m tools.spool_remedy [--all]
"""
from __future__ import annotations

import sys

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.threads import chart_for

# The seven F-grade fixtures of the 2026-09-06 decomposition, all gradient.
F_WALL = [
    "photo/logo_gaulke_roofing.png", "photo/drone_render.png",
    "photo/screenshot_phone_ui_golke.jpg", "photo/logo_golden_tee.jpg",
    "photo/logo_bridge_bar.jpg", "photo/region_blobs.png",
    "photo/summit_badge.png",
]


def report(fixture: str, testdata) -> tuple[int, int]:
    art = testdata / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    p = pf.prep(art, cfg)
    rows = pf._region_color_errors(p, result, plan, cfg)
    chart = chart_for(cfg)

    by_thread: dict[int, list[dict]] = {}
    for row in rows:
        by_thread.setdefault(row["thread_index"], []).append(row)
    loaded = sorted(by_thread)
    photo = pf._is_photo_class(plan, cfg)

    print(f"\n=== {fixture}   {'PHOTO' if photo else 'gradient/flat'} route, "
          f"{len(loaded)} cones, {len(rows)} scored rows")
    if len(loaded) < 2:
        print("  single cone — no alternative exists by construction")
        return 0, 0

    actionable = needs_cone = 0
    for t in loaded:
        offenders = sorted(
            (r for r in by_thread[t] if r["delta_e"] > pf.DELTA_E_VISIBLE),
            key=lambda r: -r["delta_e"])
        if not offenders:
            continue
        top = offenders[0]
        best_err, best_spool = pf._best_loaded_spool_error(
            top["_lab_px"], loaded, chart)
        excess = max(0.0, top["delta_e"] - best_err)
        blocks = top["delta_e"] > pf.DELTA_E_CLEARLY_DIFFERENT
        if best_spool != t and excess > pf.DELTA_E_VISIBLE:
            actionable += 1
            verdict = (f"ACTIONABLE NOW -> {chart[best_spool].number} "
                       f"({chart[best_spool].name}) is loaded and "
                       f"{top['delta_e'] - best_err:.1f} dE00 closer")
        else:
            needs_cone += 1
            verdict = "NEEDS A NEW CONE — nothing loaded is closer"
        print(f"  {'BLOCK' if blocks else ' warn'} {chart[t].number} "
              f"({chart[t].name}): raw {top['delta_e']:.1f}, "
              f"excess {excess:.1f} — {verdict}")
    return actionable, needs_cone


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    fixtures = F_WALL
    if "--all" in argv:
        fixtures = sorted(
            str(q.relative_to(TESTDATA)).replace("\\", "/")
            for q in (TESTDATA / "photo").glob("*.*"))
    tot_a = tot_n = 0
    for fx in fixtures:
        try:
            a, n = report(fx, TESTDATA)
        except Exception as exc:                        # pragma: no cover
            print(f"\n=== {fx}: SKIPPED ({exc})")
            continue
        tot_a += a
        tot_n += n
    print(f"\n{'=' * 60}\nTOTAL over {len(fixtures)} fixture(s): "
          f"{tot_a} finding(s) ACTIONABLE NOW with a loaded spool, "
          f"{tot_n} need a cone the design does not carry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
