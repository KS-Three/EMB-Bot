# Stage 0: a scale-relative flat/gradient read (`stage0_scale_relative_grad`, built OFF) — 2026-11-06

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4). The one agreement figure is Cohen's kappa against Kent's labels.
Nothing synthetic sited anything (gate 2): the gate is sited on 15 real flat
customer logos and 21 real tonal artworks. Nothing was sewn (gate 1).
Instrument: `digitizer/tools/stage0_scale_relative.py`; tests:
`digitizer/tests/test_stage0_scale_relative.py` and the ON arm of
`digitizer/tests/test_classifier_scale_invariance.py`.

## 1. What it is

ROADMAP phase 2: one artwork reaches different lanes by export resolution, and
most real logos reach the wrong one. The 08-15 spec
(`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`)
showed the flat/gradient statistic, `gradient_smoothness`, swings 7–34x across
a 146–2000 px sweep and rejected three ways of rescuing it: resample the input
to a fixed width (5a), re-site its threshold (5b), size its windows to the
image (5c). The fix had to be a replacement statistic; colour diversity (§6)
was invariant but its margin was zero once `owl_kent` was enrolled
(DOCTRINE 2026-09-11).

`tonal_frac` is the replacement, built on the recipe that made `texture_frac`
stable (2026-10-28): a SHARE of the foreground, on a fixed 512-px raster,
with hard edges excluded in raster pixels.

- Raster: the long edge INTER_AREA-downscaled to 512 px (`TEXTURE_NORM_PX`);
  a smaller file read as it is.
- A pixel is **tonal** if it is in the texture band (5x5 luminance std in
  [2, 24), more than 2 px from a hard edge — `texture_frac` exactly) **or** on
  a smooth ramp (luminance Gaussian-blurred at sigma 2 slopes >= 0.25 grey
  levels per raster px, std under 2, more than 6 px from a hard edge: the blur
  smears an edge's slope that far).
- Either way it must sit more than 4 px from the **foreground boundary**. This
  is load-bearing: PIL resamples RGBA premultiplied, and the rim pixels of a
  downscaled cut-out come back 1–4 levels off the ink; with the colour
  extension painting the ink outward there is no luminance edge there to
  exclude, so ENTHUSIAST's letter rims read as a ramp — 0.000 at native,
  0.44–0.84 downscaled — until the boundary itself counts as an edge.
- `tonal_frac` = tonal pixels / foreground pixels. Flat art is fills and
  edges, so it reads near zero at any size.

ON, non-photo territory splits `gradient` at `tonal_frac >= 0.11` (margin
0.035). Nothing else moves: the photo gate, `unique_color_mass`,
`texture_frac`'s threshold, the subject/scene split, `gradient_smoothness` and
its threshold are untouched. `tonal_frac` is reported in `signals` under both
arms, so `/classify` shows it today. OFF is the shipped tree (the classes and
confidences are unchanged; `signals` gains the one key).

**Siting.** On the rasters the product sends — the file as uploaded, and the
Studio's 1200-px cap (`PROCESS_MAX_PX`; INTER_AREA / LINEAR / CUBIC, DOCTRINE
2026-09-11) — real flat max is 0.078 (Gaulke, Studio INTER_AREA) and real
tonal min is 0.148 (drone_render, Studio INTER_CUBIC): gate at the midpoint,
half the gap as the margin. A first siting at 0.09 on the LANCZOS ladder alone
left Gaulke 0.007 from the line once BILINEAR and the Studio path were read.

## 2. The corpus

| set | rows | labels |
|---|---|---|
| real flat customer logos | becker, tires, enthusiast, fremont, bridge, gaulke, golden_tee, screenshot, mfab_hat, mfab_lc, toat_beanie, toat_machine, golke_art, fremont_patch (committed); proseal (`scratch_kent/`, local only) | Kent, spec 08-15 §3 and the pro-intake jobs |
| real tonal | drone_render, owl_kent (committed); Instagram_icon (`scratch_kent/`, local only); the 18 Commons photographs | Kent (09-11 owl, 10-27 Commons) |
| unlabelled | the 21 Commons logo styles | none — reported, never counted |
| synthetic | logo_alpha, logo_whitebg, ribbon_curve, summit, the two ramps | measured, never siting |

