# dreamsim-confirm-1108: the sitting, 2026-11-08

Kent sat all 61 pairs (53 live, 4 identical, 4 repeat) on 2026-11-08 from
20:28 to 20:39 (-06:00). `picks.jsonl` has 63 lines: 61 picks, 1 undo row and
the pick it superseded (P044).

`analyse` ran once against the sealed kit. Its full output is `analysis.txt`,
and the inputs it read are in `sitting-inputs.json`. The sealed key
(`arms.json`, hash `865d04a529bf` = the manifest's) and the manipulation deltas
(`manipulation.json`) are committed now that the sitting is over.

**This file judges and flips nothing.** The sitting was not blind to Kent's
prior judging of these logos (`rejudge_pro_jobs`), so none of its per-flag reads
can move a flag.

**The DreamSim reading, which this sitting exists for:** not confirmed.
See `docs/yardstick-perceptual-confirm-2026-11-08.md`.

## Controls

- Identical pairs called a tie: **4 of 4**.
- Repeats answered differently: **1 of 4**.
- Sides chosen: 13 right, 6 left. The shuffle put base on the left in half the
  live pairs, so this lean is Kent's, not the kit's.
- 36 of the 53 live pairs were called a tie.

## analyse's own reads

- **The trims control did not replicate.** Per `analysis.txt`, read nothing else
  in its tables as a finding.
- No primary or secondary metric clears chance on either resampling.
- The expected picks against his read +0.02 with ties in, no evidence either way.
- `analyse` scores 47 live pairs. `pooled.select` drops the six Gaulke pairs by
  `KENT_EXCLUDED`, and Kent tied all six. The DreamSim reading uses all 53, as
  pre-registered.

## Arms (manipulation check, all passed, no replacement)

| arm | logos moved | stratum |
|---|---|---|
| `apex_cut_on` | 18 | construction |
| `script_drawn_width_on` | 5 | construction |
| `white_fields_fill_on` | 12 | fill |
| `border_by_size_off` | 3 | fill |
| `fine_bars_satin_off` | 8 | line |
| `bean_only_lines_off` | 7 | line |

`tires_hat_3d` is identical to base under every arm, so it contributes no live
pair.
