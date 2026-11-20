# Flag history: tier B2, lettering lane (folded 2026-11-20)

Fourteen switches, all ON by default, folded into the code (the `cfg.X == True` path kept, the
False branch and the `PipelineConfig` field deleted; `docs/flag-audit-2026-11-19.md`). Each
section below is the field's own comment block as it stood in `config.py`, kept for the
evidence and PR pointers. The names are in `RETIRED_FIELDS`, so an old snapshot or a service
request that still sends one is ignored rather than refused.

## `lettering_columns_corner_fold`

```
Under `lettering_columns`, ONE satin column is folded round an
L-shaped corner -- an E's arm meeting its stem, an L's foot, a T's bar
end into its serif, a 7's elbow -- the way the professional's files
sew every such corner (2026-10-23, built OFF; `outline_cut._fold_corners`).
The cut takes a lone concave corner with a convex apex across it as a
junction and cuts there (a "mitre" to the apex, an "ext" along the
longer edge, an E's "slot" line), so the two strokes sew as two
columns butted at the corner: over the 38 letters of Fremont HOTEL
FREMONT, Drone PRECISION, Proseal PROSEAL and MFab AND WELDING ours
read 156 columns / 242 butts / 75 gaps against the pro's 134 / 195 /
54 (`docs/lettering-5-10mm-2026-10-23.md`). His needle paths (all four
DSTs, 57 corners read 2026-10-23) keep one column through the corner:
the crosses pivot on the inside corner, their outer ends walk the
outline round the apex at the satin pitch, and the next stroke's
crosses carry on -- no cut, no butt, no travel; he cuts only where two
concave corners face each other (a T junction, a slab serif's root).
ON, after the cut: at every lone concave corner of the letter whose
turn is `outline_cut.FOLD_TURN_MIN_DEG`..`FOLD_TURN_MAX_DEG`, that is
not one of a through pair, and where exactly two columns of like
width (within `FOLD_WIDTH_RATIO`) meet, both columns lose the crosses
inside the corner square and are joined by crosses from the inside
corner to the outline round the apex, one per pitch (kind "folded").
The legs' own crosses, and so the sewn width, are untouched; the
engine's short-stitch guard thins the pile on the inside corner as it
does on an S's curl. Layout, judged in the preview (Kent, 2026-10-22),
so ON-eligible from renders. ON since 2026-10-26 (Kent 2026-10-23, #1057). False is the pre-flag cut, byte for byte.
Tests: `tests/test_column_corner_fold.py`.
```

## `lettering_columns_fold_cuts`

```
Under `lettering_columns`, cut a lowercase SHOULDER (2026-10-13,
`outline_cut._fold_refine`). The junction rules leave a lone concave
corner uncut when its far side is smooth ("the stroke is bending
here"), so a u's bowl and its right stem, a b's or g's bowl and its
stem, sew as ONE piece whose crosses fold 45-83 deg through the branch.
Capitals meet at corners and are cut: at 80 and 120 mm a synthetic
word reads 0.0% of capital station crosses past 45 deg off their own
perpendicular against 1.4% lowercase, all of it at shoulders
(`tools/lowercase_angle.py`). ON, a piece with FOLD_MIN interior
crosses past FOLD_DEG takes the second look `_refine` already gives an
over-long one, scored on folded crosses. Built OFF (Kent's call to
flip; renders only, nothing sewn); False is byte-identical.
Tests: `tests/test_lowercase_angle.py`.

**FLIPPED ON 2026-10-20, Kent's ruling** (relayed through the foreman),
on PR #986's close-out of item 50's two open cases: the sewn judge
(`outline_cut.sewn_knots`) and its coverage guard (`COVER_SLACK`). Its
instrument is `tools/lowercase_angle.py` plus `sewn_knots`: on the
synthetic word no glyph sews worse ON than OFF at 50, 80 or 120 mm,
lowercase folds go 5 -> 0 at 80 mm and 13 -> 2 at 120, and capitals sew
as OFF. KNOWN COST: lowercase in the lane digitizes 2-3.4x slower (the
judge sews every candidate cut). KNOWN OPEN, sew-out (ROADMAP gate 1):
every fold_cuts ratio is from one synthetic word, unsewn. False is the
pre-flip construction, byte for byte (`tests/conftest.py`, PRE_FLIP).
```

