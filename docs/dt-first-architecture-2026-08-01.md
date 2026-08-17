# The DT-first architecture

*What the expired patents teach EMB-Bot's stages 1–6.*

Synthesized 2026-08-01 from four extraction lenses: the Goldman/SoftSight continuation chain (full text, all 9 US members + the US6397120B1 sibling), Wilcom WO2005061774A1 and its cited predecessors, the Brother/Melco/Pulse families, and a modern-tooling bench pass with measured timings. Engine facts checked against `digitizer/digitizer_core/` on `main`.

Provenance tags: **[P]** primary (patent text, manufacturer doc, peer-reviewed), **[T]** named trade expert, **[D]** our own derivation or measurement, **[U]** unverified. Status tags: **Desk-safe** (lands on evidence we already hold), **Corpus-gated** (needs a number measured off `scratch_corpus/`, 37 pro DSTs), **Sew-out-gated** (needs thread on fabric before it ships).

---

## 0. The thesis in one paragraph

Every serious auto-digitizer in the patent record computes **contour, skeleton, and distance transform as one artifact, before anything decides how a shape is sewn**. Goldman does it literally in a single raster pass; Brother does it by carrying the erosion counter out of the thinning loop; both then route satin-vs-fill off that artifact and nothing else. EMB-Bot computes all three, correctly, in three different places at three different times — and makes the routing decision at `stage7_sequence.py:97` from `2·area/perimeter`, a statistic the 1998 disclosure explicitly warns against, before the distance transform exists. **The gap is ordering, not algorithms.** We already call `medial_axis(return_distance=True)`; we throw the distance array away until after we have already decided we do not need it. Closing that is a refactor with a byte-identical intermediate state, and it unlocks four separate quality wins that are otherwise unreachable.

---

## 1. The canonical DT-first pipeline

### 1.0 Topology

Goldman's FIG. 2 mechanisms and FIG. 4 method 400, with our stage numbers annotated in brackets [P] US6836695B1 / US6804573B2 (identical specification across all 9 family members; SequenceMatcher 0.9986–0.9987 pairwise, so any one member is complete):

```
402  read image                              24-bit colour, 300 dpi assumed   [our stage 1]
404  segmentation (206)                      contrast-gated smooth, region grow, orphan absorb, <6 px cull
406  chain-code + THINNING + DT (208)        ONE PASS. This is the whole architecture.
408  DT evaluation (210)                     max/mu/sigma of DT at SKELETAL pixels -> thick | thin
410  branch
  THICK  412 line fit (212)                  triangular filter, fixed vertices, origin tie-break
         414 stitch angle (214)              16 candidate angles, argmin(fragment count)
         416 fragment gen (216)              modified scan-line, maximal single-operation regions
         418 path gen (218)                  recursive FROM THE EXIT fragment backwards
  THIN   422 line fit + skeleton topology (212/222)   branches as segments, node degree stored
         424 labelling (224)                 end-point anchors (m800), junction anchors (m900)
         426 merging (226)                   serif rule, bifurcation/elongation artifact removal
         428 coding (228)                    singularity bridging + stroke normals by least squares
         430 column smoothing (230)          3-normal window; split at <45 deg bends
         432 path gen (232)                  recursive, trim-free guarantee, interruption magnitude
420  output (220)
```

The load-bearing sentence is at 406: the patent says outright that the *specific method* of chain-coding, skeletonization and DT computation "is not fundamentally important." The requirement is that **all three exist together and are available to every downstream mechanism**. That is an architectural claim, not an algorithmic one, and it is exactly what we do not satisfy.

### 1.1 Segmentation (step 404) [P]

1. **Contrast-gated smoothing.** Evaluate a neighbourhood; if high contrast (an edge is present) **do not smooth** — verbatim: *"the distortion of edges (sometimes termed edge dilation) is avoided."* Low-contrast neighbourhoods get a weighted average of surrounding colour values.
2. **Region growing seeded only at points of low contrast**, sequentially. A pixel near a seed joins if its colour is similar to the seed's.
3. **Orphan absorption** into a neighbouring object, scored on **closeness AND colour similarity** jointly. 8-neighbourhood; a neighbour may belong to more than one object.
4. **Noise cull: any object under 6 pixels is deleted** and its pixels reassigned to the nearest larger neighbour.

Brother US5386789A supplies the piece Goldman lacks — automatic background identification [P]. Peripheral band Ψm as the union of four strips of widths `wl, wr, hu, hd`:

```
Psi_m = {(x,y) | 1<=x<=wl, W-wr+1<=x<=W, 1<=y<=hu, H-hd+1<=y<=H}
N_i / N(Psi_m) > K     ->  colour-area i is BACKGROUND      with 0.5 < K < 1
```

Island rescue, so the window inside the sky is not deleted:

```
Psi_m ∩ Phi_i = empty                          -> embroidering portion   (strict)
N(Psi_m ∩ Phi_i) < P  AND  N(Phi_i) < Q        -> embroidering portion   (tolerant)
```

`K` is bounded only. `P`, `Q`, `wl/wr/hu/hd` are undisclosed — free parameters.

### 1.2 The one-pass artifact (step 406) — the core [P]

**Chain coding.** A single raster scan emits closed contours per object: one exterior, zero or more interior. One pixel per contour is the head, stored absolute; every subsequent pixel is one of **8 relative directions** (E, NE, N, NW, W, SW, S, SE).

**Thinning.** The chain codes are the *input* to the thinner — an extension of Kwok, *"A Thinning Algorithm by Contour Generation,"* CACM, November 1988 [P]. Categorize **3-pixel sections** of chain code by consecutive direction differences; emit a new contour section immediately interior; iterate on the newly generated contour; **stop when a generated contour is a single-pixel-wide area at the object centre — that is the skeleton.**

**DT inside the same loop.** The algorithm is extended *"to also efficiently compute the (3,4) distance transform (DT) for each pixel contained within an object **during contour generation**."* Borgefors, *"Distance Transformations in Digital Images,"* CVGIP 34, 1986 [P]. Orthogonal step 3, diagonal 4; 4/3 ≈ 1.333 vs √2 ≈ 1.414. **Normalize by dividing by 3** to get approximate distance-to-boundary in pixels.

The peel iteration index *is* the distance value. That is why it is free.

### 1.3 The classifier (step 408) — the money rule [P]

Statistics over DT values **sampled only at skeletal pixel locations** — not the interior, not the contour: `max`, mean `μ`, standard deviation `σ`. Verbatim:

> "if 2·σ<μ<½·max then the object is considered predominantly regular. Also, if max and μ are less than predefined threshold values the object may also be considered thin."

Predominantly regular AND thin ⇒ **satin, sewn in columns**. Everything else ⇒ **fill, sewn in rows**. Rationale, also verbatim: a regular region shows *"a lack of such deviation [which] signifies that the region represented by the skeleton is of relatively uniform thickness and direction."*

It is a **variance test, not a width test.** Two axes: regularity (`2σ < μ`) and thinness (absolute magnitude against undisclosed thresholds).

And, flagged by the inventor and never claimed by anybody:

> "Although not currently employed here, it may also be possible to compute such statistics for **each skeletal branch** allowing classification to be performed within various regions of a single object."

That sentence is mixed satin/fill inside one shape. It is free, unclaimed, and no shipping product does it.

**Brother's independent restatement** of the same decision, from a different direction and with actual numbers [P]:

