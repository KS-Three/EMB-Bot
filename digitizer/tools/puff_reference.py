#!/usr/bin/env python
"""Measure a professionally digitized puff (3D foam) stitch file.

MEASUREMENT ONLY. Reads one PES/DST through pystitch (as `pro_pair.pro_counts`
does) and reports the numbers the 3D-puff constants should be replaced by:

  blocks            per colour block: {stitches, trims}
  satin_spacing_mm  median along-spine row gap of the puff block (the block
                    with the most stitches). Taken as the chord over a window
                    of 10 rows divided by 9, so DST/PES 0.1 mm rounding of
                    single stitches does not swamp a 0.18 mm gap.
  underlay          True when the puff block holds a run of >= 6 long, collinear
                    stitches (a travel/underlay pass); a satin zigzag reverses
                    direction every stitch and never qualifies.
  tie_stitches      median count of tiny (< 1 mm) stitches at run starts
  cap_rows          median count of narrow rows (< 50% of the run's median
                    width) at the two ends of each run: the column cap
  column_width_mm   (min, max) cross-stitch length of the puff block

    python -m tools.puff_reference "<path to .PES or .DST>"
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

SATIN_MIN_MM = 1.0       # a stitch at least this long crosses a column
TIE_MAX_MM = 1.0         # a stitch shorter than this is a tie / lock
WINDOW = 10              # rows per spacing window
UNDERLAY_MIN_STITCH_MM = 1.5
UNDERLAY_MIN_RUN = 6


def _split(pat):
    """-> (blocks, runs_per_block). Coordinates in mm; a run is the STITCH
    records between TRIM/JUMP/COLOR_CHANGE; a block ends on COLOR_CHANGE."""
    import pystitch
    m = pystitch.COMMAND_MASK
    blocks = [{"stitches": 0, "trims": 0}]
    runs = [[[]]]
    for x, y, c in pat.stitches:
        c &= m
        if c == pystitch.STITCH:
            blocks[-1]["stitches"] += 1
            runs[-1][-1].append((x / 10.0, y / 10.0))
        elif c in (pystitch.TRIM, pystitch.JUMP):
            if c == pystitch.TRIM:
                blocks[-1]["trims"] += 1
            if runs[-1][-1]:
                runs[-1].append([])
        elif c == pystitch.COLOR_CHANGE:
            blocks.append({"stitches": 0, "trims": 0})
            runs.append([[]])
    keep = [i for i, b in enumerate(blocks) if b["stitches"] or b["trims"]]
    return ([blocks[i] for i in keep],
            [[r for r in runs[i] if r] for i in keep])


def _len(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _median(v):
    return float(statistics.median(v)) if v else None


def measure_pattern(pat) -> dict:
    blocks, runs = _split(pat)
    if not blocks:
        raise SystemExit("no stitches")
    puff = max(range(len(blocks)), key=lambda i: blocks[i]["stitches"])

    widths, mids, caps, underlay = [], [], [], False
    for run in runs[puff]:
        segs = [(run[i], run[i + 1]) for i in range(len(run) - 1)]
        lens = [_len(a, b) for a, b in segs]
        sat = [(s, l) for s, l in zip(segs, lens) if l >= SATIN_MIN_MM]
        widths += [l for _, l in sat]
        rowmids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for (a, b), _ in sat]
        mids.append(rowmids)
        if sat:
            med = statistics.median(l for _, l in sat)
            narrow = [l < 0.5 * med for _, l in sat]
            lead = next((i for i, n in enumerate(narrow) if not n), len(narrow))
            trail = next((i for i, n in enumerate(reversed(narrow)) if not n), len(narrow))
            caps.append(lead + trail)
        # underlay: long stitches that keep going the same way
        streak = 1
        for i in range(1, len(segs)):
            (a, b), (c, d) = segs[i - 1], segs[i]
            l1, l2 = lens[i - 1], lens[i]
            ok = (l1 >= UNDERLAY_MIN_STITCH_MM and l2 >= UNDERLAY_MIN_STITCH_MM and
                  ((b[0] - a[0]) * (d[0] - c[0]) + (b[1] - a[1]) * (d[1] - c[1])) / (l1 * l2) > 0.9)
            streak = streak + 1 if ok else 1
            if streak + 1 >= UNDERLAY_MIN_RUN:
                underlay = True

    gaps = []
    for rm in mids:
        for i in range(0, len(rm) - WINDOW + 1):
            gaps.append(_len(rm[i], rm[i + WINDOW - 1]) / (WINDOW - 1))

    ties = []
    for blk in runs:
        for run in blk:
            n = 0
            for i in range(len(run) - 1):
                if _len(run[i], run[i + 1]) < TIE_MAX_MM:
                    n += 1
                else:
                    break
            ties.append(n)

    return {
        "blocks": blocks,
        "puff_block": puff,
        "satin_spacing_mm": _median(gaps),
        "underlay": underlay,
        "tie_stitches": _median(ties),
        "cap_rows": _median(caps),
        "column_width_mm": (min(widths), max(widths)) if widths else None,
    }


def measure_puff_reference(path: Path) -> dict:
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    return measure_pattern(pat)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    print(json.dumps(measure_puff_reference(Path(argv[0])), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
