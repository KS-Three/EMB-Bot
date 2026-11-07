# vlm-judge on vlm-judge-pro100: analysis (kappa with 95% bootstrap intervals; n beside every figure)

Chance-corrected throughout; no raw agreement figure exists here (ROADMAP gate 4). `before` = the base side, `after` = the arm. Order A is the sitting as Kent saw it; order B had LEFT and RIGHT swapped, mapped back into A's frame before scoring.

## Kent's own controls on this sitting (the ceiling)

- identical pairs called a tie: 0 of 0
- repeat pairs answered the same: 0 of 0
- sides: 22 left, 18 right; 59 of 99 live pairs tied

## `claude-opus-5-5-session`

103 verdicts, 0 input tokens, 0 output tokens, no API spend (the session judge, Amendment 1).

| scope | order | n scored | n Kent decided | kappa ties in | CI pairs | CI designs | reading | n both decided | kappa sides only | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | A | 99 | 40 | +0.34 | [+0.17, +0.49] | [+0.23, +0.44] | above chance | 22 | +0.65 | [+0.34, +0.91] | [+0.40, +0.89] | above chance |
| flags_0918_0928_cloud_render | A | 49 | 17 | +0.38 | [+0.16, +0.58] | [+0.23, +0.52] | above chance | 12 | +0.82 | [+0.43, +1.00] | [+0.30, +1.00] | above chance |
| other_sittings | A | 50 | 23 | +0.30 | [+0.08, +0.52] | [+0.20, +0.39] | above chance | 10 | +0.44 | [+0.00, +1.00] | [+0.00, +0.70] | no evidence either way |
| ref_engine_arms | A | 11 | 6 | +0.69 | [+0.33, +1.00] | [+0.42, +1.00] | above chance | 5 | n/a | n/a | n/a | n too small (<10) |
| flag_arms | A | 88 | 34 | +0.27 | [+0.10, +0.44] | [+0.17, +0.38] | above chance | 17 | +0.54 | [+0.21, +0.88] | [+0.17, +0.86] | above chance |

### Judge controls

| order | answered | refused | unparsed | identical called tie | repeats answered the same | L / R in its own frame | ties on live | mean confidence |
|---|---|---|---|---|---|---|---|---|
| A | 103 | 0 | 0 | 4 of 4 | 0 of 0 | 17 / 21 | 61 | 3.5 |

Swap: not run (one order only).

Order A, live pairs, Kent (rows) x judge (cols), before / tie / after:

| | before | tie | after |
|---|---|---|---|
| **before** | 8 | 4 | 0 |
| **tie** | 9 | 43 | 7 |
| **after** | 4 | 14 | 10 |

### Pairs where Kent chose a side and the judge (order A) chose the other: 4

- `P026` becker / `lettering_columns`: Kent after, judge before (confidence 2): BECKER matches. Right's MARINE is sewn with very open, sparse columns that will show fabric, and its E is malformed; left's MARINE is lumpy but fully covered.
- `P037` drone / `lettering_columns`: Kent after, judge before (confidence 4): Left sews PRECISION and THERMAL as open zigzag skeletons that will not cover, and AND DRONE breaks into scraps. Right's lettering is solid and readable.
- `P097` fremont / `lettering_columns`: Kent after, judge before (confidence 2): Right's HOTEL FREMONT and THE are heavier and bloated, losing serif detail; left's lettering is a touch cleaner and closer to the art's weight.
- `P099` drone / `directional_comp`: Kent after, judge before (confidence 2): Left fills the dark ground on a diagonal with visible jump lines across the scene; right's horizontal fill is calmer and its THERMAL is tidier.
