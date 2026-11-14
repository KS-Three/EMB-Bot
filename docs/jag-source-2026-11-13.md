# Where the jag enters: Kent's smooth / straight pins, traced by eye (2026-11-13)

**Question (the Director, under Kent's 11-13 order).** Edges that should be
smooth or straight are Kent's most-pinned fault. Find where the jag ENTERS,
spot by spot, by eye; tally his pins by cause; build the one fix the majority
cause calls for, default OFF.

**Answer.** No single cause holds a majority of the 49 pins. Stage 4's chords
(b) hold 18, the source's own pixels (a) 10, and the stitch construction (d)
21, but (d) is three different emitter mechanisms and none of them reaches 15.
(a) and (b) share one cure — redraw the outline as lines and arcs before
any stitch is planned — and together hold 28 of 49. That is built:
`PipelineConfig.outline_redraw_k`, default None (OFF, byte-identical).
Neither pull compensation (c) nor the 12 px/mm renderer (e) is the primary
cause at any pin.

Instrument readings, not quality claims (ROADMAP gate 4): every number below
is one run on one laptop, n = 1 per design.

## Method

`digitizer/tools/jag_strips.py` (new). `capture` runs one design through the
service's own call sequence and pickles each stage's geometry. Stage 3's masks
and stage 5's polygons are caught off `debugviz`, so the run is the same one
`debug_dir` would trace. `strips` cuts one strip per pin: the art's own pixels
at native resolution (nearest-neighbour, so a pixel reads as a pixel), the
working raster, the stage-3 masks, the stage-4 polygon with its vertices, the
stage-5 polygon over stage 4, our needle points and thread, and the pro's
stitches. Pins are read from the three defect-marks sittings (1110, 1111,
1112; `eye_pairs_out/`, gitignored). Today's render is phase-correlated
against the kit's render, so a pin lands where Kent put it: offsets were
under 0.1 mm on every design. Sizes and garments are each kit's own: the pro
jobs' widths (`pro_baseline.JOBS`), and 80 mm left chest for the Commons and
lettering rows.

Pictures: `digitizer/eye_pairs_out/jag-source-1113/` in the primary checkout
(`strips/`, `offon/`, `proto*/`; gitignored).

## The tally: 49 pins, 12 designs

A pin is counted when its note asks for smooth, straight, square, flat, crisp
or round, or for tips that should not be rounded. Kent's shorthand ("#6-#19")
is counted per pin. `#i` below is the pin's INDEX in the sitting's list;
Kent's own numbering is one more (his "#6-#19" on and_pizza = #5-#18 here).
Excluded: and_pizza #0 (a missing gap), Fremont #2 (a rope end's direction),
MFab #6 ("no flow"), and the QR / pixel-art rows (missing shapes). Kent wrote
that Tires' four marks are "the same issue". Traced one by one, only #0's
polygon carries the jag; #1-#3 are clean polygons sewn badly, so they are
counted under (d).

| cause | pins | where (design, source px/mm at that size: pins) |
|---|---:|---|
| **(b) vectorizing**: a clean, smooth mask written back as chords whose 12-20 degree corners the satin follows | **18** | and_pizza 21.9: #5-#18 (14); Bridge 4.41: #10; Gaulke 9.82: #3; Tires 9.27: #0; dot_music 23.9: #2 |
| **(a) source pixels / mask**: the jag is already in the mask | **10** | Becker 1.42 (0.70 mm a pixel): #2, #5 (the A's triangle, 4 x 6 source pixels), #6, #7, #8; MFab 3.85: #0, #1, #7; ProSeal 9.20: #3 (the small M, a blurry 1.5 mm stroke); low_poly 7.92: #0 (stage 3: the thin keylines' junctions eat the triangles' tips) |
| **(d) stitch construction** | **21** | three mechanisms, below |
| (c) pull compensation / overlap | 0 | stage 5 rounds a convex corner by its 0.3 mm buffer everywhere, but at no pin is that what Kent is pointing at |
| (e) the 12 px/mm renderer only | 0 | at Fremont #3 the renderer's round thread ends are part of the scallop, but the stitches make it |

The 21 (d) pins, by mechanism:

| (d) mechanism | pins |
|---|---:|
| satin stitch ENDS form a straight edge or corner, staggered or slanted (Z / I tops and bottoms, the I's serif, the k_line bar's corners, the A's bottom, Fremont's H, ProSeal's corner, Becker's letter feet) | 14: and_pizza #1, #2, #3, #4, #19, #20; k_line #4, #5; Jakarta #8; Fremont #3; ProSeal #2; Becker #10, #11; Gaulke #2 |
| satin rail wobble on a curve or ring | 4: and_pizza #21, #22 (the counters: stage 4 is a 24-gon, but the inner rail is far rougher than that); Becker #12 (the R's bump); Tires #3 |
| a fan of crosses at a cusp or junction | 3: Tires #1, #2; dot_music #1 |

Counted by DESIGN instead of by pin (each design-fault once), the split is
(a) 4 designs, (b) 5, (d) 9, and (d) is still split across its mechanisms.
The pin count is dominated by one design: and_pizza holds 14 of the 18 (b)
pins. Read the 18 as "every bowl of one wordmark", not as 18 independent
sightings.

**What the pro did at the same spots, where a pro file exists.** He redrew
the shape. Becker's border is one even satin column following a true arc,
where the art is a 1.4 mm line drawn in 0.70 mm pixels. MFab's white stripe
is one straight satin column, where the art is a staircase. Tires' and
Bridge's curves are smooth arcs, with a run outline on Tires. The A's counter
is an open trapezoid where the art has 24 pixels. The low-resolution file
was never his edge.

## Spot by spot (the strips)

- **Becker border (#2, #6, #7, #8).** The source line is two pixels wide with
  an anti-aliased ramp. The mask is a staircase of 0.70 mm steps, and the
  stage-4 polygon keeps the stair as short chords, kinks and folds where the
  native read and DP disagree. Stage 5's 0.3 mm buffer rounds each convex
  stair corner. The satin follows every step. Enters at (a), carried through
  (b).
- **Becker A counter (#5).** 4 x 6 source pixels. The polygon is a pentagon
  with a needle; stage 5 shrinks the hole; the satin rounds its top. (a).
- **Becker R (#12).** The polygon is a clean arc: letterform priors already
  refit it. The bump is two rail points a quarter-millimetre past their
  neighbours. (d).
- **and_pizza bowls (#5-#18).** 21.9 px/mm, a mask with stairs of
  0.05 mm. Stage 4 writes each bowl as chords 0.6-1.2 mm long, 5-6 facet
  vertices (12-20 degree turns) per 6 mm window. The satin's outer ends
  follow the chords. (b). The cause is `_refine_curves`' floor of one raster
  pixel: a chord stops splitting once its sagitta is under 0.046 mm, which
  on a 4 mm bowl is a 1.2 mm chord and a 17 degree corner.
- **and_pizza counters (#21, #22).** Stage 4 is a 24-gon. The stitched
  counter is lumpier than that, with wedge cracks: the rails, not the
  polygon (`docs/rail-wobble-cause-2026-09-21.md`). (d).
- **Bridge circle (#10).** 4.41 px/mm JPEG with a smooth ramp. Stage 4's
  chords are 2 mm, with a visible kink at each vertex. (b).
- **Gaulke circle (#3).** 9.82 px/mm, binary art (no anti-aliasing), so the
  source is itself a stair at 0.10 mm. Stage 4 dithers on the stair, then
  takes 3 mm chords. (b).
- **MFab (#0, #1, #7).** 3.85 px/mm with JPEG blur. The white stripes are a
  staircase in the mask and the polygons zigzag. Kent's own note: "matches
  the photo quality". (a).
- **k_line (#4, #5), Jakarta (#8), and_pizza flat tops and bottoms.** Source,
  mask and polygon are dead straight and square. The satin's ends make the
  edge: diagonal crosses ending in a staircase of thread caps. (d).
- **low_poly (#0).** One-pixel keylines between flat triangles. Stage 3
  splits the keylines into fragment masks and their junctions take the
  triangles' tips, before vectorizing. Filed under (a) as "already in the
  mask", but it is segmentation, not resolution.

## The fix: `outline_redraw_k` (`digitizer_core/outline_redraw.py`)

Every region's rings are refit, after letterform priors and before the OCR
read and the house angle, to straight lines and circular arcs. This is the
pen-tool redraw. Each ring is densified, then:

1. Douglas-Peucker chords at the cap;
2. **line / arc runs**: consecutive chords that ONE line explains within the
   cap become that line, and failing a line ONE circle, whatever the sign of
   their turns. A staircase turns left, right, left, so
   `letterform_priors._merge_arcs` (same-sign only) cannot merge it;
3. letterform priors' chamfer drop and same-sign arc merge;
4. rebuild: line-line corners at the exact intersection, so corners get
   SHARPER, and arcs written back finely (letterform priors' 0.02 mm / 0.25 mm
   step);
5. the cap checked both ways. A breach sends the primitives that wrote it
   (and, beside a pass-through piece, its neighbours) back to the trace,
   up to six rounds, before the shape is refused. A shape whose validity or
   hole count would change is refused untouched.

**Cap** = max(k x the source pixel, one working-grid pixel), with k = 0.75 as
in letterform priors. On Becker at 102 mm that is 0.53 mm; on lettering at
22 px/mm it is 0.046 mm. Stage 4's own curve refinement already lets a chord
sit a grid pixel off the arc, and a cap under that (0.034 mm) fitted some
bowls and left most as chords.

**Two regimes, by whether stage 1 upscaled the source** (the same test as
stage 4's `upscaled`):

- **upscaled** (Becker x4, Bridge x1.8, MFab x1.04): the trace is a staircase
  of source pixels, so every run is redrawn, lines and arcs.
- **at its own resolution** (lettering, Gaulke, Tires): the trace already
  carries straight edges and corners to the grid pixel, so only the runs one
  circle explains are rewritten. Straight runs and corners keep stage 4's
  vertices exactly, and a shape with no bowl comes back as the same object
  (`no-arc`). This regime exists because the first build redrew lines on
  crisp art too, and the k_line control showed its satin construction moving
  (below).

**How this differs from what was measured before.**

- DOCTRINE, "Smoothing region polygons to fix ragged edges: NO EFFECT"
  (2026-08-25): that blurred polygons with a Gaussian of a fixed radius in
  mm, and scored it on a raggedness number that turned out to be macro
  sprawl. Here nothing is blurred. Each run is REPLACED by the one line or
  circle that explains it, corners are intersections (sharper, never
  rounder), and the cap is a raster quantity of the source (k source pixels,
  floored at the grid pixel), not a radius in mm. The check is at the spots
  Kent pinned. A feature smaller than the cap cannot survive. On Becker that
  is 0.53 mm, under the source's own 0.70 mm pixel, which could not resolve
  the feature anyway.
- The 2026-10-10 low-res research ranked "iso-contour on the native coverage
  field" first. **It was built**, as `coverage_edges` (PR #818, the
  tracer head-to-head addendum). Kent ruled it no on 2026-10-12: it narrowed
  three MARINE counter slots below one thread width. It is deprecated in
  `config.py`. The redraw does not re-read the edge from coverage. It refits
  the stage-4 trace and moves no point past the cap from it.
- `letterform_priors` (ON at 0.75): the same geometry, but for text-tagged
  letters on an upscaled upload only, under a word prior. The redraw leaves a
  letter it refit alone (`meta["outline_redraw"] = "letterform"`) and does
  the rest: borders, circles, counters, every shape on a clean upload.

No physical constant (ROADMAP gate 1): the cap is a raster quantity, and the
arc rules are letterform priors'. No sew-out has seen it.

## Proof

RESULTS_PLACEHOLDER

## Not fixed, and where it goes next

- **(d) is untouched** and is the larger share of Kent's pins. The biggest
  mechanism is satin ends forming a straight edge (14 pins): the pro sews a
  flat top with stitches parallel to it, or squares the column's ends. Next
  are rail wobble on rings (4) and fans at cusps (3). Each is an emitter fix
  in `stage6_satin.py` / the Column lane. None of them is a polygon problem,
  and the redraw does not touch them.
- **A satin seam can open where the redraw moves it.** On and_pizza ON two
  wedge slits open in the "p" (at the stem-bowl join, and at the bowl's top
  right), where OFF had none. Stage 4/5 polygons are clean at both spots:
  this is the Column lane's seam placement moving with the geometry, the
  same wedge defect OFF shows elsewhere (its counter, its "&"). Bare fabric
  inside the art is LOWER ON (table above). It is the open (d) seam defect,
  not new geometry.
- low_poly's tips are stage 3's, and the redraw cannot bring back a tip the
  mask lost.
