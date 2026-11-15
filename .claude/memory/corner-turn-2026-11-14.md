---
name: corner-turn-2026-11-14
description: Kent's "nice corner with the thread" (Becker #14): `lettering_columns_corner_fold_apex_side` (OFF) lets the existing corner fold take Becker's pointed-slot E; one column top arm -> stem -> bottom arm; only the 5 Becker jobs move (28 designs: 268 -> 219 mm, trims 589 -> 584)
metadata:
  type: project
---

Director's corner-turn PR, after #1512 (edge-walk), on Kent's 2026-11-14
words: "notice how the pro makes a nice corner with the thread andc continues
the stitch to the right".

**The pro, 9 corners read by eye (Becker MARINE, MFab WELDING):**
- **Right-angle L corners:** fanned in 3 of 4: Becker E bottom-left, MFab
  E top-left and bottom-left. The crosses pivot on the inside corner, so
  the short stitches are inside.
- **Becker E top-left and R top-left:** capped. The arm or bar runs over
  the stem's top.
- **Acute corners (N, A):** capped.
- **T junctions:** butted, the arm sewn first.

**Ours:** `lettering_columns_corner_fold` (ON) already builds the fan and
refused Becker's E.
- The traced slots narrow to a point, so the stem, the arm and the arm
  across the slot all touch the tip. The fold wants exactly two.
- At hat-large size the tips turn 120-121 deg, past the fold's 110. Their
  bisector points into the stem, so the nearest apex belongs to the wrong
  arm.

**`lettering_columns_corner_fold_apex_side` (built OFF):**
- It counts only the pieces on the apex side of a corner.
- A slot tip on the OUTER outline is a corner up to 130 deg. A counter's
  corner keeps 110: ProSeal's A counter top at 125 fanned the apex he caps,
  and read worse.
- It tries each apex, nearest first, until `_fold_pair` accepts one.

**28 designs:** only the 5 Becker jobs move, their E sewn as one column.
- letters' travel on finished thread 268.1 -> 219.2 mm;
- trims 589 -> 584;
- about +150 stitches an E.
- OFF is byte-identical to main.
- With edge-walk or apex cut ON it changes only Becker's E; ProSeal never
  moves.

**Why:** the flip is Kent's.

**How to apply:**
- A fold refused on a traced letter is often a pointed slot.
- Count pieces on the apex side.
- Never widen the turn range on a counter.

Write-up: `docs/corner-turn-2026-11-14.md`. See
[[connector-edge-walk-2026-11-14]].

**Flipped ON 2026-11-14, Kent: "Flip ON"**, told: only the five Becker jobs move, one trim fewer each, about 150 more stitches per E, and the E's top-left also fans where the pro's Becker file caps. Shipped in the Column-lane flips PR beside edge-walk after the combined check (`eye_pairs_out/column-flips-1114/`). `tests/conftest.py` PRE_FLIP (`CORNER_APEX_2026_11_14_OFF`) keeps the OFF arm.
