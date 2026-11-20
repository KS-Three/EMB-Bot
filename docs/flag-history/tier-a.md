# Tier A: flags folded into the code by flag consolidation

Kent, 2026-11-19 ("Let's do the flag sprawl", `docs/flag-audit-2026-11-19.md`, tier A). Each of these 20
was ON by default and had been ON for weeks. The switch is gone: the ON behaviour is the only behaviour,
and the field names are in `digitizer_core.config.RETIRED_FIELDS` (a request or snapshot that still names
one is ignored, never an error). The fold is byte-identical: `python -m tools.fold_check` over the 44
`flag_sweep` jobs matches the merge base on every one. Below is what each one was and why it went on,
moved verbatim from its config comment, PR pointers kept. The research docs it cites still stand.

Function-level keyword parameters that the pipeline used to fill from these fields (`under_cover`,
`fourfold`, `rescued_ink_link`, `join_square`, and so on) stay in their signatures with their old
defaults, because unit tests call those emitters directly; the pipeline now passes `True`.

## `split_satin` (field)

Last default: ON. Folded 2026-11-19 (`split_satin: bool = True`).

```text
Split satin. A satin cross longer than the threshold carries
intermediate penetrations, staggered station to station so the holes
never line up (machine.SPLIT_* carry the corpus measurements: the
majority of professional crosses split from ~5 mm, ~100% by 7.5).
True is the corpus-majority default; False sews raw crosses however
long — a real house style (jolly-af and sweet-heart ship 6.5-7 mm raw
crosses), not a safety toggle. None = machine.SPLIT_SATIN_ABOVE_MM.
Wiring: stage 7's satin_shape call maps these to its `split_above_mm`
kwarg (False -> math.inf). Until that one-line wiring lands, the
machine default applies — identical behaviour for this default config.
```

## `satin_house_fourfold` (field)

Last default: ON. Folded 2026-11-19 (`satin_house_fourfold: bool = True`).

```text
The house angle's SECOND reading: when a line of lettering has no single
dominant direction in doubled-angle space -- slab-serif and block faces
whose horizontals balance their stems cancel there (Hotel Fremont:
nR^2 4.7 against the 6.9 bar, so nothing fired) -- look for TWO
orthogonal families in four-fold space and set the cross perpendicular
to the STEMS -- the family square to the line of text (the stitch-angle
rule, 2026-09-03; the 45 deg bisector it first shipped with is
retired). See `textcluster._house_along_line_deg`.

Built OFF (2026-09-02: at the 45 deg bisector it piled the ENTHUSIAST
N at 1.41x density and redded the chaining benchmark 2.43 -> 4.62/1k),
DEFAULT ON by Kent's flip (2026-09-03) once the stitch-angle rule's
pass 1 landed: the N leans 25 deg at the compensated 0.200 mm thread
pitch and the benchmark reads 4.09/1k under its 4.1 ceiling (off: 2.43,
unchanged). ON, Hotel Fremont and drone_render's THERMAL sew at the
stems' perpendicular; every other committed fixture is byte-identical
(13 measured, `tools/satin_lean.py` + an md5 sweep, 2026-09-03), and
digitize time does not move. The 4.1 margin is 0.01 -- a thin one, and
the benchmark test is the tripwire that says so if the pipeline drifts.
```

## `fill_travel_under_cover` (field)

Last default: ON. Folded 2026-11-19 (`fill_travel_under_cover: bool = True`).

```text
Fill-phase travel prefers routes over ground not yet sewn: straight only
when straight crosses unsewn ground, else the inset ring whichever way
round stays clear, else the exposed route it always took. Kent's
2026-09-02 note on the Hotel Fremont field ("the in-fill stitching
doesn't look clean") is 22 of 27 fill-phase travel runs — 286 of 450 mm
— laid on top of columns already sewn; the professional file's tatami
is smooth through the same renderer because a pro hides travel under
fill still to come. False is byte-identical to before the flag existed.
Sequencing, no fabric constant — ROADMAP gate 1 does not reach it.

Default ON -- Kent's flip, 2026-09-03, with the 2:25 exposed-vs-cut
weight ratified the same day. Measured ON: Hotel Fremont's fill-phase
exposed travel 286 -> 90 mm at 5 more trims, gaulke_roofing 204 -> 8,
photo_sunset_backlit trims 53 -> 42; cost +7-11% digitize time on
logos, +49-67% on sunset's 263-run fill. The `logo_whitebg` goldens
moved by their travel (2166 -> 2162 penetrations) and were re-pinned
per the recapture doctrine.

**THE "+7-11% ON LOGOS" HALF IS TOO LOW, re-measured 2026-09-12**
(`tools/pro_parity/flagcost.py`, warm-up discarded and a noise floor
from a repeated baseline — and with the parity config's
`fill_density_boost` ON, which adds a second fill pass customers do not
get, so the percentages below are not verified for customer defaults
until re-measured there). `precision_drone` — a logo — reads
**+26.0%**, and `machine_hat` — also a logo, and the corpus's largest
fill at 33,898 stitches — reads **+59.8%** (54.6 s of 92.2 s), which is
inside the band this comment reserved for a photo. The split is not
logo-versus-photo, it is FEW-RUN versus MANY-RUN, and a logo sits in
either: `gaulke_roofing_lc` really is +7.3%. This is the largest single
runtime bill of any flag on this list and it is worth what it buys;
budget it by the fill's run count, not by the artwork's kind.
*(docs/flag-runtime-bills-2026-09-12.md)*
```

