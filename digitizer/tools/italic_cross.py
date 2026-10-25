"""italic_cross: the angle of every satin cross against its OWN stroke, read off
a machine file -- one rule on the professional's DST and ours (2026-10-25,
`cfg.lettering_columns_italic_lean`, `digitizer_core/column_lean.py`).

WHY NOT `letter_pieces`' piece axis. On italic PROSEAL the pro sews most
letters as ONE piece of 170-200 crosses that walks the stem, the bowl and
the bars (drift over 110 deg), so a piece's principal axis is no stroke's
direction, and a "leaning share" binned by it (#1061: 0.27 -> 0.21 under
`text_lean`, his 0.31) counts a whole P by an axis it does not have. This
reads each cross against the stroke it sits on.

WHAT IT READS. `letter_pieces.read`'s pieces and letters. For each cross,
the LOCAL stroke axis is the principal direction of the cross midpoints
within HALF_MM of it along the piece's spine (MIN_CROSSES at least, over
MIN_SPAN_MM, midpoint residual RMS under STRAIGHT_MM -- a fan or a curve
gives no axis and the cross is not read). Then, y down, degrees:

  lean    the axis off the line of text's normal (+ = top to the right);
  cross   the stitch off the line of text (0 = along it, the stems' cross
          of upright text);
  square  the stitch off square-to-its-stroke (0 = square).

A cross is on a STEM when its axis is within 30 deg of upright, a BAR
within 30 deg of the line of text, a DIAGONAL between. The word's SLANT is
the median lean of its stem crosses; a bar cross is ALONG THE SLANT when it
lies within ALONG_DEG of the slant's direction.

  python -m tools.italic_cross FILE.dst [FILE.dst ...] [--ymin Y] [--ymax Y]
      [--hmin MM] [--hmax MM] [--json]

`--ymin/--ymax` keep letters whose centre lies between those y (mm, the
file's own frame), `--hmin/--hmax` their height -- e.g. PROSEAL on the
pro's hat file: `--ymin 12 --hmin 6 --hmax 12`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import letter_pieces as LP  # noqa: E402

HALF_MM = 0.9        # the local axis window, each way along the spine
MIN_CROSSES = 5
MIN_SPAN_MM = 1.2
STRAIGHT_MM = 0.12   # midpoint residual over which the window is a curve or a fan
STEM_DEG = 30.0      # axis within this of upright: a stem; of the line: a bar
ALONG_DEG = 8.0      # a bar cross this close to the slant runs along it
CLASSES = ("stem", "bar", "diag")


def fold(d: float) -> float:
    """An undirected angle difference on (-90, 90]."""
    return (d + 90.0) % 180.0 - 90.0


def crosses_of(letter: dict) -> list[dict]:
    """A `letter_pieces.read` letter -> its readable crosses:
    [{axis, lean, cross, square, cls, at, piece}]."""
    out = []
    for pi in sorted(set(letter["piece_of_cross"])):
        cr = [c for c, k in zip(letter["crosses"], letter["piece_of_cross"]) if k == pi]
        if len(cr) < MIN_CROSSES:
            continue
        A = np.array([c[0] for c in cr], float)
        B = np.array([c[1] for c in cr], float)
        M = (A + B) / 2
        s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(M, axis=0).T))])
        for i in range(len(cr)):
            m = np.abs(s - s[i]) <= HALF_MM
            if m.sum() < MIN_CROSSES or float(np.ptp(s[m])) < MIN_SPAN_MM:
                continue
            w = M[m]
            c = w.mean(0)
            _, _, vt = np.linalg.svd(w - c, full_matrices=False)
            if float(np.sqrt((((w - c) @ vt[1]) ** 2).mean())) > STRAIGHT_MM:
                continue
            axis = math.degrees(math.atan2(vt[0][1], vt[0][0])) % 180.0
            d = B[i] - A[i]
            cross = fold(math.degrees(math.atan2(d[1], d[0])))
            off_line = abs(fold(axis))
            cls = "stem" if off_line >= 90.0 - STEM_DEG else "bar" if off_line <= STEM_DEG else "diag"
            out.append({"axis": axis, "lean": fold(axis - 90.0), "cross": cross,
                        "square": fold(cross - (axis + 90.0)), "cls": cls,
                        "at": [float(v) for v in M[i]], "piece": pi})
    return out


def axial_mean(deg) -> float:
    """The mean of undirected angles (doubled, averaged, halved), on (-90, 90].
    A satin zigzag alternates +-atan(pitch / 2 width) about its true cross
    (3.8 deg on a 3 mm column at 0.4 mm), which a median of signed angles
    picks one side of; this cancels it, and a bar's crosses near +-90 do
    not average to 0."""
    r = np.radians(2.0 * np.asarray(deg, float))
    return fold(math.degrees(math.atan2(float(np.sin(r).mean()), float(np.cos(r).mean()))) / 2.0)


def summary(cs: list[dict], slant: float | None) -> dict | None:
    """Means and shares for one class of crosses; `slant` the word's."""
    if not cs:
        return None
    cross = np.array([c["cross"] for c in cs])
    sq = np.array([c["square"] for c in cs])
    out = {"n": len(cs), "lean": float(np.median([c["lean"] for c in cs])),
           "cross": axial_mean(cross), "square": axial_mean(sq),
           "on_text_5": float((np.abs(cross) <= 5.0).mean()),
           "on_text_15": float((np.abs(cross) <= 15.0).mean()),
           "square_5": float((np.abs(sq) <= 5.0).mean())}
    if slant is not None:
        along = np.array([fold(c["cross"] - (90.0 + slant)) for c in cs])
        out["along_slant"] = float((np.abs(along) <= ALONG_DEG).mean())
        out["off_slant"] = axial_mean(along)
    return out


