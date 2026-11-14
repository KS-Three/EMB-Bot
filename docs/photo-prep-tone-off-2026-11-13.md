# Photo prep tone pass: OFF by default (2026-11-13)

## Decision

Kent, 2026-11-13: "Switch it off by default".

Photo prep's tone pass (`stage1_photo_prep._tone_prep`: a 2nd-98th percentile
contrast stretch of L measured over the foreground, then CLAHE on L) is now
behind `PipelineConfig.photo_prep_tone`, default `False`. The texture kill
(`photo_prep_texture_kill`, default `"bilateral"`) is unchanged and still runs.
With the switch off the raster entering the texture kill is stage 1's raster
after the cutout, un-toned.

## Evidence

Study of the 14 corpus images on which the rembg cutout runs, at commit
`2489ac48`, request 80 mm, `left_chest`, at most 6 colours
(`detect_photographic` and `faces_route_flat` on, `edge_cap` `"none"`). Three
arms, cutout kept in all three:

- **A**: production at that commit (tone pass on, bilateral texture kill).
- **B**: tone pass off (the study patched `_tone_prep` to return its input).
  This is what `photo_prep_tone=False` now does.
- **C**: B plus `photo_prep_texture_kill="none"`.

Metric: per-region CIEDE2000 between the assigned thread and the raw photo
(preflight's `_region_color_errors` re-read), area-weighted over regions.
"Order flips" counts pairs among the 6 largest regions whose lightness order in
the raw photo is the reverse of their threads' lightness order.

| image | region aw dE00 A / B / C | flipped pairs A (of them >= 3 L* on both sides) | flipped pairs B | grade A / B |
|---|---|---|---|---|
| bw_street | 9.72 / 5.87 / 6.32 | 1 (1) | 0 | F / B |
| flower_macro | 11.77 / 6.70 / 9.05 | 0 | 0 | F / A |
| dark_dog | 13.77 / 5.75 / 5.89 | 1 (0) | 0 | F / B |
| photo__photo_chrome_specular | 9.18 / 3.93 / 4.10 | 0 | 0 | F / B |
| duotone_poster | 10.87 / 4.56 / 4.56 | 0 | 0 | B / B |
| oil_painting | 9.88 / 6.70 / 6.73 | 0 | 0 | F / B |
| food_plate | 11.99 / 10.86 / 10.45 | 1 (1) | 0 | F / C |
| kanji_brush | 20.06 / 3.32 / 3.08 | 0 | 0 | F / A |
| vintage_engraved_badge | 14.44 / 3.99 / 3.99 | 0 | 0 | C / C |
| architecture | 9.46 / 4.28 / 4.08 | 0 | 0 | D / B |
| photo__owl_kent | 6.34 / 4.14 / 4.48 | 2 (2) | 0 | F / C |
| watercolor | 12.28 / 6.39 / 6.86 | 0 | 0 | D / B |
| photo__fur_ramp | 7.38 / 5.32 / 5.32 | 0 | 0 | C / B |
| art__logo_mfab_hat | 0.47 / 0.47 / 0.47 | 0 | 0 | B / B |
| **mean / total** | **10.54 / 5.16 / 5.38** | **5 pairs on 4 images (4 on 3)** | **0** | |

- On the region metrics (area-weighted, median, worst) arm A is not the
  closest arm on any image; it ties on `art__logo_mfab_hat`, where all three
  arms produce the same design.
- Region median dE00 means: 12.24 / 6.07 / 6.07. Region worst means:
  26.21 / 15.04 / 16.62.
- Renders: `kanji_brush`'s black ink (raw L* 17 to 25) sews in arm A as four
  greys (Dark Pewter, Whale, Titanium, Cobblestone) and in arm B as one thread,
  Blackberry. `dark_dog`'s black fur sews in arm A partly as Steel and
  Battleship Gray, and in arm B as Blackberry, Black Chrome and Black.
- Grades are the corpus tool's preflight grade (`tools/photo_corpus.py`
  summary), listed for reference; they are not the decision's basis.

Reproduced on the switch itself (base `d9737a7b`, the same request, rembg
cutout available): for all 14 images the design md5 with the new default equals
the study's arm B md5, and with `photo_prep_tone=True` equals arm A's.

## Mechanism

The tone pass measures its stretch on the foreground only (`~bg_mask`). After
the rembg cutout the foreground is the subject alone, and for some subjects
that is a narrow tone range: the ink of a brush character, the fur of a black
dog. `_tone_prep` maps the foreground's 2nd-98th percentile L to 0-255, so a
range of a few L units is spread over the full scale, and CLAHE then raises
local contrast further. The region former and the thread matcher read that
stretched raster, so near-black regions are matched to mid-grey threads, and
regions of nearly equal lightness can be ordered differently from the photo.

## Not measured

- No sew-out. dE00 here is closeness of thread colour to the photo, not
  embroidery quality.
- 14 images, one size (80 mm), one garment, one colour cap.
- A photo that is washed out (low contrast across the whole subject) no longer
  gets the contrast stretch. That is the accepted cost of this default.

## Turning it back on

Per request: send `"photo_prep_tone": true` in the job config (the service
accepts every `PipelineConfig` field). In code:
`PipelineConfig(photo_prep_tone=True)`. `photo_prep_clahe_clip` and
`photo_prep_clahe_tiles` apply only when it is on.

With `photo_prep_tone=True` the prep output is byte-identical to the engine
before this change (`tests/test_photo_prep.py` pins it on `region_blobs.png`).
Tests built on the frozen 2026-10-27 engine (`tests/engine_2026_10_27.json`,
`conftest.PRE_FLIP`) carry `photo_prep_tone: true`, so their pins do not move.
