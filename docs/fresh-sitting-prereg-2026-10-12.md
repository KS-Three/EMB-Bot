# A fresh blinded eye-pairs sitting: pre-registration - 2026-10-12

MASTER_SCOPE "Waiting on Kent" 42, proposed by
[`docs/density-flow-instrument-2026-10-12.md`](density-flow-instrument-2026-10-12.md)
section 10. **This file is written before any pick exists.** It fixes the
arms, the predicted direction of every instrument, the pair budget, the
analysis and the bar for "evidence", so that the only things left are Kent's:
which logos, whether and when, and the judging. Nothing here runs the sitting,
flips a flag or moves a gate. ROADMAP gate 4 holds throughout: **no raw
agreement figure is computed, printed or quoted** - only Cohen's kappa, its
bootstrap interval and the n it rests on.

The kit is `digitizer/tools/eye_pairs/fresh_sitting.py` (tests:
`digitizer/tests/test_eye_pairs_fresh_sitting.py`). It adds no machinery: the
render, the sealed pairing, the picker and `--reveal` are the existing
`tools/eye_pairs` ones, driven from a manifest, and the scoring is
`pooled.py`'s kappa and bootstrap over `density_flow.py`'s candidates.
The directions in section 2 and the arms in section 1 are also constants in
that module, and `KEY.json` snapshots them at build time, so the record that
they preceded the data is the commit of this file and the key's own timestamp.

## Departures from the instrument doc's proposal (read these first)

1. **The equal-pitch Column redraw has no knob of its own.** The pitch
   confound of the 10-07 page was an engine bug, fixed on `main` at 1782fbea
   the same day (Column rails 0.40-0.46 mm against the satin tier's
   0.42-0.52; DOCTRINE 2026-10-07). So `lettering_columns=True` on today's
   engine already IS the equal-pitch redraw: arm 5 would be arm 3 again.
   The nearest existing thing is an alias (the same designs under a second
   pair id: a test-retest of the Column lane), OFF by default and never
   pooled. What actually separates density from construction is a measured
   gate, not an arm: section 4's pitch gate.
2. **48-60 pairs needs about 13-16 logos, not 8-10.** The doc counted
   arms x logos. An arm that changes nothing on a logo is dropped as identical
   to shipped, and over the 7 in-scope corpus logos the five real arms
   changed 7, 3, 6, 6 and 4 of them (from `pooled-inputs.json`): **3.7 pooled
   pairs per logo, not 5**. Ten logos give about 37 pairs and about 16 that Kent
   decides; 48 needs 13 logos. The kit prints this arithmetic (`check`).
3. **The blind picker has three buttons: left, right, can't tell.** It has no
   "both bad" and no note field, so this sitting cannot ask the "both bad"
   question the doc studied (no level predicted it) and a tie is only
   "can't tell". Adding either changes `server.py`'s contract for every
   sitting and is not done here.
4. **`per_stroke` is a thin arm.** It changed 3 of 7 logos and Kent saw
   "no difference" on all 3. It is kept because it is pre-registered as one of
   the two direction movers and costs 0.4 pair per logo; drop it from the
   manifest if the pair count matters more.

## 1. The arms

Each arm is exactly the `PipelineConfig` kwargs the existing sitting
machinery lays on top of the shipped Studio config; `FRESH_ARMS` is pinned
against `pairs.ARMS` by test. Knob lines are `digitizer_core/config.py` at
`a17d4355` (origin/main, 2026-10-12).

| # | arm id | the doc's name | cfg | knob on main | status |
|---|---|---|---|---|---|
| 1 | `design_angle` | `design_angle` | `design_angle=True` | `config.py:1436`, default False | exists, built OFF |
| 2 | `per_stroke` | the per-stroke rung | `satin_per_stroke=True` | `config.py:3224`, default False | exists, built OFF (wired 2026-09-06) |
| 3 | `lettering_columns` | `lettering_columns` | `lettering_columns=True` | `config.py:2078`, default False | exists, built OFF |
| 4 | `columns_words` | `columns_words` | `lettering_columns=True` + `lettering_words=True` | `config.py:2078`, `:2098`, both default False | exists, both built OFF |
| 5 | `equal_pitch_columns` | equal-pitch Column redraw | **none**: alias of arm 3, `lettering_columns=True` | - | **NO KNOB.** Nearest existing: arm 3 on today's engine, which is already equal-pitch. Not in the default arm list |
| 6 | `split_7mm` | `split_satin_above_mm` 7.0 | `split_satin_above_mm=7.0` | `config.py:3532`, default None (machine 5.0) | exists; 7.0 is the texture sitting's value and a gate-1 number (a candidate, not a ruling) |

