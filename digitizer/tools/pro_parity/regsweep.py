"""The registration sweep behind `docs/registration-plateau-2026-09-11.md`.

That study was run from a script nobody committed, so re-running it at full
corpus coverage meant rebuilding the harness. This is the harness, committed,
so the next re-run is one command.

What it measures, per arm:

- **greedy** — exactly what ships. `pairframe.register_pair`'s inner math is
  mirrored here rather than called, because the question is what the search
  finds in ONE flip against a known alternative, and `register_pair` only
  returns the winner.
- **exhaustive** — the best translation on the 0.5 mm lattice, from the
  cross-correlation argmax. `IoU = inter / (|A| + |B| - inter)` rises strictly
  with `inter` when `|A|` and `|B|` are fixed, and under a translation of a
  zero-padded mask they are, so the argmax IS the lattice optimum on overlap.
  **It is then re-scored under `register`'s own `at()`** before being compared
  with greedy: the padded correlation and the border-blurred raster are
  slightly different functions (`_corr_seeds`' own docstring measures them
  disagreeing by up to 0.012 IoU on becker), and comparing a number from one
  against a number from the other would manufacture a gap that is an artefact
  of the instrument. Both columns here are `at()` values.
- **gap** — `at(exhaustive) - at(greedy)`. Positive means the shipped search
  left something on the table. Small NEGATIVE values are legitimate and are
  printed as they fall: greedy polishes to 0.25 mm and the lattice is 0.5 mm,
  so greedy can sit slightly off-lattice and score higher. Clamping that to
  zero would hide the one direction in which this comparison is unfair to the
  lattice, so it is not clamped.
- **fill ratio** — solid thread area over bbox area of the THINNER side. The
  study's finding is that the defect lives only where this is tiny, so it is
  the sort key, not a footnote.

Arms: every prepped design as-prepped, plus one arm per colour block of OURS
with that block deleted — the brief's "a whole element the other file never
sews", applied to real thread rather than a fixture.

    cd digitizer
    PRO_PARITY_OUT=<prepped corpus> .venv/Scripts/python -m tools.pro_parity.regsweep

Reads the corpus `prep_all` already wrote; prepares nothing itself.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

from . import pairframe as pf
from . import scorecard as sc

OUT = Path(os.environ.get("PRO_PARITY_OUT", "pro_parity_out"))


def _at(pc, our_segs, bb):
    """`register`'s own objective, so greedy and exhaustive are comparable."""
    def f(dx, dy):
        return sc._iou(pc, sc.solid(
            sc.raster(our_segs, bb, res=sc.REG_RES, shift=(dx, dy)),
            res=sc.REG_RES))
    return f


def _exhaustive(pc, oc, res=sc.REG_RES, limit=sc.REG_MAX):
    """Lattice argmax of the overlap count, by the same FFT `_corr_seeds` uses.

    Returns `(dx, dy, inter)`; `inter` is an overlap COUNT, not an IoU, and is
    returned only so a caller can tell "nothing overlaps anywhere" (0) from a
    real peak. The IoU that gets compared is always re-scored under `_at`.
    """
    pad = int(limit / res) + 4
    A = np.pad(pc, pad).astype(np.float32)
    B = np.pad(oc, pad).astype(np.float32)
    H, W = A.shape
    corr = np.fft.irfft2(np.fft.rfft2(A) * np.conj(np.fft.rfft2(B)), s=(H, W))
    corr = np.rint(corr).astype(np.int64)
    n = int(limit / res)
    ks = np.arange(-n, n + 1)
    win = corr[np.ix_(ks % H, ks % W)].astype(np.float64)
    yy, xx = np.meshgrid(ks * res, ks * res, indexing="ij")
    win[yy * yy + xx * xx > limit * limit] = -1.0
    i, j = np.unravel_index(np.argmax(win), win.shape)
    return (round(float(xx[i, j]), 2), round(float(yy[i, j]), 2),
            float(max(win[i, j], 0.0)))


def _fill_ratio(segs) -> float:
    """Solid thread area / bbox area, at the search's own resolution."""
    if not segs:
        return 0.0
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    ys = [s[1] for s in segs] + [s[3] for s in segs]
    bb = (min(xs), min(ys), max(xs), max(ys))
    box = (bb[2] - bb[0]) * (bb[3] - bb[1])
    if box <= 0:
        return 0.0
    m = sc.solid(sc.raster(segs, bb, res=sc.REG_RES), res=sc.REG_RES)
    return float(m.sum()) * sc.REG_RES * sc.REG_RES / box


