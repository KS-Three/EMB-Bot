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
# Row spacing = density. The two-pass-interleave hedge this comment used to
# carry is REFUTED (docs/law19-fill-spacing-2026-08-02.md): our own fill and
# the corpus both sew rows in strict geometric order (427 patches, 2 show an
# interleave signature). But the corpus's dense ~0.20 mm reading turns out to
# be TWO POPULATIONS, not one: for 29 freebie script/lettering files it is a
# satin crossing's half-step artifact of a 0.40-0.51 mm same-rail column, not
# a tatami row at all (coverage 1.8-2.3 matches a satin reading, not a fill
# one) — but 43 commissioned cap-logo files sew a genuine ~0.19 mm area-fill
# row pitch (traverse spans 6-54 mm with 3-17 penetrations each rule out
# satin or a fan column). Which population our own fills should match is
# still unresolved, so 0.40 stands pending sew-out card block 2.
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

# --- Density-targeted fill (two-pass "cross + top") ------------------------
# Corpus measurement (2026-08-14, pro-parity task A2, tools/pro_parity):
# professional SOLID fill elements (machine_hat/lc, hotel_fremont's cap-logo
# panels) sew an effective ~0.18-0.21 mm row pitch -- roughly double
# FILL_ROW_MM's single 0.40 mm pass, not a fresh ultra-tight single pass at
# that spacing (real risk of fabric distortion/pucker sewing every row that
# close together in one direction -- the same Euler-column mechanism
# COVERAGE_CELL_MM's own comment cites for pucker). Standard professional
# practice for that density is two overlapping passes, not one ultra-tight
# pass: a "cross" pass and a "top" pass. `stage6_fill._crosshatch_fill_paths`
# already builds exactly this shape (two `_fill_paths` calls, angle and
# angle+90, concatenated) for the opt-in textured "crosshatch" look -- that
# technique widens each pass by CROSSHATCH_ROW_SCALE_FACTOR specifically so
# the COMBINED density of both passes stays near ONE ordinary pass. This is
# the identical two-pass mechanism aimed the other way: both passes run at
# the shape's own (fabric-scaled) row_mm, unwidened, so the two together
# land the combined density at 2x a single pass -- row_mm/2, which at the
# shipped 0.40 mm FILL_ROW_MM is 0.20 mm, dead center of the measured
# 0.18-0.21 mm corpus band.
#
# Only a genuinely SOLID element gets the second pass. Doubling the density
# of a thin strip is exactly the distortion risk the two-pass technique
# exists to spend on a wide field instead of a fresh tighter single pass --
# a narrow column does not gain the coverage a wide one does from a second
# full pass, it only doubles the pucker risk for no corpus-measured benefit
# (the corpus finding is specific to "solid elements": machine_hat/lc,
# hotel_fremont's cap panels, not thin lettering fills or open lattice
# work). A shape counts as solid when it still holds real body after being
# eroded half this width -- a thread-wide strip or a fine lattice arm does
# not survive that erosion and stays single-pass; a cap-logo panel easily
# does. See `stage6_fill.is_solid_fill`.
FILL_DENSITY_BOOST_MIN_WIDTH_MM = 3.0

# --- Cross-hatch fill (two angled tatami passes) ----------------------------
# The whole technique is two ordinary `_fill_paths` calls at angle and
# angle+90, concatenated — the exact trick `_underlay_paths`'s
# "double_lattice" style already relies on for its own +-45deg underlay
# passes, just aimed at the visible fill instead of underlay. Nothing new to
# tune except this one knob.

# Multiplier on `row_mm` applied to EACH individual pass, so two overlapping
# passes land at a combined stitch density in the same ballpark as one normal
# single-pass fill instead of roughly doubling it. 2.0 (each pass spaced
# twice as far apart as ordinary tatami) is a starting, reasoned value, not
# sew-out-validated — same caveat as every other tuning constant in this
# file. Lower-stakes than the density constants above already flagged
# pending sew-out, though: cross-hatch ships OPT-IN per-shape or per-design
# only, never a default, so nobody's existing output moves if this number
# turns out to need adjusting later.
CROSSHATCH_ROW_SCALE_FACTOR = 2.0

# --- Wave fill (sinusoidal row wobble) --------------------------------------
# Every interior row point (never the two row-end penetrations, which stay
# exactly on the boundary — the same edge-crispness contract `_row_points`'s
# own docstring states) rides a sine wave perpendicular to the row:
# y + WAVE_AMPLITUDE_MM * sin(2*pi*x/WAVE_LENGTH_MM + phase), phase
# alternating 0/pi by row parity so neighbouring rows move opposite ways at
# any given x instead of stacking into a corrugated-cardboard look. Both
# constants are starting, REASONED values — not sew-out-validated, same
# caveat every tuning constant in this file carries — and lower-stakes than
# the pending-sew-out density constants above for the identical reason
# CROSSHATCH_ROW_SCALE_FACTOR's own comment gives: this ships opt-in only
# (per-shape or per-design), so nobody's existing output moves if either
# number turns out to need adjusting later.

# Wobble height. Small enough to read as texture, not to distort the fill's
# own silhouette — a ninth of FILL_ROW_MM's own row spacing multiplied out
# to a legible scale, and comfortably under half a stitch length, so no row
# turn is thrown far enough off-axis to blur the edge it lands on.
WAVE_AMPLITUDE_MM = 0.35

# Wobble period along the row. Roughly FILL_STITCH_MM's default 3.0 mm times
# a small integer, so one sine cycle spans a handful of stitches: fine
# enough to actually read as a wave at the row's own scale, coarse enough
# not to collapse into per-stitch jitter (indistinguishable from noise) or
# stretch so long it never completes a visible cycle across an ordinary
# shape.
WAVE_LENGTH_MM = 4.0