## `enforce_color_cap` (field)

Last default: ON. Folded 2026-11-19 (`enforce_color_cap: bool = True`).

```text
Make `max_colors` true on EVERY lane, not just the flat one. Default
OFF and byte-identical off — it only ever runs when a design already
exceeds the cap, which no flat-lane fixture does.

`stage2_quantize` caps hard (largest populations kept, the rest merged
into their closest match, COLOR_CAP_APPLIED emitted). The SLIC+RAG lane
passes `max_k=max_colors` into k-medoids, which is a clustering
parameter and not a cap, and the re-snap can pull further spools in on
top. Since stage 0 routes SIX OF SEVEN real customer logos to gradient,
the one control a customer has over thread count is enforced on the
artwork type they do not have.

Measured at the Studio's shipped default of 6 (`tools/color_cap.py`,
2026-09-07): 6 of 26 designs sew more cones than the slider promises and
all six are gradient — flat 0/6, photo_scene 0/7, photo_subject 0/2 —
worst `drone_render` at 22 cones and 21 colour stops against a promised
6. Every cone is a spool to buy and a manual re-thread on a
single-needle machine, so this is a pricing promise, not a preference.

DEFAULT ON since 2026-09-10 (Kent's ruling on the colour bundle,
`docs/colour-bundle-decision-2026-09-10.md`): at the Studio's 6 it takes
45 cones off five corpus designs and lands every real logo on exactly
the promised number; the merges are visible (Golden Tee's GT letters
lose their maroon edge at 6) and `COLOR_CAP_APPLIED` names them. False
is the pre-flip engine byte for byte.
```

## `revalidate_small_shapes` (field)

Last default: ON. Folded 2026-11-19 (`revalidate_small_shapes: bool = True`).

```text
Let stage 4's thread re-validation reach the shapes preflight condemns.
`stage4_vectorize.revalidate_threads` re-snaps a thread that drifted off
its colour during outline simplification, gated on
`THREAD_REVALIDATE_MIN_PX = 200`. `preflight._MIN_COLOR_PIXELS` is 50 —
so a shape of 50-199 px is scored and BLOCKED by preflight and can never
be corrected by stage 4. ON, the re-ask uses preflight's floor instead,
so the two agree on what is measurable.

Measured 2026-09-06 (`tools/revalidate_floor.py`, MASTER_SCOPE 28): on
`screenshot_phone_ui_golke` the pass refuses 12 shapes, all 12 in that
band, 7 of which would change answer under the function's own estimator
and its own 3.0 dE improvement gate — worst 177 px, `0111 Whale` at
32.7 dE00 where `0015 White` scores 1.4. Across the seven fixtures
THREAD_MATCH_POOR grades F, refusals are 0/0/0/4/7 against
`logo_bridge_bar` 63 and `screenshot_phone_ui` 12.

DEFAULT ON since 2026-09-10 (Kent's ruling on the colour bundle), as
one half of a pair with `resnap_mask_matches_grader`: the mask shrinks a
footprint below the 200 px floor, so alone it declines the shape; the
lowered floor lets it act, and together they move chrome and meadow
D -> C where neither does alone. The estimator does not need the extra
pixels (a median over 50 per-pixel dE00 is sound, and
THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 is the real churn guard). False
is the pre-flip engine byte for byte.
```

## `resnap_mask_matches_grader` (field)

Last default: ON. Folded 2026-11-19 (`resnap_mask_matches_grader: bool = True`).

