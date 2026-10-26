#!/usr/bin/env python
"""outline_census: does an outline IN THE ART predict the pro's border?

The #1043 census found the pro borders by size; #1052 found the real
separator: his bordered letters carry an outline in the customer's art, and
his border is that outline widened to 2.0-2.5 mm. This asks it of every shape
on the paired jobs with ONE rule on ONE side -- `art_outline.find_art_outlines`,
the detector `cfg.border_from_outline` sews from -- against the census's own
reading of the pro's file (`border_census.analyse`, class BORDER).

  python tools/outline_census.py measure [--cache DIR] [--only SLUG ...] [--line-art-guard]
  python tools/outline_census.py digitize SLUG --off DIR --on DIR [--guard DIR]
  python tools/outline_census.py prove --off DIR --on DIR [--only SLUG ...]
  python tools/outline_census.py defects SLUG --off DIR --on DIR [--guard DIR] --crop X0 Y0 X1 Y1

`measure` reads a `border_census` cache (run `border_census.py run` first).
Population: our shapes of at least 1 mm2, less COUNTERS (any shape a letter
holds, sewn or not, or tagged `counter`: the census reads a satin letter
riding its counter's edge as a "border" -- Gaulke's, Fremont's O's) and less
the outline regions themselves (they ARE the outline; their pro class is
listed apart). Label: the pro's class is BORDER. Feature: the shape is a body
the rule finds an outline round. Cohen's kappa beside the raw agreement
(ROADMAP gate 4). The five Becker files are one artwork; so are each pair's.

`digitize` digitizes one job once and plans it twice, OFF and with
`border_from_outline` ON (stage 7 only), into two `border_census` caches
(and, with --guard, a third: ON with `border_from_outline_line_art_guard`);
`prove` censuses both and prints, OFF / ON against the pro: our BORDER vs
his BORDER (kappa, same population) and our border width vs his on the
outlined bodies.

`measure --line-art-guard` reads the census with the guard on: an outline
that is line art (`art_outline.line_art_reading`) is not one. Either way the
last table prints both readings, fill share and dropped share, for every
outline the bare rule reads.

`defects` counts, in one crop window of each file (its own frame, as
`render` crops), SPIKES -- stitches that stick out of their own colour's
silhouette: each colour block painted `THREAD_MM` wide and opened by an
`OPEN_MM` disc; a stitch that leaves the opened body and reaches
`PROTRUDE_MM` beyond it is a ray, rays whose tips lie within 1 mm one fan --
and PINHOLES: garment showing through the render, enclosed by thread, at
least `PINHOLE_MIN_MM2` after a 0.125 mm opening. One reader on every file.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

DIGITIZER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

MIN_AREA_MM2 = 1.0
ARTWORK = {"becker": "Becker", "mfab": "MFab", "bridge": "Bridge", "gaulke": "Gaulke",
           "hotel_fremont": "Fremont", "tires": "Tires", "precision": "Drone", "proseal": "ProSeal"}


def artwork(slug: str) -> str:
    return next((v for k, v in ARTWORK.items() if slug.startswith(k)), slug)


def kappa(tp: int, fp: int, fn: int, tn: int) -> tuple[float, float]:
    """(raw agreement, Cohen's kappa) of a 2x2 table."""
    n = tp + fp + fn + tn
    if n == 0:
        return float("nan"), float("nan")
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def _regions(info: dict):
    from shapely import wkt
    return [SimpleNamespace(shape_id=r["id"], polygon=wkt.loads(r["wkt"]), meta=r["meta"])
            for r in info["regions"]]


def _counters(regions) -> set[str]:
    from digitizer_core.columns import is_lettering
    from digitizer_core.enclosed_white import _encloser
    out = set()
    for r in regions:
        if r.meta.get("counter"):
            out.add(r.shape_id)
        else:
            # anything a letter holds, sewn or not (Fremont's O's hold white)
            h = _encloser(r, regions)
            if h is not None and is_lettering(h, None):
                out.add(r.shape_id)
    return out


def classify(cache: Path, slug: str, guard: bool = False) -> list[dict]:
    """Census rows of one job, each with `role` (body / outline / counter /
    none), `outline` (the holder's id for a body) and `band`/`stroke`.
    `guard`: the rule with `border_from_outline_line_art_guard` on."""
    from digitizer_core.art_outline import find_art_outlines, outline_measures
    info = json.loads((cache / slug / "ours.json").read_text(encoding="utf-8"))
    cen = json.loads((cache / slug / "census.json").read_text(encoding="utf-8"))
    regions = _regions(info)
    by_id = {r.shape_id: r for r in regions}
    outlines = find_art_outlines(regions, line_art_guard=guard)
    body_of = {b: (o, hole) for o, bodies in outlines.items() for b, hole in bodies}
    counters = _counters(regions)
    rows = []
    for row in cen["rows"]:
        if row["area"] < MIN_AREA_MM2:
            continue
        sid = row["id"]
        role = ("outline" if sid in outlines else "body" if sid in body_of
                else "counter" if sid in counters else "none")
        extra = {}
        if role == "body":
            o, hole = body_of[sid]
            band, stroke = outline_measures(by_id[o], by_id[sid], hole)
            extra = {"outline": o, "band": round(band, 2), "stroke": round(stroke, 2)}
        rows.append(dict(row, slug=slug, role=role, **extra))
    return rows


def table(rows: list[dict], label=lambda r: r["pro"]["cls"] == "BORDER") -> dict:
    pop = [r for r in rows if r["role"] in ("body", "none")]
    tp = sum(1 for r in pop if r["role"] == "body" and label(r))
    fp = sum(1 for r in pop if r["role"] == "body" and not label(r))
    fn = sum(1 for r in pop if r["role"] != "body" and label(r))
    tn = len(pop) - tp - fp - fn
    po, k = kappa(tp, fp, fn, tn)
    return {"n": len(pop), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "raw": po, "kappa": k}


def _fmt(t: dict) -> str:
    return (f"| {t['n']} | {t['tp']} | {t['fp']} | {t['fn']} | {t['tn']} | "
            f"{t['raw']:.3f} | {t['kappa']:.2f} |")


def measure_cmd(args) -> int:
    cache = Path(args.cache)
    slugs = [p.name for p in sorted(cache.iterdir()) if (p / "census.json").exists()]
    if args.only:
        slugs = [s for s in slugs if s in args.only]
    all_rows = []
    head = "| job | shapes | outline & pro border | outline, no border | border, no outline | neither | raw | kappa |\n|---|---|---|---|---|---|---|---|"
    print(head)
    for s in slugs:
        rows = classify(cache, s, args.line_art_guard)
        all_rows += rows
        print(f"| {s} " + _fmt(table(rows)))
    print(f"| **pooled** " + _fmt(table(all_rows)))
    big = [r for r in all_rows if r["mindim"] >= 4.0]
    print(f"| pooled, min dim >= 4 mm " + _fmt(table(big)))
    keep: dict[str, str] = {}
    for s in slugs:
        keep.setdefault(artwork(s), s)
    first = [r for r in all_rows if r["slug"] in keep.values()]
    print(f"| one file per artwork " + _fmt(table(first)))

    print("\nBodies (feature on), and every pro BORDER the rule misses:\n")
    print("| job | shape | role | min dim | stroke / band | pro | pro width | ours | holder |\n|---|---|---|---|---|---|---|---|---|")
    for r in all_rows:
        if r["role"] == "body" or (r["role"] == "none" and r["pro"]["cls"] == "BORDER"):
            sb = f"{r['stroke']} / {r['band']}" if r["role"] == "body" else ""
            print(f"| {r['slug']} | {r['id']} | {r['role']} | {r['mindim']} | {sb} | {r['pro']['cls']} | "
                  f"{r['pro']['width']} | {r['ours']['cls']} | {r.get('outline', '')} |")
    print("\nOutline regions (the band itself), pro class:\n")
    for r in all_rows:
        if r["role"] == "outline":
            print(f"- {r['slug']} {r['id']}: pro {r['pro']['cls']} {r['pro']['width']}, ours {r['ours']['cls']} {r['ours']['width']}")
    cnt = sum(1 for r in all_rows if r["role"] == "counter")
    cb = sum(1 for r in all_rows if r["role"] == "counter" and r["pro"]["cls"] == "BORDER")
    print(f"\nCounters left out: {cnt} ({cb} read pro BORDER -- the letter's satin on its edge)")

    print("\nPro border width on outlined, bordered bodies, by min dim:")
    for lo, hi in ((0, 4), (4, 6), (6, 99)):
        ws = [r["pro"]["width"] for r in all_rows if r["role"] == "body" and r["pro"]["cls"] == "BORDER"
              and r["pro"]["width"] and lo <= r["mindim"] < hi]
        if ws:
            print(f"  {lo}-{hi} mm: n={len(ws)} median {statistics.median(ws):.2f} "
                  f"(range {min(ws):.2f}-{max(ws):.2f})")

    # one width per outline: the art outline's own thickness, clamped
    from digitizer_core import machine
    lo, hi = machine.OUTLINE_WIDTH_MM
    print("\nPer outline: the art band round its bodies (median), the rule's width, his width:\n")
    print("| job | outline | bodies | art band | rule width | pro width (bordered bodies) |\n|---|---|---|---|---|---|")
    by: dict[tuple, list] = {}
    for r in all_rows:
        if r["role"] == "body":
            by.setdefault((r["slug"], r["outline"]), []).append(r)
    for (s, o), bs in by.items():
        band = statistics.median(b["band"] for b in bs)
        pw = [b["pro"]["width"] for b in bs if b["pro"]["cls"] == "BORDER" and b["pro"]["width"]]
        print(f"| {s} | {o} | {len(bs)} | {band:.2f} | {min(hi, max(lo, band)):.2f} | "
              + (f"{statistics.median(pw):.2f} (n {len(pw)}) |" if pw else "- |"))

    # the line-art guard's two readings, on every outline the bare rule reads
    from digitizer_core.art_outline import find_art_outlines, line_art_reading
    print(f"\nLine art (`border_from_outline_line_art_guard`): fill share under "
          f"{machine.OUTLINE_LINE_ART_FILL_SHARE} AND dropped at least "
          f"{machine.OUTLINE_LINE_ART_DROP_FRAC}:\n")
    print("| job | outline | bodies | fill share | dropped | line art |\n|---|---|---|---|---|---|")
    for s in slugs:
        regions = _regions(json.loads((cache / s / "ours.json").read_text(encoding="utf-8")))
        by_id = {r.shape_id: r for r in regions}
        for o, bodies in find_art_outlines(regions).items():
            fill, dropped = line_art_reading(by_id[o], [(by_id[b], h) for b, h in bodies])
            art = (fill < machine.OUTLINE_LINE_ART_FILL_SHARE
                   and dropped >= machine.OUTLINE_LINE_ART_DROP_FRAC)
            print(f"| {s} | {o} | {len(bodies)} | {fill:.2f} | {dropped:.3f} | "
                  f"{'yes' if art else 'no'} |")
    return 0


# ------------------------------------------------------------ OFF / ON proof
def digitize_cmd(args) -> int:
    from tools import border_census as bc
    from tools import pro_pair as pp
    from digitizer_core.pipeline import plan_stitches
    row = next(r for r in bc.PAIRS if r[0] == args.slug)
    pro, art = bc.find_pair(*row[:3])
    # --width when the pro's file is out of reach (Drive unmounted): his
    # width from the census table; the pair is then rendered, not scored
    width = args.width if args.width else pp.pro_counts(pro)["width_mm"]
    extra = json.loads(args.extra) if args.extra else {}
    d = pp.digitize(art, width, row[3], extra)
    from dataclasses import replace
    # the flag is ON by default since 2026-10-24, so the OFF arm names it
    plan_off = plan_stitches(d.result, replace(d.cfg, border_from_outline=False))
    bc.write_ours(Path(args.off) / args.slug, args.slug, row[3], width, pro, art, d.result, plan_off, d.secs)
    import pickle
    (Path(args.off) / args.slug / "result.pkl").write_bytes(
        pickle.dumps({"result": d.result, "cfg": d.cfg, "garment": row[3], "width": width,
                      "pro": str(pro), "art": str(art), "secs": d.secs}))
    plans = [("off", plan_off)]
    for tag, out, guard in (("on", args.on, False), ("guard", args.guard, True)):
        if out is None:
            continue
        plan = plan_stitches(d.result, replace(d.cfg, border_from_outline=True,
                                               border_from_outline_line_art_guard=guard))
        bc.write_ours(Path(out) / args.slug, args.slug, row[3], width, pro, art, d.result, plan, d.secs)
        plans.append((tag, plan))
    for tag, plan in plans:
        n = sum(len(r.points or []) for _b, r in plan.iter_runs())
        print(f"{args.slug} {tag}: {n} points, {len(plan.blocks)} blocks")
    return 0


def replan_cmd(args) -> int:
    """Plan a `digitize` run's pickled result again with the flag ON (stage 7
    only, seconds rather than minutes) into --on."""
    import pickle
    from dataclasses import replace
    from tools import border_census as bc
    from digitizer_core.pipeline import plan_stitches
    k = pickle.loads((Path(args.off) / args.slug / "result.pkl").read_bytes())
    plan = plan_stitches(k["result"], replace(k["cfg"], border_from_outline=True,
                                              border_from_outline_line_art_guard=args.line_art_guard))
    bc.write_ours(Path(args.on) / args.slug, args.slug, k["garment"], k["width"], k["pro"], k["art"],
                  k["result"], plan, k["secs"])
    print(args.slug, "on:", sum(len(r.points or []) for _b, r in plan.iter_runs()), "points")
    return 0


def _refind_pro(cache: Path, slug: str) -> None:
    """A cache records the pro file where it was read; when that root has
    gone (Drive unmounted), look it up again through `border_census.find`'s
    roots (PRO_PARITY_ROOT first) and rewrite the record."""
    from tools import border_census as bc
    path = cache / slug / "ours.json"
    info = json.loads(path.read_text(encoding="utf-8"))
    if Path(info["pro"]).exists():
        return
    row = next(r for r in bc.PAIRS if r[0] == slug)
    pro, _art = bc.find_pair(*row[:3])
    if pro is not None:
        info["pro"] = str(pro)
        path.write_text(json.dumps(info), encoding="utf-8")


def prove_cmd(args) -> int:
    from tools import border_census as bc
    off, on = Path(args.off), Path(args.on)
    slugs = [p.name for p in sorted(off.iterdir()) if (p / "ours.json").exists() and (on / p.name / "ours.json").exists()]
    if args.only:
        slugs = [s for s in slugs if s in args.only]
    print("| job | arm | shapes | ours & pro border | ours only | pro only | neither | raw | kappa | "
          "outlined bodies: ours width med / pro | |ours - pro| med |\n|---|---|---|---|---|---|---|---|---|---|---|")
    pooled = {"off": [], "on": []}
    for s in slugs:
        for tag, cache in (("off", off), ("on", on)):
            _refind_pro(cache, s)
            if args.reanalyse or not (cache / s / "census.json").exists():
                (cache / s / "census.json").write_text(json.dumps(bc.analyse(s, cache)), encoding="utf-8")
            rows = classify(cache, s)
            # the feature is OUR file's BORDER here, the label the pro's
            for r in rows:
                # an unsewn body (BECKER's white faces) is still ringed by
                # its outline's loop: read what rides its edge, not "UNSEWN"
                if r["ours"]["cls"] == "UNSEWN":
                    r["ours"] = dict(r["ours"], cls=r["ours"].get("raw_cls", "UNSEWN"),
                                     width=r["ours"].get("raw_width"))
                r["role_rule"] = r["role"]
                if r["role"] in ("body", "none"):
                    r["role"] = "body" if r["ours"]["cls"] == "BORDER" else "none"
            pooled[tag] += rows
            t = table(rows)
            bodies = [r for r in rows if r["role_rule"] == "body"]
            ow = [r["ours"]["width"] for r in bodies if r["ours"]["cls"] == "BORDER" and r["ours"]["width"]]
            pw = [r["pro"]["width"] for r in bodies if r["pro"]["cls"] == "BORDER" and r["pro"]["width"]]
            dif = [abs(r["ours"]["width"] - r["pro"]["width"]) for r in bodies
                   if r["ours"]["width"] and r["pro"]["width"] and "BORDER" == r["ours"]["cls"] == r["pro"]["cls"]]
            med = lambda xs: f"{statistics.median(xs):.2f}" if xs else "-"
            print(f"| {s} | {tag.upper()} " + _fmt(t) + f" {med(ow)} / {med(pw)} (n {len(ow)}/{len(pw)}) | {med(dif)} |")
    for tag in ("off", "on"):
        print(f"| **pooled** | {tag.upper()} " + _fmt(table(pooled[tag])) + " | |")

    from tools import pro_pair as pp
    print("\nThe outline regions themselves (the band the pro sews as his border), and the files:\n")
    print("| job | outline | OFF class, width | ON class, width | pro class, width |\n|---|---|---|---|---|")
    for s in slugs:
        rows = {tag: {r["id"]: r for r in pooled[tag] if r["slug"] == s and r["role_rule"] == "outline"}
                for tag in ("off", "on")}
        for sid, r_off in rows["off"].items():
            r_on = rows["on"].get(sid, r_off)
            cell = lambda c: f"{c['cls']}, {c['width']}"
            print(f"| {s} | {sid} | {cell(r_off['ours'])} | {cell(r_on['ours'])} | {cell(r_off['pro'])} |")
    print("\n| job | OFF stitches / trims | ON stitches / trims | pro stitches / trims |\n|---|---|---|---|")
    for s in slugs:
        c = [pp.pro_counts(cache / s / "ours.dst") for cache in (off, on)]
        info = json.loads((off / s / "ours.json").read_text(encoding="utf-8"))
        pc = pp.pro_counts(info["pro"])
        print(f"| {s} | " + " | ".join(f"{x['stitches']:,} / {x['trims']}" for x in c + [pc]) + " |")
    return 0


def _arms(args) -> list[tuple[str, Path]]:
    """(label, cache) of our arms: OFF, ON and, with --guard, ON+guard."""
    out = [("OFF", Path(args.off)), ("ON", Path(args.on))]
    if getattr(args, "guard", None):
        out.append(("ON+guard", Path(args.guard)))
    return out


# ------------------------------------------------------------ spikes, pinholes
THREAD_MM = 0.4         # a stitch painted this wide
OPEN_MM = 0.8           # the disc that opens a colour's silhouette
PROTRUDE_MM = 0.5       # a stitch reaching this far past it is a spike ray
PINHOLE_MIN_MM2 = 0.03  # garment specks smaller than this are not counted
DEFECT_PPM = 40.0


def _blocks_mm(design) -> list[list[list[tuple[float, float]]]]:
    """Needle-down runs per colour block, mm from the top-left of the file's
    own stitch extents (y down) -- the frame `render --crop` reads."""
    from tools import pro_pair as pp
    x0, top = pp._design_top_left_mm(design)
    blocks, block, cur = [], [], []
    for s in design["stitches"]:
        if s["type"] == "stitch":
            cur.append((s["x"] / 10.0 - x0, -s["y"] / 10.0 - top))
            continue
        if len(cur) > 1:
            block.append(cur)
        cur = []
        if s["type"] in ("color", "end"):
            blocks.append(block)
            block = []
    return blocks


def spike_rays(design, crop) -> list[tuple[float, float]]:
    """The tips of every stitch in `crop` that leaves its own colour's
    opened silhouette and reaches `PROTRUDE_MM` past it."""
    import math
    import cv2
    import numpy as np
    x0, y0, x1, y1 = crop
    w, h = int((x1 - x0) * DEFECT_PPM), int((y1 - y0) * DEFECT_PPM)
    to = lambda q: (int(round((q[0] - x0) * DEFECT_PPM)), int(round((q[1] - y0) * DEFECT_PPM)))
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(OPEN_MM * DEFECT_PPM),) * 2)
    edge = int(OPEN_MM * DEFECT_PPM)
    tips = []
    for runs in _blocks_mm(design):
        mask = np.zeros((h, w), np.uint8)
        segs = [(a, b) for run in runs for a, b in zip(run, run[1:])
                if min(a[0], b[0]) <= x1 and max(a[0], b[0]) >= x0
                and min(a[1], b[1]) <= y1 and max(a[1], b[1]) >= y0]
        if not segs:
            continue
        for a, b in segs:
            cv2.line(mask, to(a), to(b), 1, max(1, int(THREAD_MM * DEFECT_PPM)))
        body = cv2.morphologyEx(mask, cv2.MORPH_OPEN, disc)
        dist = cv2.distanceTransform((1 - body).astype(np.uint8), cv2.DIST_L2, 5) / DEFECT_PPM
        for a, b in segs:
            best, at, base = 0.0, None, math.inf
            for t in np.linspace(0.0, 1.0, 9):
                q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                px, py = to(q)
                if not (0 <= px < w and 0 <= py < h):
                    continue
                d = float(dist[py, px])
                base = min(base, d)
                if edge <= px < w - edge and edge <= py < h - edge and d > best:
                    best, at = d, q
            # a ray leaves a body of its own colour: a run with no body, which
            # the opening deletes whole, is not a spike
            if best >= PROTRUDE_MM and base <= 0.1:
                tips.append(at)
    return tips


