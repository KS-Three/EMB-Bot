# Re-set room, and where ProSeal's floor goes (W3-11, 2026-10-25)

Measured on main `7995d515` with the re-set set explicit, as #1057 will make it
default: `small_text_cap_mm` 4.0, `max_width_scale` 1.05, `min_stroke_mm` 0.85,
`letter_gap_mm` 0.25, `bold_scale` 1.45 and `lettering_columns_small_bold`.
`small_text_cap_reach_edges` is already ON on main. Ours is digitized at the
pro's width through the Studio request. The pro's DSTs come out of the committed
zip, and ProSeal's art comes from Kent's `scratch_kent/`. Both files are read by
one reader, each in its own frame. This is measurement only: no engine file is
changed.

`small_text.py:NNN` references are to main `97dde01a`, after #1085 merged; the
re-set code they point at is unchanged from `7995d515`, and the bay-mouth switch
#1085 added is OFF.

Tools: `digitizer/tools/small_text_floor_census.py steps` (the stroke at each
step) and the new `digitizer/tools/reset_room_census.py` (the line's move, its
room, its neighbours). Crops (art | ours | pro): `docs/renders/reset-room-2026-10-25/`.

## (b) The floor: the 0.85 is lost in the re-set's own widening

**The premise holds. This is a mechanism bug, not a reader artefact.** The
re-set widens each letter by `(target - min(s, f) x stroke) / 2`
(`small_text._reset_word`, `small_text.py:437`). The target is
`_stroke_target` (`:406`). The stroke in both is `it["stroke"]` (`:764`): the
tagger's `text_cluster_stroke_mm` x 2, measured on polygons that are **not** the
ones being widened. The re-set widens the letters `_retrace` has just re-read
from the art (`:754-755`). Where those are thinner than the tag says, every
letter lands short of its target by `min(s, f) x (tag - traced)`:

- ProSeal hat: the tag still describes the stage-4 tracer polygons, which are
  fatter than the half-threshold retrace of a 9.2 px/mm JPEG.
- ProSeal beanie and Drone: `restore_small_text` had already replaced the
  polygons with retraced ones (`:1662-1664`) and kept the old tag (`:1657`).

