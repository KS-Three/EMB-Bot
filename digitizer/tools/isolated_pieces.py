"""isolated_pieces: the pieces no tour can reach without a cut, ours beside the pro's.

    python -m tools.isolated_pieces --pro FILE.DST [FILE.DST ...]      # one reader, any DST
    python -m tools.isolated_pieces --census [--json OUT]               # the pro's widths, every job

Built 2026-10-25 for W4-02. `tools/sequence_pro.py` (#1072) found that any
greedy tour of our pieces is forced into 129 cuts on five hats against 96 on
the professional's, and named MFab's slivers and white left as fabric. This
reads every one of those pieces, with `sequence_pro`'s piece rule unchanged
(every needle-down segment one thread wide, opened 0.6 mm, crumbs under six
penetrations dropped) and its "within reach" rule (a gap of `TRIM_AT_MM` or
less whose straight thread lies on thread, any colour, sewn before or after).

Per colour block, the reach graph's COMPONENTS: pieces joined by in-reach
gaps. One component per block is free (the colour change cuts anyway): the
largest by area, the BODY. Every other component is ISOLATED -- any order
pays at least one cut to enter it, so sum(components - 1) is the floor any
order sews at, and `sequence_pro`'s greedy tour (`greedy_cuts`) sits at or
above it. Compare files by `entries` (components over the whole file, each
entered by a colour change or a cut), not by `isolated` or `greedy_cuts`:
those free one piece per BLOCK, so a file in more colour blocks reads fewer
for the same construction -- the pro's Drone is 22 blocks to our 9, which is
most of #1072's +33 (entries 61 ours, 60 his). For each isolated component:

- colour (our block's thread; the pro's DST has none, so his block index),
  area mm2 (footprint), `width_mm` (twice the largest inscribed radius of
  its widest piece's footprint -- a sliver is thin everywhere, so this is
  its thickness), its penetrations;
- `near_mm`: the gap to the nearest piece of the same block outside the
  component, and what lies on that gap's straight line: thread
  (`gap_on_thread`, which a gap over 3 mm can still be), and on OUR side
  the share over a white region left as fabric (`gap_white`: an
  `enclosed_background` region not stitched) and over sewn white
  (`gap_sewn_white`: one `sew_enclosed_white` sews);
- ours only, the stage that made it (`made_by`), from the plan runs that
  sewed its penetrations (`tools.inpiece_cuts.attributed`) and their
  regions' meta: `edge_cap` (the `__edge_cap__` run tier), `white` (a
  region `sew_enclosed_white` sews), `lettering` (a text cluster's glyph),
  else `segment` (an ordinary stage 2-4 region) -- and `sliver` when that
  region's own polygon is under `SLIVER_MM` wide;
- `cause` names one per component: `white_fragment` when its region lies
  within `FRAGMENT_MM` of an unsewn enclosed region of its OWN thread (a
  piece of a white field left as fabric: MFab's keyline, all 22), else
  `white_gap` when its gap to the nearest same-colour piece runs mostly over
  white left as fabric, else `made_by`.

`pro_at(...)` then reads the professional's file at the same place
(`pro_parity.pairframe.register_pair`, ours onto his), named by his thread ON
TOP there (a ground he lays under everything covers it too): `drops` (under
a quarter of the area carries any of his thread), `merges` (the piece of his
that covers it also covers our nearest same-colour piece), `bridges` (his
piece there is joined within reach to another of his pieces: no forced
cut), `alone` (his piece there is itself isolated: he cuts to it too),
`run` (his thread there is a run, not a body).

`--census` reads every piece of every pro DST the repo's pair tables name:
its footprint width and its narrowest satin column's needle SWING
(`satin_swings`: runs of `SATIN_RUN` reversing steps, each read as its
median step). The footprint cannot read under about a millimetre -- the
0.6 mm opening keeps a lock knot as a "piece" -- so the pro's narrowest SEWN
width is the swing: p01 0.70 mm over 2,141 columns in 28 files
(2026-10-25), `digitizer_core/fragment_absorb.PRO_MIN_SWING_MM`.

Reads; judges nothing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from tools import sequence_pro as sp  # noqa: E402

#: a region whose own polygon is narrower than this is called a sliver in
#: `made_by` (read only to NAME it; the fix's threshold is the census's).
SLIVER_MM = 1.0
#: a region this close to an unsewn enclosed region of its own thread is a
#: fragment of it (a work-grid pixel at 8 px/mm, plus a margin).
FRAGMENT_MM = 0.3


# ------------------------------------------------------------------ reading --

def _mv_from_cmds(cmds):
    """[(x, y, cmd, tag)] -> (moves, tags) in `sequence_pro.moves`' shape."""
    import pystitch
    mv, tags = [], []
    up, trim = True, False
    for x, y, c, a in cmds:
        if c == pystitch.STITCH:
            mv.append({"p": (x, y), "up": up, "trim": trim})
            tags.append(a)
            up = trim = False
        elif c == pystitch.JUMP:
            up = True
        elif c == pystitch.TRIM:
            up = trim = True
    return mv, tags


