---
name: blend-band-2026-11-14
description: flat_blend_band_any_scale, ON since 11-14 (Kent "Flip ON") - a JPEG blend rim between two inks sewed as its own thread on NOT-enlarged rasters because flat_ramp_blend_dissolve's 2nd round ran only on enlarged ones; ON 2 px band, Lab or RGB chord, band pixels to nearest non-band pixel
metadata:
  type: project
---

Agent-eye class 8 ("wrong thread colour") traced 2026-11-14 with the flat lane's
own stage-2 loop instrumented (`stage2_quantize._quantize_population`):

- **silhouette_logo** (JPEG kept at 13.65 px/mm): mint rim round the white
  letters (sewn Swiss Ivy 5422) is a blend by colour, 5.4 dE off green-white
  (gate 6.0), but its edge fraction is 0.64 against `aa_phantom_edge_frac`
  0.9; bear ring (Green Dust) 3.8 dE, edge 0.36. The second round
  (`flat_ramp_blend_dissolve`, ON) reads 0.98 / 0.95 at 1-2 px but never ran:
  `ramp_px` is set only for ENLARGED rasters.
- **ProSeal**: Spearmint 0.33 mm band over the teal bar, edge 0.65, 6.3 dE off
  the Lab chord (on the RGB one, read only when enlarged).
- **Not this:** Drone's bezel (gradient lane, real metallic shading;
  `line_chain_one_thread` ruled OFF), (hed)p.e.'s e (a later re-snap,
  `resnap_hairline_never_lightens` ruled OFF: never re-propose).

**Built OFF, ON since Kent 2026-11-14** ("Flip ON", accepting the silhouette logo's
green field fill turning 90 degrees; PRE_FLIP pins it False):
`flat_blend_band_any_scale` runs the round on non-enlarged flat
rasters, `BLEND_BAND_PX` 2, Lab OR RGB chord. **Join per pixel, not per
cluster:** each band pixel takes its nearest non-band pixel's label, the
PAGE included (all-ink fattened ProSeal's hex cells into their white gaps,
closed downstream). The
cluster fold, tried first, painted every speck of that colour (ProSeal's
subline grew a teal N). **Round one's blends too, once a band dissolves:**
they go to the nearest KEPT centre in Lab, and with the pale band gone that
is the teal, so the black letters' grey anti-alias edge went teal (the
same teal I and N). **Sources must be big and thick:** a band pixel joins
only a piece over stage 4's hole floor that survives a 1 px erosion; else
silhouette's disc-edge pale row (letter colour) swallowed the mint beside
it and sewed white strips on the green border.

**How to apply:** a stray thread on an edge: read the cluster's edge fraction
at 1-3 px depth and its chord residual in Lab AND RGB before blaming the
palette; ask whether the raster was enlarged. Related:
[[flat-fringe-soft-ramp-2026-11-06]], [[border-colour-change-2026-11-11]].
