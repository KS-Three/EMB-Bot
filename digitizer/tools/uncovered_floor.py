#!/usr/bin/env python
"""Adjudicate `_UNCOVERED_MIN_PATCH_MM2` — the floor its own comment calls
PROVISIONAL.

`preflight._UNCOVERED_MIN_PATCH_MM2` has been 5.0 mm² since 2026-08-20, and
the constant's comment says exactly what is wrong with it: the clean
population sat at 0.00–0.25 mm², the two known defects at 7.75 and 44.50, and
*"the middle of the table is unadjudicated"* — nobody had looked at whether a
3–5 mm² patch is a real drop. It asks for a wider fixture set and an
adjudication before the number is trusted.

This is that instrument. Per fixture it digitizes once and reports, off ONE
`run_preflight`:

  * `uncovered_worst_mm2` — threshold-free, the largest connected patch of
    artwork a sewn shape claims and no thread reaches;
  * `uncovered_top_mm2` — the largest patches, so the shoulder is visible;
  * how many patches clear each candidate floor, and whether
    `ARTWORK_UNCOVERED` fires at the shipped 5.0.

**The measure is already all-thread.** `_coverage_map` rasterises every
needle-down stitch in the plan — underlay, run, travel and fill included — so
unlike `tools/bare_anatomy.py`'s default this is the cloth reading, and a
patch here is cloth a customer could see. That is why the two disagree, and
why this is the right instrument to set a customer-facing floor on.

    .venv/bin/python tools/uncovered_floor.py --corpus
    .venv/bin/python tools/uncovered_floor.py --legacy    # the 08-20 table
    .venv/bin/python tools/uncovered_floor.py enthusiast --width 150
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.preflight import (ARTWORK_UNCOVERED,  # noqa: E402
                                      _UNCOVERED_MIN_PATCH_MM2, run_preflight)
from tools._console import utf8_console  # noqa: E402
from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

# The ladder the floor is chosen from. 5.0 is the shipped value; 1.0 is
# `dropped_elements.MIN_ELEMENT_MM2`, the sibling threshold that also missed
# ENTHUSIAST's apex (0.97 mm²) on 2026-09-30.
FLOORS = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)

# The fixtures the 2026-08-20 table was built on, at its own widths, so the
# rows that set the current floor can be re-read rather than quoted.
LEGACY = (
    ("logo_whitebg", "logo_whitebg.png", 80.0),
    ("gaulke", "logo_gaulke_roofing.png", 90.0),
    ("ribbon_curve", "ribbon_curve.png", 60.0),
    ("logo_alpha", "logo_alpha.png", 80.0),
    ("enthusiast", "photo/enthusiast_logo.png", 80.0),
    ("thermal", "photo/logo_drone_thermal_badge.png", 90.0),
    ("enthusiast120", "photo/enthusiast_logo.png", 120.0),
    ("tires", "logo_script_tires.png", 90.0),
    ("enthusiast150", "photo/enthusiast_logo.png", 150.0),
    ("becker", "becker_marine_logo.png", 90.0),
)


def measure(path: Path, width_mm: float, garment: str = "left_chest") -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS)
    result, plan = digitize(path, cfg)
    report = run_preflight(result, plan, cfg, image=path)
    m = report["metrics"]
    fired = any(f["code"] == ARTWORK_UNCOVERED for f in report["findings"])
    return dict(worst=m["uncovered_worst_mm2"], top=m["uncovered_top_mm2"] or [],
                n=m["uncovered_patches"], wanted=m["uncovered_wanted_mm2"],
                holes=m["uncovered_holes"], hole=m["uncovered_hole_mm2"],
                fired=fired, stitches=plan.stats.stitch_count)


def row(name: str, d: dict) -> str:
    # How many of the listed patches clear each floor. The list is capped, so
    # a count that saturates it is printed with a `+`.
    top, n = d["top"], d["n"] or 0
    counts = []
    for f in FLOORS:
        c = sum(1 for a in top if a >= f)
        counts.append(f"{c}{'+' if c == len(top) < n else '':<1}")
    shown = " ".join(f"{a:5.2f}" for a in top[:6])
    return (f"{name:<14s} worst={d['worst'] or 0:6.2f}  n={n:>4d}  "
            f"holes={d['holes'] or 0:>3d} @{d['hole'] or 0:5.2f}  "
            f"fires={'YES' if d['fired'] else ' no'}  "
            f"|{' '.join(f'{c:>3s}' for c in counts)}|  top: {shown}")


def main(argv: list[str] | None = None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description="Adjudicate the uncovered floor.")
    ap.add_argument("cases", nargs="*", help="tools.thin_strokes.REAL_ART names")
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--legacy", action="store_true",
                    help="the fixtures the 2026-08-20 floor was set on")
    ap.add_argument("--width", type=float, default=None)
    a = ap.parse_args(argv)

    jobs: list[tuple[str, Path, float, str]] = []
    if a.corpus:
        jobs += [(n, p, a.width or w, g) for n, p, w, g in corpus_cases(ROOT)]
    if a.legacy:
        jobs += [(n, ROOT / "testdata" / rel, a.width or w, "left_chest")
                 for n, rel, w in LEGACY]
    for n in a.cases:
        rel, w, g = REAL_ART[n]
        jobs.append((n, ROOT / "testdata" / rel, a.width or w, g))
    if not jobs:
        ap.error("give a case, --corpus or --legacy")

    print(f"shipped floor {_UNCOVERED_MIN_PATCH_MM2} mm2; "
          f"patches at or over each of {FLOORS} mm2 in the columns.")
    print(f"{'':14s} {'':13s}{'':7s}{'':11s} |"
          + " ".join(f"{f:>3g}" for f in FLOORS) + "|")
    for name, path, w, g in jobs:
        print(row(f"{name} {w:g}", measure(Path(path), w, g)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
