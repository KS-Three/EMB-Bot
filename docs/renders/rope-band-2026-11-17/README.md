# rope_band OFF | ON (built OFF, 2026-11-17)

Fault: Hotel Fremont's twisted-rope hexagon border sews as ~100 separate run-stitch loops (a faint
zigzag). The art's rope is ~100 strand blobs of ~1.1 mm^2 each, under the detail floor, so stage 4
rescues each one and stage 7 sews it as its own run loop. The professional's file does not draw the
twist: it is one plain tan satin band round the hexagon (see `docs/prime-grader/` kit, overview).

`cfg.rope_band` (`digitizer_core/rope_band.py`): after stage 5, a same-thread chain of at least 8
rescued, non-lettering strands, 12 mm or longer, each within 0.5 mm of the next, is replaced by ONE
region (the chain closed over its gaps); the ordinary ladder then sews it as satin.

## What moved

9 pro jobs run OFF and ON (`python -m tools.rope_band_sweep`, `sweep.json`).
**1 moved, 1 is pictured, 8 are byte-identical** (Becker, Gaulke, MFab, Precision Drone, Tires,
Golden Tee, TOAT machine, TOAT beanie).

| design | stitches OFF -> ON | by eye |
|---|---|---|
| `hotel_fremont_hat` (`hotel_fremont_hat.png`) | 16,270 -> 15,268 | **Better.** Both ropes are one continuous tan satin band all round the hexagon, like the pro's, instead of a zigzag of ticks. The twist is not drawn (the pro does not draw it either). The band is a little plainer than the art's rope and sits close to the black border; nothing got worse. The small tan text (EST 1895, EAT STAY PLAY) is unchanged (still run stitch: out of scope, gate 1). |

No design got worse. Not flipped; the flip question is with the director.

## The 26 fixtures (director's request: could a rule that merges chains of tiny same-colour blobs bite a photo-style design?)

`python -m tools.rope_band_sweep --fixtures` runs `tools.corpus_scorecard.FIXTURES` (26) at the Studio
request, 80 mm, `left_chest`, OFF and ON, and compares the md5 of `design["stitches"]`
(`fixtures-*of3.json`). **1 of 26 moved, 1 is pictured, 25 are byte-identical, 0 errors.** No photo,
gradient, fur or script fixture moves.

| fixture | stitches OFF -> ON | by eye |
|---|---|---|
| `photo/logo_hotel_fremont.webp` (`logo_hotel_fremont.png`) | 12,893 -> 11,902 | **Better, with one catch.** Both ropes are one continuous tan satin band (the pro's way) in place of a chain of thin loops. At 80 mm the OFF loops already read a little like twisted rope, so ON is plainer than OFF as well as than the art; it is cleaner and matches the professional's file, not the art's twist. Nothing else in the design moved. |

Would a guard spare any fixture? None needs sparing, so none is added. The three candidate guards
(chain regularity, a closed or near-closed path, same strand size) are untested on a design that
does not move; the shipped thresholds (8+ strands, 12 mm+, 0.5 mm links, <= 3 mm^2 each) already
leave all 25 others alone.