- US5563795A: run the linearizer with a **hard erosion-cycle cap (worked example: three)**. If the component fully collapses to one-pixel width inside the cap it is a *stroke* → take the shape-defining line, zigzag along it. If it does not, it is a *region* → discard the skeleton, take the border line, fill. The satin/fill call **is** a thinning-termination test.
- US5740056A supplies thresholds on N = erosion-cycle count, accumulated *"simultaneously with execution of the sequential fine-line processes"*: `1≤N<3` triple/running stitch; `3≤N<5` zigzag at **1.2 mm**; `5≤N` zigzag at **1.8 mm**. Claim 10 makes the **distance transform** the interchangeable alternative source of the same attribute, with **border pixels = 1** and per-component reduction by **max**.

Three companies, two decades apart, same architectural move: **the width metric is a byproduct of the thinning pass, carried forward as a first-class per-component attribute.** Brother's claim 1 even names it: *"shape characteristic amount."*

### 1.4 Line fitting (steps 412/422) [P]

Contour pixel strings become polygons. **Triangular filter** (US9200397B2 cl.1, i.e. Visvalingam-Whyatt): each vertex plus its two neighbouring differential chain-code points forms a triangle; **if the triangle height is below threshold, eliminate the vertex.**

Two rules that exist purely to preserve inter-object connectivity, and are not optional:

1. **Vertex placement toward the edge, never the centre** of the extracted differential chain-code points — *"all connections between adjacent objects would then be lost."*
2. **Fixed vertices** (immune to filtering) planted at the outer edge of contour chain-codes **wherever the touching/adjacent object changes**, so two objects begin sharing a common edge at an anchor.
3. **Deterministic tie-break:** on equal minimum triangle height, remove **the vertex closest to the origin in Cartesian coordinates** — so two objects sharing a boundary remove the same vertices in the same order during independent passes. Result: shared pixel boundary ⇒ shared poly-line boundary ⇒ no gaps between adjacent colour regions.

### 1.5 The thin path — anchors, artifacts, columns [P]

**Method 800, end-point anchors.** Extend the skeletal end node along the entering branch direction; extension length ∝ **local thickness = average DT along the branch end** (so the extension cannot leave the object), and record the **extension angle**. Find the closest edge contour point. Test its bend angle: **a sufficiently sharp convexity — acute, threshold "such as 30 degrees" — means the branch ends at a single sharp point and both anchors collapse to it.** Otherwise check left/right neighbour vertices if they are **not more than twice** the closest vertex's distance. Failing that, search anchor pairs outward, terminating at the max search distance **or after 4 neighbouring vertices per side**; require the vector entering the left vertex and the vector leaving the right vertex to be **in opposite relative directions to the extension angle**; among survivors choose the pair whose connecting vector is **closest to the start angle in direction and closest to local thickness in magnitude**. Also test **non-adjacent pairs separated by exactly one contour vertex**. Fallback: both anchors at the closest contour convexity.

**Method 900, junction anchors.** For each branch at the node, walk out **until the distance from the node equals the node's DT value**; node→that point is the branch angle. Build angle ranges between consecutive branches clockwise — those are the *skeletal concavities*, partitioning the plane into *n* sectors. Search for contour concavities mapping into them within `search distance = DT × 10^(2π − θ)`. Concavity direction = midpoint of angular distance between the two contour segments meeting at the concavity. Match each skeletal concavity to the **closest contour concavity whose direction is nearest the centre of that skeletal concavity's angular range**, and whose relative location falls **inside** the range.

**Artifact removal.** *Bifurcation* — two thick lines crossing at a sharp angle skeletonize to a short segment between two node pairs, not one node. Detection: **when two nodes sharing a skeletal branch map to the same two characteristic edge vertices, merge them** at the midpoint. The patent explicitly rejects the standard method: *"it is insufficient to detect this case by checking for an overlap of local thickness circles as proposed previously in the literature."* Bound `Search Distance = DT × 10^(2π + θ)`; *"The constant value of 10 was chosen empirically."* *Elongation* — if contour anchors **cannot** be found on either side of a branch angle, delete that branch and pull the nodes to its midpoint.

**Merging (426) — the serif rule.** Three conjunctive conditions: (1) a **degree-3 node with two sufficiently short branches terminating at degree-1 nodes**; (2) the **left end anchor of one short branch connects directly to the right end anchor of the other via a single contour line segment**; (3) the junction anchors do **not** form a sharp/acute concavity. Action: delete the two serif branches and **redefine the surviving branch's end anchors to the deleted branches' anchors** — the serif is sewn as part of the column, not as two stubs.

**Coding (428) — stroke normals, and they are not medial-axis rungs.** Edge normals are computed at consecutive contour points **facing inward**. The **first stroke normal is the segment between the left and right anchors at the originating node**; its angle is the stroke angle. Iterate: find the next edge point closest to the previous normal, connect it to an opposite-side point, selecting by a **least-squares minimum between (a) the new stroke segment's angle and the contour normals it connects, and (b) the normal's length measured against the average column width at that point.** Result: *"a stroke normal of minimal length connects two edge points at which the gradient is approximately equal but opposite."* Interpolation between vertices is supported; skipped vertices get **placeholders** matched later, constrained to lie **within the bounds of the normals created before and after them**.

**Column smoothing (430).** Sliding window of **three consecutive normals**: if their centre points fall on a straight line (tolerance **proportional to column thickness**, not a fixed epsilon), and the first and third imply a trend the second does not, **adjust the middle normal's angle, adding a normal if that orphans a contour point.** Endpoints: record the first and last normal's length; adjust subsequent normals within that length for a smooth transition — *"most needed for columns beginning or ending with serifs."* **Sharp-bend split:** detect high discontinuity in the normal sequence; worked example is an uppercase **"N", two locations where lines meet at under 45 degrees**, where continuous stitching gives *"sparseness on one side of the column and bunching/overstitching on the opposite side."* Fix: split into two sewable regions — **the diagonal is extended on both ends and made one satin column; the two verticals are shortened slightly where they meet it.**

**Path generation (432).** Recursive traversal from an entry node; a recursive call completes at a node for a branch **only when all other branches at that node have been traversed**; satin control points are emitted as calls unwind. Loops special-cased (a cursive lowercase "l" is **one stroke**, not an inverted-V plus an oval). **At least one generated path is guaranteed to need no thread cuts.** Then the objective: **interruption magnitude = the combined length of other columns sewn before sewing returns to the interrupted column**; if a large one is detected, re-plan around it; *"The path chosen is the one where the combined magnitude of interruptions is minimal."*

### 1.6 The thick path [P]

- **16 candidate scan angles.** For each, run the fragment generator and store the fragment count. **Choose argmin.** (US8219238B2 cl.1.) A fragment = a maximal area fillable at that angle in a single fill operation, i.e. **without needle repositioning**. Thick objects sew at **one fixed angle throughout**; angle is the free variable, order is constrained.
- **Path is generated backwards from the exit.** The fragment containing the region exit point is examined **first**; recursion runs from there; the exit fragment's control points are emitted **last**.
- Between fragments, **running stitches through the interior**, not trims — they get buried by subsequent fill.
- **Fragment provenance** (US8532810B2 cl.1): each fragment records *how* it was created — that a previous fragment was split, creating a new one connected **at its start edge or start scan-line**. The recursion needs that record; sew order is derived from it.
- **Deadlock:** if ordering is impossible, either introduce a trim, or **fragment further and accept a higher count** — at the cost of material shift and visible gaps at fragment boundaries.

### 1.7 Three transcription defects — guard against all three

