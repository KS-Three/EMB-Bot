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
    .venv/bin/python -m tools.spool_remedy --yardstick   # would excess clear it?
    .venv/bin/python -m tools.spool_remedy --masks       # same pixels? (see `masks`)
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


def yardstick(fixture: str, testdata) -> tuple[int, int]:
    """Would this fixture still BLOCK if the gradient lane were scored on
    EXCESS? -> (blocks under raw, blocks under excess).

    `MASTER_SCOPE` defect 28 decomposes the F wall as *"the raw yardstick,
    4 of 7 — `golden_tee`, `drone_render`, `region_blobs`, `summit_badge`
    clear every block once scored on EXCESS."* Nothing reproduced that, and
    the entry beside it (*"halo cones, 1 of 7"*) turned out to be a bug's
    artifact and was retracted on 2026-09-07 — which left `gaulke_roofing`
    the seventh, unexplained. This is the instrument for both: it re-runs the
    check's own scoring under each yardstick and counts what blocks.

    It is NOT `report()` with a different print. `_thread_match_findings`
    chooses the offender set on `_score`, so under excess the top row can be a
    DIFFERENT row than the raw top — a thread whose worst raw patch has a
    close loaded alternative, and whose second-worst does not, blocks on a row
    raw scoring never looks at. So every row gets its own excess here, and the
    top is taken per yardstick.

    Nothing is patched: excess is already computed on every route (2026-09-06),
    so this reads the shipped numbers rather than forcing `_is_photo_class`,
    which would also gate `PHOTO_RESOLUTION_LOW` and the subject check and
    confound the answer.
    """
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
    print(f"\n=== {fixture}   {len(loaded)} cones, {len(rows)} scored rows")
    if len(loaded) < 2:
        # The check's own early-out: with one cone there is no alternative, so
        # every excess is 0 by construction and "clears under excess" would be
        # true for a reason that has nothing to do with the design.
        print("  single cone — excess is 0 by construction, not comparable")
        return 0, 0

    raw_blocks = exc_blocks = 0
    for t in loaded:
        for r in by_thread[t]:
            if r["delta_e"] > pf.DELTA_E_VISIBLE:
                best_err, _ = pf._best_loaded_spool_error(
                    r["_lab_px"], loaded, chart)
                r["_exc"] = max(0.0, r["delta_e"] - best_err)
            else:
                r["_exc"] = 0.0
        raw_top = max(by_thread[t], key=lambda r: r["delta_e"])
        exc_top = max(by_thread[t], key=lambda r: r["_exc"])
        rb = raw_top["delta_e"] > pf.DELTA_E_CLEARLY_DIFFERENT
        eb = exc_top["_exc"] > pf.DELTA_E_CLEARLY_DIFFERENT
        raw_blocks += rb
        exc_blocks += eb
        if rb or eb:
            moved = "" if rb == eb else ("  <-- CLEARS under excess" if rb
                                         else "  <-- BLOCKS only under excess")
            same = " (same row)" if raw_top is exc_top else " (different row)"
            print(f"  {chart[t].number} ({chart[t].name}): "
                  f"raw {raw_top['delta_e']:.1f} {'BLOCK' if rb else 'warn '} | "
                  f"excess {exc_top['_exc']:.1f} {'BLOCK' if eb else 'warn '}"
                  f"{same}{moved}")
    verdict = ("CLEARS every block under excess" if raw_blocks and not exc_blocks
               else f"{exc_blocks} block(s) survive excess"
               if exc_blocks else "no blocks under either")
    print(f"  -> raw {raw_blocks} block(s), excess {exc_blocks} — {verdict}")
    return raw_blocks, exc_blocks


