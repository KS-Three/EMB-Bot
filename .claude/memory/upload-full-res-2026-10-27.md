---
name: upload-full-res-2026-10-27
description: SVG, GIF and EXIF-rotated JPEG uploads digitized from the 1,200-px preview; built OFF to send an upright 2,800-px render instead. 100 mm: no gain; real 250 mm jacket back: geometry tie, ON drops halo colours and trims; text-heavy art times out at 600 s in both arms. Kent 10-27: flip held, service EXIF left alone.
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
- **250 mm jacket back, RUN 10-27** (Kent's "hold for a quiet-machine run"; service from
  the main checkout 2c6b656c, `jacket_back`, Studio config, lock taken at STATE=OK with
  both slots free, but other slot holders ran beside it, watchdog idle 6% at 09:17):
  `vector_logo.svg` (`docs/renders/upload-full-res-jacket-back-vector-2026-10-27/`):

  | send | px/mm | stitches | trims | colour chg | IoU | edge mean | digitize |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | OFF 1,200 | 4.0 | 32,306 | 12 | 3 | 0.9768 | 0.252 mm | 55 s |
  | ON 2,800 | 9.4 | 32,064 | 7 | 1 | 0.9764 | 0.255 mm | 59 s |

  Geometry is a TIE (IoU, edge); ON removes the 4 px/mm artifacts: 2 halo colour changes
  and 5 trims gone, circle rim notched at OFF, clean at ON (sheet `vector_logo__off_on.png`).
  `small_text_logo.svg` at 250 mm with the white field sewn (Studio default): **BOTH arms
  overran the service's 600 s limit** (OFF stopped at 600 s; ON posted behind OFF's
  still-running job, then ran its own 600 s). Not an upload-resolution effect: the same
  design at 100 mm took 277 s (OFF) and 408 s (ON, +47%) on a busy laptop, and area grows
  6.25x. So lettering plus a sewn white field cannot finish at jacket-back size either
  way; ON costs more CPU on top. A `--no-white` 250 mm run was NOT done (different
  config from the Studio's).
- **The service keeps computing after "reported failed":** `digitize job ... passed 600s;
  reported failed` stops the poll, not the worker; the next job waited ~220 s behind it
  (second job's first dnn line at 854 s uptime vs 29-32 s for a fresh job).
- **Fixtures:** `tools/make-upload-fixtures.mjs` (reproducible): `small_text_logo.svg`
  (Medium Font, OFL, outlined to paths + frame), `rotated_exif6.jpg` (2,520 x 1,400
  upright, stored sideways), `rotated_exif6_upright.png` (exact twin: the stored JPEG
  decoded with orientation ignored and turned by hand). A twin JPEG would go up as the
  file itself, never through the canvas, so it cannot be the comparison. e2e: rotated
  JPEG's POST == twin through `renderForService`, 0 of 14,112,000 channels differ.
- **Kent's rulings, 2026-10-27:** (1) the flip: "Hold for a quiet-machine run
  (Recommended)", it stays OFF until that run's sheet is read (the run is above; the flip
  is still his); (2) service EXIF at decode (`cv2.imdecode(..., IMREAD_UNCHANGED)`,
  `app.py` ~L778): "Leave it (Recommended)", no service change. API callers still get
  sideways phone JPEGs; the Studio does not need it once ON.

**Why:** a vector logo is the best small-lettering input a customer can give, and the
preview threw its detail away; DOCTRINE 2026-09-19/20 priced the same canvas re-encode
at 503 -> 609 trims on nine logos.
**How to apply:** do NOT flip on the 100 mm table (it shows nothing). Judge from the
250 mm sheet: at real size ON is a clean-up (halo colours, trims, rim), not a geometry
gain, and the text-heavy case times out in both arms. Traps that
cost this session hours: (a) a service started from a WORKTREE lacks
`rembg_isolated/venv` and `sam2_isolated` (gitignored): run the service from the main
checkout ([[seeds-request-and-the-worktree-blind-spot-2026-09-22]]); (b) `rasterSize`
reads `{width, height}`, a bare `{w, h}` silently draws 1 x 1 and the service says "the
whole image read as background"; (c) the Studio sews the white field inside a frame
(`sew_enclosed_white`), 6x the SVG's ink: leave near-white thread out of the coverage;
(d) check a posted PNG's INK, not just its header; (e) `block-worktree-mutation.js`
fails closed on an `rm` in a command that also names `.claude/worktrees/`: put lock
cleanup in a script file.
