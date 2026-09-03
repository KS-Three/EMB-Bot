# Fine-lettering design review — the write-up against the code, and what it changed (2026-09-03)

Kent asked for a spot check of EMB-Bot against a long "Embroidery 101"
write-up on digitizing fine-detail lettering: thread behaviour, how to judge
height, stroke and counter, pull and push, the satin/run/bean/fill choice,
stroke-level tiering, simplification and exaggeration, the underlay ladder,
density, direction, corners, spacing, font types, manual versus auto, the
sew-out, and a proposed OCR-plus-skeleton architecture. *"Anything worth
while denoted below?"* This file is the record: what the piece asks for that
already existed, the gaps it exposed, what Kent chose to build, what was
built, and every number measured on the way. Everything below was measured
on `digitize()` / `plan.iter_runs()` and the engine's own renderer, in a
fresh `python3.12` venv on the cloud container, against a pre-change
worktree at `e2aa965`.

## 1. The verdict

The write-up says nothing the project had not already written down. Its
rules are **Laws 45–58 in `docs/lettering-mastery-2026-08-01.md`**, and the
biggest of them had shipped before this review: the cap-height underlay
ladder, the house stitch angle with the corner join, the pull-comp counter
guard, the run-stitch rescue for tiny shapes, and the too-small preflight.
Its proposed architecture — skeleton plus distance-transform stroke width per
shape, a satin/fill/run verdict, pull comp, sequencing, text grouping, an OCR
pass — *is* the Python pipeline.

Mapping the piece against the code still surfaced seven rules that were only
half-built, and two places where the project's own measurements contradict
the textbook. Those were the useful part.

### Still open when the review was delivered

| # | Rule in the piece | What shipped then | Where | Now |
|---|---|---|---|---|
| 1 | Stitch type can change within one letter | A hairline stroke inside a satin letter lost every cross under the floor and was dropped; only a whole shape fell back to fill or run | `stage6_satin.py` satin_stroke | **built, both engines** (§3, §5) |
| 2 | Is this column wide enough for satin at all | Font path had no width floor; the only guard was 0.3 design pixels | `satinplay.js` emitZigzag | **built** (§5) |
| 3 | Does this object need underlay | Python laid a center run under every satin stroke, sub-mm letters included | `stage7_sequence.py` satin branch | **built** (§4) |
| 4 | Enlarge, never close, the counters | Bold adds 0.3 mm to pull comp with no counter guard | `digitize.js` | **built** after PR #331 (§9) |
| 5 | Recognise the letters, then re-set them | Convert-to-text only saw rescued small shapes; ordinary wordmarks never got the badge | `textcluster.py` _candidates | **built** (§6) |
| 6 | Corners and tight bowls are where it fails | No short-stitch handling in the font path | `satinplay.js` | open, needs width gating |
| 7 | Small text wants more open density | Fixed 0.4 mm pitch in both engines | `machine.py` | gate 1 — card block 5 |

### Where the piece is wrong for this project

- **"Thin strokes go to run, not satin" is disproved at shape level on flat
  art.** On real client logos, 61 of 64 sub-millimetre satins were ground the
  professional also satined (`satin-gate-attribution` in memory). The rule
  survives only per stroke — item 1 — and on the photo lane, where it already
  ships.
- **Its density advice cannot be acted on from the desk.** The slope is a
  physical constant. Block 5 of `docs/sewout-card-2026-07-31.md` is where
  items 1, 3 and 7 get their numbers, and that is a standing fact, not a
  request to schedule it.

## 2. Kent's calls

