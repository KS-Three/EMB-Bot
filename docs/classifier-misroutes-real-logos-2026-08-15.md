# Stage 0 misroutes 10 of 15 real customer logos to the photo lane

*2026-08-15. Found while diagnosing `bridge_lc`'s perpendicular fills — which
turned out not to be a fill-angle bug at all.*

**Verdict up front: `GRAD_VAR_GRADIENT_MIN` is calibrated on committed fixtures
that are 100-4000x cleaner than real customer artwork. Ten of the fifteen
real-artwork designs classify `gradient` with confidence 1.00 and are routed to
the blend/photo tier. Forcing them `flat` is worth +4.85 each, +3.2 on the
corpus — the largest single lever measured on this corpus. But `flat` is not
simply the right answer for all ten, and the section on that is why this is a
recalibration job and not a one-line threshold change.**

## 1. How this was found

`pro-parity-real-art-2026-08-15.md` §11 turned up `bridge_lc` fill cells scoring
raw 0.19 — worse than chance — and going to 0.81 when rotated exactly 90 degrees.
That looked like a fill-angle convention bug.

It was not. Sweeping `cfg.fill_angle_deg` over 0/15/30/45/60/75/90 and `None`
produced **byte-identical output every time** — same 10395 stitches, same 47.9
score. `bridge_lc`'s fills never reach `stage6_fill`'s angle path, because all 83
of its regions carry `tier=None`: the design is `CLASSIFIED_GRADIENT` and goes
down the photo pipeline, never reaching stage 7's satin/fill ladder.

The angular signature is what a concentric or blend fill looks like against
straight pro rows. In the 271 worst cells:

```
pro angle:  mean  0.3 deg   std 11.3 deg     <- one consistent angle
our angle:  mean -2.8 deg   std 84.6 deg     <- essentially uniform over [-90, 90]
```

## 2. The scale of the misroute

All 15 designs, `stage0_classify.classify()` on the real customer artwork:

```
design                 class      unique_color_mass  gradient_smoothness
becker_hat_large       flat                   0.000                0.000
becker_lc_large        flat                   0.000                0.000
becker_hat_small       flat                   0.000                0.000
becker_chest_small     flat                   0.000                0.000
becker_beanie          flat                   0.000                0.000
hotel_fremont_hat      gradient               0.032                0.311
hotel_fremont_patch    gradient               0.032                0.311
tires_hat_3d           gradient               0.048                0.205
gaulke_roofing_hat     gradient               0.066                4.040
gaulke_roofing_lc      gradient               0.066                4.040
bridge_hat             gradient               0.077                6.135
bridge_lc              gradient               0.077                6.135
mfab_hat               gradient               0.174                1.094
mfab_lc                gradient               0.174                1.094
precision_drone        gradient               0.159                4.463
```

Every one at confidence 1.00. `tires_hat_3d` is a solid black script wordmark.

**The threshold is `GRAD_VAR_GRADIENT_MIN = 0.0015`, and its own calibration
comment records the problem:**

> every flat fixture (including the real enthusiast_logo) <0.0006; every gradient
> ramp and the real drone_render >=0.005.

Real customer logos read **0.205 to 6.135**. That is 137x to 4090x over the
threshold, and 340x to 10000x over the "flat fixture" band the threshold was set
against. This is not a borderline tuning question — the threshold is in the wrong
regime for the inputs the product actually receives.

The five that classify `flat` are the only ones reading *exactly* 0.000 on both
signals: Becker's artwork is a 2-colour PNG with clean alpha at 146x91 px, with
effectively no anti-aliasing to measure. **Ordinary anti-aliased edges are enough
to send a flat logo down the photo lane.**

## 3. What routing them correctly is worth

`cfg.forced_class = 'flat'` on the ten, everything else held (isolated worktree at
`7298ac8`, garment passed, chance-corrected):

