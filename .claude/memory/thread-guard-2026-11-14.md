---
name: thread-guard-2026-11-14
description: group_consistent_thread's guard (flag still OFF, Kent "Hold it, guard first") - a lone letter takes its word's thread only if that thread matches the letter's own art no worse (median per-pixel dE00, preflight's read); Drone refused 7.27 -> 13.17, Bridge's U moves 15.29 -> 14.11
metadata:
  type: project
---

Kent held `group_consistent_thread` OFF on 2026-11-14 ("Hold it, guard
first"): on drone_render (80 mm left_chest) it moved a Pumpkin 1102 shape
onto its word's Fox Fire 1305, whose thread match went warn -> block and the
grade D 40 -> F 28 (see [[group-consistency-2026-11-13]]).

**Measured before building:** for each shape the rule moves, the median
per-pixel CIEDE2000 from its own artwork to the old and the new thread,
read with preflight's `_region_color_errors`:
- Drone `S1f9b4b87`: 7.29 -> 13.04, worse, past the 10 "clearly different"
  line.
- Bridge's U of RESTAURANT (`Saca7a73b`, the case the rule was built for):
  15.29 -> 14.11, better. Bridge's score goes 0 -> 16, one block fewer.

**Built:** `stage4_vectorize.art_thread_errors(p, chart)`, stage 4's grader
read (footprint eroded 1 px, background out, 256 samples). Under the flag,
`finish_generation` hands it to `word_thread`, which refuses a move to a
thread that matches the letter's art worse. A refused letter carries
`lettering_word_thread_refused` = [old, new]; a letter with no readable
pixel moves as built. The flag stays OFF; OFF never builds the reader.

**Sheets** (`eye_pairs_out/thread-guard-1114/`):
- Drone ON+guard renders byte-identical to OFF.
- Bridge ON+guard renders byte-identical to ON (the U is fixed).
- The mascot is identical in all three arms. Its feet are `_fill_angle`'s,
  not this rule's.

**How to apply:** a rule that recolours a shape for consistency must check
the shape's own art first. "Its siblings' thread" is not evidence that the
shape's art agrees.
