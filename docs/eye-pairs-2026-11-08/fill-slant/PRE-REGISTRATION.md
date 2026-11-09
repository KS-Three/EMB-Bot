# Fill-slant blind sitting (`fill-slant-1108`): pre-registration, 2026-11-08

**Committed BEFORE anything is rendered.** Its twin is `spec.json` beside it.
**When Kent sits it, it is his. This sitting flips nothing:** no flag, route or
default moves on it, and no phase marker moves. What it can license is a
proposal to Kent; the flip is his call.

## Purpose

Kent's ruling, 2026-11-08, "Eye sitting first (Recommended)", in answer to: flip
`fill_angle_pro_slant` now, leave it OFF, or have him sit a blind ON/OFF picker
on the pro jobs first. The flag (`cfg.extra`, OFF, built in PR #1350;
`docs/fill-angle-pro-slant-2026-11-07.md`) slants each fill +20 deg (else -20)
off its OFF angle unless that cuts the shape into many more columns. Its
write-up measured direction kappa against the pro, 0.311 to 0.395; this sitting
asks whether Kent's eye prefers the result.

## Not blind to prior judging, on purpose

The blinding guard refuses a logo Kent has judged. It is lifted for
`pro_paired_job` logos by the `rejudge_pro_jobs` key in `spec.json`. Kent's
words: "Eye sitting first (Recommended)". The reason, as written in the spec:
judging a fill-direction flag against Kent's eye needs the pro-paired fill
designs. What stays blind is the PAIR: which side is the base and which the
arm is shuffled under seed 20261109 and sealed.

## The base and the one arm

Base: today's `main` defaults, no override (`base_flags` empty).

| arm | flag and value | stratum | variable | expected pick |
|---|---|---|---|---|
| `fill_slant_on` | `cfg.extra["fill_angle_pro_slant"]` True | fill | fill direction per shape: slanted +20 / -20 with a trims guard, or the shape's own angle | arm |

The kit validates flags against `PipelineConfig` fields; `fill_angle_pro_slant`
is a `cfg.extra` key, so the spec spells the arm `{"extra":
{"fill_angle_pro_slant": true}}`, which `PipelineConfig(extra=...)` takes
as is. No reserve arms. The manipulation check is "changes the stitch stream on
at least 3 logos"; if it fails, the sitting is stopped and reported, not
patched.

## The logos: every pro job

The same 22 `pro_baseline.JOBS` logos as `dreamsim-confirm-1108`, each at its
own garment and width, kind `pro_paired_job`, population A:
`becker_hat_large`, `becker_lc_large`, `becker_hat_small`,
`becker_chest_small`, `becker_beanie`, `bridge_hat`, `bridge_lc`,
`gaulke_roofing_hat`, `gaulke_roofing_lc`, `gaulke_roofing_beanie`,
`hotel_fremont_hat`, `hotel_fremont_patch`, `mfab_hat`, `mfab_lc`,
`precision_drone`, `proseal_hat`, `proseal_beanie`, `tires_hat_3d`,
`goldentee_hat`, `toat_machine_hat`, `toat_machine_beanie`, `toat_beanie`.
Ten design clusters, as `pro_baseline.ARTWORK` groups them. A logo whose ON and
OFF stitch streams are byte-identical is not a pair; it is listed in the
README after `prepare`. At most 22 live pairs, plus `n_identical` 4 and
`n_repeat` 4 controls (which enter no statistic). No logo is dropped for budget.

## The registered reading

Kent picks LEFT, RIGHT or tie per pair. Reported, on live pairs only:

1. **Counts:** pairs where Kent picked ON (`arm`), picked OFF (`base`), tied.
2. **`analyse`'s outputs**, as the tool prints them: sides-only and ties-in
   kappa against the kit's expected pick, both intervals (pairs and
   design-clustered), the controls report, the leads, and the pro-distance
   table. Those are descriptions; none carries a claim.

**Pre-registered definition of "favours ON":** more decided pairs for ON than
for base (ties excluded), **and** the design-clustered bootstrap interval of
(ON - base) / decided share lies above 0. Percentile bootstrap, B = 10,000,
resampling designs (the `design` key), seed 20261109. Fewer than 6 decided
pairs, or an interval that includes 0, is reported as "does not favour ON" and
not as evidence against it. "Favours OFF" is the mirror. The flip itself is
Kent's call; nothing here flips it.

No raw agreement share is computed or quoted (ROADMAP gate 4).

## What would invalidate the run

- A render tree that differs from the one `manifest.json` was prepared on.
- Any setting above changed after a pick has been seen: a new dated
  pre-registration, and this run is still reported.

## Honest limits, written before the data

- One flag, one sitting, one laptop render; a fill direction shows in a
  monochrome render, but a small slant can look like a tie.
- Ten clusters bound the design-clustered interval; a clear reading needs a
  large effect. Becker's five jobs share one artwork.
- Not blind to the logo, only to the pair. Kent knows these designs.
- Jobs with no fill (all satin or line) will be byte-identical and drop out.