## `lettering_columns_icon_guard`

```
Under `lettering_columns`, refuse a HOUSE-GROUP-ONLY shape whose medial
axis is a tangle: `columns.is_drawing_fragment`, junctions plus free
ends of the pruned skeleton >= `columns.ICON_GUARD_MIN_NODES` (24).
Census (`tools/column_capture_census.py --signals`, PR body): the phone
screenshot's three 4.5-6 mm captures read 36-45, which neither guard
above reaches (not blobs; the text's own grey); every hand-labelled
letter reads <= 13 and golden_tee's swashes <= 8. Composes with both.
ON by Kent's ruling 2026-10-13 (stitch output moves on the phone
screenshot only: 33 -> 30 lane shapes); False reads nothing.
Tests: `tests/test_column_capture.py`.
```

## `lettering_columns_ink_link`

```
Under `lettering_columns` (old taggers, `lettering_words` off), refuse
a HOUSE-GROUP-ONLY shape whose thread is further than the text
cluster's own ink link (CIEDE2000 20) from every text-cluster letter's
thread, unless it abuts one (within 1.0 mm): `columns.ink_strays`,
written as `meta["lettering_ink_stray"]` after the house angle.
Census (`tools/column_capture_census.py --guard`, PR body): refuses
enthusiast's shield star (34.2) and nothing else on the labelled
fixtures; golden_tee's swashes are kept. It does NOT reach the phone
screenshot's status icons, which are sewn in the text's own grey.
**FLIPPED ON 2026-10-13, Kent's ruling** (relayed through the director;
PR body: per-fixture OFF vs ON table). ON by Kent's ruling 2026-10-13:
enthusiast's star goes back to fill (+159 stitches). The phone
screenshot's status icons are STILL captured (dE 0.0 / 0.0 / 9.1 from
the text ink); the shape guard for them is `lettering_columns_icon_guard`
below (ON since the same ruling). False writes no
key and reads none. Tests: `tests/test_column_capture.py`.
```

## `lettering_columns_inside_connectors`

```
Under `lettering_columns`, a needle-down CONNECTOR between two of a
letter's runs stays inside the letter as far as its own satin reaches
(2026-10-13, `columns.column_runs`, `inside_connectors`). The link rule
tests a hop against the letter grown by 0.1 mm + the pull, and that
buffer closes a narrow notch: on Kent's Fremont 81 mm hat the M's walk
sewed a 2.5 mm connector from its right foot to its vertex, 1.65 mm of
it over the bare notch (his M->O "loop"), and Becker's MARINE N got a
visible one under `lettering_columns_square_ends`. ON, a connector, the
walk-in and the link rule test the letter grown only by the rails' side
reach (`pull - RAIL_REACH_INSET_MM`), a routed path keeps its corners
and walks only graph edges that stay inside; a hop with no such route
is a jump (a trim past `trim_at_mm`). ON by Kent's ruling 2026-10-13;
False is the pre-flip lane. Cost: Becker gains 3 trims (22 -> 25),
three in-letter hops with no on-letter route. Tests:
`tests/test_column_ends.py`.
```

## `lettering_columns_skip_blobs`

```
Under `lettering_columns`, refuse a tagged shape that is a SOLID BLOB
rather than a stroke (`columns.is_solid_blob`: mean stroke width over
the longer bbox side >= 0.40 and solidity >= 0.95), so it takes the
ordinary fill ladder. Census (`tools/column_capture_census.py`, PR body):
the house-angle group, which has no ink link, tags colour patches and
ramp discs as lettering and the lane sews them as 20 mm split satin.
**FLIPPED ON 2026-10-13, Kent's ruling** (relayed through the director;
PR body: per-fixture OFF vs ON table). ON by Kent's ruling 2026-10-13.
False is the pre-flip lane (the colour grid's patches and the fur
ramp's discs sewn as split satin). Tests: `tests/test_column_capture.py`.
```

## `lettering_columns_small_bold`

