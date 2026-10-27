# Re-set grows away from its near neighbour, widened by its traced stroke (W4-04, 2026-10-26)

Builds the pair W3-11 measured (`docs/reset-room-2026-10-25.md`, PR #1099)
behind ONE switch, OFF: `cfg.extra["small_text_reset_grow_away"]`
(`small_text.enlarge_small_text(..., grow_away=True)`). Layout, so Kent's
call from the renders (2026-10-22 ruling); nothing here needs a sew-out, and
no clearance constant moved (`CLEAR_MM` 0.8 and the halo are gate 1).

Measured on main `46949f78` (after #1057's flips and #1102) against the
branch, at the pro's width through the Studio request, with
`small_text_floor_census steps` and `reset_room_census` on one digitize per
job and arm. The pro's files and ProSeal's art come from Kent's
`scratch_kent/`.

## What the switch does

1. **Floor: the stroke is the letters' own.** The re-set widened each letter
   by `(target - min(s, f) x stroke) / 2` with `stroke` the tagger's tag,
   measured on other polygons. ON, `_traced_stroke` measures the retraced
   letters it actually grows (2 x the mean skeleton half-width,
   `textcluster._stats_of_polygon`, the tag's own measure; median over the
   line) and the widening and the `text_cluster_stroke_mm` it writes back use
   that.
2. **Room: hold the near edge, the far side takes the growth.**
   - `_near_side` reads, per 0.1 mm column of the line's letters, the gap to
     the next shape above and below, **on the art** (a snapshot taken when the
     re-set starts, not the lines already grown). The nearer side is the near
     side if its gap is under `GROW_AWAY_NEAR_MM` 2.0. ProSeal: the bar above
     (1.72 / 1.88). Drone: the dome icon below (1.28; THERMAL is 2.04 above).
     Fremont: the rope (1.78) above the date and below the tagline; THE has
     none.
   - `_grow_away` gives the placement its vertical moves: first the one
     that puts the re-set line's near edge back where the art has it, then
     that edge moved by up to `GROW_AWAY_NEAR_GIVE_MM` 0.5 either way, toward
     the neighbour first, the cost being how far the near edge moved. On
     the FAR side the design's edge gives way by the whole growth (the
     `reach_edges` half-growth rule stays on the other three sides).
   - A line that cannot hold its near edge at any scale is placed as
     before (`grow_away.held` false in its row). None of the seven lines
     with a near side needed it.

Two things the first build got wrong, both caught on the captured inputs
before the digitize:

- **One grid from the held edge** cost Drone x1.317 -> x1.234: its line fits
  between the dome icon and THERMAL only 0.50 mm up, and a 0.25 mm grid laid
  from the held edge stood at 0.37 (on the icon) and 0.62 (on THERMAL). The
  moves are now on both grids: from the held edge, and today's art-anchored
  one.
- **Neighbours read on the current regions** made Fremont's THE see its own
  grown date 1.5 mm above it and grow down. They are read on the art.

An uncapped move away from the neighbour let Fremont's hat date slide 2.3 mm
down onto THE again (the rope arcs down either side of it), which is what
the 0.5 cap stops; the pro's near edges moved 0.07-0.46.

## Placement: OFF | ON | pro, per line

`reset_room_census`, each line read whole in each file. y is DOWN, so `cap /
base` is how far the cap line and the baseline moved against the art (mm). The
near edge is the cap line when the near side is above, the baseline when below.
*Far share* is the far edge's share of the two edges' moves. *Room* is
thread to thread in a file, to the line's own neighbours above / below (min over
columns). The pro's frame is carried by the census's registration. Its rows
move up to 0.1 mm between the two arms' runs, so read anything under ~0.1 as
none.

