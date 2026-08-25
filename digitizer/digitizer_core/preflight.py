"""Preflight — what will go wrong on the machine, said BEFORE the hoop moves.

A scoring pass over a FINISHED plan. It consumes what `digitize` produced —
the `PipelineResult`, the `StitchPlan`, the config that shaped them, and
optionally the artwork itself — and returns structured findings. It never
changes the plan: every check here reads geometry the planner already
committed to, because the operator's question is "should I sew this file",
not "how should it have been sewn".

Each finding is {code, severity, message, extra}. Severity means:
  * "info"  — worth knowing, sew anyway.
  * "warn"  — will cost machine time or quality; look before sewing.
  * "block" — will visibly go wrong; resolve it or get sign-off first.
The message is written for the person at the machine: sentence case, says
what to DO, never engine vocabulary.

Three checks answer for tiers that landed after this module was written, and
all three read the FINISHED STITCHES rather than the geometry the planner
reasoned about, because that is where those tiers and their own instruments
part company:
  * `_link_findings` — chaining (laws 59-62) sews a needle-down link where a
    trim used to go, legal only where something buries it. Stage 7 tests that
    against polygons; a polygon says where a shape is, not where its thread
    landed, and the run tier sews a small shape's outline and leaves the
    inside bare. Measured over 60 configurations, stage 7's own re-derivation
    reports zero uncovered links in every one while the thread says up to
    2.29 mm of link lies on open fabric. Since 2026-08-11 the instrument
    scores BETWEEN-shape transport only: a shape's own internal routing
    (stage 6's row-skip travel) is not a chain link, and scoring it blocked
    a clean one-shape design at 104-107 mm (`_transport_and_content` has the
    classification and the closeout citation).
  * `_contour_findings` — the contour tier's per-shape starvation report,
    which went to `plan.warnings` and reached nobody reading this report.
  * `_fill_row_advance_mm`'s axis gate — the row-density instrument answered
    confidently and wrongly on contour rings, warning on three house fixtures
    out of four whose coverage was healthy. It now declines instead.

Most checks read one object at a time. `_coverage_findings` does not, and
that is deliberate: law 27 of the machine-physics playbook says the density
budget is a per-REGION sum — everything overlapping one patch of fabric,
underlay included — so a stack of individually-correct layers passes every
per-object check ever written and still puckers the garment. Its instrument
is `_coverage_map`, which rasterizes the whole plan's stitch geometry into
coverage units where 1.0 is one full covering layer of 40wt thread.

The thread-colour instrument is per-REGION, and became so on 2026-08-11.
`_thread_match_findings` scores every region's own artwork pixels against the
one spool assigned to it — the median of the PER-PIXEL CIEDE2000, never a
summary colour — and THREAD_MATCH_POOR is driven by each thread's worst
region. It used to pool a per-thread median across every region sharing a
spool, and that pooling failed twice in one day (docs/photo-quality-root-
cause-2026-08-11.md): the independent per-channel median of a bimodal pool
is a colour almost no pixel carries, and a verified per-region improvement
(stage 4's thread revalidation, #6.3) read here as a REGRESSION —
drone_render's pooled worst moved 9.2 -> 33.6 across a change that HALVED
the honest per-region worst (20.99 -> 10.64). An instrument that cannot see
a correct fix is worse than no instrument, so it changed. The 0-100 score
weighting shifts with it — a thread is now judged by its worst region, so
multi-region photo work can gain or lose findings — but the philosophy does
not: a worse colour match still costs more score.

On the PHOTO route that instrument changed again on 2026-08-24, for the
opposite failure. Reducing a photograph to a capped cone list guarantees
per-thread colour distance, so raw distance condemned work that was already
optimal: across the 32-job acceptance sheet THREAD_MATCH_POOR fired 256
times at `block`, and every photo job graded F / "do not sew". The photo
route is now scored on EXCESS over the best spool the design's own regions
already sew — a swap that costs the operator nothing — so an optimal
assignment is silent while a free improvement left untaken still blocks.

Measured in-pipeline across Kent's four acceptance portraits, 330 regions:
raw distance puts 258 of them over DELTA_E_VISIBLE and 103 over
DELTA_E_CLEARLY_DIFFERENT; excess puts 3 and 1 there. 277 of the 330 wear
the single closest cone the design loads. Per photo (regions, cones, raw
median/max, excess median/max, optimal): sparkler_dusk 99/15, 8.85/19.96,
0.00/5.29, 82; boat_dog_toddler 88/12, 7.88/24.87, 0.00/6.59, 69;
baby_deck_laugh 110/12, 6.10/30.13, 0.00/13.18, 95; face_closeup_blur
33/7, 7.67/12.80, 0.00/1.15, 31. That baby_deck_laugh 13.18 is a real
mis-assignment and still blocks, which is why this rescores rather than
exempting photos wholesale.

Non-photo routes keep the raw yardstick byte-for-byte.

The photo guardrails (photo plan §2 row 15) are the buildable-today subset
of that plan's preflight row: input resolution vs the photo floor, subject/
background lightness contrast, the cutaway-stabilizer prescription, and the
single-needle color-stop wall. The two guards that need signals which do
not exist yet (face detection, fabric nap) are documented as a seam at the
"FACE-GATED REMAINDER" comment in the threshold block, not half-built.

Every threshold is a measurement, cited next to its constant. The
instruments were validated on known-clean fixtures first (probe run
2026-07-31, extended 2026-08-01 for the coverage map): the fixture logo and
the curved ribbon produce ZERO findings, because a metric that flags clean
work trains the operator to ignore the report — the exact failure a past fan
metric had when it scored a clean ribbon 30%.

Codes are defined HERE, not in warnings_codes.py — that file is owned by
another lane this round. They follow its contract exactly (append-only
machine-readable strings, UI switches on codes never prose) and may migrate
there at merge.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from shapely.geometry import Point
from skimage.color import deltaE_ciede2000

from . import machine, stitches
from .config import PHOTO_CLASSES, PipelineConfig
from .pipeline import PipelineResult, fabric_for
from .stage0_classify import classify
from .stage1_prep import prep
from .stage6_meander import MEANDER_CELL_MM, MEANDER_COARSE_LEVELS
from .stage6_satin import strip_splits
from .stage6_scanline import SCANLINE_LEVEL_STRIDES, SCANLINE_ROW_MM
from .stage6_streamline import (STREAMLINE_D_SEP_DARK_MM,
                                STREAMLINE_D_SEP_LIGHT_MM)
from .stitches import StitchPlan
from .threads import chart_for, rgb_to_lab

# --- Codes (may migrate to warnings_codes.py at merge) ---------------------

THREAD_MATCH_POOR = "THREAD_MATCH_POOR"        # extra: {thread_number, thread_name, brand_id, delta_e, excess_delta_e, better_spool, worst_shape_id, region_count, regions_scored, regions, artwork_rgb, thread_rgb} — excess_delta_e/better_spool are None off the photo route (raw yardstick), populated on it
LETTERING_TOO_SMALL = "LETTERING_TOO_SMALL"    # extra: {count, shapes: [{shape_id, column_mm, extent_mm}]}
STITCHES_TOO_LONG = "STITCHES_TOO_LONG"        # extra: {count, max_mm}
STITCHES_TOO_SHORT = "STITCHES_TOO_SHORT"      # extra: {fraction, count, total}
TRIM_HEAVY = "TRIM_HEAVY"                      # extra: {per_1000, trims, stitches}
DENSITY_EXTREME = "DENSITY_EXTREME"            # extra: {kind, measured_mm, target_mm, ratio} (+ technique, band_mm on a tonal fill)
DENSITY_STACKED = "DENSITY_STACKED"            # extra: {peak_units, p95_units, over_warn_mm2, over_block_mm2, cell_mm}
SAME_HOLE_HEAVY = "SAME_HOLE_HEAVY"            # extra: {fraction, repeat_points, penetrations, baseline}
LINK_UNCOVERED = "LINK_UNCOVERED"              # extra: {max_mm, limit_mm, total_mm, at_mm, thread_mm}
ARTWORK_UNCOVERED = "ARTWORK_UNCOVERED"        # extra: {count, worst_mm2, total_mm2, wanted_mm2, shapes: [{shape_id, missing_mm2, area_mm2}]}
CONTOUR_STARVED = "CONTOUR_STARVED"            # extra: {count, rings, shapes}
PHOTO_RESOLUTION_LOW = "PHOTO_RESOLUTION_LOW"  # extra: {px_per_mm, min_px_per_mm}
SUBJECT_CONTRAST_LOW = "SUBJECT_CONTRAST_LOW"  # extra: {delta_l, min_delta_l, bg_lightness}
STABILIZER_CUTAWAY = "STABILIZER_CUTAWAY"      # extra: {stitch_count, threshold}
COLOR_STOPS_HEAVY = "COLOR_STOPS_HEAVY"        # extra: {color_changes, max_stops}
FACE_TOO_SMALL = "FACE_TOO_SMALL"              # extra: {count, design_mm, fits_hoop_mm, min_hoop_mm}
CLASS_OVERRIDE_TECHNIQUE_MISMATCH = "CLASS_OVERRIDE_TECHNIQUE_MISMATCH"  # extra: {forced_class, detected_class, fill_technique}

# The stage-6 warning this module re-reads. Owned by the contour-fill lane
# (warnings_codes.CONTOUR_RING_UNREACHABLE); named by string so preflight
# neither imports it nor breaks in a tree where that lane has not landed.
_CONTOUR_RING_UNREACHABLE = "CONTOUR_RING_UNREACHABLE"

# Stage 0's photo classifications, re-read from plan.warnings the same way
# and for the same reason as _CONTOUR_RING_UNREACHABLE above: the classifier
# says what it decided in its own warning codes, preflight carries that
# rather than re-deriving it. A FORCED class writes no warning (stage 0 skips
# signal computation entirely), so `_is_photo_class` checks cfg.forced_class
# first.
_CLASSIFIED_PHOTO = ("CLASSIFIED_PHOTO_SUBJECT", "CLASSIFIED_PHOTO_SCENE")

# The photo auto-route's announcement (warnings_codes.PHOTO_AUTO_TIER, emitted
# by pipeline.run_stages), re-read by the density check under the same
# by-string convention as the codes above. It has to be the warning: on the
# auto route `cfg.fill_technique` still reads "tatami" — the tier decision is
# stage 7's own recomputation (`plan_stitches`: `auto_tier or
# cfg.fill_technique`) — and this warning is the only place the plan records
# which fill tier it actually sewed.
_PHOTO_AUTO_TIER = "photo_auto_tier"

# --- Thresholds, each with its measurement ---------------------------------

# CIEDE2000 color difference. The JND sits near 1.0; the practical scale in
# Mokrzycki & Tatol 2011 ("Colour difference deltaE — a survey") reads 2-3.5
# as noticeable to an average observer, 3.5-5 as a clear difference, and
# above 5 as two different colors. Measured against our own charts: Isacord's
# worst match on the fixture logo is 4.4 (an honest "no spool is that exact
# red", not a defect), while Madeira Rayon's nearest to the same art's purple
# is 10.7 by this instrument (12.2 by the step-8 probe against the cluster
# center) — the motivating case, visibly a different color and previously
# silent. 5.0 separates those two worlds cleanly.
DELTA_E_VISIBLE = 5.0
# Twice the "two different colors" line: nobody argues the substitution is
# fine at this distance, so it escalates from warn to block.
DELTA_E_CLEARLY_DIFFERENT = 10.0

# Sewable lettering size. House sew-out fact (2026-07-22 flatten validation):
# stacked text below ~4 mm cap height dies at hat scale. Wilcom's Hatch fonts
# ship recommended ranges bottoming at 5 mm for run fonts and ~7 mm for satin
# fonts, so 4 mm is already the generous end. Measured on the benchmark logo:
# at 90 mm no shape trips this, at 55 mm one marginal letter does, at 40 mm
# nine of thirteen do — which matches how those sizes actually sew.
MIN_LETTER_EXTENT_MM = 4.0
# A satin column narrower than the needle minimum: every cross re-enters the
# previous hole's neighborhood and the stroke reads as a scar, not a line.
MIN_COLUMN_MM = machine.MIN_STITCH_MM

# Fraction of satin stitches under MIN_STITCH_MM. The benchmark logo measured
# 54.6% before the zigzag-order fix and 10.4% after (re-measured 9.9% by this
# instrument); clean fixtures sit at 1-3%. A plan back above 25% — halfway to
# the broken world — is a regression, not a style.
SATIN_SHORT_FRACTION_MAX = 0.25

# Trims per 1,000 stitches across the 39-file professional corpus: median
# 0.8, range 0.1-4.1 (docs/pro-digitizing-playbook.md, law 1). Above the top
# of the observed professional range, the machine spends real time cutting.
TRIMS_PER_1000_MAX = 4.1

# Emitted density vs the planner's own target. 1.5x either way is past any
# fabric preset's adjustment and means the geometry diverged from intent —
# gapping (too sparse) or fabric bunching (too dense) on the machine.
DENSITY_RATIO_MAX = 1.5

# How concentrated a fill run's step directions must be about ONE axis before
# `_fill_row_advance_mm` is willing to call its perpendicular steps "row
# advance". The instrument's whole model is rows along an axis with short turns
# between them, and a CONTOUR fill has no such axis — its rings sweep every
# direction — so on contour geometry the model does not degrade, it inverts:
# nearly every step reads as a turn and the median "row advance" it returns is
# really the ring chord.
#
# Measured 2026-08-02, length-weighted axial concentration |R| per fill run
# (1.0 = every step on one axis, 0 = uniform):
#
#   design (80 mm, left_chest)     tatami            contour
#   logo_whitebg                   0.913-0.974       0.004-0.150
#   logo_alpha                     0.915-0.974       0.003-0.024
#   bg_uncertain                   0.979-0.991       0.031-0.270
#
# Two populations with nothing between 0.270 and 0.913. Ungated, the contour
# side reported 2.19 / 2.35 / 2.98 mm against the 0.40 mm target and raised a
# DENSITY_EXTREME warn on three fixtures out of four whose coverage map read a
# perfectly healthy 1.36-1.39 units — a false alarm on every contour design
# ever scored. 0.6 sits in the middle of the gap with room on both sides.
#
# A plan whose fills are all below the gate reports `fill_advance_mm: None`.
# That is the honest answer, not a fallback: contour ring spacing is a real
# quantity and this instrument does not measure it.
_FILL_AXIS_MIN = 0.6

# --- Uncovered links, chaining law 60 ---------------------------------------

# Cell of the raster that answers "is there thread on this patch of fabric".
# A tenth of a millimetre is a quarter of the thread's own width, so a ribbon
# is four cells across and the reported length of a bare stretch is exact to
# one cell. NOT `COVERAGE_CELL_MM` (1.0 mm): that cell answers "how many
# layers", which is a different question at a different scale, and at 1.0 mm a
# link running beside a shape would read as covered by it.
_LINK_CELL_MM = 0.1

# Ceiling on the raster, in cells, before it is coarsened. A 200x200 mm hoop is
# 4M cells at 0.1 mm; this only bites on artwork far larger than a hoop.
_LINK_MAX_CELLS = 64_000_000

# --- Per-region coverage, law 27 --------------------------------------------

# A cell holding less than a quarter of a covering layer is fabric the design
# only grazes — a travel stitch crossing bare ground, or the outer half of a
# column's edge cell. Including it drags the median of "what the design puts
# on the garment" toward zero and makes p50 a statement about the bounding
# box rather than about the design. Measured on the fixture logo: the covered
# median moves 0.62 -> 0.93 across this floor, i.e. from "half the map is
# background" to the 1.0 one-layer reading law 16 predicts for a 0.40 mm fill.
_COVERAGE_FLOOR_UNITS = 0.25

# How big one CONNECTED patch over a threshold must be before it counts.
# Law 27's own remedy has a floor — "holes only under objects >= 5x5 mm" —
# so a stacked spot smaller than 5x5 is one the law itself declines to act
# on, and reporting it would be advice we cannot give. That floor is also
# what separates the two populations here, measured 2026-08-01:
#
#   design                        biggest patch >= 2.5   >= 3.5
#   benchmark 90 mm (clean)                11 mm2         2 mm2
#   fixture logo 80 mm (clean)              6 mm2         0
#   fixture + auto border                  17 mm2         1 mm2
#   fixture at 0.20 mm rows (2x)           23 mm2         3 mm2
#   fixture 0.20 mm rows + border         125 mm2        18 mm2   <- warn
#   fixture at 0.13 mm rows (3x)          647 mm2        43 mm2   <- block
#
# Clean work stacks in speckles at column joins and inside sub-5 mm rescued
# shapes; a real stacked-layer failure is a continuous patch two orders of
# magnitude bigger. The finding sums every patch at or over this size.
_COVERAGE_MIN_PATCH_MM2 = 25.0

# --- Artwork left uncovered -------------------------------------------------

# The instrument for "the engine meant to sew this and part of it got no
# thread" — a dropped limb, not a thin spot. Ground truth is the INTERSECTION
# of two masks, and it has to be both:
#
#   * the sewn regions' polygons (holes excluded) — the engine's own claim
#     about what it is sewing, so an area no region claims is not this
#     check's business; and
#   * the artwork's own ink (`~bg_mask`) — so a polygon that over-claims
#     cannot manufacture a defect.
#
# Measured 2026-08-20, each mask alone produces a false-positive class the
# other kills. Polygon alone: `becker_marine_logo`'s wordmark region claims
# the open counter of its "C" (a counter that is not an enclosed hole, so it
# is not an interior ring), and reports 62 mm2 of correctly-bare fabric.
# Ink alone: the same fixture's letters are hollow in the artwork, and the
# enclosed white counters are not in `bg_mask`, so 42.3% of the design reads
# "missing" when it is sewing exactly as designed.
_UNCOVERED_CELL_MM = 0.5

# Half a thread width plus a cell's diagonal slack. Thread laid along a
# shape's own boundary covers the inside of the edge and hangs over the
# outside, so the outermost half-thread of any shape reads under the floor by
# construction — the same effect `_COVERAGE_FLOOR_UNITS` names for column
# edge cells. Eroding by less reports every shape's rim as a defect.
# `cv2.erode` is called with an explicit zero border: without it a full-bleed
# design (artwork touching the image edge) never erodes there, and
# `logo_gaulke_roofing` reports a permanent 37.5 mm2 strip down its right
# border — measured 2026-08-20, 0.0 with the border fixed, at every erosion.
_UNCOVERED_ERODE_MM = 0.4

# How big one CONNECTED uncovered patch must be to report. Measured
# 2026-08-20 over the committed fixtures, worst single patch in mm2:
#
#   fixture                     mm    px/mm   worst    note
#   logo_whitebg                80    10.0     0.00
#   logo_gaulke_roofing         90    14.3     0.00    full-bleed
#   ribbon_curve                60    13.3     0.00
#   logo_alpha                  80    10.0     0.25
#   enthusiast_logo             80    17.5     1.50
#   logo_drone_thermal_badge    90    17.1     3.25    unadjudicated
#   enthusiast_logo            120    11.7     3.75
#   logo_script_tires           90    17.6     4.50    unadjudicated
#   enthusiast_logo            150     9.3     7.75    <- the reported defect
#   becker_marine_logo          90     1.6    44.50    input far below floor
#
# THIS THRESHOLD IS PROVISIONAL. The clean population sits at 0.00-0.25 and
# the two designs with a known or self-evident problem sit at 7.75 and 44.50,
# but the middle of the table is unadjudicated: nobody has looked at whether
# `logo_script_tires`' 4.50 mm2 and `logo_drone_thermal_badge`' 3.25 mm2 are
# real drops or acceptable. 5.0 clears every fixture that has been looked at
# and catches both that have, but the margin to 4.50 is 10%, not the two
# orders of magnitude `_COVERAGE_MIN_PATCH_MM2` earned. Widen the fixture set
# and adjudicate the middle before trusting this number. The METRICS below
# are reported unconditionally and are the honest output; the finding is the
# opinionated part.
_UNCOVERED_MIN_PATCH_MM2 = 5.0

# Fraction of a run's direction changes that must reverse (turn past 120 deg)
# before the run is read as a satin COLUMN rather than a path. A column lays
# two legs per same-rail advance, so its ribbons are counted half-weight —
# see `_column_weight`. Measured on both fixtures after ties and split
# penetrations are stripped: every satin run reads 1.00, and the busiest
# non-column run (a bean outline retracing its own ring) reads 0.47. 0.75
# sits in the middle of that gap with room on both sides.
_COLUMN_REVERSAL_MIN = 0.75

# --- Same-hole strikes, law 17 ----------------------------------------------

# Penetrations are binned at the DST grid (0.1 mm units) before repeats are
# counted, because that is the resolution the professional corpus was
# measured at and a strike is "the same hole" only if the file says so.
_SAME_HOLE_QUANTUM_MM = 0.1

# Points struck 2+ times, as a fraction of all penetrations. The professional
# baseline is 9.455% across the 36-file corpus (732,246 penetrations), and
# ALL 36 files contain 3+ stacked points; our own benchmark measures 9.8% —
# the same practice, not a defect (docs/machine-physics-playbook, "Field note
# — Law 17", 2026-08-01, which dismisses both charges against the engine).
# So this check exists only to catch a future regression, and the number is
# deliberately far above the baseline: 25% is 2.6x the corpus and 2.5x our
# own output. Below it the check must stay silent, because a stricter reading
# of law 17 "would condemn every satin column ever sewn, professional ones
# included". INFO severity for the same reason — it never costs score.
SAME_HOLE_RATE_MAX = 0.25

# Below this many samples a median is an anecdote; the metric stays silent
# rather than judging a design on a handful of stitches.
_MIN_SAMPLES = 30

# Sampled artwork pixels needed before a region's color is judged. A region
# smaller than this is mostly anti-alias boundary and the median is noise.
_MIN_COLOR_PIXELS = 50

# Cap on how many of a region's pixels are scored against its spool. The
# score is a median over per-pixel colour errors, which converges long
# before a real region runs out of pixels; the stride is even over raster
# order — deterministic, no RNG — the same idiom stage 4's thread
# revalidation and stage 2's k-means fit sample use, and for the same
# reason. Generous relative to stage 4's 256 because this scores ONE spool
# per region where stage 4 scores the whole ~400-spool chart.
_COLOR_SAMPLE_PX = 4096

# --- Photo guardrails (photo plan §2 row 15) ---------------------------------
#
# THE FACE-GATED REMAINDER — half CLOSED 2026-08-04:
#   * Face-size guard: BUILT (`_face_size_findings` below), exactly the way
#     this comment specified — the YuNet detection rides the pipeline the
#     way the classifier's verdict does (the PHOTO_FACES_DETECTED warning
#     from `pipeline.run_stages`, behind the photo_prep gate), and the check
#     re-reads it here rather than re-running a net. Thresholds at
#     FACE_MIN_HOOP_MM / FACE_BLOCK_HOOP_MM with their derivations.
#   * Nap-fabric water-soluble-topping line: STILL A SEAM — needs a fabric
#     nap signal that `fabrics.py` presets do not carry today (no `nap`
#     field exists). When a preset grows one, the check is one comparison
#     against `fabric_for(cfg)` plus a worksheet line, same shape as
#     STABILIZER_CUTAWAY below.
#
# Photo-class gate, measured 2026-08-04. Preflight has no class gate anywhere
# else and these two checks (resolution, subject contrast) still need one —
# that is a measurement, not a style choice. Raw input px/mm of every
# committed fixture at the suite's own sizes:
#
#   logo_whitebg @80        8.39      bg_uncertain @80       7.51
#   logo_alpha @80          8.38      ribbon_curve @80       8.78
#   drone_render @90        8.54      gradient_ramp_radial   6.40 @80
#   photo_*_stub @80       12.50      enthusiast_logo @80   17.05
#
# The flat and gradient lanes' own clean, sew-out-validated fixtures live
# UNDER the photo floor — a blanket 10 px/mm guard would flag the fixture
# logo whose zero-findings report every threshold in this module was
# validated against, and the drone render at its own acceptance size. The
# floor is a photo-class fact (Embird states it for photo input; the flat
# lane's floor is stage 1's own cfg.min_px_per_mm = 4 with its Lanczos
# rescue), so the guard reads the class the classifier already published
# rather than inventing a threshold that condemns clean flat work.

# Input resolution floor for photo-class stitching, in source pixels per
# output millimetre: below it the tonal tiers sample noise-scale detail.
# [P — Embird, via docs/photo-digitizing-plan-2026-07-31.md §1(c) hard
# floors: "input >= 10 px per output mm"]. Measured against the raster the
# INPUT delivered (`Prep.input_px_per_mm`), never the post-upscale value —
# stage 1's Lanczos rescue manufactures pixels, not information.
PHOTO_MIN_PX_PER_MM = 10.0

# How far the subject's lightness must sit from the background's before the
# subject reads in thread at all — photo-class only: a photo tier renders
# TONE, so a subject iso-luminant with its background is invisible to it
# (plan §1(d) lists "separating an iso-luminant subject from its background
# without a user click" as impossible), while a flat logo sews its actual
# hue and vanishes nowhere. The instrument is the p90 of per-foreground-
# pixel |L* - median L*(background)| (house Lab convention, threads.py) —
# p90, not the median, because a subject reads by its most-contrasting
# parts: the white icon on the mid-gray gradient fixture
# (repro_gradient_white_icon) measures p50 = 3.99 but p90 = 50.1, and the
# icon reads fine. Measured 2026-08-04 over every committed fixture with an
# opaque detected background vs a constructed iso-luminant negative (a
# (200,60,60) red subject on the (0,130,0) green whose L* matches to 0.16):
#
#   happy fixtures, p90       27.58 - 82.52   (floor: photo_scene_stub)
#   iso-luminant negative     p90 0.16, p99 2.95
#
# Two populations with nothing between 2.95 and 27.58; 10 sits in the gap
# with 3.4x room on the negative side and 2.8x on the clean side. Alpha
# cutouts decline (`Prep.bg_from_alpha`): their background is the garment,
# whose color this pipeline cannot know.
SUBJECT_DELTA_L_MIN = 10.0

# Stitch count past which the worksheet prescribes cutaway stabilizer: a
# design this heavy needs permanent support or it distorts when the hoop
# comes off. [P — OESD, via docs/photo-digitizing-plan-2026-07-31.md §2 row
# 15: "est. > 25k st -> cutaway prescription on the worksheet"]. INFO, not a
# defect: the design sews fine — on the right stabilizer. The worksheet
# renderer (src/pdfsheet.js) carries the same 25k rule for designs that
# never pass through this service (lettering, imports, combined designs);
# change one and change both.
STITCHES_CUTAWAY_MIN = 25_000

# Color stops past which a single-needle machine's operator lives at the
# machine: every color change is a stop and a manual re-thread. Vendor
# single-needle defaults cap at ~10 stops, with multi-needle modes unlocking
# 15+ [docs/photo-digitizing-plan-2026-07-31.md §1 stitch budgets; vendor
# defaults corroborate, forum evidence unverifiable [CNV]]. Measured on the
# committed fixtures 2026-08-04: every flat/photo fixture plans 0-6 changes;
# the drone render at 90 mm plans 12 and DOES fire this — deliberately, not
# noise: that plan really is past the single-needle wall today, and the
# photo plan's own palette step (build step 7, chart-restricted k-medoids)
# is what brings photo-class palettes back inside it.
COLOR_STOPS_MAX = 10

# The face-size guard's two hoop constants (photo plan §1(c) hard floors +
# §2 row 15). The plan states both halves of the rule separately and this
# guard uses both:
#   * "face work needs a 5x7\" hoop minimum" [S — Brother's own guidance via
#     the plan] — FACE_MIN_HOOP_MM names that floor in the finding's message
#     and extra, so the operator is told what to size UP to.
#   * "Impossible: ... Faces at 4x4\"" [plan §1(c)] — FACE_BLOCK_HOOP_MM is
#     the trigger: the finding fires (block — the plan's row 15 says block,
#     with a size-up suggestion) when the whole design FITS a 4x4" hoop,
#     because a design that small cannot be using anything approaching the
#     5x7 minimum, and the plan calls faces at that scale impossible
#     outright. A design between the two hoops (say 120x80 mm) already
#     NEEDS a hoop bigger than 4x4 — the 5x7 — so the stated minimum is
#     met and the guard stays silent; blocking there would flag work the
#     plan itself calls viable.
# Faces are read from the PHOTO_FACES_DETECTED warning (pipeline.run_stages,
# YuNet — plan step 3's face priors), which only exists when the photo_prep
# gate held, so this guard needs no class gate of its own: no photo lane, no
# warning, no finding.
FACE_MIN_HOOP_MM = (127.0, 178.0)     # 5x7" hoop, the stated face-work floor
FACE_BLOCK_HOOP_MM = 101.6            # 4x4" hoop (4 * 25.4mm/in) — faces at this scale: impossible

# The pipeline warning the face guard re-reads — named by string, the
# _CONTOUR_RING_UNREACHABLE / _CLASSIFIED_PHOTO pattern (that code is owned
# by warnings_codes.py, emitted by pipeline.run_stages).
_PHOTO_FACES_DETECTED = "PHOTO_FACES_DETECTED"

# Score deductions. A block is most of a letter grade on its own; two warns
# cost one. Grades: A >= 90, B >= 75, C >= 60, D >= 40, F below.
_DEDUCT = {"info": 0, "warn": 12, "block": 30}


def finding(code: str, severity: str, message: str, **extra) -> dict:
    """Same shape as warnings_codes.warn, plus severity — one report row."""
    out = {"code": code, "severity": severity, "message": message}
    if extra:
        out["extra"] = extra
    return out


# --- Thread color fidelity --------------------------------------------------

def _region_color_errors(p, result: PipelineResult,
                         cfg: PipelineConfig) -> list[dict]:
    """-> per-region colour error rows, one per scoreable region:
    {shape_id, thread_index, delta_e, artwork_rgb}.

    Each region is scored against ITS OWN pixels and ITS OWN spool — never
    pooled across the regions sharing a thread. Pooling was this
    instrument's original sin, documented twice in docs/photo-quality-root-
    cause-2026-08-11.md: the per-channel median of a bimodal pool is a
    colour almost no pixel carries, and a fix that improves one region moves
    the pool it leaves, so the pooled number can worsen across a genuine
    improvement (drone_render: pooled 9.2 -> 33.6 while the per-region
    worst halved, 20.99 -> 10.64).

    The pipeline does not carry the pre-snap cluster colors into its result,
    so the artwork is re-read through stage 1 (same config, deterministic,
    same alignment — `p` is that one shared re-read, made once in
    run_preflight for every check that needs the artwork) and each region
    polygon is rasterized back over it. Region coordinates are mm with
    origin at the artwork bbox CENTER, y-down — the exact inverse of the
    transform stage 4 applied — so px = mm * px_per_mm + center. The mask is
    eroded one pixel and background pixels are excluded, both to keep
    anti-alias halo pixels from dragging a flat color toward the background.

    `delta_e` is the MEDIAN OF THE PER-PIXEL CIEDE2000 to the region's
    assigned spool — the estimator stage 4's `revalidate_threads` settled on,
    for the reason its docstring measures: a drifted or gradient region is
    bimodal, and any statistic that collapses it to one colour FIRST (mean
    Lab, median RGB) reports the defect as absent (the traced sliver: mean
    says 5.54, the pixels say 23.87). `artwork_rgb` is still the region's
    per-channel median RGB, but it is a display swatch for the finding —
    never what the score is computed from.
    """
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.rgb.shape[:2]
    chart = chart_for(cfg)

    rows: list[dict] = []
    for r in result.regions:
        mask = np.zeros((h, w), np.uint8)

        def to_px(coords) -> np.ndarray:
            a = np.asarray(coords, np.float64)
            return np.column_stack(
                [a[:, 0] * p.px_per_mm + cx, a[:, 1] * p.px_per_mm + cy]
            ).astype(np.int32)

        cv2.fillPoly(mask, [to_px(r.polygon.exterior.coords)], 1)
        for ring in r.polygon.interiors:
            cv2.fillPoly(mask, [to_px(ring.coords)], 0)
        eroded = cv2.erode(mask, np.ones((3, 3), np.uint8))
        sel = (eroded > 0) & (~p.bg_mask)
        if not sel.any():
            sel = (mask > 0) & (~p.bg_mask)   # hairline shape: erosion ate it
        px = p.rgb[sel].reshape(-1, 3)
        if len(px) < _MIN_COLOR_PIXELS:
            continue
        if len(px) > _COLOR_SAMPLE_PX:
            idx = np.linspace(0, len(px) - 1, _COLOR_SAMPLE_PX).astype(np.int64)
            px = px[idx]
        lab_px = rgb_to_lab(px.astype(np.float64))
        lab_thr = chart.lab[r.thread_index].reshape(1, 3)
        rows.append({
            "shape_id": r.shape_id,
            "thread_index": r.thread_index,
            "delta_e": float(np.median(deltaE_ciede2000(lab_px, lab_thr))),
            "artwork_rgb": [int(v) for v in np.median(px, axis=0)],
            "_lab_px": lab_px,
        })
    return rows


def _best_loaded_spool_error(lab_px: np.ndarray, loaded: list[int],
                             chart) -> tuple[float, int]:
    """Smallest region error reachable WITHOUT loading a new cone: the best
    `delta_e` over the spools this design already sews -> (error, spool).

    Scored with `_region_color_errors`' own estimator — the median of the
    per-pixel CIEDE2000 — recomputed per candidate spool rather than as a
    distance between summary colours. That is not incidental: the region
    docstring measures the failure of collapsing first (a bimodal sliver's
    mean says 5.54 where its pixels say 23.87), and a floor computed the
    cheap way would sit below every assigned error by construction and
    manufacture excess that is not there.

    `loaded` is the set of spools this design's own REGIONS sew — precisely,
    not loosely: on an unbound photo route the machine loads more than that,
    because the per-shade snap can pull in spools no region claims. Scoring
    against the narrower set is the conservative direction (a smaller
    candidate set can only raise the floor and lower the excess), so the
    rescoring can still only fire when a strictly free swap was available
    and was not taken.
    """
    best_err, best_spool = float("inf"), loaded[0]
    for spool in loaded:
        err = float(np.median(deltaE_ciede2000(
            lab_px, chart.lab[spool].reshape(1, 3))))
        if err < best_err:
            best_err, best_spool = err, spool
    return best_err, best_spool


def _thread_match_findings(p, result: PipelineResult, plan: StitchPlan,
                           cfg: PipelineConfig) -> tuple[list[dict], float | None]:
    """One finding per thread with a region visibly off that spool's colour,
    judged by the thread's WORST region — per-region, never pooled (the
    derivation and both measured failure cases are on `_region_color_errors`).

    Distance is CIEDE2000 on CIELAB from skimage's rgb2lab on [0, 1] floats
    — the pinned house convention (threads.py), never cv2's 8-bit Lab.

    Aggregation is per THREAD rather than one finding per bad region, and
    that is a scoring decision: the operator's remedy (pick a closer spool,
    or split the artwork's colours) is per spool, and a busy photo plan with
    one badly-served thread across five regions is one problem, not five.
    The finding carries every offending region in `extra.regions` (worst
    first) so the review screen can point at all of them, and the second
    return value — the worst per-region error across the whole design,
    offender or not — rides out as `thread_worst_delta_e`, the number to
    watch across a re-digitize.
    """
    rows = _region_color_errors(p, result, cfg)
    chart = chart_for(cfg)
    findings: list[dict] = []
    worst: float | None = None
    by_thread: dict[int, list[dict]] = {}
    for row in rows:
        worst = row["delta_e"] if worst is None else max(worst, row["delta_e"])
        by_thread.setdefault(row["thread_index"], []).append(row)

    # The photo route is scored on EXCESS over the best already-loaded spool,
    # not on raw distance (2026-08-24). Reducing a photograph to a capped cone
    # list guarantees per-thread distance: on the 32-job acceptance sheet this
    # check fired 256 times at `block`, so every photo job any user ran graded
    # F / "do not sew" — the same shape as the DENSITY_EXTREME misfire fixed in
    # PR #216, and the same fix: change the yardstick, not the check.
    #
    # Measured in-pipeline before it was written, which is what settled the
    # design: over the four acceptance portraits' 330 regions, raw distance
    # puts 258 past DELTA_E_VISIBLE and 103 past DELTA_E_CLEARLY_DIFFERENT,
    # while excess puts 3 and 1 there — 277 of 330 already wear the closest
    # cone the design loads. The survivors are real and still fire (worst,
    # baby_deck_laugh: 13.18 dE00 of excess, a spool sitting loaded and that
    # much closer), which is why this rescores instead of exempting a class.
    # The module header carries the full per-photo table.
    #
    # An earlier scratchpad pass put the unbound arm's median excess at 4.19
    # and its worst at 22.60. Those numbers were wrong and are recorded here
    # so they are not re-derived: they compared median RGBs, which is the
    # collapse-first mistake `_region_color_errors` measures directly above.
    # The bind also turns out not to move this check at all — bound and
    # unbound score identically, because the escape it closes lives in the
    # shade BLOCKS while this reads `result.regions`.
    #
    # `len(loaded) > 1` guards the degenerate design: with a single cone there
    # is no alternative to be closer, every excess is 0 by construction, and
    # the check would go permanently silent instead of reporting an honestly
    # unreachable colour.
    photo = _is_photo_class(plan, cfg)
    loaded = sorted(by_thread)

    for t, t_rows in sorted(by_thread.items()):
        # `score` is what the thresholds judge; `delta_e` stays the reported
        # distance either way, so the operator still sees the true colour gap.
        for r in t_rows:
            # Strict early-out, not an approximation: the floor is a distance,
            # so it is >= 0 and excess <= raw. A region already inside
            # DELTA_E_VISIBLE therefore cannot become an offender under either
            # yardstick, and searching the cone list for it is pure cost —
            # 39 of baby_deck_laugh's 110 regions, 35% of the work.
            if photo and len(loaded) > 1 and r["delta_e"] > DELTA_E_VISIBLE:
                best_err, best_spool = _best_loaded_spool_error(
                    r["_lab_px"], loaded, chart)
                r["_score"] = max(0.0, r["delta_e"] - best_err)
                r["_alt"] = best_spool
            else:
                r["_score"] = r["delta_e"]
                r["_alt"] = None

        offenders = sorted((r for r in t_rows if r["_score"] > DELTA_E_VISIBLE),
                           key=lambda r: -r["_score"])
        if not offenders:
            continue
        top = offenders[0]
        thread = chart[t]
        clearly = top["_score"] > DELTA_E_CLEARLY_DIFFERENT
        what = "is clearly a different color than" if clearly else "is visibly off"
        n = len(offenders)
        where = (f"the shape it sews ({top['shape_id']})" if len(t_rows) == 1
                 else f"{n} of the {len(t_rows)} shapes it sews "
                      f"(worst: {top['shape_id']})")
        if top["_alt"] is not None:
            alt = chart[top["_alt"]]
            remedy = (f"{alt.number} ({alt.name}) is already loaded for this "
                      f"design and matches it better — reassign before sewing.")
        else:
            remedy = "Pick a closer thread or a different brand before sewing."
        findings.append(finding(
            THREAD_MATCH_POOR,
            "block" if clearly else "warn",
            f"{chart.label} {thread.number} ({thread.name}) {what} "
            f"{where}. {remedy}",
            brand_id=chart.id,
            thread_number=thread.number,
            thread_name=thread.name,
            delta_e=round(top["delta_e"], 1),
            # Present only on the rescored route, so a reader can tell which
            # yardstick produced the severity without inferring it.
            excess_delta_e=(None if top["_alt"] is None
                            else round(top["_score"], 1)),
            better_spool=(None if top["_alt"] is None else alt.number),
            worst_shape_id=top["shape_id"],
            region_count=n,
            regions_scored=len(t_rows),
            # Offenders are ORDERED by whichever yardstick judged them, so on
            # the photo route each entry carries its excess too — otherwise
            # the list reads as unsorted by the only number it shows.
            regions=[{"shape_id": r["shape_id"],
                      "delta_e": round(r["delta_e"], 1),
                      **({} if r["_alt"] is None
                         else {"excess_delta_e": round(r["_score"], 1)})}
                     for r in offenders],
            artwork_rgb=top["artwork_rgb"],
            thread_rgb=list(thread.rgb),
        ))
    return findings, worst


# --- Photo guardrails (photo plan §2 row 15) ---------------------------------
# The buildable-today subset. The two face/fabric-gated guards this family
# still owes are documented at the threshold block above ("THE FACE-GATED
# REMAINDER") with the seam each plugs into.

def _is_photo_class(plan: StitchPlan, cfg: PipelineConfig) -> bool:
    """Did stage 0 route this design down the photo path?

    A forced class writes no classifier warning, so cfg wins; otherwise the
    classifier's own published verdict is re-read from plan.warnings, the
    `_contour_findings` pattern. CLASSIFICATION_UNCERTAIN designs fell back
    to flat and correctly read False here.
    """
    if cfg.is_photographic is not None:
        return bool(cfg.is_photographic)
    if cfg.forced_class in PHOTO_CLASSES:
        return True
    return any(w.get("code") in _CLASSIFIED_PHOTO for w in plan.warnings)


def _photo_resolution_findings(p, plan: StitchPlan,
                               cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """Photo-class input below Embird's 10 px per output mm floor.

    Reads `Prep.input_px_per_mm` — the resolution the INPUT delivered, before
    stage 1's Lanczos rescue inflates `px_per_mm` — because upscaling
    manufactures pixels, not detail, and the question here is whether the
    source resolves what the tonal tiers will try to sample. The metric rides
    out for every class; the finding is photo-gated (see the threshold
    block's measured table: the flat lane's own clean fixtures live under
    this floor and sew fine — their floor is stage 1's cfg.min_px_per_mm).
    """
    px = float(p.input_px_per_mm)
    metrics = {"input_px_per_mm": round(px, 2)}
    if not _is_photo_class(plan, cfg) or px >= PHOTO_MIN_PX_PER_MM:
        return [], metrics
    return [finding(
        PHOTO_RESOLUTION_LOW,
        "warn",
        f"The photo has {px:.1f} pixels per output millimetre — photo-style "
        f"stitching needs at least {PHOTO_MIN_PX_PER_MM:g}. Use a larger "
        "source image or make the design smaller.",
        px_per_mm=round(px, 2),
        min_px_per_mm=PHOTO_MIN_PX_PER_MM,
    )], metrics


def _subject_contrast_findings(p, plan: StitchPlan,
                               cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """A photo subject whose lightness sits on its background's: it will not
    read in thread, because the photo tiers render tone and an iso-luminant
    subject has none to render.

    The instrument is the p90 of per-foreground-pixel |L* - median
    L*(background)| — derivation and the measured fixture-vs-negative table
    at SUBJECT_DELTA_L_MIN. It declines honestly, with the metric None, in
    the three cases where "the background's lightness" is not a fact it
    holds: no background detected, an alpha-cutout background (the garment's
    color, unknowable here — `Prep.bg_from_alpha`), or too few pixels on
    either side to call a median. The metric rides out for every class the
    instrument can measure; the finding is photo-gated, because a flat logo
    sews its actual hue and vanishes nowhere.
    """
    metrics: dict = {"subject_bg_delta_l": None}
    if p.bg_from_alpha or not p.bg_mask.any():
        return [], metrics
    fg = ~p.bg_mask
    if int(p.bg_mask.sum()) < _MIN_COLOR_PIXELS or int(fg.sum()) < _MIN_COLOR_PIXELS:
        return [], metrics
    l_bg = float(np.median(
        rgb_to_lab(p.rgb[p.bg_mask].reshape(-1, 3).astype(np.float64))[:, 0]))
    dl = np.abs(
        rgb_to_lab(p.rgb[fg].reshape(-1, 3).astype(np.float64))[:, 0] - l_bg)
    p90 = float(np.percentile(dl, 90))
    metrics["subject_bg_delta_l"] = round(p90, 2)
    if not _is_photo_class(plan, cfg) or p90 >= SUBJECT_DELTA_L_MIN:
        return [], metrics
    return [finding(
        SUBJECT_CONTRAST_LOW,
        "warn",
        "The subject is nearly the same lightness as its background, so it "
        "will vanish in thread — photo stitching renders light and dark, "
        "not hue. Increase the photo's contrast, or remove the background "
        "before digitizing.",
        delta_l=round(p90, 2),
        min_delta_l=SUBJECT_DELTA_L_MIN,
        bg_lightness=round(l_bg, 1),
    )], metrics


def _face_size_findings(plan: StitchPlan) -> tuple[list[dict], dict]:
    """A detected face in a design small enough to fit a 4x4" hoop — the
    scale the photo plan calls impossible for face work (§1(c); constants
    and both hoop derivations at FACE_MIN_HOOP_MM above).

    Faces ride in on the PHOTO_FACES_DETECTED warning the pipeline emitted
    (the `_contour_findings` re-read pattern: the stage that ran the
    detector says what it found in its own warning, preflight carries that
    to the operator rather than re-running a net on a plan that may no
    longer have its artwork). `faces_detected` rides out in the metrics
    either way, so a photo job's report says whether detection saw anything
    even when nothing fires."""
    hits = [w for w in plan.warnings if w.get("code") == _PHOTO_FACES_DETECTED]
    count = sum(int(w.get("count", 1) or 1) for w in hits)
    metrics = {"faces_detected": count}
    if not count:
        return [], metrics
    d1, d2 = sorted(float(v) for v in plan.design_size_mm)
    if d2 > FACE_BLOCK_HOOP_MM:
        return [], metrics
    noun = "A face is" if count == 1 else f"{count} faces are"
    return [finding(
        FACE_TOO_SMALL,
        "block",
        f"{noun} in this design, but at {plan.design_size_mm[0]:.0f} x "
        f"{plan.design_size_mm[1]:.0f} mm it fits a 4x4\" hoop — face "
        f"embroidery needs at least a 5x7\" hoop "
        f"({FACE_MIN_HOOP_MM[0]:g} x {FACE_MIN_HOOP_MM[1]:g} mm) of design "
        "to hold facial detail. Size the design up before sewing.",
        count=count,
        design_mm=[round(float(v), 1) for v in plan.design_size_mm],
        fits_hoop_mm=FACE_BLOCK_HOOP_MM,
        min_hoop_mm=list(FACE_MIN_HOOP_MM),
    )], metrics


# --- Class override vs. technique mismatch -----------------------------------
#
# `cfg.forced_class` (photo plan's escape hatch — `stage0_classify.classify`
# skips signal computation entirely and returns the forced verdict at
# confidence 1.0) is a legitimate power-user move: stage 0's 4-way router is
# a plain thresholded tree on three signals (see that module's own
# docstring), and any real classifier has a genuine gray zone where the
# operator's own judgment beats the heuristic. Forcing "gradient" on a
# design the router itself would call "flat" (or vice versa) is exactly
# that judgment call and deserves no finding on its own.
#
# What DOES deserve a finding: a forced class paired with a `fill_technique`
# that only makes sense on photo-tonal content. The mono/tonal fill tiers
# (`stage6_scanline`, `stage6_meander`, `stage6_streamline`, and the sketch
# preset built on streamline — `stage6_sketch.py`) all read `SourcePixels`
# raster darkness, a signal that means something on a photographic tonal
# range and very little on flat spot-color art forced into a photo-shaped
# lane. `CLASS_OVERRIDE_TECHNIQUE_MISMATCH` fires when BOTH hold: the design
# would classify differently on its own (so the override is doing real
# work, not just re-confirming what the router already thought) AND one of
# these techniques is selected. WARN, not BLOCK: forcing a class is a
# supported override, not a mistake by itself — the warning exists so the
# combination is visible before sewing, not to stop it.
_PHOTO_TONAL_TECHNIQUES = ("streamline", "scanline_tonal", "meander_tonal", "sketch")


def _class_override_findings(image, cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """`cfg.forced_class` disagreeing with the unforced classifier's own
    verdict, while a photo-tonal `fill_technique` is selected — see the
    threshold block above this function for the full reasoning.

    Needs the artwork (re-reads it through `stage0_classify.classify`, the
    same "no image, skip and say so" convention `_photo_resolution_findings`
    / `_thread_match_findings` use) and only actually runs that second
    classification when there is something to disagree about: no
    `forced_class` set, or a `fill_technique` outside the photo-tonal list,
    means nothing here can mismatch and the unforced classifier — the one
    signal-computation cost this check would otherwise add to every forced
    job — is never invoked.
    """
    metrics: dict = {"class_override_detected_class": None}
    technique = (cfg.fill_technique or "tatami").lower()
    if image is None or not cfg.forced_class or technique not in _PHOTO_TONAL_TECHNIQUES:
        return [], metrics
    unforced = classify(image, cfg, forced_class=None)
    metrics["class_override_detected_class"] = unforced.class_
    if unforced.class_ == cfg.forced_class:
        return [], metrics
    return [finding(
        CLASS_OVERRIDE_TECHNIQUE_MISMATCH,
        "warn",
        f'This design is forced to classify as "{cfg.forced_class}", but '
        f'reads as "{unforced.class_}" on its own, and the selected fill '
        f'technique ("{technique}") assumes photo-tonal content. Forcing '
        "the class is fine if that is what you intended — just confirm the "
        "result looks right before sewing.",
        forced_class=cfg.forced_class,
        detected_class=unforced.class_,
        fill_technique=technique,
    )], metrics


def _stabilizer_findings(plan: StitchPlan) -> list[dict]:
    """The cutaway prescription for a heavy design [P — OESD, via the photo
    plan §2 row 15]. INFO: nothing is wrong with the file — the operator
    just has to hoop the right stabilizer under it, and the worksheet is
    where that instruction lives (src/pdfsheet.js carries the twin rule for
    designs that never pass through this service)."""
    count = plan.stats.stitch_count
    if count <= STITCHES_CUTAWAY_MIN:
        return []
    return [finding(
        STABILIZER_CUTAWAY,
        "info",
        f"{count:,} stitches — over {STITCHES_CUTAWAY_MIN:,}, use cutaway "
        "stabilizer: tear-away releases under this much thread and the "
        "design distorts when the hoop comes off.",
        stitch_count=count,
        threshold=STITCHES_CUTAWAY_MIN,
    )]


def _color_stop_findings(plan: StitchPlan) -> tuple[list[dict], int]:
    """Color stops past the single-needle wall (COLOR_STOPS_MAX has the
    derivation and the measured fixture counts). Counted from plan.stats —
    every block boundary is a machine stop and, on a single needle, a manual
    re-thread."""
    changes = plan.stats.color_changes
    if changes <= COLOR_STOPS_MAX:
        return [], changes
    return [finding(
        COLOR_STOPS_HEAVY,
        "warn",
        f"{changes} thread changes — a single-needle machine stops for a "
        f"manual re-thread at every one, and past {COLOR_STOPS_MAX} that is "
        "an afternoon at the machine. Merge similar colors, or sew this on "
        "a multi-needle machine.",
        color_changes=changes,
        max_stops=COLOR_STOPS_MAX,
    )], changes


# --- Lettering size ---------------------------------------------------------

def _lettering_findings(plan: StitchPlan) -> tuple[list[dict], int]:
    """Satin shapes below sewable lettering size, aggregated to one finding.

    Column width is the median consecutive-step distance inside the shape's
    SATIN runs — every consecutive pair of an emitted zigzag crosses the
    column (the return leg leans one 0.4 mm spacing forward, which inflates a
    0.9 mm column to 0.99; negligible). Never sliced at fixed parity — the
    playbook's parity trap. "Too small overall" is the LARGER bbox dimension
    under 4 mm: a shape that fits entirely inside a 4 mm box is below
    lettering scale in any orientation, while a long thin dash (4 x 1 mm,
    perfectly sewable) stays out of the net.
    """
    widths: dict[str, list[float]] = {}
    pts_by_shape: dict[str, list[tuple[float, float]]] = {}
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN:
            continue
        for a, b in zip(run.points, run.points[1:]):
            widths.setdefault(run.shape_id, []).append(math.dist(a, b))
        pts_by_shape.setdefault(run.shape_id, []).extend(run.points)

    small: list[dict] = []
    for sid, ws in sorted(widths.items()):
        ws.sort()
        med = ws[len(ws) // 2]
        xs = [p[0] for p in pts_by_shape[sid]]
        ys = [p[1] for p in pts_by_shape[sid]]
        extent = max(max(xs) - min(xs), max(ys) - min(ys))
        if med < MIN_COLUMN_MM or extent < MIN_LETTER_EXTENT_MM:
            small.append({"shape_id": sid, "column_mm": round(med, 2),
                          "extent_mm": round(extent, 1)})
    if not small:
        return [], len(widths)
    n = len(small)
    total = len(widths)
    noun = "shape" if n == 1 else "shapes"

    # The denominator is the point of this line. "38 satin shapes are too
    # small" reads like a handful of stray specks to trim; "38 of 46" says the
    # wordmark itself does not fit, which is a different decision. It is also
    # the only summary here that stays honest across sizes -- see below.
    #
    # DELIBERATELY NOT a suggested size. "Enlarge the design" invites a
    # "to what?", and the arithmetic is trivial (MIN_COLUMN_MM / measured
    # column x current width), but the answer it produces is not real.
    # Measured on `photo/logo_hotel_fremont.webp` at 92.5 / 120 / 165 / 220 mm
    # (2026-08-21):
    #
    #   width   flagged/total   worst col   median col   "needed" width
    #    92.5        38/46        0.56         0.80           258
    #   120          27/47        0.62         0.80           367
    #   165          25/56        0.52         0.94           697
    #   220          13/63        0.66         0.79           397
    #
    # The flagged COUNT falls honestly (38 -> 13). But the worst column has no
    # trend at all, and the median flagged column is FLAT near 0.8 mm at every
    # size: segmentation keeps generating sub-millimetre shapes as the design
    # grows (satin total 46 -> 63 over the same range), so the failing tail
    # refills itself and never empties. A worst-shape-driven target therefore
    # swings 258 -> 697 -> 397 mm and is dominated by whichever sliver landed
    # on the knife edge -- the same instability the spur-prune multiplier hit
    # (see `.claude/memory/satin-extremity-drop-and-coverage-check.md`).
    # Quoting any of those numbers as "enlarge to this" would be inventing a
    # target the engine cannot hit. If a suggested size is ever wanted, it has
    # to come from a measurement that is stable under rescaling; this one is
    # not.
    return [finding(
        LETTERING_TOO_SMALL,
        "warn",
        f"{n} of {total} satin {noun} sew below readable size at this scale — "
        f"columns under {MIN_COLUMN_MM:g} mm or details under "
        f"{MIN_LETTER_EXTENT_MM:g} mm. Enlarging helps but does not fully "
        f"clear it: the smallest shapes regenerate at any size. Remove or "
        f"simplify the smallest lettering.",
        count=n,
        satin_total=total,
        shapes=small,
    )], len(widths)


# --- Stitch length ----------------------------------------------------------

def _stitch_length_findings(plan: StitchPlan) -> tuple[list[dict], dict]:
    """The format ceiling as a backstop, and the satin-short fraction.

    A plan should never contain a needle-down step past MAX_STITCH_MM — the
    planner splits them at the source — so any count here is a regression
    report, not a normal state. The short fraction is a quality score even
    when it stays under threshold; it rides out in the metrics.
    """
    too_long = 0
    longest = 0.0
    satin_total = satin_short = 0
    for _b, run in plan.iter_runs():
        for a, b in zip(run.points, run.points[1:]):
            d = math.dist(a, b)
            if d > machine.MAX_STITCH_MM + 1e-6:
                too_long += 1
                longest = max(longest, d)
            if run.kind == stitches.SATIN:
                satin_total += 1
                if d < machine.MIN_STITCH_MM:
                    satin_short += 1

    findings: list[dict] = []
    if too_long:
        noun = "stitch" if too_long == 1 else "stitches"
        findings.append(finding(
            STITCHES_TOO_LONG,
            "warn",
            f"{too_long} {noun} exceed the {machine.MAX_STITCH_MM:g} mm "
            "machine ceiling. Export splits them so the file will run, but "
            "the plan should not contain them — re-run digitizing and "
            "report this design.",
            count=too_long,
            max_mm=round(longest, 2),
        ))
    frac = satin_short / satin_total if satin_total else 0.0
    if satin_total >= _MIN_SAMPLES and frac > SATIN_SHORT_FRACTION_MAX:
        findings.append(finding(
            STITCHES_TOO_SHORT,
            "warn",
            f"{frac:.0%} of satin stitches are under the "
            f"{machine.MIN_STITCH_MM:g} mm needle minimum (a healthy plan "
            "runs about 10%). Thread breaks are likely — enlarge the design "
            "or thicken its thinnest strokes.",
            fraction=round(frac, 3),
            count=satin_short,
            total=satin_total,
        ))
    return findings, {"satin_short_fraction": round(frac, 3),
                      "satin_steps": satin_total}


# --- Trims ------------------------------------------------------------------

def _trim_findings(plan: StitchPlan) -> tuple[list[dict], float]:
    """Trims per 1,000 stitches against the professional corpus.

    The plan marks the first run of every color block as trimmed, but the
    first block of the design has no thread to cut yet, so the FILE contains
    one trim fewer than plan.stats reports (the same correction the service's
    stats payload makes). The rate uses what the machine will actually do.
    """
    s = plan.stats
    first = plan.blocks[0].runs[0] if plan.blocks and plan.blocks[0].runs else None
    trims = s.trims - (1 if first is not None and first.trim else 0)
    per_1000 = 1000.0 * trims / s.stitch_count if s.stitch_count else 0.0
    if per_1000 <= TRIMS_PER_1000_MAX or s.stitch_count < _MIN_SAMPLES:
        return [], per_1000
    return [finding(
        TRIM_HEAVY,
        "warn",
        f"{per_1000:.1f} trims per 1,000 stitches — professional files run "
        "0.1 to 4.1. Each cut is 2-3 seconds of machine time; consider "
        "merging or removing the smallest shapes.",
        per_1000=round(per_1000, 1),
        trims=trims,
        stitches=s.stitch_count,
    )], per_1000


# --- Density ----------------------------------------------------------------

def _fill_row_advance_mm(plan: StitchPlan) -> tuple[float | None, float | None]:
    """-> (median row-to-row advance of the emitted fill, best fill axis |R|).

    The advance is None when the plan holds no fill, and — since 2026-08-02 —
    also when no fill run is ROWS: see `_FILL_AXIS_MIN`. A contour fill's rings
    have no dominant axis, and this instrument answers confidently and wrongly
    on them, so it now declines instead. The concentration rides out beside the
    advance so a caller can tell "no fill" from "fill this cannot measure".

    A fill run is rows along one dominant axis with short turns between
    them. Each run's axis is recovered from its own steps (length-weighted
    axial mean — the angle-doubling trick, so a boustrophedon's opposite
    row directions reinforce instead of cancelling); a step within 45 deg of
    that axis is sewing along a row, anything else is a transition, and the
    transition's component PERPENDICULAR to the axis is the row advance. Two
    subtleties, both measured: the raw transition step is NOT the spacing
    (row ends ride the shape's edge — on a slanted edge it runs diagonally,
    median 1.07 mm on the fixture, nearly 3x the true 0.40), and comparing
    against the PREVIOUS step instead of the axis double-counts the first
    step of every row as a turn, which on a synthetic grid put the median on
    the wrong population entirely. Against the axis, the clean fixture reads
    0.400 mm on the 0.40 target. Median only — the tail holds column
    transitions and row skips, which are routing, not density.
    """
    adv: list[float] = []
    best_conc: float | None = None
    for _b, run in plan.iter_runs():
        if run.kind != stitches.FILL:
            continue
        pts = run.points
        if len(pts) < 3:
            continue
        # Length-weighted axial mean of the step directions.
        sx = sy = total = 0.0
        steps: list[tuple[float, float, float]] = []
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy)
            if d < 1e-9:
                continue
            ang = math.atan2(dy, dx)
            sx += d * math.cos(2 * ang)
            sy += d * math.sin(2 * ang)
            total += d
            steps.append((dx, dy, d))
        if not steps or total <= 0.0:
            continue
        # How much of that mean survived the averaging. Rows on one axis
        # reinforce (|R| -> 1); rings sweeping every direction cancel (-> 0).
        conc = math.hypot(sx, sy) / total
        best_conc = conc if best_conc is None else max(best_conc, conc)
        if conc < _FILL_AXIS_MIN:
            continue                       # not rows: this instrument declines
        axis = math.atan2(sy, sx) / 2.0
        ax, ay = math.cos(axis), math.sin(axis)
        for dx, dy, d in steps:
            if abs(dx * ax + dy * ay) / d >= math.cos(math.radians(45)):
                continue  # along a row
            perp = abs(dx * (-ay) + dy * ax)
            if perp > 1e-6:
                adv.append(perp)
    if len(adv) < _MIN_SAMPLES:
        return None, best_conc
    adv.sort()
    return adv[len(adv) // 2], best_conc


def _satin_rail_advance_mm(plan: StitchPlan) -> float | None:
    """Median same-rail advance of the emitted satin, or None without satin.

    Rails alternate A, B, A, B ... so two apart is the same rail — measured
    two-apart, never sliced at fixed parity (the playbook's parity trap).
    """
    adv: list[float] = []
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN:
            continue
        pts = run.points
        for i in range(len(pts) - 2):
            adv.append(math.dist(pts[i], pts[i + 2]))
    if len(adv) < _MIN_SAMPLES:
        return None
    adv.sort()
    return adv[len(adv) // 2]


# What each tonal fill tier means to lay down, as a (darkest, lightest) line
# spacing band in mm — the tiers' own producing constants, imported so this
# table cannot drift from what stage 6 sews. There is no single number to
# mirror the way the tatami target mirrors stage 7's formula: every tier here
# modulates its spacing by LOCAL IMAGE TONE across its band (streamline's
# `_d_sep`, scanline's stride ladder, meander's quadtree depths), so the
# design-wide median advance legitimately lands anywhere inside the band
# depending on how light the photo is.
#
# Measured, first real-portrait acceptance run (2026-08-23,
# debug_out/acceptance_2026-08-23 — the run that forced this table to exist):
# the photo auto-route (streamline) scored against the tatami target read
# "4.3x its 0.40 mm density target ... re-digitize before sewing" and cost a
# warn on every toggle-route job whose advance the instrument could measure —
# 9 of 12 (3 arms x 4 portraits; the other 3 declined the axis gate),
# measured 0.923-2.608 mm, every one INSIDE streamline's own 0.8-3.2 mm
# intent. The spec had already ruled the score non-authoritative on tonal
# work (docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md, decision
# 1); the warn TEXT was the live defect, telling every toggle-route user a
# correct thread-paint result needs re-digitizing.
#
# Per-tier edges, each read from the code that produces the spacing:
#   * streamline — `_d_sep`'s full range, dark to light.
#   * sketch — streamline's machinery with darkness attenuated
#     (SKETCH_DARKNESS_SCALE into the same `_d_sep` mapping): attenuation
#     moves spacing toward the light END of the same band, never outside it.
#   * scanline_tonal — the base row grid to its widest admitted stride.
#   * meander_tonal — the finest quadtree cell to the sparsest cell that
#     still SEWS (`_depth_grid`: darkness >= cutoff earns max_depth - 2);
#     the one coarser level (7.2 mm) is traveled, not stitched, so it is
#     no part of the sewn intent.
#
# Keys stay in lockstep with _PHOTO_TONAL_TECHNIQUES (pinned by test) — same
# membership, different job: that tuple gates the class-override check, this
# table is the density yardstick.
_TONAL_FILL_BAND_MM = {
    "streamline": (STREAMLINE_D_SEP_DARK_MM, STREAMLINE_D_SEP_LIGHT_MM),
    "sketch": (STREAMLINE_D_SEP_DARK_MM, STREAMLINE_D_SEP_LIGHT_MM),
    "scanline_tonal": (SCANLINE_ROW_MM,
                       SCANLINE_ROW_MM * max(SCANLINE_LEVEL_STRIDES)),
    "meander_tonal": (MEANDER_CELL_MM,
                      MEANDER_CELL_MM * 2 ** (MEANDER_COARSE_LEVELS - 1)),
}


def _tonal_fill_technique(plan: StitchPlan, cfg: PipelineConfig) -> str | None:
    """The tonal fill tier this plan actually sewed with, or None.

    Mirrors stage 7's own precedence (`plan_stitches`: `auto_tier or
    cfg.fill_technique`): an explicit `cfg.fill_technique` wins outright —
    including over a stale PHOTO_AUTO_TIER warning on a re-plan, where
    stage 7 re-resolves and the explicit choice sews. Only when cfg still
    reads "tatami" (`auto_photo_tier`'s own not-explicit gate) is the
    auto-route's published verdict re-read from plan.warnings, the
    `_contour_findings` pattern.
    """
    technique = (cfg.fill_technique or "tatami").lower()
    if technique == "tatami":
        for w in plan.warnings:
            if w.get("code") == _PHOTO_AUTO_TIER:
                technique = str(w.get("tier", "")).lower()
                break
    return technique if technique in _TONAL_FILL_BAND_MM else None


def _density_findings(plan: StitchPlan,
                      cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """Emitted density against the planner's own targets.

    The fill target mirrors stage 7's exact formula — (cfg.fill_row_mm or
    machine default) scaled by the fabric preset — so a deliberate density
    override or a towel preset never trips this. What trips it is the
    emitted geometry diverging from what the pipeline itself intended:
    beyond 1.5x sparse the fabric grins through the rows, beyond 1.5x dense
    it puckers.

    A tonal fill tier — the pipeline's own deliberate density decision,
    auto-routed or explicit (`_tonal_fill_technique`) — intends a BAND, not
    a number: spacing follows local image tone across `_TONAL_FILL_BAND_MM`
    (evidence at the table). The fill advance is scored against that band
    widened by the tatami target, because stage 7's never-drop ladder
    legally sews plain tatami rows inside a tonal design wherever a shape
    came back empty, so a median anywhere between the two intents is the
    pipeline doing what it said. The same 1.5x slack applies at both edges;
    past the light edge the tonal fill genuinely collapsed (gaps no tier
    intended), past the dark edge it matted. Satin is unaffected — no tonal
    tier emits satin.
    """
    fabric = fabric_for(cfg)
    fill_target = (cfg.fill_row_mm or machine.FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    satin_target = machine.SATIN_SPACING_MM
    tonal = _tonal_fill_technique(plan, cfg)

    fill_adv, fill_conc = _fill_row_advance_mm(plan)
    findings: list[dict] = []
    metrics: dict = {"fill_axis_concentration":
                     None if fill_conc is None else round(fill_conc, 3)}
    for kind, measured, target in (
        ("fill", fill_adv, fill_target),
        ("satin", _satin_rail_advance_mm(plan), satin_target),
    ):
        metrics[f"{kind}_advance_mm"] = None if measured is None else round(measured, 3)
        if measured is None:
            continue
        if kind == "fill" and tonal is not None:
            dark, light = _TONAL_FILL_BAND_MM[tonal]
            lo, hi = min(dark, target), max(light, target)
            if lo / DENSITY_RATIO_MAX <= measured <= hi * DENSITY_RATIO_MAX:
                continue
            edge = hi if measured > hi else lo
            ratio = measured / edge
            way = ("looser: expect gaps in the coverage" if ratio > 1
                   else "denser: expect the fabric to pucker")
            findings.append(finding(
                DENSITY_EXTREME,
                "warn",
                f"The fill stitching came out at {measured:.2f} mm line "
                f"spacing — outside the {lo:.2f}-{hi:.2f} mm range the "
                f"{tonal} fill sets from image tone, {way}. Check the "
                "density settings and re-digitize before sewing.",
                kind=kind,
                measured_mm=round(measured, 3),
                target_mm=round(edge, 3),
                ratio=round(ratio, 2),
                technique=tonal,
                band_mm=[round(lo, 3), round(hi, 3)],
            ))
            continue
        ratio = measured / target
        if 1.0 / DENSITY_RATIO_MAX <= ratio <= DENSITY_RATIO_MAX:
            continue
        way = ("looser: expect gaps in the coverage" if ratio > 1
               else "denser: expect the fabric to pucker")
        findings.append(finding(
            DENSITY_EXTREME,
            "warn",
            f"The {kind} stitching came out {ratio:.1f}x its "
            f"{target:.2f} mm density target, {way}. Check the density "
            "settings and re-digitize before sewing.",
            kind=kind,
            measured_mm=round(measured, 3),
            target_mm=round(target, 3),
            ratio=round(ratio, 2),
        ))
    return findings, metrics


# --- Per-region coverage (law 27) -------------------------------------------

def _column_weight(pts: list[tuple[float, float]]) -> float:
    """0.5 for a satin column, 1.0 for a path — the law-27 counting rule.

    Coverage is thread AREA over fabric area, but law 27's unit is not raw
    thread area: it is `0.4 / spacing` summed per layer, and for satin the
    spacing it means is the SAME-RAIL advance. A zigzag lays two legs between
    consecutive same-rail penetrations (A1->B1 square across, B1->A2 leaning
    forward), so its raw thread area is exactly twice `0.4 / advance`. Half
    weight restores the law's unit at any advance, and it has to: with full
    weight the playbook's own "safe classic stack" of underlay + fill + satin
    detail scores 3.2 instead of ~2.5 and trips its own warn line.

    Detection is geometric, not by run kind, so a zigzag UNDERLAY is counted
    as the column it is. Two strippings come first, and both are load-bearing
    (the playbook's parity traps):

      * `stitches.strip_ties` — stage 7 splices lock bounces INTO the runs
        they protect, and a bounce is a 180 deg reversal, which would push a
        short path over the reversal gate.
      * `stage6_satin.strip_splits` — a split satin's mid-cross penetrations
        make consecutive segments COLLINEAR, which drags a real column's
        reversal fraction down and would get it counted at double density.

    Measured after both: every satin run on both fixtures reads 1.00; the
    busiest path (a bean outline retracing its ring) reads 0.47.
    """
    rails = strip_splits(pts)
    if len(rails) < 4:
        return 1.0
    a = np.asarray(rails, np.float64)
    d = a[1:] - a[:-1]
    ln = np.hypot(d[:, 0], d[:, 1])
    ok = (ln[:-1] > 1e-9) & (ln[1:] > 1e-9)
    if ok.sum() < 3:
        return 1.0
    dot = (d[:-1, 0] * d[1:, 0] + d[:-1, 1] * d[1:, 1])[ok]
    cos = dot / (ln[:-1][ok] * ln[1:][ok])
    return 0.5 if float((cos < -0.5).mean()) >= _COLUMN_REVERSAL_MIN else 1.0


def _coverage_map(plan: StitchPlan,
                  cell_mm: float = machine.COVERAGE_CELL_MM
                  ) -> tuple[np.ndarray, tuple[float, float]] | None:
    """-> (units grid, (x0, y0) mm origin), or None for a plan with no thread.

    THE instrument for law 27. Every needle-down stitch in the whole plan —
    every block, every shape, underlay included — is rasterized as the ribbon
    of thread it actually lays: `machine.COVERAGE_THREAD_W_MM` wide, centred
    on the stitch, its area deposited into `cell_mm` cells and divided by cell
    area. The result is coverage UNITS: 1.0 is one full covering layer.

    The area comes from stitch geometry, never from region polygons, which is
    the whole point — a region's polygon says where an object is, not how much
    thread landed there, and a stacked-layer failure is invisible to any
    per-object measure. Ribbons SUM where they overlap, so underlay + fill +
    border on one patch of fabric adds up exactly as law 27 says it does.

    The attributions law 27 lists fall out of the one ribbon rule rather than
    being special-cased, which is why they can be checked against it:
      * fill at row spacing s -> ribbons tile, cell reads 0.40/s (1.0 at the
        0.40 mm default; measured 1.000 on the fixture);
      * satin at same-rail advance a -> two half-weight legs per advance,
        0.40/a over the column (measured 0.98 at a = 0.41);
      * zigzag underlay at 2.0 mm -> 0.20, which is law 28's stated
        "~0.1-0.2 units, not zero" reproduced from geometry alone;
      * a run or bean -> a thread-width ribbon, 0.40 units per pass spread
        over the 1.0 mm cell it crosses.

    Ties are excluded (`strip_ties`). A lock is 3.2 mm of thread bounced on
    one point — a point feature, not a region, and the field note on law 17
    settles that stacking it is professional practice, not a defect. Counting
    it here would put a false hotspot at the start and end of every shape.
    `SAME_HOLE_HEAVY` is where ties are answered.
    """
    segs: list[np.ndarray] = []
    wts: list[np.ndarray] = []
    for _b, run in plan.iter_runs():
        pts = stitches.strip_ties(run.points)
        if len(pts) < 2:
            continue
        a = np.asarray(pts, np.float64)
        segs.append(np.stack([a[:-1], a[1:]], axis=1))
        wts.append(np.full(len(a) - 1, _column_weight(pts)))
    if not segs:
        return None

    seg = np.concatenate(segs)                     # (N, 2, 2)
    w = np.concatenate(wts)
    d = seg[:, 1] - seg[:, 0]
    ln = np.hypot(d[:, 0], d[:, 1])
    keep = ln > 1e-9
    seg, w, d, ln = seg[keep], w[keep], d[keep], ln[keep]
    if not len(seg):
        return None

    thread_w = machine.COVERAGE_THREAD_W_MM
    x0 = float(seg[:, :, 0].min()) - thread_w
    y0 = float(seg[:, :, 1].min()) - thread_w
    nx = int(math.ceil((float(seg[:, :, 0].max()) + thread_w - x0) / cell_mm)) + 1
    ny = int(math.ceil((float(seg[:, :, 1].max()) + thread_w - y0) / cell_mm)) + 1

    # Sample each ribbon on a lattice: along the stitch at a quarter thread
    # width, and twice across it (each sample owning half the ribbon width).
    n = np.maximum(1, np.ceil(ln / machine.COVERAGE_SUBSAMPLE_MM).astype(np.int64))
    idx = np.repeat(np.arange(len(seg)), n)
    starts = np.concatenate([[0], np.cumsum(n)[:-1]])
    t = (np.arange(int(n.sum())) - np.repeat(starts, n) + 0.5) / n[idx]
    px = seg[idx, 0, 0] + d[idx, 0] * t
    py = seg[idx, 0, 1] + d[idx, 1] * t
    ux, uy = -d[idx, 1] / ln[idx], d[idx, 0] / ln[idx]      # unit normal
    # Thread area this sample carries, halved because two samples share it.
    area = (ln[idx] / n[idx]) * thread_w * w[idx] / 2.0

    grid = np.zeros(ny * nx, np.float64)
    for off in (-0.25 * thread_w, 0.25 * thread_w):
        cx = ((px + ux * off - x0) / cell_mm).astype(np.int64)
        cy = ((py + uy * off - y0) / cell_mm).astype(np.int64)
        np.clip(cx, 0, nx - 1, out=cx)
        np.clip(cy, 0, ny - 1, out=cy)
        grid += np.bincount(cy * nx + cx, weights=area, minlength=ny * nx)
    return grid.reshape(ny, nx) / (cell_mm * cell_mm), (x0, y0)


def _coverage_findings(plan: StitchPlan) -> tuple[list[dict], dict]:
    """Fabric carrying more layers than law 27's budget allows.

    The per-object density checks above cannot see this by construction: a
    fill at its correct spacing, an underlay at its correct spacing and a
    border at its correct spacing each pass, and the patch of fabric under all
    three still gets more thread than it can take. That stack is what puckers
    a garment or armours it into a plastic patch, and it is the defect this
    check exists for.

    Thresholds are `machine.COVERAGE_WARN_UNITS` / `COVERAGE_BLOCK_UNITS` —
    2.5 and 3.5, both [D] in the playbook and not primary-sourced. They fire
    on the area of CONNECTED patches at or over `_COVERAGE_MIN_PATCH_MM2`,
    never on a peak cell: clean work speckles over 2.5 wherever two satin
    columns join or a sub-5 mm shape is rescued with a triple run, and a
    check that reads those as pucker would flag both house fixtures.
    """
    empty = {"coverage_p50": None, "coverage_p95": None, "coverage_max": None,
             "coverage_area_mm2": None, "coverage_over_warn_mm2": 0.0,
             "coverage_over_block_mm2": 0.0}
    got = _coverage_map(plan)
    if got is None:
        return [], empty
    grid, _origin = got
    cell_area = machine.COVERAGE_CELL_MM ** 2
    covered = grid[grid >= _COVERAGE_FLOOR_UNITS]
    if not covered.size:
        return [], empty

    def patch_area_mm2(limit: float) -> float:
        """Area of the patches over `limit` that are big enough to act on."""
        mask = (grid >= limit).astype(np.uint8)
        if not mask.any():
            return 0.0
        _n, _lab, stats, _c = cv2.connectedComponentsWithStats(mask, connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA] * cell_area
        return float(areas[areas >= _COVERAGE_MIN_PATCH_MM2].sum())

    peak = float(grid.max())
    p95 = float(np.percentile(covered, 95))
    over_warn = patch_area_mm2(machine.COVERAGE_WARN_UNITS)
    over_block = patch_area_mm2(machine.COVERAGE_BLOCK_UNITS)
    metrics = {
        "coverage_p50": round(float(np.percentile(covered, 50)), 2),
        "coverage_p95": round(p95, 2),
        "coverage_max": round(peak, 2),
        "coverage_area_mm2": round(float(covered.size * cell_area), 1),
        "coverage_over_warn_mm2": round(over_warn, 1),
        "coverage_over_block_mm2": round(over_block, 1),
    }

    if over_block > 0.0:
        sev, limit, area = "block", machine.COVERAGE_BLOCK_UNITS, over_block
    elif over_warn > 0.0:
        sev, limit, area = "warn", machine.COVERAGE_WARN_UNITS, over_warn
    else:
        return [], metrics

    advice = ("Cut the bottom layer back where the top one covers it, or "
              "drop a layer." if sev == "block" else
              "Check that the layers there are meant to overlap.")
    return [finding(
        DENSITY_STACKED,
        sev,
        f"{area:.0f} mm2 of this design stacks more than {limit:g} layers "
        f"of thread on one patch of fabric (peak {peak:.1f}), counting "
        f"underlay, fill and outlines together. That much thread puckers the "
        f"garment and breaks needles. {advice}",
        peak_units=round(peak, 2),
        p95_units=round(p95, 2),
        over_warn_mm2=round(over_warn, 1),
        over_block_mm2=round(over_block, 1),
        cell_mm=machine.COVERAGE_CELL_MM,
    )], metrics


# --- Artwork the design meant to sew and did not ----------------------------

def _uncovered_findings(p, result: PipelineResult, plan: StitchPlan
                        ) -> tuple[list[dict], dict]:
    """Artwork a sewn region claims, that ends up with no thread on it.

    The gap this closes: every other check here measures a property of the
    stitches (how long, how dense, how stacked) or of one object in isolation.
    None of them asks whether the thread actually LANDED on the artwork, so a
    shape whose outline is correct, whose tier is correct, and which reports
    `stitched: true` can lose a whole limb and score clean. That is not
    hypothetical — `enthusiast_logo.png` drops the emblem's inward tab and a
    corner, and both `preflight` and the corpus scorecard called it an A.

    Ground truth is `polygon ∩ ink`, and both halves are load-bearing — see
    `_UNCOVERED_CELL_MM` for the false-positive class each one alone
    produces. "Covered" is `_coverage_map`'s own units grid at
    `_COVERAGE_FLOOR_UNITS`, so this check and `DENSITY_STACKED` are reading
    one instrument from opposite ends: that one says too many layers, this
    one says none.

    Regions with no runs at all are skipped — `SHAPES_LEFT_UNSEWN` already
    owns "planned but not sewn", and reporting the same area twice would
    double-count a deliberate hold-out.

    Needs the artwork, so it is skipped (metrics None) exactly like the
    thread-match check when `run_preflight` is called without an image.
    """
    empty = {"uncovered_checked": False, "uncovered_worst_mm2": None,
             "uncovered_total_mm2": None, "uncovered_wanted_mm2": None}
    got = _coverage_map(plan, cell_mm=_UNCOVERED_CELL_MM)
    if got is None:
        return [], empty
    grid, (gx0, gy0) = got
    covered = grid >= _COVERAGE_FLOOR_UNITS
    ny, nx = grid.shape

    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.bg_mask.shape

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        return np.column_stack(
            [a[:, 0] * p.px_per_mm + cx, a[:, 1] * p.px_per_mm + cy]
        ).astype(np.int32)

    sewn = {r.shape_id for _b, r in plan.iter_runs()}
    claimed = np.zeros((h, w), np.uint8)
    for r in result.regions:
        if r.shape_id not in sewn:
            continue
        cv2.fillPoly(claimed, [to_px(r.polygon.exterior.coords)], 1)
        for ring in r.polygon.interiors:
            cv2.fillPoly(claimed, [to_px(ring.coords)], 0)

    wanted_px = ((claimed > 0) & (~p.bg_mask)).astype(np.uint8)
    k = max(1, int(round(_UNCOVERED_ERODE_MM * p.px_per_mm)))
    wanted_px = cv2.erode(wanted_px, np.ones((2 * k + 1, 2 * k + 1), np.uint8),
                          borderType=cv2.BORDER_CONSTANT, borderValue=0)

    # Sample the artwork mask at each coverage cell's centre — the exact
    # inverse of the transform stage 4 applied, same as `_region_color_errors`.
    gy, gx = np.mgrid[0:ny, 0:nx]
    sx = np.clip((((gx + 0.5) * _UNCOVERED_CELL_MM + gx0) * p.px_per_mm + cx)
                 .astype(np.int64), 0, w - 1)
    sy = np.clip((((gy + 0.5) * _UNCOVERED_CELL_MM + gy0) * p.px_per_mm + cy)
                 .astype(np.int64), 0, h - 1)
    wanted = wanted_px[sy, sx] > 0

    cell_area = _UNCOVERED_CELL_MM ** 2
    wanted_mm2 = float(wanted.sum()) * cell_area
    missing = (wanted & ~covered).astype(np.uint8)
    metrics = {"uncovered_checked": True, "uncovered_worst_mm2": 0.0,
               "uncovered_total_mm2": 0.0,
               "uncovered_wanted_mm2": round(wanted_mm2, 1)}
    if not missing.any():
        return [], metrics

    _n, _labels, stats, cents = cv2.connectedComponentsWithStats(missing, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA] * cell_area
    big = np.nonzero(areas >= _UNCOVERED_MIN_PATCH_MM2)[0]
    metrics["uncovered_worst_mm2"] = round(float(areas.max()), 1)
    metrics["uncovered_total_mm2"] = round(float(areas[big].sum()), 1)
    if not len(big):
        return [], metrics

    # Attribute each patch to the region containing its centroid, so the
    # finding names the shape a person would go look at.
    by_shape: dict[str, float] = {}
    area_of: dict[str, float] = {}
    for i in big:
        px_mm = (cents[i + 1][0] + 0.5) * _UNCOVERED_CELL_MM + gx0
        py_mm = (cents[i + 1][1] + 0.5) * _UNCOVERED_CELL_MM + gy0
        owner = None
        for r in result.regions:
            if r.shape_id in sewn and r.polygon.contains(Point(px_mm, py_mm)):
                owner = r
                break
        key = owner.shape_id if owner is not None else "(unattributed)"
        by_shape[key] = by_shape.get(key, 0.0) + float(areas[i])
        if owner is not None:
            area_of[key] = round(owner.area_mm2, 1)

    shapes = [{"shape_id": sid, "missing_mm2": round(v, 1),
               "area_mm2": area_of.get(sid)}
              for sid, v in sorted(by_shape.items(), key=lambda kv: -kv[1])]
    total = metrics["uncovered_total_mm2"]
    worst = metrics["uncovered_worst_mm2"]
    n_sh = len(shapes)
    noun = "shape" if n_sh == 1 else "shapes"
    return [finding(
        ARTWORK_UNCOVERED,
        "warn",
        f"{total:.0f} mm2 of artwork across {n_sh} {noun} is claimed by a "
        f"shape the design sews, but no thread lands on it (largest bare "
        f"patch {worst:.0f} mm2). A limb or corner is missing from the "
        f"stitch-out even though the shape itself looks correct. Check the "
        f"named shapes in review before sewing.",
        count=n_sh,
        worst_mm2=worst,
        total_mm2=total,
        wanted_mm2=metrics["uncovered_wanted_mm2"],
        shapes=shapes,
    )], metrics


# --- Uncovered links (chaining law 60) --------------------------------------

def _transport_and_content(plan: StitchPlan
                           ) -> tuple[list[tuple], dict[int, list[np.ndarray]]]:
    """Split every needle-DOWN segment into chain transport and content.

    -> ([(a, b, block_index)] transport,
        {block_index: [run points as (N, 2) float arrays]} content)

    Transport is thread whose job is to get from one shape to another: a
    TRAVEL run bridging two different shapes' content, and the connection
    into any run the machine reaches with the needle still down (`jump`
    False) across a shape boundary. That connection is easy to miss and is
    exactly the thread chaining creates — it is not a step inside any run's
    own point list, so every instrument that iterates a run's consecutive
    pairs is blind to it, `_coverage_map` included.

    A shape's OWN internal routing is not transport, and getting that wrong
    was this instrument's measured false block (hardening closeout
    2026-08-02, finding 4): a fill's row-skip travel — `stage6_fill.emit`'s
    bridge between two columns of one shape, routed inside that shape's own
    polygon by construction — was scored as a between-shape link, and a
    clean ONE-shape design blocked at 104-107 mm with "thread crosses bare
    fabric between shapes". The tell is provenance the plan already carries,
    not a router flag: a travel piece is internal exactly when the nearest
    content runs before and after it in the block belong to the SAME shape
    the travel itself names. Thread from a shape to itself is that shape's
    routing in its own colour inside its own artwork; only thread between
    two different shapes' content can be law 60's stray line. (The same rule
    deliberately covers a chained in-shape link — content(F) -> travel(F) ->
    content(F): stage 6 already trims any in-shape lift past `trim_at_mm`,
    so what chaining sews there is under the float ceiling by construction.)

    Everything else — fill rows, satin crosses, borders, beans, underlay,
    ties — is content: thread the design is made of. A fill row lying on bare
    fabric is the design; a link lying on bare fabric is a defect. That is the
    whole distinction, and it is why this cannot be asked of the plan as a
    whole. Content rides out as per-run point ARRAYS, not per-stitch tuples:
    the caller rasterizes whole runs (`cv2.polylines`) and a Python tuple per
    stitch was a measured chunk of the check's 1.94x overhead.
    """
    transport: list[tuple] = []
    content: dict[int, list[np.ndarray]] = {}
    for bi, block in enumerate(plan.blocks):
        runs = [r for r in block.runs if r.points]
        # Shape of the nearest content run at-or-after each index; the +1
        # sentinel answers "after the last run" with None.
        nxt: list[str | None] = [None] * (len(runs) + 1)
        for i in range(len(runs) - 1, -1, -1):
            nxt[i] = (runs[i].shape_id if runs[i].kind != stitches.TRAVEL
                      else nxt[i + 1])
        prev_content: str | None = None
        prev_pt: tuple[float, float] | None = None
        for i, run in enumerate(runs):
            pts = run.points
            if prev_pt is not None and not run.jump:
                internal = prev_content is not None and prev_content == nxt[i]
                if not internal:
                    transport.append((prev_pt, pts[0], bi))
            if run.kind == stitches.TRAVEL:
                internal = (prev_content is not None
                            and prev_content == nxt[i + 1]
                            and run.shape_id == prev_content)
                if not internal:
                    for a, b in zip(pts, pts[1:]):
                        transport.append((a, b, bi))
            else:
                if len(pts) >= 2:
                    content.setdefault(bi, []).append(
                        np.asarray(pts, np.float64))
                prev_content = run.shape_id
            prev_pt = pts[-1]
    return transport, content


def _link_coverage(plan: StitchPlan) -> dict | None:
    """How much transport thread lies on bare fabric. -> metrics, or None.

    THE independent instrument for chaining law 60. Stage 7 decides a link is
    legal by testing its route against POLYGONS — the block's own sewing
    polygons plus stage 5's `covered_by` union — and a polygon says where an
    object is, not where its thread landed. Three tiers break that equivalence:
    the run tier sews a small shape's OUTLINE and leaves its polygon's interior
    bare, the satin tier can leave a junction its skeleton could not resolve,
    and a shape that came back empty covers nothing at all. So this asks the
    finished stitches instead, and it disagrees: measured 2026-08-02 over 60
    configurations (5 artworks x 4 sizes x 3 garments, chaining on), stage 7's
    own re-derivation reports ZERO uncovered links in every one, while this
    reads up to 2.29 mm of link on bare fabric. Spot-checked raster-free on the
    worst of them — logo_alpha at 80 mm, left chest — where the nearest
    non-travel stitch to the bare stretch is 0.494 mm away, past the 0.20 mm
    a thread's own half-width could reach.

    Cover is thread from the link's OWN colour block, or from any block that
    sews after it. Those are law 60's two mechanisms exactly — a link is buried
    under what follows, or rides on work its own thread already laid — and
    nothing else counts: thread from an EARLIER, different colour would leave
    the link legible as a line in the wrong colour across it.

    Blocks are walked last to first so one accumulating mask serves them all,
    and the walk stops at the first block that still has transport below it:
    content earlier than every remaining link can bury nothing. The content
    itself is rasterized per RUN with `cv2.polylines` at the thread's own
    width — one C call per block replacing the old per-sample disk-stamping
    loop, which sampled every needle-down stitch at cell pitch and then
    fancy-indexed 13 offsets over all of it. That loop was most of the
    check's measured 1.94x preflight overhead (hardening closeout
    2026-08-02, finding 4); the geometry drawn is the same ribbon.
    """
    transport, content = _transport_and_content(plan)
    if not transport:
        return None

    lo = np.full(2, np.inf)
    hi = np.full(2, -np.inf)
    for seg in transport:
        for p in (seg[0], seg[1]):
            lo = np.minimum(lo, p)
            hi = np.maximum(hi, p)
    for arrs in content.values():
        for a in arrs:
            lo = np.minimum(lo, a.min(axis=0))
            hi = np.maximum(hi, a.max(axis=0))
    cell = _LINK_CELL_MM
    pad = machine.COVERAGE_THREAD_W_MM
    x0, y0 = float(lo[0]) - pad, float(lo[1]) - pad
    span_x, span_y = float(hi[0]) + pad - x0, float(hi[1]) + pad - y0
    while (int(span_x / cell) + 2) * (int(span_y / cell) + 2) > _LINK_MAX_CELLS:
        cell *= 2.0
    nx = int(span_x / cell) + 2
    ny = int(span_y / cell) + 2

    rad = max(1, int(round(machine.COVERAGE_THREAD_W_MM / 2.0 / cell)))

    def sample(segs: list[tuple]) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                           np.ndarray]:
        """-> (cell x, cell y, per-sample mm, samples per segment).

        Every segment of the batch sampled in ONE pass, the same lattice trick
        `_coverage_map` uses: a per-segment Python loop with a handful of numpy
        calls in it costs more in call overhead than the arithmetic, and on the
        biggest house artwork that alone was six seconds of preflight.
        """
        a = np.asarray([s[0] for s in segs], np.float64)
        b = np.asarray([s[1] for s in segs], np.float64)
        d = b - a
        ln = np.hypot(d[:, 0], d[:, 1])
        n = np.maximum(1, np.ceil(ln / cell).astype(np.int64))
        idx = np.repeat(np.arange(len(segs)), n)
        starts = np.concatenate([[0], np.cumsum(n)[:-1]])
        t = (np.arange(int(n.sum())) - np.repeat(starts, n) + 0.5) / n[idx]
        cx = ((a[idx, 0] + d[idx, 0] * t - x0) / cell).astype(np.int64)
        cy = ((a[idx, 1] + d[idx, 1] * t - y0) / cell).astype(np.int64)
        return (np.clip(cx, 0, nx - 1), np.clip(cy, 0, ny - 1),
                (ln / n)[idx], n)

    moves: dict[int, list] = {}
    for seg in transport:
        moves.setdefault(seg[2], []).append(seg)
    first_move_bi = min(moves)

    # Fixed-point pixel coordinates for polylines: cell k's CENTER is
    # x0 + (k + 0.5) * cell, so the half-cell shift keeps the drawn ribbon
    # registered with `sample`'s floor-binned lookup cells.
    _FP_BITS = 3
    _FP = float(1 << _FP_BITS)

    def to_px(a: np.ndarray) -> np.ndarray:
        return np.round(
            ((a - (x0, y0)) / cell - 0.5) * _FP).astype(np.int32)

    laid = np.zeros((ny, nx), np.uint8)
    total_mm = uncovered_mm = 0.0
    worst_mm = 0.0
    worst_at: tuple[float, float] | None = None
    for bi in range(len(plan.blocks) - 1, first_move_bi - 1, -1):
        arrs = content.get(bi)
        if arrs:
            cv2.polylines(laid, [to_px(a) for a in arrs], False, 1,
                          thickness=2 * rad + 1, shift=_FP_BITS)
        batch = moves.get(bi)
        if not batch:
            continue
        cx, cy, step, n = sample(batch)
        total_mm += float(step.sum())
        covered = laid[cy, cx] != 0
        uncovered_mm += float(step[~covered].sum())
        # Longest unbroken bare stretch. It is carried ACROSS consecutive
        # transport segments that touch, because that is what the thread does:
        # a chained link is many 2 mm stitches end to end, and the fabric under
        # it does not know where one stitch stops. Resetting per segment
        # measured 1.89 mm on the case that is really 2.29 mm — it reports the
        # longest bare STITCH rather than the longest bare stretch.
        carry_mm = 0.0
        carry_end: tuple[float, float] | None = None
        at = 0
        for seg_i, count in enumerate(n):
            count = int(count)
            end = at + count
            joined = (carry_end is not None
                      and math.dist(batch[seg_i][0], batch[seg_i - 1][1]) < 1e-9)
            lead_mm = carry_mm if joined else 0.0
            v = covered[at:end]
            wide = float(step[at])
            hit = np.flatnonzero(v)

            def note(mm: float, last: int) -> None:
                nonlocal worst_mm, worst_at
                if mm > worst_mm:
                    worst_mm = mm
                    worst_at = (float(x0 + (cx[last] + 0.5) * cell),
                                float(y0 + (cy[last] + 0.5) * cell))

            if hit.size == 0:                       # the whole segment is bare
                carry_mm = lead_mm + count * wide
                carry_end = (cx[end - 1], cy[end - 1])
                note(carry_mm, end - 1)
            else:
                leading = int(hit[0])
                if leading or lead_mm:
                    note(lead_mm + leading * wide,
                         at + max(0, leading - 1) if leading else at)
                edges = np.concatenate([[-1], hit, [count]])
                gaps = np.diff(edges) - 1
                if gaps.size > 2:
                    k = int(gaps[1:-1].argmax()) + 1
                    g = int(gaps[k])
                    if g > 0:
                        note(g * wide, at + int(edges[k]) + g)
                trailing = count - 1 - int(hit[-1])
                carry_mm = trailing * wide
                carry_end = (cx[end - 1], cy[end - 1]) if trailing else None
                if trailing:
                    note(carry_mm, end - 1)
            at = end
    return {"segments": len(transport), "thread_mm": total_mm,
            "uncovered_mm": uncovered_mm, "max_mm": worst_mm, "at": worst_at,
            "cell_mm": cell}


def _link_findings(plan: StitchPlan,
                   cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """Transport thread the garment will show, against the fabric's own float
    ceiling.

    The threshold is `fabric.trim_at_mm` and it is not a new number: it is the
    one this engine already uses to decide when exposed thread may not be left
    on a garment ("a float long enough to catch a finger is a float someone has
    to remove with scissors" — stage 7). Chaining spends exactly that rule: it
    declines a trim on the promise the thread will be buried. Where the promise
    fails by more than the trim rule's own ceiling, the design carries a line of
    stitching across bare fabric that the operator was going to have cut out —
    strictly worse than the trim it replaced, which is why it blocks rather than
    warns, and it is the failure chaining laws 59 and 60 say must ship together.

    Under the ceiling this stays silent, and deliberately: a stretch shorter
    than `trim_at_mm` is less exposed thread than the same engine leaves lying
    as a jump, in a tacked-down form that cannot be pulled into a loop. Measured
    over the 60-configuration sweep the longest bare stretch is 2.29 mm with a
    p90 of 1.07, against a 3.0 mm ceiling on pique knit and 4.0 on terry — so
    clean work is silent on every fixture the house owns, with the margin coming
    from measurement rather than from rounding the threshold up to fit. (That
    sweep predates 2026-08-11 and measured the old transport definition,
    internal travel included; the between-shape-only instrument can only read
    lower on the same plans.)

    `link_uncovered_max_mm` rides out in the metrics whether or not it fires:
    the number is the point, and an operator watching it move across a
    re-digitize learns more than a boolean. All four link metrics count
    BETWEEN-shape transport only — a chain-off plan reports zero link thread,
    because without chaining nothing sews from one shape to another
    needle-down (`_transport_and_content` owns that classification).
    """
    got = _link_coverage(plan)
    empty = {"link_segments": 0, "link_thread_mm": 0.0,
             "link_uncovered_mm": 0.0, "link_uncovered_max_mm": 0.0}
    if got is None:
        return [], empty
    limit = max(0.0, fabric_for(cfg).trim_at_mm)
    metrics = {
        "link_segments": got["segments"],
        "link_thread_mm": round(got["thread_mm"], 1),
        "link_uncovered_mm": round(got["uncovered_mm"], 2),
        "link_uncovered_max_mm": round(got["max_mm"], 2),
    }
    if limit <= 0.0 or got["max_mm"] <= limit:
        return [], metrics
    at = got["at"] or (0.0, 0.0)
    return [finding(
        LINK_UNCOVERED,
        "block",
        f"{got['max_mm']:.1f} mm of thread crosses bare fabric between shapes "
        f"— longer than the {limit:g} mm this fabric cuts a float at. It will "
        f"show as a stray line on the garment. Re-digitize, or trim that "
        f"connection instead of sewing it.",
        max_mm=round(got["max_mm"], 2),
        limit_mm=round(limit, 2),
        total_mm=round(got["uncovered_mm"], 2),
        thread_mm=round(got["thread_mm"], 1),
        at_mm=[round(at[0], 1), round(at[1], 1)],
    )], metrics


# --- Contour fill starvation (laws 39-44) -----------------------------------

def _contour_findings(plan: StitchPlan) -> tuple[list[dict], dict]:
    """The contour tier's own starvation report, put in front of the operator.

    Stage 6 counts a contour-filled shape `starved` when the widest circle of
    bare fabric between its emitted stitches (measured per shape by
    `barecircle.widest_bare_circle` — since 2026-08-04 the gate is that
    measurement, not the dropped-ring area sum) beats
    `barecircle.starved_threshold_mm`, and stage 7 raises
    CONTOUR_RING_UNREACHABLE. That warning goes to `plan.warnings`, which the
    review screen reads and the preflight report did not, so the one number
    that says a fill has a hole in it reached nobody scoring a file.

    It is re-emitted rather than re-measured, and that is a measured decision.
    Preflight can raster the laid thread and find bare patches inside a shape
    without trusting stage 6 at all — the honest instrument this module would
    normally insist on — but it does not separate the populations. Over 80
    configurations (5 artworks x 4 sizes x 2 garments x both techniques,
    2026-08-02) the largest connected bare patch inside a shape reaches
    15.44 mm2 on plain TATAMI and 15.48 mm2 on contour, with the tatami p90 at
    1.40 against contour's 2.84: any threshold that catches a starved contour
    shape also flags clean tatami work. A check like that would train the
    operator to skip the report, so it is not shipped. Stage 6 knows which
    rings it dropped and why; preflight's job here is to carry that.

    `shapes` in the warning's extra is honoured when present and the finding
    names them. The contour lane does not put it there yet — its extra carries
    `count` and `rings` — so today this says how many and how many rings, and
    gains the names the moment that lane adds them.
    """
    hits = [w for w in plan.warnings if w.get("code") == _CONTOUR_RING_UNREACHABLE]
    if not hits:
        return [], {"contour_starved_shapes": 0}
    count = rings = 0
    shapes: list[str] = []
    for w in hits:
        extra = w.get("extra") or w
        count += int(extra.get("count", 1) or 1)
        rings += int(extra.get("rings", 0) or 0)
        for s in extra.get("shapes") or ():
            shapes.append(s if isinstance(s, str) else str(s.get("shape_id", s)))
    noun = "shape" if count == 1 else "shapes"
    which = f" ({', '.join(shapes)})" if shapes else ""
    return [finding(
        CONTOUR_STARVED,
        "warn",
        f"{count} filled {noun}{which} {'has' if count == 1 else 'have'} a "
        f"bare patch where contour rings were too short to sew. The fabric "
        f"will show through there. Check {'it' if count == 1 else 'them'} on "
        f"the review screen, or fill {'that shape' if count == 1 else 'those '
        'shapes'} with tatami rows instead.",
        count=count,
        rings=rings,
        shapes=shapes,
    )], {"contour_starved_shapes": count}


# --- Same-hole strikes (law 17) ---------------------------------------------

def _same_hole_findings(plan: StitchPlan) -> tuple[list[dict], float | None]:
    """How much of the design lands on a hole the needle has already made.

    Law 17's mechanism is real — a second strike inside the 0.5 mm blade
    radius shreds the first thread — but its trade phrasing ("tie-in/tie-off
    must never stack on one point") is stricter than professional files
    themselves. Measured, 2026-08-01: across the 36-file corpus (732,246
    penetrations) points struck 2+ times are 9.455% of penetrations and ALL
    36 files contain 3+ stacked points; our benchmark is 9.8%. So this is an
    INFO that fires only far above that — a regression detector, never a
    verdict on correct behaviour.

    Rate is (distinct points struck 2+ times) / (total penetrations), on the
    0.1 mm DST grid — the corpus's own definition and resolution, so the
    number here is comparable to the 9.455% figure rather than merely similar
    in spirit. Ties are deliberately INCLUDED: they are most of what this
    measures.
    """
    q = _SAME_HOLE_QUANTUM_MM
    keys: list[tuple[int, int]] = []
    for _b, run in plan.iter_runs():
        for x, y in run.points:
            keys.append((int(round(x / q)), int(round(y / q))))
    total = len(keys)
    if total < _MIN_SAMPLES:
        return [], None

    counts: dict[tuple[int, int], int] = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1
    repeats = sum(1 for v in counts.values() if v >= 2)
    rate = repeats / total
    if rate <= SAME_HOLE_RATE_MAX:
        return [], rate
    return [finding(
        SAME_HOLE_HEAVY,
        "info",
        f"{rate:.0%} of the needle's landings are on a spot it has already "
        f"struck — professional files run about 9%. The design will sew, but "
        f"expect the odd thread break where the stitching doubles back on "
        f"itself.",
        fraction=round(rate, 3),
        repeat_points=repeats,
        penetrations=total,
        baseline=0.09455,
    )], rate


# --- The report -------------------------------------------------------------

def run_preflight(result: PipelineResult, plan: StitchPlan,
                  cfg: PipelineConfig | None = None,
                  image=None) -> dict:
    """The full preflight report for one finished digitize() output.

    `image` is the same artwork `digitize` was given (path, bytes, or
    ndarray). It is optional because only the thread-match check needs it —
    everything else reads the plan — and a caller re-scoring a stored plan
    may no longer have the artwork. Without it the thread check is skipped
    and the report says so (`thread_match_checked`). `result` is likewise
    only read by the thread-match check, so a caller scoring a bare plan may
    pass None for both.

    Returns {"score", "grade", "findings", "metrics"} — every value a plain
    Python scalar/list/dict, safe to hand straight to a JSON boundary.
    """
    cfg = cfg or PipelineConfig()

    findings: list[dict] = []
    metrics: dict = {}

    # One stage-1 re-read serves every check that needs the artwork: the
    # thread-match rasterization and the two photo guardrails (resolution,
    # subject contrast). Without the artwork all three are skipped and the
    # metrics say so, each with its own None.
    p = prep(image, cfg) if image is not None else None

    worst_de: float | None = None
    if p is not None and result is not None:
        thread_findings, worst_de = _thread_match_findings(p, result, plan, cfg)
        findings.extend(thread_findings)
    metrics["thread_match_checked"] = p is not None and result is not None
    metrics["thread_worst_delta_e"] = None if worst_de is None else round(worst_de, 1)

    if p is not None:
        res_findings, res_metrics = _photo_resolution_findings(p, plan, cfg)
        findings.extend(res_findings)
        metrics.update(res_metrics)
        contrast_findings, contrast_metrics = _subject_contrast_findings(p, plan, cfg)
        findings.extend(contrast_findings)
        metrics.update(contrast_metrics)
    else:
        metrics["input_px_per_mm"] = None
        metrics["subject_bg_delta_l"] = None

    lettering, satin_shape_count = _lettering_findings(plan)
    findings.extend(lettering)
    metrics["satin_shapes"] = satin_shape_count

    length_findings, length_metrics = _stitch_length_findings(plan)
    findings.extend(length_findings)
    metrics.update(length_metrics)

    trim_findings, per_1000 = _trim_findings(plan)
    findings.extend(trim_findings)
    metrics["trims_per_1000"] = round(per_1000, 1)

    density_findings, density_metrics = _density_findings(plan, cfg)
    findings.extend(density_findings)
    metrics.update(density_metrics)

    coverage_findings, coverage_metrics = _coverage_findings(plan)
    findings.extend(coverage_findings)
    metrics.update(coverage_metrics)

    # Needs both the artwork and the regions, same as the thread-match check.
    if p is not None and result is not None:
        unc_findings, unc_metrics = _uncovered_findings(p, result, plan)
        findings.extend(unc_findings)
        metrics.update(unc_metrics)
    else:
        metrics.update({"uncovered_checked": False, "uncovered_worst_mm2": None,
                        "uncovered_total_mm2": None, "uncovered_wanted_mm2": None})

    link_findings, link_metrics = _link_findings(plan, cfg)
    findings.extend(link_findings)
    metrics.update(link_metrics)

    contour_findings, contour_metrics = _contour_findings(plan)
    findings.extend(contour_findings)
    metrics.update(contour_metrics)

    hole_findings, hole_rate = _same_hole_findings(plan)
    findings.extend(hole_findings)
    metrics["same_hole_fraction"] = None if hole_rate is None else round(hole_rate, 3)

    face_findings, face_metrics = _face_size_findings(plan)
    findings.extend(face_findings)
    metrics.update(face_metrics)

    override_findings, override_metrics = _class_override_findings(image, cfg)
    findings.extend(override_findings)
    metrics.update(override_metrics)

    findings.extend(_stabilizer_findings(plan))

    stop_findings, color_changes = _color_stop_findings(plan)
    findings.extend(stop_findings)
    metrics["color_changes"] = color_changes

    metrics["stitch_count"] = plan.stats.stitch_count

    score = 100
    for f in findings:
        score -= _DEDUCT.get(f["severity"], 0)
    score = max(0, score)
    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 40 else "F")

    return {"score": score, "grade": grade,
            "findings": findings, "metrics": metrics}
