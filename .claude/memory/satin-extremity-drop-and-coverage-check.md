---
name: satin-extremity-drop-and-coverage-check
description: enthusiast_logo's satin brackets silently drop tabs/corners (11.5% of emblem area) despite correct outlines and stitched:true; preflight's new ARTWORK_UNCOVERED check catches the class — ground truth needs polygon ∩ ink, neither alone
metadata:
  type: reference
---

Kent spotted two holes by eye in a live Studio render of `enthusiast_logo.png`
("lost the left arm... heads toward the star", "lost the bottom right
corner") — both real, and measured (2026-08-20, overlay diff of the design's
own exported DST against the source artwork's ink mask) as the **#1 and #3
largest missing regions in the whole design**: 97.1 of 1372.2 mm² artwork
unstitched overall (7.1%), 11.5% within the emblem alone.

**Three causes tested and excluded** — not shape formation (both brackets'
`outline_mm` are correct and mirror-symmetric, `stitched: true`), not
background intrusion (`bg_tolerance_lab`/`bg_intrusion_min_mm` swept, output
byte-identical every time despite `BACKGROUND_UNCERTAIN` firing), not the
starburst regression (`stage6_satin.py`'s DT check runs unconditionally,
confirmed at the source). PR #180 / `docs/scope/1-auto-digitizing-quality.md`.

**ROOT-CAUSED AND FIXED 2026-08-21 — and the traversal-order hypothesis above
was wrong.** It is `_prune_spurs`' own iterative cascade. Pass 1 correctly
erases the tab's two short twigs; that leaves the tab STEM holding a single
arm, i.e. a dead end it did not thin its way into; pass 2 re-measures the stem
against the same bar and deletes it. Left stem 19.000 px vs bar 19.4770 (2.4%
under, dies); right stem 20.000 px vs 19.1152 (4.6% over, lives). **One raster
pixel decides a 3.3 mm tab** between mirror twins 0.06% apart in area. Fixed by
remembering the dead ends the function itself exposes and never counting one as
a spur tip — not by moving the bar.

**Two things measured and REFUTED en route, so nobody re-tries them:** lowering
the 1.6 multiplier globally (fixes 2 fixtures, breaks 2, 7 test failures — the
decision margin is ±0.4% against 3.5% input noise, so every value just moves
which shape is on the knife edge), and swapping `dist[skel].mean()` for a
grid-independent normalizer (the twins' branching differs, so no length
statistic separates them). **A third trap, worth more than either:** the first
investigation measured `region.polygon` (165.41 mm²), but stage 7 satins the
pull-compensated `p.polygon` (194.53 mm², +0.3 mm, 17% different `half_mm`) —
every spur number, flip point and stroke list came out wrong, and the whole
"topology fork" story with it. Intercept `satin_shape` to get the operative
polygon; `region.polygon` is only what `is_satin_candidate` classifies on.

**The instrument that let it hide is fixed, not the bug itself.** `preflight`
gained `ARTWORK_UNCOVERED` (PR #181, `digitizer_core/preflight.py`
`_uncovered_findings`) — ground truth is `polygon ∩ ink`, and getting there
took three false-positive classes, each found testing against
`becker_marine_logo.png` before trusting either mask alone:

- *polygon alone* claims a letter's open counter (BECKER's "C") as area
  belonging to that shape → 62 mm² of correctly-bare fabric reads missing.
- *ink alone* (`~bg_mask`) counts every enclosed counter as artwork needing
  thread → same fixture reads 42.3% "missing" while sewing exactly as
  designed.
- *border erosion*: `cv2.erode`'s default border doesn't erode artwork
  touching the image edge, so a full-bleed design read a permanent 37.5 mm²
  strip down its border at every erosion width, until the erode call got an
  explicit zero border (`borderType=cv2.BORDER_CONSTANT, borderValue=0`).

Verified to name the exact shape (`S041897f7`) and stay silent on 6 other
fixtures. **The 5.0 mm² patch threshold is explicitly flagged provisional in
the constant's own comment** — two calibration fixtures (`logo_script_tires`
4.50, `logo_drone_thermal_badge` 3.25) sit unadjudicated close to the line,
nothing like `_COVERAGE_MIN_PATCH_MM2`'s two-orders-of-magnitude separation.
`becker_marine_logo.png` itself was excluded from calibration — 146×91 px
for a 90 mm design, 1.6 px/mm, far under `PHOTO_MIN_PX_PER_MM=10.0`.

**Tooling footgun found en route:** `tools/render-dst.mjs` draws stitches as
1-px Bresenham lines with no width — at `scale 6` (its default) that's
0.167 mm against ~0.4 mm real thread, so the SAME byte-identical DST measures
22.7% ink at `scale 2` and 10.5% at `scale 16`. Apparent density more than
doubles from render scale alone; don't judge fill/satin coverage by eye from
this tool. It also reports jump/trim counts that disagree with
pystitch/the service (100 vs 40 on one fixture) — decode through **pystitch**
for anything quantitative, same rule as [[dst-codec-axis-discrepancy]].

See also [[real-artwork-parity]] (preflight/scorecard blind spots generally)
and [[emb-bot-digitizer]].