# --- Chevron fill (zigzag row texture) --------------------------------------
# A deliberately simplified, TEXTURAL herringbone impression at one fill
# angle — not a full multi-angle banded herringbone, which would need new
# column/travel logic (out of scope for this family of purely-geometric row
# variants; see stage6_fill.py's module docstring for the column/travel
# machinery every fill technique here shares untouched). Every interior row
# point alternates +-CHEVRON_AMPLITUDE_MM, same edge-crispness contract as
# wave above: only interior points move, both row ends stay on the boundary.
# Same starting/reasoned, opt-in-only, lower-stakes caveat as
# WAVE_AMPLITUDE_MM.

# Zigzag height, alternating every single interior stitch — a period of two
# stitches, ~6 mm at FILL_STITCH_MM's default 3.0 mm: fine enough to read as
# a zigzag at the row's own stitch scale, coarse enough not to blur into
# noise. A period of one stitch (no alternation at all) would not read as a
# chevron; a period of many stitches would read as occasional bumps, not a
# herringbone texture.
CHEVRON_AMPLITUDE_MM = 0.45

# --- Contour fill (rings instead of rows) -----------------------------------
# The offset-ring tier: uniform inward offsets of the outline, sewn inner to
# outer. Numbers are the pins from docs/fill-techniques-2026-08-01.md §1.3;
# the physics they sit on (0.40 spacing, the 1.0-12.1 stitch window) is
# tatami's, unchanged. Nothing here is mirrored in the browser engine.

# The outermost ring sits half a spacing inside the edge, so the gap between
# the edge and ring 1 matches the gap between ring 1 and ring 2. Insetting a
# full spacing leaves a visible bare margin all the way round the shape.
CONTOUR_FIRST_INSET_FRAC = 0.5

# How far a ring may sit from the path in hand and still be linked into it, as
# a multiple of spacing. Past SOFT the link is stretched and counted; past HARD
# the ring belongs to a different subtree (a neck split the forest) and starts
# a new path that travel bridges. 2.05 rather than 2.0 so a ring exactly two
# spacings away — the ordinary diagonal across a one-ring gap — is not thrown
# out by float noise.
CONTOUR_ENTRY_SOFT = 1.5
CONTOUR_ENTRY_HARD = 2.05

# Law 44. Rings sit one spacing apart — 0.40 mm — so a perpendicular hop to
# the next ring is a 0.40 mm stitch: under MIN_STITCH_MM and inside the
# needle's own hole. The crossing walks at least this far ALONG the ring while
# it translates, making the hop a diagonal of hypot(this, spacing). 1.2 rather
# than the doc's 1.0 because 1.0 IS the floor and a transition landing exactly
# on it has no margin for the float error of two interpolations; 1.2 gives
# hypot(1.2, 0.4) = 1.26 mm, comfortably clear.
CONTOUR_TRANSITION_MIN_MM = 1.2

# Each ring's resample starts this fraction of its own length further round
# than the last. The golden ratio, not a quarter turn: ring circumferences all
# differ, so a fixed rational fraction re-aligns quasi-periodically and
# rebuilds the radial seam it exists to break.
CONTOUR_PHASE_STEP = 0.618

# A ring shorter than three minimum stitches is not a ring, it is the needle
# re-entering its own holes. Dropped, and counted.
CONTOUR_MIN_RING_MM = 3.0

# Offset slivers below this are numerical debris, not fabric to cover.
CONTOUR_MIN_RING_AREA_MM2 = 0.1

# The bare dot EVERY healthy contour shape leaves at its own centre, measured
# with the widest-inscribed-bare-circle instrument (barecircle.py) at the
# shipped 0.40 mm spacing.
#
# UPDATE 2026-08-04 (defect 1, the shrink): originally 0.87, from a 0.863 mm
# measurement common to a bare ring set alone. Two fixes since then close
# most of it — `_refine_terminal_generation` (stage6_contour.py) bisects the
# LAST ring's own inset distance onto the true sewability floor instead of
# wherever the fixed 0.40 mm spacing grid happened to land, and a finishing
# pass (`contour_fill`'s post-ring loop) patches whatever `widest_bare_circle`
# still calls the widest bare spot with an ordinary tatami patch, iterating
# on the instrument itself until it clears CONTOUR_FINISH_MIN_RADIUS_MM or
# the pass budget runs out. Re-measured on the same four shapes: discs of
# r = 3, 5, 15 now read 0.067, 0.070, 0.067 and the dumbbell 0.129 — a
# 0.863 -> ~0.13 mm structural dot, and for scale, tatami's own worst spot on
# the fixture logo measures 0.090 mm, so contour is now within spitting
# distance of tatami's own floor instead of ~10x it. The dumbbell's higher
# figure is real, not noise: its three separate convergence points (both
# lobe centres and the waist) need two finishing patches to close, against
# one for a plain disc, and the shape genuinely does not shrink to the exact
# disc floor. 0.13 keeps the small margin over the measured max the
# original 0.87 (0.863 measured) used.
# History: this constant replaced CONTOUR_STARVED_FRAC (an area-fraction gate
# at 1 %) on 2026-08-04: the area sum was miscalibrated in both directions —
# silent on a 1.47 mm bare core whose rings were annihilated without ever
# being counted (the mitred offset dies, so the area was never charged), and
# firing on shapes whose many small terminal slivers summed past 1 % while no
# single bare spot beat this structural dot (whitebg's Sf5200f3f at 0.499 mm,
# Sb253ebba at 0.644 mm, the dumbbell at 0.863 mm — all old-gate fires, all
# invisible next to a healthy disc's own centre, all measured before the same
# day's terminal-refine + finishing-pass shrink above).
CONTOUR_BARE_CORE_MM = 0.13

