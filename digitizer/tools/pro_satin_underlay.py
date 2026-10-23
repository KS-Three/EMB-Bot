#!/usr/bin/env python
"""What is sewn UNDER each satin column of a stitch file, by column length
and width, read off the bare stream.

Built 2026-10-22 for the short-column underlay work: the settings audit
(`docs/settings-vs-pro-2026-10-21.md`, rows 5a-5b) read the professional's
columns with a scratch classifier that was never committed. This is that
reading as a tool, so ours and his are measured by one rule and the table it
prints can be re-run.

    .venv/Scripts/python -m tools.pro_satin_underlay FILE [FILE ...] [--json OUT]
        [--min-crosses 6] [--table]

**A satin column, on the needle-down path.** Three consecutive penetrations
form a CROSS when the middle one sits off the chord of the other two by at
least `MIN_WIDTH_MM` (that offset is the width), both legs are in
[`MIN_LEG_MM`, `MAX_LEG_MM`], and the chord -- the step along the rail -- is at
most `MAX_SPACING_MM`: a satin top is laid at 0.3-0.5 mm, a zigzag underlay at
1.5 mm and up, and the spacing cap is what tells them apart. A COLUMN is a run
of `min_crosses` or more such crosses whose offsets alternate side; it is cut
where its spine turns more than `SPLIT_TURN_DEG` so an L sewn in one go reads
as two columns, the way our engine would construct it. Length is the spine's,
width the median cross.

**Its underlay.** Stitches sewn EARLIER in the same colour block, not part of
any column themselves, that lie inside the column's footprint (the spine
buffered by half the width plus `FOOT_MM`). They are the column's underlay
when their projection onto the spine covers at least `COVER_FRAC` of its
length. Each such stitch is classed by where its ends sit across the column:
ZIGZAG when the two ends are on opposite rails (each past `ZZ_FRAC` of the
half-width), EDGE when both sit past `EDGE_FRAC` on one side, CENTRE
otherwise. A column reports every class that holds `KIND_SHARE` of its
underlay stitches, so "edge + zigzag" is a reading, not a tie-break. Pitch is
the along-spine advance per zigzag stitch and the stitch length of a run.

What it cannot say: whether a centre walk was a travel line the pro routed
under the column on purpose -- on the cloth it does the same job, and the
audit's row 5b carries that caveat. A column the pro sewed over a FILL reads
the fill's rows as underlay (dense, same block) only when they lie inside its
footprint and were sewn first; the fill's own crosses are not columns here
because fill rows do not alternate at `MAX_SPACING_MM`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MIN_LEG_MM = 0.4          # tools/satin_columns.py's gates
MAX_LEG_MM = 12.0
MIN_WIDTH_MM = 0.5        # sewable satin; under it is bean / fill turns
MAX_SPACING_MM = 0.6      # rail step of a satin TOP; zigzag underlay is 1.4+
SPLIT_TURN_DEG = 60.0     # spine turn that ends a column
FOOT_MM = 0.15            # footprint margin past the rails
COVER_FRAC = 0.5          # underlay must cover this much of the spine
ZZ_FRAC = 0.25            # a zigzag leg's ends sit past this, opposite sides
EDGE_FRAC = 0.5           # an edge run's stitch sits past this, one side
KIND_SHARE = 0.25         # a class is reported at this share of the stitches
MIN_CLIP_MM = 0.2         # a stitch counts once this much of it lies in the footprint
ZZ_MIN_ADVANCE_MM = 1.0   # rail-to-rail under this advance is satin, not a zigzag leg...
DENSE_RUN = 3             # ...once three such stitches run in a row (one rung is a ladder)
LENGTH_BANDS = ((0.0, 2.5), (2.5, 5.0), (5.0, 10.0), (10.0, math.inf))
WIDTH_BANDS = ((0.0, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 5.0), (5.0, math.inf))


def _band(v: float, bands) -> str:
    for lo, hi in bands:
        if lo <= v < hi:
            return f"{lo:g}-{hi:g}" if hi != math.inf else f">={lo:g}"
    return "?"


def blocks_from_file(path: Path) -> list[list[list[tuple[float, float]]]]:
    """-> colour blocks, each a list of needle-down passes (a JUMP or TRIM
    ends a pass, a COLOR_CHANGE ends the block). mm."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    blocks: list[list[list[tuple[float, float]]]] = [[]]
    cur: list[tuple[float, float]] = []

    def flush():
        nonlocal cur
        if len(cur) >= 2:
            blocks[-1].append(cur)
        cur = []

    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            continue
        flush()
        if cmd == pystitch.COLOR_CHANGE:
            blocks.append([])
    flush()
    return [b for b in blocks if b]