| Printed | Problem | What to implement |
|---|---|---|
| `2·σ < μ < ½·max` | As printed this requires `max > 2μ`, a **high-variation** condition, contradicting the surrounding prose ("no significant variation should exist"). For a uniform bar μ≈max, so `μ < ½max` fails and a perfect stroke classifies **thick**. The sibling US6397120B1 restates the same rule with **no max term at all**: *"If the standard deviation is sufficiently low and the average thickness is below a specified threshold, the region may be classified as predominantly regular."* But a bench run on six synthetic shapes found `2σ<μ AND μ>½max` fires True on exactly the four regular shapes and False on the two irregular ones, while the printed form fires False on all six. | Ship `2σ < μ` **AND** `μ > ½·max` **AND** `2·max ≤ satin cap`, with the middle term flagged **[D]** and **ablated** on our fixtures (§3.5). The two extractions disagree on that term and only our own measurement settles it. |
| `Search Distance = DT × 10^(2π ± θ)` | θ in radians ⇒ 10^6.28 ≈ 1.9×10⁶ pixels × DT. Dimensionally impossible as printed. The patent itself says the 10 is empirical and tunable. | Bounded monotone function of θ: `DT · k · (2π ∓ θ)` or `DT · 10^((2π∓θ)/2π)`. Note the two formulas move in **opposite** directions with θ **by design** — concavity search shrinks as branches spread, merge bound grows. |
| "if max and **μ**" vs "max and **σ**" in the thin test | Mirrors disagree. σ is not a width. | Read as `thin ⟸ max < T_max AND μ < T_μ`. |

### 1.8 Constants, complete

| Constant | Value | Step |
|---|---|---|
| Input assumption | 24-bit colour, 300 dpi | 402 |
| Noise object cull | **< 6 pixels** | 404 |
| Background band test | `N_i/N(Ψm) > K`, **0.5 < K < 1** | Brother 5386789 |
| Chamfer weights / normalization | **(3,4)** / **÷3** | 406 |
| Chain-code directions | **8** | 406 |
| Kwok categorization window | **3 pixels** | 406 |
| Regularity rule | **`2σ < μ < ½·max`** at skeletal pixels (see §1.7) | 408 |
| Erosion-cycle cap (Brother alternative) | **3 cycles** | US5563795A |
| Erosion-count stitch bands (Brother) | N<3 triple; 3≤N<5 zigzag 1.2 mm; N≥5 zigzag 1.8 mm | US5740056A |
| Poly-line vertex cull | triangle height < threshold | 412/422 |
| Tie-break on equal height | **vertex closest to the origin** | 412/422 |
| Candidate scan angles | **16** (11.25° granularity) | 414 |
| Skeletal end extension | ∝ **avg DT along branch end** | 802 |
| Sharp-convexity threshold | acute, **< ~30°** | 806 |
| Neighbour-vertex proximity | **≤ 2×** closest vertex distance | 806 |
| Anchor-pair search cap | **≤ 4** vertices per side | 808 |
| Non-adjacent pair test | separated by **exactly 1** vertex | 808 |
| Branch-angle probe distance | exactly the node's **DT value** | 902 |
| Concavity search / merge bound | `DT×10^(2π−θ)` / `DT×10^(2π+θ)` (see §1.7) | 904 / 426 |
| Serif rule | degree-**3** node, two short branches at degree-**1** nodes | 426 |
| Column smoothing window | **3** normals; straightness tol ∝ **column thickness** | 430 |
| Column split bend | **< 45°** | 430 |
| Branch-point skeleton spurs | delete path 180° reversed from predecessor; counters 3 orthogonal / 5 diagonal | Brother 6192292 |

### 1.9 The 2026 substitutions — measured, not assumed [D]

| 1998 choice | 2026 replacement | Why |
|---|---|---|
| (3,4) chamfer DT | `scipy.ndimage.distance_transform_edt` (**exact**) | Measured chamfer error on a 340 px disc: **max +5.41 %, RMS 3.11 %, max abs 9.10 px = 0.91 mm at 10 px/mm**. Borgefors' worst case for the 3×3 (3,4) mask is **8.09 %**. That is larger than a whole stitch and larger than the satin/fill decision margin. Cost of exact: **22.9 ms** at 600×600, **382 ms** at 2000×2000. A hand-rolled chamfer in Python is orders of magnitude *slower*. **Never ship chamfer.** |
| Kwok one-pass thinning | `skimage.morphology.medial_axis(return_distance=True)` | Returns skeleton **and** DT co-registered on one grid from one call — the 1998 architectural requirement, satisfied by a library function. Measured 139 ms at 600×600, 1 632 ms at 2000×2000; **beats `skeletonize` at large sizes** (4 456 ms) and annihilates `thin` (Guo-Hall, **114 s**, a non-starter). `rng` must be seeded or skeletons are not reproducible. |
| Fixed-length spur pruning | **Attali/Montanari significance**: keep a branch iff its length exceeds the DT radius at its attachment point | Scale-free — compares a length to the *local* radius, no tuned λ. Measured on a 6×30 mm bar with a 1×4 mm boundary bump: spur 1.54 mm vs r_attach 30.0 px → PRUNE; the two real spine halves (6.60 mm, 22.64 mm) → KEEP. Alternative λ-medial axis (Chazal & Lieutier 2005) needs a global λ that "does not respect different scales apparent in the object." |
| Contrast-gated smoothing prose | `cv2.edgePreservingFilter(flags=RECURS_FILTER, sigma_s≈20–40, sigma_r≈0.1–0.2)` | Gastal & Oliveira domain transform, in the **main** `photo` module (verified present on our cv2 5.0.0, which is main-modules-only — no `ximgproc`). **`sigma_r` *is* Goldman's contrast gate**: differences above it are edges and are not averaged across. 689 ms at 1200²; `NORMCONV_FILTER` is 3× slower; `pyrMeanShiftFiltering` is 6.3 s **and does its own segmentation that fights k-means — avoid.** Guided filter (He/Sun/Tang) is ~12 lines on `cv2.boxFilter` if we want `eps = (contrast_threshold/255)²` as a continuous gate. |
| Integer-grid contours | **≥1 mm chords for any tangent/normal** | Measured on a perfect r=100 px circle: `cv2.findContours` perimeter **+4.8 %** over truth; tangent wobble **13.18°/step at 2 px chords, 9.27° at 3 px, 5.02° at 5 px, 2.63° at 10 px**, against a true turn of 0.57°/step. Goldman's least-squares rail pairing and 3-normal smoother exist substantially to suppress noise we can delete at the source. `skimage.measure.find_contours` gives free subpixel but returns (row,col) floats, opposite winding, and **no `RETR_CCOMP` hole topology** — that is the real migration cost. |

Licences across the stack: numpy/scipy/scikit-image/skan BSD-3, OpenCV Apache-2.0. All commercial-safe.

---

## 2. The migration map

Rules of the road, stated once:

- **The kmeans golden is `digitizer/tests/conftest.py::EXPECTED_THREADS`** — five thread numbers and names the fixture logo must resolve to, plus `test_stages.py::test_quantize_finds_the_real_colors_and_no_antialias_phantoms`. Nothing in this document touches stage 2. If a step moves those, it is wrong.
- **The DST byte pins are codec-level** (`test/dst.test.js`, records `0x00,0x00,0x03` etc., 512-byte header, `0x00,0x00,0xF3` terminator). Geometry changes cannot move them. That is the point of pinning at the codec.
- **The determinism pins are the ones at risk from every step here**: `test_pipeline.py::test_two_runs_of_the_same_input_are_identical`, `test_stages.py::test_quantize_is_deterministic`, `test_satin.py::test_same_shape_twice_gives_identical_stitches`, `test_planning.py::test_planning_the_same_regions_twice_gives_the_same_file`. Every new array must be seeded or derived.
- **Instruments are not tests.** Precedent: `tools/shape_lens.py` (its `width` section already measures "mean ribbon width vs true min/max width; the pinch blind spot" — that section is the ancestor of everything in §3). Extend it; don't build parallel tooling.

