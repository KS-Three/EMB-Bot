# Why the flat script wordmark routes to the photo lane — 2026-09-11

**Verdict: a genuine misclassification, not a borderline call — and the pixels
doing it are not the lettering. 97% of the signal that crosses the photo gate
comes from the white BACKGROUND, which carries a grain of ±1 grey level that
no eye can see.** The artwork is `digitizer/testdata/logo_script_tires.png`,
Kent's real customer logo, labelled `flat` in his own ground truth (08-15 spec
§3). Stage 0 calls it `photo_scene` at confidence 1.000.

Gate-2 clean: **this measures and changes nothing.** No threshold was moved and
none is proposed for moving — §8 says why no pair of thresholds can fix it.

Instrument: `digitizer/tools/stage0_signal_origin.py` (committed with this
doc), `digitizer/tests/test_stage0_signal_origin.py`. Windows, the main
checkout's venv, worktree code shadowing it. Reproduce with

```
cd digitizer && .venv/Scripts/python tools/stage0_signal_origin.py \
    testdata/logo_script_tires.png --ablations --sweep
```

## 1. Reproduced, and it is not near the line

| fixture | unique RGB | `unique_color_mass` | `gradient_smoothness` | class |
|---|---:|---:|---:|---|
| **`logo_script_tires.png`** | **5,581** | **0.3608** | **0.0798** | **photo_scene** (conf 1.000) |
| `logo_whitebg.png` | 54 | 0.0049 | 0.00056 | flat |
| `logo_alpha.png` | 54 | 0.0088 | 0.00006 | flat |
| `becker_marine_logo.png` | 2 | 0.0000 | 0.00000 | flat |
| `bg_uncertain.png` | 6 | 0.0030 | 0.00107 | flat |
| `ribbon_curve.png` | 17 | 0.0041 | 0.00003 | flat |

Gates: `UCM_PHOTO_MIN = 0.28` (photo vs not), then `GRAD_VAR_SUBJECT_MIN = 8.0`
picks subject vs scene, so 0.0798 lands on `scene`. **`unique_color_mass` is
the signal that routes it**; `gradient_smoothness` only chooses which photo
class. The comparables are not a different kind of artwork — they are a
different kind of FILE: 2 to 54 exact colours against 5,581.

## 2. It is the background, measured three ways

**By zone** (Otsu boundary, ±3 px counted as the anti-aliased band):

| zone | share of image | disagrees with its own 3×3 mode | share of ALL disagreement |
|---|---:|---:|---:|
| background interior | 90.6% | 38.7% | **97.1%** |
| ink interior | 7.1% | 0.8% | 0.2% |
| edge band (AA + halo) | 2.3% | 41.9% | 2.7% |

The background interior reads grey **253.00 ± 0.75**, 216 distinct colours,
p1–p99 = 251–254. That is the whole of what stage 0 is reacting to.

**By what the quantize spends its centres on.** `unique_color_mass` runs a
throwaway k-means at a FIXED k=16 and counts pixels whose label differs from
their 3×3 neighbourhood mode. On a two-colour design there is nothing for
fourteen of those centres to describe, so **five of the sixteen land inside
the white ground** (L\* 98.86, 99.24, 99.31, 99.44, 99.66 — 14.4%, 13.7%,
37.4%, 8.9%, 17.2% of the image). Their pairwise CIEDE2000 is **0.20 to 1.02**.
The repo's own `preflight.DELTA_E_VISIBLE` is **5.0**. The statistic is
splitting one colour into five and then reporting that neighbouring pixels
disagree about which it is.

**By ablation** — one property changed per arm, class across 8 seeds:

| arm | UCM | GS | classes |
|---|---|---:|---|
| original | 0.196–0.361 | 0.0798 | gradient 6, photo_scene 2 |
| **background interior → its median** | **0.011–0.017** | 0.0564 | gradient 8 |
| ink interior → its median | 0.243–0.378 | 0.0933 | photo_scene 6, gradient 2 |
| both interiors flat, AA kept | 0.010–0.013 | 0.0699 | gradient 8 |
| **AA band hardened, grain kept** | **0.402–0.423** | 0.0532 | photo_scene 8 |
| binarized (no AA, no grain) | 0.0000083 | 0.00000 | flat 8 |
| clean AA only (flat interiors, σ 0.8) | 0.011–0.014 | **0.7207** | gradient 8 |