```text
Score the thread re-validation on the SAME pixels the grader uses.
`stage4_vectorize.revalidate_threads` and
`preflight._region_color_errors` claim the same estimator and have it —
both take the median of the per-pixel CIEDE2000 — but they do not share
a MASK. Preflight erodes the polygon raster one pixel and drops
`p.bg_mask` ("to keep anti-alias halo pixels from dragging a flat color
toward the background"); `_region_footprint` is a bare `cv2.fillPoly`
and does neither. ON, the re-snap applies preflight's two operations,
hairline fallback included, and the pixel floor counts the MASKED set —
a floor that admits a shape on halo pixels and then scores it on three
real ones is not measuring what it thinks.

Measured 2026-09-07 (`tools/spool_remedy.py --masks`, MASTER_SCOPE 28):
on `logo_gaulke_roofing`'s `Se6eddd27` (0.58 mm2 at 16.1 px/mm) the two
masks are 247 px against 54 and disagree by **52.2 dE00 on one
polygon**. Stage 4's set is BIMODAL — 103 near-black + 65 near-white —
so its median makes `3971 Silver` the chart-wide argmin at 11.4 while
the region's own core is near-black and scores that same Silver 63.6.
The re-snap picks a thread on pixels the grader refuses, and the grader
then condemns the thread the re-snap picked. It is the same failure
`_region_color_errors`' docstring calls this instrument's original sin
("the per-channel median of a bimodal pool is a colour almost no pixel
carries"), fixed on preflight's side 2026-08-11 and never inherited
here.

It accounts for TWO of the three F-wall blocks that survive excess
scoring — `gaulke` and `bridge_bar`; `screenshot` is the floor above
(both footprints pick `0015` either way). **And it needs that floor
flag to finish either one.** Masking out the halo SHRINKS the footprint,
so a shape the raw raster floated over `THREAD_REVALIDATE_MIN_PX = 200`
drops under it — gaulke 247 -> 54 px, bridge_bar 240 -> 156 — and this
flag alone therefore declines both re-snaps rather than improving them.
Gaulke's F 4 -> D 46 is the value of DECLINING a wrong re-snap, not of
making a better one. Measured: bridge_bar moves only under
mask + `revalidate_small_shapes` (`6156` -> `5866`, 21.3 -> 16.2, one
more block on that fixture); on gaulke that pair is byte-identical to
this flag alone, because the palette has collapsed and `1375` is no
longer loaded for the small-shape rule to offer.

"MATCHES" is a claim, so it carries its residual — and as of 2026-09-12
the residual is ZERO on the fixture it was named for. The gap used to be
real: `_region_footprint` rounds mm->px and `_region_color_errors`
TRUNCATED, so the two rasters differed by up to a pixel at a vertex
before either mask was applied (measured 2026-09-07: 80 px out of
557,046 on gaulke, 99.99% IoU; zero on `logo_alpha`, where every vertex
happened to sit on a pixel centre). `subpixel_edges` made the vertices
fractional and blew that up to 98.8% / 97.5%, so preflight was changed
to ROUND the same way on 2026-09-09 — see `_region_color_errors`' own
`to_px`. Re-measured 2026-09-12 over every non-enclosed region on
gaulke: **553,014 / 553,014 px, exactly 100% IoU, 0 px disagreeing.**

Two corrections to what this comment used to say, both worth keeping so
nobody re-derives them: the alignment did NOT have to touch
`tag_enclosed_background` (that pass does not share `_region_footprint`
— it carries its own inline `_mm_ring_to_px`, which already rounded), and
it was done on preflight's side, not stage 4's, so `_region_footprint`
is untouched. `tests/test_resnap_mask_matches_grader.py::
test_the_flagged_mask_really_matches_the_graders` still asserts only
`> 0.999` rather than equality: 100% is measured on gaulke, not proved
for every fixture, and a rasteriser tie-break is not worth a brittle pin.

DEFAULT ON since 2026-09-10 (Kent's ruling on the colour bundle), the
other half of the pair with `revalidate_small_shapes` above. False is
the pre-flip engine byte for byte.
```

## `layer_palette_from_regions` (field)

Last default: ON. Folded 2026-11-19 (`layer_palette_from_regions: bool = True`).

```text
The review screen's per-layer cone list, derived from the regions
instead of from stage 2's memory (defect 30 — the third layer-repair
flag, beside `rehome_resnapped` and `merge_duplicate_cones` above).
`PipelineResult.palette[i]` is `thread_indices[i]`, i.e. what stage 2
CALLED layer i; three passes move a region's thread without moving the
region and the rehome repairs only one of them, so the list can name a
cone its layer does not sew. ON elects each layer's cone from its own
regions (`stage3_segment.layer_palette_threads`), which pins
`palette[i]["number"] in {r.thread_number for r in layer i}`.

REVIEW-ONLY, and that is checked rather than asserted: `result.palette`
feeds exactly one consumer, `_review_payload["palette"]`
(`digitizer_service/app.py:587`). `plan.palette`, `design.colors`,
`thread_m_by_color`, every export and every preflight number are built
from `plan.blocks` and cannot move; `reviewFromJob` keeps only
`brandId` and per-shape fields, so no `.embproj` migration.

DEFAULT ON since 2026-09-12 — Kent's ruling, taken with the corpus pass
in hand exactly as he asked for it ("corpus pass first, then flip", the
same posture as the colour bundle). False is the pre-flip engine byte
for byte, proved by execution rather than by output comparison
(`tests/test_layer_palette.py::test_off_the_election_never_runs`), and
is kept reachable and tested rather than dead-by-default.

What the pass measured, four full-corpus arms at BOTH `max_colors=12`
and the Studio's shipped 6 (`docs/palette-flip-corpus-2026-09-12.md`):
the invariant holds 0-violations on 26/26 at both settings (OFF it is
violated on 7 layers at 12 and 13 at 6); mislabelled layers 7 -> 0 and
13 -> 0; rows 132 -> 132 and 109 -> 109 with zero cones dropped that
any block sews; and the plan digest, every stitch coordinate,
`design.colors`, `thread_mm_by_color` and every stitch/trim/stop count
IDENTICAL off vs on across all 26 at both settings. "Review-only" was
an argument from the call graph and is now a corpus measurement.

THE PRICE KENT ACCEPTED, so nobody re-opens it as a bug: duplicate
review ROWS, 0 -> 7 at 12 and 0 -> 13 at 6, worst `drone_render` at 6
with 15 rows naming 6 distinct cones. `merge_duplicate_cone_layers`
folds on the DECLARED cone, upstream of this election, so two layers
can now carry the same DERIVED cone and not fold. The rows are honest —
each layer really does carry the cone it names — and there is no
half-flip, because the duplicates ARE the truth the colour cap
produced. Folding them means folding on the derived cone, which moves
sew order and goldens: a separate decision, to be measured, not slipped
in here.

ON, `PALETTE_THREAD_MISMATCH` is not structurally dead — it becomes the
detector for a layer holding TWO cones, a population that is 0 today.

No ROADMAP gate applies — gate 1 is physical constants (nothing here
touches cloth) and gate 3 is default-OFF tiers; this is a label list.
Measured population and the whole consumer inventory:
`docs/palette-mismatch-2026-09-12.md`.
```

