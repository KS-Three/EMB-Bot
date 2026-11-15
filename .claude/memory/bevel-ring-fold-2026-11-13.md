---
name: bevel-ring-fold-2026-11-13
description: "`bevel_ring_fold` built OFF 2026-11-13 (Golden Tee 'too busy', Drone ring): shadow -> page, ramp split -> one thread, thin bands (<= 0.8 mm) along a body -> the body; keylines, page-coloured shapes' edges and lines across shapes kept. A design change: default is Kent's"
metadata:
  type: project
---

# Bevel and ring fold (`bevel_ring_fold`) — 2026-11-13

Kent on Golden Tee (20 pins, one complaint): "The bean stitching makes 'golf'
look to bust"; Drone pin 3, the ring "changing colors too much". Built from
`eye_pairs_out/pro-redraws-1113/ADAPTATIONS.md` item 1 (Director's order).

**Eye first (stage 4).** Golden Tee's GOLF letters are a MOSAIC of 4-5 threads
each: the gold ramp split into two body tones (Candlelight tops, Pumpkin
bottoms, 13.9 dE00), a dark under-edge (black, then teal 3344 the cap used to
merge), red keyline bands 0.12-0.48 mm, a grey drop shadow (87 mm2, 1.3 mm,
14.3 dE00 from the white page). GT's white faces are `enclosed_background`.
Drone's ring = the black badge region with silver bevel ARCS lying as holes just
inside its outer edge. The pro: GOLF one flat gold, no outline or shadow; GT
white + gold extrusion + black outline; tee and ball arc keep their black edge.

**Rules (all in `bevel_fold.py`, mm at sewn size / CIEDE2000):**
1. shadow: band <= 2.4 mm, within 20 dE00 of the page colour, >= 40% of its
   outline on the page, >= 30% hugging art, not wrapping it -> removed (page).
2. tone merge: two shapes <= 15 dE00 sharing >= 20% of the smaller outline ->
   one thread (larger area wins) and the touching pieces union.
3. band (mean width 2A/P <= 0.8 mm = two laid 40 wt threads, what we sew as
   runs/beans) along a body -> folds into the nearest-coloured one. A band can
   be a band's parent only at 2x its area (a keyline stacked on an outline).
   Kept: wrapping >= 60% of the parent (keylines), inside the parent but not
   all along its outer edge (a reticle), any edge of a page-coloured shape (the ball
   arc, GT faces), counters, dark ink.

**Guards the controls forced (each was a real md5 change first):** To a T's 67
white gaps between brush strokes folded into the black (a band of the art's own
page colour is the page: never folded); Gaulke lost its white the same way;
Hotel Fremont has NO page colour (`bg_rgb` None), so the garment stands in, and
its small letters' white insides folded (a rescued detail lying INSIDE its
parent is a counter: kept); ProSeal's 0.13 mm light fringe read as a shadow (a
shadow is at least 2 source px wide). On a cream garment, Drone's silver arcs
(7.7 dE00) and Fremont's white (6.4) are equally "page", so only the art's OWN
page decides "page showing through".

**Traps found on the way:** `rescued_small_shape` slivers must NOT be protected
(they are the bevel noise between bands and body); a band on the page has one
other side, so the hug is judged on its off-page outline; a band inside its
parent touches it on both sides (halve the contact before the 60% wrap test);
re-threaded regions must move to their cone's layer (one spool, one position).
**The pass runs AFTER the colour cap, not before (the brief said before):**
folding first FREED a slot, the cap stopped merging the art's teal bevel (50
mm2) into black, and GOLF's O sewed dark teal. Cap first, then fold: the count
still only falls. Inside a shape only a band running along its OUTER edge
folds (Drone's ring arcs; farthest point within 0.8 mm + its width); Drone's
reticle and GOLF's O inner wall stay. A band must run along ONE colour (a line
across several is drawn art) and never lie between two shapes of one colour.
No shadow on a cut-out (the crest's white dome read as one on the garment).

**Not done / open:** black inner walls stay in GOLF's G and O and a red
segment on the T's side (the pro has gold); grey highlight patches stay inside
GOLF (page-coloured bodies); the merged gold is Candlelight (larger area) where
the pro sews an orange gold; the heraldic crest loses its grey rib shading (the
catch for default ON); Drone's arms lose some grey highlight edges.
Flattening is a design change (pro-digitizer-rules 10-21 s4): Kent chooses
default ON / OFF / a Studio "flatten shading" option (PR body).

**2026-11-14, read off the pro's own file** (`docs/flatten-shading-pro-read-2026-11-14.md`):
he sews GT's whole bevel ring (gold extrusion, cream highlight, red keyline) as ONE gold satin
inside the black outline; ours had folded it INTO the outline. GOLF is the letter faces only:
its teal extrusion (cap-merged into black), counter shading and highlights are garment. The
tee keeps its black shadow. Built inside the tick: bevel ring -> one band in the ring's body ink;
substituted (cap-merged) shading facing the page -> page; counter shade -> page; darkest-ink
own-ink bands never fold; "page showing through" = the page's OWN ink (<= 3 dE00), not 20.
Golden Tee tick ON: 5 -> 3 threads (white, black, gold), 10,482 -> 8,753 st (pro 5,973);
19 of 20 pins read fixed by eye, pin 10 partial. **Still open:** our gold is Candlelight
yellow, his orange (#fe9e32): "keep the darker tone" fits GT but turns the crest's eagles navy.
**Gold, settled same evening:** his worksheet PDF names the spool, Madeira Classic 1172
("PMS 123 Yellow Gold" is the label; 1172 is orange, (231,152,45)); the PES's #fe9e32 is only
Brother's palette. Art under our Pumpkin regions is 1.5 dE00 from it, under Candlelight 18.0:
"a ramp (each tone >= 1/4) sews its deeper end" built; the crest's navy is a 4% patch, body wins.
**Read a pro's worksheet PDF (`pdftotext -layout`) for his real threads before trusting PES colours.**
**Trap:** a hole-wall fold must check the hole is a COUNTER (holds only page colours) -- Drone's
greys inset in the black badge each sit in a hole of their own, and folding them blacked out
the scene.

Related: [[regular-structure-2026-11-13]], [[eye-first-diagnosis-2026-11-13]].

**11-14 (#1553):** #1535's "ramp sews its deeper end" now also needs the tones to meet inside 2+ separate shapes (`RAMP_MIN_OBJECTS`): the isometric icon's two touching sausages are not a ramp. The pro's Drone left scene is a redraw (light sky sewn dark slate), not a fold. `bevel_ring_fold` stays the Studio tick, not a default (11-15).
