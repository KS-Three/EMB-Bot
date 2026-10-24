"""letter_pieces: how a big satin letter is cut into pieces, read off a machine
file -- one rule for the professional's DST and ours (2026-10-24,
`docs/big-letter-construction-2026-10-24.md`).

WHAT IT READS. Needle-down runs (JUMP / TRIM / COLOR_CHANGE end a run) ->
split legs fused (consecutive stitches within FUSE_DEG of one another,
each over 0.3 mm, together at most FUSE_MAX_MM: our split satin's A->M->B,
or A->M1->M2->B on a wide cross, so a split cross counts once) -> CROSSES: a chain of stitches of MIN_CROSS mm or
more, each anti-parallel (within ANTI_DEG) to the one before, whose
midpoints advance at satin pitch (STEP_MM or less); up to two short stitches
inside a chain are skipped. A chain breaks -- a CUT -- where

  restart   the next cross starts more than JUMP_MM from the last one
            (a travel, a jump, a run between the two),
  turn      consecutive crosses differ in direction by more than TURN_DEG
            (a new object begins where the last ended, at a new angle),
  break     the needle leaves the zigzag (a run stitch, a fill row).

A PIECE is a chain of MIN_PIECE crosses or more over MIN_SPINE_MM of spine
(a lock stitch's back-and-forth has none); shorter chains are counted
(`bits`) but not called pieces. Its ROLE: `patch` under PATCH_MM of spine
(a junction fill-in), `curve` when its spine turns more than 45 deg end to
end, else by its axis -- `upright` within 20 deg of vertical, `horizontal`
within 25 deg of the line of text (arms, bars, a band across the top),
`diagonal` between.

LETTERS are each file's own: connected components of the rasterised cross
coverage (CROSS_PX px/mm, 0.4 mm thread), never a box mapped from the art.
Travel lines between letters are not crosses, so they do not join letters.

PER PIECE: crosses, spine length (the cross midpoints' path), median width,
the cross angle against the line of text (0 = a horizontal cross, square to
an upright stem; + leans clockwise in the file's y-down frame), the cross
against the piece's own axis (0 = square; the axis is the midpoints'
principal direction), drift (p90 - p10 of the cross angle along the piece),
the spine's turn (start to end direction), the longest stitch, and the
cross pitch (midpoint advance per cross) in the first and last END_MM
against the middle.

PER CUT (consecutive pieces of one letter in sewing order): the gap between
the last cross and the next piece's first, the cross-angle change, and a
kind: `corner` when the two pieces' axes differ by more than CORNER_DEG
(the stroke turns), `restart` when the next piece starts away from the
last one's end (a new stroke), else `straight` (a cut along one stroke: a
length cap or an angle reset).

  python -m tools.letter_pieces FILE.dst [--rows Y0 Y1] [--min-height MM] [--table]
                                         [--json OUT] [--png OUT]

`--rows` keeps letters whose centre lies between fractions Y0..Y1 of the
design's height (y down), e.g. 0.6 1.0 for a logo's bottom line.
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

FUSE_DEG = 12.0
FUSE_MAX_MM = 12.0
ANTI_DEG = 45.0
MIN_CROSS = 1.0
STEP_MM = 0.9
JUMP_MM = 1.5
TURN_DEG = 35.0
MIN_PIECE = 4
MIN_SPINE_MM = 0.3     # a lock stitch's back-and-forth has no spine
PATCH_MM = 2.5        # a piece shorter than this along its spine is a patch
CORNER_DEG = 30.0
END_MM = 1.0
CROSS_PX = 10.0
MIN_LETTER_MM2 = 4.0


# ------------------------------------------------------------------ files
def runs_of(path: Path) -> list[dict]:
    """Needle-down runs, mm, y down: [{block, pts (n,2)}]."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    out, cur, block = [], [], 0

    def flush():
        if len(cur) >= 2:
            out.append({"block": block, "pts": np.array(cur, float)})
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
        elif c in (pystitch.JUMP, pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.STOP):
            flush()
            cur = []
            if c == pystitch.COLOR_CHANGE:
                block += 1
        elif c == pystitch.END:
            break
    flush()
    return out