## `satin_cap_recentre` (field)

Last default: ON. Folded 2026-11-19 (`satin_cap_recentre: bool = True`).

```text
`satin_cap_recentre` (built 2026-09-19 for Kent's flip): a free end
whose spine tail is a surviving CAP FORK is cut at the kink and rebuilt
square. A flat cap's medial axis forks toward both corners; on a plain
bar the forks are twins and the pruner drops both, but on a stem whose
one edge leans three degrees one fork survives as the tail,
`_retract_cap_corner` stops at 0.8 of the half-width -- which a fork's
first millimetre still reads -- and `_extend_to_cap` extends the
diagonal onto the corner: the column tapers to a point there and the
other corner sews 1.11 mm bare. Found from the OUTLINE side
(`tools/edge_wobble.py`'s `unsewn`: Becker 32.6 mm of outline with no
thread within 0.5 mm). The cause-side twin of
`satin_rails_follow_edge`, which reaches the same corners by letting
each rail chase its edge and roughens the rails to do it. Numbers:
DOCTRINE 2026-09-19.

FLIPPED ON 2026-10-03 (Kent's ruling, on his labelled sitting of that
day, `docs/eye-pairs-2026-10-03/`): after on becker and tires -- the two
logos where the change locator found it -- no difference on four, both
bad on two, before on none; eight logos 84,475 -> 84,460 stitches and
455 -> 454 trims. Small by its own record: of Becker's 44 free ends 7
carry a fork and 3 pass the guards. False is the pre-flip engine, byte
for byte.

What it does to the fidelity headline is NOT what the headline says.
On enthusiast at 80 mm `lost_frac` reads 0.2573 -> 0.2819, and that is
the instrument: the flag shortens the design 0.2 mm at its right edge
and the 0.4 mm alignment grid snaps a step. At one physical alignment
it reads lower (0.2573 -> 0.2481; 0.1636 -> 0.1555 at one pixel). Kent
re-pinned that bar, attributed, the same day
(`tests/test_lettering_coverage_regression.py`).
```

## `satin_outer_rail_pitch` (field)

Last default: ON. Folded 2026-11-19 (`satin_outer_rail_pitch: bool = True`).

```text
Station a satin column's BODY along its OUTER rail (2026-10-06, Kent's
pick after the Hotel Fremont deep dive; `.claude/memory/
lettering-thickness-fremont-2026-10-06.md`). Stations are spaced along
the spine, so on a bend the outer rail opens to 1.3x the pitch before
`_rail_points`' refinement fires, and its inner-rail crowding clamp then
refuses the insertion: Fremont's O sewed its outer rail at 0.53 mm
against the pro's 0.33, and that gap is where the ragged edge Kent
called "wobbly" concentrates (silhouette hair 1.62 vs the pro's 1.33).
ON, a body whose outer-rail advances average over the pitch is
re-stationed evenly along the outer rail by the refinement's own
interpolation; the inner rail then crowds on a tight bend and
`_short_stitch_guard` retracts every other inner penetration -- the
professional construction (the pro's O: 22% short crosses). A straight
bar is byte-identical either way (its outer rail is its spine). Built
OFF on 2026-10-06 because it moves stitches on every curved satin
shape, so the goldens re-capture on the flip, and the price was Kent's
to see on a render first -- the Fremont O's 43 crosses become 54 (`satin_shape` direct,
rail comp 0.3: outer pitch 0.50 -> 0.39), the 2.5 mm test ring 138 ->
168 stations. Tests: `tests/test_outer_rail_pitch.py`.
**FLIPPED ON 2026-10-06, Kent's call, on the render and the price:**
Fremont at 80 mm +1.0% stitches, trims unchanged, per-letter silhouette
hair 1.49 -> 1.39 (the pro 1.21). The flip moved 19 tests, every one
read and re-pinned in that PR: 12 goldens (the flat lane, stage 2 and
push-comp byte-identity keys, re-captured on Linux), the lettering
coverage pins (`lost_frac` / `overshoot_frac` read every short stitch's
retracted end as thread inside the artwork), the MARINE junction-stack
and rail-comp trims ceilings, the tip-caps end-coverage read and the
shape-overrides byte-identity key. False is the pre-flip emitter,
byte for byte.
```

