# Flatten shading: what the pro did on Golden Tee, read stitch by stitch (2026-11-14)

Kent, 2026-11-14: "I want it exactly like the pros." The Studio's "Flatten shading" tick
(`cfg.bevel_ring_fold`, `digitizer_core/bevel_fold.py`, built 2026-11-13 in #1486, the tick
since #1508, engine default OFF) made Golden Tee cleaner but left two yellows, black rings
and a lost orange side band. This note reads the pro's own file element by element, names the
rule behind each difference in terms the engine can compute from the art, and records what
the fold now does. No pro file, render or art is committed; the sheets are under
`digitizer/eye_pairs_out/flatten-gap-1114/sheets/` (gitignored).

**How it was read.** The pro's `GOLF HAT.PES` through `tools/pro_parity/prep_all.decode` (blocks,
needle-down runs, the breaks between them), each run's stitch character from 12-stitch windows
(`inpiece_cuts.character`'s thresholds), each block drawn alone over the art. Our side: the
Studio request at 74.9 mm on `hat_front` through `tools.pro_pair.digitize`, on main 85abe7d0.

## 1. Golden Tee: the pro's file

3 threads (white #f0f0f0, gold #fe9e32, black), 7 blocks, 5,973 stitches.

| order | thread | element in the art | what the art draws there | how he sews it |
|---|---|---|---|---|
| 1 | white | GT faces (G 1,101 st, T 669) | white face | one tatami per face, under everything that follows |
| 2 | gold | GT bevel ring (G 516, T 406) | gold ramp extrusion on the lower/left sides, a cream highlight on the top/right edges, a red keyline on the right | ONE satin band all round each letter, inside the outline; no red, no cream |
| 3 | black | GT outline (G 601, T 377), TM (29), a 38-stitch piece of the G's outline seen through GOLF's G | black outline, thicker on the shadow side | satin; the TM a run |
| 4 | gold | GOLF (G+O 445, L 107, F 145) | gold ramp (yellow tops, orange bottoms), a dark teal extrusion, cream highlight slivers, a thin red keyline, a grey drop shadow, light-grey shading in the counters | one satin per letter, the face only; extrusion, keyline, highlights, shadow and counter shading are all left as garment |
| 5 | white | ball crescent | white between a hairline and the black arc | one satin band |
| 6 | black | ball arc 444, tee shadow 327 | black | satin |
| 7 | gold | tee | plain yellow (no ramp) | satin, in the SAME gold as GOLF and the GT ring |

**Merged into one thread:** every gold and yellow tone (GOLF's ramp, the GT bevel, the tee's
plain yellow) and, on the GT, the red keyline and the cream highlight with it. **Dropped:** GOLF's
teal extrusion, GOLF's drop shadow, the light-grey shading inside GOLF's counters, every cream
highlight and red keyline on GOLF. **Kept as their own shape:** the GT's whole bevel ring (the
"orange side band"), the GT outline, the tee's black shadow, the ball arc. **Fill vs satin:** only
the two GT faces are fill; everything else is satin; the TM is a run.

## 2. Precision Drone's ring, and the crest

**Drone (pro: 23 blocks, 8 threads).** The frame ring is one dark-slate satin band (#293133,
block 13) between two black satin rails (block 14, both edges). The art's silver bevel arcs are
not sewn. Ours with the tick on (since 11-13) folds the arcs into a black ring: one colour, which
is what pin 3 asked for; the pro's slate body with black rails is a second thread we do not split
out (open, below).

**Heraldic crest (no pro file).** Must-not-break: its checkered crescents, the eagles' two blues
and the rib shading.

## 3. Each difference, the rule, and where it is checked

Widths in mm at the sewn size, colours CIEDE2000; no fabric constant (ROADMAP gate 1 does not
apply). All inside `apply_bevel_fold`, so all behind the tick.

| # | ours with the tick, 11-13 | the pro | rule, computed from the art | Drone | crest |
|---|---|---|---|---|---|
| 1 | GT's gold bevel folded INTO the black outline (it was the only parent that dwarfed it: the white face is never a parent); its red keyline and cream highlight kept their own threads | one gold satin ring between face and outline | **Bevel ring.** From a face (a region in the page's own ink, or `enclosed_background`), the bands touching it and the bands touching those (mostly off the page, not in the darkest ink, not cap-substituted) are its bevel ring when the ring reaches a darkest-ink outline. The whole ring becomes ONE band in the ring's ink that also sews a BODY elsewhere in the design (largest such area; none = left alone), and is kept as its own band. A band running out onto the page joins when 15% of its outline lies against the ring. | no ring (no face in the page's ink) | no ring |
| 2 | the tee's black shadow (0.79 mm) folded into the tee | kept, black satin | **Darkest ink is drawn.** A band in the design's darkest ink (within 5 L* of it, and only if L* <= 35), in its own art ink, is never folded: shadow, outline and arc are line art. A rescued sliver of it still folds (trace noise). | keeps one 2.6 mm2 black band it used to fold | no change |
| 3 | GOLF's dark teal extrusion, sewn black (the cap merged teal 3344 into black) | garment | **Substituted shading.** A band whose own art ink has no spool here (`color_cap_merged_from`), facing the page (15% of its outline on the page or a white counter), beside bodies of ONE colour only and not wrapping one, goes to the page. A rescued sliver that touched only that shading goes with it. | drops 2 slivers, 1.1 mm2; its cap-merged greys INSET in the black badge stay (they face no page) | no change |
| 4 | light-grey shading inside GOLF's G and O kept (Fieldstone, its own thread) | garment | **Counter shade.** A light region near the page but not its own ink (> 3 dE00 from it), no wider than a shadow (2.4 mm), at most 30% of its outline on the page, and lying at least half against bands, the page's own ink or the page (not against a body), goes to the page. | none | none |
| 5 | GOLF's cream highlight slivers (14.3 from the white page) never folded: "near the page" counted as page | gold | **The page showing through is the page's OWN ink** (<= 3 dE00), not anything within 20 of it. A light band along the darkest ink on the art's own page is still left alone (the page's edge against a line: ProSeal's fringe). | unchanged (no page of its own) | unchanged |
| 6 | red keyline around GOLF's O counter kept | gold | **A counter's wall folds** like an outer edge, when the hole holds nothing but the page's colours (a counter). A hole holding art, or only the band itself (an inset), is no counter. | unchanged (its holes hold the scene) | unchanged |
| 7 | two golds: Candlelight (yellow) where the pro sews orange #fe9e32 (4.3 from our Pumpkin) | one orange gold | NOT built. The tone merge keeps the larger-area tone (Candlelight 146 mm2 vs Pumpkin 118). "Keep the darker end" would pick Pumpkin here but turns the crest's eagles navy where its art is slate. The pro's choice looks like the brand's colour, which the art alone does not say. | | |

