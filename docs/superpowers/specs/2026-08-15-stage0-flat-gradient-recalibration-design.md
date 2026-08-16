# Stage 0 flat/gradient gate — scale invariance, and why the threshold cannot be sited yet

**Status: DESIGN SETTLED, BLOCKED ON DATA. Nothing but the failing test in §7 is buildable.**
The problem, the success criterion, the ground truth and four rejected approaches
are settled. The fix is a replacement signal, and its boundary needs more real
gradient artwork than exists — six flat artworks and one gradient is not enough to
site a threshold (§6).

Evidence: `docs/classifier-misroutes-real-logos-2026-08-15.md`. Decisions in this
file were taken with Kent on 2026-08-15 and are marked *(Kent)*.

## 1. The problem, in one measurement

Stage 0 returns **up to three different classes for one image**, depending only on
what resolution it was saved at:

```
                     146px        400px        900px       2000px
becker_hat_large   photo_scene  photo_scene      flat      gradient
hotel_fremont_hat     flat        gradient     gradient    gradient
```

Ten of the fifteen real-artwork designs classify `gradient` at confidence 1.00,
including `tires_hat_3d` — a solid black script wordmark. Ground truth is that
**one** of the seven artworks is genuinely tonal *(Kent)*.

Cause: `_gradient_smoothness` and `_unique_color_mass` are computed on the raw
file with pixel-absolute constants (`GRAD_VAR_WIN = 5`, `CANNY_DILATE_PX = 3`). At
low resolution a 1-px anti-aliased edge is entirely swallowed by the 3-px dilation
and reads as zero variance; at high resolution the transition survives inside the
window and reads as a ramp. So a design's class depends on its export resolution.

**No threshold can be correct while this holds.** That is the whole reason this
spec exists, and it is why "recalibrate the constant" was rejected.

## 2. Success criterion *(Kent)*

**Scale invariance, asserted in tests.** The same artwork must classify the same
way across a resolution sweep. This is chosen deliberately over the parity score:
it is a property of the classifier alone, needs no reference file, does not depend
on the scorecard (whose own ceiling is 75-84, see
`pro-parity-real-art-2026-08-15.md` §11), and is objectively broken today.

Any parity improvement is measured but **not tuned toward**. The +3.2 corpus
points that forcing `flat` predicted is a side effect, not the goal.

## 3. Ground truth *(Kent, 2026-08-15)*

The 15 designs share 7 artworks. Labels:

| artwork | truth |
|---|---|
| Becker Marine | flat |
| Gaulke Roofing | flat |
| Hotel Fremont | flat |
| MFab | flat |
| Tires | flat |
| Bridge Bar | flat |
| Precision Thermal Drone | **gradient / photo** |

So 14 of 15 designs are flat and 1 is not, against 10 of 15 currently routed to
the photo lane.

**`hotel_fremont_hat` is labelled flat even though forcing it flat REGRESSED it
-4.3.** That regression is therefore not a mislabelling and must be explained
separately; it is the one design in the corpus with good direction agreement
(0.58), which collapses to 0.17 when forced flat. Do not treat the regression as
evidence that hotel is tonal.

## 4. Scope *(Kent)*

Both gates must end up scale-invariant, not just the flat/gradient one. Fixing
only flat/gradient would leave `unique_color_mass` resolution-dependent — at 146 px
Becker reads 0.450, over `UCM_PHOTO_MIN = 0.28`, which is why it comes back
`photo_scene`.

Kent's scope choice was "fix the shared cause once, before any signal is
measured." **That framing assumed the shared cause was the pixel-absolute
windows.** §5a and §5c disprove that: normalising the input or the windows fixes
neither invariance nor separability. The shared cause is that these statistics are
computed on raw pixel neighbourhoods at all — so the intent of the scope decision
survives (one change, both gates) but the mechanism is a **replacement statistic
that is invariant by construction** (§6), not a normalisation step in front of the
existing ones.

## 5. Approaches measured and REJECTED

Both were tested, not reasoned about. Recording them so they are not retried.

### 5a. Resample every input to a fixed working resolution — REJECTED

The obvious reading of "pixel-absolute constants" is to fix the pixel count.
Measured, normalising to 1000 px:

```
artwork   truth      gradient_smoothness @1000px working width
mfab      flat              36.25      <- highest in the set
drone     gradient           5.61
bridge    flat               3.26
becker    flat               0.09
separation: OVERLAPS at every source resolution
```

It neither separates nor achieves invariance (becker still flips between 400 and
900 px source). Upsampling introduces LANCZOS ringing, which is itself gradient
variance, so the statistic inflates rather than stabilising.

### 5b. Keep `gradient_smoothness` and re-site its threshold — REJECTED

The statistic does not separate this population **at any scaling**, including
native resolution, where `bridge` (flat) reads 6.135 against `drone` (gradient)
4.463. `mfab_hat`, a flat outlined script, is the highest reading in the corpus.

It is measuring edge and anti-aliasing energy: a busy logo with many thin strokes
scores high, a smooth photograph scores low. **Inverted relative to its intent for
this population.** Its photo/non-photo sibling `unique_color_mass` is not
implicated by this finding and should not be replaced.

### 5c. Size the windows to the image instead of the image to the windows — REJECTED

If pixel-absolute constants are the problem, the principled fix is windows
expressed as a fraction of image width (0.5% window, 0.3% dilation) rather than
5 px and 3 px. Measured, it is **much worse**:

```
                    invariance spread across a 146-2000px sweep
artwork        absolute 5px/3px (shipped)   proportional (candidate)
hotel                        28.9x                     19422.4x
tires                         7.3x                      2437.5x
gaulke                        7.9x                       522.7x
mfab                          7.2x                        54.1x
```

