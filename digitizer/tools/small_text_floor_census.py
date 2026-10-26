#!/usr/bin/env python
"""small_text_floor_census: where the pro stops sewing small text as drawn.

Measure only -- nothing in `digitizer_core/` is read differently or changed.

For every text element below ~6 mm in the paired jobs (plus a few larger
lines as a reference), one reader is pointed at BOTH machine files -- ours
(a `tools/border_census.py`-style cache: ours.dst + ours.json, digitized at
the pro's width through the Studio request) and the pro's -- each in its own
frame. The element's box is written once, in our OFF frame (the art traced at
the pro's width), and mapped into the pro's frame with `register` (the
pairframe registration without its y-flip candidate: Fremont's hexagon
registers upside down at IoU 0.98 when the flip is allowed).

Per element and per file, inside the element's box grown by max(2.5 mm, 1.5 x
the art height) up and down and 2 mm + half the art height sideways:

  block       the colour block that sews the letters: the block with the most
              thread in LETTER-LIKE components -- painted 0.3 mm wide at
              20 px/mm (a non-satin, non-bean stitch over 2.5 mm is travel
              and not painted), not touching the box edge (a field, a bar, a
              border), at least 0.3 x the art height tall, centred within
              max(1.5 mm, art height) of the line's centre.
  h_mm        sewn letter height: median height of those components among the
              ones at least 60% of the tallest (needle points plus 0.3 mm of
              painted thread, so ~0.3 mm over the polygon a stage-5 letter is).
  w_mm        sewn line width (x extent of those components) -- with the art's
              line width it gives the horizontal re-set factor.
  gap_mm      median gap between x-neighbouring components; `fused` counts
              neighbours closer than 0.05 mm (letters sewn into each other).
  stroke_mm   median satin cross (the `border_pro.columns` phases), i.e. the
              sewn column width; None when no satin.
  satin / bean / run   share of the block's in-box thread length that is a
              satin phase / a triple bean (the needle re-enters the hole two
              stitches back, |p[i+2]-p[i]| < 0.12 mm, on 0.4-3.5 mm stitches) /
              anything else (single runs, travel, underlay walks).
  verdict     DROPPED (no block thread in the box), SATIN (satin >= 0.5),
              BEAN (bean >= 0.4), RUN (otherwise).

  python -m tools.small_text_floor_census --cache DIR [--cache DIR2 ...]
      [--arm NAME=DIR ...] [--crops OUT] [--json OUT.json]

`--arm` adds a second (or third) of our digitizations of the same jobs (an ON
arm); the pro is read once per job. Art heights always come from the FIRST
cache (OFF), which is the art as traced. The cache is made with

  python -m tools.small_text_floor_census digitize --cache DIR [--set K=JSON ...] SLUG ...

(`border_census.digitize_one`, with the beanie and Golden Tee pairs it lacks).

KNOWN MISREADS (2026-10-24), read the crops before quoting a row: the pro's
Fremont lettering sits in blocks whose letters join through short in-letter
travel and the patch field, so EST / 1895 / PLAY read DROPPED or as one
blob, and HOTEL FREMONT reads its band (16.95 mm); `tools/small_text_columns.py`
reads those by colour block (`small-text-reset-2026-10-21` in memory). MFab's
outline letters read 8.05 mm against 6.1 drawn: the outline, not a re-set.

STEPS (2026-10-25, W3-11): where a re-set letter's stroke goes, step by step.

  python -m tools.small_text_floor_census steps --cache DIR [--set K=JSON ...] SLUG ...

digitizes each SLUG like `digitize`, with the re-set set explicit
(`RESET_SET`, #1057's defaults; None on main when written) under any
`--set`, and reads every re-set line (`enlarge_small_text`'s clusters) at
each step it passes through:

  est       the stroke the re-set is told the letters have: the tagger's
            `text_cluster_stroke_mm` x 2 (`small_text.py`, `it["stroke"]`).
  traced    the stroke of the shapes it actually grows -- the letters
            `_retrace` re-read from the source raster -- by the SAME measure
            (2 x the mean skeleton half-width, `textcluster._stats_of_polygon`).
  target    `_stroke_target`: the floor, or the bold scale on `est`.
  widen     what each side is buffered: (target - min(s, f) x est) / 2.
  drawn     the letters' polygons as stage 7's Column lane receives them
            (`p.region.polygon`; stage 5's grown polygon is not what the
            lane sews), by the same measure. The re-set means drawn = target.
  column    the plan's satin crosses on those letters (needle to needle,
            median): what the lane built from `drawn`.
  sewn      the census reader's `stroke_mm` on our DST, by `ELEMENTS` line.

Where `traced` < `est`, drawn lands at target - min(s, f) x (est - traced):
under the floor wherever the floor is the target. Read off `steps.json`
(cache/SLUG) with `steps --table --cache DIR`.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

PPM = 20.0
THREAD_MM = 0.3
TALL_FRAC = 0.6
FUSED_MM = 0.05
BEAN_RETURN_MM = 0.12
TRAVEL_MM = 2.5

#: (slug, label, box x0, y0, x1, y1 in our OFF frame, mm). Boxes are the
#: text cluster's (or rescued shapes') extents in the 2026-10-24 main cache.
ELEMENTS = [
    ("hotel_fremont_hat", "EST", (-10.5, -14.8, -4.3, -12.9)),
    ("hotel_fremont_hat", "1895", (4.0, -14.8, 10.4, -12.9)),
    ("hotel_fremont_hat", "THE", (-5.0, -8.7, 5.0, -5.7)),
    ("hotel_fremont_hat", "EAT|STAY", (-13.7, 10.2, 4.4, 12.8)),
    ("hotel_fremont_hat", "PLAY", (7.8, 10.3, 16.2, 12.7)),
    ("hotel_fremont_hat", "HOTEL FREMONT (ref)", (-43.1, -3.6, 43.0, 3.5)),
    ("hotel_fremont_patch", "EST", (-10.5, -14.8, -4.3, -12.9)),
    ("hotel_fremont_patch", "1895", (4.0, -14.8, 10.4, -12.9)),
    ("hotel_fremont_patch", "THE", (-5.0, -8.7, 5.0, -5.7)),
    ("hotel_fremont_patch", "EAT|STAY", (-13.7, 10.2, 4.4, 12.8)),
    ("hotel_fremont_patch", "PLAY", (7.8, 10.3, 16.2, 12.7)),
    ("proseal_hat", "SPRAY FOAM", (-36.5, 28.3, -0.7, 31.5)),
    ("proseal_hat", "+ COATINGS", (8.2, 28.3, 35.6, 31.5)),
    ("proseal_hat", "PROSEAL (ref)", (-41.3, 14.5, 39.3, 23.7)),
    ("precision_drone", "AND DRONE", (-13.6, 24.1, 17.7, 26.3)),
    ("precision_drone", "THERMAL (ref)", (-31.1, 10.2, 31.2, 16.9)),
    ("proseal_beanie", "SPRAY FOAM", (-32.0, 24.7, -0.6, 27.5)),
    ("proseal_beanie", "+ COATINGS", (2.0, 24.7, 31.2, 27.6)),
    ("proseal_beanie", "PROSEAL (ref)", (-36.1, 12.6, 34.3, 20.7)),
    # the mark is ~0.9 mm in the art and no region of ours holds it (dropped)
    ("goldentee_hat", "TM", (24.5, 6.0, 30.5, 10.5), 0.86),
    ("toat_machine_hat", "LLC (ref)", (9.4, 12.9, 24.8, 19.9)),
    ("gaulke_roofing_hat", "STEEL ROOFING (ref)", (-57.0, 17.1, 56.9, 23.4)),
    ("gaulke_roofing_lc", "STEEL ROOFING (ref)", (-47.5, 14.2, 47.5, 19.5)),
    ("gaulke_roofing_beanie", "STEEL ROOFING (ref)", (-46.8, 13.9, 46.8, 19.2)),
    ("mfab_lc", "AND WELDING LLC (ref)", (-43.0, 3.6, 41.9, 10.9)),
]

#: pairs `border_census.PAIRS` lacks, in its row shape
EXTRA_PAIRS = [
    ("proseal_beanie", "Proseal/PROSEALHAT BEANI.DST", "Proseal/PROSeal Logo.jpg", "beanie"),
    ("gaulke_roofing_beanie", "Gaulke Roofing/c golke logo HAT BEANI.DST",
     "Gaulke Roofing/Gaulke Roofing Logo.png", "beanie"),
    ("goldentee_hat", " Golden Tee/GOLF HAT.DST", "Golden Tee/Golden Tee Logo.jpg", "hat_front"),
]


def digitize_main(argv) -> int:
    """`digitize`: cache ours.dst + ours.json for SLUGs at the pro's width,
    the Studio's request plus `--set` flags."""
    from tools import border_census as bc
    from tools import pro_pair as pp
    ap = argparse.ArgumentParser(prog="small_text_floor_census digitize")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("slugs", nargs="+")
    args = ap.parse_args(argv)
    extra = pp.parse_sets(args.set)
    known = {r[0] for r in bc.PAIRS}
    bc.PAIRS += [r for r in EXTRA_PAIRS if r[0] not in known]
    bc.ART_FALLBACK.setdefault("goldentee", bc._T / "photo" / "logo_golden_tee.jpg")
    if extra:
        dig = pp.digitize
        bc_dig = (lambda art, w, g="hat_front", e=None: dig(art, w, g, {**extra, **(e or {})}))
        pp.digitize = bc_dig
    for slug in args.slugs:
        info = bc.digitize_one(slug, Path(args.cache))
        print(slug, info["width_mm"], info["secs"], flush=True)
    return 0


