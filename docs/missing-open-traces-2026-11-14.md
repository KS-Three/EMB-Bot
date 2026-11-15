# Missing elements still open: where they go (2026-11-14, evening)

These are the next pins in the missing family of
`docs/missing-invented-traced-2026-11-14.md`, traced with
`PipelineConfig(debug_dir=...)` on main `10d1d863` at 80 mm left chest. Nothing
is built here. Each finding names the stage and the rule, so the next session
starts at the fix.

## heraldic_crest: the eagles' eyes (2 pins, nitpick)

**What is lost.** Each eye is about 12 x 6 source pixels: two white specks
(about 5 px, 0.09 mm2 each) either side of a black pupil (8 px, 0.15 mm2), in
the navy head. The source is 585 px across 80.5 mm, 7.3 px/mm, and the work
grid enlarges it x1.22.

**Stage by stage:**
- Stage 1 (denoised) still has the eye, white and black.
- Stage 2 (labels) does not: two stray pixels remain. The cause is
  `stage2_quantize._majority_filter`. It reassigns every EDGE pixel (one with
  a differently labelled 4-neighbour) to the dominant label among the
  NON-edge pixels in its 3 x 3. A feature 2-3 px across has no interior
  pixel, so all of it takes the head's label; two passes
  (`cfg.aa_iterations`) finish it.
- The module docstring warns that an edge-fraction test alone "would also
  delete legitimately tiny real-color features". The majority filter, which
  runs before that test, does exactly that to anything this small.
- Stage 3 would drop it anyway. Kept through stage 2, each colour piece is
  under the run tier's floors (`RUN_MIN_AREA_MM2` 0.16; loop 2.2 mm). So the
  eye needs two changes, not one.

**Where a fix would go:**
1. In the majority filter: skip an edge pixel that IS its colour, near its
   own cluster centre and far from the neighbour's. An anti-alias pixel is a
   blend on the chord between two centres; the eye's pure white and black
   pixels are not.
2. At stage 3: keep a compound detail. Touching small pieces of other
   colours, ringed by one host, together clear the floors, so keep them as
   one dot.

Both reach every flat design, so they need a corpus check before Kent sees
a sheet. A crest run takes about 12 minutes on the shared laptop.

## heraldic_crest: the crown (1 pin)

This is shape detail, not a missing element. The crown's lobes and scrolls,
about 1 mm each, are rounded and merged. Its keylines are one source pixel
(0.14 mm) of dark brown between the yellow and the navy, under any sewable
width.

The shape-detail worker's family covers it (`docs/shape-detail-traced-2026-11-14.md`,
the inlet and teeth flags). The keylines would need a run tier that sews a
sub-thread line, which the hairline-keyline work (`border_from_outline_hairline_run`)
reads only on a closed outline ring.

## arabic_calligraphy: the stems between leaves (2 pins, nitpick)

**Corrected later the same evening.** The first reading above blamed
stage 4; a mask trace at stage 3 shows the stem never reaches it.

**What the masks show** (stage 3's input at the pin-2 stem; work grid
11.5 px/mm, detail floor 297 px):
- The stem is not one mask. Its pixels split between the leaves' gold
  (layer 0) and the leaves' darker edge gold (layer 1, the art's outline
  round each leaf).
- They arrive as crumbs: on layer 1, one 49 px and one 18 px piece plus
  1-6 px bits; on layer 0, pieces of 6-11 px.
- Together they come to about 120 px, under the chain rescue's 297 px floor
  (`_chained_small_regions`).
- Each piece is the leaves' own ink family, so the contrast rescue
  (`keep_thin_strokes`, more than `merge_delta_e` 6 off its neighbour) does
  not keep it.
- `resolve_small_regions` absorbs every crumb into the leaf with the most
  halo. Of stage 3's output in the window, only the three leaves and one
  23 px layer-1 piece remain.

So the stem becomes a thin spur on one leaf or another, and the leaf's satin
decomposition does not sew a spur that thin. One stem survives elsewhere
because its pieces happened to stay together.

**Where a fix would go:** a same-ink thin line. Crumbs of one ink family
that chain from leaf to leaf (a bridge between two full-size regions of
that family) are a stroke. Sew it as one run or bean line on its skeleton,
the way `bean_dark_ink` sews dark ink, instead of absorbing it piece by
piece. That is a new line tier, not a threshold; the crest's crown keylines
want the same tier.

## Does the Studio's "Flatten shading" tick reach the tonal pins?

`cfg.bevel_ring_fold`, as improved by #1522 and #1535, run ON against OFF on
main `d9699832` (sheets `flatten_*` in
`digitizer/eye_pairs_out/missing-1114/sheets/`).

**Precision Drone, trees and propellers (2 pins): no.**
- Both pins come out the same ON as OFF: the trees are the grey sky's
  lumpy lower edge, and the propellers are grey blades merged into the dark
  body.
- The tick changes the design elsewhere: 14,760 -> 13,604 stitches,
  93 -> 86 trims.
- The pro redraws both: black tree silhouettes against sparse sky lines,
  and blades in black keylines. That is a redraw of tonal art (Phase 4,
  gate 2), not a flattening.

**Isometric icon, shading band (2 pins): partly.**
- ON, the invented dark-red band under the sausage is folded away at both
  pins, and the yellow top band merges into the body.
- But the shaded side then sews as pink satin pieces at several angles,
  which reads messy.
- 10,859 -> 9,733 stitches, 29 -> 27 trims.
- Worth showing Kent beside the tick's own sheets. It is not a cure as it
  stands.

## Not traced

- The gradient mascot's nostril tail (1 pin).
