# Claude as the eye, the 100-pair repeat (`vlm-judge-100`): results, 2026-11-06

The judge of Amendment 1 (`PRE-REGISTRATION.md`), this Claude Code session
on `claude-opus-5-5`, gave all 103 verdicts on 2026-11-06 in thirteen
batches (twelve of eight, one of seven). Each batch was written to
`verdicts-claude-opus-5-5-session.jsonl` with `vlm_judge record` before the
next pair was opened. The judge read `pairs.json` and the three pictures per
pair, and nothing else from the kit. `arms.json` and Kent's labels were first
read by `analyse --pro100`, which ran once after the 103rd verdict and wrote
`analysis.md` / `analysis.json`.

**This file judges nothing about the engine and flips nothing.** Kappa is
chance-corrected throughout. No raw agreement figure exists here (ROADMAP
gate 4).

## The kit

- **Render.** `render --sitting-size` finished 143 of 143 designs with 0
  failed. Eleven designs came from the 11-04 lane and 132 were rendered on
  11-06 (Amendment 1). The run was stopped and resumed twice, once for build
  sessions and once for a laptop restart. It resumes from disk, so nothing
  was re-drawn.
- **Kit.** Built with seed 20261104: 99 live pairs plus 4 identical pairs,
  103 in all. One pair was excluded, `off-flags-1003:cap_recentre:becker`.
  No design was missing.

## The pre-registered primary

| scope | n scored | n Kent decided | kappa, ties in | CI pairs | CI designs (fixture) | reading |
|---|---|---|---|---|---|---|
| 99 live pairs, order A | 99 | 40 | **+0.34** | [+0.17, +0.49] | [+0.23, +0.44] | **above chance** |

Both intervals clear zero. On the 100 labelled pro pairs, re-drawn at each
sitting's own size, the session's blind L / R / tie tracks Kent's labels
above chance.

**Beside the 11-04 read, never pooled.** The judge model changed, so this is
not a same-instrument repeat:

| read | judge | n | kappa, ties in | CI pairs | CI designs | sides only |
|---|---|---|---|---|---|---|
| `vlm-judge` 11-04 | `claude-fable-5-1` session | 54 | +0.36 | [+0.16, +0.55] | [+0.20, +0.45] | +0.45, n 16, no evidence |
| `vlm-judge-100` 11-06 | `claude-opus-5-5` session | 99 | +0.34 | [+0.17, +0.49] | [+0.23, +0.44] | **+0.65, n 22, above chance** |

The two judges, sittings and fixtures read the same within their intervals.
The secondary is the one that moved.

## What the agreement is made of

Kent (rows) against the judge (columns), 99 live pairs:

| | before | tie | after |
|---|---|---|---|
| **before** (the base side) | 8 | 4 | 0 |
| **tie** | 9 | 43 | 7 |
| **after** (the arm) | 4 | 14 | 10 |

- **Where the agreement comes from.** Most of it is shared ties: 43 of
  Kent's 59 ties.
- **The base side.** Where Kent picked the base, the judge never picked the
  arm (8 base, 4 tie, 0 arm).
- **Kent's 28 arm picks.** The judge backed the arm on 10, tied 14, and
  picked the base on 4.
- **Unlike 11-04, the judge backs the arm here.** That judge backed the arm
  on 2 of Kent's 14 arm picks and picked the base on 19 of its 22 decided
  pairs. This judge's decided picks split 21 base, 17 arm.

## Secondaries (reported whatever the primary says, promoted to nothing)

