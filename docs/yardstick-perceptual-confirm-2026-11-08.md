# Perceptual yardstick vs Kent's eye: the confirmation (2026-11-08)

**DreamSim is NOT confirmed.** On the new blind sitting `dreamsim-confirm-1108`
it reads 3-way kappa **+0.099**, pairs interval **[-0.04, +0.24]**, against
mse's -0.005. The pre-registered rule
(`docs/eye-pairs-2026-11-08/dreamsim-confirm/PRE-REGISTRATION.md`) needs the
pairs lower bound above 0 **and** a win over mse's point kappa. The second half
holds and the first does not. On the pre-registered hold-out (the 29 live
population-A pairs of pro-lettering-1102) it reads **-0.127**, no evidence
either way.

Read together with the first run (`yardstick-perceptual-result-2026-11-08.md`,
+0.197 on the 100 pooled pairs), the +0.197 did not replicate on fresh pairs.
Whatever DreamSim tracks of Kent's eye is too weak to stand in for him. Nothing
flips, no default moves and no phase moves. No raw agreement share is computed
(ROADMAP gate 4).

## The confirmation sitting (primary)

Kent sat 61 pairs on 2026-11-08, 20:28 to 20:39 (-06:00): 53 live, 4 identical,
4 repeat. `from-sitting` built the pair list from the 53 live population-A
pairs, as the pre-registration names. No pro file was missing, and no pair was
skipped except the identical and repeat controls. `scores.csv` md5
`0774d84fd2f7cbb839c2846b511d758b` (148 rows: 106 pair rows plus 21 self and
21 blank oracle rows). Kent chose a side on 17 pairs and tied 36.

| metric | kappa 3-way (ties in, n 53) | CI pairs | CI designs | reading | kappa 2x2 (n both decided) |
|---|---|---|---|---|---|
| **dreamsim (primary)** | **+0.099** | [-0.04, +0.24] | [-0.00, +0.21] | no evidence either way | +0.329 (17) |
| mse (control) | -0.005 | [-0.17, +0.17] | [-0.11, +0.08] | no evidence either way | -0.091 (15) |
| flip | +0.057 | [-0.09, +0.21] | [-0.07, +0.21] | no evidence either way | +0.131 (17) |
| lpips_vgg | +0.028 | [-0.11, +0.17] | [-0.09, +0.17] | no evidence either way | +0.105 (17) |
| lpips_alex | -0.096 | [-0.24, +0.05] | [-0.19, +0.02] | no evidence either way | -0.365 (17) |

