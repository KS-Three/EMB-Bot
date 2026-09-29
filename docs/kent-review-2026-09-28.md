# Kent's review, 2026-09-28 — eleven pending flags and the 08-27 engine, labelled before | after

> **OUTCOME — Kent picked two things on this review (2026-09-28), and both
> landed 2026-09-29:** `cfg.satin_rail_comp` is **default ON**, and the page
> has a change locator. The flip's price, which no render sitting could show,
> is in the "Outcome" section at the end: MARINE at 80 mm goes **9 → 22
> trims** at +15% stitches; ENTHUSIAST's `lost_frac` drops under its bar for
> the first time (0.2748 → 0.2565) while its bare artwork rises 6.27 → 7.10%;
> Becker at 114 mm under `wide_columns` loses the fold guard's margin. **Kent
> took the price** (2026-09-29, shown the table: *"Take the price, let it
> merge"*), so it is an accepted price, not an open defect. Not picked:
> retiring `screenshot` from the corpus.

**Result, in Kent's words: "The changes were VERY hard to tell the differences
with the 'before and after' by the human eye."** He judged all 77 pairs on the
rebuilt page (PR #514) over four sittings between 2026-09-20 and 2026-09-28.
No per-arm ruling was set on the page, so nothing flips; this doc records
what his eye said and what it licenses.

Two things did read at full-design view:

- **Today's engine beats the 08-27 engine on 7 of 9 logos**, with a note on 8
  of the 9 pairs; the other two logos were bad under both engines. This is the
  first direct measure of the month's engine work against his eye.
- **`satin_rail_comp` is the only flag with a positive lean**: 5 after better,
  0 before better, 4 both bad. Three flags lean the other way wherever they
  change anything: `directional_comp` (4 before better), `lettering_min_column_mm`
  (2 of 3), `wide_columns` (1 before better, 5 both bad).

And one thing stays true from the 2026-09-18 review: a handful of logos are
bad under both settings of most arms — gaulke, golden_tee, screenshot, and
drone — so no flag rescues them.

## What was shown

- **The page:** `https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp`, rebuilt by
  `tools.eye_pairs_gallery --labelled` (PR #514): the nine `REAL_ART` logos at
  their own width and garment, `max_colors=6`; BEFORE shipped on the left and
  AFTER the flag on the right, the flag named; for the 08-27 arm, the old
  engine on the left and today's shipped engine on the right. 77 pairs: every
  (logo, arm) whose stitches differ from shipped; 31 identical and not shown.
  Rendered in a cloud container with the cutout venv present, so tires shows
  the cutout on both sides (the 09-18 page did not).
- **Carried over:** the 34 first-sitting verdicts (six flags, 2026-09-18) with
  their ids migrated. One was re-judged: `satin_patch_junctions="satin"` on
  enthusiast, *no difference* → *after better*, flag did its job. The three
  tires pairs from that sitting were not re-clicked, so their verdicts now
  stand on the cutout renders.
- **Pace:** 43 new pairs plus one re-judgement across 2026-09-20 20:47–20:53
  UTC (rail_comp, lettering_column, directional_comp, patch_junctions),
  09-22 16:25–16:28 (wide_columns, four of the 08-27 pairs), 09-23
  01:49–01:51 (the other five 08-27 pairs, rail_comp on screenshot), and
  09-28 23:45–23:46 (phantom_dissolve). About 15 s a pair, with notes on 10.

## Verdicts

Pairs / verdicts per arm. *Job* is "did the flag do what it claims?": yes /
no / can't tell (two directional_comp pairs were left blank; the 08-27 arm
has no job control).

| arm | shown | after better | before better | no difference | both bad | identical, not shown | job y/n/? |
|---|---|---|---|---|---|---|---|
| `satin_polygon_axis="artwork"` | 9 | – | – | 8 | 1 (enthusiast) | 0 | –/–/9 |
| `satin_rails_follow_edge` | 9 | 1 (tires) | – | 8 | – | 0 | 1/–/8 |
| `design_angle` | 9 | – | 1 (tires) | 8 | – | 0 | –/–/9 |
| `satin_per_stroke` | 3 | – | – | 3 | – | 6 | –/–/3 |
| `satin_patch_junctions="satin"` | 2 | 1 (enthusiast) | – | 1 | – | 7 | 1/–/1 |
| `classify_area_weighted` | 2 | – | – | – | 2 (drone, screenshot) | 7 | –/–/2 |
| `satin_rail_comp` | 9 | 5 (becker, bridge, enthusiast, fremont, tires) | – | – | 4 (drone, gaulke, golden_tee, screenshot) | 0 | 3/–/6 |
| `wide_columns` | 8 | – | 1 (becker) | 2 (screenshot, tires) | 5 (bridge, drone, enthusiast, gaulke, golden_tee) | 1 | –/–/8 |
| `lettering_min_column_mm=1.0` | 3 | – | 2 (enthusiast, fremont) | – | 1 (screenshot) | 6 | 1/–/2 |
| `dissolve_phantom_blends` | 5 | 1 (bridge) | – | – | 4 (gaulke, golden_tee, screenshot, tires) | 4 | –/–/5 |
| `directional_comp` | 9 | 1 (drone) | 4 (enthusiast, fremont, gaulke, tires) | – | 4 (becker, bridge, golden_tee, screenshot) | 0 | 1/–/6 |
| engine at `25da2fe` (08-27) → today | 9 | today 7 (becker, bridge, drone, enthusiast, fremont, screenshot, tires) | then 0 | – | 2 (gaulke, golden_tee) | 0 | – |

Totals over the 77: 16 after better, 8 before better, 30 no difference, 23
both bad. On the 68 flag pairs the job question was answered *can't tell* 59
times, *yes* 7, *no* never.

## His notes, verbatim

- `satin_rail_comp` / tires (after better, job yes): *The "I" and "S" improved,
  The top of the "r" has thread missing*
- `directional_comp` / screenshot (both bad): *This is a shitty logo, don't
  use this one anyore.*
- 08-27 → today / becker (today): *After actually captures the "C" border in
  Becker, The MARINE improved, but still has oportnuities for improvement*
- 08-27 → today / bridge (today): *The yellow back stitching looks cleaner*
- 08-27 → today / drone (today): *More detail on the woods imagry*
- 08-27 → today / enthusiast (today): *The Red logo trim is much cleaner.*
- 08-27 → today / fremont (today): *"THE" and "EAT STAY PLAY" is cleaner*
- 08-27 → today / screenshot (today): *Before image has letters all over the
  place.*
- 08-27 → today / tires (today): *After has much smoother bordering edges*
- 08-27 → today / gaulke (both bad): *TO very different to tell what's being
  done here.*

The full store, including the first sitting's docs, is
`docs/eye-pairs-2026-09-28/kent-notes.json`.

## What it says

**The engine moved since 08-27, and his eye saw it.** Seven of nine today,
none for the old engine, and the notes name what moved: cleaner trims and
borders (enthusiast, tires, bridge), letters where they belong (screenshot),
the C border and MARINE on becker, the wood detail on drone. The two both-bad
logos, gaulke and golden_tee, are bad under both engines. This licenses one
sentence and no more: the work between 2026-08-27 and 2026-09-18 reads as
better to him at full size on seven of nine real logos. It says nothing about
the distance to Ember (`.claude/memory/kent-eye-vs-instruments-2026-08-27.md`
holds that datum, and this page never showed Ember), and the tires pair is
environment-confounded as the page's badge says: the old engine ran in a
worktree without the cutout venv. Note also that these pairs were the easy
ones to tell apart — the old engine's becker has 6,702 stitches to today's
17,701 — so "very hard to tell" is about the flag pairs, not this row.

**`satin_rail_comp` is the flag to look at, and the only one.** Five after
better against no before better, the flag did its job on three (enthusiast,
fremont, tires), and his tires note names a gain and a cost in the same
breath: the I and S improved, the top of the r lost thread. The four both-bad
logos are the four that are both-bad under most arms, so they do not count
against it. Its intent is to put the pull compensation on the rails instead
of the polygon buffer; whether a flip needs a sew-out is ROADMAP gate 1's
question, since it moves where compensation is applied, not how much.

**Three flags made logos worse where they acted.** `directional_comp` lost
on four logos and won on one; `lettering_min_column_mm=1.0` lost on both
logos it changed for the better-or-worse question; `wide_columns` lost on
becker and was both-bad on five. Nothing here argues for flipping any of
them, and the first two argue against. `dissolve_phantom_blends` won on
bridge alone and was both-bad on four.

**The both-bad logos are an engine problem, not a flag problem.** golden_tee
is both bad under five arms, screenshot under five, gaulke under four, drone
under three. No flag rescued any of them; the 08-27 engine did not either
(gaulke and golden_tee both bad there too). The 2026-09-18 review named
three both-bad logos as the lead if quality work resumes; it is these four.
For screenshot his note is a ruling on the fixture itself: don't use it
again. It is wired into `tools.thin_strokes.REAL_ART` and eight other tools;
retiring it is its own change.

**"Very hard to tell" is a tool finding as much as an engine one.** 30 of
77 read as no difference and 59 of 68 job questions as can't tell, and the
page still gives no pointer to where a pair changed — the 09-18 review said
the same and measured that the changes are local (0.05% to 38% of a design
after a blur). A change locator on the page (outline or auto-zoom to the
largest changed region) is the obvious next step for the instrument, and it
would make the next sitting faster and less "can't tell". Not built; Kent's
call.

## Side effects recorded elsewhere

- **Blinding:** every one of PR #506's ten blind-sitting arms, plus
  `rails_follow_edge`, has now been seen labelled on these nine logos. A blind
  sitting on them is contaminated for every arm; one would need logos he has
  not judged here.
- **The 09-18 tires verdicts** (`rails_follow_edge` after better,
  `design_angle` before better, `polygon_axis` no difference) were given on
  no-cutout renders and were not re-clicked on the cutout ones. They stand as
  given; read them with that in mind.
- **Rulings:** none set. The page's per-arm ruling controls (flip ON / keep
  OFF / needs work) are still there, and a session can read them back the
  same way this doc was made.

## Outcome — the flip landed 2026-09-29, and what the suite priced

Kent's picks on this review were **flip `satin_rail_comp` ON** and **build the
change locator**; both are in the PR after #549. The flag's default moved one
line; the suite is where the flip was priced, and three of its readings are
things his eye could not have seen on the page.

**Blast radius, measured the way #481 measured `keep_thin_strokes`.** The
first full run on the flipped engine was **39 failed**. The same 36 (less the
flag's own file and a rembg timeout) run against a worktree at the pre-change
commit (`main` at 72102e8a) returned **3 failed** — the three node IDs CI
deselects — so 33 were the flip's or the machine's. Four of those turned out
to be the machine's: `test_shade_palette_demand`'s photo_subject stub,
`test_photo_sequencing`'s two-square depth sort and the owl in both
`test_merge_adjacent_same_thread` and `test_is_photographic` fail on ANY
tree the moment `rembg_isolated/venv` exists (the pre-change tree with the
venv linked in: the same four), which CI never has and a cloud session that
rendered the page does (filed as #553). That leaves **29 tests in 14 files
as the flip's**, handled per the repo's own conventions:

| What moved | Tests | How it was handled |
|---|---|---|
| Flat-lane golden, 3 keys (`whitebg` 4575 → 4580, `alpha` 4595 → 4602, `ribbon` 991 → 990 coords; ids, areas, warnings unmoved) | 6 (`test_flat_lane_byte_identical`, `test_stage2_photo_segment`) | re-captured with `recapture_flat_lane_key.py --pre-change-tree`, `machine OK` on each; `enthusiast` refused (platform red, deselected) |
| `test_pushcomp`'s isotropic pins, 3 of 4 tuples | 4 (incl. `test_shape_overrides`) | re-pinned where the pre-change tree reproduces; `towel` recorded, not written |
| The polygon-growth harness (`column_of`) reading no overhang on the rails | 7 (`test_pushcomp`) | harness pinned to `satin_rail_comp=False`; the rails' hand-off is `test_rail_comp`'s |
| Tests pricing another flag on the fixture they measured | 6 (`test_preflight`'s injection; `test_wide_columns`; `test_corner_twigs`, `test_edge_cap_lettering`, `test_trim_levers` ×2) | pinned on the grown polygon, dated, with the rails' reading in the note; the flag also joins `conftest.PRE_FLIP` as the standing posture |
| Geometry guards reading a satin column's rails as "outside" its planned polygon | 2 (`test_contour`, `test_planning`) | the sewn footprint of a satin-tier shape is its artwork plus the pull |
| Synthetic fixtures the flip exposed | 2 (`test_borders_last`'s ribbon lay INSIDE the fill and survived OFF only as a 0.3 mm rind; `test_photo_sequencing`'s 1.4 mm ribbon sat 0.1 mm under the zigzag line) | fixture geometry corrected (ribbon beside the fill; 1.2 mm) |
| The lettering instruments | 2 (`test_lettering_coverage_regression`) | the strict xfail XPASSed and is retired; the bare bar re-pinned with the trade attributed |

**What the flip costs, on the instruments, same tree, OFF → ON (2026-09-29):**

| Fixture | Instrument | OFF | ON |
|---|---|---|---|
| MARINE 80.2 mm (the lettering route's fixture) | trims / stitches | 9 / 1,784 | **22 / 2,058** |
| MARINE, letter-to-shape hops · underlay→satin · satin→underlay | trims by cause | 3 · 3 · 1 | 6 · 5 · 7 |
| MARINE, both 09-19 trim levers ON | trims | 8 | 17 |
| ENTHUSIAST 80 mm | `lost_frac` (headline, bar 0.26) | 0.2748 | **0.2565** |
| ENTHUSIAST 80 mm | bare artwork (`rail_edge --bare`) | 6.27% | **7.10%** |
| ENTHUSIAST 80 mm | uncovered ink, colour-free (bar 2%) | 0.90% | 1.76% |
| ENTHUSIAST 80 mm | trims / stitches | 12 / 2,388 | 16 / 2,369 |
| Becker 114 mm, `wide_columns=True`, twigs+stack off | `coverage_max`, guarded / unguarded (warn 6.67) | 5.38 / 7.18 | 7.47 / 7.63 |

Read together: the rails stand less proud of the ink AND cover less of it,
which is the "narrower column" trade the bare guard was built to catch, and
it caught it. Measured the same night, and the mechanism named at first was WRONG: it is not the symmetric-offset rail model's under-reach. Under rail comp ENTHUSIAST's share of rail points more than 0.1 mm inside the art FELL, 19.3% → 14.7%, and its cross density is unchanged (same-rail step p50 0.427 → 0.422 mm). The bare artwork rises at JUNCTIONS on Becker — 1.39% → 3.80% of its satin art on the satin-only instrument, but two thirds of that is one stretch of the C's bowl that the sewn-terms width check now routes to FILL, which `rail_edge.bare_area` counts as bare (with fill counted Becker reads 6.72% → 8.08%); the remainder is sparse crosses at the wordmark's junctions — and along the rails on ENTHUSIAST (mid-rail 2.06% → 4.12%, no fill routing there, cause not yet isolated); and the trims are the artwork skeleton's finer decomposition — MARINE's R goes 5 → 8 strokes and 8 → 14 odd nodes, one letter splits into two components — so the Euler walk jumps more (within-letter jumps 1 → 9 of the 22 trims; underlay-to-column hops 3 → 5; letter-to-letter 3 → 6). `rails_follow_edge`, the built cure for the under-reach, is measured to raise the overshoot headline (0.3289) and the wobble (0.089 → 0.102) and read no-difference on 8 of 9 logos in Kent's eye: not the lever. The trims are the larger surprise against the
09-09 measurement in `config.py`, which read rail comp as FEWER trims on four
logos (ENTHUSIAST 26 → 22, drone 96 → 83): on the lettering route's own
fixture, on today's engine, it is more than twice as many, and the levers
priced on the grown polygon do not buy them back. `tests/test_rail_comp.py`
pins the MARINE numbers as ceilings so a cheaper build lowers them without
touching the test.

**Kent's ruling on the price, 2026-09-29, shown this table with the PR
armed to merge: *"Take the price, let it merge."*** His pick had been made
on the look, which the flip improves in his eye on five logos; the trims
and the bare artwork were not on the page, and he took them knowing. So
the MARINE trims and the ENTHUSIAST bare artwork are an accepted price,
not open defects — and lowering the ceiling `tests/test_rail_comp.py` pins
means the junction tuck and the artwork decomposition named above, not the
rail model. Reverting stays one line plus this table's tests moving back. The
sew-out that would settle the amount is still owed either way.