## `satin_join_square` (field)

Last default: ON. Folded 2026-11-19 (`satin_join_square: bool = True`).

```text
A join corner's members sew SQUARE to it (2026-10-06, the serif and
junction fans; Kent's "start on" after the Hotel Fremont deep dive).
`_split_sharp_corners` already cuts an E's arm from its hanging slab
serif and the arm owns the corner, but the member's spine kept the
medial axis's own bend -- an L's skeleton turns over about one
half-width each side of the apex -- so the owner's last four or five
crosses leaned up to 45 deg into the slab and the slab's first crosses
leaned back (Fremont's E arms, the T's bar ends, the L's foot). ON,
`_satin_joined` lays each member's corner end on the member's own
straight line (`_straighten_member_end`: direction read over the
stretch 1.5-4 half-widths from the corner, the bent samples replaced,
the apex projected onto the line), so the owner's column runs square
through the butting member's width to the cap and the butting member
starts square under it -- the pro's construction. Built OFF the same
day because the join members move on every letter with a slab or an L,
so the goldens re-capture on the flip, and the render was Kent's to
judge first. **FLIPPED ON 2026-10-06, Kent's call, on the renders**
(`docs/renders/join-square-2026-10-06/`): Fremont at 80 mm re-planned
from the same stages, stitches and trims identical (13,742 / 34), fan
ends 7 -> 5 over 36 columns, the E 2 -> 0, the T's bar square across
both hanging ends. False is the pre-flip joiner, byte for byte.
Tests: `tests/test_join_corner_straight.py` (the behaviour tests pass
the flag explicitly, so they read the same whatever this default is).
**HELD OFF 2026-10-07, Kent's ruling, by its own guards:** merged with
current main and run on the lettering set, ON lost one artwork
element of at least 1 mm2 of the ENTHUSIAST wordmark (`tests/test_
lettering_coverage_regression.py::test_no_element_of_the_wordmark_goes_
unsewn`, a fixture that had never lost one) and tipped three sibling
bars (that fixture's fine `lost_frac` 0.1702 / 0.17, the tip-caps end
bare 10.53 / 9.5 mm2, a rail-comp mid-rail hole 1.24 / 0.55 mm2), all
four green OFF on the same tree. **ON AGAIN 2026-10-07 with the apex
cap, the element named (defect 60):** the S's bowl. At 80 mm
(half-width 0.87 mm) a pull-comped inner bowl is a sharp reflex
vertex, so the join-corner cut took each S at both bowls in BOTH
arms; OFF the members' bent ends still met, ON
`_straighten_member_end` projected each apex 0.80 / 0.82 mm (0.92
half-widths) onto its fitted line, the ends parted and the bowl's
wedge sewed bare -- one mechanism behind the element and all three
bars. `_STRAIGHT_MAX_MOVE_HALVES` (0.6) keeps a member whose apex sits
further off its own line than that on its pre-flip spine: a bend is
not a corner. Set on the census of apex moves under the flag (p50
enthusiast 0.92, Fremont 0.22, Becker 0.12 half-widths; the vertex
angle was tried first and would refuse Becker's and drone's real
corners too). With the cap, the seven-logo set: enthusiast is within
two stitches of OFF and its four guards green; Fremont's E arms and
T bar stay square (fan ends 18 -> 16 over 33 text columns either
way, 10 of its 16 straightenings kept); satin bare falls on five of
the six text logos against the uncapped flip (Becker 4.37 -> 2.94%,
drone 3.91 -> 2.47%; Fremont +0.04 points) and trims never rise;
corpus-wide the cap refuses about half the straightenings
(bridge 32 of 60, gaulke 9 of 14), every one with its apex over 0.6
half-widths off the line. Tests: `tests/test_join_corner_bend_cap.py`;
the trail is `docs/join-square-enthusiast-2026-10-07.md`.
```

## `satin_slab_serifs` (field)

Last default: ON. Folded 2026-11-19 (`satin_slab_serifs: bool = True`).

