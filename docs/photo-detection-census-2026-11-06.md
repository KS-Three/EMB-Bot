# Photo detection census, 2026-11-06 (MASTER_SCOPE defect 15)

**Verdict: (a). The stage-0 texture gate subsumes stage-1.25 detection on every photograph measured. Recommend defect 15 CLOSED and the stage-1.25 docstrings updated.** Caveat that decides how far to trust it: the gate's thresholds were set on this same 18-genre corpus, so 19 of 19 is a regression check, not an out-of-sample test.

Instrument readings, not quality claims (ROADMAP gate 4). No stage-0 threshold moved (gate 2), no flag flipped (gate 3), no image committed. Tool: `digitizer/tools/photo_detect_census.py`. Pinned summary: `digitizer/testdata/photo/photo_detect_census_2026-11-06.json`. Pin: `digitizer/tests/test_photo_detect_census.py`.

## Method

`/classify`'s block (`digitizer_service/app.py::classify_art`) replayed on each row, never a full digitize: stage 0 under both arms of `stage0_texture_gate`, stage 1 prep, then stage 1.25 with both signals read (`faces_always`). Config is what the Studio sends: `detect_photographic=true`, `faces_route_flat=true`, 80 mm. Rows: 16 committed fixtures (owl_kent, drone_render, summit_badge, the thermal badge, 12 other logos) and the 39 Commons corpus rows fetched by `python -m tools.photo_corpus fetch` (18 photo genres, 21 logo styles, 6 of those logo rows photographed or scanned media, labelled `photo-of-logo` as `stage0_photo_gate` does).

## The 2x2

Real photographs, n 19 (owl_kent plus the 18 corpus photo genres):

| | detection fired | silent |
|---|---|---|
| **photo class by stage 0** | 3 | 16 |
| **other class** | 0 | 0 |

- **Detection rescues: 0.** No photograph lands in a non-photo class, so there is nothing for a signal to add.
- **Escapes (`is_photographic` False with detection ON): 0.** No photograph is left without the palette bind or depth sequencing by either mechanism.
- **Gate rescues: 16 of 19.** With `stage0_texture_gate` OFF these read gradient or flat: owl_kent, architecture, dark_dog, fireworks, flower_macro, food_plate, group_people, landscape_lake, night_neon, night_skyline, oil_painting, sports_action, stained_glass, underwater_reef, vintage_sepia, watercolor. The other 3 were photo-class before the gate.
- **The 3 signals that fired:** vintage_sepia (4 faces), group_people (2 faces), sports_action (EXIF camera, 1 face). All three were already photo-class.

Photographed graphics (`photo-of-logo`), n 6: 6 photo class, 2 detected (comic_halftone by face, chalkboard_lettering by EXIF), 0 other class. Stage 0 reads the medium; these were never an escape.

Chance-corrected agreement with the hand label (photo vs logo, 49 rows, Cohen's kappa):

| reading | kappa | tp / fn / fp / tn |
|---|---|---|
| photo class by stage 0 | 1.000 | 19 / 0 / 0 / 30 |
| detection fired | 0.187 | 3 / 16 / 0 / 30 |
| Studio job `is_photographic` | 0.867 | 16 / 3 / 0 / 30 |

Detection alone is a weak photograph detector (misses 16 of 19) and has no false positives. The gate is the detector.

## False positives

**0 of 30 logos** trip either signal: the 15 committed logos (the 14 that `tests/test_photo_detection.py::LOGOS` pins, plus the thermal badge) and the 15 corpus logo rows. No logo reads as a photo class under the gate either.

## Rows still not photographic: a different cause, not an escape

Three photographs end a Studio job with `is_photographic` False: **group_people, sports_action, vintage_sepia**. Detection ON does not leave them unbound; `faces_route_flat` (Kent's 2026-09-30 ruling) re-classifies a face hit as `flat` and keeps the photographic machinery off on purpose. With detection OFF all three would be `photo_scene` with the machinery on. So detection, as shipped to the Studio, takes 3 of 19 photographs (16%) out of the photo lane, and sports_action goes there on a face found beside an EXIF hit. That is the ruling working, not defect 15, but it is the one place detection changes a photograph's route.

## Full digitize at 80 mm

The brief asked for up to 3 escape rows. There are none, so I ran the two rows that bound the question, each once as the Studio sends it and once with `is_photographic=True` forced:

| row | arm | class | is_photographic | blocks / distinct cones | duplicate cones | re-snap added / outside palette |
|---|---|---|---|---|---|---|
| owl_kent (control) | Studio | photo_scene | True | 12 / 12 | 0 | 0 / 0 |
| owl_kent | forced True | photo_scene | True | 12 / 12 | 0 | 0 / 0 |
| group_people (face-routed) | Studio | flat | False | 12 / 12 | 0 | 0 / 0 |
| group_people | forced True | photo_scene | True | 12 / 12 | 0 | 0 / 0 |

The owl is identical in both arms, as it should be: the gate alone already binds it. group_people shows no duplicate cones and no re-snap escape in either arm, so the cone-escape symptom defect 15 recorded does not appear on the face-routed route. This measures cones only. It says nothing about how the two routes look when sewn.

## What this does not cover

- **In-sample.** The texture gate's threshold and margin came from this corpus (PR #1178). Reading 19 of 19 confirms the shipped gate still catches it. It does not estimate how often an upload outside these genres lands in a non-photo class.
- **No alpha cut-outs.** A cut-out takes the grain gate alone; the corpus has none.
- **No small photographs.** The corpus has nothing under 500 px; the gate normalises to `TEXTURE_NORM_PX`, but that is not measured here.
- **EXIF is thin evidence.** No committed fixture carries a camera tag. Of the 39 corpus rows only 2 do (sports_action, a Nikon, and the chalkboard photo, a Samsung phone). How often a customer's upload keeps its header is unmeasured.

## Recommendation

1. **Close defect 15** on the gate plus `bind_resnap_all_classes` (09-10) plus the Studio sending `detect_photographic`. Closure is Kent's.
2. **Update the stale stage-1.25 text** (foreman's pass, not done here): `config.is_photographic`'s "WHY THIS IS DECLARED, NOT DETECTED" paragraph and `photo_signals.py`'s module docstring still say stage 0 cannot separate the owl from two logos; the owl is a photo class by `texture_frac` 0.358 since 10-28. The comment block at `app/src/lib/digitizer.js` ~L206-217 still presents detection as what replaces the declaration.
3. **Keep stage 1.25.** It rescues nothing here, but it is the only thing that sends a face to the flat lane (a ruling) and it costs 0.03-0.14 s. Removing it is a behaviour change and not this PR's call.
4. No fix proposed: zero real photographs escape, so there is no flag to design.
