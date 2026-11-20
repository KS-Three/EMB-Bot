# Flag history: tier B4, edges and alpha (folded 2026-11-20)

Nine switches, all ON by default, folded into the code (the `cfg.X == True` path kept, the
False branch and the `PipelineConfig` field deleted; `docs/flag-audit-2026-11-19.md`). Each
section below is the field's own comment block as it stood in `config.py`, kept for the
evidence and PR pointers. The names are in `RETIRED_FIELDS`, so an old snapshot or a service
request that still sends one is ignored rather than refused.

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

## `subpixel_corner_runs`

```
The read above repaired where its outline reversals start, instead of
switched off under a floor (Kent's ruling 2026-10-11: leave the floor
unset, fix the corners). Diagnosed on Becker at its own 1.8 px/mm,
the 10 worst reversals rendered with their flags
(`docs/native-read-corners-2026-10-11.md`): the corner side-line fit
ran once per flagged VERTEX, so a round turn's run of corners got a
different pair of short tangents each and needled out past the arc
(86 of 129 reversals beside a fitted corner); a vertex the read could
not place stayed at its pixel centre, half a pixel inside every read
neighbour, a notch; and neighbours read along disagreeing normals
crossed. ON: one fit per corner RUN with fold, support and reach
checks; an unread vertex between two reads takes their offset; a
vertex landing behind its predecessor is dropped
(`subpixel.CORNER_RUN_FOLD_PX`). Measured there with bare stage 4:
Becker reversals 7.1 -> 0.9 per 100 mm with right-angle turns 26.5 ->
20.1 (the staircase stays gone); the four golden_tee / hotel_fremont
truth cases at 1.8 / 3 / 5 px/mm lose reversals in all twelve and
move median edge error by -0.004 to +0.003 mm; the synthetic
ladder's rectangles keep their squared corners. Only the native read
(`subpixel_edges_upscaled`) is touched. Raster quantities of the
source; no sew-out has seen it. Byte-identical off.
`tests/test_subpixel_corner_runs.py`.
**FLIPPED ON 2026-10-20, Kent's ruling (via the foreman; MASTER_SCOPE
item 41)** on the measurement above, Becker 7.1 -> 0.9 reversals per
100 mm. No physical constant moved with it. False is the pre-flip
engine (`PRE_FLIP`).
```

## `subpixel_edges`

```
Sub-pixel, anti-alias-aware contour vertices (`digitizer_core/
subpixel.py`; plan `docs/superpowers/plans/2026-09-08-subpixel-edges.md`
§3, PR 2). Stage 4 traces the LABEL mask, so every vertex it hands
Douglas-Peucker is a pixel centre: the polygon carries the raster's
staircase and sits half a pixel inside every filled edge, and the
curve refinement above cannot go under one pixel because it averages
those same centres (`_CURVE_MIN_PX_PER_MM`). The edge's true position
is in the anti-alias ramp the mask thresholded away. ON, each raw
vertex is moved to where the image, sampled along the local normal in
Lab, crosses halfway between its two side colours — accepted only when
that profile is monotonic and crosses once within 0.75 px, else the
pixel centre stays (ringing, texture, a third colour, a stroke under
~3 px with no plateau) — and the SAME simplifier runs on those points
at the same 0.2 mm. Nothing is smoothed (a measured negative,
DOCTRINE). Per ring, near-floor lettering keeps today's polygon
(Kent's 2026-09-03 exemption: the inflation is what keeps those
strokes above the cross floor) and sub-detail shapes keep their 0.5 px
epsilon. The share of a shell's vertices accepted is written to
`meta["subpixel_accepted"]`. The curve refinement above is keyed to
that acceptance (plan §3 step 5, PR 3): a chord whose raw points were
at least 80% accepted is floored at a quarter pixel instead of the
staircase's one (`stage4_vectorize._CURVE_SUBPIXEL_FLOOR_PX`), its
inserted vertex is the midpoint's own sub-pixel point, and the 20
px/mm gate lifts — the floor's reason (the staircase) no longer
applies where the edge was read, so arcs gain vertices at any
resolution, on the chords that earned them, and the polygon follows
its vertices onto the edge instead of sagging between them. A source
stage 1 UPSCALED to the resolution floor is declined whatever this
says: the Lanczos ramp is manufactured and locates the resample's
edge, not the artwork's — the ladder's 200 px rung got worse on every
rectangle (plan §8 decision 3, measured 2026-09-09). Not a physical
constant anywhere (the windows, offsets and floors are raster
quantities, the contrast floor is `merge_delta_e`). DEFAULT ON — Kent's
flip, 2026-09-09 (plan §7 row 4), on the measurement in scope-history's
entries of that day: vertices on the edge at every rung drawn at its
own resolution, the rectangles to 0.01 mm, the circle's boundary
spread 0.057 -> 0.036 mm at 400 px, 45-155% more vertices on real
logos at stitch counts within 3.5%, four borderline ribbons changing
tier (three on drone, one on meadow), and every golden re-captured in
CI for it. False is the pre-flip polygon, byte for byte. Two numbers
travel with the flip as Kent's: `curve_turn_deg` (15 deg is now the
floor under the ring and ribbon; 10 would meet the ladder's criterion
on the ring) and the upscaled regime (declined, above).

**Runtime, measured 2026-09-12 and previously unwritten** — in the
parity harness's config (`fill_density_boost` ON; customers get one
fill pass, so these seconds are not verified for them). On
`machine_hat` (the corpus's largest fill) its OWN cost is **+13.3 s**
of plan time (42.7 -> 56.0 s, `curve_turn_deg` held off). Turning THIS
flag off saves far more — 42.2 s — but only because it also switches
`curve_turn_deg` off: with sub-pixel edges gone the curve pass has
nothing to refine and is byte-for-byte inert (943 vertices, 33,743
stitches, both with and without it). **Do not add this flag's number
to `curve_turn_deg`'s**: the two overlap, and the sum (73 s) is more than
the 42 s they cost together.
The time is paid in `plan_stitches`, not here in `run_stages`: finer
polygons make stage 6's fill do more geometry — see `curve_turn_deg`
for which step. Quality case unaffected; the clock is now on the
record. *(docs/flag-runtime-bills-2026-09-12.md)*
```