def fuse(pts: np.ndarray) -> np.ndarray:
    """Drop the middle points of a split cross: consecutive stitches within
    FUSE_DEG of one another, each over 0.3 mm, merge while the merged stitch
    stays under FUSE_MAX_MM (a 7.7 mm cross can come in three legs)."""
    keep = [pts[0], pts[1]] if len(pts) > 1 else [pts[0]]
    cos_min = math.cos(math.radians(FUSE_DEG))
    for q in pts[2:]:
        a, m = keep[-2], keep[-1]
        u, v = m - a, q - m
        lu, lv = float(np.hypot(*u)), float(np.hypot(*v))
        if (lu > 0.3 and lv > 0.3 and float(np.hypot(*(q - a))) <= FUSE_MAX_MM
                and float(u @ v) / (lu * lv) >= cos_min):
            keep[-1] = q
        else:
            keep.append(q)
    return np.array(keep)


def _dir(u) -> float:
    """Undirected angle of a vector, degrees in [0, 180)."""
    return math.degrees(math.atan2(u[1], u[0])) % 180.0


def _adiff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def chains(pts: np.ndarray) -> list[list[tuple]]:
    """Cross chains of one fused run. Each cross: (a, b, mid, dir_deg, len, idx)."""
    segs = []
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        d = b - a
        segs.append((a, b, (a + b) / 2, _dir(d), float(np.hypot(*d)), k, d))
    out: list[list[tuple]] = []
    cur: list[tuple] = []
    skipped = 0
    for s in segs:
        if s[4] < MIN_CROSS:
            if cur and skipped < 2:
                skipped += 1
                continue
            if len(cur) >= 2:
                out.append(cur)
            cur, skipped = [], 0
            continue
        if cur:
            last = cur[-1]
            cos = float(last[6] @ s[6]) / (last[4] * s[4])
            anti = cos <= -math.cos(math.radians(ANTI_DEG))
            near = float(np.hypot(*(s[2] - last[2]))) <= (STEP_MM + 0.6 * skipped)
            if anti and near:
                cur.append(s)
                skipped = 0
                continue
            if len(cur) >= 2:
                out.append(cur)
            cur = [s]
        else:
            cur = [s]
        skipped = 0
    if len(cur) >= 2:
        out.append(cur)
    return out


def split_turns(chain: list[tuple]) -> list[list[tuple]]:
    """A chain cut where consecutive crosses turn more than TURN_DEG."""
    parts, cur = [], [chain[0]]
    for s in chain[1:]:
        if _adiff(s[3], cur[-1][3]) > TURN_DEG:
            parts.append(cur)
            cur = [s]
        else:
            cur.append(s)
    parts.append(cur)
    return parts


# ------------------------------------------------------------- per piece
def _axis(mids: np.ndarray) -> float:
    c = mids - mids.mean(0)
    if len(mids) < 2 or float(np.abs(c).sum()) < 1e-9:
        return 0.0
    _u, _s, vt = np.linalg.svd(c, full_matrices=False)
    return _dir(vt[0])


def _signed(a: float, ref: float) -> float:
    """a - ref folded into (-90, 90]."""
    d = (a - ref) % 180.0
    return d - 180.0 if d > 90.0 else d


