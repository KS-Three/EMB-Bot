# Flag history: tier B1, satin construction (folded 2026-11-19)

Sixteen switches, all ON by default, folded into the code (the `cfg.X == True` path kept, the
False branch and the `PipelineConfig` field deleted; `docs/flag-audit-2026-11-19.md`). Each
section below is the field's own comment block as it stood in `config.py`, kept for the
evidence and PR pointers. The names are in `RETIRED_FIELDS`, so an old snapshot or a service
request that still sends one is ignored rather than refused.

## `satin_corner_twigs`

```
The spur pruner's structure rule (lettering construction plan step 3,
2026-09-19; the letterform study's mechanism #2). `_prune_spurs`
erases a corner's short twig and with it the junction's degree, so a
letter's diagonal and stem weld into one column folding through the
corner (PRECISION's N, Becker's R foot: the bare bottom-right).
Keeping every twig instead hooks a square-capped bar's spine into its
corner (the H defect, `test_pushcomp`'s rectangle). ON, a node with
two short free arms and one longer arm is a cap and both arms go
whatever their exact length; a node with one short free arm between
two longer arms is a corner and the twig stays, holding the junction
open for `_merge_through_junctions`. Measured 2026-09-19 (scope-
history, step 3a): the fixture's satin self-crossing pairs 277 -> 103
at 2,480 -> 2,192 stitches; nine logos 1,813 -> 1,004 at trims 486 ->
488, uncovered unchanged, stitches +588 of which Becker's band at
100 mm is +725 (three more strokes, each with its own underlay). No
physical constant. Built OFF and **DEFAULT ON the same day -- Kent's
flip** over the nine-logo numbers and the renders; False is the
pre-flip pruner, byte for byte.
```

## `satin_crown_cover`

