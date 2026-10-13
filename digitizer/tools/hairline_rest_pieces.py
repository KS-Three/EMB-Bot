#!/usr/bin/env python
"""`stage6_hairline.rest_planned`: what a split rest piece keeps and what it loses.

Under `cfg.hairline` a shape with thick AND thin branches sews its thin ones
as runs and hands the thick part (`m["rest"]`) to the ladder, one copy per
connected piece (`rest_planned`). Each piece's sewing polygon is `p.polygon`
(stage 5's output, clipped by every colour already sewn) cut to the piece. If
that clip left the piece's sewing polygon in several real parts, a keep-the-
largest rule sewed one and dropped the others' ink with no warning (the
hairline twin of defect 61, flagged by PR #855's audit). `rest_planned` now
keeps every part whose artwork clears `clip_piece_floor_mm2` and counts the
rest like stage 5's `CLIP_DROPPED_SLIVER`.

Per fixture, matrix row and mode (`hairline`, then `hairline` +
`hairline_over_ground`), one `build_generation` and one plan with
`stage7_sequence.rest_planned` spied, then per rest piece:

  * `parts` -- the connected parts of its sewing polygon;
  * `before_mm2` -- the INK (a part clipped to the piece's artwork) the OLD
    rule dropped: every part but the largest by area (`rest_sew_parts` sorts
    largest first and the old `rest_planned` sewed `sew[0]`);
  * `unsewn_mm2` -- the ink of every part at or over the floor that the
    CURRENT `rest_planned` did not hand to the ladder (its sewing polygon
    equals no returned copy's), read OFF the function's real output;
  * `slivers` / `sliver_mm2` -- the parts under the floor that carry some ink
    and were not handed to the ladder (a piece\'s main copy is always sewn,
    however small): the ones the warning counts, cross-checked against the
    plan's own `CLIP_DROPPED_SLIVER` warning (`warned`);
  * `uncovered` -- `ARTWORK_UNCOVERED`'s missing mm2 on the parent shape, read
    only for a plan that has an unsewn part above the floor.

    python -m tools.hairline_rest_pieces                    # drone
    python -m tools.hairline_rest_pieces --scorecard        # every corpus_scorecard FIXTURE x MATRIX
    python -m tools.hairline_rest_pieces --scorecard --json
    python -m tools.hairline_rest_pieces --scorecard --off-md5   # hairline OFF plan md5 per row

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

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core import stage7_sequence  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_core.stage5_overlap import clip_piece_floor_mm2  # noqa: E402
from digitizer_core.stage6_hairline import rest_sew_parts  # noqa: E402
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER  # noqa: E402

DEFAULT = ("photo/drone_render.png",)
MODES = (("hairline", {"hairline": True}),
         ("hairline+ground", {"hairline": True, "hairline_over_ground": True}))


def plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def census_piece(piece, parts, handed, floor: float) -> dict:
    """One rest piece: `parts` (largest first, as `rest_sew_parts` returns
    them), the sewing polygons the ladder was handed for it (`handed`), the
    ink the old keep-the-largest rule dropped, the ink of at-or-over-floor
    parts the current rule did not hand over, and the sub-floor slivers."""
    ink = [float(g.intersection(piece).area) for g in parts]
    sewn = [any(g.equals_exact(h, 1e-9) for h in handed) for g in parts]
    above = [i for i, a in enumerate(ink) if a >= floor]
    unsewn = [i for i in above if not sewn[i]]
    slivers = [i for i, a in enumerate(ink) if 1e-6 < a < floor and not sewn[i]]
    return {"parts": len(parts), "above_floor": len(above),
            "ink_mm2": [round(a, 3) for a in ink],
            "before_mm2": round(sum(ink[1:]), 3),
            "unsewn_above_floor": len(unsewn),
            "unsewn_mm2": round(sum(ink[i] for i in unsewn), 3),
            "slivers": len(slivers),
            "sliver_mm2": round(sum(ink[i] for i in slivers), 3)}


def run_mode(gen, cfg_kw: dict, extra: dict) -> dict:
    """One plan with `rest_planned` spied. -> the mode's census."""
    cfg = PipelineConfig(**cfg_kw, **extra)
    result = finish_generation(gen.fork(), cfg)
    floor = clip_piece_floor_mm2(cfg)
    orig = stage7_sequence.rest_planned
    shapes: list[dict] = []

    def spy(p, m, *a, **k):
        got = orig(p, m, *a, **k)
        pieces = []
        for piece, parts in rest_sew_parts(p, m):
            # A part's copy is told apart by its sewing polygon; a copy of
            # this piece also has the piece (or the main copy's remainder of
            # it) as its artwork, so match on the sewing polygon alone.
            handed = [c.polygon for c in got if c.region.polygon.intersects(piece)]
            pieces.append(census_piece(piece, parts, handed, floor))
        if pieces:
            shapes.append({"shape_id": p.shape_id, "pieces": pieces})
        return got

    stage7_sequence.rest_planned = spy
    try:
        plan = plan_stitches(result, cfg)
    finally:
        stage7_sequence.rest_planned = orig
    pieces = [x for s in shapes for x in s["pieces"]]
    warned = sum(w.get("count", 0) for w in plan.warnings
                 if w.get("code") == CLIP_DROPPED_SLIVER and w.get("source") == "hairline_rest")
    lost = [s for s in shapes if any(x["unsewn_above_floor"] for x in s["pieces"])]
    multi = [{"shape_id": s["shape_id"], "parts": x["parts"], "ink_mm2": x["ink_mm2"],
              "before_mm2": x["before_mm2"], "unsewn_mm2": x["unsewn_mm2"],
              "slivers": x["slivers"], "sliver_mm2": x["sliver_mm2"]}
             for s in shapes for x in s["pieces"] if x["parts"] > 1]
    return {"multi": multi, "cfg": extra, "floor_mm2": round(floor, 4), "plan": plan,
            "result": result, "cfg_obj": cfg,
            "shapes_with_rest": len(shapes), "rest_pieces": len(pieces),
            "multi_part_pieces": sum(1 for x in pieces if x["parts"] > 1),
            "multi_above_floor": sum(1 for x in pieces if x["above_floor"] > 1),
            "before_mm2": round(sum(x["before_mm2"] for x in pieces), 3),
            "unsewn_pieces": sum(1 for x in pieces if x["unsewn_above_floor"]),
            "unsewn_mm2": round(sum(x["unsewn_mm2"] for x in pieces), 3),
            "slivers": sum(x["slivers"] for x in pieces), "warned": warned,
            "sliver_mm2": round(sum(x["sliver_mm2"] for x in pieces), 3),
            "lost_shapes": lost}