def piece_stats(p: list[tuple]) -> dict:
    mids = np.array([s[2] for s in p])
    dirs = np.array([s[3] for s in p])
    lens = np.array([s[4] for s in p])
    steps = np.hypot(*np.diff(mids, axis=0).T) if len(mids) > 1 else np.zeros(0)
    spine = float(steps.sum())
    ax = _axis(mids)
    med = float(np.median(dirs))
    lean_text = np.array([_signed(d, 0.0) for d in dirs])
    vs_axis = np.array([_signed(d, ax + 90.0) for d in dirs])
    unwrapped = np.array([_signed(d, med) for d in dirs])
    # spine direction near each end (first / last 1 mm of midpoints)
    cum = np.concatenate([[0.0], np.cumsum(steps)])
    # the spine's direction over its first and last third (at least 1.5 mm):
    # a fan's midpoints swing sideways, so a short window reads a fan as a turn
    span = max(spine / 3.0, min(1.5, spine))
    head = mids[cum <= span]
    tail = mids[cum >= spine - span]
    a0 = _axis(head) if len(head) > 2 else ax
    a1 = _axis(tail) if len(tail) > 2 else ax
    end_mask = (cum <= END_MM) | (cum >= spine - END_MM)
    mid_steps = steps[~(end_mask[1:] | end_mask[:-1])] if len(steps) else steps
    end_steps = steps[(end_mask[1:] | end_mask[:-1])] if len(steps) else steps
    upright = abs(ax - 90.0)
    if spine < PATCH_MM:
        role = "patch"
    elif _adiff(a0, a1) > 45.0:
        role = "curve"
    elif upright <= 20.0:
        role = "upright"
    elif upright < 65.0:
        role = "diagonal"
    else:
        role = "horizontal"
    return {
        "role": role,
        "n": len(p), "spine_mm": round(spine, 2), "width_mm": round(float(np.median(lens)), 2),
        "axis_deg": round(ax, 1),
        "cross_vs_text_deg": round(float(np.median(lean_text)), 1),
        "cross_vs_axis_deg": round(float(np.median(vs_axis)), 1),
        "drift_deg": round(float(np.percentile(unwrapped, 90) - np.percentile(unwrapped, 10)), 1),
        "spine_turn_deg": round(_adiff(a0, a1), 1),
        "max_stitch_mm": round(float(lens.max()), 2),
        "pitch_mid_mm": round(float(np.median(mid_steps)), 3) if len(mid_steps) else None,
        "pitch_end_mm": round(float(np.median(end_steps)), 3) if len(end_steps) else None,
        "start": [round(float(v), 2) for v in mids[0]], "end": [round(float(v), 2) for v in mids[-1]],
        "first_dir": round(float(dirs[0]), 1), "last_dir": round(float(dirs[-1]), 1),
        "a0": round(a0, 1), "a1": round(a1, 1),
    }


# -------------------------------------------------------------- letters
def letters(pieces: list[dict], bits: list[list[tuple]]) -> np.ndarray:
    """Connected components of the cross coverage -> label per piece."""
    import cv2
    allc = [s for p in pieces for s in p["crosses"]]   # bits can be travel: they would bridge letters
    if not allc:
        return np.zeros(0, int)
    xy = np.array([[*s[0], *s[1]] for s in allc])
    x0, y0 = xy[:, [0, 2]].min() - 1, xy[:, [1, 3]].min() - 1
    x1, y1 = xy[:, [0, 2]].max() + 1, xy[:, [1, 3]].max() + 1
    W, H = int((x1 - x0) * CROSS_PX) + 1, int((y1 - y0) * CROSS_PX) + 1
    img = np.zeros((H, W), np.uint8)
    th = max(1, int(round(0.4 * CROSS_PX)))
    for s in allc:
        a = (int((s[0][0] - x0) * CROSS_PX), int((s[0][1] - y0) * CROSS_PX))
        b = (int((s[1][0] - x0) * CROSS_PX), int((s[1][1] - y0) * CROSS_PX))
        cv2.line(img, a, b, 255, th)
    n, lab, st, _c = cv2.connectedComponentsWithStats(img, 8)
    out = []
    for p in pieces:
        votes = {}
        for s in p["crosses"]:
            m = s[2]
            px = int((m[0] - x0) * CROSS_PX), int((m[1] - y0) * CROSS_PX)
            k = int(lab[min(max(px[1], 0), H - 1), min(max(px[0], 0), W - 1)])
            votes[k] = votes.get(k, 0) + 1
        out.append(max(votes, key=votes.get))
    area = {k: st[k, cv2.CC_STAT_AREA] / CROSS_PX ** 2 for k in range(n)}
    return np.array(out), area


