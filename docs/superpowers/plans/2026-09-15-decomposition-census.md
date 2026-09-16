# Decomposition census — item 5 measured before it is built (2026-09-15)

Kent's pick 2026-09-15: item 5 of `docs/quality-review-2026-09-08.md`
(stroke decomposition), **measure first**. This is that measurement: the plan
for what comes next rests on it.

## 1. Why measure first

Item 5 blamed the raster medial axis for Becker's trims (29 vs the pro's 12),
the K's bare crotch (37 mm²), the N's diagonal welded through a 108° fold,
and the H/E deformation. A prior-art sweep of the plans, DOCTRINE and memory
found that premise unestablished and its numbers stale:

- DOCTRINE records Becker's trim cause as travel **timing** — five hypotheses
  refuted, *"WHERE to change that … is not established"* — and letter
  fidelity as living *"in the rails, not the skeleton"*.
- Since 09-06: junction clustering shipped (Becker bare 16.0 → 9.0 mm²), the
  K reads 9.0 mm² not 37, Becker is 36 strokes not 27, and the 09-03 Goldman
  join may have closed the N — never re-measured.
- Two `_prune_spurs` prototypes were unshippable (the H defect on every
  square-capped bar; −18.3% / +20.5% on one baseline). A global spur
  multiplier was refuted (2 fixed, 2 broken, 7 tests). More raster was never
  tested on its own. A polygon-native axis was named and never built.

## 2. The instrument — `digitizer/tools/decomposition_census.py`

No engine change. It swaps the skeleton SOURCE inside
`stage6_satin.extract_strokes` for one digitize at a time; everything after
the skeleton (pinhole collapse, junction clustering, merge, corner splits,
rails, travel) is shipped code.

| arm | skeleton |
|---|---|
| `shipped` | as shipped |
| `raster12` / `raster24` | medial-axis raster at 2× / 4× (6 → 12 / 24 px/mm) |
| `noprune` | `_prune_spurs` off |
| `polyaxis` | **polygon-native**: Voronoi of the densified boundary (shapely, BSD), an edge kept only when its generators lie more than 2 × 1.6 local radii apart along the boundary (the boundary-arc residual test), drawn onto `_rasterize`'s grid |

`polyaxis` first used leaf-length pruning, and that is the wrong test,
measured on a 10 × 2 mm bar: the Voronoi axis runs spine → one corner
diagonal with no junction node, so the hook into the cap corner (the H
defect's shape) survived. The residual test gives the exact axis (x 1–9 at
y = 1). `tests/test_decomposition_census.py` pins it on a bar, a crossing,
a ring and the grid mapping, plus the fold metric.

**Confound, reported:** `_stroke_rows` (classifier rung) also calls
`extract_strokes`, so each row carries `tier_moves` against `shipped`.

## 3. Result (Windows, same-machine A/B — arms compare, absolute grades do not; DOCTRINE 2026-09-15)

| design | arm | stitches | trims | in-shape | strokes | folds >90° | folds >60° | bare mm² | satin share | tier moves |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| becker80 | shipped | 6,829 | 51 | 40 | 38 | 0 | 1 | 12.2 | 0.468 | – |
| | raster12 | 6,511 | 49 | 38 | 34 | 0 | 0 | 13.2 | 0.483 | 0 |
| | raster24 | 6,200 | 53 | 42 | 40 | 0 | 0 | **17.7** | 0.514 | 0 |
| | noprune | 6,555 | 63 | 52 | 47 | 0 | 1 | 12.0 | 0.497 | 0 |
| | **polyaxis** | **6,076** | 50 | 39 | 32 | 0 | 0 | **4.2** | 0.510 | 0 |
| becker95 | shipped | 16,545 | 43 | 32 | 1 | 0 | 0 | 0.0 | 0.096 | – |
| | (every arm) | ±40 | 43–44 | 32–33 | 1 | 0 | 0 | 0.0 | 0.096–0.098 | 0 |
| | **PRO** (committed DST) | 11,274 | **12** | | | | | | **0.443** | |
| enthusiast | shipped | 3,444 | 32 | 19 | 24 | 0 | 0 | 7.0 | 0.396 | – |
| | raster12 | 3,280 | 22 | 9 | 25 | 0 | 0 | 0.0 | 0.456 | 0 |
| | raster24 | 3,251 | 27 | 16 | 30 | 0 | 2 | 3.7 | 0.447 | 0 |
| | noprune | 3,474 | 37 | 22 | 27 | 0 | 0 | 3.7 | 0.401 | 0 |
| | **polyaxis** | 3,454 | **25** | **9** | 31 | 0 | 0 | **0.0** | 0.456 | 0 |
| fremont | shipped | 16,479 | 64 | 28 | 71 | 0 | 1 | 0.0 | 0.166 | – |
| | raster12 | 16,508 | 68 | 35 | 72 | 0 | 1 | 0.0 | 0.167 | 0 |
| | raster24 | 16,537 | 69 | 36 | 75 | 0 | 0 | 0.0 | 0.167 | 0 |
| | noprune | 16,569 | 70 | 37 | 80 | 0 | 0 | 0.0 | 0.168 | 0 |
| | **polyaxis** | 16,450 | **61** | 28 | 62 | 0 | **4** | 0.0 | 0.166 | 1 |
| drone | shipped | 18,194 | 138 | 49 | 111 | 0 | 1 | 0.0 | 0.233 | – |
| | raster12 | 18,792 | 144 | 58 | 132 | 0 | 2 | 0.0 | 0.256 | 0 |
| | raster24 | 19,586 | 141 | 55 | **167** | 0 | 1 | 0.0 | 0.297 | 0 |
| | noprune | 17,938 | 141 | 54 | 122 | 0 | 0 | 0.0 | 0.217 | 0 |
| | **polyaxis** | 18,569 | **132** | **44** | 118 | 0 | **5** | 0.0 | 0.229 | 1 |

