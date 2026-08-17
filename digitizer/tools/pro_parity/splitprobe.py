#!/usr/bin/env python
"""What KIND of satin/fill straddling caps the oracle at 76.6%?

48.1% of graded cells sit in shapes under 75% one pro type (attribution doc
§4). The dominant straddle PATTERN decides the fix: `ring` (pro satins a
border around a fill body) is solved by border-satin generation on our
existing regions; `split` needs region splitting at an artwork boundary;
`speckle` is cell-scale noise no region change can chase. Instrument, not
engine code — same join as gateprobe.py.

Usage: splitprobe.py [--csv out.csv] <prepped-design-dir>...
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely.wkt
from shapely.affinity import translate

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scorecard  # noqa: E402

# This worktree (`claude/measurement-debt`, cut from `d96f9ff`) predates the
# ribbon-promotion refactor (`26ceaa3`) that renamed `is_satin_candidate`'s
# implementation to `classify_ribbon` in `digitizer_core/stage6_satin.py`.
# `gateprobe.py` imports that name at module scope even though splitprobe
# never calls it (splitprobe only reuses `_cells_of`/`TYPE_NAMES`, which are
# unchanged since before that refactor). A no-op stub satisfies the import
# without touching engine code or backdating this worktree's history — see
# task-5-report.md for the full trace.
import digitizer_core.stage6_satin as _stage6_satin  # noqa: E402

if not hasattr(_stage6_satin, "classify_ribbon"):
    _stage6_satin.classify_ribbon = None

import gateprobe  # noqa: E402

PURITY = 0.75           # attribution doc §4's own threshold; strictly-greater,
                        # so a shape at exactly 75% one type still counts as
                        # straddled (matches "under 75% one type" being the
                        # straddle population)
RING_SHARE = 0.8        # ring = border band dominated by one type AND interior
                        # dominated by a DIFFERENT type, each at ≥ this share.
                        # Both bands must be decisive: a side-by-side split also
                        # puts its minority partly on the border, but never
                        # dominates BOTH bands with different types.
SPLIT_COMPONENTS_MAX = 2  # a clean partition is 1-2 blobs per type, not many


def classify_straddle(grid: np.ndarray) -> str:
    """Classify one shape's pro-type cell grid.

    `grid`: int cells, -1 outside the shape, else scorecard type codes
    (0 run, 1 satin, 2 fill). Returns "pure" | "ring" | "split" | "speckle".
    """
    inside = grid >= 0
    vals, counts = np.unique(grid[inside], return_counts=True)
    if len(vals) == 0:
        return "pure"
    if counts.max() / counts.sum() > PURITY:
        return "pure"

    # Border band: inside cells with an outside/edge 4-neighbour.
    pad = np.pad(inside, 1, constant_values=False)
    interior = (pad[:-2, 1:-1] & pad[2:, 1:-1]
                & pad[1:-1, :-2] & pad[1:-1, 2:]) & inside
    border = inside & ~interior
    # Ring: the border band belongs to one type, the interior to another —
    # "pro satins the outline and fills the body". Judged on band dominance,
    # NOT on where the minority sits: the ring type can be the MAJORITY of
    # the whole shape (a 5x5 shape with a satin ring is 16 satin / 9 fill).
    if border.any() and interior.any():
        bvals, bcounts = np.unique(grid[border], return_counts=True)
        ivals, icounts = np.unique(grid[interior], return_counts=True)
        b_dom = bvals[np.argmax(bcounts)]
        i_dom = ivals[np.argmax(icounts)]
        if (b_dom != i_dom
                and bcounts.max() / bcounts.sum() >= RING_SHARE
                and icounts.max() / icounts.sum() >= RING_SHARE):
            return "ring"

    # Split: each present type forms few connected components.
    try:
        from scipy.ndimage import label
    except ImportError:
        return "speckle"  # scipy is in the digitizer venv; bare env degrades
    for v in vals:
        _, n = label((grid == v) & inside)
        if n > SPLIT_COMPONENTS_MAX:
            return "speckle"
    return "split"


def _shape_grid(poly, dx: float, dy: float, bb, pt: np.ndarray) -> np.ndarray:
    """The pro type map, cropped to this region's own cell bounding box.

    Reuses gateprobe's `_cells_of` verbatim for the centre-in-polygon join;
    the only new step here is laying those cells out as a local 2-D grid for
    `classify_straddle`, with everything outside the region's cell footprint
    marked -1 the same way an ungraded pro cell already is in `pt`.
    """
    cells = gateprobe._cells_of(translate(poly, dx, dy), bb, pt.shape)
    if not cells:
        return np.empty((0, 0), dtype=int)
    i0 = min(i for i, _j in cells)
    i1 = max(i for i, _j in cells)
    j0 = min(j for _i, j in cells)
    j1 = max(j for _i, j in cells)
    grid = np.full((i1 - i0 + 1, j1 - j0 + 1), -1, dtype=int)
    for i, j in cells:
        grid[i - i0, j - j0] = pt[i, j]
    return grid


def probe_design(dirpath: Path) -> list[dict]:
    slug = dirpath.name
    regions_path = dirpath / "ours_regions.json"
    if not regions_path.exists():
        print(f"  {slug}: no ours_regions.json — prepped before 2026-08-16?")
        return []
    regions = json.loads(regions_path.read_text())
    if not regions or "wkt" not in regions[0]:
        print(f"  {slug}: ours_regions.json carries no `wkt` — re-prep needed")
        return []

    _pro_rows, pro, _psrc, _pt = scorecard.load_side(dirpath, "pro", slug)
    _our_rows, our, _osrc, _ot = scorecard.load_side(dirpath, "ours", slug)
    dx, dy, _iou = scorecard.register(pro, our, scorecard.bounds(pro, our))
    our_r = scorecard.shifted(our, dx, dy)
    bb = scorecard.bounds(pro, our_r)
    _pa, pt, _ptot = scorecard.cell_stats(pro, bb)

    rows = []
    for r in regions:
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        grid = _shape_grid(poly, dx, dy, bb, pt)
        inside = grid >= 0
        cells = int(inside.sum())
        if cells:
            vals, counts = np.unique(grid[inside], return_counts=True)
            purity = float(counts.max() / counts.sum())
        else:
            purity = None
        rows.append({
            "design": slug,
            "shape_id": r["shape_id"],
            "area_mm2": r["area_mm2"],
            "cells": cells,
            "purity": round(purity, 4) if purity is not None else None,
            "pattern": classify_straddle(grid),
        })
    return rows


def summarise(rows: list[dict]) -> None:
    graded = [r for r in rows if r["cells"] > 0]
    total_cells = sum(r["cells"] for r in graded)
    print(f"\n{len(rows)} shapes across "
          f"{len({r['design'] for r in rows})} designs; "
          f"{len(graded)} graded (land on ground the pro also sewed), "
          f"{total_cells} graded cells.\n")

    by_pattern: dict = defaultdict(lambda: {"shapes": 0, "cells": 0})
    for r in graded:
        g = by_pattern[r["pattern"]]
        g["shapes"] += 1
        g["cells"] += r["cells"]

    print(f"{'pattern':<10}{'shapes':>8}{'cells':>10}{'headroom':>11}")
    for pattern in ("ring", "split", "speckle", "pure"):
        g = by_pattern.get(pattern, {"shapes": 0, "cells": 0})
        share = f"{100.0 * g['cells'] / total_cells:.1f}%" if total_cells else "—"
        print(f"{pattern:<10}{g['shapes']:>8}{g['cells']:>10}{share:>11}")

    straddle_cells = sum(g["cells"] for p, g in by_pattern.items() if p != "pure")
    print(f"\nSTRADDLED (ring+split+speckle): {straddle_cells} of {total_cells} "
          f"graded cells ({100.0 * straddle_cells / total_cells:.1f}%)"
          if total_cells else "\nSTRADDLED: no graded cells")

    if by_pattern:
        dominant = max(by_pattern.items(), key=lambda kv: kv[1]["cells"])
        print(f"\nDOMINANT PATTERN (by cells): {dominant[0]} "
              f"({dominant[1]['cells']} cells, "
              f"{100.0 * dominant[1]['cells'] / total_cells:.1f}% of graded)"
              if total_cells else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dirs", nargs="+", help="prepped design directories")
    ap.add_argument("--csv", help="write the per-shape table here")
    args = ap.parse_args()

    rows: list[dict] = []
    for d in args.dirs:
        p = Path(d)
        if not (p / "ours_stitches.csv").exists():
            continue
        print(f"probing {p.name} ...", flush=True)
        try:
            rows.extend(probe_design(p))
        except Exception as exc:                      # noqa: BLE001
            print(f"  {p.name}: FAILED — {type(exc).__name__}: {exc}")

    if not rows:
        print("nothing probed")
        return
    if args.csv:
        keys = list(rows[0].keys())
        with open(args.csv, "w", newline="") as f:
            f.write(",".join(keys) + "\n")
            for r in rows:
                f.write(",".join("" if r[k] is None else str(r[k])
                                 for k in keys) + "\n")
        print(f"wrote {args.csv} ({len(rows)} shapes)")
    summarise(rows)


if __name__ == "__main__":
    main()
