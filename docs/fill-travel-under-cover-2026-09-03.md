# Fill travel under cover — defect 21, fixed, default ON by Kent's flip (2026-09-03)

Kent's note 1 on the Hotel Fremont screenshot: *"The in-fill stitching doesn't
look clean, not sure if it's the stitch out or the stitch rendering."* Traced
2026-09-02 (`docs/hotel-fremont-fine-details-2026-09-02.md`): the stitches.
The professional file's tatami renders smooth through the same `stitchviz`;
ours laid 22 of 27 fill-phase travel runs — 286 of 450 mm — on top of columns
already sewn. A pro hides travel under fill still to come or along an edge a
border covers. Kent picked this as the next item on 2026-09-03.

## The instrument

`tools/fill_exposure.py` (committed), and the test helper `_fill_exposed_mm`
in `tests/test_fill.py`: walk a shape's runs in sew order, accumulate the
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

## Review fix, same hour — a covered route could leave the shape

The endpoint allowance (one travel stitch around each end of a covered
route, needed because the bridge starts inside the column it just finished)
was unioned into the containment region UNCLIPPED, so a route through the
unsewn rings could leave the polygon by up to 2.5 mm near either end —
1.48 mm across a 1.5 mm slot, measured — and `_order_cost` scored it as a
bridge instead of the cut it should be. Fixed: the discs are clipped to the
shape and every covered route is hard-tested against the shape as well
(`test_covered_routing_never_leaves_the_shape`). The wins survive; a few cuts
return. All numbers below are after the fix.

## Measured, flag on vs off (fill-phase travel over the sewn footprint)

| fixture | exposed | stitches | trims |
|---|---|---|---|
| `logo_hotel_fremont` @ 80 (Kent's settings) | **286 → 90 mm** (22 → 6 runs) | 6473 → 6385 | 47 → **52** |
| `logo_gaulke_roofing` | **204 → 8 mm** (9 → 1) | 3954 → 3863 | 24 → 26 |
| `becker_marine_logo` | 30 → 14 mm | 4557 → 4529 | 28 → 28 |
| `logo_whitebg` | 10 → 10 mm | 2166 → 2162 | 6 → 6 |
| `drone_render` (blend tier) | **546 → 89 mm** (32 → 13) | 9317 → 8753 | 86 → 91 |
| `photo_dof_meadow` | 691 → 324 mm | 10116 → 9667 | 33 → 35 |
| `photo_sunset_backlit` | **711 → 344 mm** | 12345 → 11620 | **53 → 42** |

Flag off is md5-identical to `origin/main` on becker, drone, enthusiast and
Fremont. `enthusiast_logo` has no fill travel at all and is untouched either
way. The trims that come back are the score buying hidden travel with cuts
at 2 : 25 — the 2.0 exposed-stitch weight is an unanchored judgement (unlike
`_TRIM_STITCH_EQUIVALENT`'s 25, which Kent set), and whether five more cuts
on Fremont are worth 196 mm less visible travel is his call.

Two instruments, do not mix them: the fill-phase figure above counts travel
inside fill-tier shapes against their own sewn footprint with a one-stitch
tolerance; the 2026-09-02 "39 runs, 570 mm" and the render's "30 runs,
564 mm" count every travel run in the design against a half-row footprint
with no tolerance. Same defect, different denominators.

Whole-design render (every tier, half-row footprint): Fremont exposed
**564 → 303 mm**, 30 → 20 runs; the long diagonals across the lower field are
gone, what remains is hauls between the regions the letters cut the field
into.

## Cost

| fixture | flag off | flag on |
|---|---|---|
| Fremont | 10.9 s | 12.1 s |
| gaulke | 38.0 s | 40.5 s |
| drone | 22.8 s | 24.5 s |
| meadow | 14.3 s | 19.4 s |
| sunset (263 fill runs) | 33.6 s | **50–56 s** |

Two optimisations landed on the way, both behaviour-preserving: `_ring_route`
rebuilt its cumulative arc table on every call — **34.8 s of a 90 s profile**
on sunset, the hottest function in stage 6 before this change existed — and is
now cached per ring; and the unsewn-ground rings are reused across
consecutive bridges, re-checked against the CURRENT unsewn ground, before the
inset buffer is rebuilt. What remains on sunset is the covered scoring pass
itself (`_order_cost` with routing, twice per shape) and the shapely set
operations behind it; the cost is superlinear in fill-run count. The app's
poll budget is 300 s and the 60 s budget in `tests/test_service.py` is on
small fixtures, so it ships un-gated; the cheapest next step is to reuse the
winning `_order_cost` pass's bridges in `emit`.

## Default ON — Kent's flip, and the goldens

Built default OFF (Kent picked the work item, not the default); flipped ON
the same session on the numbers above, with the 2 : 25 exposed-vs-cut
weight ratified. `logo_whitebg` moved by exactly its travel (2166 → 2162
penetrations; region ids, areas, warnings unmoved) and is re-pinned in
`flat_lane_golden.json` via `tools/recapture_flat_lane_key.py
logo_whitebg.png --pre-change-tree <worktree at origin/main f4009a6>
--control ribbon_curve.png` (machine OK, control OK) and in
`test_pushcomp.GOLDEN_FLAG_OFF[("logo_whitebg.png", "left_chest")]` (the
pre-change tree reproduces the old tuple here); `towel` is unchanged by this
engine and stays the known red.

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
