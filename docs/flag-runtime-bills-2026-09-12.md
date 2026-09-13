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

> **Caveat added 2026-09-13: every clock number in this file was measured in
> the parity harness's configuration, not the customer's.**
> `prep_all.parity_config` deliberately switches ON `fill_density_boost`,
> which is OFF by default. It sews solid fills as two crossing passes instead
> of one, and the fill's routing is where most of these bills land, so both
> the **ranking** and the **percentages** are unverified for customer
> defaults. Nothing has been timed with the boost off. Do not quote these as
> customer digitize time until someone re-runs `flagcost.py` that way. The fill-ANGLE findings further down are
> unaffected: the angle is chosen before the boost branch, from the same row
> spacing, and a re-run of the six turned designs with the boost off gave
> identical angle choices on all 18 design-by-arm sets.

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

Tatami rows sit 0.15 mm apart in this config (`machine.FILL_ROW_MM`, 0.15 since
2026-09-03, × the fabric's `density_adjust`, 1.0 for the default pique; *this
line said 0.4 mm, the pre-2026-09-03 value, until corrected 2026-09-13*), and
the angle search only has to RANK 17
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
| row/32 (0.0047 mm) | **1 / 122** | 1.3× | 244 |
| row/16 | 5 / 122 | 1.4× | 192 |
| row/8 | 8 / 122 | 1.6× | 145 |
| row/4 | 23 / 122 | 1.9× | 105 |
| row/2 | 43 / 122 | 2.2× | 73 |
| row/1 | 69 / 122 | 2.5× | 50 |

*(Two runs of the same deterministic harness: control, row/32, row/16 and
row/8 in the second; row/4, row/2 and row/1 in the first, which had no control.
They share row/8 and agree on it exactly — 8 / 122 both times — and the
search code the control validated is identical in both.)*

The control is clean, so the changes are real. At **0.0047 mm** — a thirty-second
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

## The two flags turn fill rows — measured 2026-09-13

The disproof above showed the fill angle can flip on 0.0047 mm of geometry.
`subpixel_edges` and `curve_turn_deg` move outlines by far more than that, so
the question was whether they already change what ships.

**Method** (`tools/pro_parity/angleflags.py`): every automatic fill-angle
choice across all 23 designs, in three arms — shipped (both on),
`curve_turn_deg` off, both off. Shapes are paired by `shape_id`, falling back
to the nearest centroid within 1 mm and 10% area, because a `shape_id` hashes
the rounded centroid and the flags can rename a shape. Unpaired shapes are
reported and **not counted as turned**, so every count below is a floor.
`machine_lc` is dropped as a duplicate of `machine_hat`.

| shipped vs | shapes | paired | rows turn >10° | share of paired fill area | designs whose ≥200 mm² fill turns |
|---|---|---|---|---|---|
| `curve_turn_deg` off | 117 | 97 | 31 | **41%** | 4 |
| both off | 117 | 95 | 39 | **65%** | **6** |

The six: `gaulke_plowing_hat`, `machine_beanie`, `machine_hat`,
`precision_drone`, `proseal_hat`, `toat_beanie`. The largest turns:

| design | fill | shipped | both off | shipped margin |
|---|---|---|---|---|
| `machine_hat` | 2,790.7 mm² | 90.00° | −2.82° | 3 columns |
| `toat_beanie` | 2,197.2 mm² | 90.00° | −2.90° | 2 |
| `machine_beanie` | 2,176.8 mm² | 90.00° | −2.68° | 3 |
| `precision_drone` | 1,227.4 mm² | 45.00° | 0.00° | 3 |

**These are not near-ties being knocked over.** On each of the four, the
shipped angle beats its runner-up by 2–3 columns. The flags change the
shape's column structure enough to change the winner outright: three badge
backgrounds go from rows just off horizontal (the PCA angle) to exactly
vertical.

**The near-ties are real, but they are mostly small shapes.** Of the 117
shipped choices, 80 are exact column ties decided only by closeness to PCA,
covering 5,512 mm². The 24 choices won by two or more columns cover 11,099 mm²,
which is most of the fill.

