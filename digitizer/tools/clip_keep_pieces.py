#!/usr/bin/env python
"""`cfg.clip_keep_pieces` (defect 61): what stage 5's clip cuts off a shape, OFF vs ON.

Stage 5 grows each shape, then clips it by every colour already sewn. Where
that clip cuts the shape in two, OFF keeps only the largest piece
(`_largest_polygon`) and drops the rest without a word. ON keeps every piece
whose ARTWORK clears the stage-4 region floor as its own region of the same
thread and tier, and counts the rest in `CLIP_DROPPED_SLIVER`.

Per fixture and matrix row, one generation and stages 5-7 twice:

  * `splits` — every shape the clip cut where it matters: each cut-off
    piece's artwork area (mm²), whether ON keeps it, and how much of it no
    other sewn polygon covers (`bare`: what OFF leaves as fabric); and every
    parent that sews a DIFFERENT piece ON because OFF's largest piece was not
    the one carrying its ink (`switched`, artwork sewn OFF -> ON);
  * cost — stitches and trims OFF -> ON, and whether the OFF plan's md5
    equals the ON plan's (it must wherever nothing splits over the floor).

    python -m tools.clip_keep_pieces                     # drone
    python -m tools.clip_keep_pieces --scorecard         # every corpus_scorecard FIXTURE x MATRIX
    python -m tools.clip_keep_pieces photo/drone_render.png --matrix 0 --json
    python -m tools.clip_keep_pieces --halo-lever        # the six split fixtures

`--halo-lever` prices the flip on top of bridge's JPEG-halo lever, the
banked `cfg.dissolve_phantom_blends` (MASTER_SCOPE item 46: "the halo at its
own lever first, then this flip"). Per fixture, garment and lever setting:
the shipped default against `clip_keep_pieces` ON -- stitches, trims, each
kept piece's thread and its parent's mean width (`2 * area / perimeter`;
`thin` is under `tools.halo_spools.HALO_MAX_WIDTH_MM`), and Cohen's kappa of
thread-down against that arm's own stitched artwork, chance-corrected so a
gain is not the floor moving (ROADMAP gate 4). `thin` is NOT a halo test:
gaulke's roof line was thin and real (DOCTRINE: nothing yet tells a halo
band from a drawn stroke), so the reading names the threads and leaves the
call to the reader. `halo_spools`' own test flags no region on bridge at
today's defaults, so it cannot be the tag here (measured 2026-10-20).

Report-only; changes nothing. Measured 2026-10-12 and 2026-10-20, PR bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core import pipeline  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_core.stage5_overlap import CLIP_PIECE_OF_KEY, clip_piece_floor_mm2  # noqa: E402
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER  # noqa: E402

DEFAULT = ("photo/drone_render.png",)


def plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _plan(result, cfg):
    """plan_stitches, with stage 5's planned regions captured."""
    seen = []
    orig = pipeline.resolve_overlaps

    def spy(*a, **k):
        planned, warns = orig(*a, **k)
        seen.extend(planned)
        return planned, warns

    pipeline.resolve_overlaps = spy
    try:
        plan = plan_stitches(result, cfg)
    finally:
        pipeline.resolve_overlaps = orig
    return plan, seen


def _uncovered(result, plan, cfg, image) -> dict:
    """`ARTWORK_UNCOVERED`'s reading of this plan: {shape_id: missing mm²}."""
    from digitizer_core.preflight import ARTWORK_UNCOVERED, run_preflight
    report = run_preflight(result, plan, cfg, image=image)
    out = {}
    for f in report["findings"]:
        if f.get("code") == ARTWORK_UNCOVERED:
            for s in (f.get("extra") or f).get("shapes", []):
                out[s["shape_id"]] = s["missing_mm2"]
    return out


