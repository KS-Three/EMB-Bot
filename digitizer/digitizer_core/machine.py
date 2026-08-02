"""Machine physics — every hard number the stitch planner obeys, in one place.

These are constraints of thread, needle, and fabric, not preferences, which is
why they live apart from `PipelineConfig`: a caller may tune density or fabric,
but nothing may hand the planner a stitch longer than the format can encode or
shorter than the needle can survive.

Sources are the blueprint's constraint table and standard digitizing practice;
Kent's sew-outs at milestones 3, 5 and 6 are what tune the tunable ones. Where
a number is a format limit rather than a craft rule, it says so — those are not
negotiable by sew-out.
"""
from __future__ import annotations

# --- Format limits (not tunable) ------------------------------------------

# A Tajima DST record encodes a delta of at most +-121 units of 0.1 mm on each
# axis. Anything longer must be split into multiple records, so the planner
# never emits a longer move.
MAX_STITCH_MM = 12.1

# --- Needle and thread limits ---------------------------------------------

# Below this the needle lands in (or beside) the previous hole: thread shreds,
# needles heat, and the machine's thread-break detector starts crying wolf.
MIN_STITCH_MM = 1.0

# Anything shorter than this is not a stitch at all, it is a rounding artifact
# of the geometry, and is removed outright rather than merged.
TINY_STITCH_MM = 0.5

# --- Fill ------------------------------------------------------------------

# Run length along a tatami row. Measured across 19 professional files
# (2026-07-30 corpus study, tools/study_pro.py): pro fills run 2.0-3.4 mm with
# a median near 2.6; the old 4.0 sat outside the observed range entirely.
FILL_STITCH_MM = 3.0
# Row spacing = density. Dense pro fills measure ~0.20 mm EFFECTIVE spacing in
# the corpus — but that may be two interleaved 0.40 passes, and doubling
# density doubles stitch count, so 0.40 stands until a sew-out decides.
FILL_ROW_MM = 0.40

# Penetrations realign every Nth row. Without a stagger, every row starts its
# stitches at the same offset and the needle holes line up into visible
# channels running through the fill — the single most recognisable mark of a
# naive scanline fill.
FILL_STAGGERS = 4

# Narrower than this cannot hold a tatami fill: the rows have nowhere to go and
# the result is a lumpy running stitch. Satin's job — the classifier sends
# such shapes there, and only what satin also cannot take gets warned.
MIN_FILL_WIDTH_MM = 1.2

# --- Satin ----------------------------------------------------------------

# Spacing of zigzag crosses along the stroke. Satin reads as a solid band of
# parallel thread; at 0.4 mm adjacent threads just touch without piling up.
SATIN_SPACING_MM = 0.4

# Ribbons wider than this sew better as fill: long satin crosses float, snag,
# and pull the fabric visibly. The 19-file corpus study says professionals
# satin much wider than the old 3.0 — little-romeo lettering runs 3.4 mm
# median / 4.2 max, beckers 4.2 / 5.1 — always over underlay. 5.0 matches
# practice; columns past ~2.5 mm force zigzag underlay in stage 6. NOTE: the
# browser engine still classifies at 3.0 (satinMaxWidthMm) — divergence is
# deliberate, corpus-driven, and Python-side only until its own sew-out.
SATIN_MAX_WIDTH_MM = 5.0
# Above this ribbon width a column must carry zigzag underlay: wide crosses
# float without it. Every wide-satin file in the corpus shows support passes.
SATIN_ZIGZAG_ABOVE_MM = 2.5

# A cross shorter than this is degenerate — the two rails have pinched
# together (shared tips, stroke ends) and sewing it would pile thread on a
# point. Dropped during emission, exactly as the browser engine does.
SATIN_MIN_CROSS_MM = 0.5

# --- Split satin (wide-cross intermediate penetrations) ---------------------
# Measured 2026-07-31 over the 36-file professional corpus (scratch_corpus)
# plus Kent's three commissioned files, with a traverse-level instrument:
# study_pro.classify is BLIND to splits, because a split cross reads as two
# collinear segments and the reversal fraction falls below its satin gate —
# which is why the earlier study reported wide satin as unsplit.