def _widths(lab, pids) -> dict:
    """piece id -> twice its footprint's largest inscribed radius, mm."""
    import cv2
    import numpy as np
    out = {}
    for pid in pids:
        mask = (lab == pid).astype(np.uint8)
        if not mask.any():
            out[pid] = 0.0
            continue
        dt = cv2.distanceTransform(np.pad(mask, 1), cv2.DIST_L2, 5)
        out[pid] = round(2.0 * float(dt.max()) / sp.PPM, 2)
    return out


def read_block(mv, extents, on_thread) -> dict:
    """One colour block: pieces, the reach graph, its components, the greedy
    tour's forced cuts. Pieces keep `sequence_pro.read_block`'s crumb rule."""
    from shapely.ops import nearest_points
    lab, ids, origin = sp.pieces(mv, extents)
    counts = Counter(i for i in ids if i)
    keep = {p for p, n in counts.items() if n >= sp.MIN_PIECE_PTS}
    geoms = sp._piece_geoms(lab, list(keep), origin)
    widths = _widths(lab, geoms)
    pts = {p: [i for i, q in enumerate(ids) if q == p] for p in geoms}
    order = []
    for pid in ids:
        if pid in geoms and (not order or order[-1] != pid):
            order.append(pid)
    reach = {p: set() for p in geoms}
    gaps = {}
    srt = sorted(geoms)
    for i, a in enumerate(srt):
        for b in srt[i + 1:]:
            d = geoms[a].distance(geoms[b])
            qa, qb = nearest_points(geoms[a], geoms[b])
            on = d <= sp.THREAD_MM or bool(on_thread((qa.x, qa.y), (qb.x, qb.y)))
            gaps[(a, b)] = gaps[(b, a)] = (d, on, ((qa.x, qa.y), (qb.x, qb.y)))
            if d <= sp.TRIM_AT_MM and on:
                reach[a].add(b)
                reach[b].add(a)
    comp, cid = {}, 0
    for p in srt:
        if p in comp:
            continue
        stack = [p]
        comp[p] = cid
        while stack:
            q = stack.pop()
            for r in reach[q]:
                if r not in comp:
                    comp[r] = cid
                    stack.append(r)
        cid += 1
    comps = {}
    for p, c in comp.items():
        comps.setdefault(c, []).append(p)
    body = max(comps, key=lambda c: (sum(geoms[p].area for p in comps[c]), -c)) if comps else None
    # sequence_pro's greedy tour, from the file's own first piece
    greedy = 0
    entered_by_cut = []
    if order:
        cur, todo = order[0], set(geoms) - {order[0]}
        while todo:
            near = reach[cur] & todo
            pool = near or todo
            greedy += not near
            cur = min(pool, key=lambda q: (geoms[cur].distance(geoms[q]), q))
            if not near:
                entered_by_cut.append(cur)
            todo.discard(cur)
    return {"geoms": geoms, "widths": widths, "pts": pts, "reach": reach, "gaps": gaps,
            "comps": comps, "body": body, "greedy_cuts": greedy, "entered_by_cut": entered_by_cut,
            "floor_cuts": max(0, len(comps) - 1)}


