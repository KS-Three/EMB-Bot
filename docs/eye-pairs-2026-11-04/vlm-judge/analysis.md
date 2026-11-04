# vlm-judge on pro-lettering-1102: analysis (kappa with 95% bootstrap intervals; n beside every figure)

Chance-corrected throughout; no raw agreement figure exists here (ROADMAP gate 4). `before` = the base side, `after` = the arm. Order A is the sitting as Kent saw it; order B had LEFT and RIGHT swapped, mapped back into A's frame before scoring.

## Kent's own controls on this sitting (the ceiling)

- identical pairs called a tie: 3 of 3
- repeat pairs answered the same: 1 of 4
- sides: 22 left, 7 right; 25 of 54 live pairs tied

Excluded from every read and control (the judge was not blind on them, Amendment 1): P001, P002, P003.

## `claude-fable-5-1-session`

64 verdicts, 0 input tokens, 0 output tokens, no API spend (the session judge, Amendment 1).

| scope | order | n scored | n Kent decided | kappa ties in | CI pairs | CI designs | reading | n both decided | kappa sides only | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | A | 54 | 29 | +0.36 | [+0.16, +0.55] | [+0.20, +0.45] | above chance | 16 | +0.45 | [-0.14, +1.00] | [-0.12, +0.74] | no evidence either way |
| passing_arms_only | A | 28 | 15 | +0.18 | [-0.08, +0.43] | [-0.15, +0.34] | no evidence either way | 6 | -0.20 | [-0.50, +0.00] | [-1.00, +0.00] | n too small (<10) |
| vs_kit_expected_label | A | 54 | 54 | +0.16 | [+0.01, +0.30] | [-0.00, +0.28] | no evidence either way | 22 | +0.05 | [-0.25, +0.49] | [-0.26, +0.41] | no evidence either way |

### Judge controls

| order | answered | refused | unparsed | identical called tie | repeats answered the same | L / R in its own frame | ties on live | mean confidence |
|---|---|---|---|---|---|---|---|---|
| A | 61 | 0 | 0 | 3 of 3 | 4 of 4 | 16 / 7 | 32 | 3.48 |

Swap: not run (one order only).

Order A, live pairs, Kent (rows) x judge (cols), before / tie / after:

| | before | tie | after |
|---|---|---|---|
| **before** | 11 | 3 | 1 |
| **tie** | 6 | 19 | 0 |
| **after** | 2 | 10 | 2 |

### Pairs where Kent chose a side and the judge (order A) chose the other: 3

- `P022` toat_machine_hat / `inside_stagger_off`: Kent after, judge before (confidence 2): RIGHT's achine letters look chunkier with a split in the c and blockier h and n; LEFT's script runs smoother. Small difference.
- `P030` k_line / `text_lean_off`: Kent before, judge after (confidence 3): RIGHT's LINE has a clean one-piece N diagonal and a tidier E; LEFT's N is chopped into segments.
- `P061` proseal_beanie / `exit_next_off`: Kent after, judge before (confidence 2): LEFT's hexagon top-right corner shows a notch where the sides meet and its S and E carry extra splits; RIGHT's corner is joined. Small difference.