# Above this cross length the needle penetrates mid-cross instead of throwing
# one long stitch. Corpus split fraction by cross length: 14% at 3.0 mm, 27%
# at 4.0, 24% at 4.5, 53% at 5.0, 65% at 5.5, 92% at 7.0, ~100% from 7.5 —
# the majority crossover sits between the 4.5 and 5.0 buckets. House styles
# disagree (PRECISION DRON HAT splits from ~3.5 mm; be-joy from ~5.0; beckers
# logo hat sews raw crosses to ~6; jolly-af and sweet-heart to ~7), so 5.0 is
# the corpus-wide median vote. It coincides with SATIN_MAX_WIDTH_MM: a column
# that CLASSIFIES satin (mean ribbon width <= 5.0) splits only where it
# locally bulges past its mean — junctions and flares, exactly the crosses
# that float. This is the structural fix long before the format ceiling
# (MAX_STITCH_MM 12.1) forces anything.
SPLIT_SATIN_ABOVE_MM = 5.0

# Target segment of a split cross: k = ceil(cross / this) segments, interior
# penetrations at j/k. Corpus: implied segment W/k med 2.51 (p25 2.07, p75
# 2.95), raw segment med inside wide columns 3.10, and the observed k mode
# matches ceil(W / 3.0) at 5, 6, 7 and 9 mm widths (k=2 at 83% / 68%, k=3 at
# 49% / 79%). Equal to FILL_STITCH_MM, and that is no accident: a cross too
# long to lie flat penetrates at fill pitch.
SPLIT_SEGMENT_MM = 3.0

# Stagger: the penetration comb shifts along the cross station to station so
# split holes never trench a straight line down the column — the same defect
# FILL_STAGGERS exists for. Corpus (27,256 k=2 split crosses): offset from
# mid-cross |t-0.5| med 0.117 of the cross, station-to-station shift med
# 0.214, and the aligned-hole minority is 131 columns of 1,922. Observed
# cycles run 3 stations (best-friend, amplitude ~0.26) to 6 (be-joy, ~0.13).
# A 4-station wave at +-0.23 of one segment reproduces the medians — at k=2,
# 0.23/2 = 0.115 of the cross — and matches FILL_STAGGERS' period.
SPLIT_STAGGER_PERIOD = 4
SPLIT_STAGGER_STEP_SEGS = 0.23
SPLIT_STAGGER_WAVE = (1.0, -1.0, 1.0 / 3.0, -1.0 / 3.0)

# Inside-curve protection ("short stitches"). On a bend the inside rail is
# shorter than the outside one, so penetrations bunch up; closer than this and
# the needle chews the same spot. Every other cross is shortened by the pull
# fraction so alternate penetrations land away from the rail.
SATIN_SHORT_STITCH_AT_MM = 0.3
SATIN_SHORT_STITCH_PULL = 0.35
# Absolute ceiling on that pull. Clearing a needle hole takes the same few
# tenths of a millimetre whatever the column width, but the fraction scales
# with the column: measured on ribbon_curve.png at 80 mm, 0.35 x a 2.78 mm
# cross retracted a penetration 0.97 mm off its rail and read as two ~1.0 mm
# same-rail gaps against the 0.40 mm spacing target. 0.6 = 2 x
# SATIN_SHORT_STITCH_AT_MM: one full same-hole radius clear of the old hole.
SATIN_SHORT_STITCH_PULL_MAX_MM = 0.6

# --- Border (the outline tier) ---------------------------------------------
# Measured over 39 professional DSTs (tools/border_pro.py): 18 satin borders,
# 14 bean outlines. NOTHING here is mirrored in the browser engine — it has no
# border tier at all — so the "a mirrored value moves in both or neither" rule
# has nothing to move.

# A border column is THINNER than a lettering column: median 1.40 mm
# (p10 0.78, p90 2.98) against 2.21 mm for satin generally. An outline is a
# line, not a stroke of letterform weight; bordering at lettering width is
# most of why a machine outline reads heavy.
BORDER_WIDTH_MM = 1.40

