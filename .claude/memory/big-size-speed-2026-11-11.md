---
name: big-size-speed-2026-11-11
description: Jacket-back sizes (198-300 mm) - where the time goes, the two exact speed fixes built 11-11, and what still blocks the 600 s service limit
metadata:
  type: project
---

# Big sizes: where the time goes (2026-11-11)

Kent asked for the low-poly dolphin (`testdata/photo/corpus/low_poly.png`) at
jacket-back size beside a polo logo. The picture is fine; the run time is not.

| width | regions | stitches | whole run | vs `JOB_TIMEOUT_S` 600 |
|---|---|---|---|---|
| 96 mm (left chest) | 168 | 14,646 | ~75 s | fine |
| 198 mm (biggest hoop, what auto-fit gives) | 912 | 66,785 | 445-750 s | at the limit |
| 300 mm (fits no hoop) | 2,353 | 164,242 | 1,270-2,200 s | 2-4x over |

Region count x14 from 96 to 300 mm; `plan_stitches` x20-60. The spread in each
cell is this laptop, not the code (see "Timing trap").

## Built (exact: stitches, warnings and preflight md5-identical at 96, 198, 300 mm)

1. **Same-thread hoist** (`stage7_sequence._within_margin`). Not a pair-count
   problem: 9 blocks, 3 calls. Each call was one GEOS `distance` between two
   thread unions of 13,000-270,000 parts, which is brute force over part
   pairs (108.6 s for one pair). Pairs of 1e6+ coordinate pairs now go to
   `_parts_within_margin`: an `STRtree` over one side's parts, `dwithin` query,
   stop at the first hit. Replay of the real 300 mm calls: 144 s -> 17 s and
   134 s -> 12 s, same block order. In-run 320 s -> 26 s. Zero at 198 mm (the
   hoist costs nothing there).
2. **Per-region whole-raster work in build** (`stage4_vectorize.revalidate_threads`,
   `tag_enclosed_background`; `stage3_segment.resolve_small_regions`). Each
   region filled and summed a mask the size of the whole frame. Now a window
   (`_region_footprint_window`), and the stem test's crop sum runs after its
   box reject. Timed in-process, same session: 300 mm 240.9 s -> 51.1 s
   (build 331 -> 143), 198 mm 61.1 s -> 30.7 s (build 97 -> 69).

## Traps met

- **A fill window sized to the exterior ring is not exact.** `cv2.fillPoly`
  clips a hole ring that reaches past the canvas and fills differently. The
  window is the union box of EVERY ring; when that box leaves the frame, fill
  the full frame and crop. `tests/test_region_footprint_window.py` (400 random
  polygons, pads 0/1/3).
- **`shapely.get_num_coordinates` returns numpy int32**: 50,000 x 50,000
  wraps, and the wrapped product sends the biggest pairs back to the slow
  call. Wrap in `int()`.
- **Plain `shapely.dwithin(a, b, m)` on two collections is as slow as
  `distance`.** Only the tree over parts is fast.

## Timing trap (this laptop)

Whole-stage wall time is not an instrument here: base 300 mm
`build_generation` read 174, 283, 331, 340 s in four runs on one tree (CPU at
70% of nominal, 6.7 of 39 GB free). Time the changed FUNCTIONS in-process
with base and lane back to back, and check the untouched remainder agrees
(it did: 90.5 vs 91.5 s). Identity is by md5, which no load moves.

## Not fixed: what still blocks 198 mm

Sampling profile, 300 mm `plan_stitches`: fill order pricing 24%, fill angle
search 11%, bury trims 10%, hoist 12% (now ~1%). At 198 mm the first two
dominate and neither fix above touches them, so the hoop-size job still sits
at the 600 s limit. Next exact candidates are in those two; nothing is built.