Asked which gaps to take on: **1, 2 and 5**, all three. Asked whether the
Python engine should adopt the JS engine's 5 mm underlay rung (item 3): **gate
it now**, using the existing number rather than a new one. Item 6 (short
stitches in the font path) and item 7 (density) were not chosen and are
unchanged. Item 4 (a counter guard on Bold's widening) was Kent's pick for
the follow-up once PR #331 merged, and is §9.

One thing went a step past the approved wording, and is flagged here and in
the PR: the font-path guards were approved as *"warn only, no clamp"*, and
the warning is warn-only — but the cross floor alone, dropping crosses one at
a time, left the surviving crosses joined by chords across the glyph on an
outline face (cooper_marif: a diagonal through the F). So the font path got
the same hairline-stretch run fallback as the Python engine. Sizing is still
the user's; nothing is clamped.

## 3. Item 1 — a hairline stretch sews as a bean run (Python)

**Mechanism (defect 24).** `satin_stroke` drops any cross under
`SATIN_MIN_CROSS_MM` (0.5 mm). A *run* of dropped stations — an E's arm, a
T's bar, the thin half of a stroke that changes weight — left the zigzag to
hop from the last survivor to the next, and the artwork between them sewed
nothing. Hotel Fremont at 92.5 mm lost 41 of 282 strokes and 83.5 mm of
spine that way, and the corner-joined bar of a T lost both halves while its
junction crosses survived (the join keeps each member's junction cross, so a
whole-stroke fallback never fires — the split has to be per station).

**What ships.** Stations are classified by cross length, run-length encoded,
and short runs of either kind absorbed into their neighbour until every run
clears `min_seg` stations (`_hairline_stretches`). A thin stretch of at
least two bean stations (2 × 0.73 mm of spine — three penetrations, under
which the needle re-enters its own holes) sews as a 3-pass bean along its
own spine stations (`_bean_along`), and `satin_stroke` now hands
`satin_shape` the stroke as PARTS in station order: satin / run / satin.
Adjacent satin parts across a corner-joined member are merged with the same
seam hop the flat list gets, so a joined stroke with no hairline is still one
part. `satin_shape` sews the parts in order — underlay only under the satin
parts, and never under a shape under the 5 mm rung (§4) — and stage 7 counts
them: `HAIRLINE_STROKES_AS_RUN` with `{count, shapes}`, which the Studio
reads as *"N strokes were too fine for satin and sew as running stitches
instead."* Every number is an existing constant (`SATIN_MIN_CROSS_MM`,
`BEAN_STITCH_MM`, `BEAN_PASSES`); gate 1 is untouched.

**A stretch shorter than three bean stations stays dropped**, exactly as
before: measured on ENTHUSIAST at 80 mm, a 0.8 mm dip inside a letter from a
0.45 mm rail dent (defect 23) was becoming a bean tail and took the chaining
benchmark from 3.8 to 5.0 trims per 1k. With the floor it reads 3.81/1k
(12 trims on enthusiast @ 93 mm, budget 4.1).

**Only where the ART has ink (the needle).** After the fallback landed, the
Fremont render grew a dark tick above the hexagon band that the source has
no trace of: a 1 mm long, 0.04 mm wide vectorization needle on a black
sliver (`S06ca1ceb`, exterior vertices `(17.87,−17.11) (18.17,−18.11)
(17.83,−17.11)`), under the outline tolerance stage 4 simplifies to
(`config.simplify_tol_mm`, 0.2 mm) and so never promised by the artwork —
but stage 5's pull compensation grew it into a stroke whose spine cleared
the run floor. A hairline stretch is now trimmed at both ends while the
cross, measured in the region's own **uncompensated** polygon, spans less
than that tolerance (`_trim_to_art`; stage 7 passes `p.region.polygon` and
`cfg.simplify_tol_mm`). A dip inside a stretch is left alone. Direct callers
and every existing test pass nothing and are byte-identical. This floor is
Python-only on purpose: fonts have no vectorizer, and a designed hairline in
a font is always intentional.

**Measured** (`digitize()` + the engine renderer, pre → with the fallback →
with the art floor):

| fixture | stitches | trims | runs | underlay |
|---|---|---|---|---|
| Hotel Fremont 92.5 mm, patch | 10185 → 10461 → **10197** | 115 → 114 → **112** | 167 → 586 | 446 → 408 (§4) |
| drone_render 80 mm, left chest | 8729 → 8797 → **8716** | 93 → 95 → **93** | 281 → 472 | 1101 → 993 (§4) |
| enthusiast_logo, becker (goldens) | byte-identical | | | |