```
`satin_tip_caps` (2026-09-29, MASTER_SCOPE defect 49): a junction node
where the arms meet at a TAPERED TIP is a cap, not a junction, and is
capped instead of tucked.

Under `satin_rail_comp` a shape keeps its artwork polygon, and the
artwork's sharp tips are sharp: ENTHUSIAST's A decomposes into 4 strokes
against the grown polygon's 2, and its apex becomes a NODE where two
arms end rather than a point one stroke runs through. Both ends then
read `free_end=False`, so `_extend_to_cap` -- the function whose entire
job is that the medial axis stops half a width short of a cap -- never
runs, and the junction trim pulls both arms back from the node on top of
it. Measured 2026-09-29: the column reaches within 0.08 mm of the apex
off the rails and stops 1.63 mm short on them, leaving a 3.61 mm2
triangle at 0.71 mm half-width -- the fixture's largest bare component,
and under preflight's `_UNCOVERED_MIN_PATCH_MM2` (5.0) so nothing warns.
Three of nine corpus logos grow an end gap of this class
(`tools/bare_anatomy.py --corpus`).

ON, an end at a node with no single owner to tuck under is CAPPED when
the boundary sits within `_TIP_REACH_HALVES` sewn half-widths along its
own end tangent -- a tip -- and tucked as before when it does not, which
is every blob junction (an arm's tangent crosses the whole ball). The
reach gate is what separates them and it is the only new number here.
False is the pre-flip engine, byte-identical on all nine corpus logos
(plan digests across two trees, 2026-09-29).

DEFAULT ON since 2026-09-29, Kent's flip on the corpus price
(scope-history, the nine-logo table): bare artwork falls on ALL NINE
and end gaps on all nine -- becker 182.07 -> 160.69 mm2, golden_tee
56.38 -> 46.20, bridge 59.57 -> 52.30, screenshot 32.79 -> 27.67 and
its worst component 1.94 -> 0.91. The worst component improves on
three, holds on five and rises on one by 0.05 mm2 (fremont). The price
is thread: a median of about +3.6% stitches, +0.5% at best, and
+12.7% with +11 trims on golden_tee -- which is also the largest
coverage gain (-18% bare). Corpus total 91,102 -> 94,929 stitches,
**+4.2%** (this read 96,929 / +6.4% when first written on 2026-09-29 --
a transcription slip in a figure nobody had re-derived; corrected
2026-09-30 by summing the per-fixture column in code rather than by
hand, which is how it was got wrong).
No sew-out backs it; whether a gap at a letter tip shows on cloth is
the card's question, and the flip was taken on the instrument.

WIDENING RETRACTED 2026-09-30, the same day it was built. Kent ruled
the construction -- "a tip's two arms BOTH cap, and overlap" -- and
dropping the `under is None` gate does implement it, but it REGRESSES
the metric a customer sees: ENTHUSIAST's `lost_frac` 0.2573 -> 0.2661
against a 0.26 bar, 100% overshoot and 0% unsewn
(`tests/test_lettering_coverage_regression.py`, which says in terms
"Do NOT raise the bar to make this pass"). The apex work was priced on
`tools/bare_anatomy.py` -- COVERAGE, ink with no thread on it -- and
that instrument cannot see thread landing OUTSIDE the ink, which is
what the widening adds. Same pattern as `satin_rails_follow_edge`,
already measured and rejected as the cure. MASTER_SCOPE defect 49 is
NOT closed. What follows describes the retracted widening:

The gate no longer requires `under is None`:
at ENTHUSIAST's A apex `_corner_forks` names a partner BOTH ways, each
arm tucking under the other, so neither capped the point and the letter
sewed bare. That population IS what the ruling is about. On the nine
logos, bare artwork and end bare now fall on ALL NINE -- becker
182.07 -> 153.19 mm2, bridge 59.57 -> 47.69, golden_tee 56.38 -> 43.75,
drone 40.19 -> 32.52, screenshot 32.79 -> 25.14 -- and the fixture's
worst component goes 3.61 mm2 @0.71mm to 0.53 @0.19. Corpus total
91,102 -> 96,606 (+6.0%). Those numbers stand as measured and are the
reason the construction is worth returning to -- but they are all
COVERAGE, and the coverage gain is not what the guard reads.
DOCTRINE 2026-09-30, "Coverage is not the metric a customer sees".
`satin_crown_cover` (2026-09-30, MASTER_SCOPE defect 50, Kent's ruling
on `docs/superpowers/plans/2026-09-30-crown-cover.md` §7): the junction
cover with its junction gate removed and `ARTWORK_UNCOVERED`'s own
thresholds, on EVERY satin shape rather than only where a junction sits.

What it is for: `satin_lettering_split` leaves 11 holes / 22.9 mm2 at
the crowns of curved letters on MARINE 127.4 where the fill lane leaves
none, and the crowns are not in any column -- the strokes' union leaves
wedges no stroke claims, 4 of the 11 at a node between two sub-strokes.
Five rail and pitch arms are refuted (DOCTRINE 2026-09-30) and every one
that moved a crown made `lost_frac` worse, which is what says the lever
is a cover rather than a wider or denser column.

It sews SATIN only, per Kent's 2026-09-09 ruling that no tatami goes
inside a satin shape; a wedge that cannot carry a column is skipped
rather than filled, and how many those are is a number this build
reports rather than a question asked in the abstract.

Built OFF. Flipped only on the corpus table AND `lost_frac`: the 09-30
apex widening closed its hole and was retracted the same day for
spending 0.0088 of `lost_frac` on overshoot, and a cover that spills
thread outside the artwork fails for exactly that reason.

FLIPPED ON 2026-10-02 (Kent's call), on exactly that evidence: MARINE
127.4 11 -> 1 hole (22.9 -> 1.5 mm2) at +2.6% stitches, `lost_frac`
0.1800 -> 0.1730; corpus holes 20 -> 10 with `lost_frac` never rising.
False is the pre-flip engine, byte for byte; tests whose numbers were
read on it hold it OFF (`tests/conftest.py`, PRE_FLIP).
```

## `satin_exit_toward_next`