Rungs per artwork: native; PIL LANCZOS / BILINEAR / NEAREST at 146, 250, 400,
640, 1000, 1200, 2000 px, downscales only; the Studio cap where the file is
over 1200 px. 651 labelled real rasters in all. Each raster is classified
once (flag ON, which computes every signal) and the OFF class re-derived from
the same signals with the module's own gates; the re-derivation is checked
against a real OFF `classify` at every native rung.

## 3. Results

### 3a. Spread across the ladder (done-test 1)

The ratio spread is the 08-15 spec's measure. On a flat row `tonal_frac` sits
at or near zero, where a ratio means nothing — the property there is the
absolute max staying under the gate.

| artwork | label | `gradient_smoothness` spread | `tonal_frac` spread | `tonal_frac` range | classes OFF | classes ON |
|---|---|---|---|---|---|---|
| tires | flat | 9.8x | — | 0.000–0.000 | flat, gradient | flat |
| enthusiast | flat | inf (min 0) | — | 0.000–0.034 | flat, gradient | flat |
| fremont | flat | 17,808x | — | 0.000–0.036 | gradient, photo_scene, photo_subject | flat, photo_scene, photo_subject |
| bridge | flat | 7.7x | — | 0.000–0.014 | gradient | flat |
| gaulke | flat | 32.6x | — | 0.000–0.083 | flat, gradient, photo_scene | flat, photo_scene |
| golden_tee | flat | 31.5x | — | 0.000–0.022 | gradient | flat |
| screenshot | flat | 7.2x | 1.5x | 0.032–0.050 | gradient | flat |
| mfab_hat | flat | 4.8x | — | 0.001–0.067 | flat, gradient, photo_scene | flat, photo_scene |
| mfab_lc | flat | 3.1x | — | 0.000–0.065 | flat, gradient, photo_scene | flat, photo_scene |
| toat_beanie | flat | 1.8x | — | 0.006–0.073 | flat, gradient | flat |
| toat_machine | flat | 3.3x | — | 0.000–0.065 | gradient, photo_scene | flat, photo_scene |
| golke_art | flat | 9.2x | — | 0.000–0.019 | gradient | flat |
| fremont_patch | flat | 201x | — | 0.000–0.034 | gradient, photo_scene | flat, photo_scene |
| proseal | flat | 3.6x | — | 0.000–0.001 | gradient | flat |
| becker | flat | (146 px native: one rung) | — | 0.000 | flat | flat |
| drone_render | tonal | 8.2x | 32x | 0.006–0.188 | gradient | flat, gradient |
| owl_kent | tonal | 1.9x | 1.4x | 0.507–0.684 | photo_scene | photo_scene |
| Instagram_icon | tonal | 24.3x | 1.3x | 0.230–0.294 | gradient | gradient |
| 18 Commons photographs | tonal | 1.5–9.3x | 1.2–3.8x (stained_glass 10.3x at NEAREST 146) | min 0.036, else >= 0.132 | | |
| summit / ramp_lin / ramp_rad | synthetic | 6.6x / 60x / 23.5x | 1.3x / 1.1x / 1.2x | | | |

Every `photo_*` that remains on a flat row ON is the photo gate
(`unique_color_mass` at 146–250 px, and two `legacy` cut-out reads on Fremont
at 146) — the other half of the 09-20 "two defects", outside this flag.

**The scale test's four DEPARTS_FROM_NATIVE fixtures** (logo_alpha,
logo_whitebg, ribbon_curve, enthusiast) read `flat` at every rung ON, all
three filters included. The ON-arm tests assert the strict xfails XPASS; the
OFF arm stays marked.