The default manifest names arms 1, 2, 3, 4, 6. Arm 5 is available as
`"equal_pitch_columns"` for a test-retest of the Column lane and is reported
beside the pool, not in it.

## 2. Predicted directions, written before any data

### 2a. The five primary instruments

"Better" is the direction the instrument must pick for a positive kappa.
These are the only readings the sitting can confirm. All are read from the
stored design's stitch stream (`density_flow.py`), never by re-digitizing.

| instrument | better is | why | evidence it comes from |
|---|---|---|---|
| `trims_per_1000` | lower | the one reading that has held in every split | #842, #847: +0.55 sides only on 76 pairs; the control |
| `flow_circvar` | lower | "one direction per stroke", "structured pattern" | a lead from one sitting (ties in: +0.26 on the flags sitting, +0.01 on the 30 pairs since); independent of the trims |
| `longest_jump_mm` | lower | the travel he names beside trims | a lead, carried by the flags sitting |
| `long_share` | **lower** | he picked the side with FEWER stitches over 4 mm | the REVERSE of the hypothesis `density_flow.CANDIDATES` still carries (higher); -0.19 [-0.32, -0.06] ties in on 76 pairs, written here as a prediction to be tested, not a fact |
| `thread_density` | higher | his density notes | not supported on 76 pairs (-0.11); kept because the sitting's equal-pitch gate is what finally tests it cleanly |

### 2b. Everything else is descriptive

`thread_density_whole`, `turns_per_100mm`, `runs_per_shape`,
`stitch_median_mm`, `short_share`, `jumps_per_1000`, `back_share_thread`,
`top_support` keep `density_flow.CANDIDATES`' directions and the scorecard
instruments keep `pooled.INSTRUMENTS`'. They are tabled with intervals but
**cannot confirm anything**: nine more candidates x 2 statistics is 18 more
readings and about half a false pass by chance.

### 2c. What each arm should do to the primaries (the manipulation check)

Reported as counts of pairs before any kappa. A blank is "not predicted":
there is no measurement to predict from, and writing one now would be a guess
dressed as a prediction. Sources are the pair tables of
`density-flow-instrument-2026-10-12.md` section 7.

| arm | `flow_circvar` | `longest_jump_mm` | `long_share` | `trims_per_1000` | `thread_density` |
|---|---|---|---|---|---|
| `design_angle` | arm lower (mechanism: one house angle per design) | | arm HIGHER, so the base is preferred (tires 0.037 to 0.072) | no move | |
| `per_stroke` | | | | | |
| `lettering_columns` | arm HIGHER, so the base is preferred | arm longer, base preferred | arm lower, arm preferred | arm lower | about equal, by the pitch gate |
| `columns_words` | arm HIGHER (golden_tee 0.50 to 0.66, fremont 0.47 to 0.61, enthusiast 0.50 to 0.60) | arm longer (enthusiast 24 to 38 mm) | arm lower | arm lower (becker 60 to 29) | about equal, by the pitch gate |
| `split_7mm` | | | arm HIGHER (raw crosses to 7 mm), base preferred | no move | |

The arms were chosen so the five primaries **disagree** on at least two of
them: on the Column arms `flow_circvar` and `longest_jump_mm` pick shipped
while `trims_per_1000` and `long_share` pick the arm; on `design_angle` flow
picks the arm and `long_share` picks shipped. A Kent who follows the trims
picks the Column arms and is indifferent elsewhere; one who follows flow picks
shipped on the Column arms and the arm on `design_angle`; one who follows
short crosses picks the arm on the Column arms and shipped on `split_7mm`.
Those three are what the pairs can tell apart, and the table above is the
reason the arms are these six and not six others.

## 3. Design

- **Logos: 8 minimum (the kit refuses fewer), 13-14 recommended.** Flat
  artwork, not photographs; at least three with lettering the Column arms can
  cut and at least two with thin strokes sitting beside blobs (the only logos
  `per_stroke` moves); a mix of clean files and enlarged small ones (becker's
  class). Preferably ones the scorecard accepts (`KEY.json` records the
  ones it refuses on; the primaries do not need the artwork, only the fidelity
  rows do). **New**: blinding is spent on the nine corpus logos
  (`second-sitting-eleven-flags-2026-09-28`); the kit refuses a byte-identical
  one unless the run is a dry run.
- **Pairs:** one live pair per (logo, arm) the arm changes, expected
  3.7 per logo; plus the existing controls, 4 identical pairs (should read
  "can't tell") and 6 repeats with sides swapped (Kent against himself).
  Controls are not pooled. The pre-registered range is 48-60 live pairs, which
  at 3.7 per logo is 13-16 logos. `KEY.json` flags a build under 48.