def run(rel: str, cfg_kw: dict, preflight: bool = False, full: bool = False) -> dict:
    """OFF = both settings False (the engine before defect 61); ON = the
    shipped default, `clip_parent_keeps_ink` alone; FULL (`full=True`) =
    `clip_keep_pieces` too, which keeps the extra pieces as their own regions."""
    gen = build_generation(str(ROOT / "testdata" / rel), PipelineConfig(**cfg_kw))
    out: dict = {"fixture": rel, "cfg": cfg_kw}
    off_by_id: dict = {}
    variants = [("off", False, False), ("on", True, False)]
    if full:
        variants.append(("full", True, True))
    for tag, flag, keep in variants:
        cfg = PipelineConfig(**cfg_kw, clip_parent_keeps_ink=flag, clip_keep_pieces=keep)
        result = finish_generation(gen.fork(), cfg)
        plan, planned = _plan(result, cfg)
        st = plan.stats
        row = {"stitches": st.stitch_count, "trims": st.trims, "md5": plan_md5(plan)}
        if preflight:
            row["uncovered"] = _uncovered(result, plan, cfg, ROOT / "testdata" / rel)
        if tag == "off":
            off_by_id = {p.shape_id: p for p in planned}
        else:
            floor = clip_piece_floor_mm2(cfg)
            sewn_by = {}
            for p in planned:
                sewn_by.setdefault(p.shape_id, []).append(p.polygon)
            kept = [p for p in planned if p.region.meta.get(CLIP_PIECE_OF_KEY)]
            slivers = [w for w in plan.warnings if w.get("code") == CLIP_DROPPED_SLIVER]
            splits: dict[str, list] = {}
            for p in kept:
                parent = p.region.meta[CLIP_PIECE_OF_KEY]
                others = [g for s, gs in sewn_by.items() if s != p.shape_id for g in gs]
                art = p.region.polygon
                bare = art.difference(unary_union([g for g in others])) if others else art
                # `others` includes the parent's own polygon: the piece's
                # artwork is disjoint from it by construction, so this is
                # what OFF left as fabric once every OTHER shape is down.
                splits.setdefault(parent, []).append(
                    {"art_mm2": round(art.area, 3), "kept": True,
                     "bare_off_mm2": round(bare.area, 3)})
            for w in slivers:
                for s in w.get("pieces", []):
                    splits.setdefault(s["id"], []).append(
                        {"art_mm2": s["art_mm2"], "kept": False})
            # A parent that sews a DIFFERENT piece ON: OFF's largest piece
            # was not the one carrying the ink (`_split_clip`).
            for p in planned:
                if p.region.meta.get(CLIP_PIECE_OF_KEY) or p.shape_id not in off_by_id:
                    continue
                o = off_by_id[p.shape_id]
                if p.polygon.equals_exact(o.polygon, 0.0):
                    continue
                art = o.region.polygon
                splits.setdefault(p.shape_id, []).append(
                    {"switched": True,
                     "art_off_mm2": round(o.polygon.intersection(art).area, 3),
                     "art_on_mm2": round(p.polygon.intersection(art).area, 3),
                     "sewn_off_mm2": round(o.polygon.area, 3),
                     "sewn_on_mm2": round(p.polygon.area, 3)})
            row.update(floor_mm2=round(floor, 4), splits=splits,
                       sliver_count=sum(w.get("count", 0) for w in slivers))
        out[tag] = row
    return out


# The fixtures #853's census found a split carrying ink on (MASTER_SCOPE 61).
SPLIT_FIXTURES = (
    "photo/logo_bridge_bar.jpg",
    "photo/drone_render.png",
    "photo/logo_golden_tee.jpg",
    "photo/logo_gaulke_roofing.png",
    "photo/photo_chrome_specular.png",
    "photo/photo_sunset_backlit.png",
)
KAPPA_PX_PER_MM = 10.0


def coverage_kappa(truth, sewn, bounds, px_per_mm: float = KAPPA_PX_PER_MM) -> float | None:
    """Cohen's kappa of two binary rasters -- `truth` and `sewn` geometries
    sampled at pixel centres over `bounds` -- or None where it is undefined."""
    import numpy as np
    import shapely

    x0, y0, x1, y1 = bounds
    step = 1.0 / px_per_mm
    xs = np.arange(x0 + step / 2, x1, step)
    ys = np.arange(y0 + step / 2, y1, step)
    gx, gy = np.meshgrid(xs, ys)
    t = shapely.contains_xy(truth, gx, gy).ravel() if not truth.is_empty else np.zeros(gx.size, bool)
    p = shapely.contains_xy(sewn, gx, gy).ravel() if not sewn.is_empty else np.zeros(gx.size, bool)
    po = float(np.mean(t == p))
    pt, pp = float(t.mean()), float(p.mean())
    pe = pt * pp + (1 - pt) * (1 - pp)
    return None if pe >= 1.0 else (po - pe) / (1 - pe)


def price_halo_lever(rel: str, cfg_kw: dict) -> dict:
    """The flip, `clip_keep_pieces` OFF -> ON, with the halo lever
    (`dissolve_phantom_blends`) OFF and ON. See the module docstring."""
    from tools.halo_spools import HALO_MAX_WIDTH_MM, _width_mm

    path = ROOT / "testdata" / rel
    out: dict = {"fixture": rel, "cfg": cfg_kw}
    for lever in (False, True):
        gen = build_generation(str(path), PipelineConfig(**cfg_kw, dissolve_phantom_blends=lever))
        arm: dict = {}
        truth = bounds = None
        for tag, keep in (("default", False), ("pieces", True)):
            cfg = PipelineConfig(**cfg_kw, dissolve_phantom_blends=lever, clip_keep_pieces=keep)
            result = finish_generation(gen.fork(), cfg)
            plan, planned = _plan(result, cfg)
            by_id = {r.shape_id: r for r in result.regions}
            if truth is None:
                # Stages 1-4 are shared by both plans of an arm.
                truth = unary_union([r.polygon for r in result.regions
                                     if r.meta.get("stitched", True)])
                bounds = unary_union([r.polygon for r in result.regions]).buffer(2.0).bounds
            pieces = []
            for p in planned:
                parent = p.region.meta.get(CLIP_PIECE_OF_KEY)
                if not parent:
                    continue
                w = _width_mm(by_id[parent].polygon)
                pieces.append({"thread": by_id[parent].thread_number,
                               "parent_width_mm": round(w, 3),
                               "thin": w < HALO_MAX_WIDTH_MM,
                               "art_mm2": round(p.region.polygon.area, 2)})
            kappa = coverage_kappa(truth, unary_union([p.polygon for p in planned]), bounds)
            arm[tag] = {
                "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                "md5": plan_md5(plan),
                "regions": len(result.regions),
                "pieces": pieces,
                "kappa": None if kappa is None else round(kappa, 4),
            }
        out["lever_on" if lever else "lever_off"] = arm
    return out


