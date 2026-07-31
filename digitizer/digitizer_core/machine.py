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