| Step | Gap | Stage touched | Moves goldens? | Effort |
|---|---|---|---|---|
| M0 | — | instrument only | **No** | 0.5 d |
| M1 | G10 | new `shapefield.py`, stage 4/6 | **No — byte-identical required** | 2–3 d |
| M2 | G1 | `stage6_satin`, `stage7_sequence` | **No — flag defaults off** | 2 d |
| M3 | G1 | flip the default | **YES. LOUDLY.** | 1 d + corpus |
| M4 | — | `stage6_satin._prune_spurs` | **Yes, small** | 1 d |
| M5 | G12 | `stage4_vectorize` | **Yes, small; makes `overlap_mm` honest** | 2 d |
| M6 | G2 | `stage6_satin`, `stage7_sequence` | **YES — new shape class** | 3–4 d |
| M7 | G3 | `stage6_fill` | **YES — every fill angle** | 2–3 d |
| M8 | G17/G16 | `stage6_satin` | Yes, letterforms only | 2 d |

---

### M0 — Measure before touching anything. **Desk-safe.**

**What changes.** Nothing in the engine. Add a `dt` section to `digitizer/tools/shape_lens.py` that, for every region of `logo_whitebg.png` and every fixture in `test_satin.py` (`BAR`, `O_RING`, `C_STROKE`, `T_SHAPE`, `BLOB`), prints one row:

```
shape  area/P_width_mm  dt_max_mm  dt_mu  dt_sigma  dt_median  dt_p10
       2sigma<mu?  mu>max/2?  trim0/trim3/trim8/trimR sigma  current_call  dt_call  AGREE?
```

Same for each connected component of each `scratch_corpus/` DST rendered to a mask (37 files).

**Which existing tests protect it.** None needed — no engine code changes. Run the full `pytest digitizer/tests` before and after to prove the diff is tool-only.

**New instrument.** This *is* the instrument. It is the evidence base for M2/M3 and the only honest way to set `T_μ`.

**Golden impact.** None.

---

### M1 — Hoist the field (G10). **Desk-safe. Byte-identical output is a hard requirement.**

**What changes.** New `digitizer_core/shapefield.py` owning one dataclass:

```python
@dataclass(frozen=True)
class ShapeField:
    mask:  np.ndarray   # bool, the pixels the field was computed on
    skel:  np.ndarray   # bool
    dist:  np.ndarray   # float, EXACT EDT in px (not chamfer, not /3)
    scale: float        # px per mm
    ox: float; oy: float
```

built by one function that calls `medial_axis(mask, return_distance=True, rng=0)` once and returns both arrays together. `_WidthField` in `stage6_satin.py` becomes a thin view over `ShapeField` — same `half_at()`, same `dist/scale`, same numbers.

**The non-obvious correction available here [D].** Today `stage6_satin._rasterize` takes an *already-simplified* polygon (`approxPolyDP` at `simplify_tol_mm = 0.2 mm`) and re-rasterizes it at `_RASTER_PX_PER_MM = 6.0`, adapted upward to `max(6.0, 8.0/wall)` and capped at 900 px. The pixel truth was already in hand at stage 3 as `RegionMask.mask`. Vector→raster→vector→raster is three lossy conversions where the patents have zero. **Build `ShapeField` from the stage-3 mask** where the mask's own resolution clears the 8-px-across-the-wall bar (`px_per_mm ≥ 4.0` floor means a 2 mm ribbon is 8 px — it usually does), and fall back to polygon rasterization only when it does not.

