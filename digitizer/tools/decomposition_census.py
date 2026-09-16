#!/usr/bin/env python
"""Is the raster skeleton what costs us strokes, trims and bare junctions?

The instrument for quality-review item 5 (`docs/quality-review-2026-09-08.md`),
written BEFORE any decomposition engine change, because that item's premise
is a hypothesis: the review blames the raster medial axis for Becker's trims,
the bare crotches and the N's welded diagonal, while DOCTRINE records the
trim cause as travel TIMING ("WHERE to change that ... is not established")
and letter fidelity as living "in the rails, not the skeleton". Plan:
`docs/superpowers/plans/2026-09-15-decomposition-census.md`.

So this does not build a new skeleton into the engine. It swaps the skeleton
SOURCE inside `stage6_satin.extract_strokes` for one digitize at a time and
measures what moves, with everything downstream of the skeleton (pinhole
collapse, junction clustering, the merge, corner splits, rails, travel)
left exactly as shipped:

  shipped   the engine as it is
  raster12  the medial-axis raster at 12 px/mm instead of 6 (cap x2)
  raster24  24 px/mm (cap x4) -- if pixels are the cause, this moves most
  noprune   `_prune_spurs` disabled (the N-weld ablation, re-run on HEAD)
  polyaxis  `cfg.satin_polygon_axis` (shipped 2026-09-16, default off):
            the axis read from the polygon by `digitizer_core/polygon_axis.py`
            and drawn onto the same grid, `_prune_spurs` skipped. The census
            sets the FLAG rather than patching a copy of the construction.

**One confound, reported rather than hidden.** `_stroke_rows` (the per-stroke
classifier rung) calls `extract_strokes` too, so an arm can change which
shapes sew satin as well as how they decompose. Every row carries
`tier_moves` -- shapes whose sewn tier differs from `shipped` -- and a
symptom that moves only on a design whose tiers moved is a routing effect,
not a decomposition one.

Metrics, per (design, arm):
  stitches, trims, in_shape (trims inside one shape, `tools/trim_locality`)
  satin_shapes, strokes      shapes through `satin_shape`, strokes they made
  folds90, folds60           column members whose spine turns more than
                             90 / 60 deg within one half-width window --
                             the N weld is a 108 deg fold inside ONE column
  bare_mm2                   uncovered artwork inside satin shapes, read the
                             way `tools/letterforms.py` reads it
  share, col_p50, col_p90    `tools/satin_columns.py` on the whole plan
  cov_max, cov_p95           preflight coverage units -- the density price
                             (`drone_render`'s M gains crossing columns under
                             `polyaxis`; the render is in the flag's PR)
  grade                      preflight's letter, same run
  tier_moves                 see above

Becker at 95.7 mm also prints the professional's committed file
(`testdata/reference/becker_hat_polo_large_beckers_logolc.dst`, 95.7 x 58.3
mm, the same artwork) through the same column instrument, with its trims.

Usage (cwd digitizer/):
  python tools/decomposition_census.py [--arms A ...] [--cases C ...]
                                       [--workers N] [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

CASES = {
    "becker80": ("becker_marine_logo.png", dict(target_width_mm=80.0)),
    "becker95": ("becker_marine_logo.png", dict(target_width_mm=95.7, garment_id="left_chest")),
    "enthusiast": ("photo/enthusiast_logo.png", dict(target_width_mm=93.0, garment_id="left_chest")),
    "fremont": ("photo/logo_hotel_fremont.webp", dict(target_width_mm=92.5)),
    "drone": ("photo/drone_render.png", dict(target_width_mm=80.0)),
}
ARMS = ("shipped", "raster12", "raster24", "noprune", "polyaxis")
PRO = {"becker95": "reference/becker_hat_polo_large_beckers_logolc.dst"}

# A polygon-axis edge survives when its generators are more than twice this
# many LOCAL radii apart along the boundary. 1.6 is the shipped `_prune_spurs`
# multiplier (in half-widths); a convex corner's twig reads ~2 radii, so it
# goes at any multiplier over 1. What this arm changes is the reference and
# the construction (local radius, geometry), not the number.
SIGNIFICANCE_RADII = 1.6
# Boundary densification for the Voronoi diagram, as a fraction of a raster
# pixel: fine enough that the diagram's interior edges trace the axis to well
# under the grid the result is drawn on.
DENSIFY_PX = 0.5
FOLD_BIG_DEG = 90.0
FOLD_SMALL_DEG = 60.0


# --- arms --------------------------------------------------------------------

def apply_arm(arm: str) -> dict:
    """Patch `stage6_satin` for one arm, in this process only.

    -> extra `PipelineConfig` keywords the arm needs. `polyaxis` is no longer
    patched at all: it SHIPPED as `cfg.satin_polygon_axis` (2026-09-16), so
    the census now measures the engine's own flag rather than a copy of it --
    the copy would drift.
    """
    from digitizer_core import stage6_satin as s6

    if arm == "shipped":
        return {}
    if arm == "polyaxis":
        return {"satin_polygon_axis": True}
    if arm in ("raster12", "raster24"):
        f = 2.0 if arm == "raster12" else 4.0
        s6._RASTER_PX_PER_MM = 6.0 * f
        s6._RASTER_MAX_PX = int(900 * f)
        return {}
    if arm == "noprune":
        s6._prune_spurs = lambda mask, spur_len_px: None
        return {}
    raise SystemExit(f"unknown arm {arm!r}")


# --- measurement --------------------------------------------------------------

def max_turn_deg(spine, step: float) -> float:
    """Largest direction change along `spine` between chords `step` long."""
    if len(spine) < 3 or step <= 0:
        return 0.0
    from shapely.geometry import LineString
    line = LineString(spine)
    n = int(line.length // step)
    if n < 2:
        return 0.0
    pts = [line.interpolate(i * step).coords[0] for i in range(n + 1)]
    worst = 0.0
    for p, q, r in zip(pts, pts[1:], pts[2:]):
        a = math.atan2(q[1] - p[1], q[0] - p[0])
        b = math.atan2(r[1] - q[1], r[0] - q[0])
        d = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
        worst = max(worst, math.degrees(d))
    return worst


def measure(case: str, arm: str) -> dict:
    extra = apply_arm(arm)
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core import stage6_satin as s6
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.preflight import run_preflight
    from curve_tiers import shapes as sewn_tiers
    from letterforms import members
    from satin_columns import measure as columns, passes_from_plan
    from trim_locality import split

    rel, kw = CASES[case]
    kw = {**kw, **extra}
    seen: list[tuple[str, object]] = []
    strokes_of: dict[str, list] = {}
    current = [None]
    real_shape, real_extract = s6.satin_shape, s6.extract_strokes

    def spy_shape(poly, shape_id, **kwargs):
        seen.append((shape_id, poly))
        current[0] = shape_id
        try:
            return real_shape(poly, shape_id, **kwargs)
        finally:
            current[0] = None

    def spy_extract(poly, **kwargs):
        out = real_extract(poly, **kwargs)
        if current[0] is not None:
            strokes_of[current[0]] = (out[0], out[1])
        return out

    s7.satin_shape, s6.extract_strokes = spy_shape, spy_extract
    try:
        result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**kw))
    finally:
        s7.satin_shape, s6.extract_strokes = real_shape, real_extract

    runs_by: dict[str, list] = {}
    for _b, r in plan.iter_runs():
        runs_by.setdefault(r.shape_id, []).append(r)
    n_strokes = folds90 = folds60 = 0
    bare = 0.0
    fold_rows = []
    for shape_id, poly in seen:
        st, half = strokes_of.get(shape_id, ([], 0.0))
        n_strokes += len(st)
        for s in st:
            for m in members(s):
                t = max_turn_deg(m.spine, max(half, 0.2))
                folds90 += t > FOLD_BIG_DEG
                folds60 += t > FOLD_SMALL_DEG
                if t > FOLD_SMALL_DEG:
                    fold_rows.append({"shape_id": shape_id, "turn_deg": round(t, 1),
                                      "at": [round(v, 1) for v in m.spine[len(m.spine) // 2]]})
        bare += sum(g.buffer(-s6._JUNCTION_PATCH_GROW_MM).area
                    for g in s6._uncovered_patches(poly, runs_by.get(shape_id, [])))
    col = columns(passes_from_plan(plan))
    tl = split(plan)
    # legibility OFF: it costs ~3.5 s per text cluster and reads the RENDER,
    # not the skeleton, so it cannot answer anything this census asks.
    rep = run_preflight(result, plan, PipelineConfig(**{**kw, "legibility_check": False}),
                        image=ROOT / "testdata" / rel)
    m = rep["metrics"]
    tiers = {sid: v[0] for sid, v in sewn_tiers(result, plan).items()}
    return {"case": case, "arm": arm, "stitches": plan.stats.stitch_count,
            "grade": rep["grade"], "cov_max": m.get("coverage_max"),
            "cov_p95": m.get("coverage_p95"),
            "findings": sorted(f"{f['code']}:{f['severity']}" for f in rep["findings"]),
            "trims": tl["trims"], "in_shape": tl["in_shape"],
            "satin_shapes": len(seen), "strokes": n_strokes,
            "folds90": int(folds90), "folds60": int(folds60),
            "bare_mm2": round(bare, 1), "share": round(col["share"], 3),
            "col_p50": None if col["median_mm"] is None else round(col["median_mm"], 2),
            "col_p90": None if col["p90_mm"] is None else round(col["p90_mm"], 2),
            "tiers": tiers, "folds": sorted(fold_rows, key=lambda r: -r["turn_deg"])[:8]}


def pro_row(case: str) -> dict | None:
    rel = PRO.get(case)
    if rel is None:
        return None
    import pystitch
    from satin_columns import measure as columns, passes_from_file

    path = ROOT / "testdata" / rel
    pat = pystitch.read(str(path))
    trims = sum(1 for _x, _y, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.TRIM)
    stitches = sum(1 for _x, _y, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.STITCH)
    col = columns(passes_from_file(path))
    return {"case": case, "arm": "PRO", "stitches": stitches, "trims": trims,
            "share": round(col["share"], 3), "col_p50": round(col["median_mm"], 2),
            "col_p90": round(col["p90_mm"], 2)}


def _job(args):
    """One failing (case, arm) must not discard every other row."""
    try:
        return measure(*args)
    except Exception as exc:  # noqa: BLE001
        import traceback
        return {"case": args[0], "arm": args[1], "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arms", nargs="*", default=list(ARMS))
    ap.add_argument("--cases", nargs="*", default=list(CASES))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    jobs = [(c, arm) for c in a.cases for arm in a.arms]
    # One process per job: an arm patches `stage6_satin` module globals, and
    # a reused worker would carry one arm's patch into the next arm's run.
    with ProcessPoolExecutor(max_workers=a.workers, max_tasks_per_child=1) as ex:
        rows = list(ex.map(_job, jobs))
    base = {r["case"]: r["tiers"] for r in rows
            if r["arm"] == "shipped" and "error" not in r}
    hdr = ("case", "arm", "stitches", "trims", "in_shape", "satin", "strokes",
           "folds90", "folds60", "bare_mm2", "share", "cov_max", "grade", "tier_moves")
    print(("{:<11}{:<10}" + "{:>10}" * 12).format(*hdr))
    report = []
    for case in a.cases:
        for r in [x for x in rows if x["case"] == case]:
            if "error" in r:
                report.append(r)
                print(f"{case:<11}{r['arm']:<10}ERROR {r['error']}")
                continue
            b = base.get(case)
            r["tier_moves"] = (None if b is None else
                               sum(1 for sid, t in r["tiers"].items() if b.get(sid) != t))
            report.append(r)
            print(("{:<11}{:<10}" + "{:>10}" * 12).format(
                case, r["arm"], r["stitches"], r["trims"], r["in_shape"], r["satin_shapes"],
                r["strokes"], r["folds90"], r["folds60"], r["bare_mm2"], r["share"],
                str(r["cov_max"]), str(r["grade"]), str(r["tier_moves"])))
        p = pro_row(case)
        if p:
            report.append(p)
            print(("{:<11}{:<10}" + "{:>10}" * 12).format(
                case, "PRO", p["stitches"], p["trims"], "-", "-", "-", "-", "-", "-",
                p["share"], "-", "-", "-"))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
