#!/usr/bin/env python
"""A line of lettering, ours against the professional's file, by four
instruments (2026-10-06, the Hotel Fremont deep dive --
`.claude/memory/lettering-thickness-fremont-2026-10-06.md`).

Kent read our HOTEL FREMONT as "waaaay thicker than the original" and
"wobbly". This is the measurement that answered both, lifted out of the
session's scratchpad so the next person re-measures instead of re-deriving:

  width    per letter: the artwork polygon's stroke width (2 x the mean
           skeleton half-width, exact EDT) against the SEWN column (apex
           offset of every satin cross, `satin_columns._crosses`), and the
           same cross read on the pro's file restricted to the letter band.
           The file is ALWAYS wider than the artwork by the fabric's pull on
           each rail; the pro's is too (0.81 -> 1.40 mm at 92.5 mm), so a
           width complaint is settled against the pro's file, never the art.
  jitter   per rail, polygon-free: a line through every 9 same-rail
           penetrations and the centre point's residual; comparable between
           ours and a DST because it needs no artwork.
  lean     each cross against its own rail's direction. NOTE a symmetric
           zigzag has an inherent lean of atan(pitch / 2w) -- 9.7 deg on a
           1.2 mm column at 0.4 mm -- so compare like widths before reading
           a lean as a defect.
  hair     the rendered silhouette (0.4 mm thread) perimeter over the same
           silhouette opened and closed by 0.5 mm, per letter: what the eye
           calls ragged. Ours 1.49 to the pro's 1.21 on Fremont, concentrated
           on curves (the outer-rail pitch, `cfg.satin_outer_rail_pitch`).

The letter band is given as fractions of the artwork's height (the Fremont
default is HOTEL FREMONT's); the pro file's band is the same fractions of
its own height, centred, which registers to ~0.3 mm on Fremont. The pro's
file is not in the repo (a customer file, CLAUDE.md); pass its path.

  .venv/Scripts/python tools/letter_band.py photo/logo_hotel_fremont.webp --width 80 --garment left_chest
  .venv/Scripts/python tools/letter_band.py photo/logo_hotel_fremont.webp --width 92.5 --garment patch \\
      --pro "../scratch_kent/Embroidery Files/Hotel Fremont/Hotel Patch/HOTEL FREMONT .DST" --pro-colour 7
  ... --flag satin_outer_rail_pitch=true     # any PipelineConfig field, as thin_strokes.py takes them
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize, machine          # noqa: E402
from digitizer_core.pipeline import fabric_for                        # noqa: E402
from digitizer_core.textcluster import _stats_of_polygon              # noqa: E402
from digitizer_core.stitches import strip_ties                        # noqa: E402
from satin_columns import MIN_LEG_MM, _crosses                        # noqa: E402
from thin_strokes import parse_flags                                  # noqa: E402

TESTDATA = HERE.parent / "testdata"
WIN = 9


# ---- the cross detector, with the apex kept ------------------------------

def crosses_xy(points):
    """-> [(x, y, width, mean leg)] for every cross in a sustained column,
    `satin_columns._crosses`'s rule with the apex position kept."""
    pts = np.asarray(points, float)
    if len(pts) < 3:
        return []
    a, b, c = pts[:-2], pts[1:-1], pts[2:]
    ac = c - a
    lac = np.hypot(*ac.T)
    area2 = ac[:, 0] * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * ac[:, 1]
    signed = np.where(lac > 1e-9, area2 / np.maximum(lac, 1e-9), 0.0)
    lu, lv = np.hypot(*(b - a).T), np.hypot(*(c - b).T)
    ok = (lu >= MIN_LEG_MM) & (lv >= MIN_LEG_MM) & (lu <= 12) & (lv <= 12) & (np.abs(signed) >= 0.1)
    side = np.sign(signed)
    out = []
    i = 0
    while i < len(ok):
        if not ok[i]:
            i += 1
            continue
        j = i + 1
        while j < len(ok) and ok[j] and side[j] == -side[j - 1]:
            j += 1
        if j - i >= 3:
            for t in range(i, j):
                out.append((b[t, 0], b[t, 1], abs(signed[t]), (lu[t] + lv[t]) / 2))
        i = j
    return out


