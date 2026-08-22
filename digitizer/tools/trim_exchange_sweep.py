#!/usr/bin/env python
"""Trims against stitches, per fixture — the instrument the goldens cannot be.

Built 2026-08-21 for the path-order selector in `stage6_fill`
(`_reorder_for_fewer_cuts`), and kept because **nothing else measures this class
of change.** Both byte-identical goldens were measured accepting the reorder on
ZERO shapes (`photo/enthusiast_logo.png`, `logo_whitebg.png`), so a green suite
says nothing whatever about a stitch-ordering or travel change. That is not a
gap to route around once — it is why this file exists.

Prints one row per fixture: trims and stitch count. Run it before a change and
after, diff the two, and you have the exchange rate the change actually costs.

    .venv/bin/python tools/trim_exchange_sweep.py BEFORE > before.tsv
    # ...make the change...
    .venv/bin/python tools/trim_exchange_sweep.py AFTER  > after.tsv
    .venv/bin/python tools/trim_exchange_sweep.py --diff before.tsv after.tsv

(`.venv/Scripts/python` on Windows.)

REFERENCE POINT, `_reorder_for_fewer_cuts` at 25 stitches/trim, all 23 committed
photo fixtures, `max_colors=6` (2026-08-21):

    +143 trims removed, +783 stitches, 5.5 st/trim
    11 designs improved, 12 unchanged, 0 worse on cuts*25 + stitches

Read `--diff`'s `score` column as `Δstitches - Δtrims * 25`: negative is better.
A POSITIVE score on any design breaks Kent's per-design never-worse rule
(2026-08-21) and is a defect, not a trade-off — that rule is what the selector's
last-path pin and its combined-cost comparison exist to guarantee.

**Two traps this tool was built out of, both of which produced confident wrong
answers before being caught by measurement:**

- Estimating travel as `length / TRAVEL_STITCH_MM` undercounts by ~2.5x, because
  `travel_path` densifies each leg of a ring route separately. Count emitted
  POINTS. This silently let a design regress through a cap that was working.
- Config matters more than it looks. `logo_hotel_fremont.webp` reads 46 holes /
  280 fill runs at 92.5 mm/patch and 44 / 247 at the default 80 mm. Never quote
  numbers from two different configs as one measurement.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402

TRIM_STITCH_EQUIVALENT = 25.0


def sweep(tag: str, max_colors: int, width_mm: float | None) -> None:
    pats = ("testdata/photo/*.png", "testdata/photo/*.webp", "testdata/photo/*.jpg")
    for f in sorted(p for pat in pats for p in glob.glob(str(ROOT / pat))):
        name = os.path.basename(f)
        kw = {"max_colors": max_colors}
        if width_mm is not None:
            kw["target_width_mm"] = width_mm
        try:
            t = time.time()
            _result, plan = digitize(f, PipelineConfig(**kw))
            print(f"{tag}\t{name}\t{plan.stats.trims}\t{plan.stats.stitch_count}"
                  f"\t{time.time() - t:.1f}")
        except Exception as exc:                       # a fixture that will not run
            print(f"{tag}\t{name}\tERR\t{type(exc).__name__}\t0")
        sys.stdout.flush()


def _load(path: str) -> dict[str, tuple[int, int]]:
    out = {}
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 4 and f[2].isdigit():
            out[f[1]] = (int(f[2]), int(f[3]))
    return out


def diff(before_path: str, after_path: str) -> int:
    before, after = _load(before_path), _load(after_path)
    shared = sorted(set(before) & set(after))
    if not shared:
        print("no fixtures in common", file=sys.stderr)
        return 2
    print(f"{'fixture':<34}{'Δtrim':>7}{'Δstitch':>9}{'st/trim':>9}{'score':>8}")
    worse, tot_t, tot_s = [], 0, 0
    for k in shared:
        dt = before[k][0] - after[k][0]
        ds = after[k][1] - before[k][1]
        if not dt and not ds:
            continue
        score = ds - dt * TRIM_STITCH_EQUIVALENT
        tot_t += dt
        tot_s += ds
        if score > 0:
            worse.append(k)
        rate = f"{ds / dt:.1f}" if dt > 0 else "-"
        print(f"{k:<34}{dt:>+7}{ds:>+9}{rate:>9}{score:>+8.0f}")
    rate = f"{tot_s / tot_t:.1f}" if tot_t > 0 else "-"
    print(f"\nTOTAL: {tot_t:+d} trims, {tot_s:+d} stitches, {rate} st/trim")
    if worse:
        print(f"\n{len(worse)} DESIGN(S) WORSE on cuts*{TRIM_STITCH_EQUIVALENT:.0f} "
              f"+ stitches — this breaks per-design never-worse:")
        for k in worse:
            print(f"    {k}")
        return 1
    print("0 designs worse — per-design never-worse holds")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag", nargs="?", default="RUN",
                    help="label for this run's rows (e.g. BEFORE / AFTER)")
    ap.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"),
                    help="compare two saved runs instead of sweeping")
    ap.add_argument("--max-colors", type=int, default=6)
    ap.add_argument("--width-mm", type=float, default=None,
                    help="override target_width_mm; default leaves the config default")
    args = ap.parse_args()
    if args.diff:
        raise SystemExit(diff(*args.diff))
    sweep(args.tag, args.max_colors, args.width_mm)


if __name__ == "__main__":
    main()