```
Under `lettering_columns`, a letter under
`machine.SATIN_UNDERLAY_MIN_EXTENT_MM` (5 mm, stage 7's `_small`) sews
like the pro's ~4 mm bold letters (2026-10-21, built OFF). Kent ruled
"match the pro" for Fremont's small words (`small_text_cap_mm` and its
siblings grow them to ~4 mm); the lane then sewed them as blobs. At
92.5 mm Hat, grown to cap 4.0 / width 1.05 / stroke 0.85, the tagline,
EST 1895 and THE measured: median satin stitch 1.23 mm against the
pro's 0.86 (fixed 0.4 mm pull a rail on a 0.8 mm stroke), and 238
crossed zigzag legs (serif blocks fanned from their inner corners).
ON, four changes for those letters only (`columns.lettering_columns_shape`
`small_bold`): the pull is `columns.SMALL_BOLD_PULL_FRAC` (0.15) of the
stroke width when that is less (median 0.85 mm); a piece wholly under
the 0.5 mm cross floor sews AT the floor instead of vanishing
(`columns._floor_crosses`); no column pivots past
`outline_cut.SMALL_BOLD_FAN_DEG` -- a straight piece ends square, never
fanned, and a piece whose rail collapses to a point is stationed along
its own length -- and the cut simplifies at 0.06 mm, not 0.12. A
letter of 5 mm or more is not touched, ON or OFF. Every mm and share
here is a candidate until sewn (gate 1). Kent flips. Tests:
`tests/test_column_small_bold.py`.
ON by default since 2026-10-23: it rode the flip sheet's `small_text_set`
arm (PR #1047) with the four `small_text_cap_*` values below, and Kent
flipped that arm as rendered; False is the off arm.
```

## `lettering_columns_small_stem`

```
Under `lettering_columns`, let a thin STEM under the area floor reach
the Column lane (2026-10-13, `columns.is_thin_stem`). Stage 7's
small-shape rescue sends every auto-tier shape under `min_detail_mm`^2
(2.25 mm^2) to the run tier before the lane is asked, and the floor is
an area: at 80 mm the synthetic word's capital I stem (0.57 x 4.87 mm,
2.771 mm^2) sews satin and its lowercase i stem at the same 0.57 mm
width (x 3.73 mm, 2.124 mm^2) sews a two-line run, though both are
tagged lettering (`tools/stem_trace.py`). ON, a lettering shape under
the floor whose long side is at least `min_detail_mm`, whose short
side is at least `machine.SATIN_MIN_CROSS_MM` and whose long / short
is at least `columns.STEM_MIN_ASPECT` (6) is not rescued to the run
tier; a dot, a blob or a shape narrower than the cross floor still is.
The aspect bar is a CANDIDATE shape ratio set by the corpus (the
phone screenshot's stems under the floor read 3.1-4.1 at 0.63-0.90 mm
across and stay run, the i stem 6.5), and nothing here is sewn
(ROADMAP gate 1). Built OFF; False is byte-identical. Tests:
`tests/test_small_stem.py`. **FLIPPED ON 2026-10-20, Kent's call (via
the foreman)**: PR #991 measured one shape moved (the 80 mm synthetic
i stem, hollow run to satin) and Fremont, the tagline cells and Becker
byte-identical. False is the pre-flip engine (`PRE_FLIP`).
```

## `lettering_columns_square_ends`

```
Under `lettering_columns`, a column ENDS ON the letter's own outline
(2026-10-13, Kent: "we need to work on lettering and how they start /
end"; `columns._hold_end_faces`). The pull push moves every cross end
out along its own cross, and at a column END that cross is not square
to the edge it stops on: Kent's Fremont 81 mm hat job (PR #898's replay)
sewed HOTEL's E upper serif 0.29 mm past the arm's end face, the N's
diagonal foot as a 142-deg ear 0.30 mm under the baseline, and the M's
V as two fans pushed 0.41 mm below the vertex with a tuck run out under
it. ON, a cross end that starts on an outline edge running ACROSS its
column (more than `columns.END_FACE_DEG`, 45, off the column's
direction), or on an edge some column's end cross lies along (the E's
arm end, which its serif's side continues), keeps only the part of its
move that runs ALONG that edge; a fan lying on a cut gets no reach; a
tuck station must lie within the rails' side reach of the letter; and
no penetration ends further out than that reach. Measured
(`tools/column_ends.py`, PR body): Fremont 81 mm hat, 36 of the lane's
column ends past their face by more than 0.10 mm -> 1. 45 deg and the
0.10 mm tolerance are CANDIDATES (geometry, sized on no fixture; nothing
sewn, ROADMAP gate 1). Built OFF (Kent's call to flip); False is
byte-identical. Tests: `tests/test_column_ends.py`.
Follow-up, same flag (2026-10-13): a column whose end is one slanted
outline edge 8-45 deg off square (the N's diagonal foot on the
baseline) is MITRED -- its last crosses turn onto that edge
(`outline_cut._mitre_ends`); a penetration on two end faces meeting at
a corner (the M's V) is held at the corner; a side keeps its own push
(a cross under 0.44 mm reaches past `pull - 0.11`, and cut back there
golden_tee's thin bars fell under the cross floor). Fremont 81 mm: 0
ends past their face (#907: 1). ON since 2026-10-13 (Kent's ruling); False
is the pre-flip lane.
```