def fans(tips) -> int:
    """Rays whose tips lie within 1 mm of each other, chained, are one fan."""
    import math
    groups: list[list] = []
    for t in tips:
        near = [g for g in groups if any(math.dist(t, u) <= 1.0 for u in g)]
        merged = [t] + [u for g in near for u in g]
        groups = [g for g in groups if g not in near] + [merged]
    return len(groups)


def pinholes(design, crop) -> tuple[list[tuple[tuple[float, float], float]], object]:
    """Garment showing through the render inside `crop`, enclosed by thread:
    [((x px, y px), mm2)], and the window image."""
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    win = pp._crop_px(stitchviz.render_design(design, px_per_mm=DEFECT_PPM), crop,
                      pp.PAD_MM, DEFECT_PPM)
    fab = np.all(np.abs(win.astype(int) - np.array(stitchviz.FABRIC_BGR)) <= 2, axis=2)
    fab = cv2.morphologyEx(fab.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, _lab, st, cen = cv2.connectedComponentsWithStats(fab, connectivity=8)
    h, w = fab.shape
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if x == 0 or y == 0 or x + bw >= w or y + bh >= h:
            continue
        if area / DEFECT_PPM ** 2 >= PINHOLE_MIN_MM2:
            out.append(((float(cen[i][0]), float(cen[i][1])), area / DEFECT_PPM ** 2))
    return out, win


def defects_cmd(args) -> int:
    """Spikes and pinholes in one crop window of each arm and the pro's file."""
    import cv2
    from tools import pro_pair as pp
    from tools.pro_parity import pairframe
    files = [(tag, cache / args.slug / "ours.dst") for tag, cache in _arms(args)]
    info = json.loads((Path(args.off) / args.slug / "ours.json").read_text(encoding="utf-8"))
    # his DST beside a PES: the same format as ours, drawn in the same
    # fallback greys (a PES's own black hides his construction on black)
    pro = Path(info["pro"])
    pro = next((q for q in (pro.with_suffix(".DST"), pro.with_suffix(".dst")) if q.exists()), pro)
    if pro.exists():
        files.append(("pro", pro))
    crop = tuple(args.crop)
    print(f"| {args.slug} {args.name or ''} | spike rays | fans | pinholes (mm2) |\n|---|---|---|---|")
    tiles = []
    for tag, path in files:
        d = pairframe.design_for(path, None, None, tag)
        tips = spike_rays(d, crop)
        holes, win = pinholes(d, crop)
        print(f"| {tag} | {len(tips)} | {fans(tips)} | {len(holes)}"
              + (f" ({', '.join(f'{a:.2f}' for _c, a in holes)})" if holes else "") + " |")
        if args.out:
            for t in tips:
                cv2.circle(win, (int((t[0] - crop[0]) * DEFECT_PPM), int((t[1] - crop[1]) * DEFECT_PPM)),
                           8, (255, 0, 255), 3)
            for c, _a in holes:
                cv2.circle(win, (int(c[0]), int(c[1])), 25, (0, 0, 255), 3)
            tiles.append(pp._label(win, f"{tag}: {len(tips)} spike rays / {fans(tips)} fans, "
                                        f"{len(holes)} pinholes"))
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        name = Path(args.out) / f"{args.slug}_{args.name or 'crop'}_defects.{args.ext}"
        cv2.imwrite(str(name), pp._hstack(tiles))
        print("wrote", name)
    return 0


def render_cmd(args) -> int:
    """OFF | ON | pro from the cached DSTs (`digitize`), each in its own frame
    as `tools/pro_pair.py` draws them: the whole design at 20 px/mm and, with
    --crop (mm from the top-left of each file's own stitch extents) or
    --band, a 40 px/mm window."""
    import cv2
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    from tools.pro_parity import pairframe
    off, on, out = Path(args.off), Path(args.on), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = json.loads((off / args.slug / "ours.json").read_text(encoding="utf-8"))
    pro = Path(info["pro"])
    designs, labels = [], []
    for tag, cache in _arms(args):
        inf = json.loads((cache / args.slug / "ours.json").read_text(encoding="utf-8"))
        cols = [tuple(c) for c in inf["blocks"]]
        designs.append(pairframe.design_for(cache / args.slug / "ours.dst", None, cols, f"{tag}"))
        labels.append(tag)
    if pro.exists():
        designs.append(pairframe.design_for(pro, None, None, pro.stem))
        labels.append("pro")
    if args.crop is None and args.band is None:
        imgs = [stitchviz.render_design(d, px_per_mm=pp.PPM) for d in designs]
        name = f"{args.slug}_whole_off_on_pro.{args.ext}"
    else:
        hi = [stitchviz.render_design(d, px_per_mm=pp.PPM_CROP) for d in designs]
        if args.crop is not None:
            imgs = [pp._crop_px(im, tuple(args.crop), pp.PAD_MM, pp.PPM_CROP) for im in hi]
        else:
            b0, b1 = args.band
            imgs = [im[int(im.shape[0] * b0):max(int(im.shape[0] * b0) + 1, int(im.shape[0] * b1)), :]
                    for im in hi]
        name = f"{args.slug}_{args.name or 'crop'}_off_on_pro.{args.ext}"
    cv2.imwrite(str(out / name), pp._hstack([pp._label(i, t) for i, t in zip(imgs, labels)]))
    print("wrote", out / name)
    return 0


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--cache", default=str(DIGITIZER / "debug_out" / "outline_census"))
    m.add_argument("--only", nargs="*")
    m.add_argument("--line-art-guard", action="store_true",
                   help="the rule with border_from_outline_line_art_guard on")
    m.set_defaults(fn=measure_cmd)
    d = sub.add_parser("digitize")
    d.add_argument("slug")
    d.add_argument("--off", required=True)
    d.add_argument("--on", required=True)
    d.add_argument("--guard", help="a third cache: ON with border_from_outline_line_art_guard")
    d.add_argument("--extra", help="JSON laid over the Studio request (e.g. a flag both arms carry)")
    d.add_argument("--width", type=float, help="design width, mm, when the pro's file is unreachable")
    d.set_defaults(fn=digitize_cmd)
    q = sub.add_parser("replan")
    q.add_argument("slug")
    q.add_argument("--off", required=True)
    q.add_argument("--on", required=True)
    q.add_argument("--line-art-guard", action="store_true",
                   help="plan --on with border_from_outline_line_art_guard as well")
    q.set_defaults(fn=replan_cmd)
    p = sub.add_parser("prove")
    p.add_argument("--off", required=True)
    p.add_argument("--on", required=True)
    p.add_argument("--only", nargs="*")
    p.add_argument("--reanalyse", action="store_true")
    p.set_defaults(fn=prove_cmd)
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--off", required=True)
    r.add_argument("--on", required=True)
    r.add_argument("--guard", help="a third arm: the ON+guard cache")
    r.add_argument("--out", required=True)
    r.add_argument("--crop", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    r.add_argument("--band", nargs=2, type=float, metavar=("Y0FRAC", "Y1FRAC"))
    r.add_argument("--name")
    r.add_argument("--ext", default="png", help="png, or jpg for a committed render")
    r.set_defaults(fn=render_cmd)
    f = sub.add_parser("defects")
    f.add_argument("slug")
    f.add_argument("--off", required=True)
    f.add_argument("--on", required=True)
    f.add_argument("--guard", help="a third arm: the ON+guard cache")
    f.add_argument("--crop", nargs=4, type=float, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    f.add_argument("--out", help="write the marked windows here")
    f.add_argument("--name")
    f.add_argument("--ext", default="png", help="png, or jpg for a committed render")
    f.set_defaults(fn=defects_cmd)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
