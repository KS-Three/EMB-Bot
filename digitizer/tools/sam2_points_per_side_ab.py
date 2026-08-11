#!/usr/bin/env python
"""Task #10 — validate `photo_segment_sam2_points_per_side=12` on a REAL photo.

Why this exists: 16 -> 12 was chosen on measurement, but the ONLY thing it was
measured against is `testdata/photo/photo_scene_stub.png`, a synthetic stub.
The photo that actually justified keeping SAM2 (Kent's, 2026-08-11, "drastically
better at the photo recognition portion") has never been re-measured at 12, so
the shipped default is unvalidated against the content that motivated it.
MASTER_SCOPE.md tracks this as one of two open risks on the SAM2 lane.

What it does: runs the SAME image through the REAL pipeline once per
`points_per_side` value, with SAM2 genuinely engaged, and reports wall clock and
what the segmenter actually produced. It refuses to report a comparison that
silently fell back to the classical segmenter — a fallback is the failure mode
this measurement is most likely to hit and least likely to notice.

Usage:
    PYTHONPATH=. .venv/Scripts/python tools/sam2_points_per_side_ab.py <image> [--points 16 12] [--mm 90] [--garment left_chest]

Notes:
  * Needs the isolated SAM2 venv built (digitizer/sam2_isolated/README.md) and
    the checkpoint prewarmed, or every run falls back and the script says so.
  * `forced_class` is deliberately NOT set: whether a real photo classifies as
    photo_subject/photo_scene at all is part of what this is checking, since
    SAM2 only engages for those two classes.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.config import PipelineConfig       # noqa: E402
from digitizer_core.pipeline import run_stages         # noqa: E402
from digitizer_core.warnings_codes import (            # noqa: E402
    PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
)

SAM2_ELIGIBLE = ("photo_subject", "photo_scene")


def run_once(image: str, points: int, mm: float, garment: str) -> dict:
    cfg = PipelineConfig(
        target_width_mm=mm,
        garment_id=garment,
        photo_segment_sam2=True,
        photo_segment_sam2_points_per_side=points,
    )
    t0 = time.perf_counter()
    res = run_stages(image, cfg)
    elapsed = time.perf_counter() - t0
    fell_back = any(
        w["code"] == PHOTO_SAM2_SEGMENTATION_UNAVAILABLE for w in res.warnings
    )
    return {
        "points": points,
        "seconds": elapsed,
        "regions": len(res.regions),
        "threads": len({r.thread_index for r in res.regions}),
        "design_class": res.design_class,
        # NOT `res.segmenter` — that is the stage-3 Segmenter's name and reads
        # "classical" on a successful SAM2 run, which is exactly backwards for
        # a reader checking whether SAM2 ran. The honest signal for THIS
        # question is the absence of the fallback warning.
        "fell_back": fell_back,
        "reason": next(
            (w.get("reason") or w.get("message") for w in res.warnings
             if w["code"] == PHOTO_SAM2_SEGMENTATION_UNAVAILABLE),
            None,
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--points", type=int, nargs="+", default=[16, 12])
    ap.add_argument("--mm", type=float, default=90.0)
    ap.add_argument("--garment", default="left_chest")
    args = ap.parse_args()

    if not Path(args.image).is_file():
        print(f"no such image: {args.image}", file=sys.stderr)
        return 2

    print(f"image   : {args.image}")
    print(f"config  : {args.mm}mm / {args.garment} / photo_segment_sam2=True")
    print()
    print(f"{'points':>7} {'seconds':>9} {'regions':>8} {'threads':>8} "
          f"{'class':<14} {'SAM2 ran':>9}")

    rows = []
    for pts in args.points:
        r = run_once(args.image, pts, args.mm, args.garment)
        rows.append(r)
        print(f"{r['points']:>7} {r['seconds']:>9.1f} {r['regions']:>8} "
              f"{r['threads']:>8} {r['design_class']:<14} "
              f"{'NO - fell back' if r['fell_back'] else 'yes':>9}")
        if r["reason"]:
            print(f"        fallback reason: {r['reason']}")

    print()
    ineligible = [r for r in rows if r["design_class"] not in SAM2_ELIGIBLE]
    if ineligible:
        print("INCONCLUSIVE — this image classifies as "
              f"{ineligible[0]['design_class']!r}, and SAM2 only engages for "
              f"{'/'.join(SAM2_ELIGIBLE)}. `points_per_side` never ran; the "
              "numbers above are the classical segmenter at two settings that "
              "did nothing. Re-run with a photo that classifies as a photo, or "
              "the classifier itself is what needs looking at.")
        return 1
    if any(r["fell_back"] for r in rows):
        print("INCONCLUSIVE — SAM2 was unavailable and the run silently used "
              "the classical segmenter. Build the isolated venv and prewarm the "
              "checkpoint (digitizer/sam2_isolated/README.md steps 1-4), then "
              "re-run. Comparing fallback output at two points_per_side values "
              "measures nothing.")
        return 1

    base, *rest = rows
    print(f"baseline points_per_side={base['points']}: "
          f"{base['seconds']:.1f}s, {base['regions']} regions")
    for r in rest:
        ds = 100.0 * (r["seconds"] - base["seconds"]) / base["seconds"]
        dr = r["regions"] - base["regions"]
        print(f"  vs {r['points']}: {ds:+.1f}% wall clock, {dr:+d} regions "
              f"({r['regions']} vs {base['regions']})")
    print()
    print("Wall clock on this box has been measured to vary by ~15% run to run "
          "(51.3s vs 59.7s for one identical config, MASTER_SCOPE.md), so treat "
          "a timing delta under that as noise. The region count is the "
          "deterministic signal - that is what killed the max_side_px 1024->512 "
          "proposal (25 -> 20 regions, reproducibly).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
