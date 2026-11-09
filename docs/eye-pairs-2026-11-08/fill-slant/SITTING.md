# fill-slant-1108: the sitting, 2026-11-09

Kent sat all 24 pairs on 2026-11-09, between 17:24 and 17:27 local time, with one
undo (P022, re-picked). The sealed map `arms.json` hashes to
`272173d9176322d62e8f2094309af96fedf37f46185076063e7abd98552336e0`, the
`sealed_sha256` in the committed `manifest.json`. So the picks were read against
the pair set the pre-registration describes.

**Kent's ruling (2026-11-09): "Keep OFF, record (Recommended)".**
`fill_angle_pro_slant` stays OFF and its code stays in the tree. The flip was
his call, as the pre-registration says, and this sitting does not move it.

## The registered reading (PRE-REGISTRATION.md, "favours ON")

On the 16 live pairs, ON (`fill_slant_on`) got **0**, OFF (base) got **7**, and
**9** were ties.

| design | live pairs | Kent's picks |
|---|---|---|
| becker | 5 | base, base, base, base, tie |
| bridge | 2 | base, tie |
| tires | 1 | base |
| toat | 1 | base |
| gaulke | 2 | tie, tie |
| mfab | 2 | tie, tie |
| fremont | 1 | tie |
| goldentee | 1 | tie |
| proseal | 1 | tie |

- **Does it favour ON?** No. ON has fewer decided pairs than base.
- **Mirror ("favours OFF"):** base leads on 7 decided pairs, at least the 6 the
  pre-registration requires. (ON - base) / decided is **-1.00**. Its
  design-clustered percentile bootstrap (B = 10,000, seed 20261109, resampling
  the 9 designs) is **[-1.00, -1.00]**: 9,953 resamples drew at least one
  decided pair, and every one of them was all base. So the reading is **favours
  OFF**.
- **Read it with these caveats:**
  - The decided pairs come from 4 designs, and Becker gives 4 of the 7.
  - The interval is degenerate because Kent never picked ON. A degenerate
    interval is not a precise effect.
  - 9 of 16 were ties: on most jobs, a 20-degree slant did not read as a
    difference at this render.

Script: the arithmetic above is plain counting over `arms.json` plus
`picks.jsonl`, read through `tools.eye_pairs.pairs.load_picks`, which applies
undo.

## `analyse`'s outputs (`analysis.md`, verbatim)

- `analyse` reads **14** live pairs, not 16. `pooled.select` drops Gaulke
  (`KENT_EXCLUDED`), and both Gaulke pairs were ties, so the decided count is 7
  either way.
- **Expected picks against his:** the pre-registration expected the arm.
  - Sides only: -0.69 [-0.96, +0.00], n too small (<10).
  - Ties in: -0.50 [-0.71, -0.19], designs [-0.66, -0.05], below chance.
  - This is the tool's kappa view of the same result.
- **Every lead** reads "n too small (<10)" sides-only and "no evidence either
  way" ties-in. The trims control does not replicate, so the lead table itself
  says to read nothing else in it.
- **Controls:**
  - 3 of 4 identical pairs were called a tie. On P009, `tires_hat_3d`, he
    picked left.
  - 0 of 4 repeats were answered differently.
  - Sides picked: 5 left, 7 right.

No raw agreement share is computed or quoted (ROADMAP gate 4).

## Files

`analysis.md` is `analyse --markdown`. `sitting-inputs.json` is `--inputs`.
`arms.json`, `manipulation.json` and `picks.jsonl` are copied from
`eye_pairs_out/fill-slant-1108`, as `dreamsim-confirm` did.
