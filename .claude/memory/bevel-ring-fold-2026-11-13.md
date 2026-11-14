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
   Kept: wrapping >= 60% of the parent (keylines), inside the parent but > 0.8
   mm from its edge (a crosshair), any edge of a page-coloured shape (the ball
   arc, GT faces), counters, dark ink.

**Traps found on the way:** `rescued_small_shape` slivers must NOT be protected
(they are the bevel noise between bands and body); a band on the page has one
other side, so the hug is judged on its off-page outline; a band inside its
parent touches it on both sides (halve the contact before the 60% wrap test);
re-threaded regions must move to their cone's layer (one spool, one position);
folding before the cap can FREE a slot, so a colour the cap used to merge comes
back (Golden Tee's teal, Drone's second orange).

**Not done / open:** GT's G keeps a black inner bevel where the pro has gold;
grey highlight patches stay inside GOLF's G and O (bodies of the page's colour);
the tee's upper black band piece (0.79 mm) folds while the pro keeps it.
Flattening is a design change (pro-digitizer-rules 10-21 s4): Kent chooses
default ON / OFF / a Studio "flatten shading" option (PR body).

Related: [[regular-structure-2026-11-13]], [[eye-first-diagnosis-2026-11-13]].
