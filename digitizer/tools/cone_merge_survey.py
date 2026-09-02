"""Where could a design sew one shade where it has two? Across the whole corpus.

## Why this exists

MASTER_SCOPE's open question 12 — "merge a tiny cone into an ADJACENT SHADE" —
is Kent's call, and its own entry says why: "how much colour step buys a stop
is cloth, not a constant." `tools/sequence_census.py` already ranks the
candidates for ONE design and likewise refuses to pick a threshold.

What neither answers is the question that decides whether the feature is worth
building at all: **across the corpus, how many merges would a given threshold
actually buy, and where do they sit?** This is that survey. It changes nothing
and recommends nothing; it counts.

## The distinction that turned out to matter

A near-identical pair is only worth what it costs to fold, and the cost splits
sharply:

  * WITHIN one layer — two cones already sewn at the same point in the order.
    Folding removes a block and touches nothing else: no reorder, no change to
    what stage 5 planned coverage against.
  * ACROSS layers — the cones sew at different points in the sew order.
    Folding means moving regions BETWEEN layers, which is a real geometry
    change: stage 5 built `covered_by` from the un-merged order, so the seam
    between those two layers stops existing.

Measured 2026-09-02 the candidates are almost entirely the second, expensive
kind — which is the finding, and the reason this survey exists rather than a
merge pass. See the header comment on `--help` output for the table.

## The trap this file exists to document

A first implementation folded LAYER PALETTE slots and fired on nothing, because
the palette and the cones regions actually carry are DIFFERENT SETS once stage
4's re-snap has run: on `drone_render` @ 80 mm the layer palette holds 16 cones
while the regions carry 19, five of which are in no layer slot at all, and one
layer carries three different cones. Blocks key on the REGION's `thread_index`
(`stage6_applique.nn_group_key`), not the layer's declared cone.

Worse, folding a layer and rewriting every region on it to the survivor's cone
DISCARDS the re-snap: those regions were moved to a better-matching thread on
purpose (`stage4_vectorize.revalidate_threads`, gated at 3.0 dE improvement),
and a layer-level rewrite spends colour the threshold never authorised. Any
future merge pass has to work on region cones and leave re-snapped regions
alone.

Usage (from digitizer/):
    .venv/bin/python tools/cone_merge_survey.py
    .venv/bin/python tools/cone_merge_survey.py --thresholds 1.5 2 3 5 --json out.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

DEFAULT_THRESHOLDS = (1.5, 2.0, 3.0, 5.0)


def survey_one(art: Path, chart, width_mm: float, garment: str) -> dict | None:
    """Cone pairs for one artwork, split by whether they share a layer.

    Reads the regions as the pipeline finishes them, so the cones counted are
    the ones BLOCKS are keyed on -- not the layer palette, which is a
    different set once the re-snap has run (see the module docstring).
    """
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import digitize

    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result, plan = digitize(art, cfg)

    by_layer: dict[int, set[int]] = {}
    for r in result.regions:
        by_layer.setdefault(r.meta["layer"], set()).add(r.thread_index)
    cones = sorted({c for s in by_layer.values() for c in s})

    within, across = [], []
    for a, b in itertools.combinations(cones, 2):
        de = chart.delta_e(a, b)
        shared = any(a in s and b in s for s in by_layer.values())
        (within if shared else across).append({"a": a, "b": b, "delta_e": round(de, 2)})
    return {
        "fixture": str(art.name),
        "cones": len(cones),
        "blocks": len(plan.blocks),
        "layers_with_multiple_cones": sum(1 for s in by_layer.values() if len(s) > 1),
        "within": sorted(within, key=lambda p: p["delta_e"]),
        "across": sorted(across, key=lambda p: p["delta_e"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--thresholds", type=float, nargs="+", default=list(DEFAULT_THRESHOLDS))
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    from corpus_scorecard import FIXTURES, TESTDATA
    from digitizer_core import PipelineConfig
    from digitizer_core.threads import chart_for
    chart = chart_for(PipelineConfig())

    rows = []
    for fx in FIXTURES:
        art = TESTDATA / fx
        if not art.exists():
            continue
        try:
            row = survey_one(art, chart, a.width, a.garment)
        except Exception as exc:                      # noqa: BLE001
            print(f"SKIP {fx}: {type(exc).__name__}: {exc}", flush=True)
            continue
        rows.append(row)
        counts = " ".join(
            f"{t:g}:w{sum(1 for p in row['within'] if p['delta_e'] <= t)}"
            f"/x{sum(1 for p in row['across'] if p['delta_e'] <= t)}"
            for t in a.thresholds)
        print(f"{row['fixture']:<34} cones={row['cones']:>2} blocks={row['blocks']:>2} "
              f"multi-cone layers={row['layers_with_multiple_cones']:>2} | {counts}", flush=True)

    print("\n=== corpus totals (w = shares a layer, x = crosses layers) ===")
    for t in a.thresholds:
        w = sum(sum(1 for p in r["within"] if p["delta_e"] <= t) for r in rows)
        x = sum(sum(1 for p in r["across"] if p["delta_e"] <= t) for r in rows)
        n = sum(1 for r in rows
                if any(p["delta_e"] <= t for p in r["within"] + r["across"]))
        print(f"  dE <= {t:g}: within={w}  across={x}   ({n} of {len(rows)} fixtures)")
    print("\nA `within` pair is a cheap fold; an `across` pair moves regions between\n"
          "layers and changes what stage 5 planned coverage against. This tool does\n"
          "not merge anything and picks no threshold -- gate 1, and open question 12.")
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
