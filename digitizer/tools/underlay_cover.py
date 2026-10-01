#!/usr/bin/env python
"""Back stitching as SEWN: how much of a design is thread sewn only to be
covered, what pattern that thread makes, and how much of the top thread
sits on it.

Kent's words for the professionally digitized Becker beside ours
(2026-10-01, the pro sitting): *"back stitching to support the detail
layering ... The back stitching helps support the top threading so it has
structure and support."* No instrument here had a number for that: our
own plan knows its underlay runs by kind, but a machine file has no kinds,
so ours and the pro's could not be read by one rule. This one reads the
STITCHES of either, in sew order, the way the needle lays them.

**The rule.** Thread is drawn into a raster in sew order at `THREAD_MM`
wide; each pixel remembers the LAST stitch that covered it. A stitch
segment is COVERED when most of its pixels end up under a stitch sewn at
least `LATER` segments after it -- the neighbours of a satin cross overlap
it and are excluded by that gap, a column sewn over a centre run is not.
A stretch of covered segments is back stitching (underlay, in the
engine's word); its pattern is read from its own geometry: a ZIGZAG when
`tools.satin_columns` sees crosses in it, LATTICE when it turns back on
itself at row ends, RUNNING otherwise (a line of 1.5-4 mm stitches down a
spine or along an edge). The top thread's SUPPORT is the share of its
pixels that already had thread beneath them when it was sewn, again at
least `LATER` segments earlier.

**What it cannot say.** Why the thread was sewn: a travel run that a later
column happens to cover reads as back stitching, which is what it does on
the cloth. And a design's own kinds, where it has them, are not consulted
-- `tools/underlay_kinds.py` is the cross-check that reads ours by kind.

Reported per design and per colour block: penetrations, thread length,
the back-stitching share of each, the pattern split, the top thread's
support, and the penetrations more than `INTERIOR_MM` inside the sewn
area ("interior holes" -- on a satin stroke those are split points or
back stitching, never the rails). An optional crop (fractions of the
design's height, top to bottom) reports the same for one band, so one word
of a logo can be compared across two digitizings whose other parts differ.

Usage:
    python -m tools.underlay_cover FILE_OR_DESIGN_JSON [--crop 0.68 1.0]
        [--debug out.png] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.satin_columns import _crosses  # noqa: E402

PX_PER_MM = 10
THREAD_MM = 0.4           # a 40-wt thread laid flat, the renderer's width
LATER = 6                 # segments: past the overlap of a cross's neighbours
COVERED_FRAC = 0.6        # a segment under this much later thread is covered
INTERIOR_MM = 1.0         # a hole this far inside the sewn area is not on a rail
RUN_MIN_SEGS = 3          # shorter covered stretches are hops, not back stitching
TWO_RAIL_MM = 0.5         # a point this far off its neighbours' chord is on a rail
TWO_RAIL_SHARE = 0.7      # ...and a run where most points are is a zigzag


def runs_from_pattern(pattern) -> list[dict]:
    """-> [{block, pts}] needle-down passes in mm (y-down, the file's frame);
    a JUMP, TRIM or COLOR_CHANGE ends a pass."""
    import pystitch

    runs: list[dict] = []
    cur: list[tuple[float, float]] = []
    block = 0
    for x, y, c in pattern.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            continue
        if len(cur) >= 2:
            runs.append({"block": block, "pts": cur})
        cur = []
        if cmd == pystitch.COLOR_CHANGE:
            block += 1
    if len(cur) >= 2:
        runs.append({"block": block, "pts": cur})
    return runs


def runs_from_file(path: Path) -> list[dict]:
    import pystitch

    pat = pystitch.read(str(path))
    if pat is None:
        raise ValueError(f"unreadable: {path}")
    return runs_from_pattern(pat)


def runs_from_design(design: dict) -> list[dict]:
    from digitizer_core.adapter import design_to_pattern

    return runs_from_pattern(design_to_pattern(design))


def load_runs(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        return runs_from_design(json.loads(path.read_text(encoding="utf-8")))
    return runs_from_file(path)


def _turns_deg(pts: np.ndarray) -> np.ndarray:
    """Turn at each interior point: 0 straight on, 180 straight back."""
    if len(pts) < 3:
        return np.zeros(0)
    u = pts[1:-1] - pts[:-2]
    v = pts[2:] - pts[1:-1]
    lu = np.hypot(*u.T)
    lv = np.hypot(*v.T)
    with np.errstate(invalid="ignore", divide="ignore"):
        cosang = (u * v).sum(1) / np.maximum(lu * lv, 1e-9)
    return np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))


def _two_rail_share(p: np.ndarray) -> float:
    """Share of points sitting at least `TWO_RAIL_MM` off the chord of their
    two-away neighbours. A sawtooth zigzag puts every apex off that chord;
    so does a LADDER (cross, a walk along the rail, cross back -- the shape
    of this engine's own satin zigzag underlay, whose turns are near 90
    degrees and which the column detector therefore does not see); a run
    down a spine or along a fill row sits on it."""
    if len(p) < 5:
        return 0.0
    a, b, c = p[:-4], p[2:-2], p[4:]
    ac = c - a
    lac = np.hypot(*ac.T)
    area2 = ac[:, 0] * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * ac[:, 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        off = np.where(lac > 1e-9, np.abs(area2) / np.maximum(lac, 1e-9), np.hypot(*(b - a).T))
    return float((off >= TWO_RAIL_MM).mean())


def pattern_of(pts: list[tuple[float, float]]) -> str:
    """ZIGZAG when the stitches swing between two rails -- the column
    detector sees crosses in most of it (a sawtooth), or most points sit off
    the chord of their neighbours two away (a ladder) -- LATTICE when the
    run turns back on itself at row ends, RUNNING otherwise."""
    if len(pts) < 3:
        return "running"
    inside, _w = _crosses(pts)
    if inside.mean() >= 0.5:
        return "zigzag"
    p = np.asarray(pts, float)
    if _two_rail_share(p) >= TWO_RAIL_SHARE:
        return "zigzag"
    if _doubles_back_share(p) >= 0.06:
        return "lattice"
    return "running"


def _doubles_back_share(p: np.ndarray) -> float:
    """Share of legs whose direction is undone within two legs: a row end,
    whether the thread turns straight back or hops one row over in two
    square turns. Needs at least eight legs to mean anything."""
    if len(p) < 9:
        return 0.0
    u = p[1:] - p[:-1]
    n = np.hypot(*u.T)
    u = u / np.maximum(n, 1e-9)[:, None]
    back1 = (u[:-1] * u[1:]).sum(1) < -0.8
    back2 = (u[:-2] * u[2:]).sum(1) < -0.8
    rev = back1[:-1] | back2
    return float(rev.mean())


def measure(runs: list[dict], px_per_mm: int = PX_PER_MM, thread_mm: float = THREAD_MM,
            crop: tuple[float, float] | None = None, debug: Path | None = None,
            details: bool = False) -> dict:
    """-> the report (see the module doc). `crop` is (top, bottom) as
    fractions of the design's height, 0 at the top of the sewn area.
    `details` adds `_segments`: the per-segment arrays (run index, length,
    covered fraction, back flag, pattern, support) a caller with its own
    labels -- our plan's run kinds -- can cross-check the rule against."""
    # --- segments in sew order ------------------------------------------
    seg_run: list[int] = []
    seg_xy: list[tuple[float, float, float, float]] = []
    for ri, r in enumerate(runs):
        pts = r["pts"]
        for a, b in zip(pts, pts[1:]):
            seg_run.append(ri)
            seg_xy.append((a[0], a[1], b[0], b[1]))
    n = len(seg_xy)
    if n == 0:
        raise ValueError("no stitches")
    S = np.asarray(seg_xy, float)
    seg_len = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])
    x0 = min(S[:, 0].min(), S[:, 2].min()) - 2 * thread_mm
    y0 = min(S[:, 1].min(), S[:, 3].min()) - 2 * thread_mm
    x1 = max(S[:, 0].max(), S[:, 2].max()) + 2 * thread_mm
    y1 = max(S[:, 1].max(), S[:, 3].max()) + 2 * thread_mm
    W = int(math.ceil((x1 - x0) * px_per_mm)) + 1
    H = int(math.ceil((y1 - y0) * px_per_mm)) + 1
    thick = max(1, int(round(thread_mm * px_per_mm)))
    owner = np.full((H, W), -1, np.int32)
    on_thread = np.zeros(n)
    pix: list[tuple[np.ndarray, np.ndarray]] = []
    for i in range(n):
        ax, ay, bx, by = S[i]
        px = ((ax - x0) * px_per_mm, (ay - y0) * px_per_mm, (bx - x0) * px_per_mm, (by - y0) * px_per_mm)
        lx = int(math.floor(min(px[0], px[2]))) - thick
        ly = int(math.floor(min(px[1], px[3]))) - thick
        hx = int(math.ceil(max(px[0], px[2]))) + thick
        hy = int(math.ceil(max(px[1], px[3]))) + thick
        canvas = np.zeros((hy - ly + 1, hx - lx + 1), np.uint8)
        cv2.line(canvas, (int(round(px[0] - lx)), int(round(px[1] - ly))),
                 (int(round(px[2] - lx)), int(round(px[3] - ly))), 255, thick)
        ys, xs = np.nonzero(canvas)
        ys = ys + ly
        xs = xs + lx
        prev = owner[ys, xs]
        on_thread[i] = float(((prev >= 0) & (prev <= i - LATER)).mean()) if len(ys) else 0.0
        owner[ys, xs] = i
        pix.append((ys, xs))
    covered = np.zeros(n)
    for i, (ys, xs) in enumerate(pix):
        own = owner[ys, xs]
        covered[i] = float((own >= i + LATER).mean()) if len(ys) else 0.0

    # --- covered stretches -> back stitching, by pattern ------------------
    is_cov = covered >= COVERED_FRAC
    back = np.zeros(n, bool)
    pattern = np.full(n, "", object)
    pieces: list[dict] = []
    i = 0
    while i < n:
        if not is_cov[i]:
            i += 1
            continue
        j = i + 1
        while j < n and is_cov[j] and seg_run[j] == seg_run[i]:
            j += 1
        if j - i >= RUN_MIN_SEGS:
            pts = [(S[k, 0], S[k, 1]) for k in range(i, j)] + [(S[j - 1, 2], S[j - 1, 3])]
            kind = pattern_of(pts)
            back[i:j] = True
            pattern[i:j] = kind
            pieces.append({"start": i, "end": j, "pattern": kind,
                           "mm": float(seg_len[i:j].sum()), "block": runs[seg_run[i]]["block"]})
        i = j

    # --- penetrations: one per segment end, plus each pass's first point ---
    pen_xy: list[tuple[float, float]] = []
    pen_seg: list[int] = []
    si = 0
    for ri, r in enumerate(runs):
        pts = r["pts"]
        pen_xy.append(pts[0])
        pen_seg.append(si)
        for k in range(1, len(pts)):
            pen_xy.append(pts[k])
            pen_seg.append(si)
            si += 1
    P = np.asarray(pen_xy, float)
    pen_seg_a = np.asarray(pen_seg)
    pen_back = back[pen_seg_a]
    pen_block = np.asarray([runs[seg_run[s]]["block"] for s in pen_seg])

    # --- interior holes: distance to the sewn area's edge ------------------
    mask = (owner >= 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5) / px_per_mm
    pxs = np.clip(((P[:, 0] - x0) * px_per_mm).round().astype(int), 0, W - 1)
    pys = np.clip(((P[:, 1] - y0) * px_per_mm).round().astype(int), 0, H - 1)
    interior = dist[pys, pxs] > INTERIOR_MM
    area_mm2 = float(mask.sum()) / (px_per_mm * px_per_mm)

    top = ~back
    top_len = seg_len[top].sum()

    def summary(sel_seg: np.ndarray, sel_pen: np.ndarray) -> dict:
        b = back & sel_seg
        t = top & sel_seg
        tl = seg_len[t].sum()
        out = {
            "penetrations": int(sel_pen.sum()),
            "thread_mm": round(float(seg_len[sel_seg].sum()), 1),
            "back_penetrations": int((pen_back & sel_pen).sum()),
            "back_share_penetrations": round(float((pen_back & sel_pen).sum() / max(1, sel_pen.sum())), 4),
            "back_thread_mm": round(float(seg_len[b].sum()), 1),
            "back_share_thread": round(float(seg_len[b].sum() / max(1e-9, seg_len[sel_seg].sum())), 4),
            "back_by_pattern_mm": {k: round(float(seg_len[b & (pattern == k)].sum()), 1)
                                   for k in ("running", "zigzag", "lattice")},
            "top_support": round(float((on_thread[t] * seg_len[t]).sum() / max(1e-9, tl)), 4),
            "interior_holes": int((interior & sel_pen).sum()),
            "interior_share": round(float((interior & sel_pen).sum() / max(1, sel_pen.sum())), 4),
            "interior_back": int((interior & pen_back & sel_pen).sum()),
            "interior_top": int((interior & ~pen_back & sel_pen).sum()),
        }
        return out

    all_seg = np.ones(n, bool)
    all_pen = np.ones(len(P), bool)
    rep = {
        "px_per_mm": px_per_mm, "thread_mm": thread_mm, "later": LATER,
        "covered_frac": COVERED_FRAC, "interior_mm": INTERIOR_MM,
        "width_mm": round(float(x1 - x0 - 4 * thread_mm), 1),
        "height_mm": round(float(y1 - y0 - 4 * thread_mm), 1),
        "sewn_area_mm2": round(area_mm2, 1),
        "runs": len(runs), "blocks": int(max(r["block"] for r in runs)) + 1,
        "back_pieces": len(pieces),
        "whole": summary(all_seg, all_pen),
        "by_block": {},
    }
    seg_block = np.asarray([runs[r]["block"] for r in seg_run])
    for b in sorted(set(seg_block.tolist())):
        rep["by_block"][str(b)] = summary(seg_block == b, pen_block == b)
    if crop is not None:
        top_mm = y0 + 2 * thread_mm + crop[0] * (y1 - y0 - 4 * thread_mm)
        bot_mm = y0 + 2 * thread_mm + crop[1] * (y1 - y0 - 4 * thread_mm)
        # The bottom edge is inclusive: a crop to 1.0 must keep the holes on
        # the design's last row, which sit exactly on it.
        mid_y = (S[:, 1] + S[:, 3]) / 2
        sel_seg = (mid_y >= top_mm) & (mid_y <= bot_mm + 1e-6)
        sel_pen = (P[:, 1] >= top_mm) & (P[:, 1] <= bot_mm + 1e-6)
        band = mask[int((top_mm - y0) * px_per_mm):int((bot_mm - y0) * px_per_mm)]
        rep["crop"] = {"top_frac": crop[0], "bottom_frac": crop[1],
                       "sewn_area_mm2": round(float(band.sum()) / (px_per_mm * px_per_mm), 1),
                       **summary(sel_seg, sel_pen)}
        rep["crop"]["holes_per_mm2"] = round(rep["crop"]["penetrations"] / max(1e-9, rep["crop"]["sewn_area_mm2"]), 3)
    rep["whole"]["holes_per_mm2"] = round(rep["whole"]["penetrations"] / max(1e-9, area_mm2), 3)
    rep["top_thread_mm"] = round(float(top_len), 1)
    if details:
        rep["_segments"] = {"run": np.asarray(seg_run), "len_mm": seg_len, "covered": covered,
                            "back": back, "pattern": pattern, "support": on_thread,
                            "pen_seg": pen_seg_a, "pen_interior": interior, "pen_back": pen_back}

    if debug is not None:
        img = np.full((H, W, 3), 238, np.uint8)
        img[mask > 0] = (205, 205, 205)
        col = {"running": (200, 80, 0), "zigzag": (0, 140, 0), "lattice": (160, 0, 160)}
        for i in range(n):
            if back[i]:
                ax, ay, bx, by = S[i]
                cv2.line(img, (int((ax - x0) * px_per_mm), int((ay - y0) * px_per_mm)),
                         (int((bx - x0) * px_per_mm), int((by - y0) * px_per_mm)), col[pattern[i]], 1)
        for k in range(len(P)):
            c = (0, 0, 220) if interior[k] and not pen_back[k] else (40, 40, 40)
            cv2.circle(img, (int(pxs[k]), int(pys[k])), 1, c, -1)
        if crop is not None:
            for yy in (top_mm, bot_mm):
                yy_px = int((yy - y0) * px_per_mm)
                cv2.line(img, (0, yy_px), (W - 1, yy_px), (0, 0, 0), 1)
        cv2.imwrite(str(debug), img)
    return rep