- **Blinding:** the sealed map and opaque ids of `tools/eye_pairs/pairs.py`.
  The judge sees `P001_L.jpg`, `P001_R.jpg`, `P001_art.png` and nothing else:
  no arm, no logo name, no seed. Sides are drawn from the manifest's seed;
  `build_pairs` flips exactly half of the live and identical entries, so the
  live pairs alone are balanced to within the number of identical controls
  (4). `KEY.json` is the unblinding key. The build's stderr names logos and
  arms (the render does), so build away from the judge or discard it; the
  picker is what the judge opens.
- **Seed:** fixed in the manifest before the build, e.g. `20261012`.
- **Kent's task:** about 60-70 clicks (left, right, can't tell) at the
  picker, `python -m tools.eye_pairs --serve --out DIR`; then `--reveal` and
  `fresh_sitting score`. Nothing is asked of him about arms.

## 4. The pitch gate: density held, construction changed

A pair whose two sides sew at different rail pitch is a density pair
whatever the arm is called (DOCTRINE 2026-10-07). For every Column-family
arm `fresh_sitting pitch-gate` measures the outer-rail median pitch on the
shipped side and on the arm's side (`tools/satin_pitch.py`, re-digitized once
per logo and arm) and compares them. **Tolerance 0.15 mm** (an instrument
comparability threshold chosen between the corrected gap of up to about 0.1
mm and the 0.3-0.4 mm gap that made the 10-07 page unjudgeable; not a cloth
constant, and not under gate 1). A pair over it is excluded from the pooled
readings and listed; a logo with no lettering to measure gives no gate (and its
pair is identical anyway). `thread_density`'s own reading is therefore taken on
pairs whose density difference is not the pitch.

## 5. Analysis plan

Frame: `before` = shipped, `after` = the arm, whichever side it was on.
Kent's L / R / can't-tell becomes before / after / same (not `both_bad`).

1. **Pool:** live pairs only, minus the retest alias, minus pitch-gate
   failures, minus any logo Kent rules off the page. Controls are reported as
   counts: repeats he answered the same way twice, the identical pairs
   answered "can't tell", the retest arm's same answers.
2. **Manipulation check** (before any kappa): per arm, on how many pairs each
   primary moved to its better side, worse side, or not at all.
3. **Statistics, per instrument:** unweighted kappa on the pairs where Kent
   and the instrument both chose a side (the exit clause read directly), and
   linear-weighted 3-way kappa over every judged pair with "can't tell" as the
   middle category (an instrument is charged for choosing where he saw
   nothing). Percentile bootstrap, B = 10,000, seed 20261011 (`pooled.SEED`),
   over pairs and, separately, over whole logos (pairs from one logo are not
   independent). A reading needs at least 10 pairs and **both intervals
   clear of zero**.
4. **A primary is CONFIRMED only if all of:** (a) both statistics read above
   chance under both intervals; (b) the sign is the one registered in 2a (a
   reading below chance is reported REVERSED and is itself a finding); (c)
   leave-one-logo-out: at most one drop leaves the sides-only kappa at or
   below zero; (d) its picks agree with the trim picks at kappa below +0.5
   (the same test that called `jumps_per_1000` "trims again"). The trim count
   itself, if above chance, is reported as what it is: a price column, known
   since #842.
5. **Multiple readings:** 5 primaries x 2 statistics is 10 readings, about a
   quarter of a false pass by chance (the two statistics are correlated, so
   the true rate sits below that and above one in twenty). Descriptive
   candidates are 18 more readings and are never confirmed.
6. **Ties** are "can't tell" only. He chose a side on 43% of pairs in the
   10-12 pool; at 50 pooled pairs expect about 21 decided. The identical
   controls say how readily he calls a tie.
7. **Not done:** no fitting, no weights, no flag flips, no re-digitizing at
   scoring, and no pooling with the old sittings in the result (a separate,
   labelled table afterwards if wanted).

**What the n buys.** At about 21 decided pairs a sides-only kappa's 95%
interval is roughly +/-0.4 (the 33-pair table of #847 reads +0.35
[+0.00, +0.65]). Only a large effect, around +0.5 or more, can clear zero; a
null at this n does not exclude a moderate one. That is the reason for 13
logos rather than 10.

## 6. What counts as phase-1 exit evidence, and what does not

ROADMAP phase 1 exits when, *on real customer designs, the metric's ranking
agrees with Kent's visual ranking, and nothing he judges better ever scores
worse.*

