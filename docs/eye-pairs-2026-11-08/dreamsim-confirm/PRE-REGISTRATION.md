# DreamSim confirmation sitting (`dreamsim-confirm-1108`): pre-registration, 2026-11-08

**Committed BEFORE anything is rendered or scored.** Its twin is `spec.json`
beside it; the kit builder reads the spec, and a test fails if a name here and
there drift apart. **When Kent sits it is his. This sitting judges nothing and
flips nothing:** no flag, route or default moves on it, and no phase marker
moves. What it can license is a proposal to Kent.

## Purpose

Confirm, or fail to confirm, the DreamSim yardstick against Kent's eye. The
first reading (`docs/yardstick-perceptual-prereg-2026-11-08.md`, result in
`docs/yardstick-perceptual-result-2026-11-08.md`) scored DreamSim on pairs
that were labelled for other reasons. This sitting builds pairs FOR the
instrument: every logo is a pro-paired job, drawn at the pro's own garment and
width, and every arm is chosen for a difference that shows in a monochrome
render, so Kent decides a side often and the instrument is scored on decided
pairs.

## Not blind to prior judging, on purpose

The blinding guard of `tools/eye_pairs/sitting.py` refuses a logo Kent has
judged. This sitting lifts it for `pro_paired_job` logos drawn from a
`pro_baseline.JOBS` row, by the opt-in `rejudge_pro_jobs` key in `spec.json`,
and for nothing else (file and generator logos stay guarded). Kent's words,
2026-11-08: "All 23 pro jobs (Recommended)". The reason, as written in the spec:
every pro-paired artwork has been judged, and the sitting's purpose is to
confirm the DreamSim instrument against Kent's eye, which needs pro-paired
designs, not blindness to the logo. `prepare` records the waiver in the
manifest (`rejudge_pro_jobs`, `blind_to_prior_judging: false`). What stays
blind is the PAIR: which side is the base and which the arm is shuffled under
seed 20261108 and sealed, as in every earlier sitting.

## The base

Today's `main` defaults with no override (`base_flags` is empty). Every arm
turns ONE flag away from its default: three that are OFF today go ON, three
that are ON today go OFF. Kent sees LEFT and RIGHT; which is the base is
shuffled with the arm on the left in half the live pairs. `n_identical` 4 and
`n_repeat` 4 are controls and enter no statistic.

## The logos: every pro job, population A, no population B

