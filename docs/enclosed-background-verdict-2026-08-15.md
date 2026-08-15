# Enclosed background regions: the verdict

*2026-08-15. Started as a design session for a garment-driven minimum feature
size — the capability `pro-parity-real-art-2026-08-15.md` §7.1 named as the
largest single lever the real-artwork corpus exposed. It ended somewhere else.*

**Verdict up front: the capability already ships, turning it on is worth +8.0
points per affected design, and the default should NOT flip.** The score rises
because `coverage` rewards blob-overlaps-blob; the output loses a thread colour
the pro used. Two much smaller fixes are the shippable remainder.

---

## 1. What was being designed, and why it dissolved

The brief was a stroke-width floor: below some garment-dependent width, promote a
thin outline to a solid fill, the way the pro turned Becker's hollow letters into
solid ones. Four steps, each of which overturned the last. The wrong turns are
kept here on purpose — each was a plausible reading of the evidence available at
the time, and the sequence is the argument for measuring before building.

**1. "Becker's outline is too thin to sew."** Measured as a raw distance-transform
percentile over all ink pixels: p10 = 0.40 mm, under Law 31's 1 mm floor. Looked
decisive.

**2. Wrong — that was measuring taper tips.** At *skeleton* pixels, which is where
stroke width actually lives, Becker is the THICKEST design in the corpus:

```
design               pro did        stroke width at skeleton (mm)
                                    p05    p25    p50
becker_hat_large     FILLED IT     1.44   2.20   2.90
becker_beanie        FILLED IT     1.12   1.70   2.30
gaulke_roofing_hat   faithful      0.64   1.00   1.30
precision_drone      faithful      0.30   0.70   1.30
```

A "stroke under 1 mm -> solidify" rule fires on `precision_drone` and
`gaulke_roofing`, which the pro left alone, and stays silent on Becker, which the
pro filled. **The rule gets the sign backwards.**

**3. "Then the counters must be too narrow to survive as bare fabric."** Also
wrong. Becker's counters are 138-342 mm² with median width 1.6-2.2 mm — entirely
sewable as exposed cloth.

**4. The actual mechanism.** Becker's artwork is a single opaque colour,
`rgb(35,31,32)`, with the letter interiors **fully transparent** (7,272
transparent pixels vs 3,818 opaque). Becker's pro file carries **5 threads,
alternating Gray `(135,135,135)` and Black**; MFab's carries **Black and White
`(240,240,240)`**. The pro read the transparent interiors as *an intended light
colour that has to be stitched, because the garment is not that colour.* We read
them as background and leave bare cloth.

Not a feature-size problem. And not two problems: "solidify" (Becker) and
"bolden" (MFab) are the same operation — put thread in an enclosed region.

## 2. The discriminator, and the one that matters

Enclosed area as a share of ink separates the corpus cleanly where stroke width
could not:

```
design               pro did                enclosed / ink
becker_hat_large     FILLED IT                     12%
becker_beanie        FILLED IT                     12%
mfab_hat             FILLED IT                     27%
tires_hat_3d         faithful                       3%
gaulke_roofing_hat   faithful (recomposed)          1%
precision_drone      faithful                       1%
hotel_fremont_hat    faithful                       0%
bridge_hat           faithful                       0%
```

3% vs 12% is a 4x gap with no overlap on all eight designs that have artwork.

## 3. It already ships, end to end

Nothing needed building. The seam exists at every layer:

| layer | where |
|---|---|
| stage 1 | `enclosed = bg & ~border_bg`, kept out of `bg` so it joins `fg` (`stage1_prep.py:242`) |
| stage 4 | `tag_enclosed_background()` sets `meta["enclosed_background"]` per region |
| pipeline | `r.meta["stitched"] = overrides.get("stitched", not enclosed)` (`pipeline.py:388`) |
| stage 7 | a layer whose regions are all enclosed sews FIRST, `depth = 0` — correct for a knockout |
| service | validates `stitched` as boolean (`app.py:314`), returns it per region (`:512`) |
| Studio | sends it (`digitizer.js:243`), reads it (`:865`), sets it (`App.svelte:415`) |
| warning | `BACKGROUND_ENCLOSED`, commented "review-toggleable" |

`digitizer.js:212` names the contract outright: **"`stitched` (BACKGROUND_ENCLOSED
restore, contract v1.1)"**.

So the per-region, user-chosen, flag-rather-than-auto design that this session's
questions arrived at independently is the design that shipped. That is a good
sign about the existing contract, and it means the defect was never missing
capability — it was that the capability is invisible.

## 4. What turning it on is worth

`shape_overrides[sid]["stitched"] = True` for every tagged region, chance-corrected
scale, restored engine, garment passed:

```
design                  off      on    delta
becker_beanie          30.5    40.3    +9.8
becker_chest_small     32.1    42.1   +10.0
becker_lc_large        28.2    35.9    +7.7
becker_hat_large       36.2    42.9    +6.7
becker_hat_small       35.7    41.3    +5.6
MEAN                   32.5    40.5    +8.0
```

