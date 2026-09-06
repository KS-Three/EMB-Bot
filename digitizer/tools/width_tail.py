#!/usr/bin/env python
"""The width tail `classify_ribbon`'s p90 gate cannot see — against the bare
cloth it actually leaves.

`classify_ribbon` admits a shape when the DOUBLED p90 medial radius is under
`machine.SATIN_MAX_WIDTH_MM`, and `promoted_ribbon`'s own guard is the same
statistic. A p90 is blind to a tail that is a few percent of the spine, and
`_rail_points`' per-station guard holds every cross to the cap — so a shape
can pass comfortably and still get no thread down the middle of a bulge.

Measured on `becker_marine_logo.png` 2026-09-06, which is why this exists:

  Sead76620 @ 80 mm  promoted_ribbon  p90 2.67 mm  MAX 7.80 mm  2.8% over cap
                     -> 23.8 mm2 bare, 100% of that design's ARTWORK_UNCOVERED

**Proven on the emitted stitches, not on the plan.** The `bare` column is the
mm2 preflight attributes to that shape in its `ARTWORK_UNCOVERED` finding, so
a tail statistic only earns attention where thread is actually missing. This
is the repo's cardinal rule and the reason `tools/seam_underlap.py` hid a
month-long defect: it read stage 5's plan.

  .venv/bin/python tools/width_tail.py becker_marine_logo.png --width 80
  .venv/bin/python tools/width_tail.py --corpus          # every fixture, 80 mm
  .venv/bin/python tools/width_tail.py --corpus --csv out.csv

What a threshold proposal needs from this, per DOCTRINE: shipped verdicts
CHANGED and flips LEFT, across the real fixtures, before any number moves.
`--gate MAX:5.0` scores one candidate rule without touching the classifier —
it reports which satin shapes it would demote and how much of the corpus's
bare cloth those shapes carry.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitches   # noqa: E402
from digitizer_core import stage6_satin as s6                  # noqa: E402
from digitizer_core.pipeline import digitize                   # noqa: E402
from digitizer_core.preflight import run_preflight             # noqa: E402


def _spine_widths_mm(poly) -> np.ndarray:
    """Every medial width along the shape's spine, in mm.

    The same construction `_dt_stats` pools into one p90 — but kept as the
    whole distribution, because the point of this tool is the part a
    percentile discards. Sampled at the spine's rasterized pixels, so a long
    stroke contributes more samples than a short one: an over-cap FRACTION
    here is a fraction of spine LENGTH, which is what bare cloth scales with.

    Sampling audited 2026-09-06 rather than assumed, since this tool exists
    because another one flattered. Against the physically correct weighting —
    each sample carrying half the distance to each neighbour — the plain
    per-sample fraction lands within 0.05 pp: `Sead76620` @ 80 mm reads
    2.804% by sample, 2.759% by arc length, 2.416% de-duplicated by pixel;
    `S714b55d9` 0.621 / 0.682 / 0.847%. MAX is identical under all three. The
    weighting choice cannot move a threshold that separates those two shapes
    by 4x, so the simple form stays.
    """
    strokes, _half, field = s6.extract_strokes(poly)
    if field is None or not strokes:
        return np.zeros(0)
    h, w = field.dist.shape
    out: list[float] = []
    for s in strokes:
        pts = np.asarray([((p[0] - field.ox) * field.scale,
                           (p[1] - field.oy) * field.scale) for p in s.spine])
        for x, y in np.round(pts).astype(int):
            if 0 <= y < h and 0 <= x < w:
                out.append(2.0 * float(field.dist[y, x]) / field.scale)
    return np.asarray(out)


def rows(art: Path, width_mm: float, garment: str) -> list[dict]:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result, plan = digitize(art, cfg)
    report = run_preflight(result, plan, cfg, image=art)
    cap = cfg.satin_max_width_mm or machine.SATIN_MAX_WIDTH_MM

    # Bare cloth per shape, straight off the finding preflight already
    # attributes — the ground truth column. A shape absent from it has none.
    bare: dict[str, float] = {}
    for f in report["findings"]:
        if f["code"] == "ARTWORK_UNCOVERED":
            for s in f["extra"]["shapes"]:
                bare[s["shape_id"]] = float(s["missing_mm2"])

    satin_ids = {r.shape_id for _b, r in plan.iter_runs()
                 if r.kind == stitches.SATIN and r.shape_id}

    out: list[dict] = []
    for r in result.regions:
        if r.shape_id not in satin_ids:
            continue
        v = s6.classify_ribbon(r.polygon, cap, design_class=result.design_class,
                               full_metrics=True)
        a = _spine_widths_mm(r.polygon)
        if not len(a):
            continue
        out.append({
            "fixture": art.name, "width_mm": width_mm, "garment": garment,
            "shape_id": r.shape_id, "reason": v.reason,
            "area_mm2": round(float(r.polygon.area), 1),
            "gate_p90_mm": round(float(v.metrics.get("dt_p90_mm") or 0.0), 2),
            "spine_p50_mm": round(float(np.percentile(a, 50)), 2),
            "spine_p99_mm": round(float(np.percentile(a, 99)), 2),
            "spine_max_mm": round(float(a.max()), 2),
            "over_cap_frac": round(float((a > cap).mean()), 4),
            "bare_mm2": round(bare.get(r.shape_id, 0.0), 1),
            "grade": f"{report['grade']} {report['score']}",
        })
    return out


def _print(rs: list[dict], gate: tuple[str, float] | None) -> None:
    print(f"{'fixture':26} {'shape':11} {'reason':17} {'area':>7} "
          f"{'gate p90':>8} {'p99':>6} {'MAX':>6} {'>cap':>6} {'BARE':>7}")
    for r in sorted(rs, key=lambda x: -x["bare_mm2"]):
        mark = ""
        if gate is not None:
            stat, thr = gate
            val = r["spine_max_mm"] if stat == "MAX" else (
                r["spine_p99_mm"] if stat == "P99" else r["over_cap_frac"])
            mark = "  <= DEMOTED" if val > thr else ""
        print(f"{r['fixture'][:26]:26} {r['shape_id']:11} {r['reason']:17} "
              f"{r['area_mm2']:7.1f} {r['gate_p90_mm']:8.2f} "
              f"{r['spine_p99_mm']:6.2f} {r['spine_max_mm']:6.2f} "
              f"{r['over_cap_frac']:6.1%} {r['bare_mm2']:7.1f}{mark}")

    tot_bare = sum(r["bare_mm2"] for r in rs)
    print(f"\n{len(rs)} satin shapes, {tot_bare:.1f} mm2 bare in total")
    if gate is None:
        return
    stat, thr = gate
    def val(r):
        return (r["spine_max_mm"] if stat == "MAX"
                else r["spine_p99_mm"] if stat == "P99" else r["over_cap_frac"])
    hit = [r for r in rs if val(r) > thr]
    caught = sum(r["bare_mm2"] for r in hit)
    clean = [r for r in hit if r["bare_mm2"] == 0.0]
    # The two numbers DOCTRINE asks for: verdicts CHANGED, and what is LEFT.
    print(f"gate {stat} > {thr}: demotes {len(hit)} of {len(rs)} satin shapes "
          f"({sum(r['area_mm2'] for r in hit):.1f} mm2 of shape area)")
    print(f"  catches {caught:.1f} of {tot_bare:.1f} mm2 bare "
          f"({(caught / tot_bare if tot_bare else 0):.0%}); "
          f"leaves {tot_bare - caught:.1f} mm2")
    print(f"  demotes {len(clean)} shapes with NO bare cloth "
          f"({sum(r['area_mm2'] for r in clean):.1f} mm2) — the cost side")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", nargs="?", help="path under testdata/, or full")
    ap.add_argument("--corpus", action="store_true",
                    help="every fixture in tools/corpus_scorecard.py's list")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--gate", default=None,
                    help="score a candidate rule: MAX:5.0, P99:5.0 or FRAC:0.01")
    ap.add_argument("--csv", type=Path, default=None)
    a = ap.parse_args()
    if not a.fixture and not a.corpus:
        ap.error("give a fixture or --corpus")

    gate = None
    if a.gate:
        stat, _, thr = a.gate.partition(":")
        if stat.upper() not in ("MAX", "P99", "FRAC") or not thr:
            ap.error("--gate wants MAX:x, P99:x or FRAC:x")
        gate = (stat.upper(), float(thr))

    arts: list[Path] = []
    if a.corpus:
        from tools.corpus_scorecard import FIXTURES
        arts = [ROOT / "testdata" / f for f in FIXTURES]
    else:
        p = Path(a.fixture)
        arts = [p if p.is_absolute() else ROOT / "testdata" / a.fixture]

    rs: list[dict] = []
    for art in arts:
        if not art.exists():
            print(f"  (missing: {art.name})", file=sys.stderr)
            continue
        try:
            rs.extend(rows(art, a.width, a.garment))
        except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the sweep
            print(f"  ({art.name}: {type(exc).__name__}: {exc})", file=sys.stderr)
    _print(rs, gate)
    if a.csv and rs:
        with a.csv.open("w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rs[0]))
            wr.writeheader()
            wr.writerows(rs)
        print(f"\nwrote {a.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