# Looser than lettering's 0.40-0.42: median 0.45 mm. A border rides an edge
# that already has coverage under it. Measured on the RAILS, like law 4 — the
# spacing between consecutive penetrations on the same side of the column.
BORDER_DENSITY_MM = 0.45

# UNMEASURED, and deliberately not invented. How far a professional's border
# centreline sits from the fill edge it covers: the over-a-fill detector fired
# ZERO times across 39 files while Hotel Fremont visibly has one, so the corpus
# has not answered it. 0.0 is the boundary condition rather than a guess — the
# column's outer rail lies exactly on the region's visible edge and the whole
# column lies inside it. When the number arrives this constant is the entire
# change; see stage6_border._centre_inset.
BORDER_SEAM_OFFSET_MM = 0.0

# Minimum turn radius forced on a ring before it is offset, so neither rail
# ever has zero radius. 1.5x the column width, which leaves the inner rail's
# own radius at r - W = 0.70 mm > 0: the inside of a corner crowds (short
# stitches fix that) but can never fold back on itself. Below that a corner is
# not a corner, it is a fold, and law 3 says folds are the only thing
# professionals split for.
BORDER_CORNER_RADIUS_MM = 2.10

# A shape must have something left inside the column or the "border" is just a
# heavy re-fill of the whole shape. Below it the light tier takes over.
BORDER_HOST_MARGIN_MM = 0.20

# A closed loop shorter than the circumference of a circle of radius
# BORDER_WIDTH_MM is a dot, not an outline. 2*pi*1.40.
BORDER_MIN_LOOP_MM = 8.80

# The circuit closes by running past its own start for one column width, at a
# half-station phase shift so the repeated penetrations miss the first holes.
BORDER_CLOSURE_OVERLAP_MM = 1.40

# How far the join may slide from the nearest station to find a flat stretch.
BORDER_JOIN_SEARCH_MM = 3.0

# Bean / triple run — the light outline tier, and the fallback wherever a
# column will not fit. 14 found: 2.75 passes median (p90 3.27) at 0.73 mm
# stitch length (p10 0.67, p90 1.87).
BEAN_PASSES = 3
BEAN_STITCH_MM = 0.73

# --- The run tier (small-shape rescue) --------------------------------------
# A shape too small to hold fill rows or satin crosses sews as a bean run on
# its own outline instead of being dropped — the same technique Wilcom's Hatch
# course teaches for small lettering, at sizes where satin and fill both die.
# Two floors decide what is still too small for even that; below them a shape
# is smaller than the mark the thread would leave sewing it, and it drops.

# The smallest closed circuit a bean run can sew: three stations at
# BEAN_STITCH_MM (3 x 0.73 = 2.19). Under three stations the "loop" is the
# needle re-entering its own holes, which reads as lint. Benchmark measurement
# (enthusiast logo at 90 mm): the period of "ENTERPRISES INC." has a ~1.2 mm
# outline and correctly dies here; the thinnest letter (the "I", 0.26 x
# 1.91 mm) has a 4.3 mm outline and survives.
RUN_MIN_LOOP_MM = 2.2

# The thread's own visual weight, squared. A 40 wt line lays ~0.4 mm wide —
# the same measurement behind SATIN_SPACING_MM (adjacent threads just touch
# at 0.4) — so a shape with less area than one thread-width square is smaller
# than a single penetration's worth of thread. Benchmark: the period is
# 0.10 mm² (dies), the thinnest subline letter is 0.50 mm² (survives).
RUN_MIN_AREA_MM2 = 0.16

# --- Travel ----------------------------------------------------------------

TRAVEL_STITCH_MM = 2.5  # shorter than fill so travel disappears under coverage
TRAVEL_INSET_MM = 0.6   # travel hugs the edge but never reaches it

# --- Underlay --------------------------------------------------------------

UNDERLAY_INSET_MM = 1.0      # edge walk sits inside the finished edge
UNDERLAY_STITCH_MM = 2.5     # structural, not decorative
UNDERLAY_ZIGZAG_MM = 2.0     # row spacing, zigzag underlay
UNDERLAY_LATTICE_MM = 2.5    # row spacing, lattice underlay

# --- Ties and trims --------------------------------------------------------

TIE_STITCH_MM = 0.8   # one leg of a lock stitch
TIE_STITCHES = 3      # three legs is the standard lock

