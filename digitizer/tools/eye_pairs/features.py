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
from tools.artfidelity_self import (INK_SATURATION_MAX, MISMATCH_MAX, WEIGHTS,
                                    art_ink_field, colour_score, ink_is_ambiguous,
                                    ink_saturation, ms_ssim, register,
                                    stitch_coverage_field)
from tools.thin_strokes import STUDIO_MAX_COLORS

# Metrics whose input is the artwork's ink mask: one refusal covers them all.
INK_METRICS = ("artfid", "artfid_no_colour", "artfid_coverage", "artfid_structure",
               "artfid_colour", "lost_elements", "lost_frac", "ragged_mm", "hausdorff_mm")
# What can be read from a Design dict alone — all the 08-27 arm ever gets.
DESIGN_ONLY_METRICS = ("stitches", "stops", "cones", "trims_per_1000",
                       "artfid_no_colour", "artfid_coverage", "artfid_structure",
                       "lost_elements", "lost_frac", "ragged_mm", "hausdorff_mm")


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


def _ink_refusal(image: Path, ours, art) -> str | None:
    """`artfidelity_self.score_image`'s refusal ladder, on fields already built."""
    ink_px = float((art >= 0.5).sum())
    sewn_px = float((ours >= 0.5).sum())
    if ink_px == 0 or sewn_px == 0:
        return "nothing to compare"
    mismatch = max(ink_px, sewn_px) / min(ink_px, sewn_px)
    if mismatch > MISMATCH_MAX:
        return f"subject mismatch, {mismatch:.1f}x"
    saturation = ink_saturation(image)
    if saturation > INK_SATURATION_MAX:
        return f"ink mask saturates the frame, {saturation:.0%}"
    if ink_is_ambiguous(image):
        return "ink ambiguous (knocked-out lettering)"
    return None


def features_design_only(image: str | Path, design: dict) -> dict:
    image = Path(image)
    row: dict = _records(design)

    ours = stitch_coverage_field(design)
    art = art_ink_field(image, float(design["widthMM"]))
    coverage, O_f, A_f, _dx, _dy = register(ours, art)
    structure = ms_ssim(O_f, A_f)
    row["artfid_coverage"] = _num(coverage)
    row["artfid_structure"] = _num(structure)
    row["artfid_no_colour"] = _num(
        100.0 * (WEIGHTS[0] * row["artfid_coverage"] + WEIGHTS[2] * row["artfid_structure"])
        / (WEIGHTS[0] + WEIGHTS[2]), 2)

    lost = dropped_elements.analyse_design(image, design)
    row["lost_elements"] = int(lost["lost"])
    row["lost_frac"] = _num(lost["lost_frac"])
    edge = edge_smoothness.analyse_design(image, design)
    row["ragged_mm"] = _num(edge["ragged_mm"])
    row["hausdorff_mm"] = _num(edge["hausdorff_mm"])

    reason = _ink_refusal(image, ours, art)
    row["refusals"] = ({m: reason for m in INK_METRICS if m in row} if reason else {})
    row["notes"] = {}
    return row


def features_full(image: str | Path, cfg: PipelineConfig, gen, result, plan,
                  design: dict) -> dict:
    image = Path(image)
    row = features_design_only(image, design)
    ink_reason = next(iter(row["refusals"].values()), None)

    colour, _excess = colour_score(image, result, plan, cfg)
    row["artfid_colour"] = _num(colour)
    row["artfid"] = _num(100.0 * (WEIGHTS[0] * row["artfid_coverage"]
                                  + WEIGHTS[1] * row["artfid_colour"]
                                  + WEIGHTS[2] * row["artfid_structure"]), 2)
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
