# The corpus scorecard baseline cannot be re-captured yet — 2026-09-02

**Verdict: do NOT re-capture `testdata/corpus_scorecard_baseline.json` today.**
Not because the drift is small — it is enormous — but because
`tools/corpus_scorecard.py`'s own rule is that "an unattributed mover blocks
the recapture", and most movers are still unattributed. Re-capturing now would
silently bless a fixture whose stitch count more than doubled.

This file records what was measured so the next attempt starts from evidence
rather than from scratch.

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
- **`summit_badge` stitch_count 3839 → 8431**, coverage area 1808 → 4789 mm²,
  satin_steps 995 → 1557. The design more than doubled. MASTER_SCOPE already
  flags this fixture as saturated at F/0 so its *score* says nothing — which is
  exactly why a doubling in its geometry could sit here unnoticed.

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

## And the corpus scores one design TWICE

Found while sweeping the same fixture list for cone colours, and it is one
`md5sum` deep:

```
adb0a79f25ff43a54c77957cc03e1bef  testdata/photo/drone_render.png
adb0a79f25ff43a54c77957cc03e1bef  testdata/photo/logo_drone_thermal_badge.png
```

`corpus_scorecard.FIXTURES` lists **27 files that are 26 distinct images**.
Both names are scored, at both matrix configs, so that one design carries
**twice the weight** of every other in every corpus-wide number — the
baseline included, and every aggregate anyone computes off this list from
here on. It also means the "eight files pulled straight from the jobs Kent
actually digitizes" the FIXTURES comment describes are seven new ones and a
second copy of a synthetic-set fixture that was already there.

Nothing is wrong with the fixture itself; the defect is that it is enrolled
twice. Not fixed here because dropping a name from `FIXTURES` moves the
baseline, and this file's whole subject is not moving the baseline until its
movers are attributed. It belongs in the same recapture: drop one name, and
say in the commit message that the entry count fell for this reason rather
than because a fixture regressed.

## What would unblock a recapture

The method that worked twice above is cheap and should be reused: **run the one
fixture with the one flag flipped**, roughly ten seconds a test, rather than
bisecting 206 merges with a four-minute full capture each time.

1. Confirm the `THREAD_MATCH_POOR` population is all `2d58da8` by spot-checking
   two or three of the fixtures that *improved* (`fur_ramp` 40 → 88,
   `photo_owl_pale` 22 → 46) the same way — declare them and see the baseline
   score return.
2. Attribute the geometry population. `link_segments` is DONE (attribution 3,
   and it was a real defect); `summit_badge`'s doubled stitch count is the
   remaining one that could be hiding another.
3. Drop the duplicate fixture name, so the recapture does not re-enrol one
   design at double weight for another three weeks.
4. Then re-capture, listing every mover and its cause in the commit message,
   as the tool's docstring requires.

Until then the scorecard still works as a **diff** — it is how all of the above
was found. What it cannot currently do is tell a regression from three weeks of
intended change, which is the job it exists for.

*(measured 2026-09-02 on `main` at `0bd9f0f`, one machine so platform numerics
cancel; `tools/corpus_scorecard.py diff`, `digitizer_core.preflight`)*
