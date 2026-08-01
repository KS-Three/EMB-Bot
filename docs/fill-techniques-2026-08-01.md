# Fill techniques beyond tatami — engine-ready specs

Continues the numbered laws. 1–14 were geometry and pipeline; 15–38 were thread, needle, fabric and shop floor. **39–44 are what the fill family demands** — the four techniques that sit beyond boustrophedon tatami: contour, motif, gradient/crossfade, and curved/flow.

Source tags as always: **[P]** primary (vendor doc, patent, peer-reviewed) · **[T]** named trade expert · **[B]** blog-corroborated · **[D]** our derivation · **[U]** unverified. Status tags: **Desk-safe** (ship on published values) · **Corpus-gated** (needs a census of our own output or the pro corpus first) · **Sew-out-gated** (needs thread on fabric before the constant is real).

---

## Part 0 — The seam we are building against

Every one of these four plugs into the same socket stage 7 already calls three times (`stitch_shape`, `satin_shape`, `run_outline`):

```
emit(poly, shape_id, *, <technique params>, trim_at_mm, start_near) -> (list[StitchRun], report)
report = {"too_thin": bool, "jumps": int, "empty": bool}
```

Five rules that contract implies, and which every new emitter must obey for **stage 7 to stay unchanged**:

1. **No emitter creates ties.** `_apply_ties` owns lock stitches and folds them into the run they protect. An emitter that emits its own ties gets them doubled — eight stitches of thread piled in one spot, exactly the failure the existing comment warns about.
2. **Every run carries its own `jump` / `trim`.** Trim is decided against `fabric.trim_at_mm` at emit time, and `report["jumps"]` counts the failures so `LONG_JUMPS_TRIMMED` can fire.
3. **Underlay runs first**, `kind=UNDERLAY`, then the fill body. Ordering within a shape is the emitter's business; ordering between shapes is stage 7's.
4. **The emitter enters at `start_near`** and picks whichever of its own valid entry points is nearest. Stage 7 settled order before stitches existed and is holding the cursor.
5. **One shape → one contiguous span of runs inside one `StitchBlock`.**

Rule 5 is the only one any of the four breaks, and only one breaks it: **the two-colour crossfade emits K blocks**. The fix belongs at stage 5, not stage 7 — see §3.4. Everything else is a new file next to `stage6_fill.py` and a branch in `sequence()`'s tier ladder.

---

## Part 1 — Laws 39–44

**Law 39 — Three of the four are wrappers; only one is a new emitter.** Curved fill is a coordinate change around the tatami row generator. Gradient is a different row *schedule* through the same generator. Pattern fill (the cheap tier of motif) is a wider stagger table. Only contour fill — and motif's Tier B tiler — generate geometry the existing engine cannot produce. Scope accordingly: the expensive-looking features are cheap and the cheap-looking one is not. [D]

**Law 40 — Rows are level sets of a phase function, and at a fixed stitch angle density may vary only along the row normal.** Rows satisfy `s = 1/|∇Φ|`; a prescribed density field `d` and direction field `n` admit a smooth Φ only when `curl(d·n) = 0`. With `n` constant that collapses to: **any along-row density variation is unrepresentable.** A genuine radial density ramp at fixed angle does not exist. Project it onto the normal, encode it in *colour assignment* instead, or route the shape to the contour tier. This is why Ink/Stitch ships Circular Fill and Contour Fill as separate methods rather than as fill parameters. [P Knöppel et al., SIGGRAPH 2015, doi:10.1145/2767000; collapse to the fixed-angle case is [D]]

**Law 41 — Coverage is additive in density, never in spacing.** `C = w·Σ(1/s_c)`. Mirroring a spacing profile — which is exactly what Wilcom's "choose complementary profiles" instruction invites — puts a **+33 % coverage bulge at both ends** of every blend and leaves the "pure" ends impure. The correct complement is hyperbolic: `s_c = p/α_c`, which conserves `Σd = 1/p` identically. [D, arithmetic verifiable in one table; the vendor instruction it corrects is [P] Wilcom]

**Law 42 — A chord lies on the concave side, and endpoint containment tests miss it.** Sagitta `≈ L²/8R`. At L = 4 mm, R = 5 mm that is **0.4 mm outside the shape** with both endpoints testing inside. Every technique here introduces curved rows or curved rings, so every one of them can violate "no stitch outside the shape" in a way tatami never could — tatami's rows are straight. Cap stitch length by curvature (`L ≤ √(8·R·tol)`) and clip against the inset shape after emission, not before. Wilcom's Spiral Fill ships with this bug in its own documentation: "Longer shapes may generate stitches extending beyond the object's perimeter." [P Wilcom; sagitta [D]]

**Law 43 — Where the metric stretches, the penetration lattice and the stitch length cannot both be exact.** Wilcom chose the lattice and capped stitch length at 4.00 mm to keep the stretched lengths legal; Ink/Stitch re-chops in XY and admits in a source comment that "we already are way off when it comes to stitch positions." Choose deliberately and per run-kind: **lattice-coherent for fill rows, re-chopped in XY for travel.** Travel is a run stitch — there is no lattice to protect, so re-chopping it is free. [P US6587745B1 + Hatch tuning advice; the split-by-run-kind rule is [D]]