Rendered: Fremont's 2.6 mm "THE" reads **THE** where before the E had no
arms and the word read as "T H ."; the beige "STAY | PLAY" subline at 2 mm
gains a Y it did not have, minus one arm the art floor trims — that subline
is below what either engine renders (item 7's territory), so this is not a
loss against the pre-change output. The needle tick is gone with the floor,
and the floor took Fremont from +276 stitches to +12 and drone from +68 to
−13 with its two extra trims gone: most of what the fallback had found on
those two was compensation-grown nothing, and what survives is the lettering. The full
suite fails only the three platform goldens CI deselects (§8).

## 4. Item 3 — no satin underlay under a 5 mm shape (Python)

`SATIN_UNDERLAY_MIN_EXTENT_MM = 5.0` in `machine.py`, the JS engine's own
`UNDERLAY_CAP_MIN_MM` (Law 50, rung 1: under a 5 mm cap, no underlay).
Stage 7's satin branch passes `underlay_style="none"` when the region's
bbox extent is under it; a hairline stretch gets no underlay at any size
(Law 50's ladder puts nothing under a running stitch, and a centre run under
a bean run would be thread under a needle that already returns three times).
Not a new number; Kent's call to gate it without a sew-out is recorded in
§2. Fremont's underlay 446 → 408 points, drone 1101 → 993.

## 5. Items 1 and 2 — the font path (JS)

Landed first, as commit `0a67171`; the full record is in
`docs/scope/2-font-library-lettering.md`, "The size guards the font path did
not have". In one paragraph: `emitZigzag` takes `minCrossMm` and
`layoutText` passes `SATIN_MIN_CROSS_MM / fitScale`, so the floor is 0.5 mm
on the fabric; a satin span is split by its width profile
(`splitByCrossFloor`) into satin stretches and bean stretches
(`beanFromGeom`, 3 × 0.73 mm, the same three-bean-station floor), with a
sewn-nothing stretch walked as underpath so the Euler circuit stays
continuous; `layoutText` returns `lettering` (cap height, stroke length and
the share under 1.0 / 0.5 mm, hairline stretches, floors), carried out by
`buildLetteringDesign` on empty results too, and `generate.letteringNote`
shows one line beside the hoop note. 83 fonts × "Fritsch" × three widths
against the pre-change tree: at 50 mm, 4 fonts move by more than 5%, all
hairline-authored (cooper_marif −39%, mai_en_fleur −33%, cats −7%,
montecarlo −6%); at 100 mm one (mai_en_fleur −15%). mai_en_fleur at an
11 mm cap fragments — 78% of it is under 0.5 mm there, which is what the
note now says; that is the trade-off, and it is reported rather than hidden.

## 6. Item 5 — Convert-to-text sees ordinary lettering

**The history.** `detect_text_clusters` admitted only `rescued_small_shape`
regions, so a real wordmark never got the "looks like text" badge:
`becker_marine_logo.png` 17 regions → 0 candidates, `drone_render.png` 74 →
0 clusters (measured 2026-08-26). A widening (`10ae9cc`) was built and
reverted the same day for three reasons, all recorded in
`docs/scope/1-auto-digitizing-quality.md`: the e2e spec asserted page-wide
that zero badges remained after converting one cluster; the star inside
enthusiast's red shield joined "ENTHUSIAST" as an eleventh letter; and a
suspected cost regression when CI's `test_service` polling budget (60 s)
expired. Thread identity as a fix was disproven — drone's letters come out
of quantization on six threads.

**What ships — two doors, two rounds.** `_candidates` (the rescued door) is
unchanged and is clustered FIRST, on its own, with the original bounds. Every
cluster that regularizes today is therefore computed by exactly the code it
was computed by yesterday: byte-identity for the measured population by
construction, not by a flag that happened to hold. Then `_letter_candidates`
(the letter door, 10ae9cc's bounds: aspect, `LETTER_MIN/MAX_HEIGHT_MM` 1.5
and 60 as a sewability floor and a cost ceiling, `LETTER_STROKE_CV_MAX` 0.55
because whole glyphs cross junctions and read 0.41–0.48 on Becker where
fragments read under 0.32) plus any rescued leftover is clustered with
`LETTER_HEIGHT_RATIO` = `SATIN_ANGLE_HEIGHT_RATIO` (0.8: one text element is
one line at one size — Becker's MARINE at 16.2 mm and arched BECKER at
25–33 mm were one cluster at 0.5, drone's three lines at 2.9 / 5.7 / 7.6–8.5 mm
one 23-member cluster) and the one-ink link. A cluster with any ordinary
member carries `text_cluster_all_rescued = False` and
`regularize_text_clusters` skips it with reason `cluster_not_all_rescued`:
tagged and grouped for the badge and Convert-to-text, never redrawn.

**The star (the one-ink link).** A word is sewn in one ink, but quantization
scatters one object across near-identical cones, so `_same_ink` is a
CIEDE2000 tolerance on the job's chart (`threads.chart_for(cfg)`, passed by
the pipeline), `TEXT_CLUSTER_DELTA_E_MAX = 20`. Measured with
`threads.CHART.delta_e`:

| pair | ΔE | outcome |
|---|---|---|
| drone PRECISION greys 0111 / 0142 / 0145 / 3971 | chain links ≤ 16.4 (pairwise max 25.3) | keep |
| drone THERMAL oranges 1102 / 1305 | 8.7 | keep |
| summit small greys 0108 / 0142 | 7.4 | keep |
| enthusiast letters 0134 Smoky vs the star 1720 Not Quite Red | **34.2** | split |
| drone PRECISION (greys) vs THERMAL (oranges) | ≥ 27.7 | split |
| summit's three big graphic shapes 0904 / 2732 / 3130 | 18.6 / 46 / 55 | pair only → no cluster |
| drone fragment pair 0142 / 3654 | 39.6 | split |

20 sits in the (16.4, 27.7) gap. It is not a perceptual bound (5 is already
"different colours" on the scale `preflight.DELTA_E_VISIBLE` cites) but a
measure of how far quantization scatters one object, calibrated on these
fixtures only — provisional, like `LETTER_STROKE_CV_MAX`. A thread the chart
cannot place is no colour evidence and geometry decides, as before. The
inter-glyph gap was the other candidate and is measured dead: the star sits
7.1 mm from the E at 7.3 mm caps (0.97 heights) while ENTERPRISES INC's own
word space is 2.8 mm at 1.8 mm caps (1.56 heights) — a gap bound that
excludes the star splits the subline.

**What it finds** (`run_stages`, quiet machine, post):

| fixture | clusters | members (thread) | rescued |
|---|---|---|---|
| enthusiast 90 mm | 2 | ENTHUSIAST 10 (0134) — the star is out; ENTERPRISES INC 14 (0134), **same cluster id as before** | 0 / 14 |
| becker 100 mm | 2 | 6 + 5, one thread (BECKER, MARINE) | 0 |
| drone 80 mm | 3 | 10 greys (PRECISION), 4 oranges (THERMAL), 7 Whale (AND DRONX) | 0 |
| Hotel Fremont 92.5 mm (probe) | 3 | HOTEL FREMONT 13, THE 5, three rope fragments | 0 |

The rope fragments and summit's `'M/|?ET?2Q24'` show what the letter door
still admits: `_cluster` is the filter, not admission, and a three-fragment
cluster costs a badge, not a stitch.

**Cost, measured directly this time** (the instruction the revert left),
quiet box, single run each, `run_stages`:

| fixture | pre → post | detect | OCR | house angle | tagged |
|---|---|---|---|---|---|
| enthusiast 90 mm | 7.9 → **8.8 s** | 0.60 → 0.97 s | 1.77 → 3.16 s | 1.86 → 0.96 s | 14 → 24 |
| drone 80 mm | 25.9 → **28.8 s** | 0.32 → 1.67 s | 0 → 2.79 s | 3.21 → 1.47 s | 0 → 21 |
| becker 100 mm | 2.0 → **3.4 s** | 0.00 → 0.51 s | 0 → 1.39 s | 1.13 → 0.62 s | 0 → 11 |

Two things paid for most of it. `_skeleton_stroke_stats` is now memoized on
the polygon (immutable, hashed on its bytes): the rescued door, the letter
door and `_lettering_groups` were skeletonizing the same regions three
times, and the house-angle pass halves. OCR is ~0.13 s per glyph, almost
all of it process spawn (`_OCR_RASTER_TARGET_PX` caps the crop, so a 30 mm
glyph costs what a 2 mm one does), and it is serial ON PURPOSE: a
four-thread pool over pytesseract was tried and took enthusiast's 24-glyph
pass from 3.3 s to **21.8 s** — each tesseract process opens its own OpenMP
team and four of them thrash four cores (serially, `OMP_THREAD_LIMIT=1`
measures 129 vs 132 ms, no difference). Measured negative, recorded in the
code.