# Mitre limit on the inward offset. The reference implementations use 10, which
# lets a sharp corner throw a long spike the needle has to chase out and back.
CONTOUR_MITRE_LIMIT = 2.0

# Law 42's tolerance: how far a chord may bow off the ring it approximates.
# Caps stitch length by curvature at L <= sqrt(8*R*tol). At 0.10 the bow stays
# inside the half-spacing the first ring is already inset by, so a chord on a
# hole ring cannot reach the hole.
CONTOUR_TOLERANCE_MM = 0.10

# Float slack on the post-emission containment clip. Same 0.01 mm the fill's
# travel test uses: enough for interpolation noise on a ring that is inset by
# 0.20 mm anyway, not enough to admit a real escape.
CONTOUR_CLIP_TOL_MM = 0.01

# Underlay rings run this many times the fill spacing — the doc's "coarse ring
# set at 3*s". Contour underlay that follows contours is the one call the
# reference implementations skip: theirs runs at the FILL ANGLE, putting
# straight rows under curved ones.
CONTOUR_UNDERLAY_SPACING_FRAC = 3.0

# Termination guard on the offset loop. A 200 mm hoop at 0.40 mm spacing needs
# 250 generations to reach the middle; this is twice that, and exists only so a
# degenerate offset that never empties cannot spin forever.
CONTOUR_MAX_GENERATIONS = 512

# Bisection precision for the terminal-ring refinement (`_terminal_refine`):
# how close to the true CONTOUR_MIN_RING_MM sewability floor the last ring's
# inset distance is pinned, in mm. 0.005 is an order of magnitude under the
# raster error barecircle.py measures the result with (~0.03 mm/pixel), so
# the refinement is never the limiting source of imprecision.
CONTOUR_TERMINAL_REFINE_TOL_MM = 0.005

# The finishing pass: once the ring set is done (refined terminal ring
# included), whatever polygon barecircle.py's own instrument still calls the
# widest bare spot gets a small ordinary tatami patch (stitch_shape) instead
# of staying empty — driven by `widest_bare_circle` itself, iteratively,
# not by a vector reconstruction of "what the rings missed" (see
# `contour_fill`'s finishing-pass comment for why the vector approach was
# tried first and measured worse).
#
# Below this radius a bare spot is not worth a patch of its own — sub-floor
# ring-to-ring gaps measured on a 15 mm disc top out at 0.048 mm across, an
# order of magnitude under this line, and every genuine core measured
# (structural dot ~0.07-0.13 mm post-refinement, the annihilated star's
# ~0.14-0.5 mm even after patching) clears it easily while patching is still
# worth doing. See CONTOUR_BARE_CORE_MM for the structural-dot measurement
# this floor is judged against.
CONTOUR_FINISH_MIN_RADIUS_MM = 0.15

# Hard cap on finishing-pass iterations per shape. Each pass patches the
# SINGLE widest remaining bare spot (barecircle.py) and re-measures, so a
# healthy shape's one structural dot closes in one pass and this only
# matters for genuinely pathological geometry (a deeply annihilated notched
# interior can need several passes as the widest spot migrates around the
# shape). Bounded so a shape that is not converging — the patch itself too
# thin to sew, or the widest spot oscillating — cannot loop forever; past
# this many passes whatever is still bare is left bare and reported honestly
# through `bare_radius_mm` / `starved`, the same as before this pass existed.
CONTOUR_FINISH_MAX_PATCHES = 8

# Below this area a finishing patch is not worth the emitter call that would
# sew it — the same order of magnitude CONTOUR_MIN_RING_AREA_MM2 draws for a
# ring, for the same reason (numerical debris off a polygon boundary, not
# fabric).
CONTOUR_FINISH_MIN_PATCH_AREA_MM2 = 0.05

# Slack added to a finishing patch's own measured bare radius before
# clipping it back to the shape. The patch is `poly` intersected with a
# plain circle at the bare spot's own centre and radius
# (`widest_bare_circle`), not any reconstruction of the bare region's own
# outline. A circle at EXACTLY the measured radius is tangent to whatever it
# was inscribed in; this margin lets the patch actually overrun the bare
# spot instead of just touching its edge. One ring spacing — the same order
# as the gap the rings themselves leave between passes.
CONTOUR_FINISH_PATCH_MARGIN_MM = 0.4

# Round-join erosion applied to a finishing patch after it is clipped to
# `poly`. `poly.intersection(disc)` is exact but can still inherit a REFLEX
# vertex straight from `poly` itself — measured on the letter-e fixture's
# mouth notch and a 5-point star's spike root: `stitch_shape` (ordinary
# tatami has no law-42 chord clip of its own) emitted a stitch up to
# ~0.55 mm outside the shape at exactly that corner. 0.05 mm already closed
# every reproduction found; this is 2x that for margin, still an order of
# magnitude under CONTOUR_FINISH_PATCH_MARGIN_MM so it costs negligible
# coverage.
CONTOUR_FINISH_EROSION_MM = 0.1

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

