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

Report-only; changes nothing. Measured 2026-10-12, PR body.
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


def run(rel: str, cfg_kw: dict) -> dict:
    gen = build_generation(str(ROOT / "testdata" / rel), PipelineConfig(**cfg_kw))
    out: dict = {"fixture": rel, "cfg": cfg_kw}
    off_by_id: dict = {}
    for tag, flag in (("off", False), ("on", True)):
        cfg = PipelineConfig(**cfg_kw, clip_keep_pieces=flag)
        result = finish_generation(gen.fork(), cfg)
        plan, planned = _plan(result, cfg)
        st = plan.stats
        row = {"stitches": st.stitch_count, "trims": st.trims, "md5": plan_md5(plan)}
        if not flag:
            off_by_id = {p.shape_id: p for p in planned}
        if flag:
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
    args = ap.parse_args(argv)
    from tools.corpus_scorecard import FIXTURES, MATRIX
    rows = MATRIX if args.matrix is None else [MATRIX[args.matrix]]
    names = list(FIXTURES) if args.scorecard else (args.fixtures or list(DEFAULT))
    for rel in names:
        for m in rows:
            kw = dict(m)
            if args.max_colors:
                kw["max_colors"] = args.max_colors
            try:
                r = run(rel, kw)
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the sweep
                print(json.dumps({"fixture": rel, "cfg": kw, "error": f"{type(exc).__name__}: {exc}"}),
                      flush=True)
                continue
            if args.json:
                print(json.dumps(r), flush=True)
                continue
            o, i = r["off"], r["on"]
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
