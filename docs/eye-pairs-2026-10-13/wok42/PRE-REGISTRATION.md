# WoK 42 blinded sitting: pre-registration, 2026-10-13

MASTER_SCOPE Waiting-on-Kent item 42, proposed by PR #847
(`docs/density-flow-instrument-2026-10-12.md` section 10). **This file is
committed BEFORE anything is rendered or measured.** Its machine-readable twin
is `spec.json` beside it; the kit builder reads that file, so a number here and
there cannot drift apart without a test failing. **Whether and when the
sitting happens is Kent's. This file judges nothing and flips nothing.**

## What was run before this was written

Exactly one thing: an **identity spike**. For each candidate arm and each
candidate logo, the engine was run once and the SHA-256 of the stitch records
was compared with the base's. The only output was "same as base" or
"different" (and the stitch-stream hash). No metric of any candidate, no
picture, no trim count was looked at. It exists so the registered arms are
not inert (the sitting would otherwise spend Kent's time on identical pairs).
Run on Kent's laptop from this worktree, base = `lettering_columns`,
`lettering_columns_skip_blobs` and `lettering_columns_ink_link` ON. Note the
spike had no photo-prep venv, which only `mfab` (Stage 0: `photo_scene`)
would read; the kit renders with it linked in and the manipulation check
below re-reads identity there.

D = the arm's design differs from base; . = byte-identical.

| arm | mfab | toat | fritsch | board80 | whitebg | thin_script |
|---|---|---|---|---|---|---|
| `design_angle` | D | D | . | . | D | D |
| `polygon_axis` (`satin_polygon_axis="artwork"`) | D | D | . | . | D | D |
| `split_7mm` | D | D | D | D | . | . |
| `fill_row_030` | D | . | D | . | D | . |
| `underlay_on_column` | D | D | . | . | D | not run |
| `lane_off` | D | D | D | D | . | . |
| *reserves:* `words` | D | D | . | . | . | . |
| `per_stroke` | D | . | . | . | . | . |
| `hop_under` | D | . | . | . | . | . |
| `exit_next_off` | D | D | D | D | . | not run |
| inert on every logo run: `mid_entry`, `bridge_off` (fill_bridge_cut), `satin_walk_cursor_reach_mm`, `satin_house_fourfold` | . | . | . | . | . | . (not run for the last two) |

(`travel_off`, `slab_off`, `tip_corner`, `junction_sq`, `stroke_nearest`,
`small_print` were also spiked and are not used.) Stage 0 routes: mfab
`photo_scene`, toat/fritsch/board80 `gradient`, whitebg/thin_script `flat`.

## The base

Today's defaults, with Kent's 2026-10-13 ruling applied:
`lettering_columns` ON (default since 2026-10-12), plus
`lettering_columns_skip_blobs` and `lettering_columns_ink_link` ON. The kit
passes all three explicitly (`--base`), so the same engine renders whether or
not those two flips have reached `main` when it is built. Every arm is
**one change on top of that base**; the BEFORE/AFTER names never appear to
Kent, only LEFT and RIGHT, and which is which is randomised.

## The logos: six qualify, short of the eight to ten asked for

Criteria, all checked by `tools.eye_pairs.sitting` (`check`): the image is
already committed here or drawn by a committed generator; it is not one of the
nine judged logos (`becker bridge drone enthusiast fremont gaulke golden_tee
screenshot tires`, plus `thermal`, byte-equal to drone) and not byte-equal to
one; it is flat art; and at least three of the six arms change it. **No client
art is added by this work**; the two client logos below were committed in PR
#556 and are already public.

| logo | what | provenance |
|---|---|---|
| `mfab` | M-FAB AND WELDING LLC, outlined black wordmark, 418 x 159 | `testdata/art/logo_mfab_hat.png`, vendor-preview crop, PR #556 |
| `toat` | To a T Machine LLC, script wordmark in a hexagon, 372 x 273 | `testdata/art/logo_toat_machine.png`, PR #556 |
| `fritsch` | the word "Fritsch", serif, 900 x 260 | generator `tools/make_hard_cases.py::serif_text` |
| `board80` | the block word "BOARD 80" with counters, 1500 x 260 | generator `tools/small_print.py::synthetic_text` |
| `whitebg` | five-colour flat logo (circle, ring, bar, two blocks) | `testdata/logo_whitebg.png`, `tools/make_test_logo.py`, scorecard FIXTURES |
| `thin_script` | script loops under a flourish (a fixture more than a logo) | `testdata/synthetic/thin_script.png`, PR #848 |

**Only two are customer art, and only four are flat-routed or wordmark
fixtures drawn by us.** Three more files qualify only as the SAME designs
again (`mfab_lc`, `toat_beanie`) or as the logo Kent already judged and
excluded (`golke_roofing`, the clean file of gaulke); they are listed in
`spec.json` as reserves and are NOT in the kit. Everything else in the repo
was checked and ruled out in `spec.json`'s `not_qualified` (gradient art,
photographs, ramps, font previews, one-stroke and block fixtures no arm
moves). Sourcing more flat logos with lettering is Kent's; the kit takes any
number of them from one spec edit (`logos[]` with provenance), and refuses a
logo that is judged, byte-equal to a judged one, or has no provenance.