## `lettering_columns_text_lean`

```
Crosses square to the LINE OF TEXT in the Column lane (2026-10-23,
`digitizer_core/column_lean.py`; `docs/lettering-10mm-up-2026-10-23.md`).
The 10 mm and up band read against the pro's files: on Becker's
MARINE (12.8-17.1 mm caps, four garments) he sews every stroke with
the STEMS' cross -- square to the line of text -- diagonals included,
so the N's diagonal, the A's legs and the M's V carry the same sheen as
the stems and his junctions are plain overlaps. The lane stations each
straight piece square to its own axis (`outline_cut.scan_stations`),
so our diagonals read as another sheen and the M's V, where two leaned
pieces meet two upright ones, sews as a tangle (crops in the doc).
Kent's adopted convention (2026-09-03, `stitch-angle-convention`):
stems square to the line of text, a 30 degree lean cap, spacing over
cos of the lean -- the satin tier's `_clamp_to_span`, which the lane
displaced for lettering on 2026-10-12 without carrying. ON, every
straight column of a Column letter whose axis the word's house cross
(`satin_angle_deg`, the house pass; else the design's) can span within
the cap is re-stationed with its crosses along the clamped house, one
every spacing / cos(lean) along the axis so the distance between
crosses stays the satin spacing; a column the house already crosses
square, a curved or ring column, and a letter with no house angle keep
their stations byte for byte. Layout, not a cloth number (judged in
the preview, Kent 2026-10-22). ON by default since 2026-10-24 (Kent:
"Flip it ON", on `docs/big-letter-construction-2026-10-24.md`: leaning
crosses within 15 deg of the line of text 0.24 -> 0.51 at 76.5 mm and
0.17 -> 0.53 at 101.9 mm on MARINE, the pro 0.47-0.58, no piece added).
False is the lane as it was, station for station. Tests:
`tests/test_column_text_lean.py`.
```

## `small_glyph_keep`

```
Small glyphs the run tier rescues (`rescued_small_shape`), kept whole
(2026-10-13; ON by Kent's ruling 2026-10-13). Kent's Fremont at 81 mm
on a hat sewed "1895" as "098" (`tools/fremont_triage.py`). Both losses
are stage 4's hole
floor (`min_detail_mm`² / 4, 0.5625 mm²), which knows nothing of what
is in the hole:
  - the 8's and 9's counters (0.30-0.52 mm², transparent in the art)
    are filled, so each digit sews as the outline of a blob;
  - the white ground's hole where the "1" sits (0.47 mm²) is filled,
    so the 1's whole artwork lies under an earlier colour and stage 5's
    clip by what is already down (`grown.difference(earlier)`) leaves
    nothing: SHAPE_NOT_STITCHED.
ON: a rescued small shape keeps every hole of at least the run tier's
own floor (`machine.RUN_MIN_AREA_MM2`, no new number), and a rescued
small shape the earlier-colour clip would leave with NO ink sews its
artwork over the colour beneath, the way lettering sews over its
ground. Both are CANDIDATES (ROADMAP gate 1): no sew-out has settled
what a 0.16 mm² counter does on a cap. Fremont is unrepresentative --
it reproduces the defect, it sizes nothing. False is the engine before
this flag, byte-identical (md5-pinned in
`tests/test_small_glyph_keep.py`). Known open: the 8's lower counter
(a 2.05 mm ring) sews no ring, under `RUN_MIN_LOOP_MM` 2.2 (gate 1).
```

## `small_text_bay_mouth`