def masks(fixture: str, spool: str, testdata) -> None:
    """Do stage 4 and preflight score a region on the SAME pixels?

    They claim the same estimator and they have it — both take the median of
    the per-pixel CIEDE2000, the one `revalidate_threads`' docstring settled
    on. **They do not have the same MASK.** `_region_color_errors` erodes the
    polygon raster one pixel and drops `p.bg_mask` (*"to keep anti-alias halo
    pixels from dragging a flat color toward the background"*);
    `_region_footprint` is a bare `cv2.fillPoly` and does neither. So the
    re-snap can pick a thread on pixels the grader would refuse, and the
    grader then condemns the thread the re-snap chose.

    Whether that gap is what is BLOCKING a given fixture is a measurement,
    not a story — run it before saying so. Measured 2026-09-07 on the three
    fixtures that still block under excess scoring, it explains exactly one.
    """
    art = testdata / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    p = pf.prep(art, cfg)
    chart = chart_for(cfg)
    rows = pf._region_color_errors(p, result, plan, cfg)
    cand = [r for r in rows if chart[r["thread_index"]].number == spool]
    if not cand:
        print(f"\n=== {fixture}: no scored row wears {spool}")
        return
    worst = max(cand, key=lambda r: r["delta_e"])
    sid = str(worst["shape_id"]).split(" shade ")[0]
    reg = next((r for r in result.regions if r.shape_id == sid), None)
    if reg is None:
        print(f"\n=== {fixture}: {sid} resolves to no region")
        return

    import numpy as np
    from skimage.color import deltaE_ciede2000
    from digitizer_core.stage4_vectorize import _region_footprint, _sample_lab
    from digitizer_core.threads import rgb_to_lab

    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    fp = _region_footprint(reg, p.rgb.shape[:2], cx, cy, p.px_per_mm)
    lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(*p.rgb.shape[:2], 3)
    samples = _sample_lab(lab[fp])
    per_spool = np.median(
        deltaE_ciede2000(samples[:, None, :], chart.lab[None, :, :]), axis=0)
    s4 = float(per_spool[reg.thread_index])
    lum = p.rgb[fp].reshape(-1, 3).mean(axis=1)
    n_raw, n_pf = int(fp.sum()), len(worst["_lab_px"])

    print(f"\n=== {fixture}  {sid}  {reg.area_mm2:.2f} mm² @ {p.px_per_mm:.1f} px/mm")
    print(f"  stage 4 (raw fillPoly)   {n_raw:>5} px  -> {spool} reads {s4:5.1f} dE00")
    print(f"  preflight (erode + ~bg)  {n_pf:>5} px  -> {spool} reads "
          f"{worst['delta_e']:5.1f} dE00")
    print(f"  gap {abs(s4 - worst['delta_e']):.1f} dE00 over {n_raw / max(n_pf, 1):.1f}x "
          f"the pixels ({int((lum < 64).sum())} near-black + "
          f"{int((lum >= 192).sum())} near-white in stage 4's set)")
    # The gap is what matters, not either number's absolute size: stage 4 can
    # read a thread as mediocre and preflight as catastrophic, and it is the
    # DISTANCE between them that says the two saw different artwork.
    if abs(s4 - worst["delta_e"]) >= pf.DELTA_E_CLEARLY_DIFFERENT:
        print("  -> MASK GAP: the two instruments scored different artwork.")
    else:
        print("  -> not the mask: both instruments agree on this region, so "
              "the cause is elsewhere (stage 4's floor, or no better cone).")


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    fixtures = F_WALL
    if "--all" in argv:
        fixtures = sorted(
            str(q.relative_to(TESTDATA)).replace("\\", "/")
            for q in (TESTDATA / "photo").glob("*.*"))
    if "--masks" in argv:
        # The three that still block under excess scoring, with the spool
        # whose block survives — from `--yardstick`, not from memory.
        for fx, spool in (("photo/logo_gaulke_roofing.png", "3971"),
                          ("photo/screenshot_phone_ui_golke.jpg", "0111"),
                          ("photo/logo_bridge_bar.jpg", "6156")):
            try:
                masks(fx, spool, TESTDATA)
            except Exception as e:                      # pragma: no cover
                print(f"\n=== {fx}: SKIPPED ({e})")
        return 0

    if "--yardstick" in argv:
        cleared, held = [], []
        for fx in fixtures:
            try:
                raw, exc = yardstick(fx, TESTDATA)
            except Exception as e:                      # pragma: no cover
                print(f"\n=== {fx}: SKIPPED ({e})")
                continue
            if raw and not exc:
                cleared.append(fx)
            elif exc:
                held.append(f"{fx} ({exc})")
        print(f"\n{'=' * 60}\nOver {len(fixtures)} fixture(s): "
              f"{len(cleared)} clear every block under EXCESS scoring, "
              f"{len(held)} still block.")
        print(f"  clears: {', '.join(cleared) or 'none'}")
        print(f"  holds : {', '.join(held) or 'none'}")
        return 0

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