**The plausible culprit was wrong.** Anti-aliased curves and thick brush
strokes do not cause this: removing the anti-aliasing RAISES `unique_color_mass`
to 0.423, and a clean anti-aliased edge over flat interiors contributes 0.011.
A synthetic control makes the sufficiency explicit — a hard two-colour render
with ±1 grey level of noise on the ground alone reads 0.459 and classifies
`photo_scene` on every seed (`test_one_grey_level_of_invisible_noise_crosses_
the_photo_gate`). *(That arm is a MECHANISM control and is used as nothing
else: gate 2 bars synthetic fixtures as calibration substitutes.)*

Provenance of the grain is not recoverable — the PNG carries no metadata, and
there is no 8×8 JPEG grid left in it (boundary step 0.524 against 0.549
elsewhere). What is visible is spatially-correlated ±1–2 level grain plus a
clipped-white halo along every stroke, i.e. a lossy or resampled original that
was sharpened. **The customer file is ordinary. Nothing is wrong with it.**

## 3. The verdict is a coin flip that prints confidence 1.000

`unique_color_mass` depends on where k-means++ seeds its centres:

```
seed   0      1      2      3      4      5      6      7      8      9     10     11
UCM  .361   .210   .328   .247   .252   .264   .203   .196   .206   .349   .284   .361
     PHOTO   -     PHOTO   -      -      -      -      -      -     PHOTO  PHOTO  PHOTO
```

**5 of 12 seeds cross the gate, 7 do not**, and the default seed 0 happens to
be the maximum of the twelve. The spread (0.165) is twice `UCM_MARGIN` (0.08),
which is the distance `_gate_confidence` treats as "clear of the threshold" —
so the printed 1.000 is the distance of ONE draw from the gate, not a
stability claim. **Do not read a stage-0 confidence as reproducibility.**

## 4. Even with the grain gone, it is still not `flat`