**The contention story, which is the one that matters for CI.**
`test_review_payload_carries_text_cluster_fields_over_http` runs in
**12.4 s** solo against its 60 s budget — and timed out at `running` three
times in this session under `-n auto`, including a quiet full run (this box
takes 26:20 for the suite, 2.5× the reference machine). Measured pre vs
post under three CPU hogs: idle 11.1 vs 11.9 s, hogs **19.3 vs 32.7 s** —
ten extra tesseract spawns cost 13 s under contention, ten times their idle
price. Tesseract opens an OpenMP team per process and OpenMP workers
spin-wait, so every glyph fights the other workers for the cores. With the
child pinned to one thread (`_one_tesseract_thread`, `OMP_THREAD_LIMIT=1`
on the live `os.environ` pytesseract hands to the child, restored after) the
same test under three hogs takes **12.1 s** — faster than the pre-change
tree under the same load, and immune to it. That is the likeliest root cause
of the `10ae9cc` CI timeout (four concurrent runs), and it is fixed at the
source rather than by raising the budget.

**The Studio.** No code change. The e2e spec
(`app/e2e/text-cluster-convert.spec.js`) reads the converted bar's own
"N shapes" count and asserts per cluster — the other cluster's badges stay,
`unstitched` grows by exactly N, "hidden — converted to text" appears N
times, Undo restores exactly N — where it used to assert zero badges
page-wide. `textClusterSeed` already votes the colour and gates the OCR
suggestion at min-confidence 55, so ENTHUSIAST (`'xENTaUS:AST'`, min 0)
seeds an empty text box and MARINE-class reads (89–96) would seed a guess.

## 7. What did not change, and why

- **Item 4**, Bold's +0.3 mm pull comp with no counter guard: not chosen.
- **Item 6**, short stitches on inside curves in the font path: not chosen,
  and it needs a width gate first.
- **Item 7**, density for small text: gate 1; card block 5.
- **The small-lettering TIER** defect 24 asked for is still open. What closed
  is the mechanism that lost the strokes; whether a 0.5 mm bean reads better
  on cloth than a dropped bar is card block 5's INC question and stays
  `pending sew-out`.
- **`_lettering_groups` (the house angle) is untouched**, and so is every
  house-angle golden; the letter door reuses its height ratio but not its
  admission, so the angle and the badge can disagree on a fragment.
- **Regularization on ordinary lettering** was not attempted; the reasoning
  in `10ae9cc` stands and is now enforced structurally (round order), not
  only by the flag.

## 8. Verification

- Python: full suite after the hairline work — 4 failed / 1668 passed, the
  three platform goldens CI deselects plus the service test's 60 s budget
  under a saturated box (13.0 s solo, above). Goldens subset after the text
  clusters and the art floor: see the PR body.
- New tests: `tests/test_small_lettering.py` (9: the T bar, the bean tier's
  numbers, an all-hairline shape, the three-station floor, the byte-identical
  plain bar, the stage-7 warning, the 5 mm rung both sides, the rung is the
  JS number, the needle); `tests/test_textcluster.py` +9 (the letter door,
  both CV bounds, floor and ceiling, two rounds, tagged-not-redrawn, the
  leftover, two lines at two sizes, the star, the unknown thread).
- JS: `test/satinplay.test.js` +7, `test/satinfont.test.js` +6,
  `app/src/lib/generate.spec.js`, `app/src/lib/digitizer.spec.js`
  (`HAIRLINE_STROKES_AS_RUN` text). Engine 458/458, Studio 918/918.
- Renders: `fremont_pair.png` / `fremont_post_pair.png` /
  `drone_pair.png` in the session scratchpad; the crops described in §3 were
  read, not inferred.

## 9. Item 4 — the Bold counter guard (follow-up, Kent's pick after PR #331)

