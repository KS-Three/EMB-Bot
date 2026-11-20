# Flag history: tier B2, image prep and clip/keyline (folded 2026-11-20)

Six switches, all ON by default, folded into the code (ON path kept, False branch and field deleted; `docs/flag-audit-2026-11-19.md`). Each section is the field's own comment block as it stood in `config.py`. The names are in `RETIRED_FIELDS`. Skipped from this batch (OFF arm is a pinned baseline, not a deletable arm): `photo_prep`, `photo_prep_background_removal`, `strip_letterbox`, `subpixel_edges`, `subpixel_edges_upscaled`, `subpixel_corner_runs`.

## `alpha_edge_extend`

```
Stage 1 stops reading the RGB under an alpha cutout's transparency.
The shape of a cutout lives in alpha; the RGB underneath is whatever
the exporter (or a browser canvas) left, and both filters above read
it — the bilateral denoise and the Lanczos floor upscale blur it into
the edge pixels the design sews. Measured 2026-09-20 on Becker: the
file (one colour everywhere, the shape in alpha) reads flat / 18
regions / 8,334 stitches / 59 trims; the SAME alpha with black under
it reads gradient / 151 / 15,318 / 175 (DOCTRINE 2026-09-19/20 — the
Studio's canvas did exactly that until the panel started sending the
file, and any exporter can). ON, every stage reads nearest-opaque
colour under every non-opaque pixel (`stage1_prep.extend_opaque_colour`)
— every stage, because stage 0's gradient signal and stage 2's
segmentation run kernels over the whole raster and mask afterwards; a
first cut that put the file's own colour back under alpha < 128 after
the two filters left Becker-with-black-underneath at gradient / 146
regions. The two readers that want the file's own colour there —
`bg_edge_rgb`, stage 2's anti-alias endpoint, and preflight's
`GROUND_SEWN` border colour — read it from `Prep.raw_rgb`; the naive
whole-image fill that gave them the extended colour sewed Fremont's
ground (scope-history 2026-09-20 §E). Not a physical constant: it
changes which pixels the stages read, never a fabric number. Built OFF
2026-09-20 (Kent's pick), measured in three forms on the census
(`tools/studio_raster_census.py`, arms `extend*`, raster
`native_black`), and FLIPPED ON the same day (Kent) in the gated form
below: with `alpha_edge_extend_upscaled_only` the extension runs only
where the resolution-floor upscale will, the one reader measured to
smear the under-alpha colour into the sewn edge. OFF is the pre-flip
engine byte for byte; a test whose numbers were read on it holds OFF.
```

## `alpha_edge_extend_stage0_whole`

```
Stage 0 classifies on the whole-image extension wherever the file has
alpha, gate or no gate; stage 1 keeps the gate above for the pixels it
sews. Measured 2026-09-20 (`tools/stage0_scale_arms.py`, scope-history,
the scale addendum) on the scale test's six fixtures and the nine real
logos: the `photo_*` misroutes on downscaled alpha cutouts are
`unique_color_mass` reading the RGB under the alpha (drone 0.335 at
250 px against 0.091 extended; ENTHUSIAST 0.34-0.51 against 0.12-0.22),
and the gate left one reachable — ENTHUSIAST at 400 px reads
`photo_scene`, exactly the pre-flip reading, between `gradient` at 320
and 500 — because the extension switches off where the art box crosses
the floor. On the nine logos at native size no class moves under any
arm, so classification gives up nothing by reading whole-image, and the
sewn pixels are untouched: this flag changes stage 0's input only. The
flat -> gradient flips on downscale are the pixel-absolute signal
windows and are NOT this flag's; the recalibration spec keeps them
(ROADMAP gate 2 — no threshold moved here). ON 2026-09-20 (Kent).
```

## `alpha_edge_extend_upscaled_only`