def read(path, ymin=-1e9, ymax=1e9, hmin=5.0, hmax=40.0) -> dict:
    """One file -> {slant, letters: [{bbox, stem, bar, diag}], all: {stem, bar, diag}}."""
    res = LP.read(Path(path))
    Ls = [L for L in res["letters"] if hmin <= L["bbox"][3] - L["bbox"][1] <= hmax
          and ymin <= (L["bbox"][1] + L["bbox"][3]) / 2 <= ymax]
    Ls.sort(key=lambda L: L["bbox"][0])
    per = [crosses_of(L) for L in Ls]
    stems = [c["lean"] for cs in per for c in cs if c["cls"] == "stem"]
    slant = float(np.median(stems)) if stems else None
    letters = [{"bbox": [round(v, 2) for v in L["bbox"]],
                **{k: summary([c for c in cs if c["cls"] == k], slant) for k in CLASSES}}
               for L, cs in zip(Ls, per)]
    pooled = [c for cs in per for c in cs]
    return {"file": Path(path).name, "slant": slant, "letters": letters,
            "all": {k: summary([c for c in pooled if c["cls"] == k], slant) for k in CLASSES}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--ymin", type=float, default=-1e9)
    ap.add_argument("--ymax", type=float, default=1e9)
    ap.add_argument("--hmin", type=float, default=5.0)
    ap.add_argument("--hmax", type=float, default=40.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = [read(f, a.ymin, a.ymax, a.hmin, a.hmax) for f in a.files]
    if a.json:
        print(json.dumps(rows, indent=1))
        return 0

    def fmt(s):
        if not s:
            return "-"
        tail = f" along-slant {s['along_slant']:.2f}" if "along_slant" in s else ""
        return (f"n{s['n']} cross {s['cross']:+.1f} square {s['square']:+.1f} "
                f"on-text<=5 {s['on_text_5']:.2f} square<=5 {s['square_5']:.2f}{tail}")
    for r in rows:
        sl = "-" if r["slant"] is None else f"{r['slant']:+.1f}"
        print(f"{r['file']}: slant {sl} deg, {len(r['letters'])} letters")
        for k in CLASSES:
            print(f"  all {k:4s}  {fmt(r['all'][k])}")
        for L in r["letters"]:
            print(f"  {L['bbox']}  stem {fmt(L['stem'])} | bar {fmt(L['bar'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
