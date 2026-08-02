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
    # Which manufacturer's chart the design is snapped to. Ids match the
    # browser's (app/src/lib/threadBrandsIndex.js) because Studio sends its
    # stored preference straight through; None = Isacord, the shop default and
    # what every golden here is pinned to. The operator buys the cone this
    # names, so an unknown id raises rather than silently substituting.
    thread_brand: str | None = None
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
    # The run-tier rescue (stages 3, 4 and 7 together). A shape below the
    # sewable floor that would otherwise be dropped is kept and sewn as a
    # light bean run on its outline: on the benchmark logo at 90 mm the whole
    # "ENTERPRISES INC." subline sits under the floor, and dropping it means
    # a line of the customer's text silently vanishing. Shapes below the
    # thread's own visual weight (machine.RUN_MIN_LOOP_MM / RUN_MIN_AREA_MM2)
    # still drop. False restores the old drop-everything behaviour.
    small_shape_rescue: bool = True

    # Stage 4
    simplify_tol_mm: float = 0.2

    # Stage 5 — sew order, underlap, pull compensation
    # Which garment/fabric the design is going on. The fabric preset supplies
    # pull compensation, underlay style, density adjustment and trim distance;
    # naming a garment picks its usual fabric. An explicit fabric_id wins.
    garment_id: str | None = None
    fabric_id: str | None = None
    # How far a color extends underneath the color that sews after it. Enough
    # to survive fabric pull, small enough never to read as a color error.
    overlap_mm: float = 0.25

    # Stage 6 — fill. None means "use the machine default", so a caller can
    # override density without knowing the whole table.
    fill_row_mm: float | None = None
    fill_stitch_mm: float | None = None
    # None = per-region principal axis (what the browser engine does, and what
    # beat a fixed angle in practice). A number forces every region to it.
    fill_angle_deg: float | None = None
    # None = the fabric preset's fill underlay style.
    underlay_style: str | None = None
    underlay: bool = True

    # Which fill technique a fill-classified shape sews with.
    #
    # "tatami"  – straight rows at one angle. THE DEFAULT, and every golden in
    #             the suite is pinned to it.
    # "contour" – uniform inward offsets of the outline, sewn inner to outer
    #             (stage6_contour). Rows follow the silhouette instead of
    #             cutting across it, which is the one thing tatami structurally
    #             cannot do: even needle distribution in a shape whose width
    #             varies along its length. Rings, letterforms, crescents.
    #             Falls back to tatami on any shape contour produces nothing
    #             for, so turning it on can never drop artwork.
    #
    # Satin classification runs first either way — a ribbon is still a ribbon.
    fill_technique: str = "tatami"
    # None = fill_row_mm (or the machine default). Contour rings are the same
    # 0.40 mm apart as tatami rows; this exists so the ring tier can be opened
    # up independently, which is what "best used for open fills with low stitch
    # counts" means in Wilcom's own positioning of Offset Fill.
    contour_spacing_mm: float | None = None
    # How far a chord may bow off the ring it approximates (Ink/Stitch calls it
    # running stitch tolerance). None = machine.CONTOUR_TOLERANCE_MM.
    contour_tolerance_mm: float | None = None

    # Satin classification. Ribbons up to this wide sew as satin columns;
    # None = the machine default (3.0 mm, matching the browser engine).
    # satin=False forces everything to fill — the pre-step-4 behaviour,
    # kept as an escape hatch for comparison sew-outs.
    satin: bool = True
    satin_max_width_mm: float | None = None

    # Split satin. A satin cross longer than the threshold carries
    # intermediate penetrations, staggered station to station so the holes
    # never line up (machine.SPLIT_* carry the corpus measurements: the
    # majority of professional crosses split from ~5 mm, ~100% by 7.5).
    # True is the corpus-majority default; False sews raw crosses however
    # long — a real house style (jolly-af and sweet-heart ship 6.5-7 mm raw
    # crosses), not a safety toggle. None = machine.SPLIT_SATIN_ABOVE_MM.
    # Wiring: stage 7's satin_shape call maps these to its `split_above_mm`
    # kwarg (False -> math.inf). Until that one-line wiring lands, the
    # machine default applies — identical behaviour for this default config.
    split_satin: bool = True
    split_satin_above_mm: float | None = None

    # Stage 6 — the border tier (an outline sewn as one closed circuit).
    #
    # "off"  – no borders. THE DEFAULT, and it is a measured choice, not
    #          timidity: our tatami fill has no ragged edge to cover (measured
    #          starvation 0.00 mm with zero variance on 13 real letterforms at
    #          three sizes, because `_row_points` puts both row ends on the
    #          shape's edge by construction), and the corpus shows a plain
    #          majority of fills going unbordered — 18 borders against 21 fill
    #          elements and 150 satin elements in the same 19 files. An
    #          unearned border is ~400 stitches per ring and a heavier logo for
    #          nothing, and Kent pays for machine time.
    # "auto" – satin border on every fill-classified shape wide enough to host
    #          a column, bean run where it is not. A shape classified as satin
    #          never gets one; see stage 7.
    # "bean" – the light tier wherever a centreline fits.
    #
    # Per-shape intent overrides the mode: `Region.meta["border"] = True/False`
    # rides the existing `match_shape_ids` carry-forward, so a review-screen
    # decision survives a re-digitize with no new contract.
    border: str = "off"
    border_width_mm: float | None = None

    # Debug artifacts: written per stage when set
    debug_dir: Path | None = None

    extra: dict = field(default_factory=dict)  # forward-compat scratch

    # Step 9 — preflight scoring. Whether the service attaches a preflight
    # report to a finished job. On by default because the report is the point
    # of digitizing through the service at all; off is for callers that score
    # separately (or benchmark the pipeline without the extra stage-1 pass
    # the thread-match check costs). Thresholds live in preflight.py with
    # their citations, deliberately not here: they are measurements, not
    # preferences.
    preflight: bool = True

    # Stage 7 — chaining. Whether a needle-up move that would be trimmed may
    # instead be sewn as a needle-down link, when its path is buried under a
    # colour that sews later or rides over work this colour has already laid
    # (chaining laws 59-62; docs/chaining-laws-2026-08-01.md). Distance stops
    # being the decision variable — coverage is — and `fabric.trim_at_mm` is
    # left governing only the moves that cannot be covered.
    #
    # True is the measured default: professionals link roughly two thirds of
    # transitions at every gap out to 40 mm. False restores the pure distance
    # test, and is what the pre-chaining goldens are pinned to.
    chain_links: bool = True