# ------------------------------------------------------------------ steps
#: the re-set with #1057's defaults, explicit (None on main when written)
RESET_SET = {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
             "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
             "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True}


def stroke_mm(poly) -> float | None:
    """2 x the mean skeleton half-width: the tagger's own measure, the one
    `text_cluster_stroke_mm` (and so the re-set's `it["stroke"]`) is."""
    from digitizer_core.textcluster import _stats_of_polygon
    s = _stats_of_polygon(poly)
    return None if s is None else 2.0 * s.mean_mm


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def steps_main(argv) -> int:
    """`steps` (module doc, STEPS)."""
    import time
    from digitizer_core import pipeline, small_text
    from tools import border_census as bc
    from tools import pro_pair as pp
    ap = argparse.ArgumentParser(prog="small_text_floor_census steps")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--table", action="store_true", help="print the cache's steps.json, digitize nothing")
    ap.add_argument("slugs", nargs="*")
    args = ap.parse_args(argv)
    cache = Path(args.cache)
    if args.table:
        print(steps_table(sorted(cache.glob("*/steps.json"))))
        return 0
    extra = {**RESET_SET, **pp.parse_sets(args.set)}
    known = {r[0] for r in bc.PAIRS}
    bc.PAIRS += [r for r in EXTRA_PAIRS if r[0] not in known]
    place, ro = small_text._place_line_reset, pipeline.resolve_overlaps
    for slug in args.slugs:
        row = next(r for r in bc.PAIRS if r[0] == slug)
        pro, art = bc.find_pair(*row[:3])
        if pro is None or art is None:
            raise SystemExit(f"{slug}: missing {'pro' if pro is None else 'art'} file")
        width = pp.pro_counts(pro)["width_mm"]
        lines: list = []
        letters: dict = {}

        def hook_place(items, *a, **k):
            found = place(items, *a, **k)
            for n, it in enumerate(items):
                rec = {"cluster": it["row"]["cluster"], "cap": round(it["cap"], 3),
                       "est": round(it["stroke"], 3), "found": found is not None,
                       "traced": _med([stroke_mm(s) for s in it["shapes"]])}
                if found:
                    s, _dy, _dxs, resets, _bars = found
                    rec.update(s=round(s, 3), f=round(resets[n]["f"], 3), widen=round(resets[n]["widen"], 3),
                               target=round(small_text._stroke_target(it, s, a[4], a[5]), 3))
                lines.append(rec)
            return found

        def hook_ro(regions, *a, **k):
            planned, warns = ro(regions, *a, **k)
            for p in planned:
                m = p.region.meta
                if m.get("small_text_reset"):
                    letters[p.region.shape_id] = {"cluster": m.get("text_cluster_id"),
                                                  "drawn": stroke_mm(p.region.polygon),
                                                  "bounds": [round(v, 2) for v in p.region.polygon.bounds]}
            return planned, warns
        small_text._place_line_reset, pipeline.resolve_overlaps = hook_place, hook_ro
        try:
            t = time.time()
            d = pp.digitize(art, width, row[3], extra)
        finally:
            small_text._place_line_reset, pipeline.resolve_overlaps = place, ro
        for _blk, run in d.plan.iter_runs():
            lt = letters.get(str(run.shape_id))
            if lt is not None and str(run.kind) == "satin":
                pts = run.points or []
                lt.setdefault("crosses", []).extend(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        out = cache / slug
        bc.write_ours(out, slug, row[3], width, pro, art, d.result, d.plan, time.time() - t)
        # the census reader on our DST, per ELEMENTS line of this slug
        from tools.study_pro import load_runs
        runs = load_runs(out / "ours.dst")[0]
        sewn = []
        for el in (e for e in ELEMENTS if e[0] == slug and "(ref)" not in e[1]):
            box = el[2]
            ah = el[3] if len(el) > 3 else None
            h = ah or (box[3] - box[1])
            m_y, m_x = max(2.5, 1.5 * h), 2.0 + 0.5 * h
            r = read_element(runs, (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y), h,
                             0.5 * (box[1] + box[3]))
            sewn.append({"label": el[1], "box": list(box), "stroke_mm": r.get("stroke_mm"),
                         "verdict": r.get("verdict")})
        rec = {"slug": slug, "set": extra, "lines": lines, "sewn": sewn,
               "letters": {k: {"cluster": v["cluster"], "bounds": v["bounds"],
                               "drawn": None if v["drawn"] is None else round(v["drawn"], 3),
                               "column": _med(v.get("crosses", [])), "crosses": len(v.get("crosses", []))}
                           for k, v in letters.items()}}
        (out / "steps.json").write_text(json.dumps(rec, default=str), encoding="utf-8")
        print(slug, width, round(time.time() - t), "s", flush=True)
    print(steps_table(sorted(cache.glob("*/steps.json"))))
    return 0


def steps_table(paths) -> str:
    """One row per re-set cluster: est | traced | s / f | target | widen |
    predicted drawn (target - min(s, f) x (est - traced)) | drawn | column |
    sewn (the census line the cluster sits in)."""
    head = ("| job | cluster (cap mm) | est | traced | traced / est | s / f | target | widen | "
            "predicted drawn | drawn | column | sewn (line) |")
    out = [head, "|" + "---|" * 12]
    for p in paths:
        rec = json.loads(Path(p).read_text(encoding="utf-8"))
        for ln in rec["lines"]:
            lts = [v for v in rec["letters"].values() if v.get("cluster") == ln["cluster"]]
            drawn, col = _med([v["drawn"] for v in lts]), _med([v["column"] for v in lts])
            sewn = ""
            if lts:
                xs = [(v["bounds"][0] + v["bounds"][2]) / 2.0 for v in lts]
                ys = [(v["bounds"][1] + v["bounds"][3]) / 2.0 for v in lts]
                cx, cy = statistics.median(xs), statistics.median(ys)
                hit = [s for s in rec["sewn"] if s["box"][0] - 3 <= cx <= s["box"][2] + 3
                       and s["box"][1] - 3 <= cy <= s["box"][3] + 3]
                sewn = "; ".join(f"{s['stroke_mm']} ({s['label']})" for s in hit)
            if not ln.get("found"):
                out.append(f"| {rec['slug']} | {ln['cluster']} ({ln['cap']}) | {ln['est']} | {ln['traced']} | "
                           f"| | | | | {drawn} | {col} | {sewn} |")
                continue
            ratio = round(ln["traced"] / ln["est"], 2) if ln["traced"] and ln["est"] else None
            pred = (round(ln["target"] - min(ln["s"], ln["f"]) * (ln["est"] - ln["traced"]), 3)
                    if ln["traced"] else None)
            out.append(f"| {rec['slug']} | {ln['cluster']} ({ln['cap']}) | {ln['est']} | {ln['traced']} | {ratio} | "
                       f"{ln['s']} / {ln['f']} | {ln['target']} | {ln['widen']} | {pred} | {drawn} | {col} | {sewn} |")
    return "\n".join(out)


# ------------------------------------------------------------------ reading
def _segments(runs, box):
    """-> {block: [(x0, y0, x1, y1, run_idx, i)]} needle-down segments with
    at least one end inside `box`."""
    x0, y0, x1, y1 = box

    def inside(q):
        return x0 <= q[0] <= x1 and y0 <= q[1] <= y1
    out: dict[int, list] = {}
    for ri, r in enumerate(runs):
        p = r["pts"]
        for i in range(len(p) - 1):
            if inside(p[i]) or inside(p[i + 1]):
                out.setdefault(r["block"], []).append((p[i][0], p[i][1], p[i + 1][0], p[i + 1][1], ri, i))
    return out


def _seg_len(s):
    return math.hypot(s[2] - s[0], s[3] - s[1])


_SAT_CACHE: dict[int, dict] = {}


def seg_kinds(runs, segs) -> list[str]:
    """'satin' (inside a `border_pro.columns` phase), 'bean' (the needle
    re-enters the hole two stitches away on a 0.4-3.5 mm stitch) or 'other',
    per segment of `segs`."""
    from tools.border_pro import columns
    # keyed by id() and holding `runs` itself: a freed list's id is reused
    # by the next one, which then read the old list's satin flags
    held = _SAT_CACHE.get(id(runs))
    if held is None or held[0] is not runs:
        held = _SAT_CACHE[id(runs)] = (runs, {})
    sat_of = held[1]
    out = []
    for s in segs:
        ri, i = s[4], s[5]
        pts = runs[ri]["pts"]
        if ri not in sat_of:
            insat = [False] * (len(pts) - 1)
            if len(pts) >= 3:
                cols, _t, _c = columns(pts)
                for a, b in cols:
                    for k in range(a, min(b, len(pts) - 1)):
                        insat[k] = True
            sat_of[ri] = insat
        if sat_of[ri][i]:
            out.append("satin")
            continue
        ln = math.dist(pts[i], pts[i + 1])
        back = (i + 2 < len(pts) and math.dist(pts[i], pts[i + 2]) < BEAN_RETURN_MM) or                (i >= 1 and math.dist(pts[i - 1], pts[i + 1]) < BEAN_RETURN_MM)
        out.append("bean" if back and 0.4 <= ln <= 3.5 else "other")
    return out


def components(segs, kinds, box, art_h, cy, reach=None):
    """Paint `segs` (0.3 mm thread, 20 px/mm; a non-satin, non-bean stitch
    longer than `TRAVEL_MM` is travel between letters and is not painted) and
    keep the letter-like components: not touching the box edge (a field, a
    bar, a border running through), at least 0.3 x the art height tall, and
    centred within `reach` -- by default max(1.5, art height) -- of the
    line's centre `cy`. A line the pro MOVED further than that reads
    DROPPED by default: Fremont's EST 1895 (cap 1.85) sits ~3 mm lower in
    his file; `tools/reset_room_census.py` passes the search box's own reach.
    -> ([(x0, y0, x1, y1) mm], [indices of the segments inside them])."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = box
    w = int(math.ceil((x1 - x0) * PPM)) + 1
    h = int(math.ceil((y1 - y0) * PPM)) + 1
    img = np.zeros((h, w), np.uint8)
    th = max(1, int(round(THREAD_MM * PPM)))

    def px(x, y):
        return int(round((x - x0) * PPM)), int(round((y - y0) * PPM))
    painted = [j for j, (s, k) in enumerate(zip(segs, kinds)) if k != "other" or _seg_len(s) <= TRAVEL_MM]
    for j in painted:
        s = segs[j]
        cv2.line(img, px(s[0], s[1]), px(s[2], s[3]), 255, th)
    n, lab, st, _c = cv2.connectedComponentsWithStats(img, 8)
    keep = {}
    for k in range(1, n):
        cx, cyy, cw, ch, _area = st[k]
        if cx <= 0 or cyy <= 0 or cx + cw >= w - 1 or cyy + ch >= h - 1:
            continue
        if ch / PPM < 0.3 * art_h:
            continue
        bb = (cx / PPM + x0, cyy / PPM + y0, (cx + cw) / PPM + x0, (cyy + ch) / PPM + y0)
        if abs(0.5 * (bb[1] + bb[3]) - cy) > (max(1.5, art_h) if reach is None else reach):
            continue
        keep[k] = bb
    idx = []
    for j in painted:
        s = segs[j]
        mx, my = px(0.5 * (s[0] + s[2]), 0.5 * (s[1] + s[3]))
        if 0 <= my < h and 0 <= mx < w and lab[my, mx] in keep:
            idx.append(j)
    return list(keep.values()), idx


def read_element(runs, box, art_h, cy, keep=None, reach=None):
    """One reader, one file: -> dict (see module doc). The letters' block is
    the one with the most thread in letter-like components. `keep`, a dict,
    is filled with `segs` / `kinds` (the line's own needle-down segments and
    their kinds) and `comps` (its letter-like components' boxes), so a second
    reader can read the SAME selection (`tools/lettering_board.py`).
    `reach`: `components`' centre reach (None: its default)."""
    best = None
    for blk, segs in _segments(runs, box).items():
        kinds = seg_kinds(runs, segs)
        comps, idx = components(segs, kinds, box, art_h, cy, reach)
        ln = sum(_seg_len(segs[j]) for j in idx)
        if comps and (best is None or ln > best[0]):
            best = (ln, blk, comps, [segs[j] for j in idx], [kinds[j] for j in idx])
    if best is None:
        return {"verdict": "DROPPED", "block": None}
    thread, blk, comps, segs, kinds = best
    if keep is not None:
        keep.update(segs=segs, kinds=kinds, comps=comps)
    hmax = max(c[3] - c[1] for c in comps)
    tall = sorted((c for c in comps if c[3] - c[1] >= TALL_FRAC * hmax), key=lambda c: c[0])
    h = statistics.median([c[3] - c[1] for c in tall])
    gaps = [b[0] - a[2] for a, b in zip(tall, tall[1:])]
    total = sum(_seg_len(s) for s in segs) or 1.0
    sat = sum(_seg_len(s) for s, k in zip(segs, kinds) if k == "satin") / total
    bean = sum(_seg_len(s) for s, k in zip(segs, kinds) if k == "bean") / total
    crosses = [_seg_len(s) for s, k in zip(segs, kinds) if k == "satin"]
    stroke = statistics.median(crosses) if crosses else None
    verdict = "SATIN" if sat >= 0.5 else "BEAN" if bean >= 0.4 else "RUN"
    return {
        "block": blk, "verdict": verdict, "h_mm": round(h, 2),
        "w_mm": round(max(c[2] for c in comps) - min(c[0] for c in comps), 2),
        "n": len(comps),
        "gap_mm": round(statistics.median(gaps), 2) if gaps else None,
        "fused": sum(1 for g in gaps if g < FUSED_MM),
        "stroke_mm": None if stroke is None else round(stroke, 2),
        "satin": round(sat, 2), "bean": round(bean, 2),
        "thread_mm": round(thread, 1),
    }


def register(pro: Path, ours: Path):
    """`pairframe.register_pair` without the y-flip candidate: both files are
    read by pystitch y-down, and a near-symmetric design (Fremont's hexagon)
    registers upside down at IoU 0.98 when the flip is allowed."""
    from tools.pro_parity import pairframe as pf
    pro_s = pf.file_segs(Path(pro), False)
    ours_s = pf.file_segs(Path(ours), False)
    s = pf.x_extent(pro_s) / max(pf.x_extent(ours_s), 1e-9)
    ours_s = pf.scale_segs(ours_s, s)
    (pcx, pcy), (ocx, ocy) = pf.centre(pro_s), pf.centre(ours_s)
    dx, dy = pcx - ocx, pcy - ocy
    ours_c = pf.sc.shifted(ours_s, dx, dy)
    rdx, rdy, iou = pf.sc.register(pro_s, ours_c, pf.sc.bounds(pro_s, ours_c))
    return pf.Reg(scale=s, flip_y=False, dx=dx + rdx, dy=dy + rdy, iou=float(iou))


# ------------------------------------------------------------------ files
def _local(path: str) -> Path:
    """A cache's recorded pro / art path, rebased onto whichever Embroidery
    Files root this machine has (`border_census.roots`) when it is missing."""
    p = Path(path)
    if p.exists():
        return p
    from tools.border_census import roots
    parts = p.parts
    if "Embroidery Files" in parts:
        rel = Path(*parts[parts.index("Embroidery Files") + 1:])
        for root in roots():
            # the zip's folder names: some carry a leading space (" Golden Tee")
            for cand in (rel, Path(" " + rel.parts[0], *rel.parts[1:])):
                if (root / cand).exists():
                    return root / cand
    return p


# ------------------------------------------------------------------ the art
def art_letters(info, box):
    """Our OFF regions inside `box` -> (union, art height, art width)."""
    from shapely import wkt
    from shapely.ops import unary_union
    x0, y0, x1, y1 = box
    polys = []
    for r in info["regions"]:
        p = wkt.loads(r["wkt"])
        b = p.bounds
        if b[0] >= x0 - 0.3 and b[2] <= x1 + 0.3 and b[1] >= y0 - 0.3 and b[3] <= y1 + 0.3 and p.area > 0.02:
            polys.append(p)
    if not polys:
        return None, 0.0, 0.0
    hs = [p.bounds[3] - p.bounds[1] for p in polys]
    hmax = max(hs)
    h = statistics.median([v for v in hs if v >= TALL_FRAC * hmax])
    u = unary_union(polys)
    return u, h, u.bounds[2] - u.bounds[0]


def _map_box(box, reg, m_x, m_y):
    s, fy = reg.scale, (-1.0 if reg.flip_y else 1.0)
    xs = [s * x + reg.dx for x in (box[0], box[2])]
    ys = sorted(s * fy * y + reg.dy for y in (box[1], box[3]))
    return (min(xs) - m_x, ys[0] - m_y, max(xs) + m_x, ys[1] + m_y)


def census(caches: dict[str, Path], elements=ELEMENTS) -> list[dict]:
    from tools.study_pro import load_runs

    arms = list(caches)
    rows = []
    loaded: dict = {}
    for slug, label, box, *art_h_mm in elements:
        base = caches[arms[0]] / slug
        if not (base / "ours.json").exists():
            continue
        info = json.loads((base / "ours.json").read_text(encoding="utf-8"))
        letters, art_h, art_w = art_letters(info, box)
        if art_h_mm:
            art_h, art_w = art_h_mm[0], box[2] - box[0]
        elif letters is None:
            continue
        m_y = max(2.5, 1.5 * art_h)
        m_x = 2.0 + 0.5 * art_h
        cy = 0.5 * (box[1] + box[3])
        row = {"slug": slug, "label": label, "width_mm": info["width_mm"],
               "art_h": round(art_h, 2), "art_w": round(art_w, 2)}
        if slug not in loaded:
            pro = _local(info["pro"])
            loaded[slug] = {"pro_runs": load_runs(pro)[0]}
        L = loaded[slug]
        for arm in arms:
            d = caches[arm] / slug
            if not (d / "ours.dst").exists():
                continue
            runs = L.setdefault(arm, load_runs(d / "ours.dst")[0]) if arm not in L else L[arm]
            ob = (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y)
            row["box"] = [round(v, 2) for v in ob]
            row[arm] = read_element(runs, ob, art_h, cy)
            if arm == arms[0]:
                reg = register(_local(info["pro"]), d / "ours.dst")
                row["reg"] = reg.as_dict()
                pb = _map_box(box, reg, m_x * reg.scale, m_y * reg.scale)
                row["pro"] = read_element(L["pro_runs"], pb, art_h * reg.scale, reg.scale * cy + reg.dy)
                row["pro_box"] = [round(v, 2) for v in pb]
        rows.append(row)
    return rows


def table(rows, arms) -> str:
    head = "| job | element | art h / w mm | " + " | ".join(
        f"{a} {c}" for a in arms + ["pro"] for c in ("h", "w", "gap (fused)", "stroke", "sat/bean", "built")) + " |"
    lines = [head, "|" + "---|" * (3 + 6 * (len(arms) + 1))]
    for r in rows:
        cells = [r["slug"], r["label"], f"{r['art_h']} / {r['art_w']}"]
        for a in arms + ["pro"]:
            e = r.get(a) or {}
            if e.get("verdict") == "DROPPED" or not e:
                cells += ["-", "-", "-", "-", "-", e.get("verdict", "n/a")]
                continue
            cells += [str(e["h_mm"]), str(e["w_mm"]), f"{e['gap_mm']} ({e['fused']})",
                      str(e["stroke_mm"]), f"{e['satin']}/{e['bean']}", e["verdict"]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def crops(rows, caches: dict[str, Path], out: Path) -> None:
    """art | each arm | pro around every element, 40 px/mm, each in its own frame."""
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    from tools.pro_parity import pairframe
    out.mkdir(parents=True, exist_ok=True)
    ppm, pad = pp.PPM_CROP, pp.PAD_MM
    renders: dict = {}
    arms = list(caches)
    for r in rows:
        slug = r["slug"]
        info = json.loads((caches[arms[0]] / slug / "ours.json").read_text(encoding="utf-8"))
        if slug not in renders:
            rr = {}
            for arm in arms:
                d = caches[arm] / slug / "ours.dst"
                if d.exists():
                    # each arm's own colour list: an arm can sew a different block order
                    blocks = json.loads((d.parent / "ours.json").read_text(encoding="utf-8"))["blocks"]
                    des = pairframe.design_for(d, None, blocks or None, slug)
                    rr[arm] = (stitchviz.render_design(des, px_per_mm=ppm), pp._design_top_left_mm(des))
            pro_p = _local(info["pro"])
            pd = pairframe.design_for(pro_p, None, None, pro_p.stem)
            rr["pro"] = (stitchviz.render_design(pd, px_per_mm=ppm), pp._design_top_left_mm(pd))
            art = _local(info["art"])
            if not art.exists():
                from tools.border_census import ART_FALLBACK
                art = next((fb for k, fb in ART_FALLBACK.items() if slug.startswith(k)), art)
            ink = pp._art_ink(art)
            rr["art"] = pp._scaled(ink, info["width_mm"], ppm, cv2.INTER_CUBIC)
            renders[slug] = rr
        rr = renders[slug]
        bx0, by0, bx1, by1 = r["box"]
        ox, oy = rr[arms[0]][1]
        tiles = [pp._label(pp._crop_px(rr["art"], (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy), 0.0, ppm), "art")]
        for arm in arms:
            if arm in rr:
                ax, ay = rr[arm][1]
                tiles.append(pp._label(pp._crop_px(rr[arm][0], (bx0 - ax, by0 - ay, bx1 - ax, by1 - ay), pad, ppm), arm))
        qx, qy = rr["pro"][1]
        pb = r["pro_box"]
        tiles.append(pp._label(pp._crop_px(rr["pro"][0], (pb[0] - qx, pb[1] - qy, pb[2] - qx, pb[3] - qy), pad, ppm), "pro"))
        name = f"{slug}_{''.join(ch if ch.isalnum() else '_' for ch in r['label'])}.png"
        cv2.imwrite(str(out / name), pp._vstack(tiles, gap=8))


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["digitize"]:
        return digitize_main(argv[1:])
    if argv[:1] == ["steps"]:
        return steps_main(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", action="append", required=True,
                    help="border_census-style cache(s) holding the OFF arm (searched in order)")
    ap.add_argument("--arm", action="append", default=[], metavar="NAME=DIR")
    ap.add_argument("--crops", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--only", action="append", default=[], help="slug(s) to read")
    args = ap.parse_args(argv)
    # several OFF caches merge per slug (the first that has it)
    off_dirs = [Path(c) for c in args.cache]
    merged = {}
    for slug, *_ in ELEMENTS:
        for c in off_dirs:
            if (c / slug / "ours.json").exists():
                merged[slug] = c
                break
    rows = []
    for slug in dict.fromkeys(e[0] for e in ELEMENTS):
        if slug not in merged or (args.only and slug not in args.only):
            continue
        caches = {"ours": merged[slug]}
        for a in args.arm:
            name, d = a.split("=", 1)
            caches[name] = Path(d)
        sub = census(caches, [e for e in ELEMENTS if e[0] == slug])
        rows += sub
        if args.crops:
            crops(sub, caches, Path(args.crops))
    arms = ["ours"] + [a.split("=", 1)[0] for a in args.arm]
    print(table(rows, arms))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