def uncovered_for(m: dict, image) -> dict:
    from digitizer_core.preflight import ARTWORK_UNCOVERED, run_preflight
    report = run_preflight(m["result"], m["plan"], m["cfg_obj"], image=image)
    out = {}
    for f in report["findings"]:
        if f.get("code") == ARTWORK_UNCOVERED:
            for s in (f.get("extra") or f).get("shapes", []):
                out[s["shape_id"]] = s["missing_mm2"]
    return out


def run(rel: str, cfg_kw: dict) -> dict:
    image = ROOT / "testdata" / rel
    gen = build_generation(str(image), PipelineConfig(**cfg_kw))
    out: dict = {"fixture": rel, "cfg": cfg_kw, "modes": {}}
    for tag, extra in MODES:
        m = run_mode(gen, cfg_kw, extra)
        row = {k: v for k, v in m.items()
               if k not in ("plan", "result", "cfg_obj", "lost_shapes")}
        row["lost"] = m["lost_shapes"]
        if m["lost_shapes"]:
            unc = uncovered_for(m, image)
            for s in row["lost"]:
                s["uncovered_mm2"] = unc.get(s["shape_id"])
            row["uncovered_fires"] = any(s["uncovered_mm2"] for s in row["lost"])
        out["modes"][tag] = row
    return out


def off_md5(rel: str, cfg_kw: dict) -> str:
    cfg = PipelineConfig(**cfg_kw)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg)
    return plan_md5(plan_stitches(finish_generation(gen.fork(), cfg), cfg))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/")
    ap.add_argument("--scorecard", action="store_true",
                    help="every corpus_scorecard FIXTURE x MATRIX row")
    ap.add_argument("--matrix", type=int, default=None,
                    help="only this corpus_scorecard MATRIX row (0-based)")
    ap.add_argument("--only", default=None, help="substring filter on fixture name")
    ap.add_argument("--slice", default=None,
                    help="LO:HI over the fixture list, to shard a sweep across processes")
    ap.add_argument("--json", action="store_true", help="one JSON line per run")
    ap.add_argument("--off-md5", action="store_true",
                    help="print the hairline-OFF plan md5 per row instead of the census")
    args = ap.parse_args(argv)
    from tools.corpus_scorecard import FIXTURES, MATRIX
    rows = MATRIX if args.matrix is None else [MATRIX[args.matrix]]
    names = list(FIXTURES) if args.scorecard else (args.fixtures or list(DEFAULT))
    if args.only:
        names = [n for n in names if args.only in n]
    if args.slice:
        lo, _, hi = args.slice.partition(":")
        names = names[int(lo or 0):int(hi) if hi else None]
    for rel in names:
        for m in rows:
            kw = dict(m)
            try:
                if args.off_md5:
                    print(f"{rel} {kw.get('garment_id')} {off_md5(rel, kw)}", flush=True)
                    continue
                r = run(rel, kw)
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the sweep
                print(json.dumps({"fixture": rel, "cfg": kw,
                                  "error": f"{type(exc).__name__}: {exc}"}), flush=True)
                continue
            if args.json:
                print(json.dumps(r), flush=True)
                continue
            for tag, row in r["modes"].items():
                print(f"{rel} {kw.get('garment_id')} [{tag}]: "
                      f"{row['shapes_with_rest']} shapes with a rest, {row['rest_pieces']} pieces, "
                      f"{row['multi_part_pieces']} multi-part ({row['multi_above_floor']} above the "
                      f"{row['floor_mm2']} mm2 floor); ink dropped before {row['before_mm2']:.3f} -> "
                      f"after {row['unsewn_mm2']:.3f} mm2; {row['slivers']} sliver(s) "
                      f"{row['sliver_mm2']:.3f} mm2 counted (warned {row['warned']})", flush=True)
                for x in row["multi"]:
                    print(f"    multi-part {x['shape_id']}: ink per part {x['ink_mm2']}", flush=True)
                for s in row["lost"]:
                    print(f"    {s['shape_id']}: still unsewn "
                          f"{[(x['ink_mm2'], x['unsewn_mm2']) for x in s['pieces'] if x['unsewn_above_floor']]}"
                          f" uncovered_mm2={s['uncovered_mm2']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