```
The lettering yardstick's trims gap, read with a per-trim census
(2026-09-19, scope-history): traced MARINE at 80 mm sews 13 trims
against the typed word's 3, and across the nine logos the lettering
trims fall in three buckets -- the hop from one letter to the NEXT
(the biggest: the Euler walk starts nearest the needle and ends
wherever the trail runs out, so the next letter is a jump over
`trim_at`), the walk refusing a within-letter hop (no unsewn spine
left), and the hop from a stroke's underlay to its own column (the
column is cap-extended and, under the stack, run into the node; the
underlay is not, so the hop reads past `trim_at` inside the column).
Two levers, one flag each, both built OFF for Kent's flip.

`satin_exit_toward_next`: the Euler walk's END is chosen too. With
two or more odd nodes the walk runs between two of them; today the
start is the odd node nearest the needle and the end falls where the
postman pairing leaves it. On, stage 7 hands the emitter the nearest
point of the next shape it will sew (`end_near`, the nearest
remaining shape by polygon distance -- the pick rule's own answer
once the needle is there) and the walk picks the (start, end) pair of
odd nodes that minimises the entry hop plus the exit hop, pairing the
rest as before; with no odd node (a closed web) the start minimises
the two hops together. Nothing about WHICH edges are travel changes,
only which end the walk leaves by. False is the walk as shipped.
Measured 2026-09-19 (scope-history, "the lettering yardstick's trims
gap"): MARINE 80 mm 13 -> 9 trims at 1,969 -> 1,953 stitches, its
letter-to-letter hops 6 -> 3 (the typed word's three); nine logos
478 -> 465 trims at -103 stitches, uncovered and finding codes
unchanged -- tires 10 -> 6, ENTHUSIAST 19 -> 12, Golden Tee 48 -> 43,
gaulke 30 -> 34 the one cost. Built OFF and FLIPPED ON the same day
-- Kent's call 2026-09-19 over those numbers (lever 2 below stays
OFF on the same call). False is the walk as shipped before it, byte
for byte, and `tests/test_trim_levers.py` pins both sides.
```

## `satin_house_anchor`

```
The house angle ANCHORED to the line of text (lettering construction
plan step 1, 2026-09-19; `textcluster.SATIN_HOUSE_STEM_WINDOW_DEG`
has the mechanism). Both votes above decide the house from EVERY
stroke of the group, and lettering with diagonals gets an answer the
diagonals pulled off the stems' perpendicular the adopted rule names:
of the 24 lettering groups on the nine real logos, the doubled-angle
vote accepts twelve that make a line and have stems, and puts NINE of
them 12-79 deg off their own line of text on upright words
(enthusiast's subline 130 deg, fremont 98, drone 115 / 108); the font
word HOTEL 27 deg, and 45 once it is turned 20 deg -- the vote does
not follow the art. ON, a group that makes a line takes the
line plus the slant of its STEMS -- the strokes within the lean cap
of the line's normal, median offset -- so an upright word sews square
to its line wherever the art is rotated, and a leaned script keeps
its lean. The votes still answer a group with no line and a group
with no stems (the bridge logo's wheel spokes). Not a physical
constant. Built OFF and measured (scope-history 2026-09-19, step 1:
drone's satin self-crossings 496 -> 430 at +167 stitches / +5 trims,
Fremont's 87 -> 66; THERMAL then shows the 09-03 rule's stems-square,
bars-perpendicular look where the vote's accidental 108 deg had
leaned everything one way -- put to Kent with the render, and he kept
the fonts' bar rule); **DEFAULT ON the same day -- Kent's flip.**
False is the pre-flip engine, byte for byte.
```

## `satin_house_from_line`

