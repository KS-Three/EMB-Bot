---
name: k3-logo-trial-2026-11-16
description: Kent 11-16 logo trial under K3 (Sonnet workers digitize/build, foreman judges sheets by eye) — 30 Commons logos, 7 flags ON; parked with findings: dark-ink carve, Texaco star (one-spine satin; a cover check cannot see it), (R) blobs, USAID FROH
metadata:
  type: project
---

Kent, 2026-11-16: "Choose a logo from the internet, have emb bot digitize it,
then YOU (Claude) use your better judgement on what's needed to fix it", then
"Let's keep going, Make sure you are using lower level agents to digitize,
while you analyze, utilize the K3 mode for this", and later "Can you speed
this up by utilizing a sonnet agent in the cloud to digitize the image, and
then the Fable model reviews?"

Thirty public-domain logos from Wikimedia Commons in three batches (960 px
PNG, Studio request, left chest). None of the art or renders is in the repo.

**How it ran (worth repeating):** local Sonnet agents digitize, probe and
build, each builder in its own worktree; a cloud Sonnet session digitizes a
batch and publishes the sheets to a private artifact the foreman reads back;
the foreman views every sheet before believing a number and writes the spec.
Every rule was built OFF and flipped by Kent from art | before | after
pictures.

**Shipped ON that day** (each has its own note or PR): the under-fill ground
guard, rim on fabric edges and the per-line size ring
([[underfill-ground-guard-2026-11-16]], [[logo-batch-2026-11-16]]);
`lettering_columns_stroke_floor` (#1611); `dark_ink_bean_by_width`
([[dark-ink-bean-by-width-2026-11-16]]); `small_text_reset_tight_word_space`
([[reset-tight-word-space-2026-11-16]]);
`lettering_columns_ribbon_handback`
([[lettering-ribbon-handback-2026-11-16]]).

**Parked, with what was measured (do not redo these):**

- **Dark-ink carve sewn as an extra thread** (Forest Service's "Green Dust",
  Bridge's BAR). `flat_dark_ink_own_ground`, PR #1610, closed unmerged after
  three rule versions; the branch `claude/dark-ink-own-ground` is kept. Every
  version changed the National Park Service arrowhead's mountain (snow went
  grey, streaks lost, a brown band at the treeline). Kent: "The national park
  logo mountains were better when the fix was off", then "Park it". Untried:
  keep a carved piece on its own label's thread and leave geometry alone.
- **Texaco's white star** sews as one 59 mm satin spine through five legs
  (8 chains; rungs pile at four joints round the T and cross its corners, so
  the T's stem reads as a bell). The satin covers 99.5% of the star, so a
  cover check cannot see it: against the ART no ordinary satin shape over
  20 mm2 in 44 jobs is under 0.90 (against the planned polygon seven read
  low, all pull-compensation growth). Forced to fill the star is clean and
  the T reads (3,771 -> 3,993 stitches, trims 7 -> 9). Twenty-three multi-arm
  satin shapes were sewn both ways: only the star and Texaco's joined X/A
  read better as fill, and chain count (star 8, Energy Star 26), largest turn
  (star 50 deg, To a T 92) and stitch pile (star 7.2, Sony's Y 7.9) do not
  separate them. No rule.
- **Texaco's disc wedges tagged as letters.** They link to each other and to
  the wordmark's O. The hand-back rule leaves them (1.43-1.53 of their
  cluster's thickness, under its 1.6), and handing them back did not fix the
  T. The plain form of that rule (any letter the ladder calls fill) was
  rejected: 31 of its 39 hits were real bold letters (Becker, Visa, Canon,
  USGS) that sew right as columns.
- **USAID's tagline reads "FROH"**: the M loses its V in the small-text
  re-set at a 3.2 mm cap. Seen in both arms of the word-space flag.
- **(R) marks sew as blobs** on IBM, Amtrak, Intel and Chevrolet. No rule
  built; what to do with one is Kent's look decision
  ([[small-marks-2026-11-14]]).
- Not faults of ours: deep blues land on a brighter spool (nearest chart
  thread); the FEMA and USAID seals at 35 mm are under what thread can draw;
  fat small caps are the satin floor (gate 1).

**Traps:**

- Numbers hid the arrowhead regression twice. View every sheet before a flip
  question.
- `start_session` is refused on a turn an agent's message started; use
  in-process Sonnet agents there, and start a cloud session on a turn Kent
  typed.
- A flip sent to a builder after its flag PR auto-merged needs its own PR.
- `tests/test_polygon_axis.py` counts the `polygon_axis=` call sites in
  `stage7_sequence.py`; a new `classify_ribbon` reader there moves the count.
