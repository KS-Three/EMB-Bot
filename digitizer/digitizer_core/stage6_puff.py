"""Stage 6 3D puff: config gate and per-shape eligibility.

Spec: docs/superpowers/specs/2026-11-19-3d-puff-design.md. Satin only; tatami
never puffs. Eligibility is against the puff width band (machine.PUFF_*),
never the flat satin ceiling.
"""
from __future__ import annotations

from . import machine
from .stage5_overlap import _inscribed_width
from .stitchwidth import measure_width_mm


def wants_puff(region, cfg) -> bool:
    """Master switch gates everything; then mode and per-shape meta."""
    if not cfg.puff:
        return False
    want = region.meta.get("puff")
    if cfg.puff_mode == "select":
        return want is True
    return want is not False


def puff_eligible(region, cfg) -> tuple[bool, str]:
    """-> (eligible, reason); reason is "" when eligible."""
    w = measure_width_mm(region.polygon)
    if w is None or w < machine.PUFF_MIN_WIDTH_MM:
        shown = "0.0" if w is None else f"{w:.1f}"
        return False, f"too thin for foam ({shown} mm)"
    # Too wide is the widest inscribed circle, not the skeleton mean: the mean
    # under-reads wide bars (a 14 mm bar reads 9.8) and would defeat the ceiling.
    widest = _inscribed_width(region.polygon)
    if widest > machine.PUFF_MAX_WIDTH_MM:
        return False, f"too wide to puff ({widest:.1f} mm)"
    return True, ""
