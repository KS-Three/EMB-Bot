#!/usr/bin/env python
"""outline_census: does an outline IN THE ART predict the pro's border?

The #1043 census found the pro borders by size; #1052 found the real
separator: his bordered letters carry an outline in the customer's art, and
his border is that outline widened to 2.0-2.5 mm. This asks it of every shape
on the paired jobs with ONE rule on ONE side -- `art_outline.find_art_outlines`,
the detector `cfg.border_from_outline` sews from -- against the census's own
reading of the pro's file (`border_census.analyse`, class BORDER).

  python tools/outline_census.py measure [--cache DIR] [--only SLUG ...]
  python tools/outline_census.py digitize SLUG --off DIR --on DIR   # one result, two plans
  python tools/outline_census.py prove --off DIR --on DIR [--only SLUG ...]

`measure` reads a `border_census` cache (run `border_census.py run` first).
Population: our shapes of at least 1 mm2, less COUNTERS (any shape a letter
holds, sewn or not, or tagged `counter`: the census reads a satin letter
riding its counter's edge as a "border" -- Gaulke's, Fremont's O's) and less
the outline regions themselves (they ARE the outline; their pro class is
listed apart). Label: the pro's class is BORDER. Feature: the shape is a body
the rule finds an outline round. Cohen's kappa beside the raw agreement
(ROADMAP gate 4). The five Becker files are one artwork; so are each pair's.

`digitize` digitizes one job once and plans it twice, OFF and with
`border_from_outline` ON (stage 7 only), into two `border_census` caches;
`prove` censuses both and prints, OFF / ON against the pro: our BORDER vs
his BORDER (kappa, same population) and our border width vs his on the
outlined bodies.
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


def classify(cache: Path, slug: str) -> list[dict]:
    """Census rows of one job, each with `role` (body / outline / counter /
    none), `outline` (the holder's id for a body) and `band`/`stroke`."""
    from digitizer_core.art_outline import find_art_outlines, outline_measures
    info = json.loads((cache / slug / "ours.json").read_text(encoding="utf-8"))
    cen = json.loads((cache / slug / "census.json").read_text(encoding="utf-8"))
    regions = _regions(info)
    by_id = {r.shape_id: r for r in regions}
    outlines = find_art_outlines(regions)
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
        rows = classify(cache, s)
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
    bc.write_ours(Path(args.off) / args.slug, args.slug, row[3], width, pro, art, d.result, d.plan, d.secs)
    import pickle
    (Path(args.off) / args.slug / "result.pkl").write_bytes(
        pickle.dumps({"result": d.result, "cfg": d.cfg, "garment": row[3], "width": width,
                      "pro": str(pro), "art": str(art), "secs": d.secs}))
    from dataclasses import replace
    on_cfg = replace(d.cfg, border_from_outline=True)
    plan_on = plan_stitches(d.result, on_cfg)
    bc.write_ours(Path(args.on) / args.slug, args.slug, row[3], width, pro, art, d.result, plan_on, d.secs)
    for tag, plan in (("off", d.plan), ("on", plan_on)):
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
    plan = plan_stitches(k["result"], replace(k["cfg"], border_from_outline=True))
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
    for tag, cache in (("OFF", off), ("ON", on)):
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
    m.set_defaults(fn=measure_cmd)
    d = sub.add_parser("digitize")
    d.add_argument("slug")
    d.add_argument("--off", required=True)
    d.add_argument("--on", required=True)
    d.add_argument("--extra", help="JSON laid over the Studio request (e.g. a flag both arms carry)")
    d.add_argument("--width", type=float, help="design width, mm, when the pro's file is unreachable")
    d.set_defaults(fn=digitize_cmd)
    q = sub.add_parser("replan")
    q.add_argument("slug")
    q.add_argument("--off", required=True)
    q.add_argument("--on", required=True)
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
    r.add_argument("--out", required=True)
    r.add_argument("--crop", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    r.add_argument("--band", nargs=2, type=float, metavar=("Y0FRAC", "Y1FRAC"))
    r.add_argument("--name")
    r.add_argument("--ext", default="png", help="png, or jpg for a committed render")
    r.set_defaults(fn=render_cmd)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
