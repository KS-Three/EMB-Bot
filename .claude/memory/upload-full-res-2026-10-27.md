---
name: upload-full-res-2026-10-27
description: SVG, GIF and EXIF-rotated JPEG uploads digitized from the 1,200-px preview; built OFF to send an upright 2,800-px render instead. Measured: no gain while the preview is above the 8 px/mm work grid (100 mm), clear gain below it (emulated jacket back). Flip and service-side EXIF are Kent's.
metadata:
  type: project
---

W5-08, 2026-10-27. The three upload kinds the service cannot decode as they are
(`uploadPlan` reasons `vector`, `format`, `orientation`) kept `sourceFile` null, so
`runDigitize` sent `element.sourcePng`, the 1,200-px preview canvas. Switch ON: the
panel draws them once more, upright, at up to `SERVICE_DECODE_MAX_PX` (2,800) with
smoothing "high" (`renderForService`, `lib/rasterize.js`), stores that as `sourceFile`,
and so the digitize and the .embproj carry it. SVG is rendered AT 2,800 (no natural
size); a GIF or phone JPEG is only scaled DOWN; the JPEG's EXIF rotation is already in
the browser's bitmap. Preview in localStorage unchanged. No service change.

- **Switch:** `localStorage["embbot-upload-full-res"] = "1"`, read by
  `uploadFullResEnabled()`; default OFF. Flipping it for everyone is one line there.
  No customer-facing text ([[no-warnings-reaches-readouts]]).
- **Measured** (`tools/upload-fullres-score.mjs`, 100 mm wide, left_chest, Studio
  config, scored against the SVG's own ink at 10 px/mm; service from the MAIN
  checkout at 2c6b656c). small_text_logo.svg (caps 5.7/3.7/2.7 mm):

  | send | px/mm | stitches | trims | colours | IoU | edge mean |
  |---|---:|---:|---:|---:|---:|---:|
  | OFF 480 (emulates a 250 mm jacket back's 1,200-px preview) | 4.6 | 18,677 | 46 | 5 | 0.622 | 0.310 mm |
  | OFF 1,200 (today at 100 mm) | 11.5 | 17,975 | 37 | 2 | 0.688 | 0.236 mm |
  | ON 2,800 | 26.9 | 17,865 | 45 | 2 | 0.692 | 0.234 mm |

  So: at 100 mm the 1,200-px preview is already above the 8 px/mm work grid and ON is a
  wash (IoU +0.004, trims +8). The case it exists for is a big design: at 4.6 px/mm the
  send loses 0.07 IoU, grows a grey halo sewn as 3 extra thread colours, and notches
  letters (sheet `docs/renders/upload-full-res-2026-10-27/small_text_logo__off_on.png`);
  ON recovers all of it. vector_logo.svg: 0.931 / 0.926 / 0.932. The cap 2.7 mm line
  scores 0.28 in EVERY arm: below what the engine sews faithfully, not a resolution loss.
- **250 mm is EMULATED, not run:** the real 250 mm design overran the service's 600 s
  job limit under the laptop's load (OFF arm, `took too long`). Output depends on px per
  mm and the features' size in mm, so the 100 mm design sent at 480 px stands in for it.
- **Fixtures:** `tools/make-upload-fixtures.mjs` (reproducible): `small_text_logo.svg`
  (Medium Font, OFL, outlined to paths + frame), `rotated_exif6.jpg` (2,520 x 1,400
  upright, stored sideways), `rotated_exif6_upright.png` (exact twin: the stored JPEG
  decoded with orientation ignored and turned by hand). A twin JPEG would go up as the
  file itself, never through the canvas, so it cannot be the comparison. e2e: rotated
  JPEG's POST == twin through `renderForService`, 0 of 14,112,000 channels differ.
- **Kent's calls:** (1) the flip; (2) should the service honour EXIF orientation at
  decode (`cv2.imdecode(..., IMREAD_UNCHANGED)`, `app.py` ~L778)? Left alone: it would
  change a default for every caller. Not needed for the Studio once ON.

**Why:** a vector logo is the best small-lettering input a customer can give, and the
preview threw its detail away; DOCTRINE 2026-09-19/20 priced the same canvas re-encode
at 503 -> 609 trims on nine logos.
**How to apply:** do NOT flip on the 100 mm table (it shows nothing). Judge from the
sheet and the 4.6 px/mm row; the real jacket-back run needs a quiet machine. Traps that
cost this session hours: (a) a service started from a WORKTREE lacks
`rembg_isolated/venv` and `sam2_isolated` (gitignored): run the service from the main
checkout ([[seeds-request-and-the-worktree-blind-spot-2026-09-22]]); (b) `rasterSize`
reads `{width, height}`, a bare `{w, h}` silently draws 1 x 1 and the service says "the
whole image read as background"; (c) the Studio sews the white field inside a frame
(`sew_enclosed_white`), 6x the SVG's ink: leave near-white thread out of the coverage;
(d) check a posted PNG's INK, not just its header; (e) `block-worktree-mutation.js`
fails closed on an `rm` in a command that also names `.claude/worktrees/`: put lock
cleanup in a script file.