```text
A slab serif's axis is its own column, not a cap (2026-10-07, Kent's
pick after the join-square flip: "T-shaped slabs: own column, not a
cap"). A slab across a stem's end (a foot, a T-shaped terminal) puts
its medial axis through the stem's node in BOTH directions, as two
short free arms -- the same silhouette as a square cap's I-beam, which
the 2026-09-19 twig rule erases. Two ways that lost the slab on Hotel
Fremont at 80 mm: the T's foot halves run into the foot's corners, so
the twig rule took them for an I-beam and the foot sewed as the stem's
terminal fan (0.48 mm2 of its bottom millimetre bare); the N's survived
the rule but meet at 144 deg, which `satin_junction_stack`'s 30 deg weld
refuses, so one half fell to the stub filter and the foot sewed as a
half column. ON, a pair that is square to the stem and leaves the node
in opposite directions (`_slab_pair`: within 35 deg of square, at
least 120 apart) is kept by `_prune_spurs` and welded by
`_merge_through_junctions` whatever its turn, into the slab's own
free-ended stroke; the stem stays a T's stem under it. A cap's forks
(45 deg off the axis) and a corner twig beside a hanging slab (40 off
square) are not pairs, so the join-square fold at the E's and T's
L-corners is untouched. Fremont ON: three letters move (T, N, R), the
design +34 stitches. Built OFF; the render is Kent's to judge.
Tests: `tests/test_slab_serifs.py`. **FLIPPED ON 2026-10-08, Kent's
call, TOGETHER with `satin_free_end_square` below** on the four-arm
render (`tools/join_square_census.py fremont --width 80 --garment
left_chest`): both ON, Fremont at 80 mm bare letter artwork 3.20 ->
0.84 mm2, fan ends 16 -> 9, +137 stitches, trims 38 -> 39.
```

## `satin_free_end_square` (field)

Last default: ON. Folded 2026-11-19 (`satin_free_end_square: bool = True`).

```text
A plain FREE END lands square too (2026-10-08, built OFF). The corner
join above straightens only `Stroke.corners` members; an arm's free end
whose spine hooks into a corner of its square cap (Fremont's E middle
arm at 80 mm: square legs 90 -> 57 deg over its last 0.5 mm) still
fans, and a slab hanging off a free end whose wings `_prune_spurs`
drops as a cap I-beam (the H's, M's, N's and T's feet at 80 mm) was
sewn only by that fan. ON, `_free_end_reading` reads the artwork across
the arm's line at its cap face: a hooked square cap is laid on the
line, and a slab is sewn as its own short column joined to the arm
(`_slab_spine`, `_attach_slabs`, cut against strokes that already own
it -- so a slab `satin_slab_serifs` has made a stroke is left to it).
Gated to arms (6 half-widths), tight lines and square cap faces, each
gate found by a corpus render (Becker's N, the U's, Enthusiast's S).
Measured: `tools/join_square_census.py`; tests
`tests/test_join_slab_square.py`. **FLIPPED ON 2026-10-08, Kent's call,
together with `satin_slab_serifs`** (see there); False is the 10-07
free end, byte for byte.
```

## `text_cluster_rescued_ink_link` (field)

Last default: ON. Folded 2026-11-19 (`text_cluster_rescued_ink_link: bool = True`).

```text
The one-ink link (`textcluster._same_ink`, CIEDE2000 20 on the job's
chart) in the text tagger's FIRST round too, the rescued door
(`textcluster.detect_text_clusters`, 2026-10-15). That round linked on
size alone (`SIMILARITY_RATIO` 0.5), so one rescued letter of a word
could join another word in another ink. Fremont at 80 mm, Kent's Hat
job: THE's black E traces at 2.19 mm2, under the 2.25 mm2 small-shape
floor, and is the word's one rescued letter. It joined the tan 1895
(heights 2.62 / 1.66, strokes 0.39 / 0.21, 5.7 mm apart: every term
within 0.5), the restore step stripped it as a stray, and T and H
alone could not make a three-member cluster: T and H went to the
Column lane as crossing satin and the E to the run rescue, a garbled
THE one millimetre under the clean one at 81 mm (where the E is
2.25 mm2, not rescued, and enters by the letter door with its word).
True: round 1 refuses a link across inks, as round 2 always has; THE
forms its own cluster and sews as bean letters, 14,897 / 46 ->
14,812 / 43, EST, 1895 and the tagline unchanged shape for shape
(`tools/fremont_triage.run_arm` at 80 mm). A link can only be refused
in that round, never added, so a rescued cluster in one ink is
unchanged; a letter freed from a mixed cluster goes to the second
round and may rejoin its line (the 3 mm tagline crop: EAT STAY PLAY
read as one line of 11 instead of 6 + 3 with two letters held by the
separator bars). Geometry, not fabric: no sew-out settles which shapes
are a line. False: the pre-flip engine, byte for byte. Tests:
`tests/test_textcluster.py`.
```

## `lettering_columns_rail_axis` (field)

Last default: ON. Folded 2026-11-19 (`lettering_columns_rail_axis: bool = True`).