```
The house angle's THIRD reading, for a line of lettering BOTH votes
refuse: the cross runs ALONG the line of text, which under the
stitch-angle rule is the stems' perpendicular for upright lettering
(the stems are the family square to the line — the rule's own
correction, 2026-09-03). Found building the lettering construction
(2026-09-19, `docs/lettering-route-review-2026-09-19.md`): a block
word with diagonals — "MARINE" in `manga_impact`, traced at 80 mm —
groups as one line of seven letters and then gets NO house at all,
because its verticals and horizontals cancel in doubled-angle space
(nR^2 5.0 against the 6.9 bar) and its diagonals pull the four-fold
resultant to 0.164, under the 0.25 floor whose own comment names "the
diagonal blind spot" as where it would first be found wanting. The
same word at 127 mm passes (17.6), so the outcome was deciding on
size, and the fallback the pass had — per-stroke tangents — is the
worst answer for a word: the cross angles read 0.23 concentration,
the "indistinguishable from random" class of the 2026-08-26 study.
ON, such a group takes the line's own direction as its cross; every
group either vote accepts is untouched, and a group with no line
(`_line_of_text_deg` None — a blob, a short two-line wordmark) still
fails open. A leaned script would have passed the first vote; the
per-stroke fade past the 30 deg cap (`_clamp_to_span`) still applies
to every diagonal. Not a physical constant. Built OFF and measured
(scope-history 2026-09-19: it fires on three of the nine real logos'
24 lettering groups — the ENTHUSIAST wordmark, whose satin runs' cross
concentration goes 0.059 -> 0.287 at +7 stitches / +1 trim, and two
tiny groups on the phone screenshot); **DEFAULT ON the same day —
Kent's flip.** False is the fail-open behaviour, byte for byte.
```

## `satin_junction_stack`

```
The bold-letter junction sewn as the pro sews it (junction construction
plan `2026-09-19-junction-construction.md`; Kent's ruling: A + B + C as
one flag). A: a weld through a node is REFUSED past
`stage6_satin._STACK_WELD_TURN_DEG` of turn by the merge's own baseline
and both arms end at the node -- a two-arm node then takes the corner
path (one arm owns the corner and is extended, the other tucks). The
number is read off the corpus with `tools/weld_turns.py`: the seam
pairs sit in the 30-60 deg welds (1,420 of 1,607), the R of the 127 mm
fixture folds at 44 deg. B: an arm ending at a meeting of several
runs INTO the node by its own half-width, so the arms stack there as
the pro's do (his p95 4-7 layers inside a MARINE junction blob against
our 2-4). C: the satin junction cover (`satin_patch_junctions =
"satin"`) under the arms for whatever is still bare. Measured
2026-09-19 (scope-history, the junction build): the R fixture at
127 mm under the split flag 311 -> 0 self-crossing pairs at 7,253 ->
7,283 stitches and trims 34 -> 44, uncovered 0.0 both ways; MARINE
at 80 mm 103 -> 0 at trims 7 -> 9; Becker at 100 mm under the split
flag uncovered 35.5 -> 0.0. The layers inside the junctions do NOT
rise to the pro's (p95 3.3-4.2 against his 3.9-7.2): B overlaps the
ends, it does not stack them. Built OFF and FLIPPED ON the same day
-- Kent's call 2026-09-19 over the fixtures, the nine-logo sheet
(stitches +0.7%, crossings 1,004 -> 596, uncovered never up, trims
476 -> 489 with Bridge Bar's +13 the cost and gaulke's -9 the gain)
and the goldens byte-identical. False is the pre-flip merge, tuck and
cover byte for byte.
```

## `satin_lettering_split`

```
Split, never fill, for lettering (lettering construction plan step 4,
2026-09-19; Kent's 2026-09-11 rule for the browser lettering engine,
applied on the traced path). A text-cluster member is classified and
sewn with NO width ceiling -- `classify_ribbon`'s width gates never
send a letter to tatami, the per-stroke rung reads its arms, and the
emitter's per-station cap is lifted with the wide-column fold guard
(`_fold_caps`) holding every bend -- so a wide letter stroke is a
split-satin column (crosses over `SPLIT_SATIN_ABOVE_MM` split as they
always did), not a fill. The ribbon gates that are about SHAPE
(aspect, irregularity, elongation) still apply: a blob still fills.
Only lettering (`meta["text_candidate"]`) is touched; every other
shape keeps `machine.satin_ceiling_mm`. Measured 2026-09-19 (scope-
history, step 4): MARINE traced at 127 mm, fill 6 -> satin 6 at
9,642 -> 7,753 stitches, trims 31 -> 47 -- and 311 satin self-
crossings, every one in the R's junction ball (DOCTRINE 2026-09-09:
a junction blob is not a column; this lifts the ceiling, it does not
build the junction); Becker at 100 mm 12,037 -> 9,056 at trims 39 ->
71; MARINE at 80 mm +328 stitches, the zigzag underlay the oversize
skip used to withhold. No physical constant moves: the ceiling is lifted
for one population the pro sews as columns (7-23% of Becker's over
5 mm), not re-tuned. Built OFF and KEPT OFF on Kent's call the same
day, on the R's fanning junction ball; then FLIPPED ON later that day
once `satin_junction_stack` (below) took the fold out of the R (311
-> 0 self-crossing pairs) and the split-satin density finding proved
to be the instrument (preflight now strips the splits before reading
the rail pitch). Kent's call over the R fixture at 127 mm: split, no
fold, no finding, 7,283 stitches / 44 trims against the fill's 9,642
/ 31. False is the pre-flip engine byte for byte: a text-cluster
member over the ceiling fills.
```