One class at every rung: real labelled 9 of 18 OFF → 11 of 18 ON (the rest
are the photo gate and the drone); synthetic 0 of 6 → 3 of 6; Commons logos
14 → 16 of 21; Commons photographs 14 → 14 of 18 (unchanged — their
variation is the photo gate's confidence floor at NEAREST 146–400).

### 3b. Tonal positives stay tonal; the margin (done-test 2)

| rungs | tonal set | real tonal artworks | flat max | tonal min | gap |
|---|---|---|---|---|---|
| native + Studio path | all | 21 | 0.078 (gaulke, Studio INTER_AREA) | 0.148 (drone, Studio INTER_CUBIC) | **+0.070** |
| native + Studio path | without drone_render | 20 | 0.078 | 0.234 (watercolor, native) | +0.156 |
| + downscales >= 400 px | all | 21 | 0.083 (gaulke, BILINEAR 1000) | 0.062 (drone, NEAREST 400) | −0.020 |
| + downscales >= 400 px | without drone_render | 20 | 0.083 | 0.207 (fireworks, NEAREST 400) | +0.125 |
| every rung | all | 21 | 0.083 | 0.006 (drone, NEAREST 146) | −0.077 |
| every rung | without drone_render | 20 | 0.083 | 0.036 (stained_glass, NEAREST 146) | −0.047 |

`owl_kent` is enrolled throughout and is nowhere near the line (min 0.507);
it was the row that zeroed colour diversity's margin.

**Chance-corrected agreement with Kent's labels** (tonal = any non-flat class):

| rasters | n | kappa OFF | kappa ON | flat routed non-flat OFF → ON | tonal routed flat OFF → ON |
|---|---|---|---|---|---|
| native only | 36 | +0.152 | **+0.942** | 13/15 → 1/15 | 0/21 → 0/21 |
| native + Studio path | 111 | +0.162 | **+0.978** | 29/33 → 1/33 | 0/78 → 0/78 |
| downscales only | 540 | +0.145 | +0.893 | 153/174 → 15/174 | 3/366 → 10/366 |
| all | 651 | +0.148 | +0.907 | 182/207 → 16/207 | 3/444 → 10/444 |

The seven tonal rasters ON loses are all the drone at 146–400 px; the three
both arms lose are photographs demoted by the photo gate's confidence floor
at NEAREST 146–400.

### 3c. Real flat customer logos routed off the flat lane (done-test 3)

| artwork | native OFF | native ON | Studio OFF | Studio ON | downscales non-flat OFF → ON |
|---|---|---|---|---|---|
| becker | flat | flat | flat | flat | (146 px native) |
| tires | gradient | flat | gradient | flat | 15/18 → 0/18 |
| enthusiast | flat | flat | flat/gradient | flat | 6/18 → 0/18 |
| fremont | gradient | flat | gradient | flat | 21/21 → 2/21 |
| bridge | gradient | flat | gradient | flat | 6/6 → 0/6 |
| gaulke | gradient | flat | gradient | flat | 17/18 → 1/18 |
| golden_tee | gradient | flat | gradient | flat | 21/21 → 0/21 |
| screenshot | gradient | flat | gradient | flat | 15/15 → 0/15 |
| mfab_hat | photo_scene | photo_scene | photo_scene | photo_scene | 6/9 → 5/9 |
| mfab_lc | gradient | flat | gradient | flat | 5/6 → 4/6 |
| toat_beanie | gradient | flat | gradient | flat | 5/6 → 0/6 |
| toat_machine | gradient | flat | gradient | flat | 6/6 → 2/6 |
| golke_art | gradient | flat | gradient | flat | 9/9 → 0/9 |
| fremont_patch | gradient | flat | gradient | flat | 6/6 → 1/6 |
| proseal | gradient | flat | gradient | flat | 15/15 → 0/15 |

**At native: 13 of 15 off the flat lane OFF (12 `gradient`, MFab hat
`photo_scene`) → 1 of 15 ON (MFab hat, the photo gate).** Every remaining ON
misroute on a downscale is `photo_scene` from `unique_color_mass`, not this
gate. The spec's seven-artwork set (Becker, Gaulke, Fremont, MFab, Tires,
Bridge, Golden Tee): 6 of 7 non-flat at native OFF → 1 of 7 ON (MFab).

