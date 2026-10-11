# Why small lettering sews as one bar per letter, and `keep_counters`

Kent's pick 2026-10-02, on bridge's "BAR & RESTAURANT" once the working grid
(`work_px_per_mm` 8.0) had brought the letters back: each one still sews as a
single satin bar. Three questions, in the order they were answered. Windows,
same machine for every pair; scratch probes, not committed.

## 1. Is it the stitch tier? No

Clean lettering — Arial Bold "BAR & RESTAURANT", 4.0 mm caps, teal — handed
to the engine at the size bridge's words are (`white-vs-coloured-ground.jpg`):

| source | ground | counters in the polygons | sews as |
|---|---|---|---|
| 40 px/mm PNG | white | 9 | letters, per-stroke satin, cross 1.1–1.35 mm |
| 3.5 px/mm PNG, traced at 8 | white | 7 | letters |
| 3.5 px/mm PNG, traced at 8 | yellow panel | **0** | silhouettes; B, A, R as blobs |
| 3.5 px/mm JPEG 4:2:0, traced at 8 | yellow panel | 0 | the same, slightly fatter |
| bridge at 80 mm | its own yellow | 0 in 11 regions | one bar per letter |
| bridge, `denoise=False` | | 3 | worse: teal slivers round the ring, trims 98 → 108 |

Given letter-shaped polygons the satin tier sews 4 mm letters. What it is
given on a coloured ground has no counters. The JPEG adds little; the denoise
is not it.

## 2. Where do the counters go? The small-region floor

On white a counter is background and never a region. On a coloured ground it
is a region of the ground's colour, and every counter of a 4 mm letter is
under `min_detail_mm`² = 2.25 mm². Traced on the yellow-panel PNG, the teal
ink's enclosed gaps after each step of the gradient lane's stage 2:

| step | counters | teal mm² |
|---|---|---|
| prep raster, by colour | 10 (0.56–1.88 mm²) | 84 |
| SEEDS + RAG merge | 5 | 104 |
| `snap_region_edges` | 9 — it recovers four | 106 |
| `resolve_small_regions` | **0** — `ABSORBED_SMALL_SHAPES` count 9 | 117 |

`stage3_segment.resolve_small_regions`, `min_area_px = (cfg.min_detail_mm *
px_per_mm) ** 2`: a sub-floor region is absorbed into the neighbour holding
most of its ring, and an enclosed gap's only neighbour is the letter round
it. The floor asks whether a shape is big enough to sew. A counter is not a
shape to sew.

Bridge loses its counters a step earlier as well. By colour only one is
visible in the prep raster at all; two leave stage 2 (0.47 and 0.56 mm²) and
stage 4's hole floor (`min_detail_mm`² × 0.25 = 0.5625 mm²) drops both.

## 3. `cfg.keep_counters` — built OFF

A sub-floor region about to be absorbed is kept out of its neighbour when
one region holds nine tenths of its one-pixel ring AND it reads as the
ground that region sits on: nearer the colour of the encloser's largest
other neighbour than the encloser's own. The letter's polygon carries the
hole. Logo classes only — the photo classes keep today's path.

What goes IN the hole is the engine's existing answer, unchanged: a gap the
run tier can sew (the rescue `keep_thin_strokes` already runs — about
1.1 mm across and up) is sewn as a small bean in its own thread, exactly as
a crisp 1.2 mm gap is today with the flag off; a smaller one is tagged
`counter` and `enclosed_background` and left unsewn, the cloth showing.
The gate is asked last, of a region about to be absorbed and of nothing
else. The first cut asked it first and took thread away that the engine
lays today — the yellow in the bowl of bridge's script "B", a dark detail on
drone's orange — which the corpus sheet caught.

`panel-png-off-vs-on.jpg`, `panel-jpeg-off-vs-on.jpg`:

| fixture | counters | teal mm² | stitches | trims |
|---|---|---|---|---|
| yellow panel, PNG | 0 → 9 | 112.4 → 100.5 | 3,798 → 4,253 | 22 → 25 |
| yellow panel, JPEG 4:2:0 | 0 → 3 | 112.2 → 108.7 | 5,178 → 5,247 | 26 → 29 |
| bridge at 80 mm, six colours | 0 → 0 | identical | identical | identical |

On the PNG panel every letter sews stroke by stroke and the words read;
three of the nine kept gaps (the three A's) carry a small lime bean, the
other six are open. That bean is where the trims go.

**What it does not do**, and the pictures show each:

- **Bridge does not move.** Its counters are closed in the raster before any
  region exists (`bridge-teal-polygons-vs-stitches.jpg`). It needs a better
  read of the counters as well — the 2026-10-02 review's luma-led matte is
  the candidate — and stage 4's hole floor to let a 0.5 mm² counter through.
  Neither is built here.
- **It does not put the ground's thread in the counter.** A small one shows
  the cloth; a larger one gets a bean in whatever thread its blended colour
  snapped to (lime on the yellow panel — a third cone for three dots). The
  right answer is the ground's fill running under small lettering, which is
  a sequencing change and not this flag.
- **The engine already keeps a crisp gap of 1.2 mm**, flag off, both lanes
  (four blocks with square gaps: four holes). What the floor takes is the
  gap under about 1.1 mm or the one a 3.5 px/mm file has blurred.
- **About half of these counters are narrower than the 1.0 mm two facing
  rails close on pique** (0.3 mm pull a side plus a 0.4 mm thread). The gain
  to expect on cloth is the letter's structure — strokes sewn as strokes —
  more than daylight in the counter. Only a sew-out says.
- One typeface, one synthetic panel. No real logo in the corpus changes
  for the better; the corpus table below is its cost.

## The corpus

`tools/flip_sheet.py run --arm off --arm counters` — 26 fixtures at 80 mm,
`left_chest`, the engine's default twelve colours, Windows:

| | |
|---|---|
| identical | 25 of 26 |
| moved | `photo/logo_bridge_bar.jpg`: +56 stitches, −1 trim, raw grade −98 → −80 (F both) — one 0.8 mm² olive speck inside a teal letter, sewn by the rescue instead of absorbed |
| cones, blocks, colour stops | +0 everywhere |

The first cut — the gate asked before the rescue — moved two: bridge's "B"
bowl lost its sewn yellow and drone's orange lost a dark detail (net −26
stitches, −3 trims, both wrong). That is the cost of asking it first.

*(measured 2026-10-02 — scratch probes over `stage2_photo_segment.segment`
and `resolve_small_regions`; `tools/flip_sheet.py run --arm off --arm
counters`; `tests/test_keep_counters.py`)*
