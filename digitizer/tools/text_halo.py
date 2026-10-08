"""How much of a design's TEXT is sewn in a thread that is not the text's?

Failure C of `docs/lettering-architecture-rd-2026-10-07.md` ("halo
strands"): anti-alias colours quantised into their own thin regions and sewn
on top of one-colour lettering, billed at "23-30% of the stitches in
Gaulke's text are not black" by the outline-cut write-up -- measured on an
engine 135 commits behind its own date (that doc's caveat). This re-measures
it on whatever engine runs it.

The text area is the union of the letters' polygons grown by 0.3 mm. The
letters are the hand-labelled ones (`testdata/lettering_truth.json`) for a
corpus fixture, or L1's words (`words.detect_words`) for any other image.
Every needle point inside that area is counted by the run's shape:

  letter   a labelled letter (or word member)
  ground   a region bigger than half the text's hull -- the card or band the
           letters sit on, whose fill runs under and between them
  other    everything else: halo strands, and counters sewn as their own
           shapes in the ground's colour (read the per-shape list to tell
           them apart -- a counter is fat, a strand is a sliver)
  no shape a run that belongs to no region (`__edge_cap__`, the design's
           outline cap)

    .venv/bin/python -m tools.text_halo                       # labelled corpus
    .venv/bin/python -m tools.text_halo testdata/art/logo_golke_roofing.png:80
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GROW_MM = 0.3


def measure(path: str, width_mm: float, garment: str, letters: set[str] | None) -> dict:
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep

    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.threads import chart_for
    from digitizer_core.words import detect_words
    from tools.thin_strokes import STUDIO_MAX_COLORS

    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS)
    gen = build_generation(path, cfg)
    if letters is not None and letters - {r.shape_id for r in gen.regions}:
        return {"stale": True}
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    regs = {r.shape_id: r for r in result.regions}
    if letters is None:
        letters = {r.shape_id for w in detect_words(result.regions, chart=chart_for(cfg))
                   for r in w.members}
    letters = {s for s in letters if s in regs}
    if not letters:
        return {"letters": 0}
    area = unary_union([regs[s].polygon for s in letters]).buffer(GROW_MM)
    inside = prep(area)
    hull = area.convex_hull.area
    ground = {s for s, r in regs.items() if s not in letters and r.polygon.area > 0.5 * hull}
    count: collections.Counter = collections.Counter()
    shapes: collections.Counter = collections.Counter()
    for block in plan.blocks:
        for run in block.runs:
            n = sum(1 for p in run.points if inside.contains(Point(p)))
            if not n:
                continue
            kind = ("letter" if run.shape_id in letters else
                    "ground" if run.shape_id in ground else
                    "other" if run.shape_id in regs else "no shape")
            count[kind] += n
            if kind == "other":
                shapes[run.shape_id] += n
    total = sum(count.values())
    rows = []
    for sid, n in shapes.most_common():
        r = regs[sid]
        rows.append({"shape_id": sid, "stitches": n, "thread": r.thread_index,
                     "area_mm2": round(r.polygon.area, 2),
                     "width_mm": round(2 * r.polygon.area / max(r.polygon.length, 1e-9), 2)})
    return {"letters": len(letters), "stitches": dict(count),
            "other_share": count["other"] / total if total else 0.0, "other_shapes": rows}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    from tools.thin_strokes import corpus_cases
    cases = []
    if args:
        for a in args:
            p, _, w = a.rpartition(":")
            cases.append((Path(p).stem, p, float(w), "left_chest", None))
    else:
        truth = json.loads((ROOT / "testdata" / "lettering_truth.json").read_text())["fixtures"]
        for name, path, w, g in corpus_cases():
            if name in truth:
                ids = {s for v in truth[name]["lines"].values() for s in v}
                cases.append((name, str(path), w, g, ids))
    for name, path, w, g, ids in cases:
        out = measure(path, w, g, ids)
        if out.get("stale"):
            print(f"{name}: STALE labels, not measured")
            continue
        if not out.get("letters"):
            print(f"{name}: no letters")
            continue
        print(f"{name}: {out['letters']} letters, stitches in the text {out['stitches']}, "
              f"other {100 * out['other_share']:.1f}%")
        for row in out["other_shapes"][:6]:
            print(f"    {row}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    raise SystemExit(main())