The design-clustered lower bound is -0.002, which the tool rounds to +0.00. It
does not clear 0 either, so the pre-registered weaker outcome ("confirmed on
pairs, not on designs") does not arise. Only 9 of the 10 artworks contribute:
`tires_hat_3d` had every arm identical to base. Oracles: DreamSim and mse pass
all three. flip and both LPIPS fail "blank is worst", as in the first run.

## The hold-out (secondary, never pooled)

The 29 live population-A pairs of pro-lettering-1102 (Kent sat 2026-11-03). No
yardstick had scored them before. `scores.csv` md5
`68ce56e2f863a830735acf5033af0b6f`. Kent decided 14 of the 29.

| metric | kappa 3-way (n 29) | CI pairs | CI designs | reading |
|---|---|---|---|---|
| **dreamsim** | **-0.127** | [-0.34, +0.09] | [-0.29, +0.00] | no evidence either way |
| mse | +0.171 | [-0.07, +0.40] | [+0.05, +0.25] | no evidence either way |
| lpips_alex | +0.095 | [-0.14, +0.32] | [-0.00, +0.15] | no evidence either way |
| lpips_vgg | +0.028 | [-0.19, +0.25] | [-0.29, +0.20] | no evidence either way |
| flip | +0.015 | [-0.19, +0.22] | [-0.10, +0.20] | no evidence either way |

The pre-registration named the catch: 14 decided pairs, 3 clusters, and repeats
in that sitting that disagreed 3 of 4. DreamSim's point estimate here is on the
wrong side of 0, below the pixel control.

## Trust in the picks

- Identical pairs called a tie: 4 of 4. Repeats answered differently: 1 of 4,
  steadier than 1102's 3 of 4.
- Sides: 13 right and 6 left, per `analyse`'s count. In `from-sitting` the left design is always `before`, so a side habit
  shows as a before/after skew: 11 after against 6 before on the 17 decided
  live pairs. The shuffle put base on the left in half the live pairs, so the
  habit cannot favour an arm. It does add noise.
- The sitting was not blind to prior judging (Kent's waiver,
  `rejudge_pro_jobs`). Its per-flag reads in `analysis.txt` must not move a flag.

## Checked independently

Two read-only agents ran after scoring.

- Every kappa was recomputed without the tool's code. All agree within 0.005.
- All 53 labels were traced end to end: the `picks.jsonl` replay, including
  P044's undo, then `arms.json` left and right, then the before/after DST in
  `pairs.csv`. There are 0 mismatches. The shown left image is md5-equal to the
  left arm's render, so nothing is swapped.
- Settings in `report.json` equal the registered ones: ppm 12, pad 3,
  max-px 1024, registration on, monochrome, tie-band 0, ensemble, B 10,000,
  seed 20261107.
- The sealed key hash `865d04a529bf` matches `arms.json`. Every `skipped.json`
  entry is `identical_to_base`, so no render failed.
- Order of events:
  - PRE-REGISTRATION committed 29863ec8 at 18:08.
  - Render 19:40 to 20:21.
  - Manifest committed 1b748dbf at 20:23.
  - First pick 20:28, last pick 20:39.
  - Scores written 21:09.

## What to know (disclosures)

1. **`sitting analyse` reports 47 live pairs; the DreamSim set is 53.** The six
   difference are the Gaulke pairs. `pooled.select` drops `gaulke` by
   `KENT_EXCLUDED` (`tools/eye_pairs/pooled.py`), and `from-sitting` does not.
   The pre-registration lists the three `gaulke_roofing_*` logos and names
   `from-sitting`'s set, so 53 is the registered reading. Kent tied all six.
   As a sensitivity, not registered: on the 47, DreamSim reads +0.116 and mse
   +0.014.
2. **The base was main at the pre-registration commit.** The nest-door flip
   (#1366) reached main at 19:07, 12 minutes before the render started, and the
   render ran on 29863ec8 without it. The registered tree is satisfied. "Today's
   defaults" is one flip stale.
3. **`analyse` ran before the DreamSim score** (20:45 against 21:09). Its sitting
   metrics were seen first. No yardstick setting changed (`report.json` above).
4. `analyse`'s own trims control did not replicate. Per its rule, nothing else
   in `analysis.txt` is read as a finding. That governs the sitting metrics, not
   the DreamSim reading.

## What this leaves

Three reads now exist: +0.197 (100 pooled pairs, passed), +0.099 (53 fresh,
failed), and -0.127 (29 hold-out, no evidence). The 2x2 on decided pairs keeps
DreamSim positive in two of three (+0.43, +0.33), but those rest on 40 and 17
pairs. No instrument here is Kent's eye. Kent's picks remain the only judge of a
flip, and the pro-pair trims family stays as ruled on 2026-11-02 ("My eye stands").

## Reproduce

On Kent's laptop, with the yardstick venv. From the repo root:

```bash
EMB_BRIDGE_PRO="<...>/Embroidery/Digitized Designs/Bridge Logo" EMB_SCRATCH_KENT="<repo>/scratch_kent" \
  python -m tools.yardstick_perceptual from-sitting docs/eye-pairs-2026-11-08/dreamsim-confirm/spec.json \
    --out-dir digitizer/eye_pairs_out/dreamsim-confirm-1108 --out <R>/pairs.csv
python -m tools.yardstick_perceptual score <R>/pairs.csv --labels --oracles --out <R>/score
```

For the hold-out, the same two commands run with
`docs/eye-pairs-2026-11-02/pro-size-lettering/spec.json` and
`--out-dir digitizer/eye_pairs_out/pro-lettering-1102`.
