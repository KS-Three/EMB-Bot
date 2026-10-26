"""small_text_columns: sewn column width, letter gaps and letter pieces of
small lettering, ours beside the professional's, each read in its own frame.

WHAT IT IS FOR. The pro's rule for raised small text (R4 and R6 of
`docs/pro-digitizer-rules-2026-10-21.md`): thin strokes sewn at a floor
(0.9 mm on Fremont, 1.26 on Drone and Proseal), wide strokes at the art's
width, letter gaps closed to 0.15-0.35 mm. This reads those three numbers
off a machine file the same way for both sides, so an arm of ours can be
held against the pro's file line by line.

HOW (the pro-rules doc's method, applied to BOTH files as DST):
- letters: per colour block, needle-down stitches of 6 mm or less drawn
  0.4 mm wide at 20 px/mm, opened by 0.55 mm so the runs travelling between
  letters fall away; each remaining connected piece is a letter or a joined
  pair. Pieces are read in the file's OWN frame (mm from its stitch extents'
  top-left), never inside a box mapped from the art or from the other file.
- a line: the pieces whose vertical centre lies in a band (mm, own frame),
  picked per side from `--pieces` output. Bars wider than 3x their height
  are dropped.
- cap: median height of pieces at least 0.7 of the line's tallest, less the
  0.4 mm thread.
- column: the satin crosses whose midpoint lies on one of the line's pieces;
  a cross is a needle-to-needle segment flanked by reversals, the crosses two
  back and two ahead parallel (|cos| >= 0.9) and of similar length (0.7-1.4x).
- gap: between x-adjacent pieces of a line, the nearest distance between
  their drawn masks (the 0.4 mm thread already in them): the VISIBLE gap.
  `gap_med` leaves out word spaces (wider than max(0.6, 0.35 cap)).
- band_<line>_<side>.png in --out: the band's stitches, the line's own
  colour blocks dark, the rest pale -- look before quoting a number.
- letters of a known word (`text_lines`, `word_letters`; the 5-10 mm band,
  2026-10-25): a joined piece is shared out between the letters it holds and
  parted -- at a 1.0 mm opening when they part there (a TIP touch), else at
  the thread's narrowest column (FUSED); each pair of neighbours gets its
  visible gap (0 when touching) and the thread they share. Used by
  `tools/letter_gap_census.py`; `pieces` is unchanged.

Ours is digitized exactly as `tools.pro_pair.digitize` does (the Studio's
request through the service's parser), with `--set key=value` overrides
added to that request, written through `digitizer_service.formats.write`
as DST and read back with pystitch -- the file the customer gets.

  python -m tools.small_text_columns --job fremont --pieces --out DIR    # both piece lists; DIR/ours.dst
  python -m tools.small_text_columns --job fremont --ours DIR/ours.dst \
      --band pro:TAG:34:39.5:28:67 --band ours:TAG:33.3:39.3:28:66 --out DIR2
  python -m tools.small_text_columns --job fremont --set small_text_cap_mm=4.0 ... --out DIR
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

REPO = DIGITIZER.parent
# gitignored (third-party files): a lane under .claude/worktrees/ reads the
# primary checkout's copy
PRO_DIR = next((p / "scratch_kent" / "Embroidery Files" for p in (REPO, *REPO.parents)
                if (p / "scratch_kent" / "Embroidery Files").is_dir()),
               REPO / "scratch_kent" / "Embroidery Files")
PPM = 20.0
THREAD_MM = 0.4
OPEN_MM = 0.55
MAX_STITCH_MM = 6.0

#: job -> art, pro file, width, garment, and the letters of its small lines.
#: A line's band is given per side with --band, picked from `--pieces`: the
#: lines move when ours is grown, so no band is fixed here.
JOBS = {
    "fremont": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_hotel_fremont.webp",
        "pro": PRO_DIR / "Hotel Fremont" / "Hotel Hat" / "HOTEL FREMONT HAT.DST",
        "width_mm": 92.5, "garment": "hat_front",
        "letters": {"EST": 3, "1895": 4, "THE": 3, "TAG": 11},
    },
    "fremont_patch": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_hotel_fremont.webp",
        "pro": PRO_DIR / "Hotel Fremont" / "Hotel Patch" / "HOTEL FREMONT .DST",
        "width_mm": 92.5, "garment": "hat_front",
        "letters": {"EST": 3, "1895": 4, "THE": 3, "TAG": 11},
    },
    "drone": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_drone_thermal_badge.png",
        "pro": PRO_DIR / "Precision Drone" / "PRECISION DRON HAT 2.DST",
        "width_mm": 62.6, "garment": "hat_front",
        "letters": {"AND DRONE": 8},
    },
    # the art is Kent's and lives ONLY in the gitignored scratch_kent/; never commit it
    "proseal": {
        "art": PRO_DIR.parent / "proseal.jpg",
        "pro": PRO_DIR / "Proseal" / "PROSEALHAT.DST",
        "width_mm": 85.9, "garment": "hat_front",
        "letters": {"SPRAY FOAM + COATINGS": 18},
    },
}


# ------------------------------------------------------------------ reading
def read_blocks(path) -> list[list]:
    """A machine file -> colour blocks of (x, y) mm points, y down, in the
    file's own frame (origin at its stitch extents' top-left); None marks a
    jump or trim."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    blocks, cur = [], []
    for x, y, c in pat.stitches:
        cmd = c & m
        if cmd == pystitch.COLOR_CHANGE:
            blocks.append(cur)
            cur = []
        elif cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
        elif cmd in (pystitch.JUMP, pystitch.TRIM):
            cur.append(None)
    blocks.append(cur)
    pts = np.array([q for b in blocks for q in b if q is not None])
    x0, y0 = pts.min(0)
    return [[None if q is None else (q[0] - x0, q[1] - y0) for q in b] for b in blocks]


