# The gradient blend tier never fires on real artwork

*2026-08-15. Asked: how well does EMB-Bot apply gradient treatment — on any
image, not one design. Measured on every gradient-classified fixture in the repo.*

**Verdict up front: 0 of 26 blend-routed regions across three real fixtures were
shaded. Every one fell back to flat tatami. On the synthetic ramps the same code
shades correctly at r2 = 1.000. The tier is not broken — it is inert, because it
requires a region to BE a parametric ramp and real artwork never is.**

The important part is not that it fails. It is that the tonal range is there and
goes unused: `drone_render.png`'s largest region is **53.6% of the design and
carries 69.5 L\* of tonal spread**, and sews as one flat colour.

## 1. What was measured

`stage6_blend.blend_fill` wrapped in a probe (production untouched) to record, per
region: shade count, rejection reason, and the best r2 the decision was made on.
Then `run_stages` + `plan_stitches` over each fixture at 80 mm.

```
fixture                          routed  SHADED   rejected r2: min/med/max   reasons
photo/gradient_ramp_linear.png        2       2   -                          -
photo/gradient_ramp_radial.png        2       1   0.806/0.806/0.806          speckled=1
photo/drone_render.png               15       0   0.003/0.087/0.644          low_r2=14, speckled=1
photo/summit_badge.png                8       0   0.026/0.180/0.642          low_r2=7, speckled=1
photo/repro_gradient_white_icon.png   3       0   0.014/0.036/0.439          low_r2=3
```

`photo/fur_ramp.png` is not routed to the blend tier at all — it classifies
outside `gradient`, which is its own instance of the classifier problem
(`classifier-misroutes-real-logos-2026-08-15.md`).

## 2. This is not a mis-set threshold

`RAMP_R2_MIN = 0.5`, `RAMP_SPECKLE_MAX = 0.35`. The distribution is bimodal with
nothing real on the high side:

- **Synthetic ramps fit at r2 = 1.000 exactly**, both regions of
  `gradient_ramp_linear.png`. By construction — they are ramps.
- **Real content sits at 0.014-0.642**, median ~0.1.

The 0.5 threshold sits in a void. And lowering it would be wrong: a fit
explaining 9% of variance is not a ramp, it is noise. **`r2 = 0.014` on
`drone_render`'s drone body is a CORRECT reading** — a metallic render with glow
halos genuinely is not a linear or radial ramp. The model is wrong for the input,
and no threshold rescues a wrong model.

Note also the second gate. `summit_badge.png`'s body — 2769.9 mm², 60.7% of the
design — DOES clear the r2 gate at 0.642, and is then rejected as `speckled`. So
even the one real region that fits gets refused. Both gates were calibrated where
r2 = 1.000 and speckle ≈ 0.

A region-slicing hypothesis was tested and **rejected**: if quantisation into
colour regions were destroying the ramp, larger regions would fit better. On
`drone_render` the correlation is `r(area, r2) = -0.226` and the largest region
(1648 mm²) has the near-worst fit at 0.014. `summit_badge` does show
`r(area, r2) = +0.772`, so the effect is not absent everywhere — it is just not
the explanation.

## 3. The tonal range is there and is being thrown away

Lab L\* p5-p95 inside each blend-routed region. L\* runs 0-100; roughly 15-20 is
enough for a visible 3-shade split, and below ~8 a region is honestly one tone.

```
fixture                     area mm2      r2   L* spread   outcome
drone_render.png              1648.5   0.014        69.5   flat
drone_render.png               101.7   0.012        58.1   flat
drone_render.png               210.2   0.052        46.5   flat
summit_badge.png              2769.9   0.642        14.0   flat (speckled)
gradient_ramp_linear.png      2340.1   1.000        34.3   shaded (4)

median L* spread, routed regions:  drone 19.5   summit_badge 10.8   synthetic 28.5
```

`drone_render`'s three largest regions carry 69.5, 58.1 and 46.5 L\* of range —
more tonal spread than the synthetic ramp the tier handles happily (34.3) — and
all three sew as a single flat colour. **The blend tier's precondition, not its
capability, is what loses them.**

`summit_badge` is the honest counter-case: median spread 10.8 and its biggest
region only 14.0. There is much less to recover there, and flat fill is closer to
defensible.

## 4. What this suggests, and what has NOT been decided

The remedy direction the measurement points at: **stop requiring a region to be a
parametric ramp before shading it.** Where a region carries real tonal range, band
it by lightness directly — the shade-decomposition and interleaved-emission halves
of `stage6_blend` already work and are proven by the synthetic fixtures; it is
only `detect_ramp_detail`'s gate in front of them that never opens.

