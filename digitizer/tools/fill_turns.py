"""fill_turns: how a machine file's fill rows turn into the next row.

    python -m tools.fill_turns FILE [FILE ...] [--json]

Reads any file `pystitch` reads, in its own frame (no registration), so the
pro's DST and our `ours.dst` (`tools/pro_pair.py`) are read the same way.

A TURN is a needle-down stitch T of at most 1.6 mm between two row stitches
A (before) and C (after) that run antiparallel (cos < -0.99), each at least
1.0 mm and each continuing a straight row (the stitch before A is parallel
to A, the one after C to C, cos > 0.99). T is split ALONG A (the row) and
ACROSS it (the row spacing). `short_turns` is the looser count the settings
audit used for "how many of our sub-0.5 mm stitches are turns": any T under
0.5 mm whose neighbours are >= 0.6 mm, >= 2x T and antiparallel (cos < -0.95).

Measured 2026-10-21 on the pro's Fremont (patch, hat), Becker (large, small),
Drone and MFab DSTs: turn length p50 0.71-0.82 mm, p10 0.41, along the row
p50 0.63-0.78, across p50 0.10-0.15. `machine.FILL_TURN_ALONG_MM` comes
from it; `docs/fill-turn-slant-2026-10-21.md` has both sides.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _segments(path) -> list[np.ndarray]:
    """Needle-down polylines (mm): a JUMP starts a new one from its landing
    point, any other command ends the current one."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    out, seg = [], []
    for x, y, c in pat.stitches:
        c &= m
        if c == pystitch.STITCH:
            seg.append((x / 10.0, y / 10.0))
            continue
        if len(seg) > 1:
            out.append(np.array(seg))
        seg = [(x / 10.0, y / 10.0)] if c == pystitch.JUMP else []
    if len(seg) > 1:
        out.append(np.array(seg))
    return out


def _pct(v, k):
    return round(float(np.percentile(v, k)), 3) if len(v) else None


def measure(path) -> dict:
    lens, turns, short_turns = [], [], 0
    for p in _segments(path):
        d = np.diff(p, axis=0)
        L = np.hypot(d[:, 0], d[:, 1])
        lens.extend(L[L > 1e-9].tolist())
        for i in range(1, len(d) - 1):
            lt = L[i]
            if lt < 1e-9:
                continue
            la, lc = L[i - 1], L[i + 1]
            if (lt < 0.5 and la >= 0.6 and lc >= 0.6 and 2 * lt <= min(la, lc)
                    and np.dot(d[i - 1], d[i + 1]) / (la * lc) < -0.95):
                short_turns += 1
            if i < 2 or i > len(d) - 3 or lt > 1.6:
                continue
            l0, l1 = L[i - 2], L[i + 2]
            if min(l0, la, lc, l1) < 1.0:
                continue
            if (np.dot(d[i - 2], d[i - 1]) / (l0 * la) < 0.99
                    or np.dot(d[i + 1], d[i + 2]) / (lc * l1) < 0.99
                    or np.dot(d[i - 1], d[i + 1]) / (la * lc) > -0.99):
                continue
            u = d[i - 1] / la
            turns.append((lt, abs(float(np.dot(d[i], u))),
                          abs(float(u[0] * d[i][1] - u[1] * d[i][0]))))
    lens = np.array(lens)
    t = np.array(turns) if turns else np.zeros((0, 3))
    sub = int((lens < 0.5).sum())
    return {
        "file": Path(path).name,
        "stitches": int(len(lens)),
        "under_0_5": sub,
        "under_0_5_pct": round(100.0 * sub / max(1, len(lens)), 2),
        "p1_mm": _pct(lens, 1),
        "short_turns": short_turns,
        "short_turn_share_pct": round(100.0 * short_turns / max(1, sub), 1),
        "turns": int(len(t)),
        "turns_under_0_5": int((t[:, 0] < 0.5).sum()),
        "turn_mm_p10_p50_p90": [_pct(t[:, 0], k) for k in (10, 50, 90)],
        "along_mm_p10_p50_p90": [_pct(t[:, 1], k) for k in (10, 50, 90)],
        "across_mm_p50": _pct(t[:, 2], 50),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.fill_turns", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true", help="one JSON object per line")
    args = ap.parse_args(argv)
    for f in args.files:
        row = measure(f)
        if args.json:
            print(json.dumps(row))
            continue
        print(f"{row['file']}: {row['stitches']} stitches, {row['under_0_5']} under 0.5 mm "
              f"({row['under_0_5_pct']}%), {row['short_turns']} of them turns; "
              f"{row['turns']} row turns, length p10/p50/p90 {row['turn_mm_p10_p50_p90']}, "
              f"along p50 {row['along_mm_p10_p50_p90'][1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