# A needle-up move longer than this is cut. Shorter ones are left as jumps:
# trimming everything wears the trimmer and slows the machine, leaving long
# floats means someone picks them out with scissors afterwards.
TRIM_AT_MM = 3.0

# --- Estimation ------------------------------------------------------------

# Thread consumed per mm of stitch path: the top thread travels down and back
# through the fabric, so the cone gives up more than the path length. Rule of
# thumb used for the operator-facing estimate only; nothing geometric.
THREAD_LENGTH_FACTOR = 1.35


def clamp_stitch_mm(value: float) -> float:
    """Keep a requested stitch length inside what the machine can actually do."""
    return max(MIN_STITCH_MM, min(MAX_STITCH_MM, value))


# --- Coverage budget (law 27) ----------------------------------------------
# "The density budget is a per-region sum, not a per-object setting:
#  coverage_units = SUM(0.4 / spacing) over everything overlapping a region,
#  underlay included" — docs/machine-physics-playbook-2026-07-31.md, law 27.
# One unit is one full covering layer of 40wt thread. Preflight's coverage map
# is the instrument; these are its physical constants.

# The width of the thread itself, and therefore the width of the ribbon a
# single stitch lays on the fabric. Law 16 [P] (Coats, Madeira): "40wt thread
# is 0.4 mm wide, and that is the unit of everything" — lines spaced 0.40 mm
# sit edge to edge, exactly one full-coverage layer. Same number as
# SATIN_SPACING_MM and FILL_ROW_MM, and that is the point: at those spacings
# the ribbons tile and the map reads exactly 1.0.
COVERAGE_THREAD_W_MM = 0.40

# Side of one coverage cell: the patch of fabric whose thread budget law 27
# is about. NOT the thread quantum. At 0.40 mm a cell answers "is a thread
# here" (binary) rather than "how many layers", so a single running line
# would read 1.0 and a 3-pass bean outline 3.0 — condemning the light outline
# tier, which exists precisely for shapes too small for anything heavier.
# 1.0 mm is 2.5 thread widths, and law 27's own smallest reasoned-about
# region is 5x5 mm (its no-holes-under-small-objects rule), so a cell is
# 1/25th of the smallest region the law discusses. Law 29 [P] agrees on the
# scale: pucker is the FABRIC buckling as an Euler column, a patch
# phenomenon, not a thread one. Cost: the benchmark's 90x19 mm design is
# 1,710 cells and a full 200x200 mm hoop 40,000 — runtime is set by stitch
# count, not by the grid.
COVERAGE_CELL_MM = 1.0

# Step along a stitch when its thread ribbon is sampled into cells: a quarter
# of the thread width, so a cell's share of a stitch is exact to ~0.04
# coverage units and a correctly spaced 0.40 mm fill reads 1.000 with no
# phase or moire artifact against the cell grid.
COVERAGE_SUBSAMPLE_MM = 0.1

# Law 27's own stack arithmetic: "the safe classic stack is underlay + fill +
# satin detail ~= 2.5 units. Never more than two full-density fills stacked."
# Both numbers are tagged [D] in the playbook (our own derivation, medium
# confidence, sew-out-gated at part 4 item 2 against Embrilliance's 6-thread-
# layer red line) — they are NOT primary-sourced, and are carried here with
# that provenance intact.
#
# Checked against what our own output actually produces, 2026-08-01, rather
# than adopted on the playbook's word. The stacking ladder lands exactly on
# law 27's prose: one full-density fill measures 1.00 units, two 2.00 ("never
# more than two full-density fills stacked" — permitted, silent), three 3.00
# ("a third layer means cutting a hole in the base" — warn), four 4.00
# (block). Real plans: the fixture logo p50 1.20 / p95 1.82 / max 2.55 and
# the benchmark at 90 mm p50 1.19 / p95 3.15 / max 4.58 — both clean, both
# silent, because the check gates on connected patch area and neither has a
# patch over 2.5 bigger than 11 mm2. An auto border over a 0.20 mm fill
# reaches 4.85 across 408 mm2 and warns; 0.13 mm rows block.
COVERAGE_WARN_UNITS = 2.5
COVERAGE_BLOCK_UNITS = 3.5


