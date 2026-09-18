#!/usr/bin/env python
"""How much of each shape's pull compensation survives stage 5.

Stage 5 grows every shape by the fabric's pull (`poly.buffer(pull)`) and then
clips it with *"never grow back over a color that is already down"*
(`stage5_overlap.resolve_overlaps`). A shape that sits in a HOLE of a ground
sewn earlier -- lettering on a patch fill -- is cut back to that hole, which is
its own artwork: the growth is taken back almost entirely, and the column sews
at artwork width. Found 2026-09-16 on Hotel Fremont at 92.5 mm chasing Kent's
"the T still needs a lot of work": THE's 0.41 mm stems grow to 1.01 mm and are
planned at 0.48 mm, under `SATIN_MIN_CROSS_MM`, so the T and E sew as bean runs
while the pro sews the same letters as 0.90 mm satin
(`docs/fremont-t-ground-clip-2026-09-16.md`).

Per planned shape, against its own artwork polygon `A`, the pull band
`B = A.buffer(pull) - A` and the polygon stage 5 handed on `G`:

  kept      area(G & B) / area(B)  -- the share of the band that survived
  to_ground area(B - G) that lies on an EARLIER layer's artwork, / area(B)
            -- what the earlier-colour clip took (the rest of any loss is the
            same-thread corridor or a held hole, which are not this defect)
  width     2 * area / perimeter of `A` and of `G`: a stroke-width proxy that
            reads true on a thin bar and is quoted only beside the row that
            names the shape

`--flag NAME=VALUE` digitizes under a `PipelineConfig` keyword (repeatable), so
`--flag satin_rail_comp=True` shows the satin shapes keeping their artwork (on
rails the pull is not in the polygon at all -- read `kept` there as n/a).

Usage (cwd digitizer/):
  python tools/ground_clip.py [cases ...] [--flag K=V ...] [--top N] [--json PATH]
cases: the keys of `tools/decomposition_census.CASES` (default: fremont).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))


def band_stats(art, grown, pull: float, earlier_art) -> dict:
    """-> {kept, to_ground, art_w, grown_w} for one shape. Pure geometry.

    `earlier_art` is the union of every earlier layer's artwork, or None when
    nothing sews before this shape. A zero pull reads kept = 1.0 and
    to_ground = 0.0: there is no band to lose.
    """
    band = art.buffer(pull).difference(art) if pull > 0 else None
    if band is None or band.area <= 0:
        kept, to_ground = 1.0, 0.0
    else:
        kept = grown.intersection(band).area / band.area
        lost = band.difference(grown)
        to_ground = (lost.intersection(earlier_art).area / band.area
                     if earlier_art is not None and not lost.is_empty else 0.0)

    def width(p):
        return 2.0 * p.area / p.length if p.length > 0 else 0.0

    return {"kept": kept, "to_ground": to_ground,
            "art_w": width(art), "grown_w": width(grown)}


def measure(case: str, flags: dict) -> dict:
    from shapely.ops import unary_union

    import decomposition_census as dc
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core import pipeline

    rel, kw = dc.CASES[case]
    cfg = PipelineConfig(**{**kw, **flags})
    captured: list = []
    real = pipeline.resolve_overlaps

    def spy(regions, fabric, cfg_, *a, **k):
        planned, warnings = real(regions, fabric, cfg_, *a, **k)
        captured.append((planned, fabric))
        return planned, warnings

    pipeline.resolve_overlaps = spy
    try:
        digitize(ROOT / "testdata" / rel, cfg)
    finally:
        pipeline.resolve_overlaps = real
    planned, fabric = captured[-1]
    pull = max(0.0, fabric.pull_comp_mm)
    layers = sorted({p.region.meta["layer"] for p in planned})
    art_by_layer = {L: unary_union([p.region.polygon for p in planned
                                    if p.region.meta["layer"] == L]) for L in layers}
    earlier, running = {}, None
    for L in layers:
        earlier[L] = running
        running = art_by_layer[L] if running is None else running.union(art_by_layer[L])
    rows = []
    for p in planned:
        s = band_stats(p.region.polygon, p.polygon, pull, earlier[p.region.meta["layer"]])
        b = p.region.polygon.bounds
        rows.append({"shape_id": p.region.shape_id, "layer": p.region.meta["layer"],
                     "bbox_mm": [round(v, 1) for v in b],
                     **{k: round(v, 3) for k, v in s.items()}})
    return {"case": case, "flags": flags, "pull_mm": pull, "fabric": fabric.id,
            "shapes": len(rows), "rows": rows}


def summarize(res: dict, top: int) -> str:
    rows = res["rows"]
    clipped = [r for r in rows if r["to_ground"] >= 0.5]
    out = [f"{res['case']}  {res['flags'] or 'shipped'}  fabric {res['fabric']} "
           f"pull {res['pull_mm']} mm: {len(rows)} shapes, "
           f"{len(clipped)} lost at least half their pull band to an earlier colour"]
    for r in sorted(rows, key=lambda r: -r["to_ground"])[:top]:
        out.append(f"  {r['shape_id']:<11} layer {r['layer']:>2}  kept {r['kept']:.2f}  "
                   f"to_ground {r['to_ground']:.2f}  width art {r['art_w']:.2f} -> "
                   f"planned {r['grown_w']:.2f} mm  bbox {r['bbox_mm']}")
    return "\n".join(out)


def _flag(text: str) -> tuple[str, object]:
    key, _, raw = text.partition("=")
    try:
        return key, json.loads(raw.lower() if raw.lower() in ("true", "false") else raw)
    except json.JSONDecodeError:
        return key, raw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*", default=["fremont"])
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    flags = dict(_flag(f) for f in args.flag)
    results = []
    for case in args.cases:
        res = measure(case, flags)
        results.append(res)
        print(summarize(res, args.top), flush=True)
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
