---
name: lettering-board-v2-2026-10-27
description: lettering board re-baselined on engine 98603fb4 (docs/scoreboards/lettering-board-2026-10-27) -- words pinned for Gaulke/Drone/Tires, cc on 39 of 42 lines (was 16); the 10-25 baseline's MFab hat and Tires had REROUTED (no rembg venv in a lane)
metadata:
  type: project
---

W5-03 (2026-10-27), measurement only. Baseline: `docs/scoreboards/lettering-board-2026-10-27.{md,json}`,
engine `98603fb4`, tesseract v5.4.0.20240606 (CI has 5.3.4), 16 pairs, 42 lines. Flag set by NAME
in `meta.flags` (39 ON, 19 OFF), not "main defaults". cc coverage per band, before -> after: <4 5/15 ->
15/15, 4-6 0/6 -> 6/6, 6-10 3/8 -> 8/8, 10+ 8/13 -> 10/13. The three still n/a: MFAB x2, Tires.

**Headline (ours / pro, cc and reach only, both chance-corrected):** <4 mm cc +0.66 / +1.00, reach
2.81 / 3.81, columns 173 / 156 (was 23 / 163: the re-set landed). 4-6 cc +0.89 / +0.98. 6-10 cc +0.81 /
+0.90. 10+ cc +1.00 / +0.68, reach 4.42 / 2.87, trims inside letters 62 / 14 (BECKER 8-16 against his 1).
Gaulke STEEL ROOFING columns 46 / 38 / 39 against 32 (hat / beanie / LC; was 44-52).

**Traps found (each would have published a wrong board):**
- A lane has NO rembg venv (it is not in git). Stage 1 then says PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE and
  a photo-routed job takes the classical route whatever the timeout: the 10-25 baseline's `mfab_hat` and
  `tires_hat_3d` had done exactly that. The board now points stage 1 at the primary checkout's venv,
  digitizes at 900 s, records both, stops at the first rerouted job and refuses to publish one.
- Gaulke's art (`photo/logo_gaulke_roofing.png`) is a phone screenshot: 546 rows of logo between black bars.
  `word_legibility` takes the ground from the whole picture, so it was BLACK, the black thread of both files
  vanished and the "ink" was the white panel. `trim_letterbox` (only where the panel's own edge differs
  from the bar). The art spells GOLKE, not the client's Gaulke nor the files' "c golke".
- Both beanie pro files are DST-only and open with a garment-coloured KNOCKDOWN block over the whole logo
  (Gaulke 1,981 stitches over 94 x 43 mm, ProSeal 2,007). The reader draws a DST in one black, so the
  pictures were black blobs: Gaulke's words "not located", ProSeal beanie's pro "no word-sized thread" in
  the 10-25 board and a bogus cc 0.00 in this board's first pass. `pro_words_design` draws block 0 as cloth.
- #1112's white faces: `letter_block` reads the SATIN block, not the longest. It moves ONE cell
  (becker_chest_small BECKER, ours: 0 columns / 4,966 stitches / 0.41 mm -> 26 / 3,451 / 1.48 mm); the other
  four Becker pairs' longest block was already the outline.
- Tires is BLIND: both files locate, but tesseract does not read the script off the ART (cc -0.48).
  MFAB 10+ is n/a in both files since #1115: ours now sews the pro's white keyline and the reader finds a
  fragment (hat 6.95 mm of 18.0 drawn, LC 7.85 of 16.6; his 8.65 and 7.95). Pro Drone DRONE: "no
  word-sized thread near the word"; its AND box takes the rope beside it.

**How to apply.** A lettering PR runs `python -m tools.lettering_board --cache DIR` (needs the lock on this
laptop: about 32 min digitizing, 13 min reading) and quotes `--compare` against THIS board. `--dump DIR` writes every
located picture: look at them before trusting a cc. The board prints its own NEXT QUEUE (columns > 1.3x, cuts
+2 over, cc/reach lower): top of it is Fremont's <4 mm words (EST/1895/EAT STAY cc 0.00-0.32 against 1.00),
Drone's PRECISION and AND DRONE (cc 0.00 / 1.00), MFab's AND WELDING (cc 0.00 / 0.92) and Becker's trims.
Related: [[lettering-board-2026-10-25]], [[word-legibility-reach-2026-10-25]], [[word-legibility-instrument-2026-10-24]].
