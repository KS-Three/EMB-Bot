"""sequence_pro: read a machine file's SEW ORDER block by block, same reader both sides.

    python -m tools.sequence_pro FILE [FILE ...] [--blocks] [--json OUT] [--render DIR]

Built 2026-10-25 for queue item L10 ("sequence like the pro"): before
reordering anything, read how the professional orders a job and how we do,
with one reader on both DSTs (read the DST, never the PES: the PES reader
reports a TRIM at every jump). Each file is read in its own frame.

What it reads, per COLOUR BLOCK (a COLOR_CHANGE ends one):

- stitches, trims (a run of TRIM records counts once), needle-up moves (a
  JUMP/TRIM stretch between two penetrations, trimmed or not) and their
  straight length in mm;
- where the block starts and ends, as a fraction of the design's own extents
  (x 0 = left, y 0 = top), and the straight hop from the previous block's
  last penetration to this block's first;
- PIECES: connected parts of the block's own footprint (every needle-down
  segment drawn one thread, 0.4 mm, wide at 10 px/mm, then opened with a
  0.6 mm square so a lone run line -- a walk between pieces -- drops out and
  the bodies it joined come apart). Each penetration takes the piece under
  it, or none. A VISIT is a maximal stretch of penetrations in one piece;
  visits - pieces = revisits. A needle-down walk ACROSS another piece reads
  as a visit to it, so revisits overcount on files that walk a lot;
- the moves BETWEEN visits of different pieces: needle-up mm (flown), needle-
  down mm (walked: the stitches laid outside any piece on the way), and how
  many were trimmed. `trims - inter_trims` is the cuts INSIDE one piece;
- ORDER, three ways over the same pieces, each the sum of the gaps between
  consecutive pieces' footprints (polygon distance, so independent of where
  each was entered or left): the file's own order (`order_gap_mm`), stage
  7's rule (`sweep_gap_mm`: start at the piece farthest from the block's
  centroid, then nearest-neighbour), and the cap rule the pro's hat files
  follow (`centre_out_gap_mm`: rows bottom-up; in a row the piece nearest
  the design's vertical centreline, then the left side outward, then the
  right side outward);
- WHY each piece-to-piece cut happened (`cut_*`, counted per step), read
  against "within reach": a gap of `TRIM_AT_MM` or less whose straight
  thread lies on thread (any colour, sewn before or after) -- the walk rule
  `cut_every_jump` uses and the pro keeps (he never lays thread across bare
  fabric). `next_in_reach`: the piece entered was within reach of the one
  left (the cut is about where the needle LEFT, not order);
  `skipped_reach`: an unsewn piece within reach was passed over (ORDER);
  `dead_end`: nothing unsewn was within reach. `reach_first_trims` is a
  greedy tour of the same pieces that always takes a reachable piece when
  one is left: what an order change alone could reach, ignoring entry and
  exit points;
- the share of piece-to-piece steps on one line (y-overlap >= 50%) that go
  left-to-right.

It reads; it does not judge. No threshold here says an order is "wrong".

Measured with it 2026-10-25 (`docs/sequence-like-pro-2026-10-25.md`) on
five hat jobs: the pro sews the cap rule on all five, and it costs him
1.7-5x the sweep's gap; ours passes over a reachable piece 18 times against
his 2, out of 145 excess cuts. Order is not the trim gap; cuts inside one
piece and isolated pieces are.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PPM = 10.0
THREAD_MM = 0.4
OPEN_MM = 0.6
MIN_PIECE_PTS = 6
TRIM_AT_MM = 3.0   # the hat preset's trim distance (fabrics.structured_cap)
COVER = 0.9        # tools.trim_classes' "lies on thread"


def read(path) -> dict:
    """A machine file -> {"blocks": [[(x, y, cmd)], ...], "extents": (x0, y0, x1, y1)} in mm, y down."""
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
        elif cmd == pystitch.END:
            break
        else:
            cur.append((x / 10.0, y / 10.0, cmd))
    blocks.append(cur)
    blocks = [b for b in blocks if any(c == pystitch.STITCH for *_xy, c in b)]
    pts = [(x, y) for b in blocks for x, y, c in b if c == pystitch.STITCH]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return {"blocks": blocks, "extents": (min(xs), min(ys), max(xs), max(ys))}


def moves(block) -> list[dict]:
    """The block as a list of penetrations and the move INTO each one:
    {"p": (x, y), "up": bool, "trim": bool}. The first penetration's move is
    the entry from wherever the needle was (up)."""
    import pystitch
    out, up, trim = [], True, False
    for x, y, c in block:
        if c == pystitch.STITCH:
            out.append({"p": (x, y), "up": up, "trim": trim})
            up = trim = False
        elif c == pystitch.JUMP:
            up = True
        elif c == pystitch.TRIM:
            up = trim = True
    return out


def pieces(mv, extents):
    """Label array + per-penetration piece id (0 = none) for one block."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = extents
    x0 -= 2
    y0 -= 2
    w = int((x1 - x0 + 2) * PPM) + 2
    h = int((y1 - y0 + 2) * PPM) + 2
    im = np.zeros((h, w), np.uint8)
    lw = max(1, int(round(THREAD_MM * PPM)))

    def px(p):
        return int(round((p[0] - x0) * PPM)), int(round((p[1] - y0) * PPM))

    for a, b in zip(mv, mv[1:]):
        if not b["up"]:
            cv2.line(im, px(a["p"]), px(b["p"]), 1, lw)
    k = int(round(OPEN_MM * PPM))
    body = cv2.morphologyEx(im, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    n, lab = cv2.connectedComponents(body, connectivity=8)
    ids = []
    for m in mv:
        qx, qy = px(m["p"])
        v = lab[max(0, qy - 2):qy + 3, max(0, qx - 2):qx + 3]
        v = v[v > 0]
        ids.append(int(np.bincount(v).argmax()) if v.size else 0)
    return lab, ids, (x0, y0)


def _piece_geoms(lab, ids, origin):
    """piece id -> shapely geometry (mm) of its footprint pixels."""
    import cv2
    import numpy as np
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    out = {}
    x0, y0 = origin
    for pid in sorted(set(i for i in ids if i)):
        mask = (lab == pid).astype(np.uint8)
        cs, _h = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polys = []
        for c in cs:
            c = c.reshape(-1, 2)
            if len(c) >= 3:
                pg = Polygon([(x0 + x / PPM, y0 + y / PPM) for x, y in c]).buffer(0)
                if not pg.is_empty:
                    polys.append(pg)
        if polys:
            out[pid] = unary_union(polys)
    return out


def footprint(blocks, extents):
    """-> on_thread(a, b): whether >= `COVER` of the straight segment a-b
    lies on thread, any block, sewn before or after (every needle-down
    segment in the file, one thread wide) -- the walk rule: a hop whose
    thread lands on work can be sewn through, one on bare fabric is cut."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = extents
    x0 -= 2
    y0 -= 2
    w = int((x1 - x0 + 2) * PPM) + 2
    h = int((y1 - y0 + 2) * PPM) + 2
    im = np.zeros((h, w), np.uint8)
    lw = max(1, int(round(THREAD_MM * PPM)))

    def px(p):
        return int(round((p[0] - x0) * PPM)), int(round((p[1] - y0) * PPM))

    for block in blocks:
        mv = moves(block)
        for a, b in zip(mv, mv[1:]):
            if not b["up"]:
                cv2.line(im, px(a["p"]), px(b["p"]), 1, lw)

    def on_thread(a, b) -> bool:
        n = max(2, int(math.dist(a, b) / 0.1))
        hit = 0
        for s in range(n + 1):
            t = s / n
            qx, qy = px((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            hit += bool(im[min(max(qy, 0), h - 1), min(max(qx, 0), w - 1)])
        return hit / (n + 1) >= COVER

    return on_thread


def read_block(block, extents, on_thread=None) -> dict:
    from shapely.ops import nearest_points
    mv = moves(block)
    st = [m for m in mv]
    up_moves = [(a, b) for a, b in zip(mv, mv[1:]) if b["up"]]
    trims = sum(1 for _a, b in up_moves if b["trim"])
    up_mm = sum(math.dist(a["p"], b["p"]) for a, b in up_moves)
    lab, ids, origin = pieces(mv, extents)
    # visits: maximal stretches of one piece id (0s between visits are travel)
    visits = []
    for i, pid in enumerate(ids):
        if pid == 0:
            continue
        if visits and visits[-1]["pid"] == pid:
            visits[-1]["last"] = i
            visits[-1]["n"] += 1
        else:
            visits.append({"pid": pid, "first": i, "last": i, "n": 1})
    counts = {}
    for v in visits:
        counts[v["pid"]] = counts.get(v["pid"], 0) + v["n"]
    keep = {p for p, n in counts.items() if n >= MIN_PIECE_PTS}
    visits = [v for v in visits if v["pid"] in keep]
    # merge consecutive visits of one piece left after dropping crumbs
    merged = []
    for v in visits:
        if merged and merged[-1]["pid"] == v["pid"]:
            merged[-1]["last"] = v["last"]
            merged[-1]["n"] += v["n"]
        else:
            merged.append(dict(v))
    visits = merged
    inter_up = inter_down = 0.0
    inter_trims = inter_n = 0
    cut_steps = []          # (index into visits of the piece left, of the piece entered)
    for k, (va, vb) in enumerate(zip(visits, visits[1:])):
        if va["pid"] == vb["pid"]:
            continue
        inter_n += 1
        cut = False
        for j in range(va["last"] + 1, vb["first"] + 1):
            d = math.dist(mv[j - 1]["p"], mv[j]["p"])
            if mv[j]["up"]:
                inter_up += d
                inter_trims += mv[j]["trim"]
                cut |= mv[j]["trim"]
            else:
                inter_down += d
        if cut:
            cut_steps.append(k)
    geoms = _piece_geoms(lab, list(keep), origin)
    seq = [v["pid"] for v in visits if v["pid"] in geoms]
    order_gap = sum(geoms[a].distance(geoms[b]) for a, b in zip(seq, seq[1:]) if a != b)
    # stage 7's own rule over the same pieces: start at the piece farthest
    # from the block's centroid, then nearest-neighbour (a SWEEP: no fly-back)
    sweep_gap = 0.0
    if geoms:
        from shapely.ops import unary_union
        ctr = unary_union(list(geoms.values())).centroid
        cur = max(geoms, key=lambda p: (round(geoms[p].centroid.distance(ctr), 6), -p))
        left = set(geoms) - {cur}
        while left:
            nxt = min(left, key=lambda p: (geoms[cur].distance(geoms[p]), p))
            sweep_gap += geoms[cur].distance(geoms[nxt])
            left.discard(nxt)
            cur = nxt
    # ORDER HEADROOM: the fewest piece-to-piece cuts ANY order could sew
    # these pieces with, when a gap of `TRIM_AT_MM` or less whose thread
    # lies on work (`on_thread`) is sewn through and every other gap is cut
    # -- the components of the "within reach" graph, minus one. A file whose
    # `inter_trims` sit at this floor has nothing an order can take off.
    parent = {p: p for p in geoms}

    def root(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    ids_ = sorted(geoms)
    reach: dict[int, set] = {p: set() for p in ids_}
    for i, a in enumerate(ids_):
        for b in ids_[i + 1:]:
            d = geoms[a].distance(geoms[b])
            if d > TRIM_AT_MM:
                continue
            if d > THREAD_MM and on_thread is not None:
                qa, qb = nearest_points(geoms[a], geoms[b])
                if not on_thread((qa.x, qa.y), (qb.x, qb.y)):
                    continue
            reach[a].add(b)
            reach[b].add(a)
            parent[root(a)] = root(b)
    min_trims = max(0, len({root(p) for p in geoms}) - 1)
    # Why each piece-to-piece cut happened, read against the pieces still
    # unsewn at that moment: `next_in_reach` -- the piece entered was within
    # reach of the one left, so the cut is where the needle LEFT, not order;
    # `skipped_reach` -- an unsewn piece within reach was passed over for a
    # farther one (order); `dead_end` -- nothing unsewn was within reach (the
    # tour stranded itself, or the piece stands alone).
    why = {"next_in_reach": 0, "skipped_reach": 0, "dead_end": 0}
    vis_ids = [v["pid"] for v in visits]
    for k in cut_steps:
        a, b = vis_ids[k], vis_ids[k + 1]
        if a not in reach or b not in reach:
            continue
        done = set(vis_ids[:k + 1])
        todo_k = set(reach) - done
        if b in reach[a]:
            why["next_in_reach"] += 1
        elif reach[a] & todo_k:
            why["skipped_reach"] += 1
        else:
            why["dead_end"] += 1
    # ...and what an ORDER change alone reaches in practice: a greedy tour of
    # the same pieces from the file's own first piece -- next, the nearest
    # unsewn piece within reach of the one just sewn, else the nearest unsewn
    # piece anywhere, for one cut. No entry/exit constraint, so it is a
    # floor for the rule, not a plan.
    reach_trims = 0
    if seq:
        cur, todo = seq[0], set(geoms) - {seq[0]}
        while todo:
            near = reach[cur] & todo
            pool = near or todo
            reach_trims += not near
            cur = min(pool, key=lambda q: (geoms[cur].distance(geoms[q]), q))
            todo.discard(cur)
    # the cap rule the pro's hat files follow, applied to the same pieces:
    # rows bottom-up; in a row, the piece nearest the design's vertical
    # centreline, then that row's left side outward, then its right side
    co_gap = 0.0
    if len(geoms) > 1:
        xc = (extents[0] + extents[2]) / 2.0
        rows: list[list[int]] = []
        for pid in sorted(geoms, key=lambda p: -geoms[p].centroid.y):
            b = geoms[pid].bounds
            for row in rows:
                y0 = min(geoms[q].bounds[1] for q in row)
                y1 = max(geoms[q].bounds[3] for q in row)
                if min(b[3], y1) - max(b[1], y0) >= 0.5 * min(b[3] - b[1], y1 - y0):
                    row.append(pid)
                    break
            else:
                rows.append([pid])
        co = []
        for row in rows:
            mid = min(row, key=lambda p: (abs(geoms[p].centroid.x - xc), p))
            cx = geoms[mid].centroid.x
            left = sorted((p for p in row if p != mid and geoms[p].centroid.x <= cx),
                          key=lambda p: -geoms[p].centroid.x)
            right = sorted((p for p in row if p != mid and geoms[p].centroid.x > cx),
                           key=lambda p: geoms[p].centroid.x)
            co += [mid, *left, *right]
        co_gap = sum(geoms[a].distance(geoms[b]) for a, b in zip(co, co[1:]))
    # left-to-right on a line
    ltr = steps = 0
    for a, b in zip(seq, seq[1:]):
        if a == b:
            continue
        ga, gb = geoms[a].bounds, geoms[b].bounds
        ov = min(ga[3], gb[3]) - max(ga[1], gb[1])
        hmin = min(ga[3] - ga[1], gb[3] - gb[1])
        if hmin > 0 and ov >= 0.5 * hmin:
            steps += 1
            ltr += geoms[b].centroid.x > geoms[a].centroid.x
    X0, Y0, X1, Y1 = extents
    W, H = max(1e-9, X1 - X0), max(1e-9, Y1 - Y0)

    def frac(p):
        return [round((p[0] - X0) / W, 3), round((p[1] - Y0) / H, 3)]

    return {"stitches": len(st), "trims": trims, "up_moves": len(up_moves), "up_mm": round(up_mm, 1),
            "start": frac(mv[0]["p"]), "end": frac(mv[-1]["p"]),
            "start_mm": [round(v, 2) for v in mv[0]["p"]], "end_mm": [round(v, 2) for v in mv[-1]["p"]],
            "pieces": len(geoms), "visits": len(seq), "revisits": len(seq) - len(set(seq)),
            "inter_moves": inter_n, "inter_up_mm": round(inter_up, 1), "inter_down_mm": round(inter_down, 1),
            "inter_trims": inter_trims, "min_inter_trims": min_trims, "reach_first_trims": reach_trims,
            **{f"cut_{k}": v for k, v in why.items()},
            "order_gap_mm": round(order_gap, 1), "sweep_gap_mm": round(sweep_gap, 1),
            "centre_out_gap_mm": round(co_gap, 1),
            "line_steps": steps, "line_ltr": ltr,
            "area_mm2": round(sum(g.area for g in geoms.values()), 1)}


def read_file(path) -> dict:
    f = read(path)
    on_thread = footprint(f["blocks"], f["extents"])
    rows = [read_block(b, f["extents"], on_thread) for b in f["blocks"]]
    for prev, r in zip(rows, rows[1:]):
        r["from_prev_mm"] = round(math.dist(prev["end_mm"], r["start_mm"]), 1)
    if rows:
        rows[0]["from_prev_mm"] = None
    tot = {k: round(sum(r[k] for r in rows), 1) for k in
           ("stitches", "trims", "up_moves", "up_mm", "pieces", "visits", "revisits", "inter_moves",
            "inter_up_mm", "inter_down_mm", "inter_trims", "min_inter_trims", "reach_first_trims",
            "cut_next_in_reach", "cut_skipped_reach", "cut_dead_end", "order_gap_mm", "sweep_gap_mm",
            "centre_out_gap_mm",
            "line_steps",
            "line_ltr")}
    tot["colour_changes"] = len(rows) - 1
    tot["colour_hop_mm"] = round(sum(r["from_prev_mm"] or 0 for r in rows), 1)
    x0, y0, x1, y1 = f["extents"]
    tot["size_mm"] = [round(x1 - x0, 1), round(y1 - y0, 1)]
    return {"file": Path(path).name, "total": tot, "blocks": rows}


_PALETTE = [(60, 60, 60), (40, 110, 200), (40, 160, 60), (170, 90, 30), (150, 50, 160),
            (30, 150, 170), (120, 120, 30), (200, 60, 90)]


def render(path, out, ppm: float = 12.0, title: str | None = None) -> None:
    """The sew path: needle-down stitches in a per-block colour (light), the
    needle-up moves as red lines, each block's piece visits numbered in sew
    order at the piece's centroid (block.visit). Own frame, no registration."""
    import cv2
    import numpy as np
    f = read(path)
    x0, y0, x1, y1 = f["extents"]
    pad = 3.0
    w, h = int((x1 - x0 + 2 * pad) * ppm), int((y1 - y0 + 2 * pad) * ppm) + 28
    im = np.full((h, w, 3), 255, np.uint8)

    def px(p):
        return int(round((p[0] - x0 + pad) * ppm)), int(round((p[1] - y0 + pad) * ppm)) + 28

    labels = []
    for bi, block in enumerate(f["blocks"]):
        mv = moves(block)
        col = _PALETTE[bi % len(_PALETTE)]
        light = tuple(int(255 - (255 - c) * 0.45) for c in col)
        for a, b in zip(mv, mv[1:]):
            if not b["up"]:
                cv2.line(im, px(a["p"]), px(b["p"]), light, 1, cv2.LINE_AA)
        lab, ids, origin = pieces(mv, f["extents"])
        seq, seen = [], {}
        for pid in ids:
            if pid and (not seq or seq[-1] != pid):
                seq.append(pid)
        geoms = _piece_geoms(lab, list(set(seq)), origin)
        for n, pid in enumerate(seq):
            if pid in geoms and geoms[pid].area > 0.5:
                c = geoms[pid].representative_point()
                labels.append((px((c.x, c.y)), f"{bi}.{n}", col))
    for block in f["blocks"]:
        mv = moves(block)
        for a, b in zip(mv, mv[1:]):
            if b["up"]:
                cv2.line(im, px(a["p"]), px(b["p"]), (0, 0, 220), 1, cv2.LINE_AA)
                cv2.circle(im, px(b["p"]), 2, (0, 0, 220), -1)
    for (x, y), t, col in labels:
        cv2.putText(im, t, (x - 8, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(im, t, (x - 8, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, col, 1, cv2.LINE_AA)
    cv2.putText(im, title or Path(path).name, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1,
                cv2.LINE_AA)
    cv2.imwrite(str(out), im)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.sequence_pro",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", type=Path, help="write every file's full reading here")
    ap.add_argument("--blocks", action="store_true", help="print one line per colour block")
    ap.add_argument("--render", type=Path, help="write each file's sew path to DIR/<stem>.png")
    args = ap.parse_args(argv)
    out = []
    for fp in args.files:
        if args.render:
            args.render.mkdir(parents=True, exist_ok=True)
            render(fp, args.render / (Path(fp).stem + ".png"))
        r = read_file(fp)
        out.append(r)
        print(json.dumps({"file": r["file"], **r["total"]}))
        if args.blocks:
            for i, b in enumerate(r["blocks"]):
                print("  ", i, json.dumps({k: v for k, v in b.items() if k not in ("start_mm", "end_mm")}))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