**Sequencing, so this stays byte-identical:** land the module and the stage-3-sourced construction **behind `cfg.extra["shapefield"] = "raster" | "mask"`, defaulting to `"raster"`** (today's path, same numbers). Prove `"mask"` agreement with the instrument, then flip in M3's window, not before.

**Which existing tests protect it.** All 17 of `test_satin.py` — in particular `test_same_shape_twice_gives_identical_stitches` (determinism through the new seeding path), `test_no_cross_escapes_the_shape` and `test_the_column_reaches_both_caps` (the `half_at()` corridor cap and cap extension both read the field), `test_a_t_is_a_through_bar_plus_a_yielding_stem` and `test_the_stem_tucks_under_the_bar_not_across_it` (`_JUNCTION_TUCK_MM` reads `field.half_at`). Plus `test_pipeline.py::test_two_runs_of_the_same_input_are_identical`.

**New instrument.** `shape_lens.py dt --compare-source` printing per-region `max/μ/σ` from the stage-3 mask against the polygon raster, in mm. Acceptance: **median |Δ| in `dt_max` under 0.05 mm across the fixture logo**; anything above that is a simplification loss we want named, not absorbed.

**Golden impact.** **Zero, by construction.** If any stitch coordinate moves in this step, the step is wrong — revert and find the divergence with the instrument.

---

### M2 — DT classifier, dark-launched (G1). **Corpus-gated.**

**What changes.** Add to `stage6_satin.py`, alongside the existing `is_satin_candidate`, not replacing it:

```python
def satin_verdict_dt(field: ShapeField, satin_max_mm: float) -> Verdict:
    skel = trim_endpoints(field.skel, k=int(round(field.dist[field.skel].max())))
    r = field.dist[skel]                      # exact px, no /3
    mx, mu, sd = r.max(), r.mean(), r.std()
    regular = (2*sd < mu) and (mu > 0.5*mx)   # <- the ablated term, see 3.5
    thin    = (2*mx / field.scale) <= satin_max_mm
    return Verdict(regular=regular, thin=thin, satin=regular and thin,
                   stats=(mx, mu, sd, float(np.median(r))))
```

Routed by `cfg.satin_classifier: str = "ribbon"` in `PipelineConfig`. `stage7_sequence.py:97` gains one branch. Default is unchanged behaviour.

**Endpoint trimming is not optional [D].** Skeleton endpoints sit where DT collapses toward zero and poison both μ and σ. Measured on a perfect constant-width bar, where true σ is 0:

```
trim= 0px  n=430  max=15.00  mu=14.02  sigma=2.91  median=15.00  p10=11.00
trim= 3px  n=418  max=15.00  mu=14.37  sigma=2.11  median=15.00  p10=14.00
trim= 8px  n=398  max=15.00  mu=14.79  sigma=0.93  median=15.00  p10=15.00
trim=15px  n=374  max=15.00  mu=15.00  sigma=0.00  median=15.00  p10=15.00
```

Trimming by `r_max` drives σ from 2.91 to **exactly 0**. Note the median is already correct at zero trim — carry `median` and `p10` in the stats tuple so §3.5 can test the robust variant against the moment variant.

**Which existing tests protect it.** Everything, because nothing changes by default. Add four new tests asserting the **new** function's verdicts on the existing fixtures — `BAR`, `O_RING`, `C_STROKE` satin; `BLOB` fill; and the one the current classifier cannot express: **a tapering wedge** (1 mm → 9 mm over 30 mm), which has a 5 mm mean width and passes today's gate. It must come back irregular.

**New instrument.** `shape_lens.py dt --ab` producing the disagreement table: every region where `ribbon` and `dt` differ, with both stat sets and a rendered PNG pair. Run it over all 37 corpus files.

**Golden impact.** None. Flag defaults off.

---

### M3 — Flip the default. ⚠️ **THIS MOVES GOLDENS. SAY IT IN THE COMMIT MESSAGE.** **Corpus-gated + Sew-out-gated.**

**What moves, precisely.** `cfg.satin_classifier` default `"ribbon"` → `"dt"` reroutes shapes between `satin_shape` and `stitch_shape`. Every downstream number for a rerouted shape changes: stitch count, run count, jump count, thread estimate, and the `SHAPE_TOO_THIN_TO_FILL` / `SHAPE_NOT_STITCHED` warning counts on the review screen. **Any test that pins a count on `logo_whitebg.png` re-pins.** The thread-identity golden (`EXPECTED_THREADS`) does **not** move — routing is downstream of stage 2 — and if it does, something is badly wrong.

**Preconditions before flipping, all three:**
1. The M2 disagreement table over 37 corpus files shows **no case where `dt` sends satin to fill on a shape that a pro digitizer satined** (corpus is the referee, not our taste).
2. The `μ > ½·max` ablation (§3.5) is decided on evidence, not on which extraction we read last.
3. A sew-out on the disagreement cases. **A classifier change is the one change on this list that a customer can see from across a room.**

**Which existing tests protect it.** `test_planning.py` in full (the plan must still lock, tie, trim and fit DST records for whatever the new routing produces), `test_adapter.py` axis goldens, `test_satin.py::test_a_shape_whose_skeleton_prunes_away_still_sews_as_fill` (the fall-through at `stage7_sequence.py:106` is the safety net and must keep firing).

**New instrument.** Extend the review-screen stats block with the verdict and its three numbers, so a disagreement is visible without running a tool.

---

### M4 — Significance-based spur pruning. **Desk-safe.**

**What changes.** `_prune_spurs(mask, spur_len_px)` currently uses `max(3.0, half_px * 1.6)` — a **global** mean half-width, so on a shape with mixed thickness the same length threshold is applied to a thin arm's real branch and a thick body's noise twig. Replace with **Attali/Montanari significance**: prune a degree-1 branch iff `branch_length < dist[attachment_node]`. We need no new dependency: `_skeleton_edges` already returns branch pixel lists, and `ShapeField.dist` is now indexable at the attachment pixel. Keep the existing 4-iteration loop (removing one spur exposes another).

Optional cross-check, cheap and independent [P]: Brother's **180°-reversal test** — during outline following, delete a path whose direction is 180° from its predecessor, counters 3 orthogonal / 5 diagonal. That is a differently-shaped detector for the same convex-corner spurs, useful as an instrument even if we do not ship it as a second filter.

**Which existing tests protect it.** `test_satin.py::test_an_o_is_one_closed_loop_not_confetti` (over-pruning shatters the loop), `test_a_t_is_a_through_bar_plus_a_yielding_stem` (under-pruning invents arms), `test_a_degenerate_sliver_reports_empty_never_raises`.

**New instrument.** Branch table per fixture: length mm, `r_attach` mm, verdict, before/after stroke count. Acceptance: **stroke count on `O_RING` stays 1, on `T_SHAPE` stays 2, and the corpus letterform components show a net reduction in strokes with no increase in `report["jumps"]`.**

**Golden impact.** Small and localized — stroke counts on some letterforms change, which changes stitch order within a shape. Re-pin `test_satin` counts if they move; nothing in stages 1–5 is touched.

---

### M5 — Fixed vertices at shared borders (G12). **Desk-safe.**

**What changes.** `stage4_vectorize.py` simplifies each `RegionMask` independently with `approxPolyDP(eps_px)` where `eps_px = max(0.5, 0.2 mm × px_per_mm)`. Two adjacent colour regions therefore simplify their **common** edge separately and can separate by up to 2× tolerance. The patent's fix is two rules: **plant fixed vertices wherever the adjacent object changes**, and **break equal-height ties deterministically**.

Implementation without leaving OpenCV: before simplification, build a one-pixel-dilated adjacency label image from `quant.labels`; walk each contour and mark every pixel where the neighbouring label changes; **split the contour at those marks and `approxPolyDP` each arc separately**, then concatenate. Marked pixels survive by construction, and both regions sharing an arc mark it at the same pixels, so both keep it.

**Which existing tests protect it.** `test_stages.py::test_touching_regions_of_different_colors_stay_separate`, `test_ring_keeps_exactly_one_hole`, `test_all_polygons_are_valid_and_sewable`, `test_pipeline.py::test_shape_ids_survive_a_boundary_change` (shape IDs hash geometry — vertex count changes are exactly what that test exists to catch).

**New instrument.** Max and median gap between adjacent regions' shared boundaries, in mm, before and after, on `logo_whitebg.png` and the corpus. Acceptance: **max shared-border gap under 0.05 mm.**

**Golden impact.** Vertex counts change, so polygon coordinates change slightly and every stitch downstream shifts by sub-tolerance amounts. Determinism tests still pass (they compare two runs). **The honest consequence to state out loud: `cfg.overlap_mm = 0.25` is currently paying partly for this defect.** Do not reduce it in the same commit — measure first, change second, sew-out third.

---

### M6 — Per-branch classification (G2). ⚠️ **MOVES GOLDENS — introduces a shape class we do not currently emit.** **Corpus-gated + Sew-out-gated.**

**What changes.** The unclaimed sentence in §1.3, made real: compute `max/μ/σ` **per skeletal branch** instead of per object, and let one region sew satin in its thin arms and fill in its thick body. We are unusually well-placed for this — `_skeleton_edges` + `_merge_through_junctions` already decompose the skeleton into named branches with node topology, so the per-branch stats are `field.dist[branch_pixels]` and nothing else. **No `skan` dependency required** (contrary to the earlier estimate); `skan` remains the fallback if we want its `branch_type` legend (0 endpoint-endpoint, 1 junction-endpoint = spur candidates, 2 junction-junction, 3 cycle). If we do adopt it: BSD-3, and note two bugs found on 0.13.1 — `Skeleton(sk, source_image=dist)` silently clamps via `img_as_float` (normalize `dist/dist.max()` and multiply back), and `summarize()['mean_pixel_value']` is **not per-branch** in that version.

The hard part is not the statistics, it is the **seam**: where a satin branch meets a filled body, the two need overlap, and stage 5's `overlap_mm` operates between *regions*, not within one. Budget the seam, not the stats.

**Which existing tests protect it.** `test_satin.py::test_report_contract_matches_the_fill_path` (the two paths must stay interchangeable to stage 7 — this becomes load-bearing), `test_planning.py::test_underlay_is_sewn_before_the_fill_it_supports`, `test_no_needle_up_move_is_left_as_a_long_float`.

**New instrument.** Per-branch table on the corpus letterforms and on a deliberately mixed fixture (a lollipop: 18 mm blob + 2 mm tail). Measured today with whole-shape statistics that shape returns `area/P` = 5.84 mm with **no signal that it is heterogeneous**, while its DT returns σ=21.91 against μ=20.73 — **the σ/μ ratio is the "this needs splitting" detector.**

**Golden impact.** New shape class. Every count on any fixture containing a mixed-thickness shape moves. `test_satin` gains fixtures.

---

### M7 — 16-angle fragment minimization (G3). ⚠️ **MOVES EVERY FILL ANGLE.** **Corpus-gated.**

**What changes.** `stage6_fill.principal_angle_deg` is PCA over contour points. Replace with the patent's rule: **for each of 16 angles, run the existing `_row_spans` → `_columns` pipeline and count columns; choose argmin.** We already have the fragmenter — `_columns` *is* the fragment generator, cutting rows into monotone columns exactly as described. This is a 16-iteration wrapper around code we ship today, O(16 × scanline), trivially cheap.

Tie-break must be explicit and deterministic (lowest angle index wins) or `test_two_runs_of_the_same_input_are_identical` will be the test that catches it.

**Which existing tests protect it.** `test_fill.py` in full: `test_principal_angle_follows_the_long_axis` **will fail and must be rewritten** — it pins the old rule by name. `test_nothing_is_sewn_across_a_hole`, `test_row_ends_land_on_the_shape_edge`, `test_penetrations_are_staggered_and_realign_every_fourth_row` all stay valid and are the real safety net.

**New instrument.** Fragment count per region, old angle vs. new, plus total travel length and `report["jumps"]` summed over the design. Acceptance: **strictly fewer columns and strictly less travel on the fixture logo and on ≥80 % of corpus regions.** This is the one step where the objective function is the instrument.

**Golden impact.** Every filled shape's stitch coordinates change. Counts re-pin. Say so.

---

### M8 — The two cheap letterform wins (G17 serif, G16 mitre). **Desk-safe.**

**What changes.** Two rules from §1.5, both narrow:

- **Serif absorption**: the three conjunctive conditions replace our length-only spur prune for the specific case of a degree-3 node with two short degree-1 branches. Crucially, the action is **not** "delete the stubs" — it is **redefine the surviving branch's end anchors to the deleted branches' anchors**, so the column extends out to span the serif tips and the serif is *sewn*, not discarded. Our current prune deletes them.
- **Sharp-bend mitre**: we already split; we split at >90° with **no run-through member**. The patent's reconstruction is asymmetric and specific — **extend the diagonal through and shorten the verticals into it** — and the trigger is **< 45°**, measured on the letter N. Adopt both the angle and the asymmetry.

**Which existing tests protect it.** `test_satin.py::test_a_t_is_a_through_bar_plus_a_yielding_stem` and `test_the_stem_tucks_under_the_bar_not_across_it` — the mitre rule is a principled version of what `_merge_through_junctions`' `dot < -0.5` weld and `_JUNCTION_TUCK_MM = 0.4` approximate today.

**New instrument.** Serif-tip coverage: bare-fabric area within the artwork polygon after stitching, on a serif-font fixture. And for the mitre: cross-angle deviation compared **two apart** along the column (the spray metric), at the bend.

**Golden impact.** Letterform shapes only. Small, visible, and the kind Kent can adjudicate from a sew-out.

---

## 3. The classifier upgrade, side by side

### 3.1 What we compute today

`digitizer/digitizer_core/stage6_satin.py:94-122`, called from `stage7_sequence.py:97`:

```python
ribbon_width_mm(poly) = 2 * poly.area / (exterior.length + sum(interiors.length))

is_satin_candidate(poly, max_width_mm):
    w = ribbon_width_mm(poly)
    if w <= 0 or w > max_width_mm:  return False
    length_est = perimeter / 2.0 - w
    return length_est >= 3.0 * w
```

Two gates: a **mean** width against `SATIN_MAX_WIDTH_MM` (~~3.0 mm in `machine.py` on `main`~~ — **RESOLVED: `main` is 5.0 now, matching what the corpus lane measured off 19 pro lettering files, median 3.4 / max 5.1; confirmed 2026-08-17 at `machine.py:336`**), and an aspect ratio ≥ 3:1 from a half-perimeter length estimate.

Two things about it are **right and worth protecting through the migration**:

- It runs on `p.region.polygon`, the **artwork** geometry, never the stage-5 pull-compensated `p.polygon` — so 0.6 mm of comp on a towel cannot flip the same logo from satin to fill. That invariant is ours, is in no patent or vendor doc read, and must survive M3. The comment at `stage7_sequence.py:93-96` should be copied verbatim onto the new function.
- `test_satin.py::test_ribbon_width_on_a_rectangle` documents the bias direction deliberately: a 24×2 bar reads 1.846 mm because end caps enter the perimeter, i.e. it **never reads wider than truth**, so it cannot sneak a wide shape past the cap. Any replacement must preserve that asymmetry — err narrow, never wide.

### 3.2 What they compute

Three numbers over one array: `max`, `μ`, `σ` of `DT[skeleton]`, per object. Regularity from `2σ < μ`; thinness from absolute magnitude. §1.3.

### 3.3 Where ours fails — measured, six synthetic shapes at 10 px/mm [D]

| shape | truth | `area/P` → implied width | DT@skel max → width | μ | σ | `2σ<μ ∧ μ>max/2` |
|---|---|---|---|---|---|---|
| A 3 mm × 40 mm straight bar | satin | 2.79 mm | **3.00 mm** | 14.02 | 2.91 | regular ✓ |
| B 3 mm curved arc | satin | 2.70 mm | **3.05 mm** | 14.12 | 2.71 | regular ✓ |
| C tapered petal 1→5 mm | satin | 3.07 mm | **5.49 mm** | 15.56 | 6.99 | regular ✓ |
| D 20 mm disc | fill | **9.50 mm** | **20.00 mm** | 99.33 | 0.47 | regular ✓ |
| **E same disc, serrated edge** | fill | **5.03 mm** | **18.62 mm** | 30.50 | 23.63 | **irregular ✗** |
| **F 18 mm blob + 2 mm tail** | split | **5.84 mm** | **18.00 mm** | 20.73 | 21.91 | **irregular ✗** |

Three failure modes, all structural, none tunable:

1. **`area/perimeter` is not a width.** For a long strip of width *w* it converges to *w*/2; for a disc of radius *R* it is *R*/2 = *w*/4. Case D: truth 20 mm, our statistic says 9.50 mm — off by 2.1× purely because the shape is compact rather than elongated. **The same number means different widths depending on elongation**, so no single threshold can be right for both. Our 3:1 aspect gate is a partial patch on exactly this, which is why it exists.
2. **Boundary noise inflates the perimeter and collapses the estimate.** Case E is case D with a serrated edge: area unchanged (31 502 vs 31 397 px), perimeter nearly doubled (1 251 vs 661 px), estimate collapses 9.50 → **5.03 mm**. Under a 5 mm cap, **we satin-stitch a 20 mm disc.** DT still reports 18.62 mm. This is not a synthetic concern — scanned logos, JPEG ringing, and anti-aliased edges after quantize produce precisely this signature, and our own contour perimeter is already **+4.8 % inflated by staircasing before any art noise** (§1.9).
3. **It cannot see mixture.** Case F returns one blended number with no signal that the shape is heterogeneous. DT returns σ ≈ μ, and that ratio *is* the detector. This is M6.

### 3.4 The spec

```python
# stage6_satin.py — replaces is_satin_candidate when cfg.satin_classifier == "dt"
# Field comes from ShapeField (M1), built on the ARTWORK polygon's mask.

skel, dist = field.skel, field.dist                  # medial_axis(rng=0), exact EDT, px
skel = trim_endpoints(skel, k=int(round(dist[skel].max())))
r    = dist[skel]                                    # px; NO /3 — that is chamfer-only
mx, mu, sd, med = r.max(), r.mean(), r.std(), np.median(r)

regular = (2*sd < mu) and (mu > 0.5*mx)              # term 2 is [D], ablate — see 3.5
thin    = (2*mx / field.scale) <= satin_max_width_mm # PHYSICAL: full width vs thread limit

if not regular:            -> fill      (M6: or split at skeleton nodes and recurse)
elif thin:                 -> satin column
else:                      -> fill
```

Three properties worth naming:

- **`thin` becomes a physical test.** `2·max_dt` in mm against the satin cap is "can a cross of this length lie flat," not a tuned proxy. It also inherits the machine-physics ceilings directly: Law 31's satin clamps (**under 1 mm → convert to multi-ply run; over 8 mm → split or fill**) become the same comparison at different constants.
- **Err-narrow is preserved differently.** `area/P` errs narrow through cap accounting; DT errs *exact*, so the safety margin must move into `satin_max_width_mm` explicitly rather than hiding in the statistic. Say that in the docstring or someone will "fix" the cap later and not know what they removed.
- **The aspect-ratio gate can retire.** It exists to catch case D, and `2σ < μ` catches D's family properly. Retiring it is part of M3, not before — and only if the corpus agrees.

### 3.5 What to measure on our own fixtures, and the ablation that decides the open question

**The open question, stated plainly.** The two extractions disagree on whether `μ > ½·max` belongs in the rule. The sibling patent US6397120B1 restates the classifier with **no max term**; the bench run says the term discriminates cleanly on six synthetic shapes. Both cannot be adopted on authority. **Our fixtures decide it.**

Three-arm ablation, run through `shape_lens.py dt --ablate`:

| arm | rule |
|---|---|
| **R1** (sibling-patent reading) | `2σ < μ` AND `μ < T_μ` |
| **R2** (bench reading) | `2σ < μ` AND `μ > ½·max` AND `2·max ≤ cap` |
| **R3** (robust variant) | `med > 2·(p90−p10)` AND `2·max ≤ cap` — moments replaced by order statistics, which the trim table shows are already correct at zero trim |

Evaluate each on three populations:

1. **The unit fixtures** — `BAR`, `O_RING`, `C_STROKE`, `T_SHAPE`, `BLOB`, plus two new ones this exposes: a **tapering wedge** (1→9 mm over 30 mm; today's classifier accepts it, and it is the single clearest case where we are wrong) and a **serrated disc** (case E). Pass condition: all seven correct, all three arms compared on the same table.
2. **`logo_whitebg.png`** — all regions, against the current routing. Any disagreement is inspected by eye against the rendered PNG pair, not adjudicated by count.
3. **`scratch_corpus/` — 37 professional DSTs.** This is the referee. For each stitch region, recover the pro digitizer's own verdict from the stitch data (satin regions have alternating cross structure at ~0.4 mm spacing; fill regions have staggered rows) and score each arm as a binary classifier against it. Report **confusion matrix, not accuracy** — the two error directions cost differently: satin-where-pro-filled is a wide floating cross that snags; fill-where-pro-satined is a lumpy scribble in lettering. **The second is worse.** Weight accordingly and say what weight you used.

**Acceptance thresholds.**
- Zero regressions on the seven unit fixtures for the chosen arm.
- On the corpus, the chosen arm must beat `ribbon` on **both** error directions, not on a blended score.
- `T_μ` (if R1 wins) is set as the corpus's own satin-width distribution boundary, reported with its median and max, exactly as the 5.0 mm figure was derived — **not** picked to make the fixtures pass.
- **Sew-out on the disagreement set before the default flips.** Corpus agreement is necessary and not sufficient; this is the change a customer can see.

---

## 4. WO2005061774A1 as the follow-on

**Status first.** Wilcom International, inventor Alexander John Polden, PCT/AU2004/001804, priority AU 2003907145 (2003-12-22), published 2005-07-07. **No national phase entered anywhere. Never granted. No enforceable claims exist in any jurisdiction.** Free worldwide, and it counts as published prior art against anyone else. Its cited stitch generator US6587745B1 (same inventor, same house — the "known stitch generation algorithms" of its stage 6) is **granted and expired**, as is US5054408A. The whole cluster is free.

Source text is OCR of the WIPO publication and is damaged in places (`ruining`/`ttoning` for "turning", `distane&`, `m imurn`, `Cnon-transversally`); element numbering is internally inconsistent once (a four-branch shape whose branches are listed "301 to 303"). Read formulas from two mirrors before implementing.

### 4.1 What it actually fixes for us

It is **not** an alternative to the DT-first architecture, and it should not be sold as one. It solves a different problem: **decomposition and angle assignment from one scalar field**, where the field's level sets are the fill lines and the field's critical values on the boundary are the cut locations.

```
f(p) = distance(p, L1) / ( distance(p, L1) + distance(p, L2) )
```

`f = 0` on L1, `1` on L2, level sets interpolate straight between two stitch definition lines. **Cut the shape along the level sets whose values are the local maxima and minima of f restricted to the outlines** — equivalently, the level sets that meet the boundary **non-transversally** (touching without crossing).

Four things follow that bear directly on our junction handling:

1. **Angle and decomposition cannot disagree**, because they come from the same object. Today we derive fill angle from PCA (`principal_angle_deg`) and decomposition from monotone row-span connectivity (`_columns`) — two independent constructions that can and do disagree, which is what "letterforms fight the skeleton" means when we say it.
2. **The satin/fill decision moves *after* decomposition.** In this scheme nothing is classified until it is already a simple two-boundary strip, at which point the question is local and well-posed: strip width vs. satin cap. Note this is a genuinely different answer from Goldman's, and the two are not contradictory — Goldman classifies whole objects, Wilcom classifies pieces. **M6 (per-branch) is the midpoint between them**, which is a good reason to do M6 before touching this.
3. **T and X junctions get named handling instead of a tangent-dot weld.** Our `_merge_through_junctions` welds the two arms whose tangents are most anti-aligned (`dot < -0.5`) and tucks the loser 0.4 mm under. Wilcom's answer at a 3-branch vertex is the **tangential cut register**: sample straight cuts through the concave vertex by splitting the vertex angle into **equal angular divisions**, then **add a horizontal, a vertical, and lines parallel to each already-cut boundary** (rationale: some fabrics must or must not be stitched in particular directions; parallel cuts reduce visible discontinuity at the join). Score them; take the highest. It is a **small discrete scoring problem, not a geometry solve.**
4. **The top-ranked criterion is not what we would have guessed.** In order of stated importance: **(1) minimise stitch shortening** — in dense areas it is common practice to shorten a proportion of stitches so they do not run all the way across, and a badly placed cut forces those short stitches to become visible; (2) cut length; (3) proximity to favoured/disfavoured directions; (4) whether the cut coincides with a long boundary. Cut quality is measured by **how few fractional stitches the resulting pieces force**. That is computable on today's output and is very likely a better cut-scoring signal than anything in our sequencer.

For four branches: two **separation classes**, defined stringently — *two cut lines are in the same class iff they intersect the same edges of the sub-shape in the same order* — take one cut per class, and **structurally exclude pairs that cross each other** rather than scoring them down. For N: **N−2 cuts required** (fewer when one cut passes through two vertices), classes computed at every vertex, pairwise compatibility captured in a **graph**, **cliques** found by graph theory, candidate sets take one cut per class of a clique, ranked within class by the evaluation function, conflicts resolved by eliminating the lower-scoring member. **Feasibility is decided before quality, never mixed.** That ordering is worth mirroring regardless of whether we adopt the rest.

Two smaller pieces are adoptable on their own and cost almost nothing:

- **Finite-width cut lines.** Give the cut a band, not a line, explicitly to *"hide very small local variations… common in polygonalised computer graphics shapes"* and absorb round-off. Classify each boundary crossing by which side of the level it entered from and pair entries with exits. This is the same failure our skeleton hits when a serif or a bezier-flattening artefact sprouts a spurious branch — a second, independent tool against the same defect as M4.
- **Sequencing and travel objectives**, directly liftable today: merge adjacent simple pieces into the longest still-simple columns (**fewer segments strictly better**); **extrapolate-then-clip** for overlaps (in that order — extend the segment past its end, then clip against the fill shape); rank travel runs by **length → smoothness → distance from the boundary (further is better) → angle to the cover stitches (larger is better)**. Our travel today follows an inset ring at `TRAVEL_INSET_MM = 0.6`, i.e. it deliberately hugs the *most* visible path available, and criterion (3) says so directly.

### 4.2 Effort and prototype order

Full adoption is **6–8 engineer-days** and it replaces working code, so it is a follow-on to the migration map, not a member of it. **Prototype in this order, in a scratch script, before committing a day of engine work:**

**P1 (half a day).** Compute `f(p)` on one corpus letterform using two `distance_transform_edt` calls against two hand-placed guide lines. Render the level sets over the artwork. The question being answered: **do the level sets look like stitch lines a human would draw?** If they do not on a plain letterform, nothing downstream matters.

**P2 (one day).** Polygonalise the outline, evaluate `f` at boundary vertices, find local extrema, draw the cut lines. Add the finite-width band and count how many extrema it suppresses. The question: **does the cut count come out near what a pro digitizer's segment count is on the same shape?** We have 37 files to check against.

**P3 (one day).** Tangential cut register at one real T junction taken from the corpus: equal angular divisions plus H plus V plus parallels-to-boundaries, scored on stitch-shortening only. Compare the winning cut against what `_merge_through_junctions` produces on the same junction, side by side, rendered. **This is the single frame that decides whether the rest is worth building.**

Do **not** prototype the clique machinery first. It is the most interesting part and the least likely to be the thing that pays.

**One thing to skip entirely:** Wilcom's interface premise. The whole method takes **user-drawn stitch definition lines** as input — the SDLs are the user-facing control surface and cuts are never edited directly. We have no user in that loop at that stage and are not adding one. Where the SDLs come from in an *automatic* pipeline is an unsolved question the patent does not answer, and the honest candidates are the medial axis (which puts us back where we started) or a direction field. **Name that gap when pitching this; do not let it hide.**

---

## 5. What not to adopt, and why

The 1998 disclosure was written for a machine with no float geometry library, no exact-EDT routine, no `shapely`, and a raster scan as the cheapest primitive available. Several of its most distinctive choices are **workarounds for that environment**, not insights, and copying them faithfully would import 1998's constraints into a codebase that does not have them.

**1. The (3,4) chamfer DT, and the ÷3 normalization.** [P] Pure 1998 economics — an exact EDT cost more than a raster pass then. Measured error today: **5.41 % on a disc, 8.09 % worst case per Borgefors**, which at 10 px/mm is 0.9 mm on an 18 mm radius — bigger than a stitch and bigger than the classifier's decision margin. Exact `distance_transform_edt` costs 22.9 ms at 600×600. A hand-rolled chamfer in Python would be **slower and wrong**. Take the exact transform, drop the ÷3 with it (it is chamfer-only bookkeeping), and delete both from the constants table.

**2. Kwok one-pass contour-generation thinning.** [P] The *coupling* is the insight; the *implementation* is a workaround for having only one cheap pass available. `medial_axis(return_distance=True)` delivers the same coupling — skeleton and DT co-registered from one call — for one line. Implementing Kwok's 3-pixel chain-code categorization to get a property a library function already provides is a week spent buying nothing.

**3. Eight-direction chain codes as the contour representation.** [P] They exist because relative 3-bit directions were the compact way to hold a contour in 1998, and because the thinner consumed them directly. We have `cv2.findContours` with `RETR_CCOMP` hierarchy and shapely polygons. What is worth taking from step 406 is the **ordering** (contour, skeleton and DT available together), not the byte format.

**4. "Remove the vertex closest to the origin in Cartesian coordinates" as the tie-break.** [P] The *goal* — two objects independently simplifying a shared boundary must remove the same vertices in the same order — is exactly right and is M5. The *mechanism* is a hack for a world with no shared-geometry representation: distance-to-origin is an arbitrary global ordering that happens to be identical for both objects. With shapely we can do the thing the hack approximates: mark the shared arc once and simplify it once. **Adopt the invariant, not the tie-break.** (Keep *a* deterministic tie-break — just make it one that means something, e.g. contour index — or the determinism tests will find you.)

**5. `10^(2π ± θ)` as printed.** [P] Dimensionally impossible (§1.7). The patent itself says the 10 is empirical. Implement a bounded monotone function and tune. Do not reproduce the formula in a comment as though it were authoritative.

**6. Brother's erosion-cycle count as the width metric.** [P] `1≤N<3 / 3≤N<5 / 5≤N` is a real, disclosed, implementable rule — and it is the **integer-resolution** version of the DT. The patent presents the two as *alternatives* (claim 5 erosion count, claim 10 distance transform) precisely because `max(DT) ≈ half-width ≈ erosion count`. Given that we already get an exact float DT from the same call as the skeleton, adopting an integer proxy with three buckets is a downgrade. **Take the architecture (carry the width attribute out of the thinning pass — that is M1), leave the metric.**

**7. Brother's fixed zigzag widths, 1.2 mm and 1.8 mm.** [P] These are *output* widths for a two-band stitch-type table, not thresholds — a 1994 machine choosing between two preset zigzag widths. Our satin columns take their width from the rails, which is strictly better. The bands are useful only as a sanity check that our width regimes land in the same neighbourhood as a shipped product's.

**8. Melco's continuous-underlay graph traversal.** ⚠️ **US9702070B2 is LIVE — priority 2009-01-16, granted 2017, term to ~2029-2030.** Claim 1 (identify group → create graph with connectors, **center walk edges**, and link-lines → determine sew order from the graph → generate stitches) and claim 5 (**duplicate every edge, Euler-tour the duplicate-line graph**) are enforceable. **Do not implement either as written.** If we want trim-free underlay across a letter group, use a minimal T-join / Chinese-postman duplication over **our own skeleton graph**, which is both a design-around and strictly better (fewer duplicated edges, shorter underlay). The push-compensation *concept* in the same specification (anisotropic shrink/expand) is old, widely disclosed, and not what the claims cover — implement that from the physics, not the text.

**9. Goldman's user-facing singularity database** (US6397120B1's §508/§514: interpretations indexed by CEP count, CEP-polygon eccentricity, and per-CEP aggregate concavity angle, ranked by similarity then by an **application count incremented on user acceptance and decremented on user edit**). [P] Genuinely clever, genuinely useless to us today: it is a learning loop that requires a population of users editing singularities in an interactive tool. We have one user and no such surface. **The extraction metrics themselves are worth keeping in the back pocket** as a feature vector if we ever build junction-type classification — especially the rotation-normalizing orientation vector, and the rule that contour traversal distance when measuring concavity is **proportional to the singularity's thickness** (another instance of "scale everything by the DT," which is the whole document's refrain).