# --- Satin entry/exit point (Laws 27-29) ------------------------------------
# Scored on 291 real professional decisions: entering at a stroke's FREE end
# (its open cap, not wherever the skeleton welded it to a junction) matches
# 85.2% of what pros actually sewed; "enter at whichever end sits nearer the
# previous exit" — the rule this replaces — matches only 42.3%. When a stroke
# has no free/junction distinction to lean on (both ends free, or both tucked
# into a junction) there is no structural signal, so proximity alone decides,
# same as before this law.
#
# Law 29 puts a ceiling on it: extra travel paid to reach the structural cap
# instead of the nearer end runs median 5.7 mm, 71.8% within 10 mm, 87.7%
# within 20 mm — past ~20 mm pros mostly stop paying. 10 mm is the corpus
# law doc's own chosen cutoff (docs/corpus-laws-round3-2026-08-01.md, engine-
# mapping table, laws 27-29: "desk-safe, highest value").
#
# NOT implemented: law 28's finer end-CLASS ordering (cap > tee > corner ~=
# butt) among junction ends. That needs classifying each junction end's own
# arm count/angle, which `Stroke` does not currently carry — only the binary
# free/not-free distinction extract_strokes already computes. Left as a
# follow-up, not guessed at here.
STRUCTURAL_ENTRY_BUDGET_MM = 10.0

# --- Push compensation (Law 24) --------------------------------------------
# Pull and push are two different effects in two different directions. Thread
# tension pulls each stitch's two penetrations together, so a column loses
# width ALONG its stitch direction — that is `Fabric.pull_comp_mm`, and it is
# what stage 5 compensates. The fabric that width displaces has to go
# somewhere, and it goes out the ENDS of the column, perpendicular to the
# stitches: a column sewn to the artwork edge lands past it.
#
# The fix is a cutback at each open end, and unlike pull comp it is a length,
# not a width. 0.4 mm is one satin spacing — the single terminal cross — which
# is how the trade describes it ("cut the end back one stitch"). 0.8 mm where
# a border will cover the junction; the border tier does not consume this yet.
#
# Source: Law 24, Embroidery Legacy, medium-high confidence. SEW-OUT GATED —
# playbook Part 4 test 4 is bordered squares at cutback 0/0.4/0.8 mm measuring
# how far the fill peeks past the border. Until that runs this is one expert's
# number, which is why `PipelineConfig.directional_comp` defaults to False.
PUSH_CUTBACK_MM = 0.4

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

# An EDGE-COVERING border is WIDER than round 2's 1.40 claimed
# (docs/corpus-laws-round3-2026-08-01.md law 41, unapplied-rulings table
# :670): real covering columns measure 1.66 mm med (p90 3.83), 2.39 mm on the
# trustworthy >=20 mm subset, and are file-dependent (1.55 to 4.53), so a
# single value is a compromise — the ruling is 1.70. Round 2's 1.40 was a
# different population: closed loops, mostly round letters — a population
# "auto" never sews, because satin-classified shapes never get a border
# (config.py, stage 7). Derived values move with this constant:
# stage6_border._BITE_MAX_MM (width/2, 0.70 -> 0.85), the too-narrow gate,
# stage7's seam-share threshold (2x width, 2.8 -> 3.4 mm), and the bean
# tier's spine inset sits 0.15 mm deeper (inset feeds host.buffer(-inset) on
# the lighten path too).
BORDER_WIDTH_MM = 1.70

# NOT looser than lettering — law 41 refuted round 2's "looser, 0.45, it
# rides an edge that already has coverage" claim: measured on real covering
# borders the density is 0.40 mm (p10 0.36, p90 0.42), IDENTICAL to lettering
# columns; there is no density relaxation, and 0.40 agrees with laws 4 and
# 21. Measured on the RAILS, like law 4 — the spacing between consecutive
# penetrations on the same side of the column.
BORDER_DENSITY_MM = 0.40

# MEASURED, not a boundary condition (docs/corpus-laws-round3-2026-08-01.md,
# law 40). Round two's over-a-fill detector fired ZERO times across 39 files
# because it required a classify()-labelled fill run in the same colour
# block; a region-level re-instrument with no such requirement finds 70
# tracking columns of 633, 41 of which actually cover a fill edge. Centreline
# offset vs. the fill edge (inward positive), covering subset n=41: median
# +0.05 mm (p10 -0.45, p90 +0.20); restricted to the trustworthy >=20 mm-long
# columns, n=25: median +0.00 mm (p10 -0.47, p90 +0.20). Confidence high on
# the number; also unanimous on ordering — 41/41 sewn AFTER the fill they
# cover, 0/41 before. See stage6_border._centre_inset.
BORDER_SEAM_OFFSET_MM = 0.0

# Minimum turn radius forced on a ring before it is offset, so neither rail
# ever has zero radius. Set at 1.5x the pre-law-41 column width (unadjudicated,
# kept when BORDER_WIDTH_MM moved to 1.70); the inner rail's own radius stays
# r - W = 0.40 mm > 0: the inside of a corner crowds (short stitches fix that)
# but can never fold back on itself. Below that a corner is not a corner, it
# is a fold, and law 3 says folds are the only thing professionals split for.
BORDER_CORNER_RADIUS_MM = 2.10

# A shape must have something left inside the column or the "border" is just a
# heavy re-fill of the whole shape. Below it the light tier takes over.
BORDER_HOST_MARGIN_MM = 0.20

# A closed loop shorter than the circumference of a circle of radius 1.40 mm
# is a dot, not an outline. 2*pi*1.40 — the pre-law-41 column width; kept when
# BORDER_WIDTH_MM moved to 1.70 because the loop gate has no adjudication of
# its own.
BORDER_MIN_LOOP_MM = 8.80

# The circuit closes by running past its own start for 1.40 mm (one pre-law-41
# column width; unadjudicated, kept when BORDER_WIDTH_MM moved), at a
# half-station phase shift so the repeated penetrations miss the first holes.
BORDER_CLOSURE_OVERLAP_MM = 1.40

# How far the join may slide from the nearest station to find a flat stretch.
BORDER_JOIN_SEARCH_MM = 3.0