### 3d. The unlabelled Commons logos (Kent's eye, not a score)

OFF `gradient` → ON `flat` at every rung: arabic_calligraphy, heraldic_crest,
flat_emoji_icon, silhouette_logo, distressed_grunge, gradient_mascot (Tux;
the 10-27 census calls it flat-shaded), outline_lineart_logo, low_poly,
pixel_art_sprite, devanagari_logo. `isometric_icon` (a photoreal render) stays
`gradient`. These rows have no label; whether each is right is Kent's call.

## 4. Stated limits

1. **The drone at 400 px and below.** At that size the badge is ~150 px
   across and its photo inset is mostly hard-edge pixels (43% of the
   foreground at native already), which the exclusion removes: 0.113 at
   LANCZOS 400 (under the gate's confidence floor), 0.072 at 250, 0.006 at
   NEAREST 146. Native and Studio read 0.148–0.157 (`gradient`). Pinned as an
   executable record in the scale test.
2. **Upscales are not measured as acceptance** (the scale test's rule: an
   upscale invents interpolation). Measured in the prototype: a 377-px TOAT
   file LANCZOS-upscaled to 1000–2000 px reads ~0.11, at the gate — its edges
   become 3–5 px ramps. The Studio never upscales before sending; a customer
   who uploads an upscaled export would meet this.
3. **The photo gate is untouched**, so its own scale defect remains: MFab,
   TOAT machine, Gaulke and Fremont reach `photo_scene` at 146–250 px through
   `unique_color_mass`. That is the other half of DOCTRINE 2026-09-20's "two
   defects" and not this flag's to fix.
4. **barcode** (unlabelled) reads 0.031–0.484 and crosses lanes either way;
   its bars blur to texture when small, the texture gate's stated limit too.

## 5. Cost

`tonal_frac` runs on the 512-px raster: one Gaussian blur, two Sobels, three
dilations — 24 ms on golden_tee (2193 px) and 12 ms on drone_render
(1536 px) against `texture_frac`'s 17 and 8 ms on Kent's laptop, next to
`unique_color_mass`'s seconds. Computed under both arms.

## 6. Flip proposal (Kent's call)

**Proposed: flip `stage0_scale_relative_grad` ON.** It delivers the phase-2
property on the flat/gradient gate: kappa against Kent's labels +0.162 →
+0.978 on what the product sends, 13 of 15 real flat logos off the flat lane
at native → 1 (that one is the photo gate), no real tonal raster lost at
native or through the Studio, the four strict xfails XPASS.

The catch, in order:

- **Goldens move.** Most real-art designs are gradient-classified today; ON
  they route flat, so every golden and pin on a gradient-classified real
  logo changes (the 08-15 spec §8 predicted 10 of 15 designs). Re-capture is
  Kent's per repo convention, judged in CI, not on Windows.
- **`hotel_fremont_hat` regressed −4.3 when forced flat** (spec §3) and will
  reach flat ON. That regression is unexplained and labelled not-a-mislabel;
  this flag does not address it.
- **The drone flips at <= 400 px** (limit 1).
- The photo gate's own scale defect stays (limit 3).

Not proposed for DOCTRINE as a negative: the candidate separated. Proposed
for DOCTRINE instead: *an alpha boundary is an edge with no luminance step —
exclude the foreground rim as well as hard edges, or a premultiplied resample
reads as a ramp* (the ENTHUSIAST 0.000 → 0.84 finding, §1).