## `satin_rail_comp`

```
Pull compensation on the RAILS instead of the polygon (quality review
2026-09-08 item 6, built 2026-09-09). Stage 5 grows every shape by the
fabric's pull with a round join and the satin tier skeletonises the
GROWN polygon: a 0.3 mm arc on every convex corner (PRECISION N: 21
vertices -> 152), every exterior slot 2 x pull narrower, and the
skeleton welding across the slots the growth sealed (THERMAL E: four
strokes on the artwork, two on the grown polygon -- measured 2026-09-09,
`tools/rail_comp.py`). ON, a satin-tier shape keeps its ARTWORK polygon
in stage 5 (fills grow as before) and `_rail_points` moves each rail
outward along its cross by the same `Fabric.pull_comp_mm` the buffer
gave it, held back only where the push would close a counter under
`min_detail_mm` -- the rail-side twin of stage 5's hole hold. The
AMOUNT is untouched (gate 1); only where it lands moves. Widened
lettering keeps its compensated column. Measured 2026-09-09 (pique,
`tools/rail_comp.py --compare`): thread-vs-target IoU ENTHUSIAST
0.876 -> 0.897, drone 0.797 -> 0.838, Fremont 0.675 -> 0.836, Becker
0.887 -> 0.884; trims 26 -> 22 / 96 -> 83 / 46 -> 45 / 36 -> 40;
thread sewn outside the artwork 147-322 mm2 -> 0. The skeleton is the
artwork's; the grown polygon's with artwork rails was measured too
(plan doc 4c) and is the safer decomposition on a blocky source --
**RULED 2026-09-19, Kent: the artwork, as shipped** (re-measured that
day with the lettering steps ON: IoU-to-target Fremont 0.681 -> 0.836,
ENTHUSIAST 0.875 -> 0.900, drone 0.803 -> 0.826; meadow 0.811 ->
0.779 at +340 stitches). Was DEFAULT OFF, byte-identical off, its flip
Kent's on a sew-out, the render and the goldens. **FLIPPED ON
2026-09-28, Kent, on the render**: the labelled sitting
(`docs/kent-review-2026-09-28.md`) read it after-better on becker,
bridge, ENTHUSIAST, Fremont and tires, before-better nowhere, both-bad
on the four logos bad under every arm; the only pending flag his eye
favoured. The sew-out is still owed (the AMOUNT is the fabric's and
unchanged; only where it lands moved). OFF is the pre-09-28 path.
**Priced when it landed (2026-09-29, `docs/kent-review-2026-09-28.md`
"Outcome"), by the suite and not by the render:** MARINE at 80 mm goes
9 -> 22 trims at +15% stitches (letter-to-shape hops 3 -> 6; the
09-19 levers do not buy it back; 21 once the walk's target was put
back on the web the same day, corpus 671 -> 654 -- DOCTRINE
2026-09-29), ENTHUSIAST at 80 mm reads
`lost_frac` 0.2748 -> 0.2565 -- under its 0.26 bar for the first time
since 768de79e -- for bare artwork 6.27 -> 7.10%, and Becker at 114 mm
under `wide_columns` loses the fold guard's margin (5.38 -> 7.47).
The trims are pinned as a ceiling in `tests/test_rail_comp.py`, and
the price is ACCEPTED -- Kent, 2026-09-29, shown the table: *"Take the
price, let it merge"* -- so the MARINE trims and the ENTHUSIAST bare
artwork are an accepted price, not open defects. Measured the same
night, the mechanism is NOT the rail model's under-reach (that share
fell, 19.3 -> 14.7% on ENTHUSIAST): the bare artwork rises at Becker's
junctions (1.39 -> 3.80% on the satin-only instrument; two thirds of
it is the C's bowl routed to FILL by the sewn-terms width check, so
with fill counted Becker reads 6.72 -> 8.08%, the rest sparse crosses
at the wordmark's junctions) and along ENTHUSIAST's rails (2.06 ->
4.12%, open), and the
trims are the artwork skeleton's finer decomposition (MARINE's R 5 -> 8
strokes, 8 -> 14 odd nodes; the walk jumps more). Those two are what
lowers the ceiling; DOCTRINE 2026-09-28 has the numbers. The tuck was
one of them and is fixed (2026-09-29, with the C's bowl): its entry
floor and stack reach-in read the ARTWORK half-width under rail comp,
a pull short of what the grown polygon sews; in sewn terms MARINE
bare 7.38 -> 7.03% at +32 stitches, bridge 99 -> 96 trims, corpus
654 -> 651. The C's bowl itself -- two thirds of Becker's
junction bare -- is the cover's FILL by design, an 8 mm blob no
column spans, not the tuck's; DOCTRINE 2026-09-29. And golden_tee's
+65% stitches (6,892 -> 11,377) were the SEAMS of the on-rails
polygon -- stage 5's artwork-union-reach-minus-earlier boundary,
a hairline notch or sliver wherever two independently vectorised
edges meet, a branch each to the medial axis (178 -> 494 strokes):
fixed the same day, the skeleton reads that polygon with the seams
of its construction closed (`stage6_satin._close_seams`, hairline
fills touching boundary stage 5 added, nothing on the artwork's
own), golden_tee 11,377 -> 7,966, MARINE byte-identical, corpus
trims 651 -> 640. Since 2026-09-30 the rails, caps and underlay
read that closed polygon too, so a spine down a closed seam is not
pinched by the seam's walls.
```

