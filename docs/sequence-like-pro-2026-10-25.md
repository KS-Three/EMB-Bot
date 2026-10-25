# Sequence like the pro: order is not the trim gap (2026-10-25)

Queue item L10 of `docs/superpowers/plans/2026-10-23-opus-team-architecture.md`:
"sew the blocks in the pro's order, so our trims and travel come down toward
his". PR #1048 (`cut_every_jump`: bury, then walk on work, then cut) had taken
Fremont from 187 trims to 44 against the pro's 20, and the plan read what was
left as ORDER. Measured first, as the brief asked. **The premise is false: no
flag was built.** This page is the measurement.

## Instrument

`digitizer/tools/sequence_pro.py`, new, pinned by `tests/test_sequence_pro.py`
on hand-built DSTs. One reader on both sides, DST only (the PES reader reports
a TRIM at every jump), each file in its own frame. Per colour block it finds
PIECES (connected parts of the block's own footprint, a lone run line opened
away so a walk between pieces does not join them), the order the needle visits
them in, every cut between two pieces and every cut inside one, and three
orders over the same pieces: the file's own, stage 7's sweep (start at the piece
farthest from the block's centroid, then nearest-neighbour) and the cap rule
(rows bottom-up, centre piece, left side outward, right side outward). Each cut
between pieces is classed against "within reach" (a gap of 3 mm or less whose
thread lies on thread, the walk rule `cut_every_jump` uses):

- **next in reach**: the piece entered was reachable from the one left; the cut
  is about where the needle left, not order;
- **passed over**: a reachable unsewn piece was skipped for a farther one, the
  only class an ORDER change removes;
- **dead end**: nothing unsewn was within reach.

`greedy tour` is the cut count of a tour of the same pieces that always takes a
reachable piece while one is left: the most an order change alone could reach
(it ignores where each piece can be entered and left, so it flatters).

## Jobs and arms

Fremont hat 92.5 mm, Becker hat large 101.9, MFab hat 104.9, Precision Drone
62.6, Gaulke roofing hat 114.2, hat preset, `tools/pro_pair.digitize` (the
Studio's request through the service parser), fixtures as
`tools/flip_sheet_renders.fixture_files` resolves them. Tree: `main` at
`a7a7259f` with #1048 merged. `off` = defaults; `cut` = `trim_bury_under_later`
and `cut_every_jump` ON, #1048's starting point.

## How the pro orders a hat

On all five files:

- **He starts at bottom-centre**: the first stitch sits at x 0.48 to 0.50 and
  y 0.86 to 1.00 of the design's extents. Each colour starts near the vertical
  centreline (median |x - 0.5| 0.02 to 0.15; ours 0.19 to 0.38).
- **Pieces go by the cap rule**: rows bottom-up; in a row the centre piece, one
  side outward, a fly back, the other side outward. The rule reproduces his
  piece order: Becker 52.5 mm against his file's 52.5, MFab 68.3 / 67.9,
  Gaulke 211.3 / 224.2, Fremont 235.8 / 254.3 (Drone, a photo badge, weaker:
  601 / 436).
- **Letter to letter** in a line, 50 to 57% of steps go left-to-right: half one
  way from the centre, half the other.
- **It costs him travel.** Over his own pieces his order's gap is 1.7 to 5 times
  stage 7's sweep: Fremont 254 vs 151 mm, Becker 52.5 vs 10.3, MFab 67.9 vs
  20.7, Drone 436 vs 176, Gaulke 224 vs 108. That is `cap_center_out`'s known
  price (DOCTRINE, measured negatives, 2026-09-19), read from his side.

## The gap table

Trims are TRIM records read from the DST. The three classes count STEPS between
pieces that carry a cut (a step can carry more than one).

| job | side | trims | inside a piece | between pieces | steps: next in reach / passed over / dead end | greedy tour | needle-up mm | between pieces: up / down mm | piece gap: file / sweep / cap rule | colours |
|---|---|---|---|---|---|---|---|---|---|---|
| Fremont | pro | 20 | 1 | 19 | 11 / 0 / 8 | 11 | 272 | 259 / 218 | 254 / 151 / 236 | 11 |
| | off | 51 | 36 | 15 | 7 / 0 / 7 | 8 | 896 | 228 / 104 | 99 / 99 / 157 | 4 |
| | cut | 44 | 17 | 27 | 7 / 2 / 11 | 10 | 548 | 300 / 331 | 190 / 112 / 198 | 4 |
| Becker | pro | 9 | 1 | 8 | 2 / 0 / 6 | 6 | 199 | 183 / 0 | 52.5 / 10.3 / 52.5 | 5 |
| | off | 27 | 15 | 12 | 4 / 0 / 7 | 7 | 413 | 264 / 13 | 49 / 91 / 127 | 1 |
| | cut | 24 | 12 | 12 | 4 / 0 / 7 | 7 | 393 | 264 / 13 | 49 / 91 / 127 | 1 |
| MFab | pro | 18 | 3 | 15 | 10 / 1 / 4 | 4 | 269 | 169 / 3 | 68 / 21 / 68 | 5 |
| | off | 59 | 21 | 38 | 2 / 6 / 26 | 31 | 904 | 553 / 230 | 441 / 259 / 490 | 3 |
| | cut | 68 | 18 | 50 | 8 / 7 / 30 | 31 | 834 | 549 / 241 | 441 / 259 / 490 | 3 |
| Drone | pro | 58 | 20 | 38 | 10 / 1 / 26 | 42 | 522 | 379 / 1021 | 436 / 176 / 601 | 23 |
| | off | 111 | 37 | 74 | 11 / 8 / 54 | 51 | 1595 | 1156 / 119 | 902 / 583 / 966 | 10 |
| | cut | 108 | 26 | 82 | 13 / 8 / 60 | 51 | 1410 | 1138 / 135 | 901 / 582 / 966 | 10 |
| Gaulke | pro | 41 | 0 | 41 | 9 / 0 / 32 | 33 | 502 | 502 / 0 | 224 / 108 / 211 | 1 |
| | off | 32 | 8 | 24 | 1 / 1 / 22 | 30 | 358 | 255 / 1 | 137 / 79 / 192 | 3 |
| | cut | 47 | 11 | 36 | 3 / 1 / 32 | 30 | 352 | 255 / 1 | 137 / 79 / 192 | 3 |

## What it says

Over the five jobs in the `cut` arm we cut 291 times, the pro 146: 145 extra.

1. **Order mistakes are few.** A reachable unsewn piece passed over: 18 steps
   ours, 2 his. Our dead ends (140) sit 11 above what a greedy tour of our own
   pieces is forced into (129). Together that is at most about 29 of the 145.
2. **His order would make ours worse.** The cap rule on our pieces raises the
   piece gap on all five jobs: Fremont 190 to 198 mm, Becker 49 to 127, MFab 441
   to 490, Drone 901 to 966, Gaulke 137 to 192. His fewer cuts do not come from
   his order; his order costs him.
3. **Colour order cannot buy cuts.** We sew fewer colours than he does on four
   of five jobs (Fremont 4 vs 11, Becker 1 vs 5, MFab 3 vs 5, Drone 10 vs 23),
   and `merge_duplicate_cones` leaves no cone sewn twice.
4. **The gap is construction**, ranked:
   1. Cuts inside one piece: 84 ours, 25 his (+59). Fremont's field block cuts
      itself 16 times, 11 of them between the field shape's own fill sections
      (his field: one piece, no cut). Becker's ring 12 (6 satin-to-satin
      splits, the rest satin/underlay hops). Drone's field 9 fill sections. The
      edge cap 19 over the five jobs (Fremont 1, Becker 3, MFab 6, Drone 5,
      Gaulke 4).
   2. Pieces that stand alone: a greedy tour of our pieces is forced into 129
      cuts against 96 for his (+33): MFab's 29 slivers in one colour (31 cuts
      for 1,438 stitches) and white left as fabric.
   3. Long buried travel: on Drone he walks 1,021 mm needle-down between
      pieces, we walk 135 mm; his 84 pieces cost him 38 between-piece cuts,
      our 90 cost us 82.

## Where the cuts are, for whoever picks this up

The levers the table points at already exist and are OFF, each Kent's flip:
`silhouette_underfill` (MFab 81 to 37 trims with the enclosed-white flags, its
own note), `trim_bury_under_later` and `cut_every_jump` (the `cut` arm here).
The field-section cuts (Fremont 16, Drone 9) are a fill lane's own bridges, not
a sequencing question. The one order effect worth a look is small: shapes that
re-enter a piece already left (run-level: Drone 11, MFab 5, Fremont 4), about
one cut each.

## Reproduce

```
cd digitizer
python -m tools.sequence_pro "<pro>.DST" ours.dst --blocks
python -m tools.sequence_pro ours.dst --render out/   # sew path, pieces numbered in visit order
```

Ours: `tools.pro_pair.digitize(art, width, "hat_front", sets)` then
`digitizer_core.export.write_dst(d.plan, "ours.dst")`.
