---
name: sliver-prune-2026-11-10
description: "2026-11-10 — `sliver_prune` built OFF (Kent on Pooh at 54 mm, \"Sliver fix (Recommended)\"): white runs on the silhouette = page-halo masks, red spike up the arm = a shirt tendril on the drawn crease; acts on enlarged rasters only; plus what the other Pooh symptoms are"
metadata:
  type: project
---

# Sliver prune (`sliver_prune`) — 2026-11-10

Kent, Studio screenshot of Pooh (`images.jpg`, 266 px, the file in gitignored
`scratch_kent/`) at 54 mm: "over digitizing degradation": white stitching on
the right edges and in the middle, a red stitch up the arm, yellow satin on
the feet, the eye, the nose, no outlines round the limbs.

**The trap that cost the first half hour.** The picture on his screen was NOT
the flat lane. The panel said "You set this to flat art" and "Changed since
the last run": the stitches were the earlier AUTOMATIC run (class `gradient`,
30 shapes, 11,036 stitch records). A repro from the panel's words matched
nothing (17,128 stitches). What settled it: the saved project in the Studio's
own `localStorage` (`embstudio:p:<id>` on the dev origin), whose `warnings`
carried `CLASSIFIED_GRADIENT` and whose `crop` and `params` reproduced the
run byte for byte (md5 53c285cd). **Read the stored run's warnings before
believing the panel's lane line.** Flat, had he pressed the button: 164
shapes, 16,497 stitches, 4.3 minutes, every shade band a facet. Worse.

**What each symptom was (automatic lane, 6 colours, 4.4 px/mm, enlarged x1.81).**
- White on the right edge: three masks of the JPEG's page halo, 0.91-0.99
  source px wide, threads 0010 / 0184 / 0184, vectorised to seven shapes
  (0.4-1.6 mm2), sewn as runs. **Fixed by this flag.**
- Red up the arm: the dark crease drawn between arm and head took the
  shirt's label and hung off it, 57 px (7.1 mm), 18.7 dE00 off the shirt.
  Present at every width (40 mm to 80 mm, where there are two). **Fixed.**
- White in the middle: the page gap under the pot (16 mm2), sewn by "Sew
  white areas" (default ON, Kent 2026-10-26). A setting, not built on.
- Nose and tongue: the 6-colour cap. No black slot (nose -> 1233 Pony), the
  9 mm2 tongue merged away. At 9 colours the nose goes dark; HUNNY turns
  olive and reads worse.
- Eye: brow + closed eye weld into one 7.4 mm2 dark read; the bean follows
  its skeleton. Resolution.
- Limb outlines: the art has them, dark brown, 1-2 source px. Only the thick
  pieces read as ink. Resolution. Offered as "Thin outline read", not picked.
- Yellow satin on the feet: a separate 0904 shape (12.9 mm2, 1 mm wide) sewn
  satin over the gold fill, and a border ring broken where the brown outline
  sits. Offered as "Feet satin first", not picked. **Still open.**

**What was built** (`digitizer_core/sliver_prune.py`, one call in
`build_generation` after `resolve_small_regions`, before `vectorize`; flat
and gradient classes). Mask level, so stage 4 traces every neighbour from the
pixels as they end up. Runs after the palette is fitted: no thread moves,
unlike `flat_page_fringe_exclude` ([[flat-page-fringe-2026-11-03]]).
- Page sliver, dropped: mean width <= 1.5 SOURCE px, >= 40% of its rim on
  the border-flood page and >= 20% on other masks, its layer's thread nearer
  the page than the neighbour's and within 20 dE00 of the page.
- Tendril, handed to the mask it has most rim on: what an opening 2 source
  px across removes from a wide mask, >= 4 kernels long, >= 75% of its rim
  on other masks and <= 10% on the page, >= 10 dE00 off its body's core,
  and not a bridge.
Widths are in source pixels (`Prep.input_px_per_mm`): a raster read, not a
stitch value, so gate 1 does not apply.

**The gate that matters: enlarged rasters only (`MIN_ENLARGEMENT` 1.25).**
First sheet run, no gate, moved 5 of 20 at 80 mm, all sources AT the grid
(x1.00): the phone screenshot gave 225 one-pixel "slivers", Golden Tee a
21.6 mm hairline moved for +267 stitches, drone 17 tendrils. At x1.02-1.19
(summit, drone, Becker's large hat at 113.5 mm): 14 slivers and 15 tendrils,
each a one-pixel line along a shading seam. Six flat logos at x2.03-3.25
(Bridge, Golke, Fremont patch, MFab LC, TOAT x2) give nothing at any width
tried. 1.25 is a candidate in the 1.19-1.34 gap (Pooh at 40 mm is 1.34).
The same lesson `flat_page_fringe_soft_ramp` already paid for.

**Measured, OFF -> ON.** 80 mm left-chest sheet
(`tools.dark_ink_flip_sheet --flag sliver_prune`): 20 of 20 DST md5
identical. Pooh (Studio request + his crop): 40 mm 6,157 -> 5,823 st, 24 ->
23 trims; 45.6 mm 8,793 -> 8,713, blocks 7 -> 6; 54 mm 10,929 -> 10,504,
shapes 30 -> 23, trims 36 -> 22, blocks 9 -> 6; 80 mm 21,220 -> 21,099,
trims 35 -> 36. So the only design it is known to move is Pooh: a flip
wants a second low-resolution cartoon first.

**How to apply.** A sub-0.5 mm oddity on a design from a small JPEG: print
`sliver_prune.page_slivers` / `tendrils` at stage 4's door (spy
`pipeline.vectorize`) before touching a stitch tier. Do not lower
`MIN_ENLARGEMENT` to reach a source at the grid.

Related: [[pot-slot-swing-2026-11-03]], [[dark-ink-floor-rescue-2026-11-03]],
[[bridge-anchor-wave-weld-2026-11-10]] (the same class of low-resolution weld,
kept as a manual edit).