# --- The "significant" border mode's two gates (2026-08-25) ---------------
#
# Kent's rule, in his words: *"a clean satin border around 'significant'
# shapes helps [create pop]. Doing the stitched border is typically very clean
# and smooth, if it's abrupt, it probably doesn't require a border, or is
# wrong."* Two gates, and BOTH are dimensionless on purpose — neither is a
# length, so neither is a physical constant ROADMAP gate 1 reserves for a
# sew-out (contrast BORDER_WIDTH_MM above, which IS corpus-measured and which
# this mode reuses rather than re-deriving).
#
# NOT CORPUS-MEASURED. Both were read off the region census of ONE image
# (`owl_kent.jpg` on its own default route, 35 regions). The two populations
# do separate with an actual empty band between them: the four shapes that
# earn a border score 2.09 / 2.51 / 2.72 / 3.39 per-ring raggedness, and the
# ten significant ones refused as abrupt run 3.91 / 4.02 / 4.53 ... 12.22. So
# the cutoff sits in a real gap rather than slicing through one population —
# but it is ONE image, and it wants real portraits behind it before it counts
# as a ruling. A human face's catchlights and nostrils are exactly the
# small-and-compact population no fixture here covers.
#
# (Correction, 2026-08-25: this comment first read "1.3-2.7" and
# "4.0/11.7/13.6". Those came from an ad-hoc script that paired an
# EXTERIOR-only perimeter with a HOLE-SUBTRACTED area — a formula the shipped
# code never used. Anyone re-deriving them got different numbers and would
# reasonably conclude the code had changed. The figures above are what
# `_raggedness` actually returns.)

# Share of the design's own stitched area a shape must carry to be
# "significant" — DISABLED (0.0) as of 2026-08-25, hours after it shipped at
# 0.0025, because measurement showed it does NOTHING where it was tuned and
# real DAMAGE where it was not. Kept as a live knob rather than deleted so the
# escape hatch survives; `cfg.border_significant_area_share` still overrides.
#
# THE MEASUREMENT, on owl_kent through the real emitter:
#   80 mm  share 0.0025 -> 3 border runs, 479 border stitches
#   80 mm  share 0.0001 -> 3 border runs, 479 border stitches   (identical)
#   160 mm share 0.0025 -> 1 border run,  383 border stitches
#   160 mm share 0.0001 -> 9 border runs, 1352 border stitches
# At the 80 mm the constant was derived on, it is inert: `border_runs` has
# already refused every shape it would drop. At 160 mm it deletes 8 of 9
# borders, and the shapes it deletes measure 4.2-62.3 mm2 — iris, nostril and
# catchlight scale on a portrait sewn at jacket-back size, which is precisely
# the population this file admitted no fixture covers.
#
# WHY IT INVERTS. The metric is dimensionless, but it is not scale-invariant
# in practice: at a larger target width stage 2 resolves MORE regions, so the
# denominator grows and every shape's share shrinks. A fixed share therefore
# gets quietly STRICTER as the design gets bigger — the opposite of what a
# significance floor should do. Do not "fix" this by re-tuning the number; any
# fixed share has the same inversion.
#
# The significance test that actually works is already downstream and is
# physically grounded: `border_runs` refuses a shape too narrow to host a
# column (an absolute mm test against the corpus-measured BORDER_WIDTH_MM) and
# lightens the marginal ones to a bean run. Let it do the job. What remains
# here is the abruptness gate, which is the half that was doing real work.
BORDER_SIGNIFICANT_AREA_SHARE = 0.0

# The "abrupt" gate: isoperimetric ratio, perimeter^2 / (4*pi*area), taken
# PER RING (see stage7_sequence._raggedness for why per ring and not per
# shape). 1.0 is a circle; higher is a more contorted outline for the area
# enclosed. Blanket "auto" spends +60% stitches on owl_kent to make the
# silhouette WORSE; this gate is what stops that.
#
# WHAT IT ACTUALLY MEASURES — corrected 2026-08-25, and the first version of
# this comment got the mechanism wrong. It said a high-raggedness ring is one
# whose border would "trace a pixel staircase". There is no pixel staircase
# to trace: stage 4 already runs Douglas-Peucker (`stage4_vectorize.py`
# approxPolyDP at `cfg.simplify_tol_mm`, config.py:359, 0.2 mm and deliberate)
# and meets that tolerance to within 0.002 mm. What raggedness actually tracks
# is MACRO SHAPE COMPLEXITY — sprawl, not edge noise. Measured on the three
# largest owl_kent regions, solidity (share of its own convex hull a shape
# fills) is 0.873 / 0.476 / 0.329: the two ragged ones are multi-armed
# sprawling shapes, and Gaussian smoothing at 8.6x the current tolerance moves
# region #2's raggedness by 0.04 (11.59 -> 11.55). No smoother can touch this
# number, because it is a SEGMENTATION output, not a contour-quality one.
#
# That is still the right gate for the right reason: a satin border on a
# sprawling multi-armed region follows every arm and inlet and reads as
# clutter rather than definition. But do not reach for a smoother to "fix"
# a shape's raggedness — see MASTER_SCOPE's measured negatives.
#
# Sits in the 3.39-to-3.91 gap measured above, but is NOT centred in it —
# 3.65 would be. Left at 3.5 as a rounder number with real margin either
# side; the honest reason to revisit is portraits, not centring.
#
# Measured alternative REJECTED: fraction of turns over 60 degrees does not
# discriminate at all here (26-67% across every region, big and small),
# because the pixel staircase is universal — it is the ring's overall
# contortion that separates the populations, not its local step angles.
BORDER_ABRUPT_RAGGEDNESS = 3.5

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
UNDERLAY_ZIGZAG_MM = 2.0     # row spacing, zigzag underlay (fill's lattice
                              # underlay only, via stage6_fill.py's
                              # _underlay_paths() -- NOT satin; see
                              # SATIN_ZIGZAG_PITCH_MM below)