**Mechanism.** The Bold weight preset widens every column by pushing its
rails apart — `WEIGHT_OFFSET_MM.bold`, 0.3 mm, folded into `pullCompMm`
and applied by `emitZigzag` as one shared offset. A counter in a satin-column
font is nothing but the gap between two rails that face each other (the eye
of an e, the slot between two stems, a script connector beside its stroke),
so bold closed every counter by the same 0.3 mm it added to the strokes:
at 0.72 mm a counter went to 0.42, under the width at which two rails pile
thread on a point, and at 0.36 mm to 0.06 — gone. The Python engine's pull
comp already holds a HOLE open when shrinking it would take it under the
detail floor (`stage5_overlap`, `hole_floor`); the font path had nothing,
and its own comment said so: *"if a different font's tightest glyph
collapses a counter at bold, shrink `WEIGHT_OFFSET_MM.bold`"* — a global
answer to a local problem.

**What ships.** The weight travels apart from the fabric's pull comp
(`weightMm`, pre-divided by the fit scale like everything else; the sum is
what it was, so normal and thin are byte-identical). `routeGlyph` samples
every rail of the glyph into a cloud with outward normals
(`satinplay.railCloud`, at the station spacing), and per station each rail
asks what faces it straight ahead (`counterGap`: the nearest rail whose
normal points back, within 1.5 stations to either side; Infinity on an
outside edge, since a column's own far rail is behind it). `stationPush`
then gives each rail the fabric's pull in full — that is physics, gate 1's
— plus the weight: whole on an open edge; across a counter no more than the
gap can spare after the pull with the floor kept, half per side; nothing at
all where the gap is already under the floor at normal weight. The floor is
`SATIN_MIN_CROSS_MM` — two rails 0.5 mm apart pile thread whether they are
one column's or two neighbours' — so no new constant. `splitByCrossFloor`
classifies with the same per-station widening, so a stretch it calls satin
keeps its crosses. `lettering.counterHeld` counts held rail stations and
`lettering.weightMm` the weight on the fabric; there is no Studio note,
because the count also includes near-touching junctions (a bar's end
0.2 mm from a bowl), where holding the weight is right but "counters" would
be the wrong word. Only the glyph's own columns are in the cloud: the gap to
the next letter is letter spacing's business.

**Measured on the two-stem probe** (1.8 mm stems, 0.3 mm weight, no pull):

| counter at normal weight | bold, unguarded | bold, guarded | outside edge |
|---|---|---|---|
| 1.44 mm | 1.14 | 1.14 (nothing held) | +0.30 |
| 0.72 mm | 0.42 | **0.50** (the floor) | +0.30 |
| 0.36 mm | 0.06 | **0.36** (untouched) | +0.30 |

**Measured on the library**, "Fritsch" in every shipped font, bold with and
without the guard:

| | fonts with a hold | stitches bold guarded / unguarded / normal |
|---|---|---|
| 25 mm | 60 of 83 | 70,162 / 73,183 / 67,276 |
| 50 mm | 54 of 83 | 108,506 / 109,950 / 106,169 |

Two things the sweep shows that a counter-only reading would miss. Decorative
faces hold at large caps (initials_XL, 35 mm cap, 725 stations) — those are
junctions and ornaments nearly touching, not counters, and the weight simply
stops short of a neighbouring column. And on hairline faces the guard
changes what bold IS: unguarded bold on mai_en_fleur at 25 mm took 1,222
stitches to 3,043 by widening every hairline connector past the cross
floor into a dense satin column, closing the gaps it wove through; guarded,
the connectors that sit between strokes keep their gaps, stay under the
floor and sew as bean runs (18 hairline spans against 0), and bold lands at
1,393. Bold now means "thicker where there is room", which is what a type
designer's bold does too. Whether a user reaching for Bold on a hairline
script wanted the closed-gap version is a taste question this doc records
rather than settles; `counterGuard: false` is one flag away, measurement
only, not a UI setting.

**Tests.** `test/satinplay.test.js` +3 (the facing-gap query on an outside
edge and across a gap; the per-station push whole / capped / withheld, pull
comp never held, legacy one-number identity; `weightMm` + `pullCompMm`
byte-identical to the folded number for bold and thin);
`test/satinfont.test.js` +2 (the three-gap table above, outer width +0.3
throughout; normal and thin untouched, weight reported on the fabric);
`test/digitize.test.js` +1 (geneva "Kent" at 2.6 mm caps holds, stitch count
within 1% of unguarded, thin and normal identical with the guard off).
Engine and Studio suites green; the run-font pins did not move.
