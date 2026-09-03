# Fill travel under cover — defect 21, fixed default ON (2026-09-03)

Kent's note 1 on the Hotel Fremont screenshot: *"The in-fill stitching doesn't
look clean, not sure if it's the stitch out or the stitch rendering."* Traced
2026-09-02 (`docs/hotel-fremont-fine-details-2026-09-02.md`): the stitches.
The professional file's tatami renders smooth through the same `stitchviz`;
ours laid 22 of 27 fill-phase travel runs — 286 of 450 mm — on top of columns
already sewn. A pro hides travel under fill still to come or along an edge a
border covers. Kent picked this as the next item on 2026-09-03.

## The instrument

`scratchpad/exposure.py`, kept as the test helper `_fill_exposed_mm` in
`tests/test_fill.py`: walk a shape's runs in sew order, accumulate the
footprint of each fill path (a full-row buffer of a half-row-simplified copy),
and for each fill-phase travel run measure how much of it lies over that
footprint beyond a one-travel-stitch tolerance (`_EXPOSED_TOLERANCE_MM` =
`TRAVEL_STITCH_MM`, 2.5 mm — the bridge starts inside the column it just
finished, by construction).

## What was tried, in order — the first two did nothing

1. **Covered routing, shape's own rings.** Straight only if it crosses unsewn
   ground; else the inset ring either way round; else today's exposed route.
   Fremont **286 → 286 mm**. The inset ring runs 0.6 mm inside the boundary,
   through columns already sewn, so an "unexposed" ring route rarely exists.
2. **Covered routing through the unsewn remainder.** `cover − sewn`, its own
   half-row inset rings, either way round, endpoints allowed one stitch.
   Fremont **286 → 286 mm** again — the routes were found (27 → 37 travel
   runs) but the exposed hauls remained, because by the time the bridge is
   built there is no unsewn ground between the two ends. **Exposure is
   decided by the ORDER, not the route.** Two diagnostic traps on the way:
   a half-row footprint buffer of a zigzag leaves slivers and the unsewn
   region shattered into 110–230 parts; and the containment test failed at
   the bridge's first point, which sits inside the column just sewn.
3. **Cover-aware column order** (`_reorder_for_cover`): the nearest-first
   walk prefers the nearest column whose straight bridge is inside the shape
   and off the fill laid so far, entered from whichever end is nearer;
   `_order_cost` scores both orders with the covered routing that will
   actually sew — cuts × 25 + travel stitches + exposed travel stitches × 2 —
   and keeps the cheaper; the last path stays pinned so the exit point, and
   every shape after it, is untouched (the design-level never-worse argument
   `_reorder_for_fewer_cuts` already rests on). **Fremont 286 → 164 mm**, and
   with the shorter way round tried first, **→ 92 mm**.

The exposed-stitch weight, 2.0, is a judgement about how a design LOOKS
(sewn once, seen once), like `_TRIM_STITCH_EQUIVALENT` is about time; a 20 mm
haul across finished tatami weighs 16 against a cut's 25, so a cut is never
bought to hide a short hop. Not a fabric constant.

## Measured, flag on vs off (fill-phase travel over the sewn footprint)

| fixture | exposed | fill-phase travel | stitches | trims |
|---|---|---|---|---|
| `logo_hotel_fremont` @ 80 (Kent's settings) | **286 → 92 mm** (22 → 6 runs) | 450 → 209 mm | 6473 → 6394 | 47 → 47 |
| `logo_gaulke_roofing` | **209 → 8 mm** (15 → 1) | 370 → 196 | 3954 → 3885 | 24 → 21 |
| `becker_marine_logo` | 27 → 14 mm | 77 → 55 | 4557 → 4531 | 28 → 28 |
| `logo_whitebg` | 10 → 10 mm | 30 → 21 | 2166 → 2162 | 6 → 6 |
| `drone_render` (blend tier) | **546 → 61 mm** (32 → 9) | 1269 → 352 | 9317 → 8724 | 86 → 90 |
| `photo_dof_meadow` | 691 → 301 mm | 1130 → 683 | 10116 → 9679 | 33 → 27 |
| `photo_sunset_backlit` | **711 → 291 mm** | 1316 → 936 | 12345 → 11779 | **53 → 30** |

Flag off is md5-identical to `origin/main` on becker, drone, enthusiast and
Fremont. `enthusiast_logo` has no fill travel at all and is untouched either
way. Drone's four extra trims are the score buying 570 fewer travel stitches
for 100 stitch-equivalents of cuts — a legitimate trade by the rule above,
recorded because defect 4 counts trims.

Whole-design render (all travel, every tier): Fremont exposed **564 → 303 mm**,
30 → 20 runs; the long diagonals across the lower field are gone, what remains
is hauls between the regions the letters cut the field into.

## Cost

| fixture | flag off | flag on |
|---|---|---|
| Fremont | 10.9 s | 12.1 s |
| gaulke | 38.0 s | 40.5 s |
| drone | 22.8 s | 24.5 s |
| meadow | 14.3 s | 17.5 s |
| sunset (263 fill runs) | 33.6 s | **50.0 s** |

Two optimisations landed on the way, both behaviour-preserving: `_ring_route`
rebuilt its cumulative arc table on every call — **34.8 s of a 90 s profile**
on sunset, the hottest function in stage 6 before this change existed — and is
now cached per ring; and the unsewn-ground rings are reused across
consecutive bridges, re-checked against the CURRENT unsewn ground, before the
inset buffer is rebuilt. What remains on sunset is the covered scoring pass
itself (`_order_cost` with routing, twice per shape, 15.6 s) and the shapely
set operations behind it. Not optimised further here; the service's 60 s job
budget in tests is on small fixtures and unaffected.

## Goldens

`logo_whitebg` moved by exactly its travel (2166 → 2162 penetrations; region
ids, areas, warnings unmoved) and was re-pinned in `flat_lane_golden.json`
(`tools/recapture_flat_lane_key.py --pre-change-tree <worktree at origin/main
baf702c> --control ribbon_curve.png`: machine OK, control OK) and in
`test_pushcomp.GOLDEN_FLAG_OFF` for `left_chest` (the pre-change tree
reproduces the old tuple here; `towel` is unchanged by this engine and stays
the known red). The full local suite's failure set is the three platform
goldens CI deselects and nothing else.

## What this does not do

- Travel in the satin, border, contour and streamline tiers is unchanged;
  only fill columns (stage 7's tatami/wave/chevron/brick/crosshatch paths and
  the blend tier's bands) route under cover. The contour tier's finish patches
  call `stitch_shape` without the flag and keep the old behaviour.
- It does not plan the order so that no island is ever left behind (a sweep
  order); it repairs the nearest-first walk locally. Fremont's remaining
  92 mm is that topology.
- It does not put travel under a later border. `borders_last` already sews
  borders after fills, so a bridge along a shape's edge is covered by its
  border when one exists; nothing here reasons about that.