def _runs(block):
    """Needle-down runs of a block: consecutive stitches no longer than
    `MAX_STITCH_MM`, split at every jump or trim."""
    runs, cur = [], []
    for q in block:
        if q is None or (cur and math.dist(q, cur[-1]) > MAX_STITCH_MM):
            if len(cur) > 1:
                runs.append(cur)
            cur = [] if q is None else [q]
        else:
            cur.append(q)
    if len(cur) > 1:
        runs.append(cur)
    return runs


def pieces(blocks) -> list[dict]:
    """Letter pieces of every colour block (module docstring)."""
    import cv2
    allp = np.array([q for b in blocks for q in b if q is not None])
    W, H = allp.max(0) + 2.0
    w, h = int(W * PPM) + 1, int(H * PPM) + 1
    tw = max(1, int(round(THREAD_MM * PPM)))
    k = int(round(OPEN_MM * PPM)) | 1
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    out = []
    for bi, b in enumerate(blocks):
        runs = _runs(b)
        if not runs:
            continue
        mask = np.zeros((h, w), np.uint8)
        for r in runs:
            p = np.round(np.array(r) * PPM).astype(np.int32)
            cv2.polylines(mask, [p], False, 255, tw)
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kern)
        n, lab, st, _c = cv2.connectedComponentsWithStats(opened, 8)
        for i in range(1, n):
            x, y, ww, hh, area = st[i]
            if area < (0.5 * PPM) ** 2:
                continue
            out.append({"block": bi, "x0": x / PPM, "y0": y / PPM, "x1": (x + ww) / PPM,
                        "y1": (y + hh) / PPM, "mask": lab[y:y + hh, x:x + ww] == i,
                        "ox": x, "oy": y})
    return out


def crosses(blocks) -> list[tuple[tuple, tuple]]:
    """Satin crosses of every block (module docstring)."""
    found = []
    for b in blocks:
        for r in _runs(b):
            p = np.array(r)
            if len(p) < 6:
                continue
            seg = np.diff(p, axis=0)
            ln = np.hypot(seg[:, 0], seg[:, 1])
            for i in range(2, len(seg) - 2):
                if ln[i] < 1e-6 or ln[i] > 4.0:
                    continue
                if np.dot(seg[i - 1], seg[i]) >= 0 or np.dot(seg[i], seg[i + 1]) >= 0:
                    continue
                ok = True
                for j in (i - 2, i + 2):
                    if ln[j] < 1e-6:
                        ok = False
                        break
                    cos = abs(np.dot(seg[i], seg[j])) / (ln[i] * ln[j])
                    if cos < 0.9 or not 0.7 <= ln[j] / ln[i] <= 1.4:
                        ok = False
                        break
                if ok:
                    found.append((tuple(p[i]), tuple(p[i + 1])))
    return found


