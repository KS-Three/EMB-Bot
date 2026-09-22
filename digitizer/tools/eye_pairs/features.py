"""One digitize per arm; every instrument reads that same plan.

Each of the repo's eye-instruments has an `analyse()` that runs the engine
for itself. Called naively that is one engine run per instrument per arm. The
functions here hold `gen`, `result`, `plan` and `design` from ONE run and feed
the instruments' inner functions — imported, never copied; `--verify` is the
drift control that keeps that honest.

A refusal is a FLAG, not a null: the value is kept and `refusals[metric]`
says why it may be unreliable (spec section 3.7). `None` means the instrument
could not produce a number at all.
"""
from __future__ import annotations

import math
from pathlib import Path

from digitizer_core import legibility as core_legibility
from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import run_preflight

from tools import curve_fidelity, dropped_elements, edge_smoothness, thin_strokes
from tools.artfidelity_self import (WEIGHTS, colour_score, composite, ms_ssim,
                                    refusal_for, register_design)
from tools.thin_strokes import STUDIO_MAX_COLORS

# Bump when a metric is added, removed or redefined. A cached features row
# whose `schema` differs is a cache MISS: without this, a metric added later
# never reached rows rendered earlier, and the analysis (which reads by
# `.get`) quietly scored that metric on fewer pairs (review finding 7,
# 2026-09-17).
#
# 2 (2026-09-20): `unsewn_frac` / `overshoot_frac`, the two halves `lost_frac`
# had been summing. They move in OPPOSITE directions under the same change, so
# an arm comparison on the total cannot say which one a change bought.
FEATURES_SCHEMA = 2

# Metrics whose input is the artwork's ink mask: one refusal covers them all.
INK_METRICS = ("artfid", "artfid_no_colour", "artfid_coverage", "artfid_structure",
               "artfid_colour", "lost_elements", "lost_frac", "unsewn_frac",
               "overshoot_frac", "ragged_mm", "hausdorff_mm")
# What can be read from a Design dict alone — all the 08-27 arm ever gets.
DESIGN_ONLY_METRICS = ("stitches", "stops", "cones", "trims_per_1000",
                       "artfid_no_colour", "artfid_coverage", "artfid_structure",
                       "lost_elements", "lost_frac", "unsewn_frac", "overshoot_frac",
                       "ragged_mm", "hausdorff_mm")


def base_cfg(width_mm: float, garment: str, **kw) -> PipelineConfig:
    """What a customer gets: the fixture's own size and garment, and the
    Studio's six colours rather than the pipeline's twelve."""
    return PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                          max_colors=STUDIO_MAX_COLORS, **kw)


