---
name: placement-axis-sizing-2026-10-28
description: "#1159 (merged 2026-10-28): a digitized image's default size is the most that fits WHERE it sits on the garment — `PLACEMENTS` table in src/garments.js, three pro-measured boxes untouched, every other row `seeded` and Kent's to correct; upload fits the box, a typed width never re-fits; live W x H mm/in badge on canvas resize; request contract unchanged"
metadata:
  type: project
---

Kent, 2026-10-27: the Studio's "suggested" size only ever meant the hoop; a
digitized image should take its size from WHERE on the garment it sits, as the
most that fits there, with live mm readouts while resizing. #1159, three parts.

- **Placement axis (`src/garments.js`)**: `PLACEMENTS` (max box mm + source
  comment per row), `GARMENT_PLACEMENTS` (default first; the default carries the
  garment's own id, so every pre-placement project resolves to the box it always
  had), `resolvePlacement(garmentId, placementId)`. **The three pro boxes are
  untouched**, by reference to `PRO_PLACEMENT_MM`: hat_front 113.5 x 64.0 (12
  hats); left_chest 96.0 x 76.5, area 5,800 (7 LCs); beanie 94.5 x 56.0.
  **Every other row is `seeded`** (inch table or a decorator chart, not a
  measurement) and Kent's to correct: hat_front_left/right 57.2 x 50.8, hat_side
  63.5 x 38.1, hat_rear 88.9 x 38.1, right_chest = LC mirrored, full_back 304.8
  x 304.8, upper_back 254.0 x 76.2, jacket_back 304.8 x 254.0, sleeve 76.2 x
  76.2, beanie_cuff 101.6 x 44.5. `project.placementId` (null = default) is
  additive like `hoopId`. **Request contract untouched**: no `placement_id` on
  the wire; `target_width_mm` already carries the chosen size; the fixture
  regenerates byte-identical.
- **Default size from the placement (`lib/placement.js`)**: `fitTargetWidthMm`
  fits the cropped aspect into the box, hoop cap and LC area cap included,
  10-400 mm to a tenth. An upload starts at the fit instead of the flat 80;
  `sourcePx` is kept so a garment or placement change re-fits; a typed or
  dragged width (`widthTyped`) is never re-fitted. `SizePanel` and
  `EmbroideryField` clamps read the box (a hat front clamps at 113.5, not 127).
  Nothing re-digitizes on its own (staleness as before, Kent 10-05, 10-25).
  Live: Hat Centered fits "Sample" to 114 x 24 mm, 5x7 hoop; Rear 89 x 19, 4x4.
- **Badge**: `EmbroideryField sizeBadge`, text from `estimate.js
  resizeBadgeText`: `79 x 17 mm (3.13 x 0.68 in) · x +0.0 · y +0.0 mm`, plus
  "· same width" on a snap; gone on release.

**Traps:** three e2e specs had pinned the old 80 mm. `size-cap-note` now reads
the LC cap as the pro's 96 mm (3.78 in); `digitize-shape-identity` and
`digitize-stale-edits` type 80 first (`setDesignWidth`) because a Tote auto-fits
two-squares.png to 198 mm, where the service promotes the white ground to a
third row. Not done: the canvas does not draw the placement box; `digitize.js`'s
typed-width clamp still reads the inch pair for default placements.

**Why:** the pro sizes to the placement ([[garment-size-like-pro-2026-10-26]]);
the hoop was never the constraint Kent meant.

**How to apply:** a new size bound goes in `PLACEMENTS` with its source; a
`seeded` row is a placeholder, not a measurement, and correcting one is Kent's.
Read the garment through `resolvePlacement`, never `garmentId` alone.
Related: [[cap-frame-height-2026-10-26]].
