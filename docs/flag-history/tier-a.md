# Tier A: flags folded into the code by flag consolidation

Kent, 2026-11-19 ("Let's do the flag sprawl", `docs/flag-audit-2026-11-19.md`, tier A). Each of these 9
was ON by default and had been ON for weeks. The switch is gone: the ON behaviour is the only behaviour,
and the field names are in `digitizer_core.config.RETIRED_FIELDS` (a request or snapshot that still names
one is ignored, never an error). The fold is byte-identical: `python -m tools.fold_check` over the 44
`flag_sweep` jobs matches the merge base on every one. Below is what each one was and why it went on,
moved verbatim from its config comment, PR pointers kept. The research docs it cites still stand.

Function-level keyword parameters that the pipeline used to fill from these fields (`under_cover`,
`fourfold`, `join_square`, and so on) stay in their signatures with their old defaults, because unit
tests call those emitters directly; the pipeline now passes `True`.

**Eleven more tier-A flags were NOT folded here** (`enforce_color_cap`, `revalidate_small_shapes`,
`resnap_mask_matches_grader`, `text_cluster_rescued_ink_link`, `text_cluster_counters_as_drawn`,
`lettering_columns_rail_axis`, `lettering_columns_inside_stagger`, `text_cluster_wide_letters`,
`border_from_outline_line_art_guard`, `small_text_cap_reach_edges`, `outline_loop_mitre`): `tests/conftest.py`
`PRE_FLIP` / `COLOUR_BUNDLE` / `WAVE3_2026_10_26_OFF` / `LETTERING_2026_10_24_OFF` set them False under ~90
test files, so the audit's premise ("no test sets them False") does not hold for them. Folding them is
byte-identical on the engine (44 of 44 jobs, branch `claude/fold-tier-a-all20-wip`) but moves 20 pinned
tests that need a judged re-pin or deletion, not a mechanical one.

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