def _thread_mm(segs) -> float:
    return sum(s[4] for s in segs)


class _no_corr_seeds:
    """`register` as it was BEFORE PR #463 — the two original seeds only.

    The study's own table is old-search-against-new, so re-running it needs
    the old search. Suppressing `_corr_seeds` is exactly what #463 added and
    nothing else: the widened frame it also introduced stays, deliberately,
    because that was a change to the OBJECTIVE and comparing two searches
    scored on different objectives would not be a comparison of searches.
    """

    def __enter__(self):
        self._real = sc._corr_seeds
        sc._corr_seeds = lambda *a, **k: []
        return self

    def __exit__(self, *exc):
        sc._corr_seeds = self._real
        return False


def arm(pro_segs, our_segs_raw, flip: bool):
    """One (design, dropped-block, flip) arm: old vs shipped vs lattice.

    Mirrors `register_pair`'s inner math — scale by x-extent, pre-shift by the
    bbox-centre delta, then `register` — so `greedy` is the shipped answer and
    not an approximation of it.
    """
    s = pf.x_extent(pro_segs) / max(pf.x_extent(our_segs_raw), 1e-9)
    ours_s = pf.scale_segs(our_segs_raw, s)
    pcx, pcy = pf.centre(pro_segs)
    ocx, ocy = pf.centre(ours_s)
    ours_c = sc.shifted(ours_s, pcx - ocx, pcy - ocy)
    bb0 = sc.bounds(pro_segs, ours_c)

    gdx, gdy, giou = sc.register(pro_segs, ours_c, bb0)
    with _no_corr_seeds():
        odx, ody, oiou = sc.register(pro_segs, ours_c, bb0)

    # `register` widens the frame by REG_MAX before rasterising; the
    # exhaustive side must score on the SAME frame or the two IoUs are not
    # the same number (that widening is exactly the fix for thread falling
    # out of frame, see `register`'s own comment).
    bb = (bb0[0] - sc.REG_MAX, bb0[1] - sc.REG_MAX,
          bb0[2] + sc.REG_MAX, bb0[3] + sc.REG_MAX)
    pc = sc.solid(sc.raster(pro_segs, bb, res=sc.REG_RES), res=sc.REG_RES)
    oc = sc.solid(sc.raster(ours_c, bb, res=sc.REG_RES), res=sc.REG_RES)
    at = _at(pc, ours_c, bb)
    edx, edy, inter = _exhaustive(pc, oc)
    eiou = at(edx, edy)
    return {
        "flip": flip,
        "old": [round(odx, 2), round(ody, 2), round(float(oiou), 6)],
        "greedy": [round(gdx, 2), round(gdy, 2), round(float(giou), 6)],
        "exhaustive": [edx, edy, round(float(eiou), 6)],
        "gap": round(float(eiou) - float(giou), 6),
        "old_gap": round(float(giou) - float(oiou), 6),
        "old_apart_mm": round(math.hypot(gdx - odx, gdy - ody), 2),
        "apart_mm": round(math.hypot(edx - gdx, edy - gdy), 2),
        "corr_inter": inter,
    }


def design_arms(pro_path: Path, ours_path: Path, max_blocks: int | None = None):
    pro = pf.file_segs(Path(pro_path), False)
    if not pro:
        raise ValueError(f"{pro_path}: no stitches")
    rows = []
    for flip in (False, True):
        ours = pf.file_segs(Path(ours_path), flip)
        if not ours:
            raise ValueError(f"{ours_path}: no stitches")
        blocks = sorted({s[5] for s in ours})
        drops = [None] + (blocks if max_blocks is None else blocks[:max_blocks])
        for drop in drops:
            kept = ours if drop is None else [s for s in ours if s[5] != drop]
            if len(kept) < 2:
                continue
            thin = kept if _thread_mm(kept) <= _thread_mm(pro) else pro
            r = arm(pro, kept, flip)
            r["drop"] = drop
            r["fill_ratio"] = round(_fill_ratio(thin), 4)
            r["ours_thread_mm"] = round(_thread_mm(kept), 1)
            r["pro_thread_mm"] = round(_thread_mm(pro), 1)
            rows.append(r)
    return rows


