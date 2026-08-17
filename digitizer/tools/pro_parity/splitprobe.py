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
from shapely.geometry import Point
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scorecard  # noqa: E402

# --- vendored from tools/pro_parity/gateprobe.py, commit 2729ea5 on
# claude/satin-gate-attribution (verified byte-identical there) ---
#
# This worktree (`claude/measurement-debt`) was cut from `d96f9ff`, which
# predates gateprobe.py's introduction entirely (`26ceaa3`, the same
# ribbon-promotion refactor that renamed `is_satin_candidate`'s
# implementation to `classify_ribbon`) — so gateprobe.py is not in this
# lane's ancestry and cannot be imported as a sibling module without also
# carrying engine-code dependencies (`classify_ribbon`, `build_shape_field`)
# this worktree's `digitizer_core` doesn't have yet. A whole-file copy would
# fork gateprobe.py's own history across lanes; TYPE_NAMES and _cells_of are
# the only two names splitprobe actually needs, and both are unchanged since
# before that refactor (scorecard.py, which _cells_of depends on, is
# byte-identical between `d96f9ff` and current main), so they are inlined
# here verbatim instead. See task-5-report.md for the full trace.
TYPE_NAMES = {0: "run", 1: "satin", 2: "fill"}


def _cells_of(poly, bb, pt_shape) -> list[tuple[int, int]]:
    """The 2 mm cells whose CENTRE falls inside the polygon.

    Centres rather than any-overlap: a cell's stitch-type reading is a
    property of what was sewn across the whole cell, so crediting a shape with
    a cell it only clips the corner of would attribute the pro's verdict about
    a NEIGHBOURING shape to this one.
    """
    x0, y0, _x1, _y1 = bb
    H, W = pt_shape
    px0, py0, px1, py1 = poly.bounds
    j0 = max(0, int((px0 - x0) / scorecard.CELL))
    j1 = min(W - 1, int((px1 - x0) / scorecard.CELL) + 1)
    i0 = max(0, int((py0 - y0) / scorecard.CELL))
    i1 = min(H - 1, int((py1 - y0) / scorecard.CELL) + 1)
    if j1 < j0 or i1 < i0:
        return []
    ready = prep(poly)
    out = []
    for i in range(i0, i1 + 1):
        cy = y0 + (i + 0.5) * scorecard.CELL
        for j in range(j0, j1 + 1):
            cx = x0 + (j + 0.5) * scorecard.CELL
            if ready.contains(Point(cx, cy)):
                out.append((i, j))
    return out
# --- end vendored block ---

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

    Uses the vendored `_cells_of` for the centre-in-polygon join; the only
    new step here is laying those cells out as a local 2-D grid for
    `classify_straddle`, with everything outside the region's cell footprint
    marked -1 the same way an ungraded pro cell already is in `pt`.
    """
    cells = _cells_of(translate(poly, dx, dy), bb, pt.shape)
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