`python tools/decomposition_census.py --workers 5` (cwd `digitizer/`),
7.5 min on 8 cores.

## 4. What it says

1. **The N weld is gone on HEAD.** No column member folds past 90° in any of
   the 25 runs. MASTER_SCOPE area 1's 08-26 "still open and unfixed" line is
   stale.
2. **Pixels are not the lever.** Raising the raster is non-monotonic and
   often worse — Becker 80 bare 12.2 → 17.7 mm² at 4×, drone 111 → 167
   strokes. A finer raster gives the thinning more wiggles to branch on; the
   defect is in the construction, not its resolution.
3. **The polygon-native axis is the one arm that helps everywhere it can.**
   Bare satin Becker 80 −66%, enthusiast 7.0 → 0; trims −1 / −7 / −3 / −6;
   in-shape trims enthusiast 19 → 9, drone 49 → 44; strokes down on three of
   four. Classifier confound one shape on two designs. **Price to check on a
   render before anything ships:** folds past 60° inside a column, Fremont
   1 → 4 and drone 1 → 5.
4. **At the pro's own size, decomposition cannot reach the Becker gap.** At
   95.7 mm Becker routes ONE satin shape — every arm is within 40 stitches —
   so our 43 trims vs the pro's 12 and our 9.6% satin share vs his 44.3% are
   the satin/fill ROUTING cliff (`research-gap-audit-2026-09-12.md` §4.2;
   area-weighting, Kent's queue), not the skeleton. The review's "29 vs 12
   on identical artwork" motivation belongs to that lever.
5. **So the premise is half right:** the skeleton construction owns bare
   junctions and a share of in-shape trims; it does not own the Becker
   parity gap, and raster resolution is not the fix.

## 5. Next PRs, in order (each Kent's to start)

1. **`cfg.satin_polygon_axis`, DEFAULT OFF, byte-identical off — BUILT
   2026-09-16**, `digitizer_core/polygon_axis.py`, wired to BOTH readers
   (`satin_shape` and the per-stroke rung `_stroke_rows`; the pooled DT
   classifier stays on the raster, deliberately — it measures widths rather
   than walking a skeleton). The census now sets that flag instead of
   patching its own copy. **Two results the flag PR rests on:**

   **The folds are mitres, not welds.** Rendered every `folds>60` member on
   Fremont and drone against `shipped`: they sit at letter junctions — the
   M's V, the T's stem, the H's bar. On Fremont's T the polygon axis
   UPGRADES the top bar from a thin bean run to a real satin column, which
   is why its count rose. `docs/renders/polygon-axis-2026-09-16/`.

   **The density price is the opposite of what the render suggested.** Drone's
   M gains crossing columns by eye, so `coverage_max` was measured beside the
   bare-area win: **drone 10.70 → 6.73** — from over the 9.33 block ceiling to
   under the 6.67 warn line — enthusiast 4.70 → 6.28, becker 80 4.57 → 5.38,
   Fremont unchanged at 6.69, no grade moving. The eye read a busier picture
   as more thread; the instrument says drone sheds its worst stack.

   **Corpus A/B, 26 fixtures at 80 mm / left_chest** (`tools/flip_sheet.py`,
   arm `polygon_axis`): **20 move, 6 byte-identical; net −276 stitches, +15
   trims, and blocks, cones and colour stops all unchanged.** Three grades up
   — **becker B 76 → B 88**, `logo_script_tires` B 88 → **A 100**,
   `photo_dof_meadow` C 64 → B 76 — and one down, `photo_grass_macro`, which
   stays F while its raw score falls 22 → 10.

   **Read the +15 per fixture, because it inverts by artwork kind.** Trims
   FALL on six of the seven real customer logos — drone −6, tires −2,
   enthusiast −2, becker −1, gaulke −1, the screenshot −1 — and RISE on the
   photographs and synthetics (summit +6, the gradient repro +5, bridge_bar
   +4, grass_macro +2, meadow +1, chrome +1), plus `logo_golden_tee` +10,
   the one real logo that pays. A satin skeleton on a photograph is reading a
   segmenter's blobs, not strokes, which is where the flag has least business
   and shows its worst rows; the lane this was built for is where it wins.

   **Runtime: roughly neutral.** becker at 80 mm 24.7 → 29.1 s (×1.18),
   enthusiast 40.1 → 38.9 s (×0.97), both measured while other cores were
   busy, so read them as "no order-of-magnitude cost", not as a benchmark.
2. **Area-weighting for `classify_ribbon`** — the lever this census points at
   for Becker parity; already the only survivor of #469's candidates.
3. Only then revisit `wide_columns` (blocked on decomposition, per its plan).

## 6. Limits

- Windows numbers. A same-machine A/B is valid for comparing arms; a quoted
  grade or baseline is not (DOCTRINE 2026-09-15).
- Five designs, one width each (Becker two). The fold metric reads spines,
  not stitches; a render is the judge of whether a 60° member is a defect.
- `polyaxis` is drawn back onto the shipped 6 px/mm grid so the walker is
  unchanged — the geometry is sub-pixel, the walk is not. A native graph
  walk is a further step the flag PR decides.
- Licensing: shapely (BSD-3) and scipy (BSD-3) only; the residual test is a
  published concept (boundary-arc potential residual), no code copied.