```
design                 gradient  forced flat   delta
gaulke_roofing_lc          36.7         44.7    +8.0
hotel_fremont_patch        43.3         51.4    +8.1
gaulke_roofing_hat         35.2         43.1    +7.9
precision_drone            37.3         44.6    +7.3
bridge_hat                 47.7         54.5    +6.8
bridge_lc                  47.9         54.6    +6.7
mfab_lc                    55.7         62.2    +6.5
mfab_hat                   54.7         56.1    +1.4
tires_hat_3d               45.3         45.4    +0.1
hotel_fremont_hat          55.6         51.3    -4.3
MEAN                                            +4.85
```

Better on 8, worse on 1, unchanged on 1. Ten of fifteen designs affected, so
**+3.2 on the corpus: 42.5 -> ~45.7.** Larger than every other lever measured
today (enclosed background +2.7, the PR #146 restore +2.0, garment threading
+0.6) and, unlike `direction`'s 20 points, actually reachable.

## 4. Why this is a recalibration, not a threshold nudge

Two things in the table above rule out simply lowering the threshold or forcing
`flat`:

**`hotel_fremont_hat` regresses -4.3 while `hotel_fremont_patch` gains +8.1 — from
IDENTICAL artwork.** Same file, same signals, same forced class, opposite
outcomes. So a design's correct lane is not a property of the artwork alone in
this measurement; part of each delta is which pro file we are being compared
against. `hotel_fremont_hat` is also the one design in the whole corpus with good
direction agreement (0.58), and forcing flat collapses it to 0.17.

**`gradient_smoothness` does not order the outcomes.** `bridge` reads 6.135 and
wants flat (+6.7). `hotel` reads 0.311 — twenty times lower — and wants blend
(-4.3). If the signal were measuring the right thing, the designs furthest into
gradient territory would benefit least from being forced flat. The ordering is
close to inverted.

So the honest reading: the *routing* is wrong on real artwork, and
`gradient_smoothness` is not discriminative on real artwork either. Recalibrating
the constant against real logos would fix the first without addressing the second.

## 5. What would settle it

- **Recalibrate against real artwork, not fixtures.** The 15 customer logos here
  are the first real-art sample this repo has. Any new threshold should be set on
  them and validated on the committed fixtures, not the reverse.
- **Check whether `gradient_smoothness` survives that.** §4 suggests it may need
  replacing rather than re-thresholding for the flat/gradient gate specifically.
  Its photo/non-photo role (`unique_color_mass`) is untouched by this finding.
- **Expect golden churn.** Ten of fifteen designs changing lane will move any
  golden that pins a gradient-classified fixture. `main` already carries 3
  failures including two `enthusiast_logo.png` goldens.
- **`hotel_fremont_hat` is the counter-example to explain.** Any recalibration
  should say why it keeps the blend tier, or accept the -4.3 knowingly.

## 6. Reproducing

Isolated worktree, so the numbers cannot move underneath the run (see
`pro-parity-real-art-2026-08-15.md` §1):

```
cd .claude/worktrees/parity-measure
PRO_PARITY_OUT=<out> <venv>/python digitizer/tools/pro_parity/prep_both.py
<venv>/python digitizer/tools/pro_parity/scorecard.py <out>/real/*/
```

The classification census is `stage0_classify.classify(art, PipelineConfig())`
per design. The forced-flat comparison sets `cfg.forced_class = 'flat'` and
re-scores against the same untouched `pro_stitches.csv`. Both were throwaway
probes rather than committed tools; the census is three lines and the forced-flat
run is `prep_both`'s `run_ours` body with one extra config line.

## 7. Relationship to earlier work

`photo-quality-root-cause-2026-08-11.md` established that for the three
gradient-classified *fixtures*, segmentation was not the bottleneck and SAM2 would
never engage. This is the adjacent, larger finding: on real customer artwork the
problem is upstream of that — those designs should mostly not be in the gradient
lane at all. That doc's conclusion stands; its population was fixtures.