```
Keep each bay's mouth open (`small_text._open_mouths`, W3-02, #1085;
built OFF 2026-10-25 as `cfg.extra["small_text_bay_mouth"]`). The
re-set's widening sews a bay shut where a terminal curls back to its
own letter (Fremont's EST 1895 at 92.5 mm: E as B, S as 8, 5 as 3); the
pro ends the terminal short and keeps a mouth (median 0.51 mm, n 18,
`small_text.BAY_MOUTH_MM`). ON, such a terminal is cut back along its
own stroke until the bay keeps that mouth; stroke, bold scale, counter
floor and scale untouched. Acts only while the re-set
(`small_text_cap_mm`) is set. Layout (ruling 2026-10-22: judged in the
preview). **ON since 2026-10-26, Kent's flip** ("Flip ON"), promoted
from `cfg.extra` to a field so the default can be ON. False is the
re-set as it was, byte for byte; `tests/conftest.py` PRE_FLIP pins it
False. Tests: `tests/test_small_text_bays.py`.
```

## `legibility_check`

```
Legibility of the lettering on the RENDER, read back by OCR against the
artwork (quality review 2026-09-08 item 11; `preflight.
_legibility_findings`, `digitizer_core/legibility.py`): the one check
that can see sewn-but-illegible — `dropped_elements` reads 0.2% on a
design whose tagline Kent calls "completely lost". Needs the tesseract
binary (the Studio's Convert-to-text pass already does; CI installs
it) and the artwork, and costs one thread render plus about 24
tesseract reads (~3.5 s) per text cluster on every generate — priced in
docs/superpowers/plans/2026-09-10-legibility-yardstick.md §4.2. DEFAULT
ON since 2026-09-10 — built OFF in PR #449 and flipped in the PR after
on Kent's ruling over the OCR crops (option A: `LETTERING_ILLEGIBLE`
warns under `preflight.LEGIBILITY_WARN` and never blocks). The report
says `legibility_checked` either way — False here, without the artwork
or without tesseract — so off is never mistaken for clean. False is the
pre-flip report byte for byte.
```

## `keep_thin_strokes`