```text
Under `lettering_columns`, a short straight bar takes its RAILS'
direction (2026-10-20, `outline_cut.straight_axis` / `_rail_pair_axis`).
Proseal at the pro's 85.9 mm hat width: the E's middle arm (4.5 x 2.2
mm, ends leaning with the italic) read 0.44 outline coherence against
the 0.55 bar, fell back to the spine's chord -- which runs acute corner
to acute corner -- and sewed its crosses at 77.6 deg beside the top
and bottom arms' 90.0: an angle change inside one letter. Synthetic
3.5-4.5 mm bars leaning 8-20 deg read 10-22 deg off. ON, a piece that
took the chord fallback (whose straightness gate is unchanged) runs
along its two longest own sides when they are parallel within the
upright snap's 7 deg and on opposite sides of the stroke -- and only
where the chord is more than those 7 deg off them (Proseal's L stem,
5.1 off, keeps its chord; only the E arm moves there). No sewn
constant: a direction, not a width or a pitch. False is the pre-flip
lane, byte for byte. Tests: `tests/test_column_rail_axis.py`.
```

## `text_cluster_counters_as_drawn` (field)

Last default: ON. Folded 2026-11-19 (`text_cluster_counters_as_drawn: bool = True`).

```text
The text tagger's LETTER door measures a glyph's stroke on the glyph
as drawn: the traced polygon with every enclosed rescued speck of
another ink punched back in as a hole (`textcluster._as_drawn`). Stage
4 fills a counter under its hole floor (`min_detail_mm`^2 / 4, 0.56
mm2) into the letter and the counter survives only as a rescued speck
of the ground's ink, so a small sans A traces as a near-solid triangle
whose stroke CV (0.556 / 0.596 on Proseal's tagline at 85.9 mm, Kent
2026-10-20) fails `LETTER_STROKE_CV_MAX` 0.55 and the A sews as a satin
blob beside its bean line-mates. Read as drawn the same A's are 0.29 /
0.32. Only the measurement moves; no bound changes. False: the door as
it was, byte for byte (`PRE_FLIP`). Tests: `tests/test_textcluster.py`.
```

## `lettering_columns_inside_stagger` (field)

Last default: ON. Folded 2026-11-19 (`lettering_columns_inside_stagger: bool = True`).

```text
Under `lettering_columns`, the INSIDE of every pivot -- an L fold's
corner (`lettering_columns_corner_fold`), an S's curl, a bowl -- is
sewn the way the professional's files sew it (2026-10-23, built OFF;
`columns._inside_stagger`, in place of `_short_stitch_guard`). Read
with one rule on his hat DSTs and ours (Fremont, Drone, MFab, Proseal,
Becker; `tools/inside_stagger.py`): his full-length inner ends walk
~0.3 mm per pair along the inner edge and almost never share a hole
(2-5 re-entries per band), and about one cross in three is shortened
by ~20% of its length. The guard shortens every other crowded cross
by 35% (capped 0.6 mm) and leaves the full ones in one hole (16-79
re-entries per band, 28-56% of the long steps under 0.1 mm). ON: a
crowded penetration (under `SATIN_SHORT_STITCH_AT_MM` from the one
before it on its rail) is pulled `columns.STAGGER_SHORT_FRAC` (20%) of
its cross, never two in a row (two in five); where a rail's ends pile
into one hole the full-length ones are spaced along the rail's course
round the pile, `STAGGER_WALK_MM` apart where the corner has room
(`columns._inside_stagger`). Layout, judged
in the preview (Kent, 2026-10-22). ON by default since 2026-10-24
(Kent, the flip sheet; same-hole re-entries per zone Becker 1.14 ->
0.60, Fremont 0.37 -> 0.34, MFab 0.29 -> 0.17, the pro 0.11 / 0.16 /
0.22). False is the guard, byte for byte.
Tests: `tests/test_column_inside_stagger.py`.
```

## `text_cluster_wide_letters` (field)

Last default: ON. Folded 2026-11-19 (`text_cluster_wide_letters: bool = True`).

```text
A wide letter never reaches the Column lane: the text tagger's letter
door refuses anything wider than `textcluster.ASPECT_RATIO_MAX` 1.4
times its height. MFab's W of WELDING at 104.9 mm hits it twice: its
right vertex touches the E's foot through the keyline, so W and E trace
as ONE region (17.5 x 6.9 mm, aspect 2.55), and the W alone, with its
long lead-in arm, is still 1.58. Under the photo path the A and N of
AND touch the same way, which leaves the D short of a line of three and the
whole word untagged. ON (2026-10-23, built OFF): such a region beside
a line it could join is cut at every neck under a quarter of its own
stroke (`textcluster._neck_split`), the pieces replacing it only when
every one is tagged; and a glyph up to `WIDE_LETTER_ASPECT_MAX` 1.8 is
adopted by a line it links to (`_adopt_wide`), never making one.
Segmentation and tagging, not fabric: layout, judged in the preview.
ON by default since 2026-10-24 (Kent, the flip sheet; MFab moves,
Fremont and Becker byte-identical). False: neither is called, byte
for byte. Tests: `tests/test_wide_letters.py`.
```

## `border_from_outline_line_art_guard` (field)

Last default: ON. Folded 2026-11-19 (`border_from_outline_line_art_guard: bool = True`).

