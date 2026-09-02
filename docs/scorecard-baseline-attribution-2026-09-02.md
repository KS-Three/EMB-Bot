# Attributing the corpus scorecard baseline — 2026-09-02

**Verdict, revised twice as the evidence came in: every mover is now
attributed, and the recapture is unblocked.** The first draft of this file said "do NOT re-capture, most
movers are unattributed" and singled out two that "could be hiding a real
defect". Both have since been run down, and neither is a reason to hold:

- `link_segments` 0 → 4 was a **defect in the instrument** — a jump read as
  thread. Fixed (attribution 3).
- `summit_badge` 3839 → 8431 was a **defect being fixed** — the baseline caught
  the design sewn without its badge body (attribution 4).

And the baseline itself was proved sound: re-scored against the engine at its
own commit it reproduces **38 of 38 rows exactly**, so every mover is real
engine change and none of it is corruption or platform noise.

What still stands between here and a recapture is ordinary and listed at the
bottom: a spot-check of the `THREAD_MATCH_POOR` population, a handful of
non-score-moving `color_changes`/`satin_steps` deltas, and one duplicate
fixture name to drop. None of it is a mystery any more.

**Read the corrections in "The state of the ruler" first** — this file's own
opening numbers were wrong for a reason worth knowing about.

## The state of the ruler

| | |
|---|---|
| Baseline last written | **2026-08-12** (`4f7d80f3`) |
| Merges since | **206** (95 commits touching `digitizer_core/`) |
| Entries that moved | **30 of 38** |
| Score changes | **17** |
| `captured_at_commit` / `captured_date` | **absent** |

**Corrected 2026-09-02, and the correction is the lesson.** This table first
read "2026-08-24 (`6b1ccdf`), 73 merges". Both numbers came from a SHALLOW
clone — a cloud session's default. `6b1ccdf` is that clone's graft root, and a
graft root answers `git log -- <path>` as the thing that last touched every
file in the tree, wearing the subject line of a real merge commit while
`%p` shows it has no parents. So the wrong commit looked like the right one,
and the two headline numbers were both understated by roughly a factor of
three. `git fetch --unshallow` gives 1390 commits where the graft gave 219.

This is CLAUDE.md gotcha 8 wearing a different face: there the stale clone
says a file NEVER existed, here it names the wrong commit as the file's author
and every conclusion drawn from that date inherits the error. **Unshallow
before dating anything.** One session already burned an afternoon on the first
face of this; this entry is the second.

The absent stamp is NOT a defect, and an earlier draft of this file called it
one. `capture()` at `4f7d80f3` did not write `captured_at_commit` or
`captured_date` — grep the file at that commit, the fields are not there. The
stamping came later. The artefact is simply older than the feature; any
recapture picks it up for free.

## What moved

Movement is in two distinct populations, and they need different treatment.

**Findings and scores — one likely cause, verified on the worst case.**
Almost every score change names `THREAD_MATCH_POOR` appearing or resolving.

**Geometry metrics — cause unknown.** `same_hole_fraction` (22 entries),
`trims_per_1000` (21), `stitch_count` (20), `coverage_max` (19),
`color_changes` (18).

## Attribution 1 — `region_blobs` 40 → 0 is a RULER change, not a regression

The scariest-looking mover in the diff: a 40-point drop with a *block*-severity
`THREAD_MATCH_POOR` appearing. It is benign.

```
is_photographic=None   score=  0  grade=F  worst_dE=10.7  THREAD_MATCH_POOR x4
is_photographic=True   score= 40  grade=D  worst_dE=10.7  THREAD_MATCH_POOR x0
```

Declaring the fixture photographic restores **exactly** the baseline score of
40 and removes all four findings — while `thread_worst_delta_e` stays
**identical at 10.7** either way. The engine's thread choice never changed;
only the yardstick applied to it did.