def isolated(rb) -> list[dict]:
    """The block's isolated components: everything but its body."""
    out = []
    for c, members in sorted(rb["comps"].items()):
        if c == rb["body"]:
            continue
        others = [p for p in rb["geoms"] if p not in members]
        near, near_p, near_pair = math.inf, None, None
        for a in members:
            for b in others:
                d, _on, seg = rb["gaps"][(a, b)]
                if d < near:
                    near, near_p, near_pair = d, b, (a, b)
        widest = max(members, key=lambda p: rb["widths"][p])
        out.append({"pieces": sorted(members), "area_mm2": round(sum(rb["geoms"][p].area for p in members), 2),
                    "width_mm": rb["widths"][widest],
                    "pens": sum(len(rb["pts"][p]) for p in members),
                    "near_mm": None if near_p is None else round(near, 2), "near_piece": near_p,
                    "gap_on_thread": None if near_pair is None else rb["gaps"][near_pair][1],
                    "gap_seg": None if near_pair is None else rb["gaps"][near_pair][2]})
    return out


def read_file(path) -> dict:
    """A machine file -> per block reading + isolated components. Own frame."""
    f = sp.read(path)
    on_thread = sp.footprint(f["blocks"], f["extents"])
    blocks = []
    for bi, blk in enumerate(f["blocks"]):
        mv = sp.moves(blk)
        rb = read_block(mv, f["extents"], on_thread)
        rows = isolated(rb)
        for r in rows:
            r["block"] = bi
        blocks.append({"rb": rb, "isolated": rows, "mv": mv})
    return {"file": Path(path).name, "extents": f["extents"], "blocks": blocks, "on_thread": on_thread}


def totals(reading) -> dict:
    """`entries`: components over the whole file -- every one is entered by a
    colour change or a cut. `isolated` frees one per block, so a file in more
    colour blocks reads fewer isolated pieces for the same construction
    (the pro's Drone: 23 blocks to our 10); compare `entries` across files."""
    b = reading["blocks"]
    return {"pieces": sum(len(x["rb"]["geoms"]) for x in b),
            "blocks": sum(1 for x in b if x["rb"]["geoms"]),
            "entries": sum(len(x["rb"]["comps"]) for x in b),
            "isolated": sum(len(x["isolated"]) for x in b),
            "floor_cuts": sum(x["rb"]["floor_cuts"] for x in b),
            "greedy_cuts": sum(x["rb"]["greedy_cuts"] for x in b)}


# --------------------------------------------------------------------- ours --

def _region_width(poly) -> float:
    """Twice the largest inscribed radius of a polygon, mm (raster 0.05 mm)."""
    import cv2
    import numpy as np
    if poly is None or poly.is_empty:
        return 0.0
    r = 20.0
    x0, y0, x1, y1 = poly.bounds
    w, h = int((x1 - x0) * r) + 4, int((y1 - y0) * r) + 4
    if w * h > 4e7:
        return float("nan")
    im = np.zeros((h, w), np.uint8)
    geoms = getattr(poly, "geoms", [poly])
    for g in geoms:
        ext = np.array([[(x - x0) * r + 2, (y - y0) * r + 2] for x, y in g.exterior.coords], np.int32)
        cv2.fillPoly(im, [ext], 1)
        for hole in g.interiors:
            hh = np.array([[(x - x0) * r + 2, (y - y0) * r + 2] for x, y in hole.coords], np.int32)
            cv2.fillPoly(im, [hh], 0)
    dt = cv2.distanceTransform(im, cv2.DIST_L2, 5)
    return round(2.0 * float(dt.max()) / r, 2)