UNDERLAY_LATTICE_MM = 2.5    # row spacing, lattice underlay

# Satin's own zigzag-underlay pitch (corpus law 23, docs/corpus-laws-round3-
# 2026-08-01.md). Deliberately a separate constant from UNDERLAY_ZIGZAG_MM:
# that one is shared with fill's lattice underlay (stage6_fill.py), and the
# corpus finding is specific to satin columns, whose zigzag underlay runs
# denser than the generic 2.0 mm pitch -- 1.45 mm crossings, not 2.0. Landed
# 2026-08-05 alongside law 26 and stage6_satin.py's _stroke_underlay() leg-
# width widening; see COVERAGE_WARN_UNITS below for the recalibration this
# and law 26 together required.
SATIN_ZIGZAG_PITCH_MM = 1.45

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
# COVERAGE_WARN_UNITS = 2.5 — recalibrated 2026-08-05 after corpus laws 23 and
# 26 landed (fabrics.py's pique_knit/jersey_tee fill_underlay edge_lattice ->
# edge_run, and SATIN_ZIGZAG_PITCH_MM 2.0 -> 1.45 with the wider 0.82x-column
# zigzag leg below). The line used to be "checked against what our own output
# actually produces" — self-fit to the PRE-law-23/26 engine, which is
# circular: it verifies the counting mechanism, not the threshold. Re-derived
# here two ways that do NOT depend on our own prior output:
#   1. Law 27's own prose is the primary number: "safe classic stack ~= 2.5
#      units". That IS the derivation, not a coincidence to be reproduced.
#   2. Cross-checked against law 28 ("underlay costs 15-20% of an element's
#      stitches but only ~0.1-0.2 coverage units") using the CORRECTED
#      engine's own underlay geometry, computed from stitch geometry alone
#      (0.4mm thread / pitch, same arithmetic _coverage_map uses): fill's
#      generic zigzag underlay (UNDERLAY_ZIGZAG_MM = 2.0mm, now used only by
#      stage6_fill.py's lattice underlay since law 26) prices at 0.4/2.0 =
#      0.208 units, the top of law 28's band almost exactly. Satin's own
#      zigzag underlay (SATIN_ZIGZAG_PITCH_MM = 1.45mm, corpus law 23 —
#      denser than the generic pitch, independently sourced, not fit to
#      match law 28's band) prices at 0.4/1.45 = 0.283, a bit over that band
#      but still cheap. A classic stack — underlay + one full-density fill
#      (1.00) + one satin detail layer (1.00) — lands at 2.21-2.28 units
#      either way: comfortably under 2.5, matching law 27's "safe"
#      classification with headroom, not against it.
# Real fixtures after both laws confirm the same story: the fixture logo
# (whitebg @ left_chest, pique_knit) now measures p50 1.00 / p95 1.49 /
# max 2.57 (was p50 1.20 / p95 1.82 / max 2.55 before law 26 removed the
# lattice pass) and the 160mm heavy-square fixture p50 1.00 / p95 1.00 /
# max 1.59. Typical output sits well under 2.5 either side of the change;
# nothing that was clean before now grazes the line, and nothing that should
# warn is newly silenced by it.
COVERAGE_WARN_UNITS = 2.5

# COVERAGE_BLOCK_UNITS = 3.5 — left EXACTLY as-is, 2026-08-05. Per
# docs/machine-physics-playbook-2026-07-31.md line ~84 this line (unlike
# COVERAGE_WARN_UNITS above) is explicitly tagged sew-out-gated, not
# desk-safe: it is Embrilliance's 6-thread-layer red line translated to our
# units, medium confidence, and part 4 item 2 of the playbook already
# prescribes the test that settles it — a stacked-fill ladder 2.0 -> 4.0
# units in 0.5 steps on twill/tearaway (EMBBOT_SEWOUT_CARD.dst block 2),
# noting the first break and hand-feel. That sew-out has not happened.
# Landing laws 23/26 changes typical coverage readings (see WARN's note
# above) but does not touch this line's own justification, so it stays
# untouched pending Kent's physical test — moving it on desk math alone
# would be exactly the self-fit mistake WARN's recalibration was trying to
# get away from.
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