def digitize_once(image: str | Path, cfg: PipelineConfig):
    gen = build_generation(str(image), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return gen, result, plan, plan_to_design(plan)


def _num(v, places: int = 4) -> float | None:
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else round(v, places)


def _records(design: dict) -> dict:
    """ONE definition of these for every arm, the 08-27 engine included."""
    stitches = design.get("stitches") or []
    n = sum(1 for s in stitches if s["type"] == "stitch")
    trims = sum(1 for s in stitches if s["type"] == "trim")
    cones = {(c.get("r"), c.get("g"), c.get("b")) for c in design.get("colors") or []}
    return {"stitches": n,
            "stops": sum(1 for s in stitches if s["type"] == "color"),
            "cones": len(cones),
            "trims_per_1000": round(1000.0 * trims / n, 2) if n else None}


def _design_only(image: Path, design: dict) -> tuple[dict, float, float]:
    """-> (row, coverage, structure) with the two components UNROUNDED, so
    `features_full` can compose `artfid` the way the instrument does — from
    raw values, rounded once to 1 dp. The stored components are rounded for
    the JSON file only."""
    row: dict = _records(design)

    # ONE registration per design, shared with both split instruments.
    reg = register_design(image, design)
    coverage = float(reg.coverage)
    structure = float(ms_ssim(reg.O_f, reg.A_f))
    row["artfid_coverage"] = _num(coverage)
    row["artfid_structure"] = _num(structure)
    row["artfid_no_colour"] = _num(
        100.0 * (WEIGHTS[0] * coverage + WEIGHTS[2] * structure)
        / (WEIGHTS[0] + WEIGHTS[2]), 1)

    lost = dropped_elements.analyse_design(image, design, registered=reg)
    row["lost_elements"] = int(lost["lost"])
    row["lost_frac"] = _num(lost["lost_frac"])
    # The two halves of the total, carried separately because they answer
    # different questions and can move opposite ways: `unsewn_frac` is artwork
    # the stitch-out never covered, `overshoot_frac` is thread standing on
    # cloth the artwork leaves bare. See `dropped_elements.analyse_design`.
    #
    # DELIBERATELY NOT in `analysis.METRICS` or `eye_pairs_gallery.METRIC_BETTER`
    # (2026-09-20). Those two are the YARDSTICK's table -- spec sections 3.2 and
    # 3.7, restated and pinned by `tests/test_eye_pairs_gallery.py::
    # test_metric_table_pins_the_yardstick_spec` -- and every metric in them is
    # a chip in Kent's labelling UI and a candidate for the phase-1 agreement
    # statistic. Adding to it mid-campaign changes what he is shown and what
    # gets scored, which is his call and the spec's, not a side effect of
    # splitting an instrument. Rows carry the two regardless, so anything
    # reading features by name (this module's own guard test) gets them.
    row["unsewn_frac"] = _num(lost["unsewn_frac"])
    row["overshoot_frac"] = _num(lost["overshoot_frac"])
    # Colour-free coverage, immune to every filter the two above ride on.
    # `uncovered_elements` is a COUNT, so it is not an INK_METRIC candidate
    # for the agreement statistic; it is a tripwire, read as 0-or-not.
    row["uncovered_ink_frac"] = _num(lost["uncovered_ink_frac"])
    row["uncovered_elements"] = int(lost["uncovered_elements"])
    edge = edge_smoothness.analyse_design(image, design, registered=reg)
    row["ragged_mm"] = _num(edge["ragged_mm"])
    row["hausdorff_mm"] = _num(edge["hausdorff_mm"])

    reason, _mismatch, _saturation = refusal_for(image, reg.ours, reg.art)
    row["refusals"] = ({m: reason for m in INK_METRICS if m in row} if reason else {})
    row["notes"] = {}
    return row, coverage, structure


def features_design_only(image: str | Path, design: dict) -> dict:
    return _design_only(Path(image), design)[0]


def features_full(image: str | Path, cfg: PipelineConfig, gen, result, plan,
                  design: dict) -> dict:
    image = Path(image)
    row, coverage, structure = _design_only(image, design)
    ink_reason = next(iter(row["refusals"].values()), None)

    colour, _excess = colour_score(image, result, plan, cfg)
    row["artfid_colour"] = _num(colour)
    row["artfid"] = _num(composite(coverage, float(colour), structure), 1)
    if ink_reason:
        row["refusals"]["artfid"] = row["refusals"]["artfid_colour"] = ink_reason

    report = run_preflight(result, plan, cfg, image=str(image))
    metrics = report["metrics"]
    row["preflight_raw_score"] = _num(metrics.get("raw_score"), 1)
    row["preflight_blocks"] = sum(1 for f in report["findings"]
                                  if f.get("severity") == "block")
    row["uncovered_total_mm2"] = _num(metrics.get("uncovered_total_mm2"), 1)
    row["thread_worst_delta_e"] = _num(metrics.get("thread_worst_delta_e"), 2)

    curve = curve_fidelity.measure([p for _k, _s, p in curve_fidelity.traces(plan)])
    row["roughness_deg"] = _num(curve.get("roughness_deg"))
    if curve.get("refusal"):
        row["notes"]["roughness_deg"] = curve["refusal"]

    row["thin_recall"] = _num(thin_strokes.measure(gen.p, cfg, plan).get("recall"))

    try:
        row["legibility"] = _num(core_legibility.measure(gen.p, result, plan).get("legibility"))
    except Exception as exc:  # noqa: BLE001 - no tesseract on Kent's box is the
        # expected case (TesseractNotFoundError), and one missing instrument
        # must not cost the other sixteen metrics.
        row["legibility"] = None
        row["notes"]["legibility"] = f"{type(exc).__name__}: {exc}"
    return row