`coverage` 0.32-0.43 -> 0.47-0.62. `underlay` 0.55 -> 0.82 on the beanie.
`travel` 0.50 -> 0.83.

Across the full 15-design corpus: **+2.7 points, 42.0 -> ~44.7, for zero lines of
code.**

## 5. Why the default should not flip

### 5.1 The win is narrow

Enclosed-region census, all 15 corpus designs:

```
becker x 5           41.0%   <- the entire effect
tires_hat_3d          4.2%
precision_drone       1.8%
the other 8           0.0%
```

### 5.2 The colour is indefensible

The transparent pixels carry `rgb(35,31,32)` — the same near-black as the ink,
because the PNG stores the flattened ink colour under the alpha. So every enclosed
region is assigned `thread_index 155`, **the identical thread as the outline that
encloses it**. Switched on, Becker sews a solid black letter where the pro sewed a
Gray interior inside a Black keyline.

The scorecard said so, and was outvoted by its own weighting: in the same run
`density` FELL 0.66 -> 0.48 and `sttype` went to 0.00, while `coverage` rose
0.40 -> 0.61. Coverage is 20 points and moved most, so the total went up. **The
+8.0 is coverage IoU rewarding overlap while the design loses a colour.**

This is the third independent instance in two days of the parity score and the
visual quality pointing in opposite directions (`pro-parity-real-art-2026-08-15.md`
§5 is the other two). Treat that as a property of the metric, not a coincidence.

### 5.3 The regression cost is broad

Five of twenty repo fixtures would change output:

```
logo_alpha.png              11.0%   <- benchmark fixture
logo_whitebg.png            10.8%   <- benchmark fixture
drone_render.png             1.6%
enthusiast_logo.png          0.8%   <- the benchmark logo
summit_badge.png             0.1%
```

The top two are substantial, and they are the repo's core fixtures. Flipping the
default means re-capturing goldens on them.

**Corrected 2026-08-15:** this paragraph originally added that `logo_whitebg.png`
and `enthusiast_logo.png` were "already entangled in the three failures `main`
carries today", making the baseline red. That was wrong. `main` is green — the
three are Windows-only platform divergence against goldens captured on
`ubuntu-latest` (`pro-parity-real-art-2026-08-15.md` §0b). The argument against
flipping the default does not depend on it and stands on §5.1-5.3 alone; what
does change is that the golden churn is only judgeable in CI, so a local run
cannot tell you whether the re-capture was clean.

## 6. The shippable remainder

Smaller than anything discussed in the design session, and it touches no goldens.
The bug is not the default; it is that **following the warning today gives you the
wrong colour with no indication that a second thread was the point.**

1. **Make `BACKGROUND_ENCLOSED` say what is at stake** — region count, area as a
   share of the design, and that those regions are currently bare fabric. Today it
   is a bare code and the 41% goes unmentioned, which is why a shipped feature
   went unused.
2. **Stop an enclosed region inheriting the enclosing thread when switched on.**
   Its pixels carry no colour information; inheriting is an accident of PNG
   flattening, not a decision. It should be marked as needing a colour choice so
   the two-tone result the pro produced is reachable at all.

Neither is scoped or planned here. Both are small.

## 7. Not this, and why

- **A garment-driven stroke-width floor** — §1 measured it firing on the wrong
  designs. Do not build it on this evidence. The separate, real finding in
  `dt-first-verdict-2026-08-11.md` (19 of 162 regions sew as sub-millimetre satin,
  Law 31) still stands on its own and is unrelated.
- **Garment colour as an engine input** — would be needed to decide *automatically*
  whether an enclosed region needs thread. It does not exist in the engine or in
  Studio, and a user-chosen colour makes it unnecessary. Only revisit if the
  default ever does flip.
- **MFab** — 0 enclosed regions tagged, because it classifies as
  `CLASSIFIED_GRADIENT` with `BACKGROUND_ABSENT` and goes down the photo lane into
  64 regions. A two-colour line logo routed as a gradient photo is a
  classification bug, separate from this and probably larger.

## 8. Reproducing

```
PRO_PARITY_OUT=<out> digitizer/.venv/Scripts/python digitizer/tools/pro_parity/prep_both.py
digitizer/.venv/Scripts/python digitizer/tools/pro_parity/scorecard.py <out>/real/*/
```

The enclosed-on measurement in §4 sets
`cfg.shape_overrides = {r.shape_id: {"stitched": True} for r in enclosed}` after a
first `run_stages` pass identifies them, then re-runs and re-scores. It was a
throwaway probe, not committed — the two lines above plus that override dict
reproduce it.

`prep_both.py` resolves `PRO_PARITY_OUT` lazily as of this session so `DESIGNS`
(which garment each design is, which artwork pairs with which stitch file) can be
imported by other probes without setting the variable.

## 9. Where this sits against the other open work

The +2.7 this would have been worth is small next to what else the real-artwork
run surfaced. For sequencing: `direction` scores **0.073, and 0.00 on 11 of 15
designs**, against a 20-point weight — the single largest recoverable deficit in
the scorecard, and invisible until `53e02ae` chance-corrected it.
