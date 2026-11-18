"""marine_match_pics: MARINE, ORIGINAL | BEFORE | AFTER, whole word and per letter.

Our renders only (`digitizer_core.stitchviz`), never the professional's file
(`tests/test_no_new_pro_renders`; the repo is public). For each Becker placement
the Studio's request is digitized twice -- BEFORE = main (`lettering_columns_block_butt` ON since #1684), AFTER = that plus the flags named by `--flags`
-- and the MARINE line (the bottom third of the design) is cut out of the
registered ORIGINAL and both renders at ONE frame:

  <slug>_word.png    three rows, ORIGINAL / BEFORE / AFTER, the whole word
  <slug>_letters.png six columns M A R I N E, three rows, each letter 2x

  python -m tools.marine_match_pics --out DIR --flags r_bowl block_butt_small ...
        [--only SLUG ...] [--ppm 20]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

BECKER = ("becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small", "becker_beanie")
KEY = "extra.lettering_columns_"
ALL = ("r_bowl", "block_butt_small", "a_bar", "block_lean")


def _runs(mask) -> list[tuple[int, int]]:
    out, on, s = [], False, 0
    for i, v in enumerate(list(mask) + [False]):
        if v and not on:
            s, on = i, True
        if not v and on:
            out.append((s, i))
            on = False
    return out


def letter_spans(orig_bw, n: int = 6):
    """x-spans of the n widest ink columns of the MARINE row (original, dark = ink)."""
    import numpy as np
    cols = (orig_bw < 128).sum(axis=0) > 3
    runs = _runs(cols)
    # a letter can split at a counter-free gap of a pixel or two: join runs closer than 4 px
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 4:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    merged = sorted(sorted(merged, key=lambda r: r[1] - r[0], reverse=True)[:n])
    return merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--flags", nargs="*", default=list(ALL), help="names after lettering_columns_ turned ON in AFTER")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--ppm", type=float, default=20.0)
    ap.add_argument("--width", type=float, help="the design's width in mm in place of the job's (Becker at 114)")
    ap.add_argument("--tag", default="", help="appended to each file name (e.g. _114mm)")
    ap.add_argument("--kent-dir", type=Path)
    a = ap.parse_args(argv)
    import json
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from tools import pro_pair, tripwire as tw
    from tools.pro_baseline import JOBS, resolve
    slugs = [s for s in BECKER if not a.only or s in a.only]
    a.out.mkdir(parents=True, exist_ok=True)
    tw.materialise(a.kent_dir or a.out / "_kent", slugs)
    before = {}                    # main: block_butt is ON by default since #1684
    after = {**before, **{KEY + f: True for f in a.flags}}
    for s in slugs:
        garment, width, art = JOBS[s][0], float(a.width or JOBS[s][1]), Path(resolve(JOBS[s][2]))
        orig = pro_pair._scaled(pro_pair._art_ink(art), width, a.ppm, cv2.INTER_AREA)
        panels = [orig]
        for extra in (before, after):
            d = pro_pair.digitize(art, width, garment, extra)
            panels.append(stitchviz.render_design(d.design, px_per_mm=a.ppm))
        word = []
        for p in panels:
            p3 = p if p.ndim == 3 else cv2.cvtColor(p, cv2.COLOR_GRAY2BGR)
            word.append(p3[int(p3.shape[0] * 0.62):])
        hh = max(p.shape[0] for p in word)
        ww0 = max(p.shape[1] for p in word)
        word = [cv2.copyMakeBorder(p, 0, hh - p.shape[0], 0, ww0 - p.shape[1], cv2.BORDER_CONSTANT, value=(235, 235, 235))
                for p in word]
        names = ("ORIGINAL", "BEFORE (block_butt)", "AFTER (" + " + ".join(a.flags) + ")")
        rows = []
        for p, nm in zip(word, names):
            rows.append(pro_pair._label(p if p.ndim == 3 else cv2.cvtColor(p, cv2.COLOR_GRAY2BGR), nm))
        cv2.imwrite(str(a.out / f"{s}{a.tag}_word.png"), pro_pair._vstack(rows))
        # per letter
        gray = cv2.cvtColor(word[0], cv2.COLOR_BGR2GRAY) if word[0].ndim == 3 else word[0]
        spans = letter_spans(gray)
        strips = []
        for p in word:
            p3 = p if p.ndim == 3 else cv2.cvtColor(p, cv2.COLOR_GRAY2BGR)
            tiles = []
            for x0, x1 in spans:
                t = p3[:, max(0, x0 - 10): x1 + 22]
                tiles.append(cv2.resize(t, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR))
            hh = max(t.shape[0] for t in tiles)
            tiles = [cv2.copyMakeBorder(t, 0, hh - t.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(235, 235, 235)) for t in tiles]
            strips.append(np.hstack(tiles))
        ww = max(r.shape[1] for r in strips)
        strips = [cv2.copyMakeBorder(r, 0, 0, 0, ww - r.shape[1], cv2.BORDER_CONSTANT, value=(235, 235, 235)) for r in strips]
        strips = [pro_pair._label(r, nm) for r, nm in zip(strips, names)]
        cv2.imwrite(str(a.out / f"{s}{a.tag}_letters.png"), pro_pair._vstack(strips))
        print(s, "ok", [tuple(sp) for sp in spans], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
