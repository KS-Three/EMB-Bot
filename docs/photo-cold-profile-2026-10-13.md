# Cold photo digitize, profiled — owl_kent, 2026-10-13

WoK 18 / MASTER_SCOPE defect 18: a **cold** photo digitize is ~80–90 s. The
2026-09-17 reorder memo fixed the *re*-stitch; the first digitize still pays
everything. Kent has not chosen a cure, so this pass asked a narrower
question: **what can be made faster without changing one output byte?**

**Answer: about 6%, and it ships here.** A content-keyed memo of the unsewn
ground that covered travel routes through takes owl_kent from **82.2 s to
77.3 s** (mean of 3 runs each), with the same stitch SHA-256 on every run.
Everything bigger is real geometry work, and each larger cut found changes
output or cannot be proven not to. Those cuts are Kent's to choose.

## Method

- `digitize(testdata/photo/owl_kent.jpg, PipelineConfig(target_width_mm=80,
  max_colors=6))`: customer defaults at the size the 2026-09-17 bisection
  used. Run in a fresh process each time, so every run is cold: imports,
  `lru_cache`s, the footprint cache and the reorder memo are all empty.
- Wall time comes from `time.perf_counter` around `digitize`. The output
  fingerprint is a SHA-256 of `plan_to_design(plan)["stitches"]`, serialised
  as JSON: every stitch's coordinates and flags, not a count.
- Function-level timings come from `cProfile`, which runs 92.5 s against 82.1 s
  unprofiled. Line-level timings come from `py-spy record -r 50 -f raw`, at
  4,688 samples.
- The machine was a 4-core cloud container, running one process at a time.
  Two runs overlapping on those cores slow each other down, so nothing
  overlapped.
- The fingerprint, the same on every run before and after the change:
  `adecd4cc…6a055813`, 30,711 stitches.

## Where the 82 seconds go

`cProfile` cumulative times, with the pipeline structure kept:

| | cum (profiled) | calls | note |
|---|---|---|---|
| `digitize` | 92.5 s | 1 | |
| ⤷ stages 0–4 (`build_generation`) | 10.0 s | 1 | segment 5.8 s |
| ⤷ `plan_stitches` | 82.4 s | 1 | |
| ⤷⤷ `stage6_blend.blend_fill` → `stitch_shape` | **78.3 s** | 17 | 95% of the plan |
| ⤷⤷⤷ `_reorder_for_cover` | **43.7 s** | 17 | `fill_travel_under_cover` |
| ⤷⤷⤷⤷ its `_order_cost` scoring | 37.6 s | 26 | **one call is 22.5 s** — see below |
| ⤷⤷⤷⤷ its greedy walk | ~6 s | | `slack.covers`, `_exposed_mm`, `union` |
| ⤷⤷⤷ `best_fill_angle_deg` | 15.4 s | 17 | 306 `_row_spans`, one scanline intersection each |
| ⤷⤷⤷ `emit` (laying the chosen order) | 12.2 s | 34 | 853 covered `travel_path`s, 10.0 s |
| ⤷⤷⤷ `_reorder_for_fewer_cuts` | 5.5 s | 17 | |
| ⤷⤷ satin, everything else | ~4 s | | |

`travel_path` is 47.8 s over 9,430 calls. Shapely is 65 s of the 92: `buffer`
26.8 s, `intersection` 16.6 s, `union` 10.0 s, `difference` 6.3 s, `covers`
4.2 s.

**One shape is most of it.** The owl's largest blend region has 599 fill
paths. Pricing its incoming order (`_order_cost`, the "before" in
`_reorder_for_cover`) takes **22.5 s in one call**, and pricing the greedy's
candidate takes another 9.3 s. Every other `_order_cost` on the design is
under 2.4 s.

The lines that dominate, as innermost `stage6_fill.py` frames in py-spy
(share of all samples):

| line | what | share |
|---|---|---|
| `_inset_ring` `poly.buffer(-inset)` | the inset rings of the unsewn ground, rebuilt per covered bridge | **24.3%** |
| `_row_spans` `poly.intersection(line)` | the fill-angle search's scanlines | **15.0%** |
| `travel_path` `inside = unsewn.buffer(0.01).union(…)` | the region a covered route must stay in | 9.8% |
| `travel_path` `cover.difference(sewn)` | the unsewn ground itself | 7.1% |
| `_order_cost` `sewn.union(footprint)` | the sewn footprint growing | 4.6% |
| `_exposed_mm` | route ∩ sewn | 3.6% |

## Shipped: the unsewn-ground memo (byte-identical, −4.9 s)

`cover.difference(sewn)`, its 0.01 mm widening and its inset rings depend
only on (`cover`, `sewn`). The same `sewn` footprint sequence comes up more
than once in a run. The scorer walks an order. `emit` then lays the same
order, so 527 of `emit`'s 828 covered bridges repeat a question the scorer
already asked, and 223 of the run's 749 ring builds start from the same
bytes. `_unsewn_ground` keys on the WKB of both geometries. It returns the
geometry a miss would have built, and builds each of the widened ground and
the rings only on first request. It is capped at 128 entries and emptied when
`stitch_shape` returns. `clear_fill_reorder_memo` clears it as well.