`gradient_smoothness` is a second, independent failure on the same artwork.
With interiors held exactly flat and only a real anti-aliased edge present, it
reads **0.7207 — 480× `GRAD_VAR_GRADIENT_MIN` (0.0015)** — and at σ 1.5,
2.024. Only a hard binarization reaches 0.0. This is the mechanism
`classifier-misroutes-real-logos-2026-08-15.md` §2 named ("ordinary
anti-aliased edges are enough") and the 08-15 spec §5b measured as inverted for
this population; the clean control above is new evidence for it, with the
interior noise removed so the AA half can be read on its own.

**Consequence: fixing the photo gate alone moves this design from
`photo_scene` to `gradient`, not to `flat`.** Both gates have to go.

## 5. One file, three classes, depending on export size

PIL LANCZOS, as `tests/test_classifier_scale_invariance.py` resamples:

| width | UCM (8 seeds) | GS | classes |
|---:|---|---:|---|
| 146 px | 0.046–0.097 | 0.1336 | gradient 8 |
| 250 px | 0.049–0.184 | 0.1075 | gradient 8 |
| 400 px | 0.105–0.307 | 0.0980 | gradient 7, photo_scene 1 |
| 640 px | 0.123–0.399 | 0.0839 | photo_scene 4, gradient 3, flat 1 |
| 900 px | 0.232–0.402 | 0.0885 | photo_scene 5, gradient 2, flat 1 |
| 1585 px (native) | 0.196–0.361 | 0.0798 | gradient 6, photo_scene 2 |
| 2000 px (up) | 0.142–0.282 | 0.1458 | gradient 6, flat 2 |

**Every `flat` in that table is the `CLASSIFICATION_UNCERTAIN` fallback, not a
flat reading** — by construction, since GS is ≥ 50× the gradient gate at every
width, so a non-photo verdict can only be `gradient` unless the photo gate's
confidence falls under `CONFIDENCE_FLOOR` and the result is discarded for the
safe default. The artwork reaches the right answer only by the classifier
admitting it does not know. This is ROADMAP phase 2's exit condition, on one
file.

## 6. What it costs today: nothing on the stitches, one wrong sentence on screen

Three arms, changing only `cfg.forced_class` (the shipped user override), same
scorer (`tools/artfidelity_self.score_image`):

| route | ARTFID | coverage | structure | stitches | trims | thread | preflight |
|---|---:|---:|---:|---:|---:|---:|---|
| `photo_scene` (default) | 85.7 | 0.794 | 0.828 | 2,345 | 12 | 8.45 m | B 88 |
| `gradient` | 85.7 | 0.794 | 0.827 | 2,327 | 13 | 8.36 m | B 88 |
| `flat` | 85.7 | 0.794 | 0.827 | 2,332 | 13 | 8.37 m | B 88 |

The satin is identical in all three (1,107 stitches over 5 runs); 6 regions, 1
cone, 2 blocks throughout. **So the misroute is currently free on the
stitches** — consistent with the 08-15 forced-flat sweep, where `tires_hat_3d`
was the one design that barely moved (+0.1).

Two things it is not free of:

- **The Studio tells the customer the wrong thing.** `CLASSIFIED_PHOTO_SCENE`
  renders as *"The art reads as a photographic scene. Photos sew rougher than
  flat artwork — check the preview closely before stitching this one out."*
  for a two-colour script wordmark. The panel does offer the flat-art nudge
  (`offerFlat`), so the customer can override — the copy is wrong, the escape
  hatch works.
- **The table above is the lane WITHOUT the cutout.** This box had no
  `rembg_isolated/venv`, so that run logged `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`
  and, per the 2026-08-24 ruling, skipped the whole photo-prep block —
  byte-identical to `photo_prep=False`. A customer on a provisioned service
  gets the other arm, so it was built and measured (§6a).

### 6a. The cutout arm, measured — also benign

Built `rembg_isolated/venv` (python3.12, `rembg==2.0.77`, `onnxruntime==1.28.0`;
pip resolved numpy 2.5.3 with numba 0.67.0, so **the README's numba-vs-numpy-2.5
conflict has aged out** — worth knowing before anyone re-probes it). Model
`isnet-general-use.onnx` cached, 6.0 s on this artwork.

With the cutout available the run reports `PHOTO_BACKGROUND_REMOVED`,
`PHOTO_PREP_APPLIED` and `TONAL_REGIONS_SPLIT` — the full photo machinery,
including the tonal split:

| arm | ARTFID | coverage | structure | stitches | trims | thread |
|---|---:|---:|---:|---:|---:|---:|
| `photo_scene` + rembg + tone/texture prep | **86.2** | 0.801 | 0.834 | 2,287 | 12 | 8.15 m |
| `flat` | 85.7 | 0.794 | 0.827 | 2,332 | 13 | 8.37 m |

**Still no damage — if anything marginally better** (+0.5 ARTFID, 45 fewer
stitches, 0.22 m less thread), and the renders of the two arms are the same
design: one black cone, script fully legible, letterforms intact. The tonal
split fires but produces no second cone. So the misroute is benign in BOTH
provisioning states, which is the stronger version of the claim — and the
reason this stays an investigation rather than a bug report.

Read the +0.5 as a wash, not a win: it is one design, and this document's own
§7 records that ARTFID is not a route-neutral instrument.

## 7. What it costs the measurements

- **ARTFID is not inflated here.** The route-comparability finding in
  `docs/artfid-eye-agreement-2026-09-11.md` §3 (gradient/photo designs scoring
  higher than they look) does **not** apply to this fixture: all three routes
  score 85.7. The 85.8 in that table is an honest number.
- **But its route LABEL is wrong, and that touches §3's own analysis.** That
  doc files `logo_script_tires` in the non-flat stratum while its stitches are
  flat-lane equivalent. Relabelling it strengthens the finding rather than
  weakening it: `route == flat` vs the eye goes **tau +0.575 (p 0.014) →
  +0.704 (p 0.003)**, and ARTFID still beats preflight grade inside both
  strata (+0.333 vs +0.126 flat; +0.524 vs −0.066 non-flat). §3's conclusion
  survives; its numbers move. *(Exploratory, n=14, and the "eye" there is
  Claude's — every caveat in that document still applies.)*
- **The 08-15 census row for this design does not reproduce.** It recorded
  `tires_hat_3d` at `unique_color_mass` 0.048, `gradient_smoothness` 0.205 →
  `gradient`. The artwork it measured (`G:/…/TIRES/Tires Logo.png`) is
  **md5-identical to the committed fixture** (`6f7bbf87cc86b4385693e23423ede788`),
  and `gradient_smoothness` contains no RNG — yet no width in §5 reproduces
  0.205. That probe was never committed, so what raster it fed cannot now be
  recovered. **Treat that one row as unattributed; the rest of the census
  matches today's code** (e.g. `precision_drone` 0.159 = `drone_render` today).
  This is why the tool above is committed rather than left in a scratch
  directory.

## 8. Why no threshold move can fix this

Stage 0's photo gate, run over every real artwork in the repo today:

| fixture | UCM | class | what it is |
|---|---:|---|---|
| **`logo_script_tires.png`** | **0.3608** | photo_scene | flat two-colour wordmark |
| `photo/drone_render.png` | 0.1592 | gradient | real tonal logo |
| `photo/summit_badge.png` | 0.1152 | gradient | synthetic badge |
| **`photo/owl_kent.jpg`** | **0.1107** | gradient | **a real photograph** |
| `photo/logo_bridge_bar.jpg` | 0.0352 | gradient | real flat logo |
| `photo/logo_hotel_fremont.webp` | 0.0320 | gradient | real flat logo |
| `photo/logo_gaulke_roofing.png` | 0.0103 | gradient | real flat logo |
| `photo/logo_golden_tee.jpg` | 0.0076 | gradient | real flat logo |
| `photo/enthusiast_logo.png` | 0.0000 | flat | real flat logo |
| `photo/photo_scene_stub.png` | 0.4256 | photo_scene | SYNTHETIC stub |

**The only real artwork in the corpus that crosses the photo gate is the
flattest one, and it scores 3.3× the real photograph.** A threshold high
enough to exclude it (>0.36) sits above every real input including the
photograph, making the photo classes unreachable for real artwork; the
ordering is inverted, so no re-siting separates these populations. Same shape
of result as the 08-15 spec reached for `gradient_smoothness` (§5b), now
measured for its sibling.

**That is a correction to the spec**, which wrote: *"Its photo/non-photo
sibling `unique_color_mass` is not implicated by this finding and should not
be replaced."* It is implicated — for a different reason than
`gradient_smoothness` (no perceptual floor, rather than measuring edge energy),
and with the extra defect that its reading is not reproducible across seeds.

## 9. What this licenses, and what it does not

- **Does not license moving a threshold** (ROADMAP gate 2, and §8 says it
  would not work anyway). Nothing here is a recalibration.
- **Supports the already-specified fix and sharpens its scope.** The 08-15
  spec's candidate signal reads this artwork **2** at 400/900/1585/2000 px
  (`bbox`), against a flat max of 16 and a tonal min of 20 — correct and
  stable. Plan §5a's PR 6a says the replacement lands for the flat/gradient
  gate and *"the photo gate follows the same construction"*. **For this
  fixture that second clause is load-bearing, not a nicety**: it exits at the
  photo gate and never reaches the flat/gradient one, so a PR 6a that ships
  only the first half leaves it misrouted (as `gradient` — see §4).
- **Does not change the blocker.** PR 6a still needs Kent's 3–5 real tonal
  artworks (`docs/stage0-signal-decision-2026-09-11.md` §3a). This adds a
  reason the fix is worth having, not permission to site the boundary.
- **Leaves the fixture where it is.** `logo_script_tires.png` is kept
  precisely because it is the bug's fixture (`docs/scope/1-auto-digitizing-
  quality.md`); it now has a tripwire asserting the property the fix must
  deliver, xfail(strict) so it reports the day it passes.

## 9a. Is the grain mechanism general? No — and what IS general is worse

Same probe over every real artwork in the repo, 4 seeds per arm. "UCM share"
is where the disagreeing pixels sit; "binarized" is the arm with all
anti-aliasing AND all grain removed — the cleanest two-colour version of the
same artwork that exists.

| fixture | class | UCM | GS | UCM share bg/ink/edge | binarized → |
|---|---|---:|---:|---|---|
| **`logo_script_tires`** | **photo_scene** | **0.361** | 0.080 | **97 / 0 / 3** | **flat** (0.0000) |
| `logo_hotel_fremont` | gradient | 0.032 | 0.311 | 33 / 0 / 67 | gradient (0.0337) |
| `logo_gaulke_roofing` | gradient | 0.010 | 0.615 | 3 / 0 / 97 | gradient (0.0091) |
| `logo_golden_tee` | gradient | 0.008 | 0.082 | 20 / 6 / 74 | gradient (0.2455) |
| `logo_bridge_bar` | gradient | 0.035 | 2.539 | 1 / 0 / 99 | gradient (0.0850) |
| `enthusiast_logo` (α) | flat | 0.000 | 0.000 | — | flat (0.0000) |
| `becker_marine_logo` (α) | flat | 0.000 | 0.000 | — | flat (0.0000) |
| `owl_kent` (real photo) | gradient | 0.111 | 1.288 | 33 / 9 / 58 | gradient (1.8855) |
| `drone_render` (real tonal, α) | gradient | 0.159 | 4.463 | 10 / 21 / 70 | gradient (18.4) |

Three things fall out, and two of them are new:

- **The grain mechanism is `logo_script_tires`'s alone.** It is the only
  fixture whose disagreement mass sits in the ground (97% against 1–33%
  elsewhere) and the only one that crosses the photo gate at all. Everywhere
  else the mass is in the EDGE BAND and the misroute is the flat/gradient
  gate. So §2 explains one fixture; it does not restate the corpus.
- **Binarizing rescues only `tires`.** Strip every soft pixel and every noisy
  one from the other four real logos and they STILL read `gradient` — at 6×,
  22×, 57× and 164× the gate. **That revises the 08-15 reading.** *"Ordinary
  anti-aliased edges are enough to send a flat logo down the photo lane"* is
  true and incomplete: for four of five real logos, the artwork's GEOMETRY
  alone — many fine strokes, hence many edges Canny's dilation cannot fully
  exclude — clears the gate with no anti-aliasing present at all. A
  replacement signal has to survive that, not merely be noise-tolerant.
- **The two real logos that DO route `flat` are flat by file format, not by
  artwork.** Both are alpha PNGs, and `_gradient_smoothness` Sobels the RGB
  grey only — it never reads alpha. Their edge softness is in the channel the
  signal ignores (`becker` `alpha_softness` 0.174, `enthusiast` 0.019, RGB
  down to 2 and 3 colours respectively), so they read exactly 0.0000 on both
  signals. That also explains why `enthusiast_logo` sits in the scale test's
  `DEPARTS_FROM_NATIVE` set: downsampling blends that alpha softness into RGB,
  where the signal can suddenly see it, and the class changes with no change
  to the artwork.

*(measured 2026-09-11 — `tools/stage0_signal_origin.py --ablations`, 4 seeds)*

### 9a-bis. The candidate signal, stressed on the same two populations

§9a says a replacement has to survive GEOMETRY, not merely tolerate noise. So
the 08-15 spec's candidate (`tools/color_diversity.py`) was put through both
tests. Kent's call, 2026-09-11.

**Geometry: it passes, cleanly.** Run on each logo's binarized twin — pure
geometry, no soft pixel and no noisy one — every real logo reads **1 or 2**,
including the four whose shipped `gradient_smoothness` stays 6–164× over its
gate after the same binarization. The failure mode that breaks the shipped
signal does not transfer to the candidate. That is real de-risking for PR 6a,
available before any new artwork lands.

**Photographs: the margin collapses to zero, and this one needs Kent.** The
09-11 measurement reports flat max **16** (`bridge`) against tonal min **20**
(`drone`), gap +4. Enrol `photo/owl_kent.jpg` — the repo's only REAL
photograph — as a real tonal positive and the tool's own verdict becomes:

```
  flat max    16  (bridge)
  tonal min   16  (owl_kent)
  gap          0  — the classes OVERLAP
  across the sweep: the classes separate at NO of the rungs every artwork reaches
```

The plan's §5a leaves *"whether photographs may serve as positives for a
flat/gradient boundary"* open as a question for Kent. **This is the number
that question is worth: if they count, the candidate does not order the
classes on today's corpus either** — so the +4 gap must not be quoted as
though photographs were in the tonal set.

Two honest limits on that. `owl_kent.jpg` is a 554 px re-save (it carries no
EXIF for the same reason), and a downscaled re-encode is not a
full-resolution photograph, so this is a caution rather than a refutation.
And it is one positive: n=2 tonal rows still fails the spec's own four-row
floor, which the tool says itself.

Worth noting either way: **`color_diversity`'s corpus enrols the SYNTHETIC
owl (`photo/photo_owl_pale.png`, excluded from the margin as gate 2 requires)
and not the real one**, which is committed two directories away and is the
artwork this repo cites whenever it needs a real photograph.

One instrument note, since §9b is about exactly this: `sweep()` reads with
`cv2.IMREAD_COLOR`, which drops alpha, while its own `foreground()` honours
alpha through `prep`. For the four alpha fixtures the two entry points
therefore disagree — `drone_render` reads 20 through the tool and 25 when its
alpha survives. Every number quoted here is the tool's own (no alpha), which
is also what the 08-15 table measured; the disagreement is flagged rather than
fixed, because changing it would move the numbers PR 6a will be sited on.

*(measured 2026-09-11 — `tools/color_diversity.py --foreground bbox`, plus
`--art testdata/photo/owl_kent.jpg --label tonal --provenance real`)*

### 9b. A defect in this document's own instrument, found by its own output

The first corpus run reported `enthusiast_logo` as `flat` in its header and
`gradient` in its very next line — the same pixels, two answers. Cause: the
probe rebuilt each ablation arm as a THREE-channel array, and `_fg_mask` calls
alpha ≤ 127 background, so every transparent pixel was silently promoted to
foreground and the arms measured an image nobody digitizes. Four of the nine
fixtures carry alpha, so four rows of that run were wrong.

Fixed (`_bgr` carries alpha; `zones` takes the real foreground; the sweep
keeps RGBA), pinned by
`test_an_arm_of_an_ALPHA_fixture_reads_the_same_image_the_file_does`, and the
table above is the re-run. **`logo_script_tires.png` has no alpha channel, so
every number in §1–§8 is unaffected** — I checked that before trusting them
rather than after.

The tell was a disagreement between two lines of my own output. It is the same
shape as §7's orphaned census row: an instrument that is not pinned against
the thing it claims to reproduce will drift, and the drift is only visible
when something forces the two readings side by side.

## 10. Kent's note: the pro digitized this as 3D puff

Kent, 2026-09-11. The pro file is `TIRES HAT 3D.PES`, and its Wilcom worksheet
confirms the technique: 114.3 × 42.2 mm, **5,640 stitches, two stops —
"Puff Grip" (279 st, a tack-down run, then the machine stops for the operator
to lay foam) and "Black 3D" (5,359 st)**, 11 trims.

It does not bear on the routing — foam is a production decision, invisible in
the pixels, and stage 0 should not try to infer it. It does bear on anything
that compares us to that file:

- Its **two colours are one thread plus a foam stop**, so a colour-count or
  block-count comparison against it is measuring puff procedure.
- Its **5,359 satin stitches at 114 mm** are puff density (foam has to be
  covered, and the columns are capped at the ends). Our 2,332 at 80.3 mm is
  neither the same density question nor the same size — a density comparison
  needs both scaled first.
- The `pro_parity` row `tires_hat_3d`, including the +0.1 forced-flat delta
  quoted in the 08-15 doc and the *"nothing should move here"* control in
  `tools/pro_parity/smoke.py`, is scored against this puff file. That does not
  invalidate those numbers, but they answer "how close are we to the puff
  digitization", not "how close are we to a flat rendering of this artwork".

*(measured 2026-09-11 — `tools/stage0_signal_origin.py`,
`tools/artfidelity_self.py`, `tools/color_diversity.py`; pro worksheet
`scratch_kent/Embroidery Files/TIRES/…/TIRES HAT 3D.pdf`)*
