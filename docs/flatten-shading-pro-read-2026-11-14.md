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
| 7 | the merged gold is Candlelight (yellow) where his thread is orange-gold | one orange gold | Built in the second PR (section 6): **a ramp sews its deeper end.** | no tone merge | unchanged (its navy is a 4% patch) |

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

- Drone's ring body: the pro sews slate between black rails; ours is one black band.
- Stitch count against his 5,973: construction (fill vs satin, underlay), not shading.

## 6. Second pass (same evening): the gold, pin 10, the ring's reach, GOLF's "dark edge"

**The gold: the fold's choice, not the cap and not the chart.**

- **His thread.** His Wilcom worksheet (`GOLF HAT.pdf`) names it: **Madeira Classic 1172**, labelled
  "PMS 123 Yellow Gold". The PES's #fe9e32 "Tangerine 52" is only Brother's nearest palette entry, not
  his spool. Our Madeira chart has 1172 at (231, 152, 45), an orange gold; PMS 123 itself is a yellow
  (our Candlelight is 2.8 dE00 from it). He sewed orange.
- **Where our yellow came from.** The tone merge keeps the larger-area tone. The art under our
  Candlelight regions averages (250, 208, 32), **18.0** dE00 from his 1172. The art under the Pumpkin
  regions averages (237, 152, 32), **1.5** from it. So he sewed the art's deeper, orange end of the ramp.
  By area (yellow 55%, orange 45%, the plain-yellow tee included) we sewed the pale end.
- **Not the cap.** The cap merged only the teal into black.
- **Not the chart.** Isacord has 0904 Spanish Gold at 4.3 from 1172, and Pumpkin 1102 (already in
  the palette) at 5.4. Candlelight is 17.1.
- **The art's mean is no fix either.** The area-weighted mean of the gold art is Sunset 1120, still
  10.2 from his thread.
- **Rule built: a ramp sews its deeper end** (`RAMP_MIN_SHARE`). When the two merged tones each cover at
  least a quarter of the merged area, the lower-L* tone sews: the lit end is the highlight. Otherwise
  the larger tone wins, as before. The crest's navy is 4% of its blue, a shading patch, so the slate
  body stays. Golden Tee now sews Pumpkin, 5.4 from his 1172.

**The ring's reach.** I overlaid his block 1 (gold ring) and block 2 (outline) stitches on our folded
regions (same centre, 0.26 mm apart). Round the GT the two match. Ours ran further only at the
bottom, where the ring chain kept going into GOLF's own keylines (the T's band down the F, pin 14).
His ring stops at the GT outline. **Rule:** a band that runs along a coloured body (HUG_FRAC of its
outline) is that body's keyline, so the ring does not take it and the band fold gives it to the
letter.

**Pin 10.** Between GOLF's O and L, his file has black satin at GOLF's top. That is the GT outline's
bottom edge (block 2), sewn before GOLF, with garment below it. Ours had sewn the G's keyline there,
gold, all the way down the gap. **Rule:** a ring band lying out on the page beside the outline
(EDGE_HUG_FRAC against the ring, touching a darkest-ink outline that the cap did not substitute)
joins the outline's ink. It is kept only within a band's width of that outline; past it, it is page.

**GOLF's "dark edge".** His GOLF has none. Every black stitch within 1 mm of GOLF's gold belongs
to the GT outline's bottom edge (blocks 2 runs 0, 1 and 3: 83, 39 and 38 stitches). It passes under
GOLF's tops because he sews block 2 before GOLF. GOLF's own extrusion is garment in his file. What
reads as a dark edge there is the GT outline, which ours keeps too.

**Result.** Golden Tee with the tick on: 3 threads (white, black, Pumpkin), 8,753 -> 8,363 stitches
(his 5,973). By eye on Kent's pins, every gold pin is now his shade. Pins 1-9 and 11-20 stay fixed.
Pin 10 is still partial: the gold column across the O-L gap is gone and the gap is garment like his
below GOLF's top, but his black wedge at the top of the gap (the GT outline's end) is not sewn. Our
GT outline stops above GOLF there. Controls with the tick on, md5 equal to tick off: Becker hat
large and Gaulke Roofing hat. Drone and crest: the fold's output is identical to main's (no region
changes).