| line | near side (art gap) | pro: h, w; cap / base | OFF | ON | near edge (far share): pro / OFF / ON | room up / down: pro; OFF; ON | re-set OFF -> ON |
|---|---|---|---|---|---|---|---|
| ProSeal hat tagline | above, bar (1.88) | 4.06 (x1.30), x1.08; -0.03 / +0.92 | 3.75 (x1.20), x1.02; **-0.63** / 0.00 | 4.10 (x1.31), x1.04; **+0.02 / +1.00** | -0.03 (97%) / -0.63 (0%) / +0.02 (98%) | 1.05 / -; 0.35 / -; 0.95 / - | x1.291 -> x1.291 (the 4.0 cap) |
| ProSeal beanie tagline | above, bar (1.72) | 3.83 (x1.49), x1.14; -0.32 / +0.94 | 3.20 (x1.25), x1.02; -0.83 / -0.20 | 4.20 (x1.64), x1.20; -0.08 / +1.55 | -0.32 (75%) / -0.83 (19%) / -0.08 (95%) | 0.65 / -; 0.15 / -; 0.75 / - | **x1.15 -> x1.56** |
| Drone AND DRONE | below, dome icon (1.28; THERMAL 2.04 above) | 3.46 (x1.58), x1.01; -1.11 / +0.15 | 3.18 (x1.45), x0.99; -0.93 / +0.05 | 3.38 (x1.54), x0.99; -1.03 / +0.15 | +0.15 (88%) / +0.05 (95%) / +0.15 (87%) | 0.15 / 0.30; 0.40 / 0.60; 0.30 / 0.45 | x1.317 f1.12 -> **x1.401** f1.10 |
| Fremont patch EST 1895 | above, rope (1.78) | 3.67 (x1.99), x1.29; -0.17 / +1.66 | 4.20 (x2.27), x1.57; **+1.87 / +4.22** | 4.15 (x2.24), x1.25; +0.32 / +2.62 | -0.17 (91%) / +1.87 (69%) / +0.32 (89%) | 1.10 / 1.45; 2.85 / - (beside THE); 1.30 / 0.55 | x2.0 f1.40 -> x2.0 f1.10 |
| Fremont hat EST 1895 * | above, rope (1.78) | 4.09 (x2.21), x1.46; +0.96 / +3.19 | 4.05 (x2.19), x1.62; **+2.23 / +4.43** | 4.15 (x2.24), x1.25; +0.33 / +2.63 | +0.96 (77%) / +2.23 (67%) / +0.33 (89%) | 2.30 / 0.40; 3.40 / 1.65; 1.40 / 0.65 | x2.0 f1.85 -> x2.0 f1.10 |
| Fremont patch EAT \| STAY \| PLAY | below, rope (1.78) | 3.33 (x1.36), x1.15; -0.62 / +0.27 | 4.30 (x1.76), x1.13; -1.62 / +0.24 | 4.45 (x1.82), x1.14; -1.67 / +0.34 | +0.27 (70%) / +0.24 (87%) / +0.34 (83%) | - / 1.45; 0.35 / 1.65; 0.35 / 1.65 | x1.577 f0.8, unchanged |
| Fremont hat EAT \| STAY \| PLAY | below, rope (1.78) | 3.86 (x1.58), x1.20; -0.99 / +0.43 | 4.40 (x1.80), x1.14; -1.64 / +0.32 | 4.45 (x1.82), x1.14; -1.69 / +0.32 | +0.43 (70%) / +0.32 (84%) / +0.32 (84%) | 0.65 / 1.85; 0.10 / 1.45; 0.15 / 1.60 | x1.575 f0.8, unchanged |
| Fremont patch THE * | none (2.25 / 2.2) | 3.53 (x1.16), x1.06; -0.73 / -0.24 | 4.10 (x1.35), x1.26; -0.52 / +0.54 | 4.25 (x1.40), x1.24; -0.57 / +0.64 | - | 1.45 / 1.25; 0.75 / 1.25; 0.75 / 1.20 | x1.318, unchanged |
| Fremont hat THE * | none (2.3 / 2.2) | 3.59 (x1.18), x1.04; -0.35 / +0.20 | 4.40 (x1.45), x1.02; -0.62 / +0.74 | 4.25 (x1.40), x1.23; -0.57 / +0.64 | - | 1.40 / 1.25; 1.35 / 0.95; 1.45 / 1.05 | x1.317 f0.99 -> f1.32 |