def main():
    slugs = [a for a in sys.argv[1:] if not a.startswith("-")]
    man = json.loads((OUT / "manifest.json").read_text())
    entries = [e for e in man if e.get("ok") and (not slugs or e["slug"] in slugs)]
    print(f"{len(entries)} prepped designs from {OUT}", flush=True)
    out = []
    t0 = time.time()
    for e in entries:
        ours = OUT / e["slug"] / "ours.dst"
        if not ours.exists():
            print(f"[{e['slug']}] SKIP - no ours.dst", flush=True)
            continue
        t = time.time()
        with warnings.catch_warnings():
            # The degenerate arms are the POINT of this sweep; the floor
            # warning firing on them is expected, not a finding.
            warnings.simplefilter("ignore", pf.RegistrationWarning)
            rows = design_arms(Path(e["file"]), ours)
        for r in rows:
            r["slug"] = e["slug"]
        out.extend(rows)
        worst = max(rows, key=lambda r: r["old_gap"])
        print(f"[{e['slug']}] {len(rows)} arms, worst old-vs-new "
              f"{worst['old_gap']:+.4f} (drop={worst['drop']} "
              f"flip={worst['flip']} {worst['old_apart_mm']} mm apart)  "
              f"{time.time()-t:.1f}s", flush=True)
    (OUT / "regsweep.json").write_text(json.dumps(out, indent=1))

    lat = [r for r in out if r["gap"] > 1e-4]
    old = [r for r in out if r["old_gap"] > 1e-4]
    print(f"\n{len(out)} arms over {len(entries)} designs in "
          f"{time.time()-t0:.0f}s", flush=True)
    print(f"  {len(lat)} arms where the 0.5 mm lattice beats the SHIPPED search",
          flush=True)
    print(f"  {len(old)} arms where the shipped search beats the PRE-#463 one",
          flush=True)
    for r in sorted(old, key=lambda r: -r["old_apart_mm"])[:20]:
        print(f"  {r['slug']:<22} drop={str(r['drop']):>4} "
              f"flip={r['flip']!s:<5} fill={r['fill_ratio']:.4f} "
              f"old={r['old'][2]:.4f}@({r['old'][0]:+.2f},{r['old'][1]:+.2f}) "
              f"new={r['greedy'][2]:.4f}@({r['greedy'][0]:+.2f},"
              f"{r['greedy'][1]:+.2f}) {r['old_apart_mm']} mm apart",
              flush=True)
    band = [(0.0, 0.01), (0.01, 0.1), (0.1, 0.3), (0.3, 1.01)]
    print("\nby fill ratio of the thinner side "
          "(arms / lattice-beats-shipped / shipped-beats-old):", flush=True)
    for lo, hi in band:
        sel = [r for r in out if lo <= r["fill_ratio"] < hi]
        if sel:
            print(f"  {lo:.2f}-{hi:.2f}  {len(sel):4d} arms  "
                  f"{sum(1 for r in sel if r['gap'] > 1e-4)}  "
                  f"{sum(1 for r in sel if r['old_gap'] > 1e-4)}", flush=True)

    # The rows above are PER FLIP. `register_pair` returns the better of the
    # two, so a flip that loses outright can be off by centimetres without any
    # caller ever seeing it. This is the number callers actually get, and it
    # is the one comparable to the study's own claim.
    pairs: dict = {}
    for r in out:
        pairs.setdefault((r["slug"], r["drop"]), []).append(r)
    moved = []
    for (slug, drop), rs in pairs.items():
        o = max(rs, key=lambda r: r["old"][2])
        n = max(rs, key=lambda r: r["greedy"][2])
        d = math.hypot(n["greedy"][0] - o["old"][0], n["greedy"][1] - o["old"][1])
        if d > 0.5 or o["flip"] != n["flip"]:
            moved.append((slug, drop, o, n, d))
    print(f"\nas `register_pair` would return it (best flip wins): "
          f"{len(pairs)} pairs, {len(moved)} where the returned alignment "
          f"moves", flush=True)
    for slug, drop, o, n, d in sorted(moved, key=lambda m: -m[4]):
        flip = "" if o["flip"] == n["flip"] else "  FLIP CHANGED"
        print(f"  {slug:<22} drop={str(drop):>4} fill={n['fill_ratio']:.4f} "
              f"old={o['old'][2]:.4f} new={n['greedy'][2]:.4f} "
              f"{d:.2f} mm apart{flip}", flush=True)


if __name__ == "__main__":
    main()
