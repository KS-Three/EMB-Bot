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

## The gap

- **`subpixel_edges` (+48.4%) and `curve_turn_deg` (+32.1%) document no
  runtime cost at all.** Their `config.py` blocks are long and careful about
  quality trade-offs; neither mentions the clock. Both now carry the measured
  number.
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
