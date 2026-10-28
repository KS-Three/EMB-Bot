---
name: lane-reading-before-run-2026-10-28
description: "#1158 (merged 2026-10-28): `POST /classify` replays stage 0 + 1.25 on the same upload and config as `/digitize` and answers the lane before the run; the Studio's reading row stands above Auto Digitize with Sew-as-flat-art on it. Routing unmoved. Stage 0's `np.unique(axis=0)` held the GIL 17 s; packed to 24-bit, counts identical"
metadata:
  type: project
---

Kent, 2026-10-27: his owl digitized better as flat art than down the lane the
engine picked, and nothing said which lane until the run had cost him the
better part of a minute. #1158 tells him the lane EARLY. **Nothing about the
automatic routing moves** (Kent's 2026-10-26 ruling, [[lane-census-2026-10-25]]).

- **Service `POST /classify`**: same upload and `config` as `/digitize`,
  replaying `build_generation`'s stage-0 and stage-1.25 block (classify, stage-1
  prep, EXIF + YuNet, the face->flat reroute). Returns `{class, confidence,
  signals, warnings, forced_class_accepted, elapsed_ms}`; `warnings` carries the
  same `CLASSIFIED_*` / `FACE_ROUTED_FLAT` / `PHOTO_DETECTED` codes the Studio
  keys on after a run. A forced class skips every signal and stage 1.25. Two at
  a time in the threadpool, not cached. Drift guard in `tests/test_service.py`:
  codes and class equal `/digitize` on the same fixture.
- **Studio**: `lib/digitizer.js classifyArt()` (404 from an older service ->
  `null`). `DigitizePanel` asks when the artwork lands, the forced class or the
  crop changes; 250 ms debounce, module-level cache by request key. The reading
  row stands ABOVE the Auto Digitize button: `/classify` before a run, the job's
  warnings after; in flight or on any failure, no row. **No "Preview both"**:
  Kent 2026-10-27, "Don't build".
- **`elapsed_ms`, Kent's laptop at 100% CPU (upper bounds)**: becker_marine_logo
  185; photo/owl_kent.jpg 2,450; photo/logo_hotel_fremont.webp 15,599;
  photo/logo_golden_tee.jpg 32,256. Stage 0 is k-means on every pixel at the
  art's own size, so the big squares are the slow ones.
- **Stage 0 froze the service**: `_unique_color_mass`'s `np.unique(px, axis=0)`
  sorts a void dtype under the GIL; a `/health` probe took 17.7 s (idle 0.06)
  during golden_tee's stage 0, the Studio read "no answer" as the browser lane,
  and e2e lost its digitize panel. Fix (`stage0_classify.py`, one expression):
  pack RGB into a 24-bit integer. 13 fixtures, every count identical; 0.0-17.4 s
  -> 0.00-0.21 s; golden_tee stage 0 28.5 -> 15.1 s. Not a recalibration (gate 2).
- **Finding, its own lane after this wave (Kent 2026-10-27)**: owl_kent.jpg at
  80 mm left_chest, automatic (gradient) 376 s, 37,553 stitches; `forced_class:
  "flat"` hit the 600 s stop from TestClient AND the Studio. The 29 s / 8 s that
  framed the lane were at 266 px. This is also why "Preview both" is out.

**Why:** the reading row only ever told Kent the lane after he had paid for it.

**How to apply:** a lane message before the run comes from `/classify`, never a
Studio guess, and its codes stay equal to `/digitize`'s (the drift guard). A
per-pixel `np.unique(axis=0)` in the service is a GIL hold: pack first.
Related: [[digitize-speed-2026-10-26]].
