"""Pipeline configuration. One dataclass, everything explicit, everything
serializable — this is the parameter set the stateless service round-trips,
so no hidden module-level tunables anywhere else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    # Physical target: the artwork's finished embroidered width. The px->mm
    # factor derives from this against the non-background artwork bbox.
    target_width_mm: float = 80.0

    # Stage 2
    max_colors: int = 12
    seed: int = 0                      # k-means RNG seed — fixed for determinism
    # Cluster centers within this CIE76 distance are the SAME flat color that
    # k-means split; merged before spool snapping. Also the perpendicular
    # tolerance for the phantom-blend collinearity test.
    merge_delta_e: float = 6.0
    aa_iterations: int = 2             # AA-halo majority-filter passes
    aa_phantom_edge_frac: float = 0.9  # cluster >90% edge pixels = phantom blend color

    # Stage 1
    bg_tolerance_lab: float = 6.0      # Delta-E-ish flood tolerance
    bg_margin_mm: float = 3.0          # intrusion past this inside a shape's hull = uncertain
    bg_intrusion_min_mm: float = 2.0   # intrusion below (this mm)^2 is boundary noise, not art loss
    min_px_per_mm: float = 4.0         # resolution floor at target size
    upscale_cap: float = 4.0           # max Lanczos upscale factor
    denoise: bool = True

    # Stage 3
    min_detail_mm: float = 1.5         # blueprint hard constraint
    # Absorbed regions below this fraction of the min-detail area are
    # anti-alias cleanup, not lost artwork — absorbed silently so the review
    # screen's warning stays meaningful ("30 details merged" from AA slivers
    # is noise that trains the user to ignore warnings).
    report_absorb_frac: float = 0.25

    # Stage 4
    simplify_tol_mm: float = 0.2

    # Debug artifacts: written per stage when set
    debug_dir: Path | None = None

    extra: dict = field(default_factory=dict)  # forward-compat scratch
