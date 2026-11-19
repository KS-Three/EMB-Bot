"""Stage 6 3D puff: config gate and per-shape eligibility.

Spec: docs/superpowers/specs/2026-11-19-3d-puff-design.md. Satin only; tatami
never puffs. Eligibility is against the puff width band (machine.PUFF_*),
never the flat satin ceiling.
"""
from __future__ import annotations

from . import machine
from .stitchwidth import measure_width_mm


def _max_inscribed_diameter_mm(geom) -> float:
    """Widest inscribed circle's diameter over every part; holes count as edges."""
    from shapely.ops import polylabel
    parts = list(getattr(geom, "geoms", [geom]))
    best = 0.0
    for part in parts:
        try:
            c = polylabel(part, tolerance=0.02)
            best = max(best, 2.0 * float(part.boundary.distance(c)))
        except Exception:  # noqa: BLE001 -- a degenerate part has no width
            continue
    return best


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
    geom = region.polygon
    # measure_width_mm takes a single Polygon: a MultiPolygon is judged by its
    # largest part.
    main = max(getattr(geom, "geoms", [geom]), key=lambda g: g.area)
    w = measure_width_mm(main)
    if w is None or w < machine.PUFF_MIN_WIDTH_MM:
        shown = "0.0" if w is None else f"{w:.1f}"
        return False, f"too thin for foam ({shown} mm)"
    # Too wide is the widest inscribed circle, not the skeleton mean: the mean
    # under-reads wide bars (a 14 mm bar reads 9.8) and would defeat the ceiling.
    widest = _max_inscribed_diameter_mm(region.polygon)
    if widest > machine.PUFF_MAX_WIDTH_MM:
        return False, f"too wide to puff ({widest:.1f} mm)"
    return True, ""