```
Keep a CONTRASTING sub-floor region instead of absorbing it into the
shape it touches (`stage3_segment.resolve_small_regions`). Today a region
under the detail floor that has any neighbour is unioned into whichever
neighbour shares the longest halo, whatever colour either is: a 0.5 mm
tan glyph on a white ground touches the ground and becomes ground; a
dark stroke drawn across a coloured panel becomes panel. That is the
flat lane's half of "whole elements missing" (`docs/superpowers/plans/
2026-09-08-real-logo-lane-and-thin-strokes.md` §3.1, §4b). ON, a small
region is absorbed only when it is plausibly a sliver OF its absorber —
its quantised colour within `merge_delta_e` (CIE76, the flat lane's own
merge tolerance; no new number) of the absorber's. A contrasting region
that clears the run tier's floors (`RUN_MIN_AREA_MM2` and the
`RUN_MIN_LOOP_MM` loop proxy) is kept for the run tier exactly as an
isolated small shape is today, and reaches stage 4 as a
`rescued_small_shape` — door 1 of the text cluster. One that fails the
floors is absorbed as before. The plan predicted `logo_whitebg`'s teal
patch would be one of those (1 mm, proxy 2 mm against 2.2); measured, it
is 1.19 mm with a 2.38 mm proxy, so ON it is kept and sewn as a 27-point
run in its own thread — one more cone, +3 stitches, +1 trim — and the
golden holds OFF only (both pinned in `tests/test_keep_thin_strokes.py`).

Measured 2026-09-08 on the stitches (`tools/thin_strokes.py --corpus
--forced-class flat --flag keep_thin_strokes`, scope-history 09-08):
see that entry for the per-fixture table.

ON THE GRADIENT AND PHOTO LANES the same flag adds a THIRD population
(`thin_ink.find_thin_ink`, plan §4c, PR 3): before SEEDS, the flat
lane's own quantiser runs over the foreground and every connected
component that reads as a stroke — thin along its whole skeleton (width
under `min_detail_mm` at the 90th percentile, at least
`THIN_INK_MIN_PX` wide), at least `RUN_MIN_LOOP_MM / 2` long, and ON ONE
GROUND (the two-pixel ring around it dominated by a single label, which
is what separates a stroke drawn on something from a band a posterised
ramp leaves between two levels) — leaves the SEEDS foreground and comes
back as its own label block after the palette, the way the enclosed
population already does. A superpixel is ~47 px a side on Fremont; a
0.4 mm stroke was a quarter of a block and gone before any floor.
GRADIENT CLASS ONLY: the pipeline passes the population gate as
`keep_thin_strokes and class_ == "gradient"`, so `photo_subject` and
`photo_scene` are byte-identical ON. Measured 2026-09-08 over the
committed photo fixtures (scope-history 09-08, three ring shares): the
population is empty on the smooth ramps and the stubs but NOT on the
photographs — the owl keeps 199 mm and the chrome 230 mm of "strokes"
at the share that keeps Fremont's lettering whole, and the share that
empties them (0.9) costs Fremont 15 of its 162 strokes — so the plan's
"empty on photographs" is met by the gate, not by the test. Where
nothing qualifies the gradient lane is byte-identical too. The photo
lane's `resolve_small_regions` still runs without layer colours: the
absorb rule above is the flat lane's, the population is this lane's.

DEFAULT ON since 2026-09-13 — Kent's ruling, on the flip sheet
`docs/thin-strokes-flip-2026-09-13.md` and its renders: *"Flip it — take
gaulke and becker as the price."* So the costs below are ACCEPTED, not
open defects, and they are written here in the terms he accepted them
in — they land on designs this flag cannot help, and nothing should be
spent trying to avoid them:

  - `logo_gaulke_roofing`: 2 → 4 cones (`0015, 4174, 0015` →
    `0015, 2564, 0111, 0145, 0015`) for ZERO recall change — 15 of 18
    thin strokes lost on either arm, on either garment.
  - `becker_marine_logo`: a second cone on a ONE-cone design
    (`1776, 1776` → `1776, 0020, 1776`) for one rescued region,
    +2 stitches, +1 trim.
  - `logo_golden_tee`: an extra colour stop and raw preflight −32 → −50
    (clamped F 0 both ways).
  - `logo_bridge_bar`: +29 regions and +28 trims (49 → 78 regions,
    96 → 124 trims) — its "thin strokes" are 400px-JPEG ringing, not
    artwork. With the BANKED `cfg.dissolve_phantom_blends` also on that
    bill collapses to +1 region and +1 trim (33 regions, 65 trims).
    Recorded as an OPEN LEAD, not a recommendation: that flag was ruled
    OFF and banked 2026-09-04 and the ruling stands; Kent did not rule
    on it here, and nothing should flip it on this evidence. (It was
    flipped ON 2026-10-20 on other evidence: item 46, PR #1003.)

What it buys, same sheet: Fremont 18 → 3 lost thin strokes (85.2% →
92.5%, the sub-0.5 mm band 52.2% → 92.0%) and C 64 → B 76 as TRIM_HEAVY
clears; drone's `AND DRONE` subline goes from not sewn at all to sewn;
the phone screenshot gets strictly cheaper (−153 stitches, −4 trims).
The added thread is the missing elements themselves — Fremont's tan cone
(`EST 1895`, `EAT | STAY | PLAY`) 1,478 → 3,428 while its white ground
gives back 444 — not spread cost.

THE HAIRLINE RESIDUAL, recorded honestly. ON, Fremont's
`STITCHES_TOO_SHORT` share goes 66% → 72% of satin stitches under the
1 mm needle minimum: the rescued strokes are 0.3–0.5 mm of ink and sew
as three-pass hairline beans. The flip ENLARGES that question rather
than creating it — `cfg.small_shape_rescue` (ON by default) already sews
sub-floor shapes this way today — and it is a ROADMAP **gate-1**
question: only a sew-out can say whether a 0.3–0.5 mm bean stroke marks
a knit or breaks thread. `cfg.lettering_min_column_mm` is the flag that
would widen them; it is itself a gate-1 number, still OFF, and measured
as not moving the tier (2026-09-09).

`False` remains the pre-flip engine exactly as it was, is reachable, and
stays tested: `tests/test_keep_thin_strokes.py` pins both arms of
`resolve_small_regions` on the same masks and pins the primary golden
holding OFF beside the teal patch being kept ON, and
`test_flag_defaults_on` there pins this default itself.
```