**What six logos means for the target.** Six arms over six logos is at most 36
pairs, and the identity table above gives **22 live pairs** (4 + 4 + 4 + 3 + 3
+ 4, `thin_script` not run for `underlay_on_column`) plus 4 identical-pair and
4 repeat controls: **about 30 pairs, not 48 to 60.** At the 43% rate he chose
a side on #847's pairs, about 9 are decided, which puts a sides-only kappa
interval near plus or minus 0.5. **This sitting alone can detect only a large
effect and can license nothing; its job is to add its pairs to the 76
measured ones** (`pooled`/`density_flow`), and to say, arm by arm, whether the
leads can be tested by these flags at all.

## The six arms

One variable each. "moves" and "holds" are the mechanism-based expectations the
manipulation check enforces (below). `expected_pick` is the side the lead
under test implies for Kent's eye; where no lead applies it is `tie`.

| arm | flags on the base | variable | moves | holds | expected pick |
|---|---|---|---|---|---|
| `design_angle` | `design_angle=True` | stitch direction across shapes | none required (see below) | trims, long_share, density | **tie** |
| `polygon_axis` | `satin_polygon_axis="artwork"` | stitch direction within satin | none required | trims, long_share, density | **tie** |
| `split_7mm` | `split_satin_above_mm=7.0` | stitch length | `long_share` up | trims, density | **base** (he picks fewer long stitches) |
| `fill_row_030` | `fill_row_mm=0.30` | thread density only | `thread_density_whole` down | trims, flow, long_share | **base** (denser) |
| `underlay_on_column` | `satin_underlay_on_column=True` | trims only | `trims_per_1000` down | flow, long_share | **arm** (fewer trims) |
| `lane_off` | `lettering_columns=False` | construction, pitch-matched | `trims_per_1000` up | none (the control) | **base** |

How the pairs separate the variables:

- **Flow without trims:** `design_angle` and `polygon_axis` change direction and
  are expected to leave trims, length and density alone. **A caveat written
  down now, not found later:** `flow_circvar` is the spread of direction
  WITHIN a shape, and `design_angle` targets direction ACROSS shapes, so these
  two arms are registered with no required movement of it; whether it moves is
  a measurement. If `flow_circvar` moves on fewer than half the logos where
  they differ, this sitting cannot test the flow lead with these flags, and the
  report says so instead of reading it off `lane_off` alone.
- **Trims without flow:** `underlay_on_column` (built to remove the lift between
  a stroke's underlay and its column; documented trims down, direction
  untouched).
- **Length alone:** `split_7mm`, the direct test of the reversed `long_share`
  lead.
- **Density without construction:** `fill_row_030` doubles the fill row pitch
  and changes nothing else. It reaches fills only (mfab, fritsch, whitebg); no
  satin-density knob exists in the config and none is added here.
- **Construction with density held:** `lane_off`. The Column lane sewed at half
  the satin pitch until the 2026-10-07 correction (`tools/satin_pitch.py`);
  today both sides lay 0.40 mm. That claim is checked, not assumed: a pair
  whose whole-design `thread_density` differs by more than 10% is flagged
  `density_matched = false` in the analysis and read as construction plus
  density.

The base-ON `lettering_columns` is why PR #847's pair (`lettering_columns`,
`columns_words`) is gone: `lane_off` is its mirror and `words` is the first
reserve.

## The manipulation check, and the one replacement rule

Before Kent sees a picture, the kit measures each arm against the base on every
logo it changes, from the designs alone (no pick exists). An arm passes when,
on at least 2 of those logos and at least half of them, every `moves` metric
moves the stated way by its threshold (`trims_per_1000` 0.5, `flow_circvar`
0.02, `long_share` 0.02 absolute; `thread_density_whole` 5% relative) and every
`holds` metric moves by less than it (Amendment 1). A failing arm, or one identical
to base on 4 or more of the 6 logos, is replaced once by the first reserve of
its stratum (`spec.json`: `words` for construction; `exit_next_off`, then
`hop_under` for trims; `per_stroke` for flow). The swap and the reason go into
the manifest. The table of deltas is NOT committed until the sitting is over: a
reader who sees "this arm adds 20% stitches" can pick it out of the six pairs
of one logo. Only pass/fail per arm is reported.

## What is hidden, and what is committed

- Sides: exactly half the live pairs put the base on the left, shuffled under
  `seed` 20261013 (`pairs.build_pairs`; LEFT was always shipped before).
- Arm names: the picker serves opaque ids (`P001_L.jpg`); the sealed key
  (`arms.json`) stays in the render directory and is **committed only after the
  sitting**, with `picks.jsonl`, as every earlier sitting's was. What is
  committed now is the manifest, which carries the sealed map's SHA-256 (a
  commitment: the key cannot change after the fact), the design hashes, the
  counts and the exact commands.
- Do not open `arms.json`, `features.json`, `designs/` or `manipulation.json`
  in the render directory before `--reveal`.

## Analysis plan, fixed now

**Population.** Live pairs only. The identical and repeat pairs are controls.

