# Prime grader scorecards

Written by `digitizer/tools/prime_grader.py scorecard` (COOKBOOK, "The prime
grader"). One card per run, `latest.json` is the newest. Text only: the kit's
pictures hold client artwork and stay in the gitignored
`digitizer/eye_pairs_out/`.

Every figure here is an instrument reading, not a quality claim (ROADMAP
gate 4). No flag is flipped on it.

## Two readers, Monday and Thursday (Kent, 2026-11-19)

From the first two-reader card on, each design is graded by two blind readers
(RUNBOOK A). Kent's ruling, shown the repeat test (`repeat-2026-11-19.md`):
"Two readers, twice a week". A card lists only the faults **both** readers
place (same class within 3 mm) as findings; each reader's other faults are in
a separate "One reader only (not acted on)" section. A design's grade counts
only when both readers give it; where they differ it is marked "readers
disagree" and is left out of the grade row and of the moves against the last
card. The first two-reader card is not comparable with any one-reader card.

## Rubric 2026-11-18: the 2026-11-19 card is the new baseline

The rubric changed on 2026-11-18 (`RUBRIC_VERSION` 2026-11-18, sha `9a169b106243`),
together with how the kit draws stitches: flat-ended strips, so a satin
column's edge is the envelope it sews instead of a row of round-cap bumps
(blind readers had called clean columns "scalloped, saw-toothed on every edge",
#1648; `docs/renders/satin-caps-2026-11-18/`). **The first card under this rubric
is `scorecard-2026-11-19.md` (tree `f8373d58`, two readers per design), and it is
not comparable with any earlier card**: the scorecard says so in place of a
movement list, and a move between the two is neither the engine's nor the
rubric's alone. Compare later cards against that one. The 2026-11-17 and 2026-11-18 cards were read
under rubric 2026-11-17 with round-capped renders.

## First run, 2026-11-17, against Kent's marks

Nine blind readers (one fresh agent per design, rubric 2026-11-17) graded the
nine committed pro-paired designs on main `3608ef63`. Their readings were then
scored against Kent's defect-marks sittings (`against-kent-2026-11-17.json`).

- **Grades:** linear-weighted kappa 0.29, CI95 [0.00, 0.47], n 6. Every grade
  is within one step of his, but the readers gave Okay to 7 of 9 designs and
  never Good or Terrible; he gave Good to three of the six and Terrible to one.
  The grader bunches toward the middle.
- **His gross pins at his spot (3 mm):** 9 of 41, against 0.14 by chance, so
  0.09 above chance. Within 5 mm: 16; within 8 mm: 28. The median distance
  from one of his pins to the nearest reader fault is 5.5 mm.
- **By class at his spot:** missing 4 of 9, pen flow 2 of 3, edge 1 of 6,
  letter 0 of 9, artefact (stray, blob) 0 of 5.

**Reading it.** This run does NOT show the grader landing on his spots. It
names the same kinds of fault on the same designs (lumpy borders, stitch
direction flipping inside MARINE, closed counters), mostly at another instance
of the fault than the two or three he pinned. Three things blur the
comparison and none of them is measured here:

1. His marks were made on tree `950855bf` (2026-11-10); these renders are six
   days and a run of flag flips newer, so a fault he pinned may be gone.
2. He pins the worst two or three of a repeat; a reader that pins a different
   instance scores as a miss.
3. MFab and Tires ran without `rembg_isolated` here.

A fair test needs the readers and Kent on the SAME renders: a fresh
defect-marks sitting on a kit built from this tool's run.