**This is the result that matters most in this spec.** `gradient_smoothness`
cannot be stabilised by rescaling the image (5a) *or* the windows (5c). It already
swings 7-34x on the shipped constants. The instability is in the statistic, not in
how it is sized — which is the same conclusion §5b reaches from separability, now
reached independently from invariance.

**Consequence: the invariance half and the new-signal half are NOT separable.**
An earlier draft of §7 claimed invariance could ship on its own by normalising.
That is false: invariance requires replacing the statistic, and replacing it is
what §6 shows is blocked on data.

## 6. The candidate signal, and the blocker

A scale-invariant colour-diversity statistic — **distinct 3-bit-per-channel
colours needed to cover 90% of foreground pixels**. A fraction of pixels rather
than a pixel count, so it is invariant by construction, and 3-bit quantisation
swallows anti-aliasing and JPEG speckle.

```
                       src146  src400  src900  src2000
tires      flat            2       2       2        2
becker     flat            3       3       3        3
mfab       flat            5       5       5        5
gaulke     flat            5       2       2        2
hotel      flat            6       5       3        2
bridge     flat           17      17      17       17
drone      gradient       22      19      19       20
```

**Invariance: achieved.** Constant across a 14x resolution range on five of seven;
the other two converge as resolution rises.

**Boundary: not sitable.** `flat max 17` against `gradient min 19` — a gap of 2,
resting entirely on `bridge` (the one .jpg, whose compression noise lifts it) versus
`drone`. Bilateral denoising does not help: it pulls `drone` down as much as
`bridge`.

**The blocker is the label distribution, not the signal.** Six flat artworks and
**one** gradient. A single positive example cannot site a boundary. Supplementing
from the repo's synthetic gradient fixtures (`gradient_ramp_linear`,
`gradient_ramp_radial`, `summit_badge`, `drone_render`) would reintroduce exactly
the fixture bias that produced the original miscalibration — that is the
calibration/validation inversion Kent raised at the outset, and it is the reason
this is blocked rather than guessed.

### What would unblock it *(Kent to supply)*

Real customer artwork whose **artwork** carried genuine tonal content — airbrushed
or shaded logos, photo patches, badges with real ramps. Four or five would make a
boundary defensible. Note the requirement is on the artwork, not the stitch file:
the `Embroidery Files` folder holds 45 DST and 16 PES but only 7 artworks, so more
jobs likely have art elsewhere in the business files.

## 7. What can be built before that artwork exists

Per §5c, **not the fix** — invariance cannot be reached without the replacement
signal, and the replacement signal cannot be calibrated yet. Exactly one thing is
buildable now, and it is worth building:

**A regression test that asserts scale invariance.** LANDED as
`digitizer/tests/test_classifier_scale_invariance.py`: **6 passed, 7 xfailed**.

Three things about it differ from how this section was first drafted, each because
building it produced a measurement:

1. **Committed fixtures only, no customer artwork.** The seven real artworks are
   not in the repo and do not need to be — 8 of the 20 committed fixtures already
   flip class across a resolution sweep, so the property is demonstrable on repo
   data alone.
2. **The defect is not universal, so it is declared per fixture.** A first draft
   marked every case `xfail(strict=True)` and five XPASSed. The measured sets are
   now written out: `photo/drone_render.png` and `photo/enthusiast_logo.png` flip
   across the sweep; those two plus `logo_alpha.png`, `logo_whitebg.png` and
   `ribbon_curve.png` depart from their own native class. `photo/summit_badge.png`
   is stable on both counts — and for a reason unrelated to correctness: its
   gradient reading (0.458) sits far enough above the 0.0015 threshold that no
   downscale in range crosses it.
3. **It is not an artifact of the resampler.** `photo/enthusiast_logo.png` is
   `flat` at its native 1400x316 and `gradient` at 500 px under NEAREST,
   BILINEAR, BICUBIC and LANCZOS alike. NEAREST interpolates nothing and posts
   the *highest* reading of the four (23.1). The class also depends on WHICH
   filter was used: at 1000 px NEAREST gives `flat` while the other three give
   `gradient`. Two images a human could not tell apart get different lanes.

A companion test pins the native classifications as a plain passing test, so a
future recalibration that breaks the native answers is caught there instead of
hiding inside an expected failure. `strict=True` throughout: when the defect is
fixed these XPASS, which strict mode reports as a failure, forcing the marker to
be deleted rather than the property silently passing and being forgotten. Their
turning green *is* the acceptance criterion from §2.

Deliberately NOT in scope: changing any threshold, normalising the input,
resizing the windows, replacing `unique_color_mass`, and the `hotel_fremont_hat`
regression (§3) — each rejected or deferred above with a measurement.

## 8. Expected cost when it does land

Ten of fifteen designs changing lane will move any golden pinning a
gradient-classified fixture. Golden re-capture is Kent's call per repo
convention, so the implementation plan must present the churn for approval rather
than re-capturing.

**Judge that churn in CI, not on Windows.** An earlier version of this section
said `main` already carried three failures. It does not — `main` is green
(`gh run list --branch main`, `842d3a1` conclusion `success`). Those three
failures are Windows-only: CI is `ubuntu-latest`, the goldens were captured
there, and on `photo/enthusiast_logo.png` all 31 shape_ids match with 30 of 31
areas identical, one region reading 0.3208 mm² against the golden's 0.3784. The
golden's own capture commit fails locally too, so it was never produced by this
platform. See `pro-parity-real-art-2026-08-15.md` §0b for the full ruling-out.
A recalibration's golden churn is therefore only measurable in CI.