**No design decision is made here and nothing was changed.**

### ANSWERED 2026-08-16 — do not redesign this. It is already built.

The four open questions this section originally listed are answered by work
already in the repo, found the day after by reading the history instead of the
code. **A future session should read this subsection before proposing anything.**

**The real blocker is not the gate.** `0923b91` (2026-08-12) recorded it:
`stage7_sequence` never reads `shade_thread_idx` or `shade_rgb`. Both
`stage6_blend` and `stage6_streamline` compute a per-shade chart snap and report
it; nothing consumes it. A block's thread is `group[0].region.thread_index` — the
region's ONE assigned thread — so **every shade of every decomposed region sews in
the same colour.** Verified independently: those names appear only where they are
computed and in `debugviz`. The blend tier has never produced multi-thread shading
in the product, so even the two synthetic regions that "shade" at r2 = 1.000 sew
one thread each.

**Banding inside the fill tier was built, measured, and deleted.** `0923b91` added
`blend_tonal_bands` — lightness bucketing with no ramp fit, exactly the remedy §4
was reaching for. It decomposed the geometry correctly and changed nothing
visible, because the shades still shared one thread. `e460ceb` removed it in
favour of the upstream route rather than keep two mechanisms for one job.

**The chosen route is `split_tonal_regions`** (`stage2_photo_segment.py:1267`,
`cfg.split_tonal_regions`, default False), on a sharper insight than §4 had:
*a region IS the unit that owns one thread*, so no fill-tier trick can produce
colour. It splits tonally-diverse regions before anything reads a region mean, and
each part gets its own spool through machinery that already exists.

Its gates are `TONAL_SPLIT_MIN_AREA_MM2 = 150.0` **and**
`TONAL_SPLIT_MIN_DELTAE = 18.0` — so the "L\* spread floor" §4 wanted already
exists, and the fill-angle and speckle questions are moot because the ramp fit is
not in this path at all.

### The corpus run it was parked on — done 2026-08-16

`split_tonal_regions` carried "opt-in pending a corpus run" for four days. Run on
genuinely tonal inputs (not the 15 real logos, 10 of which are misrouted into this
lane by the classifier bug and are labelled flat):

```
design            regions  threads  stitches  trims
precision_drone       +4       +3      +7%     +6%
drone_render         +10       +3     +10%    +21%
summit_badge          +7       +1      +4%    +48%
```

**Far cheaper than the owl measurement that motivated parking it** (+74% stitches,
trims 33->91). That owl was the worst case: a 4200 mm² body spanning 81 L\*.

On `precision_drone`, the one tonal design with a pro reference: **-2.7**
(37.3 -> 34.6). `coverage` IMPROVES 0.48 -> 0.52, which is what tonal splitting is
for; the loss is `travel` 0.62 -> 0.54 and `sttype` 0.26 -> 0.20, i.e. the split
body's extra entries and exits.

It fires on **exactly one region** on that design — the body, 1039.6 mm², span
80.9 ΔE, the largest span in the corpus. Nothing else clears 150 mm². Lettering is
never split, and the palette GROWS 16 -> 19 rather than being squeezed: 1 of 65
sub-floor regions changed thread. **So the score drop is not text damage or
palette starvation** — two hypotheses tested and rejected here, along with a third
("the gate is area-based") that was simply wrong.

**Status: TABLED by Kent 2026-08-16**, in favour of getting non-gradient artwork
right first. Not rejected — the remaining question is purely whether the split
body reads better by eye, which the scorecard is a poor judge of (it measures trim
economy while the benefit is tonal fidelity). `summit_badge` at +48% trims for +1
thread is the weakest case, so "on for high-span regions only" stays available.

## 5. The pattern this is the second instance of

Both findings today have the same shape, and it is worth naming:

| component | calibrated on | behaviour on real artwork |
|---|---|---|
| `stage0_classify`'s flat/gradient gate | committed fixtures reading <0.0006 | real logos read 0.205-6.135, so 10 of 15 misroute |
| `stage6_blend`'s ramp gate | synthetic ramps fitting at r2 = 1.000 | real content fits at ~0.1, so 0 of 26 shade |

In both cases the component is correct on its calibration set, the calibration set
is far cleaner than customer input, and the result is a capability that is present
in the code and absent in practice. `pro-parity-real-art-2026-08-15.md` is the
third: artwork reconstructed from the pro's own stitches flattered the engine by
11.3 points. **Synthetic references have been flattering this codebase in three
independent places.** Kent's 7 real artworks are the first corrective, and there
are only 7.
