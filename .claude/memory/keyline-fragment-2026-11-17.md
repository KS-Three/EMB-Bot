---
name: keyline-fragment-2026-11-17
description: Drone's P/R/C dark bars are tracing remnants of a hairline keyline; keyline_fragment_drop narrowed to 4 conditions (outer edge, not darkest ink, >5 L* darker, <=3 src px) and flipped ON 11-17 (Kent "Flip ON"); 2 of 35 runs move
metadata:
  type: project
---

2026-11-17, Kent on the Drone render at 80 mm: "The P,R & C should not have the dark stitch
lines on them". Stage 2 leaves a few mm of the chrome letters' hairline dark edge as its own
regions (P bottom twice, R leg, C foot with `merge_chroma_guard`), each sewn as a dark satin bar.

- **Built rule over-reached** (PR #1640): deleted To a T's speed lines (thin dark bands INSIDE
  the white fill, hugging its hole rings) and Golden Tee's black shadow and an F band.
- **Four conditions separate remnant from drawn art** (`keyline_fragment.py`): on the host's
  OUTER outline; not the design's darkest ink in its own art ink (`bevel_fold` rule, a rescued
  or cap-merged piece is not protected); darker than the host by > `DARKEST_L_TOL` (5 L*; a
  2 L* sliver was Golden Tee's F); a hairline in the art, <= `HAIRLINE_SRC_PX` 3.0 source px.
- **Trap.** Source width alone does NOT separate them: To a T's speed lines are ~1 px too
  (0.21-0.3 mm at 0.24 mm/px); the hole rule is what keeps them. And the 3.0 px bound rests on
  three examples (Drone remnants 1.3-1.9 px, Golden Tee's bar 15 px).
- **Measured.** 9 pro jobs + 26 fixtures, by stitch md5: 2 of 35 move, `drone_render` 18,337 ->
  18,267 (better) and `logo_bridge_bar` 10,827 -> 10,813 (a stray chip gone). Pictures:
  `docs/renders/keyline-fragment-2026-11-17/`. ON in the Studio since PR #1643.
- **Tests with the flag ON.** 1,754 passed; the one red, `enthusiast_logo`'s stage-2 / flat-lane
  golden, is red with the flag OFF too (platform golden, CI deselects it).
