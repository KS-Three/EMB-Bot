---
name: stage0-texture-gate-2026-10-28
description: Stage 0's photo gate was a grain detector; texture_frac route + two-ink veto (ON, cfg.stage0_texture_gate) send all 18 corpus photographs to the photo lane; six "logo" rows are photographs by medium
metadata:
  type: project
---

**Finding (2026-10-28).** `unique_color_mass` counts per-pixel GRAIN; a
downsampled photograph has none, so 15 of the 18 Commons corpus photographs
read 0.02-0.27 against 0.28 and sewed as `gradient` logos. Built ON:
`texture_frac` (share of an opaque file's foreground on a 512-px raster with
5x5 luminance std 2-24, more than 2 px from a hard edge) >= 0.13 is a second
route in (photos min 0.192 watercolor, designed graphics max 0.066 TOAT
beanie, stable 250-1600 px). The 2-px edge exclusion is load-bearing: the
small real `testdata/art/` logos read 0.22-0.25 without it;
`two_tone_mass` >= 0.90 is two inks and vetoes (tires, arabic leave
`photo_scene`); an alpha cut-out keeps the grain gate alone (drone stays
`gradient`). `cfg.stage0_texture_gate=False` is the old tree byte-for-byte;
`tests/engine_2026_10_27.json` holds it False so `frozen_cfg` pins stand.

**Why:** Kent 2026-10-27: the digitizer must improve ALL photos, not the ones
on hand. ROADMAP gate 2's "real tonal artwork" is the corpus itself.

**How to apply:**
- Read the gate with `python -m tools.stage0_photo_gate` (margins, both arms,
  `--ladder`); `tools/classify_lens.py` re-derives the tree and self-checks.
- Stage 0 reads the MEDIUM: halftone_dots, chalkboard_lettering,
  duotone_poster, kanji_brush, comic_halftone, vintage_engraved_badge are
  photographs/scans of graphics and route photo by design. No pixel rule
  separates them (brute force over 20 statistics: 5-miss floor). Do not raise
  the gate to exclude them; Kent judges them on the sxs page.
- Faces still sew flat downstream (group_people, sports_action,
  vintage_sepia, comic_halftone): stage 1.25's ruling, untouched.
- Known limits: a barcode at ~250 px reads 0.175; a steep smooth ramp counts
  as texture (synthetic `region_blobs` 0.197) — no real opaque logo here does.
- A rembg venv reached through a directory junction hangs on `import rembg`
  (>540 s; 8 s by its real path), so every photo-lane row reads
  `rembg worker timed out after 120s` and runs the classical route. COPY the
  venv into the lane (474 MB); check `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`
  in the row json before reading a photo-lane row as the Studio's
  ([[lettering-board-v2-2026-10-27]] hit the no-venv form of this).

Related: [[photo-corpus-sxs-2026-10-27]], [[stage0-flake-output-alignment-2026-10-25]].
