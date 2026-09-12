# What the default-ON flags cost in clock — 2026-09-12

The edge cap's flip measured its stitch bill (+5.9–26.3%) and not its clock,
and the clock was **86 minutes a design** (PR #464). This asks the obvious
follow-up question of every other flag that went on by default since
2026-09-01: *was its runtime ever measured?*

**Headline: there is no second edge cap.** Nothing here is an outlier of that
kind — the worst is 60% of one design, not 388×, and every expensive flag is
doing real work (all of them change the stitches). What there is, is a
documentation gap: **two flags have substantial runtime bills that are written
down nowhere**, and a third's documented band understates it on the very
design class it names.

Harness: `tools/pro_parity/flagcost.py`, run over the prepped corpus.

## The instrument had to be fixed first, and the inert flags are why

The first version timed the baseline, then one arm per flag. On
`hotel_fremont_hat` every arm came out ~1.5 s cheaper than the baseline —
including three flags that returned a **byte-identical plan**:

| flag | "cost" | plan |
|---|---|---|
| `satin_house_fourfold` | +1.66 s (13.3%) | byte-identical |
| `merge_duplicate_cones` | +1.69 s (13.5%) | byte-identical |
| `rehome_resnapped` | +1.70 s (13.6%) | byte-identical |

A flag that changes nothing cannot cost 13% of a run. The inert arms were the
error bar, and they said the instrument was wrong: **the first `run_stages` in
a process pays import, cache and allocator costs no later one repeats.**

Fixed by discarding a warm-up pass, re-measuring the baseline *after* the
arms, and treating the difference between the two baselines as the noise
floor. The same three flags then read −0.05 s, −0.24 s and −0.15 s. Every
number below is from the corrected harness; the first sweep's numbers were
discarded rather than adjusted.

Drift per design: `gaulke_roofing_lc` ±0.04 s, `precision_drone` ±0.09 s,
`hotel_fremont_hat` ±0.69 s, `machine_hat` ±1.85 s. **On Fremont the drift is
larger than most of the effects, so most flags are simply unresolved there** —
that is stated rather than papered over.

## Measured

Four designs, chosen to span what the corpus contains rather than to sample
it: satin lettering (`hotel_fremont_hat`), a fill-dominated flat logo
(`gaulke_roofing_lc`), a gradient badge (`precision_drone`), and the corpus's
largest fill (`machine_hat`, 33,898 stitches). Share of that design's total
digitize time, worst design for each flag:

| flag | worst | `machine_hat` | `precision_drone` | `roofing_lc` | `fremont_hat` |
|---|---|---|---|---|---|
| `fill_travel_under_cover` | **+59.8%** | +54.60 s | +26.0% | +7.3% | *noise* |
| `subpixel_edges` | **+48.4%** | +44.16 s | +10.6% | +3.5% (inert) | *noise* |
| `curve_turn_deg` | **+32.1%** | +29.32 s | +5.8% | inert | *noise* |
| `borders_last` | +16.0% | *noise* | +4.7% | +14.1% | +1.80 s |
| `edge_cap` | +14.3% | inert | +2.2% | +1.06 s | +13.4% |
| `enclosed_by_garment` | — | *noise* | *noise* | *noise* | *noise* |
| `design_ramp` | — | *noise* | inert | *noise* | *noise* |
| `satin_house_fourfold` | — | *noise* | inert | *noise* | *noise* |
| `merge_duplicate_cones` | — | *noise* | inert | inert | *noise* |
| `rehome_resnapped` | — | *noise* | inert | *noise* | *noise* |

Five of the ten are under the noise floor or inert on every design measured.
`edge_cap`'s remaining 14.3% is what the cap legitimately costs now that
PR #464 removed the pathological part.

**Correction before this merged: the `subpixel_edges` and `curve_turn_deg`
rows are not independent, and their two numbers must not be added.** This
harness turns ONE flag off at a time, which cannot see an interaction, and
these two interact. A fourth arm with both off, on `machine_hat`:

| arm | region vertices | plan | stitches |
|---|---|---|---|
| both on (shipped) | 5,213 | 84.8 s | 33,898 |
| `curve_turn_deg` off | 999 | 56.0 s | 33,771 |
| `subpixel_edges` off | 943 | 42.6 s | 33,743 |
| **both off** | **943** | **42.7 s** | **33,743** |

"`subpixel_edges` off" and "both off" are the same run: **without sub-pixel
edges, `curve_turn_deg` is byte-for-byte inert** — it has nothing to refine.
So the one-at-a-time table above credits `subpixel_edges` with 44.2 s that is
mostly `curve_turn_deg`'s, and the two rows sum to 73 s against a real joint
cost of 42.1 s. The honest split:

- `subpixel_edges` on its own: **+13.3 s** (42.7 → 56.0 s)
- `curve_turn_deg` on top of it: **+28.8 s** (56.0 → 84.8 s), for **127
  stitches** of 33,898 — it is the pass that takes 999 vertices to 5,213.

**`flagcost.py` now says in its docstring that a one-flag-off arm measures a
flag's cost GIVEN every other flag, not its cost alone.**

## Which step pays

cProfile of `plan_stitches` on `machine_hat`, each arm diffed against the
shipped run. **All of it is stage 6's fill, on the design's 5 fill shapes**
(`stage7_sequence.stitch_one` → `stage6_fill.stitch_shape`), and none of it
is the refinement itself (`run_stages` is ~3.5 s in every arm). Two loops redo
shapely booleans against a polygon that now has 5× the vertices:

- **The fill angle search.** `best_fill_angle_deg` tries 17 candidate row
  angles (16 plus the PCA angle) and runs `_row_spans` for every one, which
  intersects each scan row with the polygon: **~14 s**, and +16–17 s of
  shapely `intersection` self-time over 24,350 calls.
- **The cover-aware reorder and routing** — `fill_travel_under_cover`'s own
  machinery (`_reorder_for_cover`, `_order_cost`, `travel_path`, and the
  `sewn` footprint's `union` / `buffer`): **~10–19 s**, with `travel_path`
  called 2,720–2,810 → 4,190 times because the denser polygon fragments the
  fill into more pieces to route between.

The shipped and both-off plans differ by **155 stitches of 33,898 (0.46%)**.

## The obvious speed-up, tried and disproved

Tatami rows sit 0.4 mm apart, and the angle search only has to RANK 17
angles, so it looked safe to run that ranking on a simplified polygon and keep
the full one for laying the rows. **It is not safe at any tolerance that buys
anything.**

Method: `best_fill_angle_deg` wrapped so that every real call — all 122 angle
searches the shipped pipeline makes across the 23 designs — also runs the same
search on `poly.simplify(tol, preserve_topology=True)`, while RETURNING the
shipped angle, so the shapes asked about are exactly the shipped ones. PCA stays
on the original polygon. A **control arm** runs the copied search on the
unsimplified polygon; it must read zero, or every other row is measuring the
harness.

| tolerance | angle changed | search speed-up | mean vertices |
|---|---|---|---|
| **control (none)** | **0 / 122** | 1.0× | 440 |
| row/32 (0.0125 mm) | **1 / 122** | 1.3× | 244 |
| row/16 | 5 / 122 | 1.4× | 192 |
| row/8 | 8 / 122 | 1.6× | 145 |
| row/4 | 23 / 122 | 1.9× | 105 |
| row/2 | 43 / 122 | 2.2× | 73 |
| row/1 | 69 / 122 | 2.5× | 50 |

*(Two runs of the same deterministic harness: control, row/32, row/16 and
row/8 in the second; row/4, row/2 and row/1 in the first, which had no control.
They share row/8 and agree on it exactly — 8 / 122 both times — and the
search code the control validated is identical in both.)*

The control is clean, so the changes are real. At **0.0125 mm** — a thirtieth
of a row, far below a thread — `becker_hat_large` already flips from **90° to
−83°**, and that tolerance saves only a quarter of the search. Other flips
are just as large: `becker_beanie` 157.5° → 146.25° on a 1,574 mm² shape,
`gaulke_plowing_hat` 45° → 78.75°.

**Why: the ranking is a discrete COUNT with a strict tiebreak.** The key is
`(columns, distance to PCA, angle)`, and many candidate angles tie or come
within one column of each other. Scanlines sample the polygon at fixed rows,
so moving a single vertex a hundredth of a millimetre can change whether one
row's span splits — one column more or fewer — and that flips the winner
between two near-equivalent directions. **The auto fill angle is not a stable
property of the artwork at sub-thread scale.** That is the same family as the
satin/fill classifier flipping under boundary detail
(`classifier-stability-2026-09-03`), and it implies — NOT measured here —
that `subpixel_edges` and `curve_turn_deg` may be moving fill angles as well
as costing time.

Search time also turned out to depend less on vertices than the profile made
it look: cutting mean vertices from 440 to 244 bought 1.3×, not 1.8×. Rows and
per-call overhead are a large fixed share, so even a correct speed-up here
would have recovered less than the ~14 s the angle search costs.

**No engine change.** Do not retry this with a different simplifier without
the control arm and a zero-mismatch bar; the result above is why.

## The gap

- **`subpixel_edges` and `curve_turn_deg` document no runtime cost at all.**
  Their `config.py` blocks are long and careful about quality trade-offs;
  neither mentions the clock. Together they cost `machine_hat` **42.1 s of
  84.8 s** of plan time — `subpixel_edges` 13.3 s of it and `curve_turn_deg`
  28.8 s on top, which only exists because sub-pixel edges are on. (The
  +48.4% / +32.1% in the table above are one-at-a-time numbers that overlap;
  see the correction under it.) Both now carry the split.
- **`fill_travel_under_cover`'s documented band understates on logos.** The
  config says *"+7–11% digitize time on logos, +49–67% on sunset's 263-run
  fill"*. Measured: `precision_drone`, a logo, reads **+26.0%**, and
  `machine_hat`, also a logo, reads **+59.8%**. The two bands are not
  logo-versus-photo; they are **few-run versus many-run**, and a logo can sit
  in either. Corrected in place.

## What this does and does not say

It says these three flags carry real, load-bearing costs that scale with how
much fill work a design has, and that two of them were unwritten. **It does
not say any of them should be off** — all three change the output, and their
quality cases were argued and ruled on their own merits.

Limits, stated: four designs, not 23; one machine; wall clock, not CPU;
`machine_hat` and `machine_lc` are near-duplicates in the corpus (same art
size, 33,898 against 33,921 stitches), so the "largest fill" column is one
design's evidence, not two. A flag reading *noise* here is unmeasured on that
design, not proven free.