Twenty-two rows, not the twenty-three Kent's ruling names: `pro_baseline.JOBS`
holds 22 jobs on the commit this was cut from (`1df61ab3`), and the spec takes
all of them. Every logo is kind `pro_paired_job`, source `job`, pinned by
`sha256_16`, drawn at that row's garment and width and read beside the pro's
DST. The artwork is resolved through the job; none is copied into the
repository (proseal's lives under gitignored `scratch_kent/`). One artwork at
several jobs is several logos for pairing and ONE where the analysis says
"over designs".

| logo | design (cluster) |
|---|---|
| `becker_hat_large` | `becker` |
| `becker_lc_large` | `becker` |
| `becker_hat_small` | `becker` |
| `becker_chest_small` | `becker` |
| `becker_beanie` | `becker` |
| `bridge_hat` | `bridge` |
| `bridge_lc` | `bridge` |
| `gaulke_roofing_hat` | `gaulke` |
| `gaulke_roofing_lc` | `gaulke` |
| `gaulke_roofing_beanie` | `gaulke` |
| `hotel_fremont_hat` | `fremont` |
| `hotel_fremont_patch` | `fremont` |
| `mfab_hat` | `mfab` |
| `mfab_lc` | `mfab` |
| `precision_drone` | `drone` |
| `proseal_hat` | `proseal` |
| `proseal_beanie` | `proseal` |
| `tires_hat_3d` | `tires` |
| `goldentee_hat` | `goldentee` |
| `toat_machine_hat` | `toat` |
| `toat_machine_beanie` | `toat` |
| `toat_beanie` | `toat` |

Ten design clusters, as `pro_baseline.ARTWORK` groups them.

## The six arms, and two reserves

Chosen for a VISIBLE difference in a monochrome render of the stitches (no
arm is a thread-colour, density-constant or pull change; none is FABRIC:
`python -m tools.flag_ledger` lists the three OFF flags as LAYOUT, and the
three ON flags carry "Layout, judged in the preview" in their `config.py`
comments). The `moves` and `holds` of every arm are EMPTY: no arm registers a
metric movement, so what each arm changes is a measurement, not an expectation,
and the manipulation check reduces to "changes the stitch stream on at least 3
logos".

| arm | flag and value | stratum | variable | expected pick | basis (memory) |
|---|---|---|---|---|---|
| `apex_cut_on` | `lettering_columns_apex_cut` True | construction | an acute tip: one piece of crosses, or two mitred columns | arm | `apex-cut-2026-10-25`, `apex-walk-2026-10-27` |
| `script_drawn_width_on` | `script_strokes_drawn_width` True | construction | crowded script: stops at the drawn half-width, or reaches the polygon | arm | `script-strokes-2026-10-26` |
| `white_fields_fill_on` | `sew_enclosed_white_fields_fill` True | fill | a sewn white field: a 22 deg fill, or Column-lane letters | arm | `white-faces-fill-2026-10-25` |
| `border_by_size_off` | `border_by_size` False | fill | a plain fill 6 mm and up: satin border, or bare | base | `border-by-size-2026-10-23`, `border-by-size-colour-seams-2026-10-28` |
| `fine_bars_satin_off` | `fine_bars_satin` False | line | a thin free bar: one satin bar, or a hollow bean ring | base | `fine-bars-satin-2026-10-25` |
| `bean_only_lines_off` | `bean_only_lines` False | line | what gets a bean: only drawn lines, or by size | base | `bean-census-2026-10-27` |

Reserves, each replacing a failing arm of its own stratum ONCE
(`settle_arms`), before any picture is seen: `untagged_riders_on`
(`underfill_untagged_riders` True, stratum fill; `mfab-and-recheck-2026-11-06`,
`underfill-knockouts-2026-10-26`) and `dark_ink_bean_off` (`dark_ink_bean`
False, stratum line; `dark-ink-bean-2026-10-28`). A reserve that fails too stays,
flagged `passes: false`.

Expected picks are the kit's prediction for the cost reading only; **the
DreamSim reading never uses them.** Where an arm's flag is OFF today the
expected pick is the arm (built to match the pro, never flipped); where it is
ON today it is the base (Kent flipped it on numbers or in the preview).

## The budget, and the drop order

**Target 50 to 70 live pairs, plus 4 identical and 4 repeat controls.** 22 logos
times 6 arms is 132 at most; how many pairs are live (the arm changes the
stitches) is not known until `prepare` runs. `prepare` does NOT enforce a
budget: `sitting.py` never reads `drop_order_if_over_budget`, which is
documentation for a person. If the build leaves more than 70 live pairs, whole
logos are removed in this order, one at a time, by identity counts alone and
never by a picture or a figure, each removal a dated amendment to this file and
an edit to `spec.json` written before any pick exists, then a rebuild:

`toat_beanie`, `toat_machine_beanie`, `gaulke_roofing_beanie`,
`gaulke_roofing_lc`, `becker_beanie`, `becker_chest_small`, `becker_lc_large`,
`becker_hat_small`, `proseal_beanie`, `mfab_lc`, `hotel_fremont_patch`,
`bridge_lc`.

That is the second and later garments first; the ten logos left
(`becker_hat_large`, `bridge_hat`, `gaulke_roofing_hat`, `hotel_fremont_hat`,
`mfab_hat`, `precision_drone`, `proseal_hat`, `tires_hat_3d`, `goldentee_hat`,
`toat_machine_hat`) keep one job per artwork cluster and are never dropped.
Ten logos by six arms cannot exceed 60 live pairs, so the list always reaches
the budget. If the build leaves fewer than 50, nothing is added.

## What is hidden, and what is committed

The picker serves opaque ids; the sealed key (`arms.json`) stays in
`digitizer/eye_pairs_out/dreamsim-confirm-1108/` and is committed only after the
sitting, with `picks.jsonl`. What is committed now is `manifest.json`: the
sealed map's SHA-256, design hashes, counts, the waiver, and no arm-to-pair
mapping. Each design's DST (`designs/<logo>__<arm>.dst`) holds a client's
stitches and **is never copied under `docs/`** (Kent 2026-10-27); nor is any
render of a pro file.

## The registered reading: DreamSim against Kent's eye

Exactly as `docs/yardstick-perceptual-prereg-2026-11-08.md`, with the
instrument `tools/yardstick_perceptual.py score` at main, shipped defaults,
unchanged:

| setting | value |
|---|---|
| render scale | `--ppm` 12 px/mm, `--pad-mm` 3, `--max-px` 1024 |
| registration | on (`pairframe.register_pair`) |
| colour | monochrome (no `--colour`) |
| tie rule | `--tie-band` 0.0: equal distances only |
| DreamSim | `--dreamsim-type ensemble` |
| bootstrap | percentile, B = 10,000 over pairs and over designs, seed 20261107 |
| oracles | `--oracles` on (self row and blank canvas, reported beside the kappa) |

**Data.** The live population-A pairs of this sitting, from
`python -m tools.yardstick_perceptual from-sitting` (`--populations A --kinds
live`, its defaults): `ours_path` is the design's DST, `ref_path` the pro's DST
of the job, labels LEFT / RIGHT / tie mapped onto before / after / same by the
side shown. The sitting must be completely picked or the adapter refuses. A pair
whose design file is missing is a hard error; a pair whose pro file is missing
is listed with its reason and left out, never imputed.
**`EMB_BRIDGE_PRO` must point at Kent's `Bridge Logo` folder when running from
a worktree** (and `EMB_SCRATCH_KENT` at `scratch_kent`): the first run skipped
19 Bridge pairs without it, a path problem and not a render failure.

**Primary: `dreamsim`.** Cohen's kappa against Kent's picks with ties in, the
3x3 table, linear-weighted, plus the bootstrap 95% interval over pairs and
the design-clustered interval.

**Secondary:** `flip`, `lpips_alex`, `lpips_vgg` and the pixel control `mse`,
reported the same way. Leads only; none can carry a claim.

**The claim rule, identical to the first, fixed now.** "DreamSim agrees with
Kent above chance" is **confirmed** only if the pairs-bootstrap 95% lower bound
is above 0 **and** DreamSim beats `mse`'s point kappa. The design-clustered
interval is reported beside it, and it is stated in advance that **if the pairs
interval clears and the designs interval does not, the result is reported as
"confirmed on pairs, not on designs"**, and nothing stronger. A secondary
metric clearing its interval is a lead for a further sitting, nothing more.

No raw agreement share is computed or quoted (ROADMAP gate 4).

## The second registered reading: the hold-out

The 29 live population-A pairs of `pro-lettering-1102`
(`docs/eye-pairs-2026-11-02/pro-size-lettering/`), labelled by Kent on
2026-11-03 and **never scored by any yardstick**. Same instrument, same
settings, same claim rule, same metrics; the pair list comes from
`from-sitting` on that sitting's spec and its `eye_pairs_out` folder. It is
reported **separately and never pooled** with the new sitting's reading.

**Its small-n catch, stated in advance:** Kent decided 14 of the 29 pairs (11
left, 3 right) and tied 15; the pairs sit in 3 design clusters (`mfab`,
`proseal`, `toat`); and Kent's repeats in that sitting disagreed 3 of 4. The
interval will be wide, the designs interval wider, and a miss there says the
sitting was a weak instrument as much as that DreamSim is. The claim rule is
applied as written; it is not relaxed for n.

## What would invalidate the run

- A render tree that differs from the tree the committed `spec.json`'s sitting
  was prepared on (for the hold-out, the 1102 tree as committed).
- More than 10% of renders failing: the run is still reported, and the reading
  is marked partial.
- Any setting above changed after a score has been seen. A change means a
  new dated pre-registration, and this run is still reported.

## Honest limits, written before the data

- A single laptop render; another machine could differ at the margins. `mfab`
  is photo-class and routes through the photo-prep venv, linked from the
  primary checkout.
- Ten clusters bound the designs interval; a clear designs reading needs a
  large effect.
- Several arms only change art of a certain kind (`script_drawn_width_on`
  crowded script, `white_fields_fill_on` sewn white fields,
  `fine_bars_satin_off` thin bars); few pairs each is expected.
- The monochrome render shows geometry and density, not thread colour; an arm
  that differs only in colour order would score as a tie.
- Not blind to the logo, only to the pair (above). Kent knows these designs.
- An arm whose OFF or ON side is simply worse will be picked against, which
  shows the instrument sees a gross defect, not that a flag is right.
