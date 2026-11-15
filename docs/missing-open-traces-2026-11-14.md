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

**Stage by stage:**
- At stage 3 each stem is its own small region of the leaves' thread,
  between two leaves.
- At stage 4 one stem survives as a thin line; the other is gone. The run
  reports `DROPPED_SMALL_SHAPES` 12, all small, largest 3.53 mm2.
- Stage 5 and the stitches carry only the survivor.

So the stem is dropped as a small same-thread piece at stage 4, not by the
contrast rescue (it is the leaves' own colour) and not by stage 5's clip.
The exact rule was not reached. The next step is a region trace of which
`DROPPED_SMALL_SHAPES` piece sits under pin 2 (70.4, 9.8) and pin 3
(6.7, 15.9), and whether merging it into the leaf it touches
(`SAME_THREAD_SHAPES_MERGED` fires 3 times on this design) would keep it.

## Not traced

- Isometric icon's shading band (2 pins): stage 2 tonal.
- Precision Drone's trees and propellers (2 pins): tonal art; Phase 4 and
  gate 2.
- The gradient mascot's nostril tail (1 pin).