# How far a FUTURE colour's sewing polygon is eroded before it may count as
# cover for a needle-down link. The already-laid half of stage 7's link cover
# is real emitted thread (rebuilt from `runs`, 2026-08-03); this half cannot
# be — that colour has not been planned when the link is routed — so its
# ARTWORK polygon stands in for its thread, and no tier stitches its whole
# polygon. Measured 2026-08-04 (both committed fixtures, logo_alpha +
# logo_whitebg @ 80 mm / left_chest), real emitted non-travel runs vs the
# artwork polygon `covered_by` quotes, worst case per tier:
#
#   fill:  nearest stitch centreline up to 0.223 mm inside the boundary
#          (thread edge 0.023 mm shy). Interior is honest: rows tile at
#          FILL_ROW_MM, holding a 0.20 mm half-spacing ceiling everywhere.
#   satin: up to 0.501 mm to the nearest centreline at the boundary (thread
#          edge 0.301 mm shy) — the column stops short at tips and fans on
#          curves, exactly the class the 2026-08-03 rebuild proved wrong for
#          the block's own tiers.
#   run:   an outline run covers NO interior at all, so no erosion makes its
#          polygon honest except the one that swallows it — its inradius,
#          measured 0.527/0.539 mm on the fixtures' rescued shapes (shapes
#          under min_detail_mm² sew as outline runs).
#
# The binding number is the run tier's 0.539 mm, plus LINK_COVER_TOL_MM —
# the cover is buffered back OUT by that much for the containment test, so
# the inset must pre-pay it: 0.539 + 0.2 = 0.739, rounded up to 0.75. At
# 0.75 every measured run-tier shape erodes to empty (covers nothing,
# honestly) and every fill/satin boundary shortfall is bounded with margin.
#
# What an inset cannot fix, also measured so nobody re-derives it: hairline
# gaps between fanned satin crosses persist at ANY inset (still there at
# 1.0 mm) — <= 0.127 mm inscribed radius, <= 0.121 mm beyond the thread
# edge, < 1 mm² per shape. Narrower than one thread width; whether that
# clearance shows on fabric is the sew-out question that still gates
# `chain_links`' default.
#
# The two errors are not symmetric: erring big turns a buriable link into a
# jump (a needle-up move, invisible); erring small sews a float on bare
# fabric. Round up, never down.
LINK_COVER_INSET_MM = 0.75

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


# --- Appliqué (docs/specialty-techniques-2026-08-01.md §2) ------------------
# Every number below is carried from that spec with its source tier intact:
# [V] vendor doc, [S] supplier tech sheet, [P] production/trade writeup,
# [D] derived. Nothing here is invented. The offsets are SIGNED NORMALS on the
# digitized boundary B: s < 0 inward (onto the appliqué fabric), s > 0 outward
# (onto the ground garment) — §2.2.

# 1 DST coordinate unit = 1 Melco point = 0.1 mm. Every offset is quantized to
# this BEFORE rail generation so the two cover rails cannot accumulate a
# half-unit drift against each other — §2.2 unit note.
APPLIQUE_QUANTIZE_MM = 0.1

# Layer 1, placement / guide run (§2.5). Single run, never bean: a bean triples
# the perforations that later sit OUTSIDE the cover satin on any shape you
# shrink.
APPLIQUE_PLACEMENT_STITCH_MM = 2.50   # [P]; Melco outline/detail 15-25 pt [V]
APPLIQUE_PLACEMENT_OFFSET_MM = 0.00   # [V] relative to the outline B
APPLIQUE_PLACEMENT_PASSES = 1         # [P] 2 if the base is dark or textured

# Layer 2, cutting line (§2.6). Trim-in-place only, and only where scissors fit.
APPLIQUE_CUTTING_STITCH_MM = 2.00     # [D] shorter than placement — you cut against it
APPLIQUE_CUTTING_OFFSET_MM = 0.00     # [V] coincident with B

# Layer 3, tackdown (§2.7). Offset is relative to the GUIDE RUN, not to B, and
# is a run-stitch-only parameter — §2.2. Inward because the tackdown must
# compress the appliqué against the stabilizer, not the ground fabric: outside
# stitches compress background fabric and cause peeling [P].
APPLIQUE_TACK_OFFSET_MM = -1.00       # [V][P] run / double-run / E spine
APPLIQUE_TACK_STITCH_MM = 2.50        # [V]
APPLIQUE_TACK_PASSES = 2              # [V] double run
APPLIQUE_TACK_WIDTH_MM = 2.00         # [V] zigzag/E only; = W_cover - 2*bury at the 3.0 default

# Layer 4, cover (§2.8).
APPLIQUE_COVER_SPACING_MM = 0.40      # [P]; Melco 4.2 pt [V]
APPLIQUE_COVER_SPACING_MIN_MM = 0.30  # [P] below this the needle cuts the fabric
APPLIQUE_COVER_SPACING_MAX_MM = 0.60  # [P] above this the raw edge shows through
APPLIQUE_COVER_PULL_COMP_MM = 0.20    # [P] up to 0.30 on knits
# Zigzag cover's own spacing, read by stage6_applique._cover_layer only when
# `cover == "zigzag"` — it replaces `geom.spacing_mm` (the satin figure above)
# for that call, rather than stretching one constant to mean two different
# pitches. §2.8 states TWO candidate zigzag spacings with no tie-break between
# them: 1.69 mm (= 15 SPI) `[S]` Stahls', or 3.0 mm, Melco's ZigZag-appliqué
# preset default of 30 pt `[V]`. This module already leans Melco/`[V]` where
# the spec offers a choice (`APPLIQUE_COVER_SPACING_MM` above cites Melco's
# 4.2 pt; `APPLIQUE_TACK_STITCH_MM`, `APPLIQUE_TACK_PASSES` do too), so 3.0 mm
# is picked for consistency with the rest of this file's defaults, NOT because
# it was sewn out and measured — it wasn't. Flagged as an open question a real
# sew-out could revise; see `docs/specialty-techniques-2026-08-01.md` §2.8 and
# §2.10's material matrix (which prints the 1.69 mm figure against tackle
# twill specifically) before changing it.
APPLIQUE_ZIGZAG_COVER_SPACING_MM = 3.0  # [V] Melco 30pt preset; unvalidated by sew-out
# Applied in stage6_applique._cover_layer, the same direction as
# Fabric.pull_comp_mm on an ordinary satin column: each rail moves `this`
# further from the other, so the stitched column is `2*this` wider than the
# solved width (see that function's docstring for the measured before/after).
# The "up to 0.30 on knits" note above is context, not a by-material table —
# there is no knit-specific override wired in, only the single 0.20 mm value.
# Stahls' publishes 4-8 stitches of closure overlap past the start point [S].
# Applied in stage6_applique._cover_layer, replacing the border module's
# generic BORDER_CLOSURE_OVERLAP_MM (a distance) for this call site only.
APPLIQUE_CLOSURE_OVERLAP_STITCHES = 6