**10. `pyrMeanShiftFiltering` for the contrast-gated smoothing step.** [D] 6.3 s at 1200², **and it performs its own segmentation that will fight our k-means.** If we adopt Goldman's never-average-across-an-edge rule at stage 1, the tool is `cv2.edgePreservingFilter` with `RECURS_FILTER` and a low `sigma_r`, or `bilateralFilter` if sub-50 ms matters. Our current stage-1 denoise (`bilateralFilter(d=5, sigmaColor=30, sigmaSpace=5)`) is already in the right family and nearly a no-op on flat art, which is the intent — the upgrade is real but small, and it is not on the critical path for anything in §2.

**11. Migrating to subpixel contours right now.** [D] `skimage.measure.find_contours` gives free subpixel accuracy, and the tangent-noise numbers in §1.9 are ugly enough to be tempting. But it returns `(row, col)` floats in the opposite winding convention and **provides no hole/parent topology** — we would have to rebuild `RETR_CCOMP` nesting ourselves, and `stage4_vectorize.py` is built on that hierarchy. **The cheap 90 % of the benefit is a one-line discipline: never compute a tangent or normal from adjacent pixel pairs; use ≥10 px chords, or `approxPolyDP` plus one Chaikin pass.** Bank that; revisit the migration only if rail quality after M8 still points at contour quantization.

---

**If only three land:** M1 (hoist the field — zero risk, unlocks everything), M2+M3 (the classifier, the one change a customer sees), M7 (fill angle by fragment count — we already own the fragmenter). M5 is the cheapest honest thing on the list and makes a constant we already ship mean what its comment says.