def _on_piece(pt, pc) -> bool:
    x, y = int(round(pt[0] * PPM)) - pc["ox"], int(round(pt[1] * PPM)) - pc["oy"]
    m = pc["mask"]
    return 0 <= y < m.shape[0] and 0 <= x < m.shape[1] and bool(m[y, x])


def _gap(a, b) -> float:
    """Nearest distance (mm) between two pieces' drawn masks."""
    import cv2
    x0, y0 = min(a["ox"], b["ox"]), min(a["oy"], b["oy"])
    x1 = max(a["ox"] + a["mask"].shape[1], b["ox"] + b["mask"].shape[1])
    y1 = max(a["oy"] + a["mask"].shape[0], b["oy"] + b["mask"].shape[0])
    ma = np.zeros((y1 - y0, x1 - x0), np.uint8)
    ma[a["oy"] - y0:a["oy"] - y0 + a["mask"].shape[0], a["ox"] - x0:a["ox"] - x0 + a["mask"].shape[1]] = a["mask"]
    mb = np.zeros_like(ma, dtype=bool)
    mb[b["oy"] - y0:b["oy"] - y0 + b["mask"].shape[0], b["ox"] - x0:b["ox"] - x0 + b["mask"].shape[1]] = b["mask"]
    if (ma.astype(bool) & mb).any():
        return 0.0
    dist = cv2.distanceTransform((ma == 0).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dist[mb].min()) / PPM


def line(pcs, xs, band) -> dict:
    """One line's numbers: pieces with vertical centre in `band`."""
    y0, y1 = band[:2]
    xlo, xhi = (band[2], band[3]) if len(band) == 4 else (-1e9, 1e9)
    sel = [p for p in pcs
           if y0 <= (p["y0"] + p["y1"]) / 2 <= y1 and xlo <= (p["x0"] + p["x1"]) / 2 <= xhi
           and (p["x1"] - p["x0"]) <= 3 * (p["y1"] - p["y0"])]
    if not sel:
        return {"pieces": 0}
    sel.sort(key=lambda p: p["x0"])
    hs = [p["y1"] - p["y0"] for p in sel]
    cap = float(np.median([hh for hh in hs if hh >= 0.7 * max(hs)])) - THREAD_MM
    widths = sorted(math.dist(a, b) for a, b in xs
                    if any(_on_piece(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), p) for p in sel))
    gaps = [_gap(a, b) for a, b in zip(sel, sel[1:])]
    vis = [g for g in gaps if g > 0]
    word_gap = max(0.6, 0.35 * cap)         # a space between words, not a letter gap
    letter_gaps = [g for g in gaps if g < word_gap]
    return {"pieces": len(sel), "blocks": sorted({p["block"] for p in sel}), "cap_mm": round(cap, 2),
            "column_med": round(float(np.median(widths)), 2) if widths else None,
            "column_p10": round(float(np.percentile(widths, 10)), 2) if widths else None,
            "column_p90": round(float(np.percentile(widths, 90)), 2) if widths else None,
            "crosses": len(widths),
            "gap_med": round(float(np.median(letter_gaps)), 2) if letter_gaps else None,
            "gaps": [round(g, 2) for g in gaps], "touching": len(gaps) - len(vis),
            "x": [round(sel[0]["x0"], 1), round(sel[-1]["x1"], 1)]}


# ------------------------------------------------------------------ letters of a word
# The 5-10 mm band (2026-10-25, `tools/letter_gap_census.py`). At this size a
# word's letters can TOUCH in thread -- the pro's Fremont O and T meet at a
# serif tip -- so a piece may hold two or three letters, on either side. The
# word's text is known, so a joined piece is shared out between the letters it
# holds and CUT at the thread's own narrowest column; the gap of a cut pair is
# 0 and its `contact_mm` is the thread crossing the cut. A pair still joined
# after a FUSE_OPEN_MM opening is FUSED (a broad bridge), not a tip touch: that
# opening is the 2026-10-23 band reader's (`docs/lettering-5-10mm-2026-10-23.md`).
FUSE_OPEN_MM = 1.0
#: a glyph's sewn width relative to a typical capital, used ONLY to share a
#: joined piece out between its letters and to seed where each cut is looked
#: for; anything not listed is 1.0
LETTER_SHARE = {"I": 0.35, "1": 0.5, "J": 0.7, "L": 0.85, "F": 0.85, "E": 0.85, "T": 0.9,
                "M": 1.25, "W": 1.45}