def _fmt(label: str, s: dict) -> str:
    pat = s["back_by_pattern_mm"]
    return (f"{label:<12} pen {s['penetrations']:>6}  thread {s['thread_mm']:>8.0f} mm  "
            f"back {100 * s['back_share_penetrations']:5.1f}% of holes / {100 * s['back_share_thread']:5.1f}% of thread "
            f"(run {pat['running']:.0f} / zig {pat['zigzag']:.0f} / lattice {pat['lattice']:.0f} mm)  "
            f"support {100 * s['top_support']:5.1f}%  interior {100 * s['interior_share']:5.1f}% "
            f"(top {s['interior_top']}, back {s['interior_back']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path, help="a machine file, or one of our design JSONs")
    ap.add_argument("--crop", nargs=2, type=float, metavar=("TOP", "BOTTOM"),
                    help="a band of the design's height as fractions, 0 at the top")
    ap.add_argument("--debug", type=Path, help="write a map: back stitching coloured by pattern, interior top holes red")
    ap.add_argument("--json", type=Path, help="write the report")
    a = ap.parse_args(argv)
    runs = load_runs(a.path)
    rep = measure(runs, crop=tuple(a.crop) if a.crop else None, debug=a.debug)
    print(f"{a.path.name}: {rep['width_mm']} x {rep['height_mm']} mm, {rep['runs']} passes, "
          f"{rep['blocks']} blocks, {rep['back_pieces']} back-stitching pieces, "
          f"sewn area {rep['sewn_area_mm2']} mm2, {rep['whole']['holes_per_mm2']} holes/mm2")
    print(_fmt("whole", rep["whole"]))
    for b, s in rep["by_block"].items():
        print(_fmt(f"block {b}", s))
    if "crop" in rep:
        print(_fmt(f"crop {rep['crop']['top_frac']:.2f}-{rep['crop']['bottom_frac']:.2f}", rep["crop"])
              + f"  {rep['crop']['holes_per_mm2']} holes/mm2")
    if a.json:
        a.json.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
