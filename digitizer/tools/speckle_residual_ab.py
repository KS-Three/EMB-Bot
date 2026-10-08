#!/usr/bin/env python
"""A/B `cfg.blend_speckle_residual` on real photos: verdict tally + renders.

The flag swaps the blend tier's speckle measure from raw-tone local variance
to the fit's stitch-scale residual (`stage6_blend._residual_speckle_ratio`;
the second candidate in `docs/tonal-eng-measurements-2026-08-22.md` §1). It
only matters where the blend tier runs — the DEFAULT route, which stage 0
sends real photos down as `gradient` — so this runs the default config and
flips only the flag. Per photo it prints the ramp verdicts each arm reached
(counted at `detect_ramp_detail`, the decision itself) and the plan's colour
blocks and stitch count, and draws OFF beside ON in thread colours with
`thread_color_render._panel`, so the change goes to the eye, not a score.

  .venv/bin/python tools/speckle_residual_ab.py photo/owl_kent.jpg \\
      photo/drone_render.png --out docs/renders/speckle-residual-2026-10-08
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, stage6_blend            # noqa: E402
from digitizer_core.pipeline import digitize                       # noqa: E402
from thread_color_render import TESTDATA, _panel                   # noqa: E402


def _arm(art: Path, width_mm: float, on: bool):
    tally: Counter = Counter()
    real = stage6_blend.detect_ramp_detail

    def counted(*a, **k):
        out = real(*a, **k)
        tally[out[1] or "ACCEPT"] += 1
        return out

    stage6_blend.detect_ramp_detail = counted
    try:
        cfg = PipelineConfig(target_width_mm=width_mm,
                             blend_speckle_residual=on)
        result, plan = digitize(art, cfg)
    finally:
        stage6_blend.detect_ramp_detail = real
    return cfg, result, plan, tally


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="+", help="paths under digitizer/testdata/")
    ap.add_argument("--width", type=float, default=100.0)
    ap.add_argument("--out", type=Path, default=Path("/tmp"))
    ap.add_argument("--px-per-mm", type=float, default=8.0)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for fixture in a.fixtures:
        art = TESTDATA / fixture
        arms = [_arm(art, a.width, on) for on in (False, True)]
        pts = [pt for _b, r in arms[0][2].iter_runs() for pt in r.points]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        bounds = (min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3)
        panels = []
        for tag, (cfg, res, plan, tally) in zip(("OFF", "ON"), arms):
            blocks = len(plan.blocks)
            stitches = sum(len(r.points) for _b, r in plan.iter_runs())
            verdicts = " ".join(f"{k}={v}" for k, v in sorted(tally.items()))
            print(f"{fixture} {tag:>3}: class={res.design_class} "
                  f"blocks={blocks} stitches={stitches} ramp[{verdicts}]")
            panels.append(_panel(art, cfg, res, plan, bounds, a.px_per_mm, {},
                                 f"{Path(fixture).stem} blend_speckle_residual="
                                 f"{tag}  blocks={blocks}  "
                                 f"accept={tally.get('ACCEPT', 0)}"))
        path = a.out / f"{Path(fixture).stem}_{a.width:g}mm_off_on.png"
        cv2.imwrite(str(path), np.hstack(panels))
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
