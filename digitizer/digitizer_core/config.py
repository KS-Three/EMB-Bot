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

    # Stage 0
    # Skip signal computation, force this classification instead — the UI
    # override the plan calls for, and the escape hatch every test that
    # needs a specific class without depending on threshold tuning uses.
    # One of "flat" | "gradient" | "photo_subject" | "photo_scene", or None
    # to classify normally.
    forced_class: str | None = None

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
    # Directional pull/push compensation (Laws 22-24). False is the shipped
    # behaviour: one isotropic `buffer(pull)` outward in every direction, which
    # is right on average and wrong everywhere specific — no major package does
    # it, because pull acts ALONG the stitch direction and push acts across it.
    #
    # True compensates each tier the way its stitches actually run:
    #   fill  – growth only along the fill angle, on the edges its rows
    #           penetrate; the edges the rows run parallel to keep artwork size.
    #   satin – growth stays isotropic, which is already exact on the rails (a
    #           column's stitch direction IS its boundary normal there), and
    #           each open END is cut back by `machine.PUSH_CUTBACK_MM` plus the
    #           pull the isotropic step wrongly added there.
    #
    # Default False because the cutback is sew-out-gated (playbook Part 4 test
    # 4) and because every committed golden is pinned to the isotropic result.
    directional_comp: bool = False

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
    #
    # READ THIS BEFORE TURNING "contour" ON. An adversarial pass on 2026-08-02
    # confirmed three defects no shipped test could see. As of 2026-08-04 the
    # instrument that pass mandated exists and two of the three are fixed;
    # the tier still ships off because "tatami" is byte-identical to the
    # engine that has always shipped and contour's remaining cost (defect 1)
    # is real, measured, and un-sew-out-gated — not because nothing changed.
    #
    # THE INSTRUMENT (built first, as mandated): `barecircle.py` measures the
    # widest circle of bare fabric inscribable in a shape further than half a
    # thread width from any emitted stitch — rasterized exact-EDT, trusting
    # only the polygon and the runs, never this tier's own bookkeeping.
    # Validated against the pass's own figures (tests/test_barecircle.py):
    # Sb253ebba contour 0.640 cited / 0.644 measured, tatami 0.090 / 0.094;
    # the 10-point star's mitred-offset annihilation (offsets dead at
    # ~5.6 mm of inset against an inradius of 10.00, ledger charging ~0.2)
    # reproduces. ONE figure did not survive re-measurement as written: the
    # star's "2.94 mm bare disc" is a DIAMETER — every reconstruction
    # measures 1.28-1.43 mm bare RADIUS, and defect 2's own "silent on that
    # 1.47 mm bare radius" (= 2.94/2) only coheres under that reading.
    #
    #  1. A BARE CORE INSIDE ORDINARY SHAPES — STILL OPEN, NOW MEASURED.
    #     `_rings` stops when the mitred `_offset` returns nothing, and the
    #     fabric inside the last ring is never charged to `skipped_area_mm2`.
    #     Every healthy shape leaves a 0.86 mm structural centre dot
    #     (machine.CONTOUR_BARE_CORE_MM — ~10x tatami's 0.090); notched
    #     interiors can be annihilated wholesale (the star's 1.33 mm core).
    #     The gate now CATCHES the pathological cores and the report carries
    #     `bare_radius_mm` per shape, but shrinking the structural dot itself
    #     (a finishing pass? tighter terminal offsets?) is unbuilt and is the
    #     reason this tier is not default-quality yet.
    #  2. `starved` MISCALIBRATION — FIXED 2026-08-04, both directions.
    #     The area-fraction gate is gone; `starved` IS the instrument's
    #     measurement, fired when the widest bare spot beats
    #     `barecircle.starved_threshold_mm` (the measured structural dot plus
    #     half a ring spacing — 1.07 mm at shipped density; derivation at the
    #     function). The old gate's silence on the star's 1.47 mm class now
    #     fires; its false alarms — whitebg's Sf5200f3f at 0.499 mm bare (the
    #     cited "firing on 0.51") and Sb253ebba at 0.644, both under a
    #     healthy disc's own dot — are now silent. Proven in both directions
    #     in tests/test_barecircle.py and tests/test_contour.py.
    #  3. TRANSITION-CHORD CONTAINMENT — FIXED 2026-08-04. `_link` now
    #     containment-tests the ring-to-ring crossing chord and banks the
    #     path (travel, not an escaping stitch) when it fails. The cited
    #     15 mm disc with a 0.3 mm hole reproduced (one transition 0.255 mm
    #     outside pre-fix) and is the regression pin; the cited 0.45 mm neck
    #     could not be reconstructed from its description — four neck
    #     geometries tried, none escapes even pre-fix.
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

    # Stage 6 — the appliqué tier (docs/specialty-techniques-2026-08-01.md §2).
    #
    # OFF by default, and that default is load-bearing: with `applique` False
    # nothing in this block is read, no step metadata is attached, and a design
    # sews byte-for-byte what it sewed before the tier existed. `tests/
    # test_applique.py::test_applique_off_is_byte_identical` pins that.
    #
    # Per-shape intent overrides the mode in both directions, exactly as
    # `border` does: `Region.meta["applique"] = True/False` rides the existing
    # `match_shape_ids` carry-forward, so a review-screen decision survives a
    # re-digitize with no new contract.
    applique: bool = False
    # "trim_in_place" (4 layers, 2 stops) | "pre_cut" (3 layers, 1 stop).
    # Wilcom's guide-run panel makes this an explicit switch and §2.1 calls it
    # "the single biggest branch in the feature".
    applique_mode: str = "trim_in_place"
    # Shop-level trim discipline: tight | normal | loose. §2.3's implementation
    # corollary is emphatic — expose THIS and derive the cover width from the
    # tolerance stack. Do not expose cover width as a free number the user
    # guesses at.
    applique_trim_discipline: str = "normal"
    # Pre-cut only: how accurately the piece lands. "hand" (0.75 mm) or
    # "heat_tacked" (0.40 mm). Laser cutting adds no geometry, it removes
    # tolerance — the whole benefit shows up here (§2.9).
    applique_placement: str = "hand"
    # Which material floor the solved width may not go under: twill | felt |
    # woven | knit | loose_weave (§2.13 W_floor_material).
    applique_material: str = "woven"
    # Tackdown stitch type: run | double_run | zigzag | e_stitch | none.
    # Trim-in-place wants run/double_run — a zigzag tack gets clipped by the
    # scissors and leaves fabric whiskers (§2.7). None = pick from the mode.
    applique_tackdown: str | None = None
    # Cover stitch type: satin | zigzag | e_stitch. Zigzag at 1.69 mm is the
    # tackle-twill look and a genuinely different aesthetic, not a cheap satin.
    applique_cover: str = "satin"
    # Override the solved cover width, in mm. None = solve from the tolerance
    # stack, which is what you want; a number here is an escape hatch for a
    # sew-out comparison and is still clamped to [2.5, 5.0].
    applique_cover_width_mm: float | None = None

    # --- Review-screen shape edits (the shape-layers contract v1) ----------
    #
    # Both fields are keyed by the content-derived shape_id the review payload
    # reports (`regions.assign_shape_ids`): the same artwork re-digitized with
    # the same stage 1-4 parameters produces the same ids, which is what makes
    # a stateless edit round-trip possible at all. Applied by
    # `regions.apply_shape_edits` / `apply_layer_overrides`, called from
    # `pipeline.run_stages` so both `digitize()` and a service re-digitize
    # pass through them. Empty (the defaults) is byte-identical to the engine
    # before the contract existed.
    #
    # Shapes the user removed on the review screen. Dropped AFTER stage 4 —
    # ids are assigned against the full generation first, so the survivors'
    # ids cannot churn — and reported via SHAPES_DELETED_BY_USER so the panel
    # can say "2 shapes hidden by you" rather than losing them silently. An id
    # that matches nothing is a SHAPE_EDIT_UNKNOWN_ID warning, never an error:
    # the art may have changed under the edit.
    deleted_shape_ids: list = field(default_factory=list)
    # Per-shape decisions, keyed by shape_id. Each value is a dict that may
    # hold any of:
    #   thread_index: int     – recolor: index into the job's chart. Applied
    #                           to the Region itself before stage-5 grouping,
    #                           so the shape moves to that thread's color
    #                           block; the palette gains the thread if nothing
    #                           else sews it.
    #   fill_angle_deg: float – this shape's fill angle. Beats the global
    #                           fill_angle_deg and the per-region PCA; the
    #                           full precedence is stated where stage 7
    #                           decides it.
    #   tier: str             – "auto" (default) | "satin" | "fill" | "run".
    #                           Forces the stitch tier. Geometry the forced
    #                           tier cannot sew falls through the same rescue
    #                           ladder the auto path uses, so artwork never
    #                           silently vanishes.
    #   border: str           – "off" | "auto" | "bean". Per-shape border
    #                           intent; beats the global `border` mode in both
    #                           directions. (The pre-contract True/False meta
    #                           form is still honoured.)
    #   layer: int            – explicit sew-order layer; stage 5 already
    #                           orders color blocks by meta["layer"]. Applied
    #                           AFTER the palette is compacted, so moving a
    #                           shape never drops its thread from the color
    #                           list.
    #   sew_order: int         – explicit position (0-based) in this shape's
    #                           color layer's OWN sew sequence (contract
    #                           v1.2) — distinct from `layer`, which picks
    #                           which layer a shape sews in; this picks where
    #                           within it. Stage 7 forces a pinned shape into
    #                           its slot once the running pick count reaches
    #                           it, and fills every unpinned slot with
    #                           nearest-neighbour exactly as before, so a
    #                           layer with no override sews byte-identical.
    # Values ride Region.meta so stages 5 and 7 pick them up where each
    # decision is made. Unknown shape_ids warn (SHAPE_EDIT_UNKNOWN_ID).
    shape_overrides: dict = field(default_factory=dict)

    # Debug artifacts: written per stage when set
    debug_dir: Path | None = None

    # Forward-compat scratch. Known keys:
    #   shapefield: bool — DT-first migration M1
    #               (docs/dt-first-architecture-2026-08-01.md §2). Off by
    #               default (absent or falsy = today's path, byte-identical
    #               by construction). On routes stage6_satin's skeleton/DT
    #               extraction through digitizer_core/shapefield.py's
    #               ShapeField instead of stage6_satin's own inline
    #               rasterize+medial_axis call — same numbers, hoisted for
    #               a later stage (M2/M3, not this one) to eventually share.
    extra: dict = field(default_factory=dict)

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
    # OFF BY DEFAULT AS OF 2026-08-02, and it shipped on for less than a day.
    # The laws are right and the win is real — benchmark trims/1k 8.42 -> 2.63,
    # inside the professional band for the first time — but the COVERAGE TEST
    # that makes a link safe is measured against polygons, and a polygon is not
    # thread.
    #
    # `_link_cover` quotes `p.polygon` for every shape the block has sewn. A
    # fill does not stitch its whole polygon (its first row sits half a row
    # inside the boundary, and `_columns` drops non-monotone spans), and a
    # satin column does not either (it stops short at the tips and fans on
    # curves). So the router is told it may travel over ground its own colour
    # never reaches, and it does.
    #
    # Measured on the benchmark at 90 mm, against the union of every emitted
    # non-travel stitch in the design, over each link's REAL sewn path
    # (previous run's last point -> link -> next run's first point), bare being
    # further than half a thread width from any thread of any colour:
    #
    #     left_chest  chain off:  0 links,  0 exposed,  0.00 mm bare
    #     left_chest  chain ON:  23 links, 17 exposed, 12.38 mm, worst 0.673 mm
    #     full_back   chain off:  1 link,   0 exposed,  0.00 mm bare
    #     full_back   chain ON:  31 links, 26 exposed, 29.11 mm, worst 1.055 mm
    #
    # full_back is fleece_sweatshirt, a stock preset. The control is exactly
    # zero, so every millimetre of that is chaining's.
    #
    # Neither shipped instrument can see it, and that is structural, not an
    # oversight: `tests/test_chaining.py::_uncovered_links` and
    # `tools/chain_probe.py::uncovered_travel` both rebuild the cover from the
    # same polygons the router trusted, both skip one-point links (37% of the
    # benchmark's), and both test `LineString(run.points)` when `_link_stitches`
    # returns only the route's INTERIOR — so up to RUN_STITCH_MM at each end is
    # never examined by anything.
    #
    # Turning this off costs a needle-up move, not a thread cut: refusing a
    # link makes it a jump, and the measured trims/1k does not move. That is
    # the cheap direction to be wrong in, and a float on fleece is not.
    #
    # UPDATE 2026-08-03: the first of the three preconditions is done.
    # `_link_cover` now builds the already-laid half of its cover from `runs`
    # — the block's real emitted stitch centrelines, buffered to their real
    # thread width — instead of from `p.polygon`. Measured on the committed
    # `logo_alpha` fixture (the benchmark file the numbers above were measured
    # on lives outside the repo and could not be re-measured): chaining's
    # extra links (10 -> 14) now add ZERO bare exposure — `exp`/`bare`/`worst`
    # land on exactly the same figures chaining OFF does — while still
    # cutting trims (13 -> 9) and total stitch count (3012 -> 2992). See
    # `tests/test_chaining.py::test_chaining_adds_no_bare_fabric_exposure_on_
    # the_committed_fixture`.
    #
    # UPDATE 2026-08-04: the second is done too. `covered_by` — the half of
    # the cover whose stitches do not exist yet at routing time — is now
    # eroded by LINK_COVER_INSET_MM (0.75 mm, machine.py has the full
    # derivation table) before it may bury a link. Derived from measurement
    # on both committed fixtures, real emitted runs vs the artwork polygon
    # `covered_by` quotes: fill's nearest centreline stops up to 0.223 mm
    # inside the boundary (thread edge 0.023 mm shy), satin's up to 0.501 mm
    # (edge 0.301 mm shy — tips stop short, columns fan), and a run-tier
    # shape covers no interior at all, honest only once eroded away at its
    # inradius (0.527/0.539 mm measured). Worst measured 0.539 +
    # LINK_COVER_TOL_MM the cover buffers back on = 0.739, rounded up to
    # 0.75. Re-measured with chaining ON after the inset (chain_probe, both
    # committed fixtures): every link the inset disqualifies becomes a jump,
    # never an exposure, and on these fixtures none needed it — logo_alpha
    # still links 13 -> 17 and trims 14 -> 10 (st 3312 -> 3292), logo_whitebg
    # unchanged (chaining adds nothing there, with or without the inset),
    # chaining's ADDED bare exposure 0.00 mm on both (exp/bare/worst land on
    # exactly the chain-off floor: 0.7 mm/0.2057 and 0.8 mm/0.2045, stage 6's
    # own pre-existing in-shape travel). The inset is live, not idle: it
    # removes 20-32% of each block's future-colour cover area on logo_alpha
    # and erodes the run-tier sliver out of the cover entirely; the fixtures'
    # links just never rode the dishonest margin. Pinned by
    # `tests/test_chaining.py::test_a_sliver_of_a_future_colour_no_longer_
    # counts_as_cover` (a 1.2 mm band that linked pre-inset must now cut).
    # What no inset can fix, measured so nobody re-derives it: hairline gaps
    # between fanned satin crosses persist at any inset (<= 0.127 mm
    # inscribed radius, <= 0.121 mm beyond the thread edge) — under one
    # thread width, left to the sew-out below.
    #
    # Still outstanding, and still why this stays off by default:
    #   - A sew-out that says at what clearance a needle-down float actually
    #     shows — LINK_COVER_TOL_MM is still a thread spec, not a measurement.
    chain_links: bool = False
