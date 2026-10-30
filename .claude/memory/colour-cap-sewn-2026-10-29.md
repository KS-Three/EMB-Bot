---
name: colour-cap-sewn-2026-10-29
description: "Census item 3 re-read: the sewn design loaded more cones than the cap because the sew-white recolour runs AFTER enforce_color_cap and the blend tier snaps bands to the whole chart; color_cap_sewn (OFF) re-caps the final regions and folds strays on the blocks"
metadata:
  type: project
---

# The colour cap holds on the sewn design — 2026-10-29

**What the census got wrong.** Item 3 of `docs/photo-style-census-2026-10-27.md`
blamed `_cap_tonal_layers` / `cfg.tonal_split_layer_cap` for not reaching the
gradient lane. That is defect 20's fill-LAYER (density) cap; it never capped a
colour on any lane. Read block threads, not regions or the warning.

**The two mechanisms** (`python -m tools.cone_escape IMG [--set k=v]`, Studio
request 80 mm left chest, cap 6):

1. `apply_enclosed_white` (finish_generation) recolours the fields "Sew white
   areas" sews to White 0015 AFTER `enforce_color_cap` ranked them. Both leaks
   on main: isometric_icon 7/6 (2 fields, 1.3 m), watercolor 7/6 (4 fields,
   7.4 m); drone_render 7/6 too.
2. `stage6_blend.blend_fill` / `design_shade_scheme` snap each band to the
   whole chart; the photo lane's `shade_palette_bind` is gated on
   `is_photographic`. Golden Tee 9/6 (strays 4.7 / 10.4 / 17 mm), summit_badge
   9/6 (2.3 / 6.0 / 10.5 m); forced gradient: flower_macro 13 (7 strays of
   9–57 mm), underwater_reef 9, food_plate 8, night_skyline 8 (2 × 5.8 m).

Under budget but banded: gradient_ramp_linear / radial and
repro_gradient_white_icon sew 5 cones from 1–2 regions. A per-band bind to
the region's cone would flatten them to 1 — measured, not built.

**Built, `cfg.color_cap_sewn` OFF** (false in `tests/engine_2026_10_27.json`):
a second `enforce_color_cap(protected=, stitched_only=True)` at the end of
`finish_generation`'s recolours (review recolours + the sew-white thread
protected and counted); `stage7_sequence.fold_stray_cones` over the blocks
before the adjacent merge: regions' cones keep slots, strays fill free slots
longest thread first, the rest recoloured in place to nearest kept (CIEDE2000).
One `COLOR_CAP_APPLIED` per design. Not touched: knockdown's garment cone.

**Why:** every cone is a spool and a re-thread; "Colors (max 6)" is a price.
**How to apply:** a thread-count claim quotes `colors_used` off the blocks
(`tools/photo_corpus.py` `distinct_threads`) and names which mechanism added
each extra. Kent 2026-10-30: the ticked white COUNTS and is protected (option
A); the flip is still his.
Related: [[photo-corpus-sxs-2026-10-27]], [[stage0-texture-gate-2026-10-28]].