def column_segments(points):
    pts = np.asarray(points, float)
    if len(pts) < 5:
        return []
    a, b, c = pts[:-2], pts[1:-1], pts[2:]
    ac = c - a
    lac = np.hypot(*ac.T)
    area2 = ac[:, 0] * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * ac[:, 1]
    signed = np.where(lac > 1e-9, area2 / np.maximum(lac, 1e-9), 0.0)
    lu, lv = np.hypot(*(b - a).T), np.hypot(*(c - b).T)
    ok = (lu >= MIN_LEG_MM) & (lv >= MIN_LEG_MM) & (lu <= 12) & (lv <= 12) & (np.abs(signed) >= 0.5)
    side = np.sign(signed)
    segs = []
    i = 0
    while i < len(ok):
        if not ok[i]:
            i += 1
            continue
        j = i + 1
        while j < len(ok) and ok[j] and side[j] == -side[j - 1]:
            j += 1
        if j - i >= 2 * WIN:
            segs.append((i, j + 2))
        i = j
    return segs


def rail_jitter(seqs):
    res = []
    for s in seqs:
        pts = np.asarray(s, float)
        for i, j in column_segments(pts):
            seg = pts[i:j]
            for rail in (seg[0::2], seg[1::2]):
                for k in range(0, len(rail) - WIN + 1):
                    w = rail[k:k + WIN]
                    c = w.mean(0)
                    _, _, vt = np.linalg.svd(w - c)
                    res.append(abs((w[WIN // 2] - c) @ vt[1]))
    return np.asarray(res)


def cross_lean(seqs):
    out = []
    for s in seqs:
        pts = np.asarray(s, float)
        for i, j in column_segments(pts):
            seg = pts[i:j]
            for k in range(2, len(seg) - 2):
                cross = seg[k + 1] - seg[k]
                rail = seg[k + 2] - seg[k - 2]
                cl, rl = np.hypot(*cross), np.hypot(*rail)
                if cl < 0.5 or rl < 1e-6:
                    continue
                out.append(math.degrees(math.asin(min(1.0, abs(cross @ rail) / (cl * rl)))))
    return np.asarray(out)


def hair_per_letter(seqs, x0, x1, y0, y1, px=40):
    import cv2
    img = np.zeros((int((y1 - y0) * px), int((x1 - x0) * px)), np.uint8)
    for pts in seqs:
        p = np.asarray([((x - x0) * px, (y - y0) * px) for x, y in pts], np.int32)
        if len(p) > 1:
            cv2.polylines(img, [p], False, 255, int(machine.COVERAGE_THREAD_W_MM * px), cv2.LINE_8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.5 * px) | 1,) * 2)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(img)
    rows = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 3 * px * px:
            continue
        m = (lab == i).astype(np.uint8) * 255
        sm = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_CLOSE, k), cv2.MORPH_OPEN, k)
        c1, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        c2, _ = cv2.findContours(sm, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        l1 = sum(cv2.arcLength(c, True) for c in c1) / px
        l2 = sum(cv2.arcLength(c, True) for c in c2) / px
        rows.append((float(cent[i][0]), l1 / l2 if l2 else 0.0))
    rows.sort()
    return [r[1] for r in rows]


# ---- the two sides ----------------------------------------------------------

def ours(image, cfg, band_frac):
    result, plan = digitize(str(image), cfg)
    W = cfg.target_width_mm
    from PIL import Image
    im = Image.open(image)
    H = W * im.size[1] / im.size[0]
    band = ((band_frac[0] - 0.5) * H - 0.6, (band_frac[1] - 0.5) * H + 0.6)
    letters = [r for r in result.regions
               if r.polygon.bounds[1] >= band[0] and r.polygon.bounds[3] <= band[1]
               and (r.polygon.bounds[3] - r.polygon.bounds[1]) > 0.09 * H and r.area_mm2 < 0.02 * W * H]
    letters.sort(key=lambda r: r.polygon.bounds[0])
    runs_by = {}
    for _b, run in plan.iter_runs():
        runs_by.setdefault(run.shape_id, []).append(run)
    rows = []
    satin_seqs = []
    sil_seqs = []
    for r in letters:
        sat = [run.points for run in runs_by.get(r.shape_id, []) if run.kind == "satin"]
        if not sat:
            continue
        st = _stats_of_polygon(r.polygon)
        art = 2.0 * st.mean_mm if st else float("nan")
        ws = np.asarray([w for pts in sat for _, _, w, _ in crosses_xy(strip_ties(pts))])
        rows.append((r.shape_id, art, ws))
        satin_seqs += sat
        sil_seqs += [run.points for run in runs_by.get(r.shape_id, []) if run.kind in ("satin", "underlay", "run")]
    return rows, satin_seqs, sil_seqs, band, W, H, plan


def pro(path, colour, band_frac):
    import pystitch
    p = pystitch.read(str(path))
    b = p.bounds()
    W, H = (b[2] - b[0]) / 10, (b[3] - b[1]) / 10
    cy = (b[1] + b[3]) / 20
    band = ((band_frac[0] - 0.5) * H + cy - 0.6, (band_frac[1] - 0.5) * H + cy + 0.6)
    seqs, cur, col, cols = [], [], 0, []
    for x, y, cmd in p.stitches:
        c = cmd & 0xFF
        if c == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
        else:
            if len(cur) > 2:
                seqs.append(cur)
                cols.append(col)
            cur = []
            if c == pystitch.COLOR_CHANGE:
                col += 1
    if len(cur) > 2:
        seqs.append(cur)
        cols.append(col)
    clipped = []
    for s, c in zip(seqs, cols):
        if colour is not None and c != colour:
            continue
        run = []
        for x, y in s:
            if band[0] <= y <= band[1] and abs(x) < W / 2 - 1:
                run.append((x, y))
            else:
                if len(run) > 2:
                    clipped.append(run)
                run = []
        if len(run) > 2:
            clipped.append(run)
    ws = np.asarray([w for s in clipped for _, _, w, _ in crosses_xy(s)])
    return clipped, ws, band, W, H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="artwork under testdata/, or a path")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--band", type=float, nargs=2, default=(0.428, 0.559),
                    help="letter band as fractions of the artwork height (default: HOTEL FREMONT)")
    ap.add_argument("--pro", help="the professional's machine file of the same artwork")
    ap.add_argument("--pro-colour", type=int, default=None, help="colour block index of the lettering in --pro")
    ap.add_argument("--flag", action="append", default=[], help="PipelineConfig field, NAME[=VALUE]")
    a = ap.parse_args()
    image = Path(a.image) if Path(a.image).exists() else TESTDATA / a.image
    cfg = PipelineConfig(target_width_mm=a.width, garment_id=a.garment, **parse_flags(a.flag))
    fab = fabric_for(cfg)
    rows, satin_seqs, sil_seqs, band, W, H, plan = ours(image, cfg, a.band)
    print(f"ours: {image.name} at {a.width} mm / {a.garment} ({fab.id}, pull {fab.pull_comp_mm}/side); "
          f"{plan.stats.stitch_count} stitches, {plan.stats.trims} trims; band {band[0]:.1f}..{band[1]:.1f} mm, {len(rows)} letters")
    print(f"  {'sid':10} {'art':>5} {'sewn':>5} {'p10':>5} {'p90':>5} {'n':>4} {'sewn/art':>8}")
    allw = []
    for sid, art, ws in rows:
        allw.append(ws)
        print(f"  {sid:10} {art:5.2f} {np.median(ws):5.2f} {np.percentile(ws, 10):5.2f} {np.percentile(ws, 90):5.2f} {len(ws):4d} {np.median(ws) / art:8.2f}")
    w = np.concatenate(allw)
    j = rail_jitter(satin_seqs)
    l = cross_lean(satin_seqs)
    h = hair_per_letter(sil_seqs, -W / 2 - 1, W / 2 + 1, band[0] - 1, band[1] + 1)
    print(f"  all crosses: med {np.median(w):.2f} p10 {np.percentile(w, 10):.2f} p90 {np.percentile(w, 90):.2f} (n {len(w)})")
    print(f"  rail jitter |dev| med {np.median(j):.3f} p90 {np.percentile(j, 90):.3f} mm; lean med {np.median(l):.1f} p90 {np.percentile(l, 90):.1f} deg; "
          f"hair per letter mean {np.mean(h):.2f} ({' '.join(f'{v:.2f}' for v in h)})")
    if a.pro:
        seqs, ws, pband, pW, pH = pro(a.pro, a.pro_colour, a.band)
        k = a.width / pW
        j = rail_jitter(seqs)
        l = cross_lean(seqs)
        h = hair_per_letter([[(x * k, y * k) for x, y in s] for s in seqs], -W / 2 - 1, W / 2 + 1, pband[0] * k - 1, pband[1] * k + 1)
        print(f"pro: {Path(a.pro).name}, {pW:.1f} x {pH:.1f} mm, band {pband[0]:.1f}..{pband[1]:.1f}; scaled to {a.width} mm for hair")
        print(f"  crosses: med {np.median(ws):.2f} p10 {np.percentile(ws, 10):.2f} p90 {np.percentile(ws, 90):.2f} (n {len(ws)}); "
              f">= 1.0 mm med {np.median(ws[ws >= 1.0]):.2f}; share under 1.0 {100 * (ws < 1.0).mean():.0f}% (short stitches)")
        print(f"  rail jitter |dev| med {np.median(j):.3f} p90 {np.percentile(j, 90):.3f} mm; lean med {np.median(l):.1f} p90 {np.percentile(l, 90):.1f} deg; "
              f"hair per letter mean {np.mean(h):.2f} ({' '.join(f'{v:.2f}' for v in h)})")


if __name__ == "__main__":
    main()
