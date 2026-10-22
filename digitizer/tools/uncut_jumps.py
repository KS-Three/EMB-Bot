"""uncut_jumps: every needle-up move in a DST, cut or uncut, by hop length.

    python -m tools.uncut_jumps FILE.dst [FILE.dst ...] [--json]

Reads the RAW DST records, so both sides are judged by the record stream a
machine sees, not by a reader's guess. A move is the maximal run of
non-stitch records between two needle penetrations:

  colour   it holds a colour change: a machine stop, counted apart.
  cut      three or more JUMP records: DST has no trim record, and a machine
           (and `pystitch`'s own DST writer and reader) reads three or more
           consecutive jumps as a trim.
  uncut    one or two JUMP records: the needle lifts and moves, the thread
           is NOT cut. A float the operator scissors off, or a loop.

Bins are the hop's straight length, last penetration to first. Read the
DST, never the PES (its reader reports a TRIM at every jump).

Measured with it 2026-10-21 for `cfg.trim_every_jump`
(`docs/trim-every-jump-2026-10-21.md`).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

BINS = (0.5, 1.0, 2.0, 3.0, 6.0, 12.1)
CUT_RECORDS = 3


def _bin_label(d: float) -> str:
    lo = 0.0
    for hi in BINS:
        if d < hi:
            return f"{lo:g}-{hi:g}"
        lo = hi
    return f">={lo:g}"


LABELS = tuple(_bin_label(b - 1e-9) for b in BINS) + (_bin_label(1e9),)


def moves(path) -> list[dict]:
    """One row per needle-up move: kind, hop length (mm), jump records.

    Decodes the 3-byte records itself: `pystitch.read` folds a run of
    consecutive jump records into one JUMP, which hides the record count a
    machine reads a trim from."""
    from pystitch.DstReader import decode_dx, decode_dy
    data = Path(path).read_bytes()[512:]
    out: list[dict] = []
    x = y = 0
    last = None            # last penetration, 0.1 mm units
    jumps = 0
    colour = False
    for i in range(0, len(data) - 2, 3):
        b0, b1, b2 = data[i], data[i + 1], data[i + 2]
        if b2 & 0b11110011 == 0b11110011:          # end of design
            break
        x += decode_dx(b0, b1, b2)
        y += decode_dy(b0, b1, b2)
        if b2 & 0b11000011 == 0b11000011:          # colour change / stop
            colour = True
        elif b2 & 0b10000011 == 0b10000011:        # jump
            jumps += 1
        else:                                      # needle penetration
            if last is not None and (jumps or colour):
                d = math.dist(last, (x, y)) / 10.0
                kind = "colour" if colour else ("cut" if jumps >= CUT_RECORDS else "uncut")
                out.append({"kind": kind, "mm": round(d, 3), "records": jumps})
            last = (x, y)
            jumps = 0
            colour = False
    return out


def summary(path) -> dict:
    rows = moves(path)
    uncut = {lab: 0 for lab in LABELS}
    for r in rows:
        if r["kind"] == "uncut":
            uncut[_bin_label(r["mm"])] += 1
    cut = [r["mm"] for r in rows if r["kind"] == "cut"]
    return {
        "file": str(path),
        "cuts": len(cut),
        "uncut": sum(uncut.values()),
        "colour": sum(1 for r in rows if r["kind"] == "colour"),
        "shortest_cut_mm": round(min(cut), 2) if cut else None,
        "uncut_by_mm": uncut,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = [summary(f) for f in a.files]
    if a.json:
        print(json.dumps(rows, indent=1))
        return 0
    print("cuts uncut colour short  " + " ".join(f"{lab:>7}" for lab in LABELS) + "  file")
    for s in rows:
        sc = "-" if s["shortest_cut_mm"] is None else f"{s['shortest_cut_mm']:.2f}"
        print(f"{s['cuts']:4d} {s['uncut']:5d} {s['colour']:6d} {sc:>5}  "
              + " ".join(f"{s['uncut_by_mm'][lab]:7d}" for lab in LABELS) + f"  {s['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