**Kent's pick** maps LEFT / RIGHT / tie onto `before` / `after` / `same` by the
side shown, so the statistic never sees which side was the arm. (This picker
has no "both bad"; a tie is a tie, and the both-bad analysis of #847 is not
repeated.)

**Statistic.** Cohen's kappa between Kent's pick and each lead's pick (the lower
or higher side by the registered direction), in the two forms `pooled.py`
already uses: **sides only** (2 x 2, pairs where both chose a side) and **ties
in** (3 x 3, linear-weighted). **95% percentile bootstrap, 10,000
resamples, seed 20261011, over pairs AND over designs** (the `design` key; a
logo's pairs are not independent). A reading needs **both intervals clear of
zero and at least 10 pairs where Kent chose a side**; otherwise the report says
"no evidence either way" or "n too small". **No raw agreement figure is
computed or printed** (ROADMAP gate 4).

**Confirmatory leads (four), directions written now:** `flow_circvar` lower,
`long_share` LOWER (the reverse of #847's original hypothesis, as its data
suggest), `thread_density` higher, and `trims_per_1000` lower, the **control**:
the one instrument that cleared chance in #842 and #847, so **if it does not
replicate on these pairs, nothing else in the sitting is read.** Secondary,
reported and not read as findings: `longest_jump_mm`, `jumps_per_1000`,
`turns_per_100mm`. Everything else `density_flow` computes is printed under
"exploratory". Four leads times two statistics is eight readings: about 0.4
false "above chance" expected by chance alone, and none is corrected for.

**The separation reading.** Each lead is also read on the pairs whose
`trims_per_1000` differs by less than 0.5 between sides (trims held) against
those that differ by more. A flow lead that clears chance only where trims
moved is the trims lead again; that is the point of the arms.

**Does this pre-registration predict his eye?** Kappa (ties in, 3 x 3) between
each pair's `expected_pick` (table above, mapped to the side shown) and Kent's
pick, with the same two intervals. It is the honest scorecard of this document.

**Controls, reported as counts of his own answers and nothing else:** how many
identical pairs he called a tie, and how many of the repeats he answered the
same way twice, each with its n. Used only to flag a side habit or a noisy
sitting.

**What it does not do.** It flips no flag and moves no gate; no phase is
advanced from it (Kent's alone). Its pairs append to `pooled-inputs` as a
new sitting so the 115-pair instrument can be re-run at a larger n. Reading
before every pair is picked is refused (`--reveal` and `analyse` both).

## Honest limits, written before the data

- Thirty pairs on six logos, two of them customer art and two of them
  fixtures; the pooled run, not this sitting, is where an interval could
  narrow.
- `flow_circvar` and `design_angle` target different things (above).
- `fill_row_030` reaches fills only and `underlay_on_column` the non-lane
  satin tier, so neither moves `fritsch` or `board80` (all letters in the
  lane) as much as `mfab`.
- mfab is photo-class (Stage 0 `photo_scene`) and 5.2 px/mm; with the photo-prep
  venv linked in, as the product ships it, its renders carry a cutout that
  another machine's would not.
- The 0.30 mm fill row, the 7.0 mm split and the pre-flip lettering tier are
  probes of an eye, **candidates, never settings** (ROADMAP gate 1).

## Amendment 1, 2026-10-13, before anything was rendered

Two numbers in the manipulation check were set without a scale to hold them
against, and are corrected here. Nothing was rendered or measured between the
first commit and this one; the scale comes from PUBLISHED price tables
(`docs/eye-pairs-2026-10-07` and `-10-08`): the base sews about 5 to 7 trims
per 1000 stitches, so a threshold of 1.0 asks a trims arm for a 15 to 20%
change, while `underlay_on_column`'s documented effect is 3% over nine logos
(478 to 465 trims). Changed: **`trims_per_1000` threshold 1.0 to 0.5** (about
a tenth of the base rate), and a `holds` metric must move by **less than its
threshold** instead of less than half of it (half of 0.5 trims per 1000 is two
trims on a 9,000-stitch design, inside the noise of any arm that reorders
anything). No arm, flag, direction, expected pick, logo or statistic changed.

## Amendment 2, 2026-10-13, before any pick exists

The kit builder ran the manipulation check once, on all six arms, after
Amendment 1. The rule above said nothing about two cases it then met, and
this fixes them in words before a picture is shown: **a reserve that fails
the check too, and a failing arm whose stratum has no reserve (`density` has
none), stay in the sitting, flagged `passes: false` in the manifest.** Nothing
is swapped a second time in search of a pass, and nothing is dropped after
looking. What changes is the reading: the analysis now reports every lead on
all live pairs AND, beside it, on the pairs of arms that passed the check
alone (`isolating_only`), so a lead is never read off pairs whose arm did not
isolate its variable without saying so. No arm, flag, direction, expected
pick, logo or statistic was changed. No pick exists and Kent has seen no
picture; the builder did read the check's per-arm, per-logo deltas to see why
arms failed, which is what the check is for and not something a pick could have
touched. The manifest reports pass or fail per arm and nothing finer; the table
of deltas stays unpublished until the sitting is over.