def _seg_share(seg, polys) -> float:
    """Share of the straight segment `seg` lying inside any of `polys`."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    if seg is None or not polys:
        return 0.0
    ln = LineString(seg)
    if ln.length < 1e-6:
        return 0.0
    return round(ln.intersection(unary_union(polys)).length / ln.length, 2)


def read_plan(plan, result) -> dict:
    """Our plan, read by the same rule, every isolated component traced back
    to the runs that sewed it and their regions."""
    import pystitch
    from tools.inpiece_cuts import attributed
    cmds = attributed(plan)
    pts = [(x, y) for b in cmds for x, y, c, _a in b if c == pystitch.STITCH]
    ext = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    # the walk rule's thread map over every block (sequence_pro.footprint's input shape)
    raw = [[(x, y, c) for x, y, c, _a in b] for b in cmds]
    on_thread = sp.footprint(raw, ext)
    regs = {r.shape_id: r for r in result.regions}
    left = [r for r in result.regions
            if r.meta.get("enclosed_background") and not r.meta.get("stitched", True)]
    white_fabric = [r.polygon for r in left]
    white_sewn = [r.polygon for r in result.regions if r.meta.get("sew_enclosed_white")
                  and r.meta.get("stitched", True)]
    blocks = []
    for bi, blk in enumerate(cmds):
        mv, tags = _mv_from_cmds(blk)
        if not mv:
            continue
        rb = read_block(mv, ext, on_thread)
        rows = isolated(rb)
        for r in rows:
            r["block"] = bi
            r["rgb"] = list(plan.blocks[bi].rgb) if bi < len(plan.blocks) else None
            runs = Counter()
            for p in r["pieces"]:
                for i in rb["pts"][p]:
                    b0, r0 = tags[i]
                    run = plan.blocks[b0].runs[r0]
                    runs[(str(run.shape_id), str(run.kind))] += 1
            r["runs"] = {f"{s}|{k}": n for (s, k), n in runs.most_common()}
            sids = Counter()
            for (s, k), n in runs.items():
                sids[s] += n
            top = sids.most_common(1)[0][0] if sids else None
            r["shape"] = top
            reg = regs.get(top)
            r["made_by"] = made_by(top, reg)
            r["region_area_mm2"] = round(reg.area_mm2, 2) if reg is not None else None
            r["region_width_mm"] = _region_width(reg.polygon) if reg is not None else None
            if r["made_by"] == "segment" and r["region_width_mm"] is not None \
                    and r["region_width_mm"] < SLIVER_MM:
                r["made_by"] = "sliver"
            # a FRAGMENT of a field left as fabric: its own region lies
            # against (within `FRAGMENT_MM`) an unsewn enclosed region of
            # the same thread -- the rest of what it belongs to is not sewn
            same = [q.polygon for q in left if reg is not None and q.thread_number == reg.thread_number]
            r["beside_unsewn_mm"] = (round(min(reg.polygon.distance(q) for q in same), 2)
                                     if same else None)
            r["gap_white"] = _seg_share(r["gap_seg"], white_fabric)
            r["gap_sewn_white"] = _seg_share(r["gap_seg"], white_sewn)
        blocks.append({"rb": rb, "isolated": rows, "mv": mv, "tags": tags})
    return {"file": "plan", "extents": ext, "blocks": blocks, "on_thread": on_thread}


def made_by(shape_id, reg) -> str:
    if shape_id is None:
        return "unknown"
    if str(shape_id) == "__edge_cap__":
        return "edge_cap"
    if str(shape_id).startswith("__"):
        return str(shape_id).strip("_") or "synthetic"
    if reg is None:
        return "unknown"
    m = reg.meta
    if m.get("sew_enclosed_white"):
        return "white"
    if m.get("text_cluster_id") is not None or m.get("lettering_group") is not None:
        return "lettering"
    return "segment"


def cause(row) -> str:
    """One name per isolated component of ours, for the table.

    White first: a component that is a fragment of a field of its own
    thread left as fabric (`beside_unsewn_mm`), or whose gap to its nearest
    same-colour piece runs mostly over white left as fabric, is cut off BY
    that white."""
    b = row.get("beside_unsewn_mm")
    if b is not None and b <= FRAGMENT_MM:
        return "white_fragment"
    if row.get("gap_white", 0) >= 0.5 and (row.get("near_mm") or math.inf) <= sp.TRIM_AT_MM:
        return "white_gap"
    return row["made_by"]


# ---------------------------------------------------------------------- pro --

def pro_at(ours, pro, reg) -> None:
    """For every isolated component of ours (`ours` = `read_plan`), what the
    pro's file (`pro` = `read_file`) does at the same place. `reg` maps ours
    onto his (`register_pair(pro_dst, ours_dst)`). Writes `row["pro"]`."""
    from shapely.affinity import affine_transform
    from shapely.ops import unary_union
    mat = reg.matrix()
    pro_pieces = []    # (block, pid, geom)
    for bi, b in enumerate(pro["blocks"]):
        for pid, g in b["rb"]["geoms"].items():
            pro_pieces.append((bi, pid, g))
    thread = _thread_mask(pro)
    for b in ours["blocks"]:
        for row in b["isolated"]:
            g = unary_union([b["rb"]["geoms"][p] for p in row["pieces"]])
            gp = affine_transform(g, mat)
            area = max(gp.area, 1e-9)
            cover = thread(gp)
            hits = sorted(((gp.intersection(pg).area, bi, pid, pg) for bi, pid, pg in pro_pieces
                           if pg.intersects(gp)), key=lambda t: -t[0])
            piece_cover = (gp.intersection(unary_union([h[3] for h in hits])).area / area) if hits else 0.0
            out = {"thread_cover": round(cover, 2), "piece_cover": round(piece_cover, 2)}
            if cover < 0.25:
                out["verdict"] = "drops"
            elif not hits or piece_cover < 0.25:
                out["verdict"] = "run"
            else:
                # the thread ON TOP names the place: of his pieces covering
                # a fair share of it, the one sewn last (a ground he lays
                # under everything covers it too, and would read as a merge)
                fair = [h for h in hits if h[0] >= 0.3 * area] or hits[:1]
                _a, pbi, ppid, pg = max(fair, key=lambda h: (h[1], h[0]))
                pb = pro["blocks"][pbi]["rb"]
                out["block"] = pbi
                out["width_mm"] = pb["widths"][ppid]
                near = row.get("near_piece")
                ng = affine_transform(b["rb"]["geoms"][near], mat) if near is not None else None
                if ng is not None and pg.intersection(ng).area >= 0.25 * min(ng.area, pg.area, area):
                    out["verdict"] = "merges"
                else:
                    cid = next(c for c, m in pb["comps"].items() if ppid in m)
                    out["verdict"] = "bridges" if (cid == pb["body"] or len(pb["comps"][cid]) > 1) \
                        else "alone"
            row["pro"] = out


def _thread_mask(reading):
    """-> cover(geom): the share of a polygon (mm, the file's frame) under any
    needle-down thread of the file, every segment one thread wide on
    `sequence_pro`'s raster (shapely's buffer of every segment cost minutes)."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = reading["extents"]
    x0 -= 2
    y0 -= 2
    w = int((x1 - x0 + 2) * sp.PPM) + 2
    h = int((y1 - y0 + 2) * sp.PPM) + 2
    im = np.zeros((h, w), np.uint8)
    lw = max(1, int(round(sp.THREAD_MM * sp.PPM)))

    def px(p):
        return int(round((p[0] - x0) * sp.PPM)), int(round((p[1] - y0) * sp.PPM))

    for b in reading["blocks"]:
        mv = b["mv"]
        for a, c in zip(mv, mv[1:]):
            if not c["up"]:
                cv2.line(im, px(a["p"]), px(c["p"]), 1, lw)

    def cover(geom) -> float:
        poly = np.zeros_like(im)
        for g in getattr(geom, "geoms", [geom]):
            if g.is_empty or not hasattr(g, "exterior"):
                continue
            cv2.fillPoly(poly, [np.array([px(q) for q in g.exterior.coords], np.int32)], 1)
            for hole in g.interiors:
                cv2.fillPoly(poly, [np.array([px(q) for q in hole.coords], np.int32)], 0)
        n = int(poly.sum())
        return round(float((poly & im).sum()) / n, 2) if n else 0.0

    return cover