#: a cut is the thread's narrowest column within this share of the letter's
#: width either side of where the shares put it
CUT_SEARCH = 0.35


def text_lines(pcs, min_h: float = 4.0) -> list[dict]:
    """Pieces at least `min_h` mm tall (no bar wider than 3x its height)
    grouped into lines of text, top to bottom: a piece joins the first line
    whose centre lies within 0.3 of the taller one's height and whose height
    is 0.6-1.6x its own. -> [{"cy", "h", "pieces"}], pieces left to right."""
    sel = [p for p in pcs if p["y1"] - p["y0"] >= min_h and (p["x1"] - p["x0"]) <= 3 * (p["y1"] - p["y0"])]
    sel.sort(key=lambda p: (p["y0"] + p["y1"]) / 2)
    lines: list[dict] = []
    for p in sel:
        cy, h = (p["y0"] + p["y1"]) / 2, p["y1"] - p["y0"]
        for ln in lines:
            if abs(ln["cy"] - cy) < 0.3 * max(ln["h"], h) and 0.6 < h / ln["h"] < 1.6:
                ln["pieces"].append(p)
                ln["cy"] = float(np.mean([(q["y0"] + q["y1"]) / 2 for q in ln["pieces"]]))
                break
        else:
            lines.append({"cy": cy, "h": h, "pieces": [p]})
    for ln in lines:
        ln["pieces"].sort(key=lambda p: p["x0"])
        ln["h"] = float(np.median([p["y1"] - p["y0"] for p in ln["pieces"]]))
    return lines


def _compose(parts) -> dict:
    """One piece-shaped dict (ox, oy, mask, mm box) over several pieces."""
    ox, oy = min(p["ox"] for p in parts), min(p["oy"] for p in parts)
    x1 = max(p["ox"] + p["mask"].shape[1] for p in parts)
    y1 = max(p["oy"] + p["mask"].shape[0] for p in parts)
    m = np.zeros((y1 - oy, x1 - ox), bool)
    for p in parts:
        m[p["oy"] - oy:p["oy"] - oy + p["mask"].shape[0], p["ox"] - ox:p["ox"] - ox + p["mask"].shape[1]] |= p["mask"]
    return {"block": parts[0]["block"], "ox": ox, "oy": oy, "mask": m,
            "x0": ox / PPM, "y0": oy / PPM, "x1": x1 / PPM, "y1": y1 / PPM}


def _x_units(pcs) -> list[dict]:
    """A line's pieces merged into units, left to right: a piece whose x
    extent overlaps the unit before it by half the narrower of the two is part
    of it (a split stroke, a tail under its letter)."""
    units: list[list] = []
    for p in sorted(pcs, key=lambda q: q["x0"]):
        if units:
            last = units[-1]
            lo, hi = min(q["x0"] for q in last), max(q["x1"] for q in last)
            over = min(hi, p["x1"]) - max(lo, p["x0"])
            if over > 0.5 * min(hi - lo, p["x1"] - p["x0"]):
                last.append(p)
                continue
        units.append([p])
    return [_compose(u) for u in units]


def _share(widths, glyphs) -> list[tuple[int, int]] | None:
    """Consecutive glyphs shared out over units of `widths` (mm), every unit
    at least one: the split whose units' widths best match their letters'
    LETTER_SHARE at one common scale (least squares). -> [(i0, i1)] per unit;
    None when there are more units than glyphs."""
    u, n = len(widths), len(glyphs)
    if u > n or not u:
        return None
    sh = [LETTER_SHARE.get(g, 1.0) for g in glyphs]
    s = sum(widths) / sum(sh)
    cum = np.concatenate([[0.0], np.cumsum(sh)])
    inf = float("inf")
    best = [[inf] * (n + 1) for _ in range(u + 1)]
    back = [[0] * (n + 1) for _ in range(u + 1)]
    best[0][0] = 0.0
    for k in range(1, u + 1):
        for j in range(k, n - (u - k) + 1):
            for i in range(k - 1, j):
                if best[k - 1][i] == inf:
                    continue
                c = best[k - 1][i] + (widths[k - 1] - s * (cum[j] - cum[i])) ** 2
                if c < best[k][j]:
                    best[k][j], back[k][j] = c, i
    out, j = [], n
    for k in range(u, 0, -1):
        i = back[k][j]
        out.append((i, j))
        j = i
    return out[::-1]