**Law 44 — Ring-to-ring and row-to-row transitions are stitches, not travel, and they land under the floor.** Adjacent contour rings are one row spacing apart — 0.40 mm — and a naive hop emits a 0.40 mm segment against a 1.0 mm floor (Law 18) inside the 0.5 mm same-hole radius (Law 17). Neither milling nor FDM has a minimum segment length, so **no paper in the CAM literature addresses this and every reference implementation will hand us sub-minimum stitches.** Walk 1.0–1.5 mm *along* the ring while translating, giving √(1.5² + 0.4²) ≈ 1.55 mm. [D; the geometry it fixes is [P] via Ink/Stitch's `1.5 * offset` threshold]

---

## 1. Contour fill — uniform inward-offset rings

### 1.1 Chosen algorithm

**Uniform inward offsets → nesting forest → inner-to-outer continuous linking.** Not a spiral, not yet.

This is Wilcom's **Offset Fill** semantics ([curves-5.htm](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Decorative/curves/curves-5.htm)) and Ink/Stitch's default *Inner to Outer* strategy ([inkstitch.org/docs/stitches/contour-fill](https://inkstitch.org/docs/stitches/contour-fill/)), and it is the only variant with **no topological precondition** — it terminates on every shape: necks, holes, thin arms, five-way branches. Every spiral variant (single spiral, Fermat, Connected Fermat Spirals) is a *re-linking of the exact same ring forest*, so Phase 1 builds 90 % of the spiral work and Phases 2–3 arrive behind a strategy flag without touching ring generation.

The degeneracy taxonomy is Held's (CAD 1994, [doi:10.1016/0010-4485(94)90042-6](https://doi.org/10.1016/0010-4485(94)90042-6)); the linking problem is Park & Chung (CAD 2002, [doi:10.1016/S0010-4485(01)00088-4](https://doi.org/10.1016/S0010-4485(01)00088-4)). **Do not build the Voronoi route.** Held's proximity maps exist to make split/merge events combinatorial rather than numerical; Clipper2 does that robustly enough at embroidery scale, and Ink/Stitch's rebuild-containment-every-iteration approach is empirically sufficient.

Deferred, explicitly: Fermat/CFS (Zhao et al., ACM TOG 2016, [doi:10.1145/2897824.2925958](https://doi.org/10.1145/2897824.2925958)) buys a boundary-anchored start *and* end — ideal for lock placement and object chaining. In FDM that saves retractions; for us it saves trims, and **our edge-walk travel already makes travel cheap**, so the marginal value is real but lower than in the source domain. It does not gate v1.

### 1.2 Emitter architecture — `stage6_contour.py`

**In:** `poly` (with interiors), `spacing_mm`, `stitch_mm`, `strategy`, `underlay_style`, `trim_at_mm`, `start_near`.

```
offset_rings(poly, s)      -> RingForest      # networkx-free: parent/child by containment
resample_ring(ring, ...)   -> polyline        # one-sided inward tolerance, phase-shifted
link_inner_to_outer(forest, start_near) -> list[StitchRun]
```

- **Rings.** Inset `s/2`, then repeatedly by `s`. Rebuild parent/child containment *every iteration* — never cache; a hole approaching the outline changes nesting mid-sequence. Holes are nodes with negative offset (expanding out while the exterior contracts in). Filter rings with area < 0.1 mm² or fewer than 4 coords. `mitre_limit ≈ 2` or round joins — Ink/Stitch's 10 produces spikes the needle has to chase.
- **Linking.** Recurse into children before continuing the parent; on exit, skip forward `s` along the parent. Entry points searched within `1.5·s`, hard fallback `2.05·s`. **Where Ink/Stitch silently skips a child that has no qualifying entry point, we count it** — a skipped child is an unfilled region and must reach `report` and a warning code.
- **Transitions (Law 44).** Diagonal, ≥ 1.0 mm along-ring travel while translating. This also kills the radial "seam" of aligned transitions, which is the single loudest tell of machine-generated contour fill.
- **Runs.** All body geometry is `kind=FILL`, one continuous run per subtree. Transitions are *inside* the run, not between runs — that is the point.
- **Travel between subtrees** (after a neck splits the forest) uses the existing `travel_path(poly, ring, a, b, slack)` unchanged. Contour fill is near-zero-travel by construction; the only travel is inter-subtree.
- **Underlay:** emit one contour ring at inset `1.5·s` as edge-walk, plus a coarse ring set at `3·s`. Ink/Stitch's documented limitation is that contour underlay *doesn't follow contours* — it uses the fill angle. Beating that is one function call and a visible differentiator.
- **Ties / sequencing:** untouched. Ties land on the outermost ring under the border, which is where they belong.

### 1.3 Parameters

| Expose (`PipelineConfig`) | Pin (`machine.py`) |
|---|---|
| `contour_spacing_mm` (default `FILL_ROW_MM`) | `CONTOUR_FIRST_INSET_FRAC = 0.5` |
| `contour_strategy = "inner_to_outer" \| "fermat"` | `CONTOUR_ENTRY_SOFT = 1.5` / `_HARD = 2.05` (× spacing) |
| `contour_tolerance_mm` (Ink/Stitch's "running stitch tolerance"; default 0.10) | `CONTOUR_TRANSITION_MIN_MM = 1.0` |
| `contour_offset_fraction` (Wilcom's name for the stagger analogue) | `CONTOUR_PHASE_STEP = 0.618` (golden ratio, **not** 1/4 — ring circumferences all differ, so a fixed quarter re-aligns quasi-periodically) |
| | `CONTOUR_MIN_RING_MM = 3.0` (perimeter < 3·`MIN_STITCH_MM` → bean tack or drop) |
| | `CONTOUR_MITRE_LIMIT = 2.0` |

### 1.4 Failure modes and guards — instrument first

| # | Failure | Instrument (build this first) | Guard (threshold the census justifies) |
|---|---|---|---|
| C1 | Ring starvation in necks < `s` — bare fabric stripe | `tools/census_pro.py --contour`: histogram of per-ring nearest-neighbour distance, and a coverage raster diff against the polygon | Warn `CONTOUR_NECK_STARVED` when uncovered area > 1 % of shape; Phase 3 adaptive spacing is the fix, not a clamp |
| C2 | Chord escapes on hole rings and reflex corners (Law 42) | Post-emit containment census on the *inset* polygon, not the polygon | One-sided tolerance at resample: `e_max` inward, 0 outward. Hard clip after emission |
| C3 | Sub-floor transitions (Law 44) | Stitch-length histogram per run-kind, same instrument as the satin same-rail census | Assert min stitch ≥ `MIN_STITCH_MM` after emission; the diagonal makes this pass by construction, the assert catches regressions |
| C4 | Radial spoke artifact on circles/rects | FFT the angular distribution of penetrations per ring set | `contour_offset_fraction` phase shift; reject if any angular harmonic exceeds the flat-field baseline |
| C5 | Silently skipped child ring | `report["skipped_rings"]` counter | New code `CONTOUR_RING_UNREACHABLE`, `extra: {"count": int}` |
| C6 | Wedge underfill at sharp tips | Area census against Arachne's closed form `¼(w*)²(tan(α/2) − α/2)` | Warn, and take Wilcom's answer — recommend cutting the tip in the worksheet. Do not silently sliver |
| C7 | Invalid offset geometry / slivers | count of `make_valid()` repairs per shape | drop area < 0.1 mm², count them |

### 1.5 Test plan

Synthetic fixtures into `digitizer/testdata` via `tools/make_hard_cases.py`:

1. **Annulus** — hole handling. Wilcom's Spiral Fill *ignores holes entirely*; our floor is "zero penetrations inside the hole, asserted."
2. **Dumbbell** at neck = 1.5·s / 1.0·s / 0.7·s / 0.4·s. Assert: forest branches below 2·s; no ring below 0.35 mm neighbour distance; C1 instrument reports the starvation rather than the engine hiding it.
3. **Five-point star** — wedge underfill + tip ring dropped, not slivered.
4. **Crescent** — the Law 42 test. Reflex corner, hole ring, chord violation.
5. **Letter "e"** — hole approaching outline mid-offset; nesting re-derivation.
6. **Comb, five 1.2 mm arms** — five-way branch. Assert `inner_to_outer` succeeds and that a future `fermat` strategy *refuses* rather than producing garbage.
7. **50 mm circle** — C4 spoke FFT with and without offset fraction.
8. **2 mm-wide S-curve** — degenerates to ~5 rings or hands off to satin. Must not produce a smear.

Measure, every fixture: stitch-length histogram, ring-to-ring nearest-neighbour distribution, containment (100 %, no exceptions), stitch count vs. tatami on the same shape, `report` counters.

### 1.6 Effort and payoff

**Phase 1: 5–7 engineer-days**, ~600–750 LOC in `stage6_contour.py` + ~250 LOC tests. Dependency: `pyclipr` (BSL-1.0) or `pyclipper` (MIT) — both permissive; Shapely already present. Phase 2 (Fermat) +4 days. Phase 3 (Arachne adaptive spacing, `arXiv:2004.13497`) +5 days and needs `skimage.morphology.medial_axis(..., return_distance=True)`.

**Payoff:** market parity with Wilcom Offset Fill and Hatch's "Inner to Outer" in one feature. Visibly different output on rings, letters, and any shape where tatami's straight rows fight the silhouette — even needle distribution in shapes of varying width, which is the exact thing tatami cannot do. And it clears two bars Wilcom's own product violates: holes are respected, and no stitch leaves the shape.

---

## 2. Motif & patterned fill

### 2.1 Chosen algorithm — and the taxonomy the vendors blur

| Tier | What varies | Relation to us today |
|---|---|---|
| **A. Pattern (needle-point) fill** | Where penetrations land inside otherwise-normal tatami rows | **Generalization of `_stagger_slots` / `_stagger_phase`** |
| **B. Motif fill** | A stitch-figure tiled on an affine lattice | New emitter |
| **C. Motif run** | One motif repeated along a path | Trivial once B exists |

Embird states Tier A outright: pattern "is created with layout of needle points within rows of stitches. Therefore, **length of stitches in fill is given by needle points distance in pattern**" ([Embird fill parameters](https://www.embird.net/machine-embroidery-tutorials/studio-next/par_fill.htm)). Tajima DG16 advertises the same split (>40 standard fill patterns vs. >165 programmed).

**Tier A is the cheapest ship in this entire document.** `_stagger_phase(row_index, staggers, stitch_mm)` returns a scalar from a 4-element sequence. A pattern fill replaces that with a table: `pattern[row % R] -> [fractional needle offsets across the row]`. Row generation, hole handling, edge-walk travel, containment, the 0.35 mm floor, the 1.0–12.1 mm window — **nothing changes**. A few hundred lines, zero new invariants.

Tier B's algorithm is **anchor-lattice tiling with Eulerian anchor-splice routing**, taken from Ink/Stitch's `cross_stitch.py` (GPL-3.0 — method only, no code) rather than from any vendor doc, because it is the only open implementation that solves the routing problem honestly.

The load-bearing design fact, consistent across all three vendors: **a motif is defined by its anchors, not by its drawing.** Wilcom: "Click two reference points for the motif. These should coincide with entry and exit points," and those points determine *both* orientation and default spacing ([Create & save motifs](https://docs.wilcom.com/embroiderystudio/e4/en/MainHelp/Decorative/motifs/Create_save_motifs.htm)). So RP1→RP2 **is** the tiling basis vector, default column spacing = |RP2 − RP1|, and the exit anchor of motif *n* is the entry anchor of motif *n+1*: **inter-motif travel is zero-length by construction.** Nothing to hide because nothing to travel.

### 2.2 Emitter architecture — `stage6_motif.py`

**In:** `poly`, `motif` (a definition object), lattice params, `boundary_mode`, `trim_at_mm`, `start_near`.

Motif definition, authored in a unit box:
```
polyline    : list[(x,y)]              # one connected chain, underlay-free (Wilcom's own rule)
anchors     : {anchor_id: (x,y)}       # entry + exit minimum
good_anchors / bad_anchors             # anchors from which the tour needs no exposed travel
min_leg / max_leg (unit space)         # precomputed, for the §2.4 scale validator
```

Pipeline:
1. **Rotate the shape by −angle** about a stable origin, tile axis-aligned, rotate stitches back. Same trick for mirrored rows. Cheaper and more exact than rotating every cell.
2. **Quantize the lattice origin**: `origin = min − (min mod cell) − offset`, with an `align_grid_to = shape_bbox | global` switch. This is what makes two adjacent regions with identical params tile continuously. **Build it day one** — retrofitting changes every output.
3. **Cell selection**: `shapely.prepare(poly)` once, then `contains` → whole, `intersects` → accept iff overlap ≥ `coverage_pct`.
4. **Routing**: anchor graph, keyed by **integer lattice identity `(i, j, anchor_id)`** with a canonical rule mapping shared anchors of neighbouring cells to one key. Ink/Stitch matches anchors by exact float-tuple equality, which survives only because every coordinate comes from identical arithmetic; integer keys are exactly equivalent, strictly more robust, and make multi-lattice overlays exact by construction instead of by `nearest_points` snapping. Then: seed from an anchor belonging to exactly one motif (biases the start to the region's outer edge), splice unvisited motifs at every good anchor while walking, and permit exactly one bad-anchor splice when the good pass stalls.
5. **Emission**: only at the end does the point sequence become stitches. `segmentize(max_stitch_len)` divides evenly — never greedy max-length stepping, which leaves a runt final sub-stitch.

**Stage 7 integration:** one `StitchRun` per connected component, `kind=FILL`. Components are real — necks and holes fragment a tiling. Order components by proximity and connect with **our existing edge-walk travel**, which is already needle-down and containment-safe. Ink/Stitch reaches for `nx.shortest_path` plus boundary-aware connectors here; `travel_path` dominates both. **This is the piece we do not have to build.**

### 2.3 Parameters

| Expose | Pin |
|---|---|
| `motif_id`, `motif_2_id` (Wilcom Motif 1 / 2, alternating rows) | `MOTIF_COVERAGE_PCT = 50.0` (Ink/Stitch's documented default) |
| `motif_scale`, `motif_width_scale` (Embird separates isotropic from x-only) | `MOTIF_MIN_FRAGMENT_MM = 2.0` |
| `motif_col_spacing_mm` / `_row_spacing_mm` (default = motif dims → seamless) | `MOTIF_COVERAGE_EPS = 1e-4` (makes a 100 % threshold reachable) |
| `motif_row_offset_mm` (0.00 = perpendicular grid; `col/2` = brick) | `MOTIF_EXPAND_WHOLE_ONLY_MM = 0.2` |
| `motif_angle_deg` — **overrides** the digitized stitch angle, per Wilcom | |
| `motif_boundary_mode = whole_only \| clip \| clip_and_repair` | |
| `align_grid_to`, `grid_offset_x/y_mm` | |
| `motif_repeats` (bean-style thickening; `nb_repeats = count // 2`) | |

**Boundary policy gets three modes, not one.** Wilcom clips ("Clip to fit shape"); Ink/Stitch accepts or rejects whole cells and calls the result "a pixelated pattern," recommending a 0.2 mm expand to cover the resulting edge gaps. Both are correct for different motifs. Our "no stitch outside the shape" invariant makes `clip_and_repair` the honest default: clip, **drop every fragment below `MOTIF_MIN_FRAGMENT_MM`**, re-splice survivors as open chains in a second pass. Without the drop you get one- and two-stitch orphans along every boundary, each needing travel in and out — the dominant defect in naive motif fills.

### 2.4 Failure modes and guards

| # | Failure | Instrument | Guard |
|---|---|---|---|
| M1 | Scaled motif legs fall under 1.0 mm | Precompute `min_leg_unit` per motif; report the legal scale range | `scale_min = MIN_STITCH_MM / min_leg_unit`. **Validate at parameter time and clamp or refuse** — do not emit and rely on the collapse pass, which destroys the motif's shape while leaving it nominally valid |
| M2 | Legs over 12.1 mm on large scales | leg-length histogram | even subdivision, `ceil(L/max)` equal parts |
| M3 | Boundary orphans | count of fragments below threshold, per shape | `clip_and_repair` drop + count → `MOTIF_FRAGMENTS_DROPPED` |
| M4 | Exposed tie on an open fill | Motif fills are frequently the *only* layer and Wilcom's authoring procedure disables underlay on motifs — so a 3-leg `TIE_STITCHES` lock at `TIE_STITCH_MM` has nothing to bury into | Place component start under the first motif's own geometry. This is the one place a new emitter legitimately constrains where stage 7's tie lands, and it does so by choosing `points[0]`, not by emitting a tie |
| M5 | Float-equality anchor mismatch | assert every splice resolves to a key already in the graph | integer lattice keys (§2.2) |
| M6 | Containment after collapse | census *after* the collapse pass, not before — collapsing merges points and can move one across a boundary the pre-collapse sequence respected | hard assert |
| M7 | Density illegible | coverage-unit map (Law 27) — motif fills are low-coverage by nature | `motif_repeats` is the right lever for weight, **not** tighter row spacing, which destroys the motif's legibility |

### 2.5 Test plan

Tier A: golden test that `pattern = [[0], [0.25], [0.5], [0.75]]` reproduces today's 4-stagger **byte-identically**. That is a real gate, not a hope — the tables are mathematically the same object.

Tier B fixtures: square (baseline lattice), annulus (hole fragments the tiling), 8 mm-wide bar (component fragmentation), letter "O" at 20 mm, two abutting squares with identical params (assert `align_grid_to=global` makes the lattices continuous across the seam — this is the test that catches the day-one-or-never decision), and a 3 mm neck (assert components split cleanly and edge-walk connects them without a trim).

Measure: leg-length histogram vs [1.0, 12.1]; zero-length junction count (should equal motif-count − components); travel length as a fraction of total; containment; trims per 1k against the corpus band (≤ 4.1).

### 2.6 Effort and payoff

**Tier A: 1.5–2 days**, ~200 LOC, mostly in `stage6_fill.py` — highest value per line in this document. **Tier B: 6–8 days**, ~700 LOC + a motif library format + 3–5 shipped motifs. **Tier C: 1 day** on top of B.

**Payoff:** Tier A gives texture variety on every existing fill for almost nothing. Tier B is the first thing in EMB-Bot that looks *decorative* rather than *reproductive* — candlewick, wicker, chevrons, two-part interlocking pairs. It also unlocks low-stitch-count fills, which is a direct cost lever: Wilcom positions Offset Fill as "best used for open fills with low stitch counts," and the same is true here.

---

## 3. Gradient & crossfade fill

### 3.1 Chosen algorithm

Two features, kept separate:

**(a) Single-colour density ramp** — Wilcom **Accordion Spacing**, Hatch **Gradient Fill**, Ink/Stitch **end row spacing**. Row spacing varies along the ramp axis.

**(b) Two-to-five-colour crossfade** — Wilcom/Hatch **Colour Blending**, Ink/Stitch **Linear Gradient Fill**. Which rows belong to which colour varies; spacing does not.

The algorithm for (a) is **phase / inverse-CDF row placement**, not the accumulator every implementation uses. Define line density `d(t) = 1/s(t)` in rows/mm and phase `Φ(t) = ∫d`; place row *i* at `t_i = Φ⁻¹(i + ½)`.

Ink/Stitch's actual code is forward Euler on `dy/di = s(y)`:

```python
current_row_y += row_spacing + (end_row_spacing - row_spacing) * ((current_row_y - start) / height)
```

Three consequences, all [D] and all checkable in a spreadsheet: the realized profile is **exponential, not linear in row index** (`s_i = s₀·e^{ki}`); Euler under-integrates, so a steep ramp (0.35 → 2.00 mm over 20 mm) lands the last rows **6.6 % dense**; and it silently voids Ink/Stitch's own cross-region alignment, since row positions are no longer multiples of anything. **We have the same latent bug in a different form** — `_row_spans` anchors to each shape's own bbox (`y = miny + row_mm * (i + 0.5)`), so abutting regions never aligned in the first place. Tolerable at constant density. Fatal for a blend group, where every shade must sit on one lattice.

Inverse-CDF has no accumulation error, gives `N` in closed form before any geometry exists (preflight gets exact stitch counts), makes coverage exactly `C(t) = w·d(t)`, and **reduces to the current formula identically at constant spacing** — `d = 1/p` gives `t_i = t_min + p(i+½)`, byte-for-byte. Goldens survive.

For (b), the algorithm is a **shared lattice plus a largest-remainder assignment scheduler**. Generate *one* row set at pitch `p` and assign each row a colour by running-error:

```python
acc += alpha(t); c = argmax(acc); acc[c] -= 1.0
```

This is the highest-averages method — same family as Bresenham and Euclidean rhythms. Over any prefix, `|count_c(n) − Σα_c| < 1`, and same-colour runs are as short as the weights allow. **It reproduces the published hand-digitizer recipe exactly**: at α = (2/3, 1/3) on a 0.40 lattice it emits colour A on two of every three rows and B on one of three, which is the mrxstitch "three passes at 1.2 mm, two orange offset by 0.4, one red" strip verbatim ([mrxstitch.com/density](https://www.mrxstitch.com/density/)). The scheduler *is* the craft method, generalized to continuous weights — which is the whole point, because the craft method steps between 2/3, 1/2 and 1/3 and therefore bands, whereas the scheduler interpolates and does not.

### 3.2 Emitter architecture

Two surgical changes and one new module.

**`stage6_fill.py`, one function:**
```
row_positions(t_min, t_max, density_fn, samples=4000) -> np.ndarray   # monotone Φ⁻¹
```
`_row_spans` swaps `y = miny + row_mm*(i+0.5)` for a lookup into that array. **Everything downstream is already spacing-agnostic**: `_columns` tests `ri == prev_row_idx + 1`, purely index-based; `_row_points` staggers on row index, immune to the ramp. The docstring comment about rows being "a millimetre apart" goes stale but the logic holds.

**`stage6_blend.py` (new)** takes the full lattice, runs the scheduler, and returns per-colour row subsequences **with the column structure inherited from the full-lattice pass**. This is the integration warning: `_columns` must be generalized to "the next row belonging to this colour" — a colour holding 1-in-3 rows has index gaps of 3. Do *not* re-run `_columns` on the per-colour subset.

### 3.3 Why the shared lattice, not per-colour generation

Three guarantees by construction: coverage exactly conserved (every lattice slot filled exactly once); **no two colours' penetrations can collide** — minimum separation is `p`, which independently satisfies Law 17's same-hole radius; and stitch count equals a plain single-colour fill of the same region. Independently generated per-colour rows can land arbitrarily close: needle into a previous hole, thread pile, deflection.

Only reason to generate independently is a per-shade stitch angle. Then enforce `|t_a − t_b| ≥ 0.5p` and nudge violators by ≤ ±0.15p.

### 3.4 The one place stage 7 changes — and it changes at stage 5

A crossfade region emits **K `StitchBlock`s**, one per thread. That breaks Part 0's rule 5. The fix is not in `sequence()`:

- **Stage 5 emits K `PlannedRegion`s** sharing one outline, one `blend_group` id, and consecutive `sew_index`. Stage 7 then sees K ordinary regions and needs only one new rule: **keep a blend group adjacent in sew order** — which is Law 25's time-adjacency argument applied to shades instead of fills-and-borders.
- **Stage 5's `overlap_mm = 0.25` underlap must NOT be applied between blend shades.** They interleave on one outline; they do not abut. Per-colour underlap creeps every shade outward.
- **Pull compensation is applied once to the shared outline**, not K times, for the same reason.
- **Underlay forced off or edge-run only** inside gradient regions. Wilcom and Hatch both say so in their own docs; the craft version is blunt — a travel run or standard underlay under an open fill "will look like a mistake, not a texture." Wire this to `PipelineConfig.underlay_style`, overriding the fabric preset.
- **Travel routed through the dense end of the ramp.** `TRAVEL_INSET_MM = 0.6` is sized to hide under 0.4 mm coverage; under 1.5 mm rows it shows. Raise to `local_spacing + 0.6` or route dense. This is the concrete form of Hatch's "Travel on Edge" and Wilcom's Trapunto advice.

### 3.5 Parameters

| Expose | Pin |
|---|---|
| `fill_density_profile = constant \| linear_density \| linear_spacing \| u_shape \| n_shape \| field` (default `constant`; recommended non-trivial default `linear_density`) | `GRADIENT_ROW_MIN_MM = 0.35` (existing floor) |
| `fill_row_open_mm` (open-end pitch, 0.45–2.00) | `GRADIENT_ROW_MAX_MM = 2.00` [S — sew-out-gated] |
| `gradient_origin_mm` / `_end_mm` / `_axis_deg` — **Φ anchor, shared per blend group** | `GRADIENT_OPEN_STITCH_MM = 2.5` (shorten runs where local spacing > 1.0 mm so open rows do not float) [D] |
| `blend_shades: list[str]`, `blend_stops: list[float]` | `THREAD_COVERAGE_MM = 0.40` — Law 16's number, **calibrate by sew-out, not geometry** (40 wt solid-equivalent diameter is ≈ 0.152 mm; the 2.6× gap is multifilament spread and loft) |
| `blend_pitch_mm` (shared lattice, default 0.40) | `BLEND_ALPHA_MIN = 0.20` = `pitch / GRADIENT_ROW_MAX_MM` |
| `blend_conserve: bool = True` — `False` (solid ground + overlay, up to 2× coverage) must raise a density warning | `BLEND_MIN_ROWS_PER_COLUMN = 3` |
| `row_dither_mm = 0.05`, `min_angle_off_axis_deg = 2.0` | |

Why `α_min = 0.20`: a colour whose local share gives `p/α > 2.00 mm` contributes isolated rows that read as stray lines and costs a trim plus a colour block for near-zero gain. Consequence: **at most 5 shades can meaningfully coexist at any point, 3–4 practically** — which is where the photo plan's "3–5 chart shades" landed independently.

### 3.6 Failure modes and guards

| # | Failure | Instrument | Guard |
|---|---|---|---|
| G1 | Piecewise-constant banding | FFT the realized spacing sequence | **Never quantize `s` or `d`.** Quantize only final positions, only at export |
| G2 | Accumulator drift | compare realized `t_i` against the closed form | inverse-CDF, never `y += s(y)` |
| G3 | **Export-lattice collapse at 0°/90°** | `export.py` does `int(round(pt*10))`. At exactly axis-aligned angles every point in a row shares a quantized normal, so a 0.40→0.80 ramp realizes only {0.4,0.5,0.6,0.7,0.8} in Bresenham-periodic runs — period-2/3 structure at ~1 cycle/mm, plainly visible. **And we default to per-region principal axis, so rectangles, bars and text hit 0°/90° constantly.** | `row_dither_mm = 0.05` (one full LSB, decorrelates quantization error from the signal), auto-on when `|angle mod 90| < 2°`. Prefer dither over rotating the angle — it doesn't change the design's look |
| G4 | Twill grain rotates across the ramp | slope = `stitch_mm / (S·s(t))`: at S=4, 4 mm stitch, s 0.4→1.2 the slope goes 2.5 → 0.83 | Either accept (reads as texture gradient) or hold twill constant via `stitch_mm(t) = S·s(t)·tanφ` clamped to [2.0, 5.0]. Also adopt **fractional staggers** — Ink/Stitch documents that fractional values show less visible diagonal, and a drifting twill at integer S is where diagonals show worst |
| G5 | Last-row edge stripe | `Φ_total` fractional part | `N = round(Φ_total)`, rows at `(i+½)·Φ_total/N`. Spreads the error uniformly (< 1 % for N > 50) instead of dumping a 4× dense stripe or a 1.4× gap on one edge |
| G6 | Coverage bulge from mirrored spacing (Law 41) | `Σ w/s_c(t)` at 100 sample points | assert within [0.98, 1.02]·C*. A mirrored-spacing blend fails at +33 % on both ends — this is the test that catches the vendor-recommended bug |
| G7 | Cross-region seam | Φ anchored to shape bbox today | anchor to blend-group origin |

### 3.7 Test plan

1. **Backwards compatibility:** `constant` profile → byte-identical plan. Analytically guaranteed; assert it anyway.
2. **Profile fidelity:** measured spacings match the analytic profile within **0.02 mm** at 100 points.
3. **Coverage conservation:** G6, above.
4. **Even assignment:** every 20-row window has per-colour counts within ±1 of `20·α_c`.
5. **Physics:** `t_i` strictly increasing; min gap ≥ 0.35; max ≤ 2.00; full containment; no two different-colour penetrations closer than 0.5·p.
6. **Anti-banding:** FFT at fill angle exactly 0°, with and without `row_dither_mm`. The difference should be dramatic. This is the numeric gate for G1/G3.
7. **Craft-recipe reproduction:** α = (2/3, 1/3) on a 0.40 lattice must emit the mrxstitch strip-1 pattern. Cheap regression pinning the scheduler to published practice.

### 3.8 Effort and payoff

**Ramp (a): 2.5–3 days** — `row_positions()` is a pure function testable against closed forms with no geometry, plus a one-line swap and the dither. **Crossfade (b): 5–7 days**, most of it in the stage-5 blend-group plumbing and the `_columns` subsequence generalization, not the scheduler (which is nine lines).

**Payoff:** shading. This is the single most requested capability in the gap between "EMB-Bot output" and "a professional digitized logo," and it is the upstream half of the photo-digitizing plan's blend tier — building it here retires that dependency. It is also the only one of the four with an immediate cost story: a conserved blend costs **the same stitches as a plain fill**.

---

## 4. Curved / flow-following fill

### 4.1 Chosen algorithm

**Parametric map (Wilcom's UT transform), not normal-offset level sets.** [US6587745B1](https://patents.google.com/patent/US6587745B1/en), Wilcom Pty Ltd — and it is worth quoting the patent's own strategy because it is exactly our architecture: transform the region into a rectified coordinate space, "use known calculation methods for straight line stitching," transform back.

Two viable architectures, one axis that decides:

| | Row spacing | Penetration lattice | Topology |
|---|---|---|---|
| Normal-offset family | Exact by construction | **Destroyed** — no cross-row correspondence | Fails at cusps/swallowtails |
| **Parametric map (UT)** | Approximate (a few %) | **Preserved exactly** | Safe, given one inequality |

Build the map. It is the only one that keeps monotone columns, exact boustrophedon, and the 4-stagger — the three things our tatami's cleanliness rests on. And it makes curved fill *a coordinate change wrapped around the existing engine* rather than a second engine.

The patent's own key facts: U = arc length along the first guide, T = distance along the line joining the guides' first points; the region is cut into quadrilateral slices with "straight lines closer together where the curvature is greater"; the composite per-quad affine is C⁰ across seams; holes come along for free; stitch length passes through unchanged; and the admissibility condition is stated explicitly — **"it is necessary that the lines defining the sides of the quadrilateral shapes do not cross each other."**

That condition, the offset cusp condition, and the Jacobian sign flip are **the same inequality**: `t·κ = 1`. Parallel-curve theory gives `ds_t = (1 − tκ)ds` and `κ_t = κ/|1 − tκ|`, with a singularity exactly where `t = 1/κ`. So the entire admissibility test collapses to one guardrail: **band half-width on the concave side < min radius of curvature.** In practice `W_concave ≤ 0.8/max(κ⁺)`; if the shape is wider, split the shape — do not stretch the map.

**Ship Florentine (one guide) before Liquid (two).** For a single guide the direction field is the gradient of a distance function — integrable — so exactly uniform spacing is achievable. For two guides the interpolated field is generally not curl-free and uniform spacing is **impossible in principle** (Knöppel et al., SIGGRAPH 2015). *This is why the patent has to admit "a few percent" — it's the two-curve case.* One guide is fundamentally better-conditioned than two.

Explicitly rejected: **Jobard–Lefer streamlines**. Greedy rejection guarantees realized spacing in `[d_sep, 2d_sep]`, not `= d_sep` — at 0.40 mm target that means gaps to 0.80 mm, visible show-through — plus discarded short streamlines leave uncovered slivers and there is zero cross-streamline correspondence, so stagger is impossible. It belongs in a future artistic/texture tier, which is exactly how the academic embroidery work uses it (Liu et al., CGF 2023).

### 4.2 Emitter architecture — `stage6_curved.py`

Seven stages; stage 4 is `stage6_fill.py` called unmodified.

0. **Guide acquisition.** One guide (Florentine) or two (Liquid). Synthesize the second by offsetting far enough to span the shape, as the patent does. Resample to uniform arc length, then **smooth** — `scipy.interpolate.splprep(s=...)` and take derivatives analytically. Curvature enters every guardrail and raw digitized polylines have wild discrete κ.
1. **Curvature audit.** Three admissibility tests, all cheap, all before any geometry: band half-width ≤ 0.8·R_min; `d·κ_max ≤ 0.05`; `L_max = √(8·R_min·tol)`.
2. **Build the map.** Station whenever accumulated turn exceeds ~2–3° *or* arc length exceeds Δs — this implements the patent's curvature-adaptive slicing. **Assert no rung crossings.**
3. **Map the shape.** Split boundary edges at quad crossings, `poly.intersection(quad)` per quad, `shapely.affinity.affine_transform` each piece, union in UT. Holes free.
4. **Run the existing tatami engine, unchanged, in UT.** `_row_spans`, `_columns`, `_row_points` — horizontal rows, monotone-column decomposition, 4-stagger in *u*, hole-aware.
5. **Row spacing schedule.** Non-uniform `t`: `t_{k+1} = t_k + d/σ_t(t_k)`. Rows stay level sets of `t`, so correspondence, monotonicity and stagger are untouched — only their `t` values become non-uniform. This is the direct analogue of satin's interpolated stations: **for fills you don't add rows, you re-space the stations.**
6. **Map back and re-chop.** Rows keep lattice phase, split any chord over `min(12.1, L_max)`. **Travel discards the lattice and is re-chopped by XY arc length** (Law 43). Clip everything against the inset shape.
7. **Verify in XY, post-hoc.** Do not trust the map — measure the output.

**The critical architectural payoff: decomposition happens in UT, not XY.** Monotone columns, boustrophedon, stagger, holes, edge-walk travel all run unchanged. Curved fill is a wrapper, not a rewrite.

**The one integration risk to check before scoping:** `_columns` must be monotone in *the sweep parameter*, not hard-coded to x. `stage6_fill._fill_paths` already rotates before generating rows, so the sweep direction is parameterized — this looks free, but verify it against `_columns`' actual contiguity test first.

### 4.3 Parameters

| Expose | Pin |
|---|---|
| `curved_guide` (one polyline) / `curved_guide_2` | `CURVED_STITCH_MM = 4.0` — **Wilcom's "4.00 mm or less" is a stretch budget, not taste.** Guide at the concave edge with R = 10 mm, band W = 20 mm → outermost row stretches 3×; 4.0 mm becomes 12.0 mm, just under our 12.1 ceiling. [P advice, [D] derivation] |
| `curved_row_mm` (default 0.42–0.45, **not** 0.40 — see below) | `CURVED_BAND_KAPPA_MAX = 0.8` (band half-width fraction of R_min) |
| `curved_smoothing_s` (spline smoothing) | `CURVED_STAGGER_KAPPA_MAX = 0.05` (`d·κ` ceiling → **min guide radius ≥ 20 × row spacing = 8 mm at 0.40**) |
| `curved_tolerance_mm` (default 0.10, feeds `L ≤ √(8R·tol)`) | `CURVED_STATION_TURN_DEG = 2.5` |

**Why nominal 0.42–0.45 rather than 0.40:** we have only **12.5 % contraction headroom** (0.35/0.40). The patent's "few percent" fits — barely. A −13 % excursion puts us under the floor: thread buildup, needle deflection, breaks (Law 16, Law 29). Run curved fills slightly open, or reject/re-slice when the map's minimum t-scale drops below `0.35/nominal`.

### 4.4 Failure modes and guards

| # | Failure | Instrument | Guard |
|---|---|---|---|
| V1 | Offset cusp / swallowtail | rung-crossing test at map build | cap band at 0.8·R_min; reject and split, don't stretch |
| V2 | Row fragmentation at holes and pinches | count of level-set topology changes | decompose in UT; do **not** `linemerge()` fragments back together in XY |
| V3 | Stitch length > 12.1 (convex stretch) | per-run length histogram | per-row step count `n_i = ⌈L_i/target⌉`, uniform within the row |
| V4 | Stitch length < 1.0 (concave contraction) | same histogram, other tail | same scheme + merge pass |
| V5 | Density drift, both signs | nearest-neighbour row-distance census in **XY**, not UT | non-uniform `t` schedule; hard reject below 0.35 |
| V6 | **Stagger phase slip → fake split line** | phase-vs-row-index plot. At d = 0.40, κ = 0.1/mm the ratio is 4 %/row — 40 % of a stitch drifted across a 40 mm row. At κ = 0.5/mm it is 20 %/row and the lattice is gone in four rows. Random phase is cosmetically survivable; the danger is **transient re-alignment**, where drifting phase periodically passes through 0 mod L and adjacent rows momentarily share a column — producing exactly the artifact stagger exists to suppress | stagger in **u**, never in XY arc length; guardrail `d·κ ≤ 0.05` |
| V7 | Chord bulges outside the shape (Law 42) | containment census on the emitted polyline, not endpoints | `L ≤ √(8R·tol)`; final clip against inset shape |
| V8 | Travel explosion | at R = 10, W = 8 the longest:shortest row ratio is 9× | budget for it; re-chop travel in XY; `report["jumps"]` already instruments it |
| V9 | κ spikes from digitizer noise | curvature histogram of raw vs smoothed guide | compute κ only from the smoothed curve |
| V10 | Guide misses the shape | intersection test | **degrade to constant-angle tatami** — Ink/Stitch's behaviour, and correct. Don't error |

### 4.5 Test plan

Fixtures: circular arc band (R = 20, W = 6) — the clean case; tight arc (R = 6, W = 4) — trips V6's guardrail, assert the fallback fires; leaf/petal with a pointed tip; annulus with a guide on the inner ring; an S-curve guide with an inflection (κ changes sign — the map must not flip); a shape with three holes (patent's own worked case); and a guide that misses the shape entirely (V10).

Measure, all in XY after the inverse map: nearest-neighbour row distance in [0.35, 1.15·d]; every stitch length in [1.0, 12.1]; 100 % containment against the *un-inset* polygon; stagger phase drift per row; travel-length fraction; stitch count vs. flat tatami on the same shape.

### 4.6 Effort and payoff

**8–12 days**, ~900 LOC in `stage6_curved.py`. The map builder and the curvature audit are most of it; the fill call is one line. Dependencies all present and permissive: shapely, numpy, scipy (BSD-3). Liquid (two guides) is +3 days on top and needs honest tolerance reporting because Law 40 says exact spacing is unavailable.

**Payoff:** the highest-visual-impact feature of the four. Curved fills are what make a digitized feather look like a feather rather than a feather-shaped rectangle of tatami. Wilcom sells Florentine and Liquid as headline "Curved Fills" features. It also composes: once the UT map exists, motif fill and gradient fill both run inside it for free, because both are wrappers around the same row generator.

---

## Part 5 — Recommended build order

| # | Technique | Days | Risk | Gate |
|---|---|---|---|---|
| **1** | **Pattern fill (motif Tier A)** — 2-D needle-offset table | 1.5–2 | Very low | **Desk-safe.** Golden: 4-stagger table reproduces today byte-identically |
| **2** | **Density ramp** — `row_positions()` + one-line swap + `row_dither_mm` | 2.5–3 | Low | **Desk-safe for the math**, corpus-gated for the open ceiling |
| **3** | **Contour fill Phase 1** — rings, forest, inner-to-outer | 5–7 | Medium | **Corpus-gated**, then desk-safe |
| **4** | **Crossfade** — shared lattice + scheduler + blend groups | 5–7 | Medium-high (touches stage 5) | **Sew-out-gated** |
| **5** | **Motif fill Tier B** — lattice + anchor-splice routing | 6–8 | Medium | **Sew-out-gated on ties** |
| **6** | **Curved fill (Florentine)** — UT map | 8–12 | High | **Sew-out-gated on density headroom** |
| — | *Deferred:* Fermat/CFS, Arachne adaptive spacing, Liquid, motif runs, streamline texture tier | — | — | after 1–6 |

**Why this order and not "biggest payoff first."** Items 1 and 2 are the two that *reduce* risk on everything below them: pattern fill proves the stagger table generalizes, and the density ramp installs `row_positions()`, which crossfade (4) and curved fill (6) both consume. Item 3 is independent of all of them and is the only one that can be built in parallel by a second lane. Item 6 last because it is the only one that can invalidate `_columns`' contiguity contract, and it should land against an engine whose other three fill modes are already golden-tested.

### Evidence gates, by item

**1 — Pattern fill: no new evidence needed.** The 4-stagger is already corpus-validated; a table generalizes it without changing a single physical quantity. Golden test is the whole gate.

**2 — Density ramp: gated on a corpus census, then one new sew-out patch.**
- *Corpus:* run `tools/census_pro.py` over the pro DST corpus for **row-spacing variance within a single fill object**. If professional files show intra-object spacing ramps, we have real target values and the vendor docs' silence stops mattering. Neither Wilcom nor Hatch publishes numeric start/end spacing anywhere — this is the [CNV] gap, and the corpus is the only place to close it.
- *Sew-out:* `GRADIENT_ROW_MAX_MM = 2.00` is craft-blog tier [S]. **New patch for the next card revision: an open-fill ladder, 15 mm squares at 0.40 / 0.70 / 1.00 / 1.40 / 2.00 mm on pique + cutaway.** Question: at what spacing does it stop reading as fill and start reading as stripes, and at what spacing does `TRAVEL_INSET_MM = 0.6` stop hiding travel. Both answers come from one hooping. Note that **block 2 of the existing card (FILL squares at 0.40 / 0.20 / double-pass) already brackets the dense side** — this ladder is its open-side twin.

**3 — Contour fill: corpus-gated on one question, then desk-safe.** Census the corpus for objects whose stitch angle rotates within a single object — that is what a contour fill looks like from the outside. It tells us whether professional shops actually ship contour fills or whether this is a vendor feature nobody uses. The physics is otherwise unchanged from tatami: same 0.40 spacing, same stitch window, same travel. **Phase 3 (Arachne adaptive spacing) is separately sew-out-gated** on the same open-fill ladder as item 2, because it deliberately varies spacing in necks.

**4 — Crossfade: sew-out-gated, and it needs a patch that does not exist yet.** Two constants are load-bearing and neither is measured:
- `THREAD_COVERAGE_MM = 0.40` is Law 16's number and is [P] for *edge-to-edge touching*, but the Murray–Davies tone model uses it as a **coverage width**, and the geometric solid-equivalent diameter of 40 wt is ≈ 0.152 mm [D]. The 2.6× gap is multifilament spread and loft. *Test:* a two-colour interleave ladder at α = (1/2,1/2), (2/3,1/3), (3/4,1/4) on one 0.40 lattice, photographed and colour-sampled. Does the apparent colour match the linear-luminance prediction, or is there dot gain requiring a Yule–Nielsen exponent?
- `BLEND_ALPHA_MIN = 0.20` follows from `GRADIENT_ROW_MAX_MM`, so item 2's ladder settles it.

**5 — Motif Tier B: gated on the one thing the existing card already answers.** Block 1 (LOCK) sews two 14 × 2.2 satin bars with tie offsets 0.8 mm and 0.45 mm, **no underlay**. That is precisely the M4 question: does a 3-leg lock at `TIE_STITCH_MM = 0.8` read as a defect when there is no coverage over it? Motif fills are low-coverage and Wilcom's own authoring procedure disables their underlay, so every component start is a bare tie. **Read block 1 before building the router's start-point selection**, not after. Everything else in Tier B is desk-safe.

**6 — Curved fill: sew-out-gated on the density-headroom question, and blocked behind the axis dispute.**
- *The gating question:* we have 12.5 % contraction headroom and the patent admits "a few percent." Where exactly does contraction start showing as roping? **Block 2 of the existing card is the relevant instrument** — square B at 0.20 mm spacing is a 2× over-density patch, which brackets the failure but does not locate it. *New patch:* a spacing ladder 0.30 / 0.33 / 0.35 / 0.38 / 0.40 mm, five 15 mm squares. That number sets `curved_row_mm`'s nominal and the map's reject threshold, and it is worth having independently — it is the same unverified constant as Law 16's hard floor.
- *The blocker:* per the sew-out card, **the DST axis dispute (`docs/dst-axis-verdict-2026-07-31.md`) gates interpretation of every patch on that hooping.** Our JS bit table is transposed vs pyembroidery/Tajima standard, unresolved. The L-mark patch runs first; everything else on the card is uninterpretable if X/Y are flipped. Curved fill is the most orientation-sensitive feature in this document — a guide curve that sews mirrored is not a subtle defect — so it should not ship on unverified axis convention.

### One instrumentation task that gates all six

Every failure table above assumes a per-run-kind census that does not fully exist yet. Before item 1, extend `tools/census_pro.py` with a single reusable report: **stitch-length histogram, nearest-neighbour penetration distance, row/ring spacing distribution, containment count, and travel fraction — bucketed by `StitchRun.kind`.** That is one instrument, half a day, and it is the acceptance harness for all four techniques and for the sew-out photographs. Per house style: the census comes first, the threshold comes from the census, and the guard comes last. Both charges against Law 17 were dismissed by exactly this method, and the naive fix in either direction would have been damaging.