**Rendered** (`machine_hat`, flags on vs off): the whole black background runs
vertical as shipped and horizontal with the flags off. `toat_beanie`'s turned
fill is near-white thread, so the line renderer cannot show it; that design is
unconfirmed by eye. The renders also differ in texture, with vertical blocks of
dotted gaps as shipped against horizontal streaks with the flags off. **That is
not read as a defect here.** The renderer draws 1 px lines at 10 px/mm, so its
white gaps are not fabric coverage, and this repo has misread render coverage
before.

**Superseded 2026-09-13 by better renders, all six designs.** Two things made
the first renders misleading, and both are worth knowing before drawing any
fill:
- **They drew the underlay**, which is laid across the top rows and made every
  background read as a crosshatch whichever way the top rows ran.
- **They used the parity config**, whose `fill_density_boost` sews solid fills
  as two crossing passes that customers never get. That second pass was the
  "dotted blocks" texture.

Redrawn in the customer configuration (single-pass fill, top stitching only,
light threads darkened, a 15 mm close-up at 30 px/mm on the densest patch of
the turned fill), the rows are unambiguous. `machine_hat`, `toat_beanie` and
`machine_beanie` sew vertical rows across the whole badge background as
shipped, and horizontal with the flags off. On those three the background sits
around three thin horizontal satin bars, so vertical rows are cut into short
lengths between the bars while horizontal rows run alongside them.
`precision_drone`'s main fill is 45° diagonal against horizontal.
`gaulke_plowing_hat`'s fill is 45° against about 79°. `proseal_hat`'s 11° turn
is barely visible. `toat_beanie` is now confirmed by eye.

**What this does not settle: which rows sew better.** Both flags went on for
edge fidelity (2026-09-03, 2026-09-09), and rotating the main fill was never
part of their case. It is now on the record. Changing either flag or the angle
rule changes shipped output on at least six designs, so it needs a look or a
sew-out, and it is Kent's call.

## Keeping the edge flags but sewing the flags-off rows: two cheap routes, both ruled out — 2026-09-13

Kent looked at renders of the six turned fills and preferred the flags-off
rows. The obvious ask is to keep the flags' smoother edges and choose the fill
angle as if they were off. Both cheap ways to do that fail.

**1. "Keep the principal (PCA) direction unless another angle wins by k
columns."** On the three To-a-T badge backgrounds, the flags-off angle
(≈ −2.8°) is the principal direction and 90° only beats it narrowly, so this
looked promising. It was simulated offline from every candidate's column count
on the shipped outline, across all 23 designs. A control checked the simulation
first: k = 1, today's rule, reproduces the shipped angle on 122 / 122 calls.

| k | big turned fills (≥200 mm², turned >10°) given flags-off rows | shapes changed vs shipped |
|---|---|---|
| 3 | 1 / 7 | 22 / 117 |
| 5–6 | **2 / 7** | 38–42 / 117 (≈7,400 mm²) |

Only the To-a-T badges' flags-off angle is their principal direction.
`machine_beanie` keeps 90° even at k = 6, and the flags-off rows on
`precision_drone` (0°) and `gaulke_plowing_hat` (78.75°) are not principal at
all. The rule fixes 2 of 7 and churns about 40 other shapes.

**2. Choose the angle on the stage-4 outline, before stage 5 reshapes it.**
Measured inside a flags-off run, so shapes pair exactly by `shape_id`, 111 / 111:
the stage-4 outline gives the angle actually sewn on only **58 / 111 shapes, 23%
of fill area**, and on **none of the big fills** (`machine_hat` 78.75° against
−2.82° sewn, `precision_drone` 168.75° against 0°). Stage 5's pull compensation
and overlap clipping move the column counts enough to change the winner. A
faithful flags-off angle therefore needs flags-off stage-5 geometry, and stage 5
reshapes each fill against all its neighbours.

**What is left.** A faithful route has to run a second, flags-off stage 4, the
polygon-dependent passes after it (enclosed-background tagging, thread
revalidation, colour cap, lettering clusters, border layering) and stage 5,
purely to pick angles. Even then coarse and refined shapes pair on only about
81% (95 / 117), and none of it has been timed. The other faithful route is to
turn `subpixel_edges` off. On this 10 px/mm corpus that is identical to both
flags off, because `curve_turn_deg` is gated off without it below 20 px/mm
(`stage4_vectorize.py`). It gives up the edge fidelity both flags were switched
on for.
