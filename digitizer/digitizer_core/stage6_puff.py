"""Stage 6 3D puff: config gate and per-shape eligibility.

Spec: docs/superpowers/specs/2026-11-19-3d-puff-design.md. Satin only; tatami
never puffs. Eligibility is against the puff width band (machine.PUFF_*),
never the flat satin ceiling.
"""
from __future__ import annotations

from . import machine
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
    if w > machine.PUFF_MAX_WIDTH_MM:
        return False, f"too wide to puff ({w:.1f} mm)"
    return True, ""