Cause: `2d58da8` (PR #245, "photo machinery: declare it, and ask the question in
one place"), which gates preflight's photo yardstick on `cfg.is_photographic`
instead of on a class name. Its own commit message describes the intended
effect on the other side — `owl_kent.jpg` had "twelve THREAD_MATCH_POOR
findings that were the wrong ruler rather than real mismatches". The flip side,
visible here, is that undeclared content is now graded on the strict tatami
ruler. That is the change working as designed.

Ruled out first, both by measurement, both null:

| hypothesis | result |
|---|---|
| `shade_palette_bind` (defect 9's fix) | identical with it on or off — score 0, ΔE 10.7 both ways |
| the check itself changed | only one commit touched `preflight.py` in the window, and it is `2d58da8` |

**This is also defect 15 seen from the other side.** The dashboard records that
an undeclared photograph loses the palette bind and depth sequencing; here an
undeclared fixture loses the right *grading ruler* too, on a metric nobody was
watching. Same root: the declaration is unreachable and nothing infers it.

## Attribution 2 — the geometry movers are NOT the obvious suspects

`enthusiast_logo @ 80mm/hat_front`, against a baseline of
`trims/1k 8.1 · satin_steps 1416 · link_segments 0`:

```
default              trims/1k=7.3   satin_steps=1284   link_segments=4   stitches=2477
borders_last=False   trims/1k=6.9   satin_steps=1280   link_segments=4   stitches=2469
```

Turning `borders_last` off moves trims **further** from the baseline, not back
to it, and leaves `satin_steps` and `link_segments` where they are. So the
biggest recent sew-order change does not account for this fixture's drift.

Two things in that table deserve their own look:

- **`link_segments` 0 → 4 — ATTRIBUTED, and it was a defect in the instrument.
  Fixed here.** See "Attribution 3" below; this bullet is kept only so the
  trail from "a number moved" to "an instrument was lying" stays readable.
- **`summit_badge` stitch_count 3839 → 8431 — ATTRIBUTED, and it is a FIX.**
  See "Attribution 4" below. The design did not grow; the baseline caught it
  sewn with a piece missing.

Other unexplained geometry movement, listed so the next pass has targets:

| fixture | movement |
|---|---|
| `drone_render` | `color_changes` 23 → 18 (plausibly the re-snap rehome, defect 16's fix — untested) |
| `gradient_ramp_linear` / `_radial` | `color_changes` 1 → 3 on both |
| `repro_gradient_white_icon` | `color_changes` 5 → 2 |
| `enthusiast_logo` | `satin_steps` 1416 → 1284 |

## Attribution 3 — `link_segments` 0 → 4 was a false positive, now fixed

The one mover that could have been hiding a real defect, and it was hiding a
defect in the *ruler* instead. `_link_findings`' own docstring promises that
"a chain-off plan reports zero link thread"; `chain_links` ships default-OFF;
this fixture reported four link segments and 4.2 mm of link thread.

**Cause: a jump is not thread, and the classifier forgot it for travel runs.**
A shape routinely OPENS with its own travel run, and stage 7 marks that run
`jump` because the machine lifts to reach it (`machine.TINY_STITCH_MM`, 0.5 mm).
On this fixture:

```
r22  satin     S6959709e  jump=False       <- last content of the first shape
r23  travel    Scd87e08f  jump=True        <- SECOND shape's own opening routing
r24  underlay  Scd87e08f  jump=False
```

The needle is UP between r22 and r23, so no thread goes from `S6959709e` to
`Scd87e08f` at all. But `_transport_and_content` compared against the last
CONTENT it had seen rather than against where the needle was standing, so
r23's 3.51 mm and the 0.24 mm step out of it into r24 were both scored as
between-shape transport. The connect branch already encoded the rule
(`not run.jump`); the travel branch did not — so the fix is one rule made
consistent with itself, not a threshold loosened. It tracks the shape the
needle STANDS in (`at_shape`, cleared on every lift), and can only ever
reclassify thread the needle was not down for.

Measured over the whole scorecard corpus, chaining off, old vs new:

| | old | new |
|---|---|---|
| runs reporting any link | 12 of 54 | 10 of 54 |
| total link thread | 39.8 mm | 9.0 mm |
| worst single run | `logo_hotel_fremont @left_chest` 7.2 mm | `photo_subject_stub @left_chest` 2.9 mm |

**30.8 mm of the 39.8 was thread the needle was not down for.** No fixture
blocked before or after — `link_uncovered_mm` is 0.0 everywhere, so nothing
sat on bare fabric and this was never a safety breach. What it was is an
instrument guarding a gate-3 flag reading 4.2 mm where its own contract says
0.0, which is how a real breach later gets waved past.

`tests/test_preflight.py` now pins all three halves: the jumped-open shape
reports zero, a genuine link that merely *starts* after a jump still blocks,
and on the real fixture a chain-off plan can never reach the float ceiling.
The first and third fail against the old classifier (4.2 mm, verified by
reverting).

### The 9.0 mm that remains is a SECOND provenance bug — measured, NOT fixed

`photo_subject_stub @left_chest`, the new worst case, is one travel run:

```
r64  fill    Sad8d0cf6-shade0
r65  travel  Sad8d0cf6        <- 2.88 mm, both segments scored as transport
r66  border  Sad8d0cf6
```

That is one region's own routing between its shade-0 fill and its own border.
It reads as between-shape only because the layered streamline tier derives its
per-shade ids as `f"{region.shape_id}-shade{i}"`
(`stage6_streamline.py:875`, the single construction site) and the classifier
compares ids as opaque strings.

**Deliberately not fixed in the same change.** The jump fix has an airtight
argument — the needle was up, so no thread exists. Normalising the shade
suffix does not: it needs an answer to whether stage 6/7 treat shade layers of
one region as one shape for the trim rule, which is the premise the docstring
leans on when it waves in-shape chained links through. Getting that wrong
hides needle-down thread, which is the exact failure gate 3 exists for. It is
worth a session; it is not worth a guess.

## The baseline REPRODUCES — 38 of 38, so every mover is real

Re-scored against the engine at its own commit (`4f7d80f3`, the tree extracted
with `git archive` and run with this container's venv), the shipped baseline
comes back **exactly**:

```
of 38 baseline rows re-scored on the 4f7d80f3 engine
agree     : 38
DISAGREE  : 0
errored   : 0
```

Three things fall out of that, and each was an open question:

1. **The baseline is a valid ruler**, not a corrupted or hand-edited artefact.
   Every one of the 30 movers is genuine engine change over 206 merges — which
   is what makes attributing them worth the work rather than a wild goose
   chase.
2. **No metric here is platform-sensitive.** The photo lane reproduced bit-for-bit
   on a Linux container against a three-week-old commit. That is NOT true of
   the three goldens CI deselects (`test_pushcomp`,
   `test_flat_lane_byte_identical`, `test_stage2_photo_segment`), so it could
   not be assumed. A recapture run in a cloud session is comparable to one on
   Kent's box for these numbers.
3. **The method is cheap and repeatable.** `git archive <commit> digitizer |
   tar -x` into a throwaway directory, then run it with the existing venv. No
   worktree, no checkout, the working tree never touched. That is what makes
   the bisect below a five-minute job instead of an afternoon.

## Attribution 4 — `summit_badge` did not grow; it was BROKEN when captured

Bisected over the 95 commits touching `digitizer_core/` in the real window,
binary search on the stitch count (~10 probes at ~30s):

```
[ 0] 21a415c0  2026-08-12  ->  3843     <- the baseline's own reading
[ 2] e460ceba  2026-08-12  ->  3843
[ 3] d2184fa2  2026-08-13  ->  8263     <- the jump, one commit later
[47] 21bb0d65  2026-08-23  ->  8412
[94] 78d9f5d8  2026-09-01  ->  8433
```

`d2184fa2` is *"fix(digitizer): stage 4 was discarding whole regions and
calling them 'details'"*, and it names this fixture in its own commit message:

> On `summit_badge.png` it is one 2,787 mm² drop: **the whole badge body**.

`approxPolyDP` can make a traced boundary self-intersect; `make_valid` repairs
it, but returns a bare `MultiPolygon` for a simple figure-eight and a
`GeometryCollection` when the shape also sheds a dangling edge — polygons one
level deeper. Stage 4 scanned only the top level, read "no polygons at all",
and dropped the region entire.

So the baseline's row is a snapshot of `summit_badge` **sewn without its badge
body**, captured the day before the fix landed. 3839 → 8263 is that body coming
back; the remaining +2% over 90 further commits is ordinary drift. The
coverage-area move (1808 → 4789 mm², +2,981) is the 2,787 mm² body plus its
knock-on.

**This retires the entry's last real worry.** MASTER_SCOPE flags this fixture
as saturated at F/0, so its *score* says nothing and a geometry doubling could
sit unnoticed — which is why it was singled out for a look. Looked at, it is
the corpus doing its job: recording a defect being fixed. Nothing here blocks
a recapture.

## And the corpus scores one design TWICE — already known since 2026-08-23

```
adb0a79f25ff43a54c77957cc03e1bef  testdata/photo/drone_render.png
adb0a79f25ff43a54c77957cc03e1bef  testdata/photo/logo_drone_thermal_badge.png
```

`corpus_scorecard.FIXTURES` lists **27 files that are 26 distinct images**, both
scored at both matrix configs, so that one design carries twice the weight of
every other in every corpus-wide number — the baseline included.

**This was found on 2026-08-23, not here.** An earlier draft of this file
reported it as a discovery; it is a rediscovery, and the difference matters
because the earlier find already did the harder half. `tools/pro_parity/
blockcensus.py` documents it in its module docstring — *"the scorecard's
FIXTURES carries both, so its aggregates double-count one image"* — includes
the image once, and, better than a comment, **verifies the duplication at
runtime** (`_dup_note`), printing a DIVERGED warning if the two files ever
stop matching so nobody trusts a stale note. `docs/superpowers/plans/
2026-08-24-option-c-is-inert.md` uses it too, to discount an apparent
corroboration: *"`drone_render.png` and `logo_drone_thermal_badge.png`
reporting identical 19/11 ... is not two independent confirmations."*

So the defect is not that nobody noticed. It is that the notice lived in the
tool that worked around it and in one plan doc, while `FIXTURES` itself and
MASTER_SCOPE carried the uncorrected claim — and the scorecard, the thing whose
aggregates are actually skewed, still enrols both names. Two sessions have now
paid to rediscover it.

**The fix is to drop the name from `FIXTURES`**, which moves the baseline, so
it belongs in the recapture rather than before it — listed below. `blockcensus`
needs no change: it already does the right thing.

## What would unblock a recapture

The method that worked twice above is cheap and should be reused: **run the one
fixture with the one flag flipped**, roughly ten seconds a test, rather than
bisecting 206 merges with a four-minute full capture each time.

1. ~~Confirm the `THREAD_MATCH_POOR` population is all `2d58da8`.~~ **DONE —
   it is, in both directions.** Measured on the three fixtures that moved most:

   | fixture | stage 0 verdict | photo ruler? | score | `worst_dE` then/now |
   |---|---|---|---|---|
   | `fur_ramp` | `CLASSIFIED_PHOTO_SCENE` | yes, undeclared | 40 → 88 | 9.3 / **9.3** |
   | `photo_owl_pale` | `CLASSIFIED_PHOTO_SCENE` | yes, undeclared | 22 → 46 | 6.9 / **6.9** |
   | `region_blobs` | `CLASSIFIED_GRADIENT` | no | 40 → 0 | 9.1 / 10.7 |

   The two improvers carry an **identical** `thread_worst_delta_e` across the
   change: the engine's thread choice never moved, only the yardstick applied
   to it. Declaring them `is_photographic=True` is a NO-OP — they already
   classify photo, so `_is_photo_class` returns True without a declaration —
   and that no-op is easy to misread as the hypothesis failing. It is the
   hypothesis holding. `region_blobs` is the mirror: classified GRADIENT, so it
   lost the lenient ruler and needs an explicit declaration to get it back,
   which restores exactly 40.
2. Attribute the geometry population. Both singled-out movers are DONE:
   `link_segments` was a real defect in the instrument (attribution 3), and
   `summit_badge` was a real defect being FIXED (attribution 4). Of the small
   remainder, the gradient ramps are also done — **`gradient_ramp_linear`
   `color_changes` 1 → 3 bisects to `b37cd808` (2026-08-19), "stage 7 sews
   blend shades in their snapped threads"**, which is the shade-bind work
   landing: a ramp that used to collapse to one thread now sews the three its
   per-shade snap had already computed and stage 7 was throwing away. Intended,
   and `gradient_ramp_radial` moves identically.

   **`drone_render` `color_changes` 23 → 16 bisects to `da7fc806`** (#293,
   2026-08-28, "hoist a revisited spool beside itself when geometry allows"),
   which takes it 23 → 19; #309's duplicate-cone folding and #311's default
   flip take the remaining 19 → 16. That is the defect-16 work stream doing
   exactly what it exists for — one spool revisited across other colours,
   hoisted back beside itself — so every step of this mover is an intended
   reduction in stops. (An earlier draft said 23 → 18; that was measured
   before #309 and #311 landed.)

   **`enthusiast_logo` `satin_steps` 1416 → 1278 is `070a1136`** (2026-08-14,
   "never build a column on a corner fork"), and the revert/reapply pair around
   it confirms the attribution better than any bisect could:

   ```
   [5] c91ab601  ->  1416   <- the baseline's own value
   [6] 3a1f6735  ->  1459
   [7] 070a1136  ->  1278   <- the corner-fork fix
   [8] a6435f2a  ->  1416   <- Revert "DO NOT MERGE — pro-parity engine work"
   [9] 83683544  ->  1278   <- Reapply
   ```

   Back to exactly 1416 on the revert, down again on the reapply. The fix stops
   building satin columns on corner forks — the medial axis runs a branch into
   a bold corner's point, and a zigzag across that wedge IS the starburst Kent
   saw on `becker_lc_large`'s "E" and "A". Fewer satin steps because it stops
   sewing spurious wedges. A quality fix; the remaining 1278 → 1284 over 85
   further commits is drift.

   **A trap worth recording:** the first attempt bisected on a hand-rolled
   proxy (count points on satin runs) instead of preflight's own `satin_steps`.
   The proxy reads 1448 where preflight reads 1416, so the equality test never
   matched, the search collapsed to the wrong end of the window, and it named a
   commit with confidence. Bisect on the METRIC THE BASELINE STORES, not on
   something that correlates with it.
3. Drop the duplicate fixture name, so the recapture does not re-enrol one
   design at double weight for another three weeks.
4. Then re-capture, listing every mover and its cause in the commit message,
   as the tool's docstring requires.

Until then the scorecard still works as a **diff** — it is how all of the above
was found. What it cannot currently do is tell a regression from three weeks of
intended change, which is the job it exists for.

*(measured 2026-09-02 across `main` at `0bd9f0f` through `78d9f5d8`, one Linux
container; `tools/corpus_scorecard.py diff`, `digitizer_core.preflight`,
`tools/sequence_census.py`, and `git archive`-extracted trees at `4f7d80f3` and
95 commits after it. Platform numerics do not cancel here — they were shown not
to apply: all 38 rows reproduce on this machine.)*