## 4. Result (tick ON after vs before, same request)

| | threads | colour blocks | stitches |
|---|---|---|---|
| Golden Tee, tick OFF | 6 | 7 | 13,636 |
| Golden Tee, tick ON before | 5 | 6 | 10,482 |
| **Golden Tee, tick ON after** | **3** (white, black, gold) | 4 | **8,753** |
| Golden Tee, pro | 3 | 7 | 5,973 |

- **Kent's 20 Golden Tee pins, read by eye on `goldentee_pins_*.png`: 19 read fixed, 1 partial.**
  Pin 10 (between GOLF's O and L) is the partial one: the GT's red keyline running down there is
  now gold, but it still sews as its own satin column across the gap, with a black fleck. The pro
  sews a black wedge there. Every gold pin is our yellow, not his orange (row 7).
- Drone, tick ON after vs before: about 5 mm2 moves (two cap-merged slivers dropped, two tiny
  bands folded, one black band kept); the ring arcs fold as before.
- Crest: no rule fires (one 0.37 mm2 Golden Brown sliver).
- Controls with the tick ON, md5 equal to tick OFF on the final code: Becker hat large, Gaulke
  Roofing hat, To a T machine hat (the page-showing-through case), Hotel Fremont hat (no page of
  its own). MFab hat is `photo_scene`, so the fold never runs there.
- Tick OFF: `pipeline.py` loads `bevel_fold` only when the tick is on, and this change does not
  touch `pipeline.py`, so tick OFF is byte-identical by construction.

## 5. Open

- The gold's shade (row 7).
- Drone's ring body: the pro sews slate between black rails; ours is one black band.
- GOLF's letters still carry the GT ring's gold band where the T's stem runs down behind them
  (pin 10, and a gold column at the F's top, pin 14).
- 8,753 stitches against his 5,973: construction (fill vs satin, underlay), not shading.
