---
name: enclosed-known-colour-2026-11-17
description: enclosed_white_keeps_known_colour ON (Kent 11-17) - a known-colour enclosed area (black letter band) keeps its own thread under the Studio's white sew thread; one logo of 50 census runs moves
metadata:
  type: project
---

**Fault (Kent's 2026-11-17 logo trial).** A red square logo in a thin black frame,
white letters each wrapped in a thick black band, black counters. Stage 1 takes the
black frame as the page (`bg_rgb=(0,0,0)`), so the band and counters are
`enclosed_background` regions of a KNOWN colour (11.4% of pixels). The Studio sends
`sew_enclosed_white=True`, `sew_enclosed_rgb=[255,255,255]`; `apply_enclosed_white`
gave every planned area the CHOSEN thread (white), overriding the region's own
black, and `DUPLICATE_CONE_LAYERS_MERGED` fused the white band with the white
letters: the word sewed as one white blob.

**Rule, built OFF.** `enclosed_white_keeps_known_colour`: in `apply_enclosed_white`,
an area whose colour is known (not `enclosed_colour_unknown`) and farther than the
existing `enclosed_by_garment_de00` (10, CIEDE2000) from the chosen thread keeps its
own `thread_index`. No new constant. It still SEWS (`sew_enclosed_white` mark, its
own front layer), the same path as `sew_enclosed_rgb=null`. Only when the chosen
thread is near white (within 10 dE00 of white; the Studio default): an explicit
non-white pick recolours known areas as before (narrowed 11-17 after
`test_sew_enclosed_white` showed red picks losing). White page, near-white
page and alpha art behave as before.

**What moves.** Census over the 22 corpus jobs and 30 trial logos
(`scratch_trials/k3-2026-11-16/b8_enclosed_known/census.csv`; the two ProSeal jobs
skipped, `EMB_SCRATCH_KENT` unset): exactly ONE design has a known, non-white page
with an enclosed share, 07_lego at 80 mm left_chest: 29,407 st / 39 trims ->
26,739 / 12, equal to the `sew_enclosed_rgb=null` arm. Controls (Bridge, Golden
Tee, MFab, Becker large, Hotel Fremont, DHL) byte-identical OFF vs ON.

**Traps.** `--set sew_enclosed_white=false` does NOT turn the sewing off on this
art: `cfg` takes it, but `white_keyline_art.detect` reads the logo as white-keyline
art and its recipe (ON for every job since 2026-10-27) forces
`sew_enclosed_white` back ON inside `finish_generation`. Unticking "Sew white
areas" cannot rescue a keyline-shaped logo. The black FRAME is the page flood and
nothing sews it; left as is. The late colour cap's protected set still lists a kept
thread when `sew_enclosed_rgb` is set (harmless, only under cap pressure).

Built OFF, then **flipped ON 2026-11-17**: Kent, shown the ORIGINAL ART | OFF | ON
sheet, answered "Flip ON (Recommended)". `ENCLOSED_KNOWN_COLOUR_2026_11_17_OFF` in
conftest is in `PRE_FLIP`; `engine_2026_10_27.json` stays false.