def _letter(unit, m, glyph, ui) -> dict:
    """A piece-shaped letter from `m`, a mask in `unit`'s own pixels."""
    rows, cols = np.flatnonzero(m.any(1)), np.flatnonzero(m.any(0))
    if not len(rows):
        rows = cols = np.array([0])
    sub = m[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    ox, oy = unit["ox"] + int(cols[0]), unit["oy"] + int(rows[0])
    return {"block": unit["block"], "glyph": glyph, "unit": ui, "ox": ox, "oy": oy, "mask": sub,
            "x0": ox / PPM, "y0": oy / PPM, "x1": (ox + sub.shape[1]) / PPM, "y1": (oy + sub.shape[0]) / PPM}


def _cut_columns(unit, m, glyphs) -> tuple[list[np.ndarray], list[dict]]:
    """`m` (a mask in `unit`'s pixels) holding `glyphs` that no opening parts,
    cut at the thread's narrowest columns -> (letter masks, cuts); a cut is
    {"x_mm", "y_mm", "contact_mm"}: contact is the thread crossing it."""
    col = m.sum(0)
    nz = np.flatnonzero(col)
    a0, a1 = (int(nz[0]), int(nz[-1]) + 1) if len(nz) else (0, m.shape[1])
    sh = [LETTER_SHARE.get(g, 1.0) for g in glyphs]
    s = (a1 - a0) / sum(sh)
    xs, cuts, at = [a0], [], float(a0)
    for j in range(len(glyphs) - 1):
        at += sh[j] * s
        r = CUT_SEARCH * min(sh[j], sh[j + 1]) * s
        lo, hi = max(xs[-1] + 1, int(at - r)), min(a1 - 1, int(at + r) + 1)
        if hi <= lo:
            lo, hi = xs[-1] + 1, max(xs[-1] + 2, a1 - 1)
        seg = col[lo:hi]
        cand = np.flatnonzero(seg == seg.min()) + lo
        c = int(cand[np.argmin(np.abs(cand - at))])
        rows = np.flatnonzero(m[:, c])
        cuts.append({"x_mm": (unit["ox"] + c) / PPM,
                     "y_mm": (unit["oy"] + float(rows.mean())) / PPM if len(rows) else unit["y0"],
                     "contact_mm": round(float(col[c]) / PPM, 2)})
        xs.append(c)
    xs.append(a1)
    out = []
    for a, b in zip(xs, xs[1:]):
        lm = np.zeros_like(m)
        lm[:, a:b] = m[:, a:b]
        out.append(lm)
    return out, cuts


def _cut(unit, glyphs, ui: int) -> tuple[list[dict], list[dict]]:
    """A unit holding `glyphs` parted into letters -> (letters, joins), a join
    per neighbour pair: {"x_mm", "y_mm", "contact_mm", "fused"}, own frame.

    The unit is opened by FUSE_OPEN_MM: letters that part there merely TOUCH
    at 0.4 mm thread, and each unit pixel goes to the nearest part (contact =
    the boundary they share). Letters still joined are FUSED and are cut at
    the thread's narrowest column (contact = the thread crossing the cut)."""
    import cv2
    m = unit["mask"]
    if len(glyphs) == 1:
        return [{**unit, "glyph": glyphs[0], "unit": ui}], []
    k = int(round(FUSE_OPEN_MM * PPM)) | 1
    opened = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _c = cv2.connectedComponentsWithStats(opened, 8)
    parts = [{"block": unit["block"], "ox": int(st[i][0]), "oy": int(st[i][1]),
              "mask": lab[st[i][1]:st[i][1] + st[i][3], st[i][0]:st[i][0] + st[i][2]] == i,
              "x0": st[i][0] / PPM, "x1": (st[i][0] + st[i][2]) / PPM, "y0": 0.0, "y1": 0.0}
             for i in range(1, n) if st[i][4] >= (0.5 * PPM) ** 2]
    parts = _x_units(parts) if parts else []
    groups = _share([p["x1"] - p["x0"] for p in parts], glyphs) if parts else None
    if groups is None:          # nothing parts cleanly: one fused run, cut by columns
        masks, cuts = _cut_columns(unit, m, glyphs)
        return ([_letter(unit, lm, g, ui) for lm, g in zip(masks, glyphs)],
                [{**c, "fused": True} for c in cuts])
    # every unit pixel to its nearest part
    dist = []
    for p in parts:
        pm = np.zeros(m.shape, np.uint8)
        pm[p["oy"]:p["oy"] + p["mask"].shape[0], p["ox"]:p["ox"] + p["mask"].shape[1]] = p["mask"]
        dist.append(cv2.distanceTransform(1 - pm, cv2.DIST_L2, 5))
    owner = np.argmin(np.stack(dist), axis=0)
    letters, joins = [], []
    for pi, (i0, i1) in enumerate(groups):
        pm = m & (owner == pi)
        if pi:                  # touch with the part before: the boundary they share
            prev = m & (owner == pi - 1)
            near = cv2.dilate(prev.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            edge = pm & near
            ys, xs = np.nonzero(edge)
            joins.append({"x_mm": (unit["ox"] + float(xs.mean())) / PPM if len(xs) else letters[-1]["x1"],
                          "y_mm": (unit["oy"] + float(ys.mean())) / PPM if len(ys) else unit["y0"],
                          "contact_mm": round(len(ys) / PPM, 2), "fused": False})
        if i1 - i0 == 1:
            letters.append(_letter(unit, pm, glyphs[i0], ui))
            continue
        masks, cuts = _cut_columns(unit, pm, glyphs[i0:i1])
        letters += [_letter(unit, lm, g, ui) for lm, g in zip(masks, glyphs[i0:i1])]
        joins += [{**c, "fused": True} for c in cuts]
    return letters, joins


def word_letters(pcs, text: str) -> dict:
    """The letters of `text` (one line; words split by spaces) in a line's
    `pcs`, read the same way in any file (the block comment above). ->
    {"letters", "pairs", "units", "note"}: each pair of neighbours is
    {"pair", "i", "space", "gap_mm", "contact_mm", "fused", "x_mm", "y_mm"},
    gap 0 when they touch; `space` marks the pair across a word space."""
    glyphs = [c for c in text if not c.isspace()]
    breaks, k = set(), 0
    for c in text:
        if c.isspace():
            breaks.add(k - 1)
        else:
            k += 1
    units = _x_units(pcs)
    groups = _share([un["x1"] - un["x0"] for un in units], glyphs)
    if groups is None:
        return {"letters": [], "pairs": [], "units": len(units),
                "note": f"{len(units)} pieces for {len(glyphs)} letters: a letter is in pieces"}
    letters, cuts = [], {}
    for ui, (un, (i0, i1)) in enumerate(zip(units, groups)):
        lt, ct = _cut(un, glyphs[i0:i1], ui)
        for j, c in enumerate(ct):
            cuts[i0 + j] = c
        letters += lt
    pairs = []
    for i in range(len(letters) - 1):
        a, b = letters[i], letters[i + 1]
        row = {"pair": a["glyph"] + b["glyph"], "i": i, "space": i in breaks}
        if i in cuts:
            row.update(gap_mm=0.0, **cuts[i])
        else:
            row.update(gap_mm=round(_gap(a, b), 2), contact_mm=0.0, fused=False,
                       x_mm=(a["x1"] + b["x0"]) / 2, y_mm=(max(a["y0"], b["y0"]) + min(a["y1"], b["y1"])) / 2)
        pairs.append(row)
    return {"letters": letters, "pairs": pairs, "units": len(units), "note": None}


def render_band(blocks, band, keep=None, ppm: float = 40.0, pad_mm: float = 1.0):
    """The band's needle-down stitches drawn 0.4 mm wide on white (BGR
    uint8): the blocks in `keep` (the line's own) dark, every other block
    pale. Jumps and trims left out."""
    import cv2
    y0, y1 = band[0] - pad_mm, band[1] + pad_mm
    x0, x1 = (band[2] - pad_mm, band[3] + pad_mm) if len(band) == 4 else (0.0, max(
        q[0] for b in blocks for q in b if q is not None) + pad_mm)
    w, h = int((x1 - x0) * ppm) + 1, int((y1 - y0) * ppm) + 1
    img = np.full((h, w, 3), 255, np.uint8)
    tw = max(1, int(round(THREAD_MM * ppm)))
    order = [bi for bi in range(len(blocks)) if keep is None or bi not in keep] + sorted(keep or [])
    for bi in order:
        shade = (30, 30, 30) if keep is None or bi in keep else (215, 215, 215)
        for r in _runs(blocks[bi]):
            p = np.round((np.array(r) - (x0, y0)) * ppm).astype(np.int32)
            cv2.polylines(img, [p], False, shade, tw, cv2.LINE_AA)
    return img


# ------------------------------------------------------------------ ours
def digitize_dst(job: dict, overrides: dict, out: Path):
    """Ours through `tools.pro_pair.digitize` with `overrides` on the
    Studio's request -> (path of ours.dst, Digitized)."""
    from digitizer_core.export import plan_to_pattern
    from digitizer_service import formats
    from tools import pro_pair

    from digitizer_core import small_text

    grow = small_text.enlarge_small_text
    rows: list = []

    def enlarge(*a, **k):           # the growth's own report, kept
        out = grow(*a, **k)
        rows.extend(out)
        return out
    small_text.enlarge_small_text = enlarge
    try:
        d = pro_pair.digitize(job["art"], job["width_mm"], job["garment"], extra=overrides)
    finally:
        small_text.enlarge_small_text = grow
    d.growth = rows
    out.mkdir(parents=True, exist_ok=True)
    path = out / "ours.dst"
    path.write_bytes(formats.write(plan_to_pattern(d.plan), "dst"))
    return path, d


def _value(s: str):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--job", choices=sorted(JOBS), required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override on the Studio request (JSON value)")
    ap.add_argument("--band", action="append", default=[], metavar="SIDE:NAME:Y0:Y1[:X0:X1]",
                    help="a line's band on one side (pro|ours), mm in that file's own frame")
    ap.add_argument("--pieces", action="store_true", help="print every piece of both files")
    ap.add_argument("--ours", type=Path, help="read this DST as ours instead of digitizing")
    ap.add_argument("--out", type=Path, default=Path("small_text_columns_out"))
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    job = JOBS[args.job]
    overrides = dict((k, _value(v)) for k, v in (s.split("=", 1) for s in args.set))
    meta = {}
    if args.ours:
        ours_path = args.ours
    else:
        ours_path, d = digitize_dst(job, overrides, args.out)
        c = d.plan.counters if hasattr(d.plan, "counters") else {}
        meta = {k: v for k, v in (c or {}).items() if "column" in k or "floor" in k or "small" in k}
        meta["growth"] = d.growth
    sides = {"pro": read_blocks(job["pro"]), "ours": read_blocks(ours_path)}
    report = {"job": args.job, "overrides": overrides, "ours": str(ours_path), "counters": meta, "lines": {}}
    bands = {}
    for b in args.band:
        side, name, *nums = b.split(":")
        bands.setdefault(name, {})[side] = [float(v) for v in nums]
    for side, blocks in sides.items():
        pcs = pieces(blocks)
        if args.pieces:
            print(f"--- {side}")
            for p in sorted(pcs, key=lambda p: (round(p["y0"]), p["x0"])):
                print(f"  block {p['block']:2d}  x {p['x0']:5.1f}-{p['x1']:5.1f}  y {p['y0']:5.1f}-{p['y1']:5.1f}"
                      f"  ({p['x1'] - p['x0']:4.1f} x {p['y1'] - p['y0']:4.1f})")
        xs = crosses(blocks)
        for name, per in bands.items():
            if side in per:
                got = report["lines"].setdefault(name, {})[side] = line(pcs, xs, per[side])
                import cv2
                args.out.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(args.out / f"band_{name}_{side}.png"),
                            render_band(blocks, per[side], set(got.get("blocks", []))))
    print(json.dumps(report, indent=1))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
