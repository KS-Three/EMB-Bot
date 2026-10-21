---
name: beanie-knockdown-2026-10-21
description: Beanie knockdown built and flipped ON by Kent the same day — garment-coloured sparse fill under the whole design, sewn first; Kent's rule is the engine decides per garment like backing, don't ask per logo
metadata:
  type: project
---

2026-10-21, PR #1027. `cfg.beanie_knockdown` (`digitizer_core/knockdown.py`):
for `garment_id == "beanie"` with a known `garment_rgb`, block 0 is a tatami at
0.50 mm rows / 3.5 mm stitches, no underlay, over the planned shapes grown 2.0 mm
with holes filled, in the cone nearest the garment colour. Doc:
`docs/beanie-knockdown-2026-10-21.md`.

**Kent flipped it ON over the renders, unsewn**, and answered the sew-test question
with: the engine should know what each garment needs (like backing), so don't ask
about a specific logo. **Why:** it is a per-garment construction habit (pro 6 of 6
beanie files), not a design choice. **How to apply:** garment-driven construction
rules go in as engine behaviour keyed on `garment_id`; don't put a per-logo choice
to Kent.

Traps found building it:
- Stage 6 `travel_path` lifts past 4x straight distance / 20 mm; the knockdown has
  its own edge router (`_stay_down`) because the pro's is one piece, 0 trims.
- The margin raster read (0.3 mm lines, 10 px/mm) reads ~0.2 mm SHORT: ours built
  at 1.5 read 1.32, so the pro's "1.6-1.8" is ~1.8-2.0 true. Calibrate a raster
  instrument on our own known build before quoting the pro.
- Not copied: on badge designs (To a T, Machine E) the pro stops the knockdown at
  the satin border. Related: [[pro-rules-across-jobs-2026-10-21]].