## `satin_tip_caps`

```

```

## `satin_underlay_short_columns`

```
`satin_underlay_short_columns` (built OFF 2026-10-22, Kent's flip after
a sew-out -- underlay is a physical constant, ROADMAP gate 1): the
columns our two short rules leave bare get the centre run the pro
puts under his. Read on his 27 job DSTs (`tools/pro_satin_underlay.py`;
TIRES HAT 3D is puff foam and bare by design): a centre run under
83-97% of satin columns in every length and width band, columns under
5 mm long bare 0-13% per job where ours are 46% (audit row 5b). Ours
skip two ways: a shape whose artwork extent is under
`machine.SATIN_UNDERLAY_MIN_EXTENT_MM` sews every column bare (law
50's first rung, stage 7, satin tier and Column lane alike), and a
stroke whose spine is under `machine.UNDERLAY_STITCH_MM` gets no run
at all (`stage6_satin._stroke_underlay`); the Column lane has its own
1.8 mm floor (`columns._centre_underlay`). ON, the small shape keeps
the fabric's satin underlay style and both floors drop to one stitch
(`machine.MIN_STITCH_MM`). The zigzag threshold, its pitch and the
hairline tier do not move: the brief's "3.5 mm pitch" was row 5a's
WIDTH threshold, and his zigzag's share and pitch swing with the
reader's satin gate (0.6-1.3 mm per leg), so neither is settled.
Browser twin: `underlayShortColumns` (src/satinfont.js, the lettering
engine's cap-height rung). False is the engine byte for byte.
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `small_solids_satin`

```
Small SOLIDS as one satin dot (2026-10-20, built OFF). The run tier sews
a shape under the area floor (`min_detail_mm` ** 2) as a bean circuit on
its OUTLINE, which reads solid only when the stroke is narrower than the
thread is wide. Proseal at the pro's 85.9 mm Hat: the "+" (1.52 x 1.52
mm, 1.11 mm^2) and six teal spray hexagons (1.1-1.3 mm, 1.11-1.61 mm^2)
sewed as rings with bare cloth inside; the pro's file sews each as one
satin blob. ON: a rescued shape that is not lettering, has no hole, and
whose ring would leave its inside bare -- `buffer(-laid / 2)` at or over
`machine.RUN_MIN_AREA_MM2` (the run tier's own one-penetration floor;
laid = the block's `thread_profile().width_mm`) -- sews ONE satin column
along its long axis, each cross the shape's own width, on the ARTWORK
polygon (`stage6_satin.small_solid_satin`, the junction cover's
principal-spine column). No new constant; whether a 1.2 mm satin dot
holds on a cap is a sew-out question (ROADMAP gate 1). A shape the
column cannot sew keeps the ring. False, byte-identical.
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `compact_solids_satin`

```
Compact solids sew as one satin column, not a fill with a ring round
it (2026-10-22, built OFF; Proseal's blue bubbles). The rule above
covers a solid UNDER the detail floor; this is the same answer for one
the fill tier takes. Proseal at the pro's 85.9 mm Hat: the sixteen
spray hexagons at or over the floor (2.0-3.7 mm across) fail the ribbon
classifier's aspect test (`classify_ribbon`: a blob's length estimate
is ~1.3 widths against the 3 a ribbon needs), sew as tatami rows, and
the bean edge cap (`edge_cap="bean"`, every row end in open air) then
draws a ring round each one -- the "satin border" Kent saw. The pro's
DST sews every hexagon, 1.6 to 4.8 mm across, as ONE satin blob: 15-32
stitches at 1.1-2.8 mm, nothing round it, and no fill anywhere in the
spray. ON: a shape the classifier refused for ASPECT only (its width
already fits the ceiling), not lettering, no hole, not riding a design
ramp, whose ring would leave its inside bare (`is_small_solid`, the
rule above's own test), sews `small_solid_satin` at the block's satin
pitch and the design's satin ceiling. A satin run is linear cover, so
the edge cap omits that edge on its own -- no cap rule changes. A
shape the column cannot sew (a chord over the ceiling, fewer than two
crosses) keeps the fill. No new constant: the ceiling is
`machine.satin_ceiling_mm` (5.0 hat), the pitch the satin tier's own.
Whether a 4.8 mm satin dot holds on a cap is the same gate-1 question
the rule above carries. False, byte-identical (tests/test_compact_solids_satin.py).
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `fine_bars_satin`

```
Fine ink bars sew satin (`columns.is_fine_bar`, built OFF 2026-10-25,
Kent: "measure what the pro does with small symbols and fine line art
... then propose a rule to build OFF"). The pro sews every free-standing
thin ink bar as ONE satin at its drawn width plus his ordinary pull
(about 0.86-1.10 mm of needle) in all 5 artworks that have them (To a
T, Precision Drone, Hotel Fremont, Gaulke, Golden Tee); ours sends every
bar under the area floor (`min_detail_mm`^2) to a hollow bean ring, so a
parallel set of speed rules sews half bold, half thin. ON, a non-
lettering, hole-free, ink-coloured stem under the floor -- aspect
`STEM_MIN_ASPECT` or under one `SATIN_MIN_CROSS_MM` across, not lighter
than everything it touches -- skips the run rescue for the ordinary
satin tier, ahead of the hairline tier; `small_solids_satin` keeps the
shapes it would take; no satin out of it falls back to the ring exactly.
Measured over 16 paired jobs: 37 of the 38 target regions cure (To a T
x4 30, Fremont separators 4, drone 2, MFab LC's LLC hairline; MFab hat's
photo-class generation keeps its ring on `photo_width_floor`), region
kappa 0.905; tests `tests/test_fine_bars_satin.py`. No width, pull, density or stitch
length moves: whether a 1 mm bar holds on a cap is the sew-out question
`small_solids_satin` already carries (gate 1). Layout (ruling 2026-10-22:
judged in the preview). ON by default since Kent's flip on the wave-3
flip sheet, 2026-10-26: "Fine bars as satin" ("For all art. Short thin
bars ... sew as one satin bar like the pro's instead of a hollow ring").
False is the engine before the flip (`PRE_FLIP`).
```

## `small_dot_rung`

```
A rung for closed parts under the run loop floor (2026-10-14, built
OFF; MASTER_SCOPE "Waiting on Kent" 52 asks "lower the floor or a dot
rung"; this PRICES the rung, Kent decides). `machine.RUN_MIN_LOOP_MM`
(2.2) drops the 80 mm i/j dot (0.446 mm², 0.75 mm across) at stage 3,
whose 2 x max(w, h) perimeter proxy reads 1.5 mm (the real ring is
2.49 mm). ON: stage 3's proxy and stage 4's real-ring test admit a part
down to `machine.DOT_RUNG_MIN_LOOP_MM` (still over `RUN_MIN_AREA_MM2`;
not a part nine tenths ringed by other small regions, which is a small
glyph's counter), and the run tier sews an OUTER ring between that and
RUN_MIN_LOOP_MM as a tack ring (`DOT_RUNG_STITCH_MM`, `DOT_RUNG_PASSES`)
instead of skipping it. A sub-floor HOLE ring is still skipped, on
purpose: Fremont 81 mm Hat's 8 has a 2.05 mm counter ring, and sewing it
shut that counter (glyph legibility 1895 0.551 -> 0.426, the 8's open
counters 1 -> 0). The 8's OTHER counter is shut by the 0.73 mm bean on
its own 2.39 mm ring, not by this floor. Rings at or over 2.2 mm sew
exactly as before. All three numbers are CANDIDATES (ROADMAP gate 1).
Off, byte-identical (md5-pinned in `tests/test_small_dot_rung.py`).
**FLIPPED ON 2026-10-20, Kent's call (via the foreman), WITH its
lettering scope below**: PR #991's renders show the rung alone burying
Fremont 80 mm Hat's Wisconsin star; scoped it is byte-identical to OFF
on Fremont at 50 and 80 mm, the tagline cells and Becker, and keeps the
synthetic i/j dots. `RUN_MIN_LOOP_MM` 2.2 stays (gate 1). False is the
pre-flip engine (`PRE_FLIP`).
```

## `small_dot_rung_lettering`

```
The dot rung scoped to lettering (2026-10-15, built OFF; read only when
`small_dot_rung` is ON). PR #939's catch: stage 3 cannot tell an i dot
from a photo speck, so the rung ON admits specks (photo_sunset_backlit
+78 shapes / +23 trims, photo_dof_meadow +20). No tagger exists at
stage 3, so the scope is geometric: the rung admits a part only when a
region of the SAME colour stands below it as a stem -- its top within
1.5 dot heights under the dot, at least three dot heights tall, its top
three dot heights under the dot, no wider than 2 dots, a stroke of
steady width (rows under 1.5 dots, solid) (`stage3_segment._STEM_*`).
Same colour is the
layers' own CIELAB (`layer_lab`) or the raster's mean (`lab_img`, which
the photo lane hands over only when this is on), within
`cfg.merge_delta_e`; with neither, nothing is admitted. The three ratios
are classification candidates, not physical constants; the rung's own
numbers and `RUN_MIN_LOOP_MM` are untouched (ROADMAP gate 1). Off (or
with the rung off), byte-identical (md5-pinned in
`tests/test_dot_rung_lettering.py`); `tools/small_dot_rung.py` measures.
**FLIPPED ON 2026-10-20 with `small_dot_rung`** (Kent's call; the
unscoped rung costs Fremont's star, PR #991). False is the unscoped
rung; the pre-flip engine pins both False (`PRE_FLIP`).
```

## `small_shape_rescue`

```
The run-tier rescue (stages 3, 4 and 7 together). A shape below the
sewable floor that would otherwise be dropped is kept and sewn as a
light bean run on its outline: on the benchmark logo at 90 mm the whole
"ENTERPRISES INC." subline sits under the floor, and dropping it means
a line of the customer's text silently vanishing. Shapes below the
thread's own visual weight (machine.RUN_MIN_LOOP_MM / RUN_MIN_AREA_MM2)
still drop. False restores the old drop-everything behaviour.
```
