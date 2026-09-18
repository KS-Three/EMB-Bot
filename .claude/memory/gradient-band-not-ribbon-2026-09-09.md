---
name: gradient-band-not-ribbon-2026-09-09
description: The icon's "golden stitching that looks different" was a 2 mm gradient slice sewn as a satin column; Kent ruled a gradient band is not a ribbon. Two rules failed before one worked — the band is defined by the PIXELS at its edge (a soft cut, not an edge), the probe needs a pixel floor, and the band must inherit its parent's fill angle or it still reads as its own texture.
metadata:
  type: project
---

**What Kent saw (2026-09-09, after #439):** *"any idea what the yellow/golden
stitching looks different than everything else?"* One shape: Brother 209
Tangerine, 37 mm², ~1.25 mm mean width, a crescent the quantizer cut out of the
gradient's orange→yellow run, against the white ring. `classify_ribbon` said
`promoted_ribbon` → one satin column, 41 crosses across it in a field of
diagonal tatami, both tapered tips unsewn. Second thing in the same picture:
the golden 208 Orange FILL's rows ran at 148° beside Vermilion at 112–122° —
`Fill angle: Auto (per shape)` picks per shape; nine angles on one icon.

**Kent's ruling (three options put to him):** engine rule — a gradient band is
not a ribbon; refuse satin, sew it as tatami like its neighbours. Not taken:
per-shape tier override on screen (by hand every time), drop to 5 colours.

**Two rules failed before one worked — read these before touching it:**

1. *"Its colour lies between its two neighbours' colours."* Tangerine IS a
   Lab interpolation of Vermilion→Orange (t 0.74, 3 units off the line) — but
   its two SPATIAL neighbours are Vermilion (62%) and the White ring (38%):
   the ring cuts the gradient off, Orange never touches it. Off by 31. The
   rule failed on the very shape it was written for. Also chart-snapping on
   a 40-colour chart breaks collinearity (10.3 off on a synthetic that was
   exactly collinear in source RGB).
2. *Flat-panel synthetic fixtures are not gradients.* Three flat panels with
   hard steps are three strokes side by side; the fixture said "band" and the
   engine (correctly) said "no".

**What works — the pixels at the edge:** a stroke's outline is an edge in the
artwork; a band's outline is a line the quantizer drew through a smooth
gradient. `gradient_band.soft_share` probes 0.4 mm inside and outside every
boundary sample of every ribbon-shaped region (width ≤ satin cap, aspect ≥ 3)
in stage 1's prepared image and compares Lab. Measured on the icon at
62.5 px/mm: a cut through the gradient reads **1.2–5.3** (p10–p90, four
shapes); an edge against the white ring reads **73–84**. `BAND_SOFT_DE` 12
sits in a thirteen-fold gap.

**The threshold on the share is 0.35, not 0.5 — derived, not tuned.** A
ribbon with ONE gradient side (the crescent: gradient one side, ring the other)
has soft share L/(2L+2w): 0.375 at the aspect floor of 3, **0.47 measured on
the crescent** (118 samples), → 0.5. A stroke reads ~0. At 0.5 the rule
missed the crescent by 0.03.

**The probe needs a SOURCE-pixel floor (`_PROBE_MIN_PX` 2.5 /
`Prep.input_px_per_mm`) or every edge is soft.** Gaulke's 0.06 mm hairlines
got a 0.02 mm probe → 0.7–1.0. Stage 1 Lanczos-upscales low-res sources
(Becker 1.5 → 4 px/mm) and the upscale manufactures pixels without narrowing
the ramp, so the floor counts INPUT pixels; a region whose third-width cannot
hold 2.5 of them is unjudgeable and left alone (Becker entirely, at 80 mm).

**Becker's letters read soft 1.00 for a DIFFERENT reason first: alpha.** It
is an alpha-cutout PNG, and the RGB under transparency is whatever the
exporter left — the letters' own dark. 97% of the prepared image is one
colour; both probes read (35,31,32) everywhere. A probe that lands in
`bg_mask` is hard whatever the colours say — the artwork ends there. The
mm↔px transform itself was right (overlay checked on Becker); the icon is a
centred square, so a wrong centre would never have shown there anyway.

**A bevel is soft at one scale and a gradient at two.** The drone badge's
extruded lettering (P, R, N faces with a shaded shadow along one edge) read
0.41–0.47 at the near probe — exactly a one-sided band — and were demoted.
A FAR probe 1.2 mm further out (`BAND_FAR_MM`, tolerance 20) drops the P to
0.31 but the R and N stay 0.39–0.40: the extrusion is itself shaded, smooth
over 2 mm. What separates them is the NEIGHBOUR across the soft side: the
crescent's is the 484 mm² vermilion fill (a slice sits beside its sweep), a
letter face's is its own extrusion — another ribbon by the classifier's two
shape gates. Kent's words were "between fills"; made literal, the parent must
not be ribbon-shaped. Drone: 25 judged, 0 tagged. Cost: a photo forced flat
whose slices are all thin keeps its satin slices (no regression from today).

**Sewing it as fill is only half the ruling.** Tagged and sewn tatami, the
crescent's own auto angle ran ACROSS it (140 rows of 1.25 mm at 90°) beside
Vermilion at 112° — still its own texture. `stage7_sequence._fill_angle_deg`
(the five inline precedence expressions collapsed into one function) follows
`meta["gradient_band_of"]` — the neighbour across the most soft samples — to
the parent's angle, computing `best_fill_angle_deg` on the PARENT's compensated
polygon at this fill's `row_mm` when the parent has no override: the identical
call stage 6 makes for the parent, so the rows are parallel by construction.

**Wiring:** `cfg.gradient_band_fill` (default ON, flat lane only, `False`
byte-identical); tags set in `pipeline.finish_generation` with `p.rgb` in
hand; `is_gradient_band` read by `stage5_overlap._comp_axis`,
`stage7_sequence._sews_satin` and `stitch_one` before the classifier; explicit
`tier: "satin"` still wins; `GRADIENT_BANDS_AS_FILL` names the shapes;
`meta["gradient_band_soft"]` on every judged candidate is the instrument;
`tools/gradient_bands.py --all --render` is the corpus survey.

Related: [[border-seam-ownership-2026-09-09]] (same session, same icon),
[[satin-gate-attribution]] (the `promoted_ribbon` path this refuses for bands),
[[classifier-stability-2026-09-03]] (why a verdict change ships with a survey).