```text
The rule's false positive (2026-10-25, #1078): a hairline DRAWING is
not an outline. Bridge Bar's bowl-and-waves (0.8-1.0 mm black lines round
yellow cells of the disc they sit on) reads as one, and ON sews each
cell a 1.5 mm satin loop -- spikes fanned at the cells' tips -- while the
drawing's own stroke ends, thinner than `machine.MIN_FILL_WIDTH_MM`,
fall to a rest-fill that drops them (garment shows). ON, an outline that
is a hairline AND leaves strokes beyond its loops
(`art_outline.line_art_reading`, thresholds `machine.OUTLINE_LINE_ART_*`)
is not one: the drawing sews as it did before `border_from_outline`
(Bridge hat and LC byte-identical to the flag OFF), and its cells are
free for another holder. A hairline that is a pure ring stays an outline:
To-a-T Machine's 0.8 mm frame, which the pro widens to a 2.0-2.3 mm
border. Census kappa 0.76 -> 0.85 (n 588, the five Bridge false
positives gone, no true one lost); Becker, MFab, Fremont byte-identical.
The pro's Bridge files carry no drawing (his art was redrawn without
it), so this is our construction's limit, not his rule. Acts only with
`border_from_outline`. Layout (ruling 2026-10-22: judged in the preview).
**ON since 2026-10-25, Kent's flip** ("Flip it ON", from #1078's OFF | ON
| ON+guard | pro renders of the bowl: spike rays 22 -> 1, pinholes 3 -> 1
on the hat). False is the engine as it was, byte for byte;
`tests/conftest.py` PRE_FLIP pins it False.
```

## `small_text_cap_reach_edges` (field)

Last default: ON. Folded 2026-11-19 (`small_text_cap_reach_edges: bool = True`).

```text
With `small_text_cap_letter_gap_mm`: the re-set reaches the two kinds
of small line it refused as `no_room` (2026-10-24, L8; census
`tools/small_text_floor_census.py`). Across the paired jobs the pro
sews NO line under ~4 mm as drawn, as a run or not at all: ProSeal's
"SPRAY FOAM + COATINGS" goes 3.0 -> 4.55 mm satin on the 86 mm hat and
2.6 -> 4.0 on the 75 mm beanie, inside the same design height (63.3
against our 63.1 mm). Ours stayed a 3 mm bean line under the re-set,
for reasons this fixes: (1) the design's EDGE is tested against the
letters, not their `CLEAR_MM` halo, and gives way by half the line's
growth -- a line on the bottom edge could never fit, at any growth
(the pro's sews 0.6 mm past it); the halo still clears every shape;
(2) a letter-sized shape standing on the line's band INSIDE its span
joins the line whatever its thread, as `_join_line_ends` already does
past either end -- ProSeal's A of SPRAY traces in a thread of its own
and blocked its own line; (3) clusters of one line whose hulls overlap
are placed as one (the beanie's COATINGS is two interleaved clusters),
and words of one line keep a sewn letter gap apart, not two halos.
Measured: ProSeal hat tagline 3.15 mm bean -> 4.35-4.45 satin (pro
4.55), beanie 2.8 -> 3.65-3.7 (pro 4.0); Fremont and Drone DSTs
byte-identical. Geometry, not fabric: where the letters go. Tests:
`tests/test_small_text_reach_edges.py`. **ON since 2026-10-24, Kent's
flip** from the wave-2 flip sheet; it acts only while the re-set
(`small_text_cap_letter_gap_mm`) is set, so with that None it changes
nothing. False: the re-set as #1029 built it, byte for byte;
`tests/conftest.py` PRE_FLIP pins it False.
```

## `outline_loop_mitre` (field)

Last default: ON. Folded 2026-11-19 (`outline_loop_mitre: bool = True`).

```text
A satin loop round a letter -- `enclosed_white_keyline`'s keyline loops
and `border_from_outline`'s outline loops (`stage6_border.keyline_runs`)
-- keeps its far rail at the satin pitch through the letter's convex
corners, as the professional's keyline and outline satin do
(2026-10-25, built OFF; `stage6_border._pivot_ring`). The loop casts
each cross along a normal smoothed over half its width either side, so
through a corner its far ends spread 1.1 mm apart where the pro's sit
0.4 mm apart: the spikes on MFab's white keyline at every M-FAB corner
(#1059, #1065). The pro's corner is the same round arc, not a mitre
(far ends 1.00 widths from the corner on MFab's keyline, 1.12 on
Becker's outline; a mitre point is 1.43 / 1.55) -- the name is the
brief's. ON: crosses put between any two whose far ends part by more
than `LOOP_PIVOT_GAP` steps on a convex turn, one per step of the far
rail; the near ends' pile short-stitched. Layout, judged in the preview
(Kent, 2026-10-22). ON by default since Kent's flip on the wave-3 flip
sheet, 2026-10-26: "Outline corners pivot" ("For all art. The satin
loop round a letter turns its corners with tightly packed stitches, as
the pro does, instead of fanning into spikes"). False is the loop as it
was, byte for byte (`PRE_FLIP`). Set for a plan by
`stage6_border.loop_mitre_scope`.
Tests: `tests/test_outline_loop_mitre.py`.
```