def blocks_from_plan(plan) -> list[list[list[tuple[float, float]]]]:
    """Our own plan by the file's rules: a run's `jump`/`trim` ends a pass,
    a new block a block. Kinds are NOT consulted -- that is the point."""
    blocks = []
    for b in plan.blocks:
        passes: list[list[tuple[float, float]]] = []
        cur: list[tuple[float, float]] = []
        for r in b.runs:
            if r.jump or r.trim:
                if len(cur) >= 2:
                    passes.append(cur)
                cur = []
            cur.extend(tuple(p) for p in r.points)
        if len(cur) >= 2:
            passes.append(cur)
        if passes:
            blocks.append(passes)
    return blocks


def columns_in_pass(pts: list[tuple[float, float]], min_crosses: int) -> list[dict]:
    """Columns of one pass: {i0, i1 (apex index range, inclusive), spine,
    width, length}."""
    n = len(pts)
    if n < min_crosses + 2:
        return []
    p = np.asarray(pts, float)
    a, b, c = p[:-2], p[1:-1], p[2:]
    u, v, ac = b - a, c - b, c - a
    lu, lv, lac = np.hypot(*u.T), np.hypot(*v.T), np.hypot(*ac.T)
    area2 = ac[:, 0] * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * ac[:, 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        signed = np.where(lac > 1e-9, area2 / np.maximum(lac, 1e-9), 0.0)
    width = np.abs(signed)
    ok = ((lu >= MIN_LEG_MM) & (lv >= MIN_LEG_MM) & (lu <= MAX_LEG_MM) & (lv <= MAX_LEG_MM)
          & (width >= MIN_WIDTH_MM) & (lac <= MAX_SPACING_MM))
    side = np.sign(signed)
    out: list[dict] = []
    i = 0
    while i < len(ok):
        if not ok[i]:
            i += 1
            continue
        j = i + 1
        while j < len(ok) and ok[j] and side[j] == -side[j - 1]:
            j += 1
        if j - i >= min_crosses:
            # apex k of cross k sits at p[k+1]; the spine point is the midpoint
            # of the apex and its chord's midpoint
            mids = (b[i:j] + (a[i:j] + c[i:j]) / 2.0) / 2.0
            out += _split_on_turns(mids, width[i:j], i, min_crosses)
        i = j
    return out


def _split_on_turns(mids: np.ndarray, widths: np.ndarray, i0: int, min_crosses: int) -> list[dict]:
    """Cut a run of crosses where the spine heading turns by SPLIT_TURN_DEG,
    read over a window of crosses either side (one cross is noise)."""
    n = len(mids)
    w = max(3, min(8, n // 4))
    cuts = [0]
    if n >= 2 * w + 2:
        k = w
        while k < n - w:
            d0 = mids[k] - mids[k - w]
            d1 = mids[k + w] - mids[k]
            n0, n1 = np.hypot(*d0), np.hypot(*d1)
            if n0 > 1e-6 and n1 > 1e-6:
                cosang = float(np.dot(d0, d1) / (n0 * n1))
                if cosang < math.cos(math.radians(SPLIT_TURN_DEG)):
                    cuts.append(k)
                    k += w
                    continue
            k += 1
    cuts.append(n)
    out = []
    for s, e in zip(cuts, cuts[1:]):
        if e - s < min_crosses:
            continue
        m = mids[s:e]
        length = float(np.hypot(*np.diff(m, axis=0).T).sum())
        out.append({"i0": i0 + s, "i1": i0 + e - 1, "spine": m,
                    "width": float(np.median(widths[s:e])), "length": length})
    return out


def _underlay_of(col: dict, earlier: list[np.ndarray]) -> dict:
    """Classify the earlier stitches under one column."""
    spine = col["spine"]
    if len(spine) < 2 or col["length"] < 1e-6:
        return {"covered": 0.0, "kinds": [], "n": 0}
    half = col["width"] / 2.0
    line = LineString(spine)
    foot = line.buffer(half + FOOT_MM, cap_style=2)
    # Local frame per stitch: signed offset across the spine, position along.
    # A stitch is CLIPPED to the footprint first: under a short column most
    # of a 2 mm run stitch lies outside it, and dropping every stitch with an
    # end outside read every column under 2.5 mm as bare (first cut of this
    # tool, 2026-10-22).
    from shapely.geometry import Point
    bx0, by0, bx1, by1 = foot.bounds
    segs = []  # (s0, s1, off0, off1, length, (pa, pb) mm)
    dense = 0
    for arr in earlier:
        if len(arr) < 2:
            continue
        near = ((arr[:, 0] >= bx0 - 1) & (arr[:, 0] <= bx1 + 1)
                & (arr[:, 1] >= by0 - 1) & (arr[:, 1] <= by1 + 1))
        if not near.any():
            continue
        chunk = []   # (seg, is_dense_cross) in stitch order
        for k in range(len(arr) - 1):
            if not (near[k] or near[k + 1]):
                chunk.append(None)
                continue
            seg = LineString([arr[k], arr[k + 1]])
            clip = seg.intersection(foot)
            if clip.is_empty or clip.geom_type != "LineString" or clip.length < MIN_CLIP_MM:
                chunk.append(None)
                continue
            pa, pb = clip.coords[0], clip.coords[-1]
            sa, sb = line.project(Point(pa)), line.project(Point(pb))
            oa, ob = _signed_offset(line, spine, pa, sa), _signed_offset(line, spine, pb, sb)
            f0, f1 = oa / max(half, 1e-6), ob / max(half, 1e-6)
            cross = (f0 * f1 < 0 and abs(f0) >= ZZ_FRAC and abs(f1) >= ZZ_FRAC
                     and abs(sb - sa) < ZZ_MIN_ADVANCE_MM)
            chunk.append(((sa, sb, oa, ob, float(clip.length), (pa, pb)), cross))
        # Rail-to-rail thread advancing under a millimetre, THREE OR MORE
        # stitches in a row, is satin: a fan corner's long outer steps, a
        # taper wedge, an earlier column's crosses the column mask did not
        # reach. One such rung between rail steps is our own ladder
        # underlay (`_stroke_underlay`'s zigzag: a cross at each station,
        # then a step along the rail), and stays.
        i = 0
        while i < len(chunk):
            if chunk[i] is None or not chunk[i][1]:
                if chunk[i] is not None:
                    segs.append(chunk[i][0])
                i += 1
                continue
            j = i
            while j < len(chunk) and chunk[j] is not None and chunk[j][1]:
                j += 1
            if j - i >= DENSE_RUN:
                dense += j - i
            else:
                segs.extend(chunk[k][0] for k in range(i, j))
            i = j
    if not segs:
        return {"covered": 0.0, "kinds": [], "n": 0, "dense": dense}
    # coverage along the spine
    iv = sorted((min(s0, s1), max(s0, s1)) for s0, s1, *_ in segs)
    covered, cs, ce = 0.0, iv[0][0], iv[0][1]
    for s, e in iv[1:]:
        if s > ce:
            covered += ce - cs
            cs, ce = s, e
        else:
            ce = max(ce, e)
    covered += ce - cs
    frac = covered / col["length"]
    zz, edge, centre = [], [], []
    for s0, s1, o0, o1, ln, _xy in segs:
        f0, f1 = o0 / max(half, 1e-6), o1 / max(half, 1e-6)
        if f0 * f1 < 0 and abs(f0) >= ZZ_FRAC and abs(f1) >= ZZ_FRAC:
            zz.append(abs(s1 - s0))
        elif abs(f0) >= EDGE_FRAC and abs(f1) >= EDGE_FRAC and f0 * f1 > 0:
            edge.append(ln)
        else:
            centre.append(ln)
    n = len(segs)
    kinds = []
    if len(zz) >= KIND_SHARE * n:
        kinds.append("zigzag")
    if len(edge) >= KIND_SHARE * n:
        kinds.append("edge")
    if len(centre) >= KIND_SHARE * n:
        kinds.append("centre")
    return {"covered": frac, "kinds": kinds, "n": n, "dense": dense,
            "segs_xy": [xy for *_r, xy in segs],
            "zz_pitch": float(np.median(zz)) if zz else None,
            "run_stitch": float(np.median(centre + edge)) if (centre or edge) else None}


def _signed_offset(line: LineString, spine: np.ndarray, p, s: float) -> float:
    q = line.interpolate(s)
    # tangent at s
    s2 = min(line.length, s + 0.2) if s + 0.2 <= line.length else max(0.0, s - 0.2)
    q2 = line.interpolate(s2)
    tx, ty = (q2.x - q.x), (q2.y - q.y)
    if s2 < s:
        tx, ty = -tx, -ty
    tn = math.hypot(tx, ty) or 1.0
    dx, dy = p[0] - q.x, p[1] - q.y
    return (tx * dy - ty * dx) / tn


def read_columns(blocks, min_crosses: int = 6, keep_segs: bool = False) -> list[dict]:
    """Every column of a design with its underlay reading. `keep_segs`: each
    row also carries `under_segs`, the counted underlay stitches clipped to
    the footprint (mm, file frame), for a picture."""
    rows: list[dict] = []
    for bi, passes in enumerate(blocks):
        arrs = [np.asarray(ps, float) for ps in passes]
        cols = []
        for pi, ps in enumerate(passes):
            for c in columns_in_pass(ps, min_crosses):
                c["pass"] = pi
                cols.append(c)
        # mask: penetrations that are part of a column (apex range +-1)
        masks = [np.zeros(len(a), bool) for a in arrs]
        for c in cols:
            masks[c["pass"]][c["i0"]:c["i1"] + 3] = True
        for c in cols:
            earlier = []
            for pi in range(c["pass"] + 1):
                a, m = arrs[pi], masks[pi]
                stop = len(a) if pi < c["pass"] else c["i0"] + 1
                keep = ~m[:stop]
                # split the pass into stretches of non-column stitches
                idx = np.flatnonzero(keep)
                if not len(idx):
                    continue
                breaks = np.flatnonzero(np.diff(idx) > 1)
                for chunk in np.split(idx, breaks + 1):
                    if len(chunk) >= 2:
                        earlier.append(a[chunk])
            u = _underlay_of(c, earlier)
            rows.append({"block": bi, "length": round(c["length"], 2),
                         "width": round(c["width"], 2),
                         "len_band": _band(c["length"], LENGTH_BANDS),
                         "wid_band": _band(c["width"], WIDTH_BANDS),
                         "bare": u["covered"] < COVER_FRAC,
                         "covered": round(u["covered"], 2), "kinds": u["kinds"],
                         "zz_pitch": u.get("zz_pitch"), "run_stitch": u.get("run_stitch"),
                         **({"under_segs": u.get("segs_xy", [])} if keep_segs else {})})
    return rows


def table(rows: list[dict]) -> dict:
    """length band x width band -> counts and shares."""
    out: dict = {}
    for r in rows:
        key = (r["len_band"], r["wid_band"])
        t = out.setdefault(key, {"n": 0, "bare": 0, "centre": 0, "edge": 0, "zigzag": 0,
                                 "zz": [], "run": []})
        t["n"] += 1
        if r["bare"]:
            t["bare"] += 1
        else:
            for k in r["kinds"]:
                t[k] += 1
            if r["zz_pitch"]:
                t["zz"].append(r["zz_pitch"])
            if r["run_stitch"]:
                t["run"].append(r["run_stitch"])
    res = {}
    for key, t in out.items():
        n = t["n"]
        res[f"{key[0]}|{key[1]}"] = {
            "n": n, "bare_pct": round(100 * t["bare"] / n, 1),
            "centre_pct": round(100 * t["centre"] / n, 1),
            "edge_pct": round(100 * t["edge"] / n, 1),
            "zigzag_pct": round(100 * t["zigzag"] / n, 1),
            "zz_pitch_med": round(float(np.median(t["zz"])), 2) if t["zz"] else None,
            "run_stitch_med": round(float(np.median(t["run"])), 2) if t["run"] else None,
        }
    return res


def print_table(res: dict) -> None:
    hdr = f"{'length':>8} {'width':>8} {'n':>5} {'bare%':>6} {'ctr%':>6} {'edge%':>6} {'zz%':>6} {'zz pitch':>9} {'run st':>7}"
    print(hdr)
    order = {f"{lo:g}-{hi:g}" if hi != math.inf else f">={lo:g}": k for k, (lo, hi) in enumerate(LENGTH_BANDS)}
    worder = {f"{lo:g}-{hi:g}" if hi != math.inf else f">={lo:g}": k for k, (lo, hi) in enumerate(WIDTH_BANDS)}
    for key in sorted(res, key=lambda k: (order[k.split("|")[0]], worder[k.split("|")[1]])):
        t = res[key]
        lb, wb = key.split("|")
        print(f"{lb:>8} {wb:>8} {t['n']:>5} {t['bare_pct']:>6} {t['centre_pct']:>6} {t['edge_pct']:>6} "
              f"{t['zigzag_pct']:>6} {str(t['zz_pitch_med']):>9} {str(t['run_stitch_med']):>7}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--min-crosses", type=int, default=6)
    ap.add_argument("--per-file", action="store_true")
    a = ap.parse_args(argv)
    allrows: list[dict] = []
    per = {}
    for f in a.files:
        rows = read_columns(blocks_from_file(Path(f)), a.min_crosses)
        for r in rows:
            r["file"] = Path(f).name
        allrows += rows
        n = len(rows)
        bare = sum(r["bare"] for r in rows)
        short = [r for r in rows if r["length"] < 5.0]
        sb = sum(r["bare"] for r in short)
        per[Path(f).name] = {"columns": n, "bare_pct": round(100 * bare / n, 1) if n else None,
                             "short": len(short),
                             "short_bare_pct": round(100 * sb / len(short), 1) if short else None}
        print(f"{Path(f).name}: {n} columns, bare {bare} ({per[Path(f).name]['bare_pct']}%), "
              f"<5 mm: {len(short)} bare {sb} ({per[Path(f).name]['short_bare_pct']}%)")
        if a.per_file:
            print_table(table(rows))
    print()
    res = table(allrows)
    print_table(res)
    if a.json:
        Path(a.json).write_text(json.dumps({"per_file": per, "table": res, "columns": allrows},
                                           indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