def _seg_dist(p, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    d = B - A
    L2 = np.maximum((d ** 2).sum(1), 1e-12)
    t = np.clip(((p - A) * d).sum(1) / L2, 0.0, 1.0)
    q = A + d * t[:, None]
    return np.hypot(*(q - p).T)


def _end_kind(cross: tuple, axis: float, width: float, i: int, ps: list, stats: list) -> str:
    """What a piece's end meets, read at its end cross's midpoint:
    `free` (nothing: a stroke terminal), `butt` (the BODY of another piece: a
    junction), `corner` / `straight` (another piece's END, axes apart by more
    / less than CORNER_DEG), `patch` (only a junction patch)."""
    p = cross[2]
    reach = 0.5 * width + 0.6
    best = None
    for j, (q, sq) in enumerate(zip(ps, stats)):
        if j == i:
            continue
        A = np.array([s[0] for s in q["crosses"]])
        B = np.array([s[1] for s in q["crosses"]])
        d = _seg_dist(p, A, B)
        k = int(np.argmin(d))
        if d[k] <= reach and (best is None or d[k] < best[0]):
            best = (float(d[k]), j, k, len(q["crosses"]))
    if best is None:
        return "free"
    _d, j, k, n = best
    if stats[j]["role"] == "patch":
        return "patch"
    if 3 <= k < n - 3:
        return "butt"
    other = stats[j]["a0"] if k < 3 else stats[j]["a1"]
    return "corner" if _adiff(axis, other) > CORNER_DEG else "straight"


def read(path: Path, rows=None) -> dict:
    """-> {letters: [{bbox, pieces: [...], cuts: [...]}], bits}"""
    rr = runs_of(Path(path))
    pieces, bits, order = [], [], 0
    for r in rr:
        fp = fuse(r["pts"])
        for ch in chains(fp):
            for part in split_turns(ch):
                spine = sum(float(np.hypot(*(b[2] - a[2]))) for a, b in zip(part, part[1:]))
                if len(part) >= MIN_PIECE and spine >= MIN_SPINE_MM:
                    pieces.append({"crosses": part, "block": r["block"], "order": order})
                    order += 1
                else:
                    bits.append(part)
    if not pieces:
        return {"letters": [], "bits": len(bits)}
    lab, area = letters(pieces, bits)
    allmid = np.array([s[2] for p in pieces for s in p["crosses"]])
    ylo, yhi = float(allmid[:, 1].min()), float(allmid[:, 1].max())
    groups: dict[int, list[dict]] = {}
    for p, k in zip(pieces, lab):
        groups.setdefault(int(k), []).append(p)
    out = []
    for k, ps in groups.items():
        if area.get(k, 0) < MIN_LETTER_MM2:
            continue
        mids = np.array([s[2] for p in ps for s in p["crosses"]])
        ends = np.array([pt for p in ps for s in p["crosses"] for pt in (s[0], s[1])])
        bx = [float(ends[:, 0].min()), float(ends[:, 1].min()), float(ends[:, 0].max()), float(ends[:, 1].max())]
        cy = (bx[1] + bx[3]) / 2
        if rows is not None:
            f = (cy - ylo) / max(yhi - ylo, 1e-9)
            if not (rows[0] <= f <= rows[1]):
                continue
        ps.sort(key=lambda p: p["order"])
        stats = [piece_stats(p["crosses"]) | {"order": p["order"], "block": p["block"]} for p in ps]
        cuts = []
        for a, b, pa, pb in zip(stats, stats[1:], ps, ps[1:]):
            gap = float(np.hypot(*(np.array(b["start"]) - np.array(a["end"]))))
            # where the next piece starts, measured against the last one's body
            body = np.array([s[2] for s in pa["crosses"]])
            near = float(np.min(np.hypot(*(body - np.array(b["start"])).T)))
            axd = _adiff(a["a1"], b["a0"])
            if near > max(a["width_mm"], 1.5):
                kind = "restart"
            elif axd > CORNER_DEG:
                kind = "corner"
            else:
                kind = "straight"
            cuts.append({"after": a["order"], "before": b["order"], "gap_mm": round(gap, 2),
                         "near_mm": round(near, 2), "axis_turn_deg": round(axd, 1),
                         "cross_turn_deg": round(_adiff(a["last_dir"], b["first_dir"]), 1),
                         "kind": kind, "at": b["start"]})
        for i, (st, p) in enumerate(zip(stats, ps)):
            if st["role"] == "patch":
                st["ends"] = []
                continue
            st["ends"] = [_end_kind(p["crosses"][0], st["a0"], st["width_mm"], i, ps, stats),
                          _end_kind(p["crosses"][-1], st["a1"], st["width_mm"], i, ps, stats)]
        out.append({"bbox": [round(v, 2) for v in bx], "pieces": stats, "cuts": cuts,
                    "crosses": [[[float(v) for v in s[0]], [float(v) for v in s[1]]]
                                for p in ps for s in p["crosses"]],
                    "piece_of_cross": [i for i, p in enumerate(ps) for _s in p["crosses"]]})
    out.sort(key=lambda L: (round(((L["bbox"][1] + L["bbox"][3]) / 2) / 5), L["bbox"][0]))
    return {"letters": out, "bits": len(bits)}


# ---------------------------------------------------------------- render
def render(res: dict, png: Path, ppm: float = 24.0) -> None:
    """Each piece in its own colour, numbered at its first cross."""
    import cv2
    Ls = res["letters"]
    if not Ls:
        return
    x0 = min(L["bbox"][0] for L in Ls) - 1
    y0 = min(L["bbox"][1] for L in Ls) - 1
    x1 = max(L["bbox"][2] for L in Ls) + 1
    y1 = max(L["bbox"][3] for L in Ls) + 1
    W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    img = np.full((H, W, 3), 255, np.uint8)
    pal = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
           (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207)]
    for L in Ls:
        for (a, b), pi in zip(L["crosses"], L["piece_of_cross"]):
            col = pal[pi % len(pal)][::-1]
            pa = (int((a[0] - x0) * ppm), int((a[1] - y0) * ppm))
            pb = (int((b[0] - x0) * ppm), int((b[1] - y0) * ppm))
            cv2.line(img, pa, pb, col, 1, cv2.LINE_AA)
        for i, p in enumerate(L["pieces"]):
            s = p["start"]
            org = (int((s[0] - x0) * ppm), int((s[1] - y0) * ppm))
            cv2.putText(img, str(i), org, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(img, str(i), org, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(png), img)


def letter_measures(L: dict) -> dict:
    """What a letter's construction does to its thread, comparable across files:

      pieces / patches   non-patch pieces, patches
      flat_share         crosses within 15 deg of the line of text, over the
                         crosses of pieces whose axis is within 45 deg of
                         vertical (stems, legs, leaning diagonals)
      drift_p90          the 90th percentile of the non-patch pieces' drift
      long_share         crosses over 5.0 mm (SPLIT_SATIN_ABOVE_MM's length)
      max_cross          the longest cross
      same_hole          rail steps under 0.1 mm over all rail steps (the
                         needle back in one hole: a fan's pivot, a pile)
      end_pitch_ratio    median cross pitch in the pieces' last END_MM over
                         the middle's (> 1: the ends sew sparser)
    """
    crosses = [(np.array(a), np.array(b)) for a, b in L["crosses"]]
    owner = L["piece_of_cross"]
    P = L["pieces"]
    flat_n = flat_k = long_k = 0
    for (a, b), pi in zip(crosses, owner):
        ln = float(np.hypot(*(b - a)))
        long_k += ln > 5.0
        if P[pi]["role"] != "patch" and abs(P[pi]["axis_deg"] - 90.0) <= 45.0:
            flat_n += 1
            flat_k += abs(_signed(_dir(b - a), 0.0)) <= 15.0
    steps = []
    for pi in range(len(P)):
        idx = [k for k, o in enumerate(owner) if o == pi]
        pts = [crosses[idx[0]][0]] + [crosses[k][1] for k in idx]
        steps += [float(np.hypot(*(pts[k + 2] - pts[k]))) for k in range(len(pts) - 2)]
    real = [p for p in P if p["role"] != "patch"]
    ratios = [p["pitch_end_mm"] / p["pitch_mid_mm"] for p in real
              if p["pitch_mid_mm"] and p["pitch_end_mm"]]
    lens = [float(np.hypot(*(b - a))) for a, b in crosses]
    return {"pieces": len(real), "patches": len(P) - len(real),
            "flat_share": round(flat_k / flat_n, 3) if flat_n else None,
            "drift_p90": round(float(np.percentile([p["drift_deg"] for p in real], 90)), 1) if real else None,
            "long_share": round(long_k / max(len(crosses), 1), 3),
            "max_cross": round(max(lens), 2) if lens else None,
            "same_hole": round(sum(s < 0.1 for s in steps) / max(len(steps), 1), 3),
            "end_pitch_ratio": round(float(np.median(ratios)), 2) if ratios else None,
            "crosses": len(crosses)}


def word_measures(Ls: list[dict]) -> dict:
    """One row for a set of letters (the doc's tables): pieces, patches,
    piece ends by kind, pieces whose spine turns over 45 deg (a corner or
    curve sewn through), and the crosses of LEANING strokes (non-patch
    pieces whose axis is 12-65 deg off vertical): share within 15 deg of the
    line of text and the median angle from it; plus `letter_measures`' thread
    numbers pooled (long_share, max_cross, same_hole by cross count)."""
    ends: dict[str, int] = {}
    real = patches = turned = 0
    lean, per = [], []
    long_k = n = same = steps = 0
    max_cross = 0.0
    for L in Ls:
        k = 0
        for p in L["pieces"]:
            if p["role"] == "patch":
                patches += 1
                continue
            real += 1
            k += 1
            turned += p["spine_turn_deg"] > 45.0
            for e in p.get("ends", []):
                ends[e] = ends.get(e, 0) + 1
        per.append(k)
        for (a, b), i in zip(L["crosses"], L["piece_of_cross"]):
            p = L["pieces"][i]
            if p["role"] != "patch" and 12.0 <= abs(p["axis_deg"] - 90.0) <= 65.0:
                lean.append(abs(_signed(_dir(np.array(b) - np.array(a)), 0.0)))
        m = letter_measures(L)
        long_k += m["long_share"] * m["crosses"]
        n += m["crosses"]
        same += m["same_hole"] * m["crosses"]
        max_cross = max(max_cross, m["max_cross"] or 0.0)
    lean = np.array(lean)
    return {"letters": len(Ls), "pieces": real, "per_letter": per, "patches": patches,
            "turned": turned, "ends": ends,
            "lean_flat": round(float((lean <= 15.0).mean()), 3) if len(lean) else None,
            "lean_med_deg": round(float(np.median(lean)), 1) if len(lean) else None,
            "lean_crosses": int(len(lean)),
            "long_share": round(long_k / max(n, 1), 3), "max_cross": round(max_cross, 2),
            "same_hole": round(same / max(n, 1), 4), "crosses": n}


def summary(res: dict) -> dict:
    Ps = [p for L in res["letters"] for p in L["pieces"]]
    Cs = [c for L in res["letters"] for c in L["cuts"]]
    if not Ps:
        return {}
    kinds = {}
    for c in Cs:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    return {"letters": len(res["letters"]), "pieces": len(Ps), "bits": res["bits"],
            "spine_med_mm": round(float(np.median([p["spine_mm"] for p in Ps])), 2),
            "spine_max_mm": round(float(max(p["spine_mm"] for p in Ps)), 2),
            "cuts": kinds,
            "roles": {r: sum(1 for p in Ps if p["role"] == r)
                      for r in ("upright", "diagonal", "horizontal", "curve", "patch")},
            "ends": {k: sum(1 for p in Ps for e in p.get("ends", []) if e == k)
                     for k in ("free", "butt", "corner", "straight", "patch")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--rows", type=float, nargs=2)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--min-height", type=float, default=0.0,
                    help="keep letters at least this tall (mm)")
    ap.add_argument("--table", action="store_true", help="one `word_measures` row, nothing else")
    a = ap.parse_args(argv)
    res = read(a.file, a.rows)
    res["letters"] = [L for L in res["letters"] if L["bbox"][3] - L["bbox"][1] >= a.min_height]
    if a.table:
        print(json.dumps(word_measures(res["letters"])))
        if a.png:
            render(res, a.png)
        return 0
    print(json.dumps(summary(res)))
    for i, L in enumerate(res["letters"]):
        print(f"letter {i} bbox {L['bbox']} pieces {len(L['pieces'])}")
        for j, p in enumerate(L["pieces"]):
            print(f"  {j:2d} {p['role']:10s} n={p['n']:3d} spine={p['spine_mm']:5.2f} w={p['width_mm']:.2f} "
                  f"ax={p['axis_deg']:5.1f} vsText={p['cross_vs_text_deg']:6.1f} "
                  f"vsAxis={p['cross_vs_axis_deg']:6.1f} drift={p['drift_deg']:5.1f} "
                  f"turn={p['spine_turn_deg']:5.1f} max={p['max_stitch_mm']:.2f} "
                  f"pitch m/e={p['pitch_mid_mm']}/{p['pitch_end_mm']} ends={p.get('ends')}")
        for c in L["cuts"]:
            print(f"     cut {c['kind']:8s} gap={c['gap_mm']:.2f} near={c['near_mm']:.2f} "
                  f"axis_turn={c['axis_turn_deg']:.0f} cross_turn={c['cross_turn_deg']:.0f} at {c['at']}")
    if a.json:
        a.json.write_text(json.dumps(res), encoding="utf-8")
    if a.png:
        render(res, a.png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
