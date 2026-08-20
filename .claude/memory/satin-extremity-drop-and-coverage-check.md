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
confirmed at the source). Root cause: still open — satin rail generation on
a bracket-with-spur outline covers the main limb and drops the spur,
asymmetric between mirror twins (traversal-order smell, not a threshold).
PR #180 / `docs/scope/1-auto-digitizing-quality.md`.

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