**Sizing.** A 256-entry cap held **37 MB** of geometry at the end of the run,
with entries up to 0.26 MB. That is too much to keep in a long-lived service
for a 6% gain. Every hit has to come from the same shape, because `cover` is
in the key. An offline LRU replay of the run's 837 lookups (587 distinct keys,
250 repeats) gave these hit counts by cap:

| cap | 4 | 8 | 16 | 32 | 64 | **128** | 256 |
|---|---|---|---|---|---|---|---|
| hits of 250 | 61 | 71 | 89 | 111 | 163 | **250** | 250 |

So 128 keeps every hit. Emptying the memo at the end of each shape means
nothing is held between shapes or between jobs. At most one shape's 128
entries are live at a time, roughly 33 MB at the largest entry size measured.

| arm | run 1 | run 2 | run 3 | mean | stitches SHA |
|---|---|---|---|---|---|
| main | 82.08 s | 81.48 s | 83.14 s | **82.2 s** | `adecd4cc…` |
| memo | 77.58 s | 76.81 s | 77.61 s | **77.3 s** | `adecd4cc…` |

The runs alternated base, new, base, new; run 1 of each was a separate pass.
The difference is **−4.9 s (−6%)**. That is about three times the spread
within either arm (1.7 s for main, 0.8 s for the memo). These were measured
at the first cap of 256.

**The container drifted during the session, so compare runs only within the
same time window.** About an hour later, the memo disabled (cap 0) ran in
88.5 s and cap 256 in 84.0 s. That is −4.4 s, in line with the table, but
every number had moved up by about 6 s. The final 128-cap build was re-timed
against main, alternating, and that result is in the PR body.

**Why it is exact, not approximately so.** GEOS is deterministic on the same
coordinates, and WKB carries every coordinate bit-for-bit, so equal keys mean
equal inputs. The stored values are immutable shapely geometries. The ring
list a caller gets is a fresh `list`, so its in-place `sort` and the stale-ring
cache behave as before. `tests/test_unsewn_ground_memo.py` pins this with
three unit tests: a hit equals a miss, a different `sewn` gets a different
answer, and the memo is bounded. A fourth test plans owl_kent twice, once
memoized and once through the inline computation the memo replaced, and
compares every stitch.

## Tried and not shipped

| candidate | measured | why not |
|---|---|---|
| Build `inside` lazily, skipping it when no ring passes the length budget | samples on that line 461 → 496, so no change | Some candidate always reaches the containment test. The idea was sound and the gain was zero, so it was reverted. |
| Memoize the whole covered `travel_path` call | ≤3.7 s (the 527 repeated `emit` calls), partly overlapping the memo above | Exact in principle. But the answer also depends on the per-shape route cache's stale rings, and the call writes to that cache. The key would have to carry that state and the memo would have to replay the write. That is more machinery than −6% justifies in a byte-identical pass; it is the next candidate if one is wanted. |
| Vectorise `_row_spans` (`shapely.intersection` over an array of scanlines) | `_row_spans` self time is 0.5 s of 15.4 | It is the same GEOS call per element, so it is exact, but it only removes Python overhead. The 15 s is GEOS overlay work. |
| Intersect all of an angle's scanlines in one overlay | not run | OverlayNG nodes and merges a multi-line input differently, so identical output cannot be proven. The 2026-09-12 simplify experiment already showed that angle-search shortcuts move angles (`docs/flag-runtime-bills-2026-09-12.md`). |
| Reuse the winning angle's scanlines in `_fill_paths` | ≤ 1/18 of 15.4 s ≈ 0.8 s | Exact, but small. |
| Prepared geometries for `covers` | `covers` is 4.2 s in total | GEOS prepared predicates use a different algorithm. Routes that hug the boundary are exactly where the two could disagree, and the code widens `slack` by 0.01 mm for that reason. Not provable. |
| Skip the "after" `_order_cost` when the greedy returns the incoming order | ~0.1 s | Exact, but the big shape always reorders, so there is nothing to win. |

## What is left, and it is Kent's

After this change, about 72 s of the 77 s is `stitch_shape` on 17 blend
regions. `fill_travel_under_cover` is still its largest bill (≈ 40 s). Most of
that is pricing two orders of one 599-path shape, and the routing it prices is
the feature itself. The 2026-09-17 options still stand, and none of them is
byte-identical:

1. turn the flag off, which costs +2,500 stitches on owl_kent and brings back
   the exposed travel it hides;
2. change the algorithm: price fewer orders, or cap the probe on very large
   shapes. This moves output, and the golden tests would have to be
   re-blessed;
3. accept the cold cost. The review-edit path is already memoized.

**Not measured here:** other photographs, Kent's Windows box, and the
service's `/digitize` overhead. The −4.9 s comes from one fixture on one
container.