def _print_halo_lever(r: dict) -> None:
    g = r["cfg"].get("garment_id")
    for lever in ("lever_off", "lever_on"):
        d, p = r[lever]["default"], r[lever]["pieces"]
        ds = p["stitches"] - d["stitches"]
        pcs = p["pieces"]
        thin = [x for x in pcs if x["thin"]]
        threads = ",".join(sorted({x["thread"] for x in thin})) or "-"
        print(f"{r['fixture']} {g} {lever}: stitches {d['stitches']}->{p['stitches']} "
              f"({ds:+d}, {100.0 * ds / d['stitches']:+.1f}%), trims {d['trims']}->{p['trims']}, "
              f"pieces {len(pcs)} ({sum(x['art_mm2'] for x in pcs):.2f} mm2 art), "
              f"thin {len(thin)} ({sum(x['art_mm2'] for x in thin):.2f} mm2, threads {threads}), "
              f"kappa {d['kappa']}->{p['kappa']}", flush=True)


def _scorecard_cases():
    from tools.corpus_scorecard import FIXTURES, MATRIX
    return [(f, dict(m)) for f in FIXTURES for m in MATRIX]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/")
    ap.add_argument("--scorecard", action="store_true",
                    help="every corpus_scorecard FIXTURE x MATRIX row")
    ap.add_argument("--matrix", type=int, default=None,
                    help="only this corpus_scorecard MATRIX row (0-based)")
    ap.add_argument("--max-colors", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="one JSON line per run")
    ap.add_argument("--preflight", action="store_true",
                    help="also read ARTWORK_UNCOVERED's per-shape finding OFF and ON")
    ap.add_argument("--full", action="store_true",
                    help="also run FULL: clip_keep_pieces on too (extra pieces as own regions)")
    ap.add_argument("--halo-lever", action="store_true",
                    help="price the flip with dissolve_phantom_blends OFF and ON")
    args = ap.parse_args(argv)
    from tools.corpus_scorecard import FIXTURES, MATRIX
    if args.halo_lever:
        rows = MATRIX if args.matrix is None else [MATRIX[args.matrix]]
        for rel in (args.fixtures or SPLIT_FIXTURES):
            for m in rows:
                r = price_halo_lever(rel, dict(m))
                print(json.dumps(r), flush=True) if args.json else _print_halo_lever(r)
        return 0
    rows = MATRIX if args.matrix is None else [MATRIX[args.matrix]]
    names = list(FIXTURES) if args.scorecard else (args.fixtures or list(DEFAULT))
    for rel in names:
        for m in rows:
            kw = dict(m)
            if args.max_colors:
                kw["max_colors"] = args.max_colors
            try:
                r = run(rel, kw, preflight=args.preflight, full=args.full)
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the sweep
                print(json.dumps({"fixture": rel, "cfg": kw, "error": f"{type(exc).__name__}: {exc}"}),
                      flush=True)
                continue
            if args.json:
                print(json.dumps(r), flush=True)
                continue
            o, i = r["off"], r["full" if args.full else "on"]
            n_split = len(i["splits"])
            entries = [s for v in i["splits"].values() for s in v]
            kept = sum(1 for s in entries if s.get("kept"))
            switched = sum(1 for s in entries if s.get("switched"))
            dropped = (sum(s.get("art_mm2", 0.0) for s in entries)
                       + sum(s["art_on_mm2"] - s["art_off_mm2"] for s in entries if s.get("switched")))
            print(f"{rel} {kw.get('garment_id')}: {n_split} shapes split, "
                  f"{dropped:.2f} mm2 artwork dropped OFF, {kept} pieces kept ON, "
                  f"{switched} parents switched to their ink, "
                  f"{i['sliver_count']} slivers; stitches {o['stitches']}->{i['stitches']}, "
                  f"trims {o['trims']}->{i['trims']}, md5 {'same' if o['md5'] == i['md5'] else 'DIFFERS'}",
                  flush=True)
            for sid, pieces in sorted(i["splits"].items()):
                print(f"    {sid}: {pieces}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