The mechanism belongs to `small_text.py`, so to the W3-02 lane
(`claude/reset-bays-open-w3`; its PR #1085 merged on 2026-10-25). Nothing is fixed here.

`small_text_floor_census.py steps`, per re-set cluster. *tag* (the tool's `est`) and *traced* use
the same measure (2 x the mean skeleton half-width, `textcluster._stats_of_polygon`,
which is the tag's own). *Predicted drawn* is `target - min(s, f) x (tag - traced)`.
*Drawn* is the letters' polygons as the Column lane receives them
(`p.region.polygon`). *Column* is the plan's satin crosses. *Sewn* is the floor
census reader on our DST. *Pro* is the same reader on his:

| job (source px/mm) | line | tag | traced | traced / tag | s / f | target | predicted drawn | drawn | column | sewn | pro |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ProSeal hat (9.2) | SPRAY FOAM | 0.394 | 0.332 | **0.84** | 1.29 / 1.29 | 0.85 | 0.77 | 0.75 | 0.74 | **0.72** | 1.20 |
| | + COATINGS | 0.422 | 0.329 | **0.78** | 1.29 / 1.29 | 0.85 | 0.73 | 0.72 | 0.70 | **0.70** | 1.26 |
| ProSeal beanie (10.5) | SPRAY FOAM, 1st cluster | 0.317 | 0.290 | 0.91 | 1.15 / 1.15 | 0.85 | 0.82 | 0.82 | 0.75 | 0.78 | 1.10 |
| | SPRAY FOAM, 2nd cluster | 0.358 | 0.292 | 0.82 | 1.15 / 1.15 | 0.85 | 0.77 | 0.83 | 0.77 | 0.78 | 1.10 |
| | COATINGS | 0.386 | 0.290 | **0.75** | 1.15 / 1.15 | 0.85 | 0.74 | 0.72 | 0.72 | **0.72** | 1.17 |
| Drone (12.3) | AND DRONE | 0.537 | 0.361 | **0.67** | 1.32 / 1.12 | 1.025 | 0.83 | 0.87 | 0.85 | **0.81** | 1.20 |
| Fremont hat (27) | THE | 0.450 | 0.464 | 1.03 | 1.32 / 0.99 | 0.86 | 0.87 | 0.95 | 0.98 | 0.98 | 0.89 |
| | EAT\|STAY, PLAY | 0.28 | 0.26 | 0.92 | 1.58 / 0.80 | 0.85 | 0.83 | 0.96-1.02 | 0.89-0.95 | 0.90-0.95 | 0.90 |
| | EST, 1895 | 0.24 | 0.24 | 1.00 | 2.0 / 1.85 | 0.85 | 0.85 | 0.88-0.90 | 0.77-0.92 | n/r | n/r |
| Fremont patch (27) | THE | 0.450 | 0.464 | 1.03 | 1.32 / 1.32 | 0.86 | 0.88 | 0.90 | 0.87 | 0.89 | 0.90 |
| | EAT\|STAY, PLAY | 0.28 | 0.26 | 0.92 | 1.58 / 0.80 | 0.85 | 0.83 | 0.96-1.02 | 0.87-0.89 | 0.89-0.91 | 0.89 |
| | EST, 1895 | 0.24 | 0.24 | 1.00 | 2.0 / 1.4 | 0.85 | 0.85 | 0.95 | 0.81-0.91 | n/r | 0.86 |

*n/r*: the census reader does not reach the line, which ours moved 3.0-3.25 mm
(see below). Drawn runs about 0.05-0.15 over the prediction on Fremont: the
measure reads round-ended widened letters a little wide. On ProSeal, drawn
agrees with the prediction to 0.03.

**Where the source is coarse, the tag reads 10-49% over the traced stroke and the
letters land under the floor.** That is ProSeal at 9.2 and 10.5 px/mm and Drone at 12.3. Fremont's
art is 27 px/mm, its ratio is 0.92-1.03, and every Fremont line sews at
0.87-0.98. On Drone the fat tag also raised the bold target, to 1.025, so the
shortfall still leaves it at 0.81-0.87.

**One letter, step by step** (ProSeal hat, the I of COATINGS; ours, cache trace):

| step | width |
|---|---|
| art stem (the retraced I, before scaling) | 0.325 mm |
| what the re-set is told (`it["stroke"]`) | 0.422 |
| `_stroke_target` | 0.85 (the floor: 1.45 x 1.291 x 0.422 = 0.79 is under it) |
| widen per side, `(0.85 - 1.291 x 0.422) / 2` | 0.153 |
| **drawn stem**, the polygon the lane sews (bounds) | **0.726**: 0.325 x 1.291 + 2 x 0.153. The 0.85 is gone here |
| stage 5's grown polygon | 1.38; not what the lane sews (`stage7_sequence` reads `p.region.polygon`) |
| plan: rails | 0.70-0.71 apart. Crosses alternate 0.70 square and 0.80 diagonal; `small_bold`'s pull, 0.15 x 2A/P = 0.095, sits under the 0.11 rail inset |
| sewn, the census reader on the DST | line median 0.70 |
| the pro's I, horizontal crosses | 1.30 (his line median 1.26) |

**The reader is right.** The plan's crosses and the DST reader agree within
0.02 mm on every ProSeal and Drone line. The pro's stems read 1.30 straight
across (horizontal crosses only) against his line median of 1.26. The lane
itself loses only about 0.03: `cross = drawn - 2 x (0.11 - 0.15 x 2A/P)`.

**Fixing the tag alone is not enough.** A what-if replay of
`enlarge_small_text` on the captured inputs, with the tag set to the traced
stroke (replay only, no engine change):

- ProSeal hat: drawn 0.75 / 0.72 becomes 0.81 / 0.81.
- Drone: 0.87 becomes 0.93, and the line grows x1.40 instead of x1.32 (a
  smaller bold target means a smaller widening and a smaller halo).
- **ProSeal beanie: all three clusters go to `no_room`, so the tagline is not
  re-set at all.** The larger widening grows the halo past the room left
  between the bar and the design edge.

So the tag fix has to land with a placement change from (a) below, or behind a
switch of its own.

**Gate 1, reported, not acted on.** His columns are 1.10-1.26 on ProSeal and
1.20-1.26 on Drone, against 0.86-0.90 on Fremont. Even repaired, the 0.85 floor
sits well under the first two. Divided by the traced stroke times his own
height scale (the table below), his bold factor reads 1.7-2.5 on Fremont, 2.1
on Drone and 2.5-3.0 on ProSeal, against the 1.45 candidate.
`_stroke_target`'s docstring (`:401-403`) derived 1.45 / 1.36 / 1.60 from
strokes of 0.30 (Fremont), 0.59 (Drone) and 0.61 (ProSeal), which are the fat
tags, not the traced letters. `min_stroke_mm` 0.85 and `bold_scale`
1.45 keep their values: fabric settles them.

## (a) Room: how the pro makes room for a re-set line

`reset_room_census.py`, every line read whole: SPRAY FOAM + COATINGS is one line
of type, as are EST 1895 and EAT | STAY | PLAY. Notes on reading the table:

- Moves are in our frame, mm, with y pointing **down**: *cap* and *base* are how
  far the cap line and the baseline moved against the art.
- *Room* is free fabric from the line to its own art neighbours above and
  below, at the tightest column. The art's is polygon to polygon. A file's is
  thread edge to thread edge, so it already carries pull and half a thread from
  both sides, about 0.3-0.5 mm against the art.
- The pro's frame is carried into ours by translation, with scale taken from
  the design's big word: PROSEAL, THERMAL or HOTEL FREMONT. The beanie's is
  x0.9645, because his width includes his knockdown. Neighbours that stayed put
  read 0.0-0.3 mm off, which is the frame's precision.

| line (art cap, room up / down) | pro: h (x), w (x) | pro: cap / base | pro: room up / down | ours: h (x), w (x) | ours: cap / base | ours: room up / down | ours' re-set row |
|---|---|---|---|---|---|---|---|
| ProSeal hat tagline (3.12; bar 1.8 / design edge) | 4.05 (x1.30), x1.08 | -0.10 / **+0.84** | 1.05 / - | 3.75 (x1.20), x1.01 | **-0.63** / 0.00 | 0.35 / - | x1.291 (its own cap), dy -0.25 |
| ProSeal beanie tagline (2.56; bar 1.65 / edge) | 3.81 (x1.49), x1.13 | -0.46 / **+0.79** | 0.65 / - | 3.20 (x1.25), x1.02 | **-0.83** / -0.20 | 0.15 / - | **x1.15 of 1.56**, dy -0.5 |
| Drone AND DRONE (2.20; THERMAL 2.0 / icon 1.15) | 3.45 (x1.57), x1.01 | **-1.18** / +0.07 | 0.15 / 0.30 | 3.15 (x1.43), x0.99 | -0.93 / +0.02 | 0.40 / 0.65 | **x1.317 of 1.82**, dy -0.5 |
| Fremont patch EST 1895 (1.85; rope 1.75 / THE 4.1) | 3.67 (x1.99), x1.29 | -0.17 / **+1.66** | (no rope) / 1.45 | 4.20 (x2.27), x1.57 | +1.87 / +4.22 | - / - (beside THE) | x2.0 (MAX_SCALE), dy **+3.0** |
| Fremont hat EST 1895 (1.85; rope 1.7 / THE 4.15) | 4.09 (x2.21), x1.46 | **+0.96** / +3.19 | (no rope) / 0.40 | 4.05 (x2.19), x1.62 | +2.23 / +4.43 | - / 0.0 | x2.0, dy **+3.25** |
| Fremont patch EAT\|STAY\|PLAY (2.44; band 2.55 / rope 1.75) | 3.33 (x1.36), x1.15 | **-0.62** / +0.27 | - / (no rope) | 4.30 (x1.76), x1.13 | -1.62 / +0.24 | 0.35 / - | x1.577 of 1.636, dy -0.75 |
| Fremont hat EAT\|STAY\|PLAY (2.44; band 2.55 / rope 1.7) | 3.86 (x1.58), x1.20 | **-0.99** / +0.43 | 0.65 / (no rope) | 4.40 (x1.80), x1.14 | -1.64 / +0.32 | 0.0 / - | x1.575 of 1.636, dy -0.75 |
| Fremont patch THE (3.03; 2.25 / 2.2) | 3.53 (x1.16), x1.06 | -0.73 / -0.24 | 1.45 / 1.25 | 4.10 (x1.35), x1.26 | -0.52 / +0.54 | 0.75 / 1.25 | x1.318 (its own cap), dy 0 |
| Fremont hat THE (3.04; 2.3 / 2.2) | 3.59 (x1.18), x1.04 | -0.35 / +0.20 | 1.40 / 1.25 | 4.40 (x1.45), x1.02 | -0.62 / +0.74 | 1.15 / 0.85 | x1.317, dy 0 |
| Golden Tee TM (0.86, row only) | a 2.07 mm run at (23.7-28.1, 7.8-9.9) | | | dropped: never traced | | | |

**The pro's rule.** He grows a re-set line away from its nearer neighbour:

- The neighbour is the one the art leaves under ~2 mm to (ProSeal's bar
  1.65-1.8, Drone's icon 1.15, Fremont's rope 1.7-1.75).
- The edge facing it moves at most 0.46 mm: 0.10, 0.46, 0.07, 0.17, 0.27, 0.43.
- 63-94% of the growth goes to the other side: past the design's own edge on
  ProSeal, where the baseline drops 0.79-0.84 mm.
- He re-lays no bar or badge. ProSeal's bar moves -0.02 / -0.14 in y and
  -0.22 / -0.36 in length. Fremont's Wisconsin badge moves -0.19 / +0.14.
  THE's band bars move at most 0.4 and are only thicker, by his construction.
  Drone's dash ends sit where the art has them: the left one at -24.95 in both
  files, the right one within 1.0 mm. The census does not pair them, because
  he sews them in the letters' block, joined to the A and the E.
- The line keeps 0.30-1.05 mm of thread to thread from that near neighbour.
  The far side ends as close as 0.15: Drone to THERMAL.

**Rows that contradict it:**

1. **Fremont hat EST 1895.** The near edge moved 0.96 mm *away* from the
   near neighbour: he moved the whole line 2.07 mm down into the free space,
   to 0.40 mm above THE. He sews no rope there (a plain satin border instead),
   so the near neighbour is gone, and its room went to the line. On the patch
   he keeps the near edge (-0.17).
2. **Fremont patch THE.** Its art room is the same either side (2.25 / 2.2),
   so the rule names no near side. He moves it up 0.48 and grows it only
   x1.16. On the hat he grows THE about its centre (-0.35 / +0.20).

Where he puts the room he does not spend on height: he widens the lines
x1.04-1.46 (ProSeal x1.08 / x1.13, Fremont EST 1895 x1.29 / x1.46, the
tagline x1.15 / x1.20), except Drone, which is x1.01.

**What ours does instead, and why it stops short.** No line is skipped or
`blocked_by`: the report places every line. Ours scales each line about its
own centre, then takes the smallest slide that fits (`_place_line_reset`,
`small_text.py:558-640`), so the growth goes where the slide lets it go:

- **ProSeal: up, toward the bar** (cap -0.63 / -0.83, baseline 0.00 / -0.20).
  That is the side the pro holds. On the beanie, a replay of the placement at
  every scale from x1.20 to x1.56 refuses each one two ways:
  - any upward slide of 0.5 or more puts the halo (`CLEAR_MM` 0.8 plus the
    widening, `:595`) on the bar at y 22.0-23.0;
  - any slide of 0.25 or less crosses the design edge, which gives way by only
    half the growth (`edge_room`, `:589`).
  So it stops at MIN_SCALE x1.15, where the pro is at x1.49. He spends all of
  the growth past that edge (+0.79).
- **Drone: up, like the pro.** Every scale over x1.317 hits THERMAL above, or
  the icon and the dash below and beside it. The halo is capped at the art's
  own clearance (`:843`). He grows to x1.57, leaving 0.15 to THERMAL and 0.30
  to the icon (thread edge to edge).
- **Fremont EST 1895: 3.0-3.25 mm down**, further than the pro's 0.74-2.07.
  The line ends up straddling THE, its baseline below THE's cap line, at x2.0
  where he stops at x1.99 / x2.21. It is not short of room. It overshoots.
- **Fremont tagline and THE: bigger than his.** x1.76-1.80 against his
  x1.36-1.58, and x1.35-1.45 against x1.16-1.18. The tagline ends 0.0-0.35 mm
  from the band, where he leaves 0.65.

**Crops**, art | ours | pro, each in its own frame, 1.5 caps above and below
the line (`docs/renders/reset-room-2026-10-25/`):
`proseal_hat_SPRAY_FOAM_COATINGS.jpg`, `proseal_beanie_SPRAY_FOAM_COATINGS.jpg`,
`precision_drone_AND_DRONE.jpg`, `hotel_fremont_{hat,patch}_EST_1895.jpg`,
`hotel_fremont_{hat,patch}_THE.jpg`, `hotel_fremont_{hat,patch}_EAT_STAY_PLAY.jpg`.
The hat's EST 1895 crop shows the whole story in one picture: the rope above
the date, the plain border he sews instead, his date lowered to just above the band, and
ours straddling THE.

## Instruments: what changed, and what each one cannot do

- `small_text_floor_census.py`:
  - `steps` mode, the table above.
  - `read_element(..., reach=)`: the census reads a letter only within
    `max(1.5, cap)` of the art line's centre, so a line moved further than that
    reads DROPPED. That is Fremont's EST 1895 in both files, the "known
    misread" of 2026-10-24. The default is unchanged, and so is every caller.
  - `seg_kinds`' satin cache was keyed by `id(runs)` alone. A freed run list's
    id is reused and read the old list's flags. It now holds the list.
- `reset_room_census.py` reads its own line:
  - Letter pieces of every colour block, read both painted and opened by
    0.55 mm, so letters the pro joins through travel come apart.
  - Pieces are grouped into rows. The row that covers the art's span wins,
    discounted by how far it sits off the line.
  - A same-height letter of another colour within two caps joins the row
    (Drone's A, ProSeal's A).
  - Its line boxes are the census's, each line whole. Drone's is widened to
    hold the first A of AND, which the census's box left out.
- Neighbours are found by clipping each block's thread to the art shape's box,
  grown by 1 mm. A neighbour moved further than that, or sewn joined into the
  letters' own block, reads *not found*, and so do Drone's dashes. The room is
  measured only against neighbours a file still sews. Fremont's rope is not in
  the pro's file, and its 2-4 "found" pieces are partial hits on his border
  (IoU 0.31-0.34).
- Tests: `tests/test_reset_room_census.py`, 18 tests on synthetic shifted lines.
  A line moved, grown, spread or grown one way; a bar re-laid and joined to a
  frame; a bar dropped; letters joined to a dash; a rope; the next line down;
  the census reach.

## Reproduce

```
cd digitizer
python -m tools.small_text_floor_census steps --cache C proseal_hat proseal_beanie precision_drone hotel_fremont_hat hotel_fremont_patch
python -m tools.reset_room_census digitize --cache R proseal_hat proseal_beanie precision_drone hotel_fremont_hat hotel_fremont_patch goldentee_hat
python -m tools.reset_room_census --cache R --json R/room.json --crops OUT --debug DBG
```

Each digitize takes 4-35 minutes on Kent's laptop under load. ProSeal needs its
art from `border_census.roots()`.