# The tolerance stack (§2.3). No source states it as an equation; it is [D],
# and it then validates against four independent published number sets.
APPLIQUE_MARGIN_BURY_MM = 0.50        # [D] margin to hide the tackdown thread
APPLIQUE_MARGIN_EDGE_MM = 0.50        # [D] margin to overshoot the raw edge
# Trim clearance band [t_lo, t_hi] by shop discipline. t_hi is the published
# axis (§2.3 validation table); t_lo = 0.30 is recovered from §2.4's worked
# default, where the raw edge lands at s = o_tack + t_lo = -1.00 + 0.30 = -0.70.
APPLIQUE_TRIM_CLEARANCE_MM = {
    "tight":  (0.30, 1.5),   # [P] duckbill scissors -> W_req 2.5 mm ("risky")
    "normal": (0.30, 2.0),   # [P] beginner safe zone 3.0-3.8; Hatch baseline 3.00
    "loose":  (0.30, 3.0),   # [P] Melco DS11 practice: cover 40 pt = 4.0 mm
}
# Pre-cut placement error e. Governs W_req = 2*(e + m_edge) instead of the trim
# band — §2.3, and the heat-tacked row is the strongest confirmation available
# (Stahls' Poly-Twill publishes 2 mm for 1"-3" letters at e ~ 0.4).
APPLIQUE_PLACEMENT_ERROR_MM = {"hand": 0.75, "heat_tacked": 0.40}   # [V][S]

# Surplus goes INWARD: an operator can under-trim, but the tackdown thread hard-
# stops over-trimming. The production floor calls this the 65/35 rule [P].
# Pre-cut has no trim step and therefore no asymmetry — 50/50, centred on B [V].
APPLIQUE_INSIDE_SHARE_TRIM = 0.65     # [P]
APPLIQUE_INSIDE_SHARE_PRECUT = 0.50   # [V]

# Cover width bounds. The 2.5 floor is §2.13's own clamp ("absolute minimum:
# 2.5 mm (risky)" [P]); note it sits ABOVE the twill material floor below and
# above Stahls' published 2 mm, so the clamp is what binds on pre-cut twill —
# a deliberate conservatism, not an oversight. 5.0 is the snag ceiling [D].
# Whichever bound binds, `solve_cover_width`'s own "clamped" field says so and
# stage6_applique.check_gates turns it into APPLIQUE_COVER_WIDTH_CLAMPED.
APPLIQUE_COVER_WIDTH_FLOOR_MM = 2.50
APPLIQUE_COVER_WIDTH_MAX_MM = 5.00
# W_floor_material, §2.13. Only binds where it exceeds the 2.5 clamp floor.
APPLIQUE_COVER_FLOOR_BY_MATERIAL = {
    "twill": 2.0, "felt": 2.5, "woven": 3.0, "knit": 3.0, "loose_weave": 3.5,
}

# Gates (§2.12) — all [D], all must be enforced.
# A shape narrower than `2*|c_in| + this` has no fabric left showing between the
# two inner rails. §2.12 prints 5.9 mm, which is the floor for §2.4's rails
# (c_in -1.95); we sew §2.13's (c_in -1.50, see stage6_applique.cover_rails), so
# the shipped floor is 4.0 mm — measured by ribbon sweep, the gate fires at
# 3.5 mm and clears at 4.0 mm exactly. It falls through to plain satin and the
# engine must SAY it did.
APPLIQUE_MIN_FEATURE_MARGIN_MM = 1.0
# Scissors must physically fit to cut the piece. Two separate floors, one per
# mode: pre-cut is hand-cut from sheet stock BEFORE placement (no in-hoop trim
# step to fall back to, so the floor is lower), trim-in-place is cut IN THE
# HOOP after tackdown (tighter access, so the floor is higher). Fed by
# `narrowest_passage_diameter`, not `min_inscribed_diameter` — see that
# function's docstring for why the single-largest-inscribed-circle measure is
# blind to a dog-bone-shaped piece's own neck.
APPLIQUE_MIN_INSCRIBED_PRECUT_MM = 8.0
APPLIQUE_MIN_INSCRIBED_TRIM_MM = 12.0
# Below |c_in| + this, the cover's inner rail self-intersects on a concave turn.
APPLIQUE_MIN_CONCAVE_MARGIN_MM = 0.3
# A hole smaller than this cannot be trimmed in the hoop; force pre-cut.
APPLIQUE_MIN_HOLE_DIAMETER_MM = 15.0

# Multi-piece (§2.11). The one hard vendor number: Wilcom states it directly —
# "Set the cutting overlap to half the width of the cover stitching" [V], and
# Hatch's Partial Appliqué tool is documented accurate to +-1/2 the cover width.
# NOT the same thing as `APPLIQUE_CLOSURE_OVERLAP_STITCHES` above despite the
# similar name: this is how far one piece's CUTTING BOUNDARY dilates into a
# neighbour it overlaps (Mode B multi-piece batching, §2.11), not how far a
# single piece's own cover circuit overlaps its own start. Mode B is not
# built — `applique_pass` only detects and warns overlapping pieces
# (`APPLIQUE_PIECES_OVERLAP`) — so this constant stays unread until it is.
APPLIQUE_OVERLAP_ALLOWANCE_FRAC = 0.5

# Machine speed for the worksheet — the Tajima will not infer it [P] (§2.10).
APPLIQUE_COVER_SPM = 700
APPLIQUE_TRIM_HEAVY_SPM = 650