\* The rows the brief said not to fit (W3-11's contradicting rows), reported:

- **Fremont hat EST 1895:** the pro sews no rope here and moved the date
  2.07 mm down whole. Ours keeps the rope, so ON holds the date under it, as
  the pro does on the PATCH (where he keeps the rope: -0.17). OFF's date
  straddled THE (beside it, its baseline below THE's cap line); ON leaves
  0.55-0.65 mm above it.
- **THE:** no near side on either job, so ON places it as OFF does. On the
  hat it now widens to f 1.32, because the date no longer stands beside it.
  Its E reads as an E; OFF's closed into a B. The pro's is narrower, x1.04.

`no_room`: **0 of the 17 re-set rows in either arm** (5 jobs). W3-11's
replay of the stroke fix alone sent the beanie's three to `no_room`. Every
line with a near side held it (`grow_away.held`), so no line fell back.

## Stroke: drawn, the plan's column and the sewn DST against the pro's

`small_text_floor_census steps`, per re-set cluster. *Sewn* is the floor
census reader on our DST, by line. The pro's is the same reader on his file
(Fremont's from W3-11, which read it by colour block; his file is
unchanged). *n/r*: the reader does not reach the line (OFF's date moved
3 mm).

| line | tag -> traced | drawn OFF -> ON | column OFF -> ON | **sewn OFF -> ON** | pro |
|---|---|---|---|---|---|
| ProSeal hat SPRAY FOAM | 0.394 -> 0.332 | 0.75 -> 0.86 | 0.74 -> 0.84 | **0.72 -> 0.81** | 1.20 |
| ProSeal hat + COATINGS | 0.422 -> 0.329 | 0.72 -> 0.81 | 0.70 -> 0.83 | **0.71 -> 0.82** | 1.26 |
| ProSeal beanie SPRAY FOAM (2 clusters) | 0.358 / 0.317 -> 0.29 | 0.83 / 0.82 -> 0.89 / 0.84 | 0.77 / 0.75 -> 0.84 / 0.83 | **0.78 -> 0.81** | 1.10 |
| ProSeal beanie + COATINGS | 0.386 -> 0.290 | 0.72 -> 0.86 | 0.72 -> 0.83 | **0.71 -> 0.82** | 1.17 |
| Drone AND DRONE | 0.537 -> 0.361 | 0.87 -> 0.93 | 0.90 -> 0.90 | 0.89 -> 0.91 | 1.20 |
| Fremont hat EST / 1895 | 0.24 -> 0.24 | 0.90 / 0.88 -> 0.97 / 0.95 | 0.93 / 0.77 -> 0.91 / 0.86 | n/r -> 0.89 / 0.86 | n/r |
| Fremont hat EAT \| STAY / PLAY | 0.28 -> 0.26 | 1.02 / 0.96 -> 0.96 / 0.96 | 0.89 / 0.88 -> 0.97 / 0.91 | 0.91 / 0.92 -> 0.95 / 0.91 | 0.90 |
| Fremont hat THE | 0.450 -> 0.464 | 0.95 -> 0.90 | 1.00 -> 0.89 | 0.98 -> **0.89** | 0.89 |
| Fremont patch EST / 1895 | 0.24 -> 0.24 | 0.95 / 0.95 -> 0.99 / 0.95 | 0.93 / 0.81 -> 0.92 / 0.89 | n/r -> 0.89 / 0.90 | 0.86 |
| Fremont patch EAT \| STAY / PLAY | 0.28 -> 0.26 | 1.02 / 0.96 -> 0.96 / 0.98 | 0.89 / 0.87 -> 0.97 / 0.90 | 0.98 / 0.89 -> 0.91 / 0.91 | 0.89 |
| Fremont patch THE | 0.450 -> 0.464 | 0.90 -> 0.90 | 0.87 -> 0.88 | 0.89 -> 0.90 | 0.90 |

- **ProSeal reaches the floor's neighbourhood: 0.71-0.78 -> 0.81-0.82.** The
  last ~0.03 under 0.85 is the Column lane's own (W3-11: `cross = drawn - 2
  x (0.11 - 0.15 x 2A/P)`), not the re-set's.
- **Drone barely moves (+0.02).** Its fat tag had also raised its bold
  target (1.025), and the two errors nearly cancelled: by formula the drawn
  stroke goes 0.827 -> 0.849. The measure reads widened round letters a
  little wide, hence 0.87 -> 0.93.
- **Fremont, where tag and traced agree (0.92-1.03), moves within 0.09.**
  Its EST 1895 is read at all for the first time, at 0.86-0.90 against the
  pro's 0.86.

## Gate checks

- **Layout (Kent 2026-10-22):** placement is judged from the renders,
  `docs/renders/reset-grow-away-2026-10-26/` (OFF | ON | pro, stitches only;
  no art panel). One crop per re-set line, nine in all.
- **Gate 1, reported, not acted on.** No constant moved. `CLEAR_MM` 0.8,
  the halo, `min_stroke_mm` 0.85 and `bold_scale` 1.45 are as they were.
  `GROW_AWAY_NEAR_MM` 2.0 and `GROW_AWAY_NEAR_GIVE_MM` 0.5 are layout,
  read off the pro's files: where the letters go, not what fabric holds.
  - **Drone stops at x1.40 against the pro's x1.57** because of the 0.8 mm
    halo plus widening, against THERMAL above, the dome below and the
    dashes beside. The pro keeps 0.15 mm (THERMAL) and 0.30 mm (icon) thread
    to thread; ON keeps 0.30 / 0.45. Reaching his height means a smaller
    clearance, which is a `CLEAR_MM` call for Kent after a sew-out.
  - **The beanie is not blocked by clearance under this switch.** It grows
    to x1.56, past the pro's x1.49, and keeps 0.75 mm to the bar (pro 0.65).
  - ProSeal's and Drone's columns are still 0.81-0.91 against the pro's
    1.10-1.26. That is the 0.85 floor and the 1.45 bold factor, both gate 1
    (W3-11 has his bold factor at 1.7-3.0 on the traced strokes).
- **Gate 4:** no agreement figure is quoted here; every number is a
  measurement in mm or a scale.

## What it does not do (residuals, for whoever picks the next lane)

- **Width.** The re-set still takes the widest letters that fit, and the
  design's side edges still give way by half the growth. With the height
  now reached, the beanie's line runs x1.20 wide, past its bar's ends (the
  pro's: x1.14, inside them). Fremont's date goes the other way: f 1.10
  (OFF 1.40 / 1.85). Its line width is x1.25 against the pro's x1.29 on the
  patch and x1.46 on the hat, but ours stands 0.5 mm taller (the 4.0 cap
  plus the widening), so it reads condensed.
- **The "+" of ProSeal's tagline is not grown.** It is its own shape, not a
  letter of the line; the pro's is grown with the words.
- **Height past the pro's.** That is the 4.0 cap target, not this switch:
  the beanie 4.20 against 3.83, the tagline 4.45 against 3.33-3.86, THE 4.25
  against 3.53-3.59.

## Tests and proof

- `tests/test_small_text_grow_away.py`, 16 tests, on `test_small_text.py`'s
  synthetic scene with a rule 1.5 mm from the line. They cover:
  - OFF is byte-identical, md5-pinned on main's own `small_text.py` (loaded
    from `46949f78`, captured before the switch existed).
  - OFF never reaches the new code.
  - ON with both parts stubbed equals OFF in process (platform-safe).
  - The switch needs the re-set.
  - Stroke: drawn reaches the target from the traced stroke, and the
    written-back stroke equals traced x min(s, f) + 2 x widen.
  - Placement: the near edge holds and the far side takes >= 80% of the
    growth, both ways round. A line OFF left `no_room` fits. No near side
    places as before. No hold falls back to today's placement.
  - `_near_side`: the tighter side at the tightest column, a shape beside the
    line in its band ignored, read on the art. `_grow_away`: both grids, the
    0.5 cap, the far room.
  - The `cfg.extra` key reaches the call; absent, today's call word for word.
- The existing small-text suites pass unchanged: 95 tests including every
  md5 pin (`test_small_text`, `_reset`, `_reach_edges`, `_bays`,
  `_counter_guard`, `test_reset_room_census`).
- Full pipeline, OFF on the branch against main: ProSeal beanie and Drone
  digitized with the switch absent give byte-identical DSTs (md5
  `8f2b522b...` and `5ad4a63e...` on both).

## Reproduce

Each arm is one digitize per job: `small_text_floor_census steps --cache DIR
SLUG` (it writes `ours.dst`, `ours.json` and `steps.json`), with
`small_text.enlarge_small_text` wrapped to also write `reset_room_census`'s
`art.json` and `growth.json` (what its `digitize` mode writes). The ON arm
wraps it as `functools.partial(enlarge_small_text, grow_away=True)`, the way
`tools/bay_census.py` arms its switch, which is what the pipeline passes when
`cfg.extra["small_text_reset_grow_away"]` is set. ProSeal needs Kent's
`scratch_kent/` (`border_census.roots()`). Each job took 4-17 minutes on
Kent's laptop under load.

```
cd digitizer
python -m tools.small_text_floor_census steps --table --cache OFF
python -m tools.reset_room_census --cache OFF --json OFF/room.json
python -m tools.reset_room_census --cache ON --json ON/room.json
python -m pytest -q tests/test_small_text_grow_away.py
```