## `subpixel_edges_upscaled`

```
The upscaled regime `subpixel_edges` declines, read at the SOURCE's
resolution instead. A source under `min_px_per_mm` reaches stage 4 as
a Lanczos enlargement, and on an alpha cutout not even that: the
`alpha < 128` threshold makes the background mask and a NEAREST
resize of it carries every edge up as a staircase of source pixels —
`becker_marine_logo.png`, a real client logo, is 146 px wide with its
whole shape in alpha, 1.46 px/mm at 100 mm, so every outline and every
MARINE letter sews a 0.68 mm stair. The ramp that locates the edge to
a fraction of a SOURCE pixel is still in the file (Becker's alpha has
256 levels, 17% of its pixels mid-ramp): ON, stage 4 hands each raw
contour vertex down to the source's frame (`Prep.upscale`), reads the
source's own pixels — Lab of the RGB composited over white by alpha,
with alpha itself as a fourth channel so a transparent-to-ink edge has
contrast whatever the ink's colour — with the same windows, plateaus
and area integral `subpixel.py` uses on a native-resolution source,
and brings the moved vertex back up. The chords the normals and
corners are read over scale with the upscale so they span source
pixels, not stair steps. Nothing is smoothed; a vertex the profile
refuses keeps its pixel centre exactly as before. Not upscaled, or
`subpixel_edges` off, this is inert. No physical constant: every
number is a raster quantity of the source. Built 2026-09-18 for Kent's
"outlining non-standard shapes" ask, OFF; **DEFAULT ON the same day —
Kent's flip**, on the ladder's 200 px rung, a synthetic disc's radial
RMS 0.25 -> 0.013 mm, and the Becker renders in scope-history's entry
of that day, with the cost on the table: Becker at 100 mm flips its
outline band fill -> satin into the satin decomposition defect (bare
0 -> 35 mm2) until that arm lands. No committed golden pins an
upscaled source, so the flip moved none; the Becker-keyed tests that
moved are named in that entry. False is the pre-flip polygon — the
staircase — byte for byte.
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

## `border_from_outline`

```
Border from the art's outline (`digitizer_core/art_outline.py`, built
OFF 2026-10-24). The pro's border choice is not a stroke threshold: he
borders a shape when the ART draws an outline round it (BECKER's faces
in their black keyline, MFab's M-FAB in its white one) and satins the
same stroke when it does not (MARINE). Census `tools/outline_census.py`:
kappa 0.76 over 586 shapes on ten paired files. ON, an outline (a region
whose hole holds a body at least as wide as the outline is thick; a
letter's counters, sewn or not, excluded) sews as one satin
loop round each hole at the pro's width -- one per outline, the art
outline's own thickness clamped to `machine.OUTLINE_WIDTH_MM` (1.5-2.5),
out past a thinner art outline but never into a body; where the art
draws it thicker the rest is filled under. Its bodies sew as plain
fills under it, never satin. Wins over `border_by_size` on a shape both
read (no second ring in the body's own colour) and over
`enclosed_white_keyline` on a keyline band that holds an outlined body.
Layout (ruling 2026-10-22: judged in the preview).
**ON since 2026-10-24, Kent's flip** from the wave-2 flip sheet (Becker
small 8,512 / 21 -> 11,100 / 25 with white sewn, faces fill, loops on
top; pro 8,694 / 40). False is the engine as it was, byte for byte;
`tests/conftest.py` PRE_FLIP pins it False.
```

## What went with the switches (2026-11-20)

OFF-arm instruments and tests that could not exist without the switches. Their record is in
the PRs and docs they cite; the files are in git history before this fold.

- `tools/stage0_scale_arms.py` + `tests/test_stage0_scale_arms.py`: the three forms of
  `alpha_edge_extend` against stage 0 (scope-history 2026-09-20, the scale addendum).
- `tools/clip_parent_ink_render.py`: artwork | before | after for `clip_parent_keeps_ink`
  (defect 61, 2026-10-12).
- `tools/studio_raster_census.py`: the four `extend*` arms (`PREFIX_ARMS` is now empty).
- `tests/test_classifier_scale_invariance.py`: the two "record" tests that read the engine with
  `alpha_edge_extend=False` / `alpha_edge_extend_stage0_whole=False` (the drone's invariance
  came through the alpha extension; ENTHUSIAST's 400 px flip was the gate's boundary).
- `tools/outline_census.py digitize`: its OFF arm was `border_from_outline=False`; the baseline
  is now the unguarded rule. The 2026-10-24 OFF caches stay the record.