| scope | n | kappa, ties in | CI pairs | CI designs | reading | n both decided | kappa sides | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|---|---|---|---|
| sides only, all live | — | — | — | — | — | 22 | +0.65 | [+0.34, +0.91] | [+0.40, +0.89] | above chance |
| `flags-0918-0928` (cloud render) | 49 | +0.38 | [+0.16, +0.58] | [+0.23, +0.52] | above chance | 12 | +0.82 | [+0.43, +1.00] | [+0.30, +1.00] | above chance |
| the other eight sittings | 50 | +0.30 | [+0.08, +0.52] | [+0.20, +0.39] | above chance | 10 | +0.44 | [+0.00, +1.00] | [+0.00, +0.70] | no evidence either way |
| ref-engine arms (`ref_0827`, `ref_0930am`) | 11 | +0.69 | [+0.33, +1.00] | [+0.42, +1.00] | above chance | 5 | n/a | | | n too small (<10) |
| flag arms | 88 | +0.27 | [+0.10, +0.44] | [+0.17, +0.38] | above chance | 17 | +0.54 | [+0.21, +0.88] | [+0.17, +0.86] | above chance |

- **The cloud-render sitting does not carry the read.** It was judged by
  Kent on pictures this laptop never held, and both it and the other eight
  sittings read above chance with overlapping intervals.
- **The ref-engine arms read higher than the flag arms, but n is 11.** The
  ref-engine arms are whole-engine differences (an older base against a
  newer one); the flag arms are one switch each. The difference is in the
  direction one would expect, but it rests on 11 pairs.
- **The design intervals are fixture clusters** (six clusters), as
  pre-registered. They come out narrower than the pair intervals here, which
  is a property of these six fixtures and not a claim of extra precision.

## Controls

| control | result |
|---|---|
| identical pairs called a tie | **4 of 4** |
| refusals / parse failures | 0 / 0 of 103 |
| L / R picks in the judge's own frame | 17 L / 21 R (the kit puts the base on the left in exactly half) |
| ties on live pairs | 61 of 99 (Kent: 59 of 99) |
| mean stated confidence | 3.5 |
| repeat and swap controls | not run (void for a judge with memory; pre-registered) |

## Pairs where Kent chose a side and the judge chose the other (4)

Listed, not scored. Reasons are the judge's own, recorded before the arms
were unsealed:

- `P026` becker, `lettering_columns`: Kent after, judge before (confidence
  2). *"Right's MARINE is sewn with very open, sparse columns that will show
  fabric, and its E is malformed; left's MARINE is lumpy but fully covered."*
- `P037` drone, `lettering_columns`: Kent after, judge before (confidence
  4). *"Left sews PRECISION and THERMAL as open zigzag skeletons that will
  not cover, and AND DRONE breaks into scraps. Right's lettering is solid
  and readable."*
- `P097` fremont, `lettering_columns`: Kent after, judge before (confidence
  2). *"Right's HOTEL FREMONT and THE are heavier and bloated, losing serif
  detail; left's lettering is a touch cleaner."*
- `P099` drone, `directional_comp`: Kent after, judge before (confidence 2).
  *"Left fills the dark ground on a diagonal with visible jump lines across
  the scene; right's horizontal fill is calmer and its THERMAL is tidier."*

Three of the four are `lettering_columns`. On two of those the judge's
reason is coverage: open columns that "will show fabric". That is a
sew-out question this picture cannot settle (ROADMAP gate 1).

## What this licenses (the pre-registered outcome rule, word for word)

The primary is **above chance**. Together with the 11-04 read, that is two
independent sets on which a session's blind pick tracks Kent's: nine
sittings over six fixtures here, plus `pro-lettering-1102`. It licenses **a
proposal to Kent, not a build**:

- a vision pre-screen row on the eye-pairs page ("the judge calls this
  identical / damaged / look");
- spending the registered API arms' few dollars once a key exists.

It licenses **no** flag flip, routing change or engine-quality claim. No
per-arm kappa was computed: n per arm is 1 to 9. The pre-screen has its
own pre-registration (`PRESCREEN-PRE-REGISTRATION.md`, committed before this
kit was built). That pre-registration is not computed here.

## Not done, by design

- No prompt change.
- No API call. The `claude-opus-5-5` and `claude-haiku-5-5` arms and their
  two orders stay as registered.
- No comparison against the pro's DST.
- No pooling with the 11-04 verdicts.
- Kent's sittings themselves were not repeated.