```
The extension only where the resolution-floor upscale will run (the
artwork under `min_px_per_mm` at the target width, decided the same
way in stage 0 and stage 1 — `alpha_edge.upscale_expected`). Measured
2026-09-20: the Lanczos upscale is the reader that smeared black under
Becker's alpha into 59 -> 157 trims; the three cutouts above the floor
read the same from the file and from black and paid for the
whole-image extension (ENTHUSIAST +5 trims, drone +33, Fremont +78 mm
of exposed travel). Built 2026-09-20 on Kent's pick, measured beside
the other two forms in scope-history: Becker's six rows read the cure
(8,440 stitches / 54 trims / flat / B from the file, from black under
its alpha and from the Studio raster alike) and the other nine rows
are byte-identical to OFF. ON 2026-09-20 (Kent), with
`alpha_edge_extend`; the whole-image form is `alpha_edge_extend=True`
with this False.
```

## `clip_parent_keeps_ink`

```
Stage 5 clips each grown shape by the colours already sewn, and the
clip can cut it in two: a later colour whose artwork overlaps an
earlier one's comes out as several polygons. False (shipped) keeps only
the largest (`_largest_polygon`) and drops the rest silently -- drone's
`S426e81b9` loses a 9 mm² piece that way (MASTER_SCOPE defect 61) -- and
"largest" is by sewn area, so it can keep a piece of underlap tongue
and drop the shape's ink. Two settings, one per half of the cure:

`clip_parent_keeps_ink` (default TRUE, Kent's ruling 2026-10-12): after a
split the shape keeps the piece carrying the most ARTWORK, the largest
among equals, not the piece with the most sewn area -- a pure tongue
piece is never kept over the ink. Wherever the largest piece is also
the inkiest, the shape sews what it always did; it adds no region and
no warning. False is `_largest_polygon`, byte for byte.
```

## `enclosed_alpha_hole_parts`

```
A TRANSPARENT hole (alpha path) that the vectorizer has cut into
several colour regions. `tag_enclosed_background` asks two ratios of
one region against one connected component of stage 1's enclosed
mask: the region is mostly the component, AND the component is mostly
the region. The second ratio is what keeps a region that merely
swallows a small enclosed sliver from being hidden — right for a hole
found by COLOUR. On the alpha path the hole's pixels carry no colour
of their own (`enclosed_colour_unknown`); `alpha_edge_extend` paints
them with the nearest opaque colour, so a counter inside a two-tone
letter is painted in two tones and vectorizes as two regions, each
under the 0.6 share of its hole, and BOTH fail open and sew in the
letter's thread. Measured 2026-10-23 on Precision Drone at the pro's
62.6 mm (`docs/lettering-5-10mm-2026-10-23.md`): PRECISION's O (6.3 mm
cap) carries its 4.1 x 3.4 mm counter in its polygon, two regions of
7.1 and 4.9 mm² sit in it, neither tagged, and the O sews as a solid
blob; the P and R counters (one region each) are tagged and stay open.
ON (default since Kent's ruling 2026-10-23), a region on the alpha path is tagged when IT is mostly inside one
transparent component (the first ratio alone): nothing with a colour
of its own can sit under alpha < 128, so the second ratio protects
nothing there. The no-alpha path keeps both ratios. Layout, not a
fabric number (ruling 2026-10-22: judged in the preview). OFF is the
engine as it was, byte for byte.
```

## `white_keyline_art_recipe`

```
`white_keyline_art_recipe` (BUILT OFF 2026-10-26, `white_keyline_art`):
the white-keyline recipe -- `silhouette_underfill`, `sew_enclosed_white`,
`enclosed_white_keyline`, `silhouette_underfill_panels`,
`outline_loop_mitre`, `silhouette_underfill_rim` -- turns ON by itself,
but only on white-keyline art: a dark host round a white field that
outlines letters (MFab's keyline round M-FAB). Kent, 2026-10-26: "Gate to
MFab art first (Recommended)" -- as a default for all art the recipe
damaged four of 20 other paired jobs (Gaulke, Tires, ProSeal, Becker).
Read on the stage-4 regions in `finish_generation`, before the recipe's
first switch acts; it holds on MFab hat and LC and on none of the other
20. ON by default since 2026-10-26, Kent's ruling, verbatim: "Gate to
MFab art first (Recommended)" -- "The recipe turns on by default only
where a dark shape carries white outlines round letters (the panels lane
already detects this). Only MFab changes now." False is the off arm.
Tests: `tests/test_white_keyline_art.py`.
```