**Counts as evidence for the exit** (all of):
- at least one primary CONFIRMED by section 5 step 4, and it is not the trim
  count;
- at least 20 pairs where he and that instrument both chose a side, over at
  least 8 logos;
- the second clause: **zero** decided pairs where the instrument picks the side
  he did not. One is "clause 1 only", reported as such.

**Does not count:** a trims-only result (a price, not a fidelity or
construction score); ties-in alone or sides-only alone; a reading below
chance; fewer than 20 decided pairs or fewer than 8 logos; a reading that one
logo carries; pairs from the nine spent logos; a dry run; anything decided
after unblinding. A null result is "no evidence either way", not "disproved".

Even evidence is not an advance: only Kent advances a phase, and gates 3 and
4 hold. Likewise a confirmed primary flips no flag.

## 7. How it runs

```
# Kent's logos and the manifest live in a git-ignored folder:
#   digitizer/eye_pairs_local/{manifest.json, logos/*.png}
cd digitizer
python -m tools.eye_pairs.fresh_sitting check      --manifest eye_pairs_local/manifest.json
python -m tools.eye_pairs.fresh_sitting build      --manifest eye_pairs_local/manifest.json --out eye_pairs_out/fresh-1012
python -m tools.eye_pairs.fresh_sitting pitch-gate --manifest eye_pairs_local/manifest.json --out eye_pairs_out/fresh-1012
python -m tools.eye_pairs --serve  --out eye_pairs_out/fresh-1012     # Kent judges
python -m tools.eye_pairs --reveal --out eye_pairs_out/fresh-1012     # the existing tallies
python -m tools.eye_pairs.fresh_sitting score      --out eye_pairs_out/fresh-1012
```

Manifest (`seed` is required; paths resolve against the manifest's folder):

```
{"tag": "fresh-1012", "seed": 20261012,
 "arms": ["design_angle", "per_stroke", "lettering_columns", "columns_words", "split_7mm"],
 "n_identical": 4, "n_repeat": 6, "logos_dir": "logos",
 "logos": [{"name": "Lg01", "file": "lg01.png", "width_mm": 80, "garment": "left_chest"}]}
```

`build` refuses: a logo outside a git-ignored folder (the folder is ignored by
`.gitignore`; nothing of Kent's art is ever staged), a logo byte-identical to
a corpus one, fewer than 8 logos, a missing or non-integer seed, and an
output directory that already holds picks. Cost: 1 shipped + 5 arm renders
per logo, 30-150 s in earlier sittings (about 500 s each measured today on a loaded
laptop), so 13 logos is one to several hours; the render is resumable. After the sitting, only NUMBERS are committed to
`docs/eye-pairs-<date>/` (as for every earlier sitting); the renders and the
logos stay in the ignored folders.

## 8. What is Kent's

- **The logos** (this is the one real decision; the kit works with any):
  1. *His own new art, kept local.* Best evidence: they are the customer
     designs the exit is about. Never committed (the folder is ignored and the
     kit refuses otherwise); only scoring numbers reach the repo.
  2. *CC0 or public-domain logos, after a licence check.* Copyright and
     trademark are separate questions; a PD-textlogo is not a licence to
     sell embroidery of a mark. Kept local as well. Acceptable if he does not
     want to use clients' art; the licence check is his (or a lawyer's), not
     mine.
  3. *Synthetic logos.* Fast, and not "real customer designs": cannot be exit
     evidence. A pipeline check at best. Not recommended.
- **Go or no-go, and when.** The kit builds and proves itself on spent
  logos; running the sitting spends his attention and, once judged, the
  logos' blinding.
- **How many logos:** 8 is the floor the kit enforces; 13 is what 48 pooled
  pairs needs. At 10 the sitting is a lead, not exit evidence, by its own rule
  (about 16 decided pairs against the 20 it asks).
- **Whether the alias retest arm runs.** Default off.

## 9. Limits that bound this design

- 10 readings, one expected false pass at a quarter, interval about +/-0.4 at
  21 decided pairs: it can confirm a large effect and cannot refute a
  moderate one.
- The change rates behind the pair arithmetic come from 7 logos; a different
  set moves them (the real count is in `KEY.json`).
- The pitch gate's 0.15 mm is a comparability choice, listed as a candidate.
  It needs a re-digitize per Column arm and logo.
- The picker has no "both bad" and no notes: the vocabulary that suggested
  these candidates came from his notes, and this sitting collects none.
- Kent can still tell an arm from its look. Blinding hides names, sides and
  order, not a visibly different construction.
- A dry run proves the plumbing only. Its logos are spent and its picks
  synthetic; nothing it prints is evidence about Kent's eye.