# --- Chaining: the needle-down link between two shapes (laws 59-62) ---------
# Measured 2026-08-01 over 434 inter-element transitions in the 36-file
# professional corpus — 273 needle-down links against 161 trims. See
# docs/chaining-laws-2026-08-01.md. These are the constants of the link
# itself; the decision of whether a link is legal at all is geometry, and
# lives in stage 7.

# Stitch length along a link. Law 61 [M]: median 1.96 mm, p10 1.20, p90 2.48.
# Deliberately NOT the same number as TRAVEL_STITCH_MM (2.5, stage 6's
# in-shape bridge, which sits above the professional p90 and moves only with
# its own sew-out and its browser mirror). A link crosses ground the operator
# may see through a single covering layer, so it takes the measured figure.
RUN_STITCH_MM = 2.0

# How far outside the covering geometry a link may stray and still count as
# buried. Half of COVERAGE_THREAD_W_MM: the covering element's own edge
# stitches are 0.4 mm-wide ribbons centred on its boundary, so they physically
# lap this far past the polygon edge. Larger than that and the tolerance is
# inventing cover that no thread provides — measured on the benchmark, 0.3 mm
# starts admitting links across bare inter-letter fabric.
LINK_COVER_TOL_MM = 0.2

# The gap past which a link is refused outright, whatever the coverage. Law 59
# [M] is flat — professionals link 56-75% of transitions at every bucket from 0
# to 40 mm — and then it is not: past 40 mm the corpus flips to 69.7% trimmed
# (33 transitions, only 10 linked). 40 mm is that knee, read straight off law
# 59's own table.
#
# It is deliberately NOT the p90 of linked gaps (27.6 mm). A p90 says one link
# in ten is longer, so capping there would refuse a tenth of what professionals
# actually do. The knee says something different and stronger: past it, the
# profession's own answer flips.
#
# The 30% that still link past 40 mm are real (the longest observed is
# 61.7 mm), and we cannot tell from geometry which transitions they are — that
# call is made by a digitizer who knows what the garment is for. So we take the
# majority answer, because the two errors are not symmetric: an unnecessary
# trim costs two seconds of machine time and is invisible in the finished
# garment, and an unnecessary 60 mm link is either a float or a detour long
# enough to read as one.
#
# Without this the stitch budget alone lets a 60 mm gap through — 36 stitches
# at 2.0 mm is 72 mm of allowance — so this is the cap that actually binds at
# distance, and the stitch cap is what binds on detour.
LINK_MAX_GAP_MM = 40.0

# The ceiling on a link, in stitches. Law 62 [M]: the median link is 7
# stitches and p90 is 36, so 36 is "no longer than nine in ten professional
# links". It is also where a link stops being cheaper than the trim it
# replaces: a trim costs 2-3 s of trimmer time (~33 stitches at 800 spm) plus
# a lock at each end. Budgeting in STITCHES rather than millimetres is law 62's
# own point — a link is short in stitches even when long in millimetres — and
# at RUN_STITCH_MM this cap allows 72 mm of path, past the corpus's longest
# observed linked gap of 61.7 mm (law 59).
LINK_MAX_STITCHES = 36

# The median link, in stitches. Law 62 [M]. Every link is allowed at least
# this much path however short its gap, so a one-millimetre hop around a
# corner is still permitted the detour a professional would spend on it.
LINK_MEDIAN_STITCHES = 7

# How much longer than the gap a link's PATH may run. From the corpus's own
# two medians read against each other: the median link is 7 stitches of
# 1.96 mm (13.7 mm of path) across a median 7.83 mm gap, a ratio of 1.75, and
# at p90 it is 36 stitches (70.6 mm) across 27.6 mm, a ratio of 2.56. 2.5 is
# the p90 figure — a link may bend as far out of its way as nine in ten
# professional links do, and no further.
#
# This is a budget, not a preference: it is what keeps the route search from
# considering a detour nobody would sew, and without it the search spends its
# whole node allowance on waypoints strewn along a straight line it has
# already established is not covered.
LINK_DETOUR_FACTOR = 2.5
