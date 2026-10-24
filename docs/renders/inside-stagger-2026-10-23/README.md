# Inside stagger at pivots (2026-10-23)

`cfg.lettering_columns_inside_stagger` (built OFF): the inside of a satin
pivot in the Column lane — an L fold's corner (`lettering_columns_corner_fold`),
an S's curl, a bowl — sewn by `columns._inside_stagger` instead of
`stage6_satin._short_stitch_guard`.

## What is here

- `table.json`, `run.log`: `python -m tools.inside_stagger --json table.json`
  (cwd `digitizer/`). One reader on the pro's hat DSTs and on ours, arms
  `off` (lane as on main), `on` (this flag), `fold` (corner fold),
  `fold_on` (both). Becker is the pro's side only: no letters file.
- `<job>_corner_<k>.png`: `python -m tools.inside_stagger --jobs drone,fremont,mfab
  --crops DIR`. Needle paths at 100 px/mm, 3.6 mm square: ours `fold` |
  ours `fold_on` | the pro's nearest pivot (our corner mapped by the word's
  box). Lines are stitches, red dots are needle holes. The corners are ours'
  with the most same-hole re-entries.
- `drone_pro_pair_off.png`, `drone_pro_pair_on.png`: `tools/pro_pair.py`, the
  Studio's request at 62.6 mm Hat with `lettering_columns_corner_fold` on, and
  this flag off / on. Crop 0-33 x 39.5-49.5 mm (PREC of PRECISION). The
  Studio's thread render, art | ours | pro.

## The reader (`tools/inside_stagger.py`)

Needle-down runs → zigzag columns → stations. A pivot zone is four or more
stations whose inner ends stay in a 0.6 mm disc while the crosses sweep
50 degrees or more and the outer ends walk at the satin pitch. Long inner end = a
local maximum of cross length; short = a local minimum.

- **long_step**: distance between consecutive long inner ends (the walk).
- **pile**: share of those steps under 0.1 mm.
- **depth / rel**: how much shorter a short cross is than its neighbours'
  mean, in mm and as a share of that mean.
- **short_frac**: short crosses over interior crosses.
- **same_hole**: inner ends within 0.1 mm of an earlier one in the zone.
- **under1**: crosses under 1 mm.

**The inner span is not reported.** The disc sets it, not the construction:
at 0.6 mm the pro and ours both read 0.8-1.0 mm. PR #1054's "spread
0.6-0.7 mm" came from a 0.45 mm window, which caps the spread at 0.9 mm.

**Watch the zone count.** Spreading the ends can push a zone out of the disc,
and then it drops out of the read (Proseal `fold` 15 → `fold_on` 8 zones).