# ------------------------------------------------------------------- census --

def census_files() -> list[tuple[str, Path]]:
    """The pro's DSTs: every job `border_census.PAIRS` and the intake
    registry carry, one row per file (the third-party `test_files_*` corpus
    is not the pro's and stays out)."""
    from tools import border_census as bc
    from tools.pro_intake import registered_pairs
    seen, out = set(), []
    for row in [*bc.PAIRS, *registered_pairs(with_art=False)]:
        slug, rel = row[0], row[1]
        if slug.startswith("test_files_"):
            continue
        p = Path(rel) if Path(rel).is_absolute() else bc.find(rel)
        if p is not None and p.suffix.lower() == ".pes":
            p = bc.find(rel[:-4] + ".DST") or None
        if p is None or not Path(p).exists():
            continue
        key = str(Path(p).resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((slug, Path(p)))
    return out


#: a run of this many consecutive needle-down steps that each reverse the
#: last (cosine under -0.7, `inpiece_cuts.character`'s satin test) is a satin
#: column, and its median step is the column's needle swing
SATIN_RUN = 8


def satin_swings(mv, idx) -> list[float]:
    """The needle swing (mm) of every satin column among penetrations `idx`
    of `mv` (one piece): maximal runs of >= `SATIN_RUN` reversing steps,
    each read as the median of its steps' extent ACROSS the column (a step's
    component normal to the column's axis there, the sum of it and the next
    step: a step's own length also carries the advance along the column)."""
    idx = sorted(idx)
    out, run = [], []

    def close():
        if len(run) >= SATIN_RUN:
            widths = []
            for v, w in zip(run, run[1:]):
                ax = (v[0] + w[0], v[1] + w[1])
                la = math.hypot(*ax)
                widths.append(abs(v[0] * ax[1] - v[1] * ax[0]) / la if la > 1e-6 else math.hypot(*v))
            s = sorted(widths)
            out.append(round(s[len(s) // 2], 2))

    prev = None
    for a, b in zip(idx, idx[1:]):
        if b != a + 1 or mv[b]["up"]:
            close()
            run, prev = [], None
            continue
        v = (mv[b]["p"][0] - mv[a]["p"][0], mv[b]["p"][1] - mv[a]["p"][1])
        ln = math.hypot(*v)
        if ln < 1e-6:
            continue
        if prev is not None and (v[0] * prev[0] + v[1] * prev[1]) / (ln * math.hypot(*prev)) >= -0.7:
            close()
            run = []
        run.append(v)
        prev = v
    close()
    return out


def census(files=None) -> dict:
    """Every piece of the pro's: its footprint width and, where it has one,
    its narrowest satin column's needle swing (`satin_swing_mm`) -- the
    width he actually sews, which a footprint cannot read under about a
    millimetre (the 0.6 mm opening keeps a lock knot as a "piece"). All
    pieces, and the isolated ones he cuts to (components other than a
    block's body)."""
    rows = []
    for slug, p in files or census_files():
        r = read_file(p)
        for bi, b in enumerate(r["blocks"]):
            rb = b["rb"]
            iso = {p for c, m in rb["comps"].items() if c != rb["body"] for p in m}
            for pid, g in rb["geoms"].items():
                sw = satin_swings(b["mv"], rb["pts"][pid])
                rows.append({"slug": slug, "file": p.name, "block": bi, "piece": pid,
                             "width_mm": rb["widths"][pid], "area_mm2": round(g.area, 2),
                             "pens": len(rb["pts"][pid]), "isolated": pid in iso,
                             "satin_swing_mm": min(sw) if sw else None, "satin_columns": len(sw)})
    return {"files": [[s, str(p)] for s, p in (files or census_files())], "pieces": rows}


def _pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[k]


def summary(cen) -> dict:
    allw = [r["width_mm"] for r in cen["pieces"]]
    isow = [r["width_mm"] for r in cen["pieces"] if r["isolated"]]
    sw = [r["satin_swing_mm"] for r in cen["pieces"] if r.get("satin_swing_mm") is not None]
    cols = [r["satin_columns"] for r in cen["pieces"]]
    return {"files": len(cen["files"]), "pieces": len(allw), "isolated": len(isow),
            "width_min": min(allw) if allw else None, "width_p05": _pct(allw, 0.05),
            "isolated_width_min": min(isow) if isow else None, "isolated_width_p05": _pct(isow, 0.05),
            "isolated_width_p10": _pct(isow, 0.10), "isolated_width_median": _pct(isow, 0.5),
            "satin_pieces": len(sw), "satin_columns": sum(cols),
            "satin_swing_min": min(sw) if sw else None, "satin_swing_p01": _pct(sw, 0.01),
            "satin_swing_p05": _pct(sw, 0.05), "satin_swing_median": _pct(sw, 0.5)}


def _strip(reading) -> list[dict]:
    out = []
    for b in reading["blocks"]:
        for r in b["isolated"]:
            out.append({k: v for k, v in r.items() if k != "gap_seg"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.isolated_pieces",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--pro", nargs="*", default=[], help="machine files to read on their own")
    ap.add_argument("--census", action="store_true", help="the pro's piece widths over every job")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    out = {}
    for fp in args.pro:
        r = read_file(fp)
        out[Path(fp).name] = {"total": totals(r), "isolated": _strip(r)}
        print(Path(fp).name, json.dumps(totals(r)))
    if args.census:
        cen = census()
        out["census"] = cen
        out["census_summary"] = summary(cen)
        print(json.dumps(out["census_summary"]))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
