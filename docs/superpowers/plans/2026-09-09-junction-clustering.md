# Junction clustering in stage 6 — item 5 of the quality review, first PR

**Status: BUILT 2026-09-09 (PR 1 of item 5). Kent's pick after the
`subpixel_edges` flip (#432).**

The quality review (`docs/quality-review-2026-09-08.md` §3, item 5) traces
Becker's 27-stroke outline, its 29 trims against the pro's 12, the K's bare
crotch and the N's welded fold to one thing: the raster skeleton at 6 px/mm
hands `_merge_through_junctions` a junction as SEVERAL branch pixels, and the
arms are paired per pixel. This PR takes the first, cheapest half of that:
branch nodes a short stub apart are one junction. The polygon-native medial
axis the review asks for is PR 3 of this plan, not this one.

## 0. What already governs this — read before changing the plan

- **A default that moves every polygon by a pixel finds the mechanisms that
  were balanced on one** (DOCTRINE 2026-09-09). The flip's fallout named this
  mechanism: the PLUS in `test_stroke_classify.py` decomposed into two bars
  at 6 px/mm once its diamond was collapsed and into three at 1.25×, where
  the same crossing is two 3-way nodes a pixel apart. "Adjacent junction
  pixels are not clustered anywhere; that is the next mechanism in this
  family, measured and not built." This plan builds it.
- **`_prune_spurs` never re-measures a stem its own pass un-branched**
  (2026-08-21, the extremity drop). Clustering runs AFTER the prune, on the
  edge list, and touches no mask pixel, so the guard is untouched.
- **When thread is missing at a junction, sew the hole — do not tune a
  cross** (DOCTRINE 2026-09-06): `cfg.satin_patch_junctions` covers a bare
  junction after the fact and costs +0.25% across the corpus. This plan
  changes which arms meet where; it does not replace the patch, and it must
  be measured through the instrument that reported the defect
  (`ARTWORK_UNCOVERED`), not on the geometry it computes for itself.
- **`textcluster` composes `_skeleton_edges` and `_merge_through_junctions`
  itself and gets byte-identical chains** (that function's docstring). The
  clustering pass is a separate function called only from
  `extract_strokes`; the composition `textcluster` uses is not touched.
- **A stub between two branch nodes is dropped as junction noise**
  (`extract_strokes`, `_MIN_STROKE_HALFWIDTHS` = 1.2) — but only AFTER the
  arms have been paired at each of its ends. Any clustering threshold at or
  under 1.2 half-widths removes nothing that was ever sewn as a stroke.
- **Goldens are re-captured on ubuntu-latest with the pre-change proof, never
  here** (#432's precedent). The three flat-lane keys are single-stroke
  shapes with no branch node at all (`tools/junction_nodes.py`: 0 nodes on
  whitebg, alpha, ribbon on both traces), so this PR moves no golden.

## 1. The gap

`tools/junction_nodes.py` on the corpus at the default config (ON):

| fixture | satin shapes | strokes | branch nodes | node-to-node edges | of which ≤ 0.5 half-widths |
|---|---|---|---|---|---|
| becker (80 mm) | 8 | 35 | 73 | 84 | 26 |
| drone | 43 | 88 | 80 | 76 | 9 |
| enthusiast (93 mm) | 12 | 25 | 20 | 17 | 5 |
| fremont | 19 | 61 | 45 | 34 | 0 |
| whitebg / alpha / ribbon | 1 each | 1 each | 0 | 0 | 0 |

A stub of a quarter to half a half-width between two branch pixels is not a
stroke; it is the raster's rendering of one junction whose arms meet
off-centre or whose width is even in pixels. Paired per pixel, a crossing
gives three strokes (one bar and two half-bars) and a five-way meeting a
chain of welds nobody drew.

## 2. Why the current pipeline cannot do this itself

`_merge_through_junctions` groups arms by node PIXEL (`incident[pts[0]]`)
and welds the most anti-aligned pair at each. At a split crossing each
3-way node sees three arms — two real ones and the stub — welds one pair,
and the stub is left to be dropped later by `extract_strokes`' length
filter. The pairing that should have happened between arms at DIFFERENT
pixels never can. `_collapse_pinholes` (2026-09-09) fixes the one-pixel
diamond form of this at the raster level; a stub of two or more pixels is a
graph problem.

## 3. The design

`stage6_satin._cluster_junctions(edges, max_len_px, dt_mm)`, called in
`extract_strokes` between `_skeleton_edges` and `_merge_through_junctions`:

1. every open edge with both ends at branch nodes and pixel length
   ≤ `max_len_px` is a **stub**;
2. the nodes joined by stubs are unioned; a cluster's representative is the
   member the distance transform reads deepest (the junction's centre,
   where the blob is widest), raster order breaking ties;
3. every arm that reached another member is re-rooted at the representative
   BY WAY OF the stubs' own pixels — its path stays the skeleton's, only its
   endpoint moves — and the stubs themselves are gone;
4. an edge list with no stub is handed back as the same object, so a shape
   with no split junction is byte-identical to before.

`max_len_px = max(_JUNCTION_CLUSTER_MIN_PX, _JUNCTION_CLUSTER_HALFWIDTHS ×
half_px)`. The fraction is read off the corpus (§1, §5) and is bounded above
by `_MIN_STROKE_HALFWIDTHS` for the reason in §0; the floor is the diagonal
pair (2.83 px of path) on the narrowest ribbon the raster admits.

Not in this PR: the cap-arm classifier at branch nodes (the review's second
half; `_corner_forks` already classifies corner forks by the DT profile), an
explicit junction cover (the patch flag exists), the polygon-native medial
axis.

## 4. What it should move — predictions, to be tested

- The PLUS decomposes into its two bars at both scales
  (`test_stroke_classify.py`'s scale test back to stroke-for-stroke; the
  (2, 3) pin of 2026-09-09 gone).
- Becker's outline: fewer strokes than 35 at 80 mm, fewer trims; the K's
  crotch (`Sead76620`) no worse on `ARTWORK_UNCOVERED`.
- Drone and enthusiast: fewer strokes on the shapes with stubs; stitch
  counts within a few percent.
- No flat-lane golden moves (§0).
- `crowd`/`head`/`tail` same-rail readings (the flip entry's footprint) do
  not rise.

## 5. Instrument first — `tools/junction_nodes.py`

Lists every node-to-node edge per satin shape with its pixel length, the DT
at both ends and the shape's half-width, bins them by length/half-width,
and reports strokes and nodes per fixture. The threshold is read off its
histogram; the tool re-runs after the change to show what is left.

## 6. What must not regress, with its fixture

- `tests/test_skeleton_pinholes.py`, the enthusiast "N" at 150 mm
  (`test_preflight.py`, the bracket-tab test) — the diamond fix stands.
- `test_satin.py`'s starburst test on the ribbon — no nodes, byte-identical.
- The fault-injection prune test (`subpixel_edges=False`, 150 mm).
- `textcluster`'s chains — the composition without this pass.
- The three flat-lane goldens and the pushcomp pins — 0 nodes.

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 1 | **BUILT 2026-09-09** — `_cluster_junctions`, the instrument, tests, the corpus footprint | ~150 lines + tests | none: the threshold is geometry read off the corpus, not a fabric constant |
| 2 | a cap-arm classifier at branch nodes, on the clustered graph (the review's second half) | medium | none |
| 3 | polygon-native medial axis with a millimetre-scale significance prune | large | none on construction; goldens move |

## 8. Decisions for Kent

- Whether PR 2 or the wide-column policy (review item 4) comes next.
