# Fill rows turn on a slant (`fill_turn_slant`, built OFF) — 2026-10-21

The settings audit (`docs/settings-vs-pro-2026-10-21.md`, row 24, gap #2) found
that at the end of every fill row we step straight across to the next row: one
row spacing, 0.10-0.22 mm at the 0.15 row. The needle lands beside its own hole.
The pro turns on a slant. This is construction, not a fabric constant: the row
spacing does not move, and the number comes off his files, not off cloth. ROADMAP
gate 1 does not apply. The flip is Kent's.

## What the pro does, read in his own frame

`digitizer/tools/fill_turns.py` (new). A turn is a stitch of at most 1.6 mm
between two antiparallel row stitches that each continue a straight row. It is
split along the row and across it.

| Pro DST | turns | length p10 / p50 / p90 (mm) | along p50 | under 0.5 mm, all stitches |
|---|---|---|---|---|
| `HOTEL FREMONT .DST` (patch) | 266 | 0.41 / 0.71 / 1.36 | 0.63 | 209 (1.35%) |
| `HOTEL FREMONT HAT.DST` | 457 | 0.41 / 0.71 / 1.33 | 0.66 | 295 (1.73%) |
| `beckers logo hat.DST` | 450 | 0.41 / 0.72 / 1.34 | 0.67 | 228 (1.85%) |
| `beckers logo hat 2 A.DST` | 334 | 0.41 / 0.72 / 1.34 | 0.63 | 197 (2.27%) |
| `PRECISION DRON HAT 2.DST` | 551 | 0.41 / 0.83 / 1.41 | 0.78 | 841 (5.78%) |
| `mf4b logo hat.DST` | 723 | 0.41 / 0.76 / 1.39 | 0.71 | 513 (2.92%) |

The across component's p50 is 0.10-0.15 mm: his row spacing. Hence
`machine.FILL_TURN_ALONG_MM = 0.7`, a turn of 0.716 mm at the 0.15 row.

## The construction

`stage6_fill._slant_turns`: a turn joins two points on the boundary. The point
further OUT along the row stays on the boundary. The inner point is pulled in
until the turn runs 0.7 mm along the row, and the slanted thread then lies over
the corner the pull left bare.

- **Narrowing or square edge:** the next row's entry is pulled.
- **Widening edge:** this row's exit is pulled.
- **Column's last turn, near-square edge:** the exit is pulled, so the last row
  keeps its corner.
- **Preferred row too short** to keep `MIN_STITCH_MM`: the turn's other end is
  pulled instead.
- **Left alone:** a turn already 0.7 mm along (a sloped edge), and one neither row
  can afford.

The row grid, the stagger and the interior penetrations do not change. Every fill
technique's pass gets it; the underlay never does. Reach is stage 7's six tatami
calls and the blend tier's two, the same as `fill_order_sewn_paths`. The satin
tier's patch fills, the contour finish patches and the beanie knockdown do not
pass the flag.

**The first build pulled every entry, and it was wrong.** On a widening edge it
bared the outer corner, so the visible edge was drawn by every second row's exit:
a staircase on every edge under about 60° to the rows. Fremont's lower band showed
it. Renders: `renders/fill-turn-slant-2026-10-21/edge_angles_first_build_staircase.png`
against `edge_angles_off_on.png`.

On the synthetic parallelograms (20-75°), a box, a disc and a triangle, the bare
area under a 0.4 mm thread is 0.000-0.002 mm² ON against 0.000 OFF. Pinned in
`test_on_sloped_edges_keep_their_line`.

## Before / after on the four jobs

Measured with `tools/pro_pair.py`'s digitize path (the Studio's request through
the service parser) at the pro's width and garment, on `main` at `03ccab4e`:
Fremont patch 92.5 mm, Becker 101.9 hat, Drone 62.6 hat, MFab 104.9 hat. Both
sides are read from the written DST by `tools/fill_turns.py`.

| Job | stitches under 0.5 mm, OFF → ON | row turns under 0.5 | turn p50 (pro) | p1 stitch | stitches | trims |
|---|---|---|---|---|---|---|
| Fremont | **3,084 → 847** (13.1% → 3.7%) | 1,586 → 88 | 0.20 → 0.71 (0.71) | 0.10 → 0.20 | 23,517 → 23,166 (-1.5%) | 83 = 83 |
| Becker | 859 → 823 (9.2% → 8.8%) | 66 → 36 | 0.30 → 0.72 (0.72) | 0.22 → 0.28 | 9,382 → 9,375 | 28 = 28 |
| Drone | **2,013 → 1,098** (13.8% → 7.6%) | 722 → 39 | 0.22 → 0.73 (0.83) | 0.10 → 0.10 | 14,611 → 14,405 (-1.4%) | 122 = 122 |
| MFab | 563 → 454 (4.7% → 3.8%) | 91 → 2 | 0.22 → 0.76 (0.76) | 0.22 → 0.30 | 12,075 → 12,050 | 63 = 63 |

- **Becker hardly moves.** It has one fill shape; its short stitches are satin and
  bean, not fill turns.
- **What remains under 0.5 mm** on Fremont and Drone is mostly not fill turns:
  `short_turns` (the audit's looser count) is 321 and 465. These are the job for
  satin and run work.
- **Ours is uniform where the pro varies.** Our turns sit at 0.71-0.73 (p10 =
  p90); the pro's spread from 0.41 to 1.4, because his edges slope.

**Edge coverage.** The 0.6 mm inner band of every fill-only shape, under a 0.4 mm
thread, is unchanged: Fremont 0.9925 = 0.9925, Drone 0.9996 → 0.9995, Becker and
MFab 1.0. Drawn at half that width (0.2 mm) it falls 0.7-1.2 points on Fremont and
Drone. That is the corner the slanted thread lies over. Thread width is what
decides it, which makes it a sew-out question, not a render one.

**Edge holes.** By construction each edge takes a penetration every second row
instead of every row; the penetration panels in the renders show the halving. I
did not quote an "edge penetrations per mm" figure. Our fills sew on a polygon
grown past their region (on Fremont's field, 4,962 of 10,300 penetrations lie
outside its own region), so a point pulled 0.7 mm in lands ON the region's edge,
and that count rose for the wrong reason.

**Default OFF is byte-identical.** The four DSTs OFF match `main` exactly:
Fremont `dac6bf81`, Becker `e8b62499`, Drone `bd4d626c`, MFab `8f929179`. Those
are the trim-economy doc's baselines too. The unit fixtures are pinned by
`test_default_is_off_and_off_is_the_old_call`.

Renders, OFF | ON, at the 5 mm window holding the most straight-across turns,
thread above and penetrations below: `renders/fill-turn-slant-2026-10-21/`.

## The browser engine has the same turn

`src/fill.js` `sewColumns` walks each column as `[lo, hi]` per row and
`sewTo(hi_k, lo_{k+1})`: the same straight step, one pitch long (its own comment
says so: "A fill's own turns are one pitch long"). Not changed here. It is a
follow-up.

## Not in this change

- The flip. **Kent 2026-10-22: hold OFF; an OFF/ON fill swatch goes on the next
  sew-out card**, which decides the slanted corner at real thread width.
- A floor number for the turn (any value, any garment): gate 1.
- The browser engine (`src/fill.js`).
- The satin tier's patch fills, contour finish patches and knockdown: no cfg
  reaches them.
