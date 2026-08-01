# How the masters' machines think

*A teardown of commercial auto-digitizing, from their own patents — and where EMB-Bot actually stands against it.*

Synthesized 2026-08-01 from four research lenses: Wilcom/SoftSight patents, Brother/Melco/Pulse patents, academic literature, open-source internals, and the vendor-documentation parameter census. Engine facts checked against `digitizer/digitizer_core/` at `feat/satin-rails`.

---

## 0. Three corrections before anything else

**0.1 — Wilcom does not own auto-digitizing. Nobody does anymore.**

Wilcom's entire granted software portfolio is two patents: a 1985 stitch processor (US4821662A) and a 1998 curved-line fill (US6587745B1). Both expired. There is no Wilcom patent on auto-digitizing, satin generation from shapes, branching, corner handling, underlay, or pull compensation. Everything ES and Hatch actually do is **trade secret**, not disclosure.

The real auto-digitizing pipeline in the patent record belongs to **David A. Goldman / SoftSight Inc → Vistaprint → Cimpress**, rooted at application 09/134,981 filed **1998-08-17**. Eight patents, one continuation chain, **every member expired ~2018-08-17**. It is a complete classical-CV bitmap→stitches pipeline and it is stage-for-stage isomorphic to ours.

**0.2 — the most sophisticated shape-decomposition document in the corpus was never granted anywhere.**

Wilcom's **WO2005061774A1** ("Turning complex fill stitching", Polden, priority 2003-12-22) ceased at non-entry into national phase — DE withdrawn 2006-06, EPO non-entry 2007-01. Granted in no jurisdiction. Its level-set cut lines and clique-based branch decomposition are free worldwide *and* count as published prior art against anyone else.

**0.3 — the ceiling is lower than we assumed.**

From the vendor parameter census: **commercial auto-digitize turns roughly six knobs, and all six are categorical.** Which colour is fill vs. detail vs. omit; which of three stitch types; outlines on/off; border on/off; colour order; colour-matching method. Every *continuous, geometry-dependent* knob — density, pull comp, underlay type and margin, short-stitch trigger, split length, corner fraction, stagger fractions — comes from an **Auto Fabric preset**: a user-selected global constant, unconditioned by image analysis.

That is the whole game. Their quality ceiling is set by treating geometry-dependent values as global constants. We already condition four of them per shape. **That is the lead, and section 4 is the plan to widen it.**

---

## 1. The canonical pipeline, stage by stage

Reconstructed primarily from US6804573B2 (Goldman, full text), with Brother US5386789A, Pulse US6390005B1/US5809921A, Melco US9702070B2 and the Wilcom/Hatch/Embird documentation filling in what the patents leave out.

Verdicts: **BEHIND** / **PARITY** / **AHEAD**, and they are per-mechanism, not per-stage — several stages are both.

---

### Stage 1 — Segmentation (their step 206)

**What they do.** Classify pixels into contiguous same-colour objects. Smooth selectively: evaluate a neighbourhood, and if it is high-contrast (an edge), **do not smooth** — explicitly to avoid edge dilation. Region-grow seeded only at low-contrast points. Absorb unsegmented orphans into a neighbouring object scored on **both** spatial closeness and colour similarity. **Delete every object smaller than six pixels** and reassign its pixels to the nearest larger neighbour.

Brother US5386789A adds the piece Goldman doesn't have — **automatic background identification**. Define a peripheral band Ψ_m of width wl/wr/hu/hd around the image. Count N_i = effective pixels of colour-area *i* inside Ψ_m. Then `N_i / N(Ψ_m) > K` with `0.5 < K < 1` ⇒ area *i* is background. Island rescue so you don't delete the window inside the sky: reclassify a sub-portion Φ_i as embroiderable if `Ψ_m ∩ Φ_i = ∅`, or if `N(Ψ_m ∩ Φ_i) < P` and `N(Φ_i) < Q`.

**What we do.** `stage1_prep.py` + `stage2_quantize.py` + `stage3_segment.py`. Background by flood fill at `bg_tolerance_lab=6.0` against **per-element convex hulls** (the global hull false-fired on every multi-element logo). Stage 1 measures the background *edge* colour and stage 2 uses it as a virtual blend endpoint so AA halos stop becoming phantom pale threads. Quantization is our own seeded k-means in CIELAB (not `cv2.kmeans` — determinism), clusters merged at CIE76 ≤ 6.0, a 2-pass majority filter on AA, phantom-blend clusters killed at `aa_phantom_edge_frac=0.9`, spool snapping by **CIEDE2000** (CIE76 sent dark navy to a grey thread — measured). `resolve_small_regions` absorbs slivers with `report_absorb_frac=0.25` so "30 details merged" from AA noise doesn't train the user to ignore warnings.

**Verdict: AHEAD on colour, PARITY on background, BEHIND on one primitive.**

- AHEAD: CIEDE2000 snapping and the phantom-blend edge test are strictly better than 1998 8-bit hue bucketing, and better than anything in the Goldman disclosure. The AA-halo work has no counterpart in any patent read.
- PARITY: our hull-flood background is at least as good as Brother's peripheral band, and ΔE-based rather than count-based. Brother's **island rescue test is worth stealing as a cross-check** — it's two formulas and it's the exact failure Hatch still ships (non-transparent background → a stitched white square).
- BEHIND: we do **not** do contrast-gated smoothing. Our denoise is unconditional. Goldman's rule — never average across an edge — is a five-line change to stage 1 and directly protects the vectorize stage from softened corners.

---

### Stage 2 — Chain code, skeleton, distance transform (their step 208)

**What they do.** One raster scan emits closed contour strings **and** computes the **(3,4) chamfer distance transform** for every interior pixel simultaneously, citing Borgefors, *"Distance Transformations in Digital Images"*, CVGIP 34, 1986. Normalise by **dividing the DT by three** to get approximate distance-to-boundary in pixels. The contour generator runs iteratively on its own output — each contour is the peel of the previous — terminating when a contour is one pixel wide, which *is* the skeleton. The patent says outright that the choice of method "is not fundamentally important"; what matters is that contour, skeleton and thickness all exist downstream, from one pass.

**What we do.** We compute them in different places at different times. `stage4_vectorize.py` traces contours to polygons; `stage6_satin.py` rasterizes the polygon back to a mask at ≥8 px across the wall and runs `skimage.medial_axis(rng=0)`.

**Verdict: BEHIND, structurally.** Not on quality — on architecture. We rasterize → vectorize → re-rasterize → skeletonize, and the distance transform only exists inside the satin module, after the satin/fill decision has already been made from polygon area and perimeter. The DT is the single most informative array in the pipeline and we compute it *after* we've already decided we don't need it. Consequences run through stages 3, 6 and 7 (see gaps G1, G2, G10).

`rng=0` on `medial_axis` is non-negotiable and was found by a failing determinism test — unseeded tie-breaking would have shipped.

---

### Stage 3 — Thick vs. thin: the satin/fill decision (their step 210)

This is the money rule and it is worth quoting.

**What they do.** Compute statistics of DT values **at skeletal pixels only**: max, mean μ, standard deviation σ. Then, verbatim from US6804573:

> "if 2·σ < μ < ½·max then the object is considered predominantly regular. Also, if max and μ are less than predefined threshold values the object may also be considered thin."

Predominantly regular + thin ⇒ **satin, sewn in columns**. Everything else ⇒ **fill, sewn in rows**. The rationale, also verbatim: for a regular region "no significant variation … should exist of the associated skeletal pixels' labeled distance transform values … a lack of such deviation signifies that the region represented by the skeleton is of relatively uniform thickness and direction."

It is a **variance test, not a width test.** That distinction is the whole point: it keys on *uniformity of thickness*, which is what actually makes a region satin-able, and it rejects tapering blobs that a max-width test wrongly accepts.

Melco US9702070 takes the pragmatic alternative: assign a temporary top-stitch type, generate temporary stitches, sort by stitch width, take the **70th percentile** of the width distribution as the object's "size" (their stated reason for the 70th and not the median: *err toward more underlay support*), then look that size up in a fabric-keyed chart. Worked example: **satin 0–60 pt, step-fill above 60 pt**, 1 pt = 0.1 mm, so **crossover at 6.0 mm**.

**What we do.** `is_satin_candidate` in `stage6_satin.py`: ribbon width = `2·area/perimeter` ≤ `SATIN_MAX_WIDTH_MM` (5.0, corpus-measured from 19 pro files where lettering runs 3.4 median / 5.1 max) **and** length ≥ 3× width. Run on the **artwork** polygon, never the stage-5 grown one — otherwise 0.6 mm of pull comp on a towel flips the same logo from satin to fill.

**Verdict: BEHIND on the test, AHEAD on the threshold, AHEAD on the invariant.**

- BEHIND: `2·area/perimeter` is a *mean* ribbon width. It is exactly the statistic Goldman warns against. A wedge that runs 1 mm at one end and 9 mm at the other has a 5 mm mean and passes our gate; its DT variance would fail theirs instantly. This is gap **G1** and it is the highest-leverage single change in this document.
- AHEAD: 5.0 mm is measured off 39 professional DSTs. Melco's 6.0 mm is a UI default in a patent example; Wilcom publishes nothing. Our number has provenance.
- AHEAD: classifying on artwork rather than compensated geometry — so a design sews the same structure on every fabric — is not in any patent or vendor doc read. It is ours and it is right.
- **Free and explicitly unclaimed:** Goldman flags but never uses per-skeletal-branch statistics — *"it may also be possible to compute such statistics for each skeletal branch allowing classification to be performed within various regions of a single object."* That is mixed satin/fill inside one shape. Nobody claimed it. Nobody ships it. Gap **G2**.

---

### Stage 4 — Vectorize / line fitting (their step 412)

**What they do.** Reduce differential chain-code points by **triangular filtering**: *"if a triangle height is below a particular threshold value, its associated vertex is eliminated from the poly-line approximation"* (this is Visvalingam-Whyatt; claimed as US9200397 cl.1, expired). Critically, US9200397 cl.4 adds a pre-pass that **plants fixed vertices at the outer edge wherever an adjacent object has changed**, so shared borders of neighbouring colour regions cannot drift apart under simplification.

**What we do.** `stage4_vectorize.py`, Douglas-Peucker via Shapely `simplify` at `simplify_tol_mm=0.2`, plus `match_shape_ids()` geometry carry-forward so shape identity survives a re-digitize (shape IDs used to churn on a 0.95% area change at a log-bucket boundary — removed area from the hash).

**Verdict: PARITY on decimation, BEHIND on registration.**

DP vs. triangular filtering is a wash — DP bounds perpendicular error, VW bounds removed area; for stitch geometry either is fine at 0.2 mm. But we have **no shared-border pinning**. Two adjacent colour regions are simplified independently and their common edge can separate by up to 2× tolerance before stage 5 ever sees it. Stage 5's underlap papers over it at 0.25 mm, which means our underlap constant is partly paying for a vectorize defect. Gap **G12** — cheap, and it makes the underlap number honest.

---

### Stage 5 — Compensation and overlap

**What they do.** Three separate mechanisms, from three companies.

*Pull compensation.* Pulse US5343401A fixes the vocabulary still in use: pull comp is a **percentage over-stitch**, set separately for satin and tatami, and — the part worth copying — **chosen at output time, not at digitizing time**, so a design re-outputs at a different size or density without redrawing. Wilcom's published fabric values: drills/cotton **0.20**, T-shirt **0.35**, fleece/jumper **0.40**, lettering **0.2–0.3 mm**.

*Push compensation.* Melco US9702070's specification (the granted claims are elsewhere — see §5). Physics stated plainly: thread stretches during sewing, so a shape **shrinks perpendicular to the stitch direction and expands parallel to it**. Their calibration: a digitized **1.000″ square with horizontal stitch direction sews out ≈1.1″ tall × 0.95″ wide** — **+10 % along the stitch axis, −5 % across it**. Procedure: measure the width of an element's end (mean of last 5 stitches, or median of last 10); look up a table; **skip entirely if that end intersects another design element** (otherwise the elements separate); also measure the end's height (last 5 stitch lines) and skip below a threshold, which excludes curved and short ends. Exemplary table, verbatim, in points:

| end width | push compensation |
|---|---|
| 0–20 pt (0–2 mm) | −4 pt (−0.4 mm) |
| 20–35 pt | −5 pt (−0.5 mm) |
| 35–50 pt | −6 pt (−0.6 mm) |
| 50+ pt | −7 pt (−0.7 mm) |

*Overlap/knockout.* Pulse US5809921A (expired 2017) resolves layering **without boolean geometry**. Sort carving segments by layer, accumulate covered region U, negate it, then for each fill line enumerate every candidate penetration point by **Bresenham** and ask the region containing that point whether to drop a stitch — with a **most-recently-used region cache** to make the lookup cheap. Overlap areas get *solely* the top pattern; non-overlap gets *solely* the background pattern. One continuous pass, zero stitching on top of stitching.

**What we do.** `stage5_overlap.py`. Sew order first (descending pixel weight — biggest areas first, details last and crisp), then underlap: extend the colour that sews **first** underneath the one that sews after, and forbid the later colour from growing back. `overlap_mm=0.25`. Then pull comp as a **uniform `poly.buffer(pull)`** from the fabric preset. Plus one mechanism nobody else has: the **same-thread fusion corridor** — two shapes of the same thread have no seam logic between them, so eight letter pairs fused and "ENTERPRISES INC." sewed as "ENERPRSES NC"; the fix holds open the lens of bare fabric within one pull of both shapes (buffering both sides at 2× pull carved compensation off frontage out to nearly 4× pull — the lens is one pull per side, queried at two).

**Verdict: AHEAD on ordering and same-thread, BEHIND on both compensation axes, BEHIND on knockout.**

- AHEAD: order-then-grow, with the later colour forbidden from growing back, is the correct construction and it is not in any patent read — Pulse and Melco both compensate geometry without a sew-order interlock. Reverse the two and every seam sits proud.
- AHEAD: the same-thread corridor is genuinely novel as far as this survey goes. Melco's "suppress push comp where ends intersect" is the same *class* of idea on a different axis, which is a good sign we're on a real principle.
- BEHIND: **our pull comp is isotropic.** The stage 5 docstring says so honestly — *"true pull comp acts perpendicular to the stitch direction only, which needs the fill angle and belongs with a later directional-compensation pass."* Every commercial tool is directional. Machine-physics Law 22-24 says the same. Gap **G6**.
- BEHIND: **we have no push compensation at all.** Not a smaller version — none. Ink/Stitch shipped it in v3.3.0 (2026-07-31). Gap **G5**.
- BEHIND: our knockout is geometric (buffer, intersect, subtract) and it has already cost us one tuning cycle (the 2p→p corridor correction). Pulse's per-penetration-point test has no radius to tune and no boolean robustness failures. Gap **G7**.
- Also missing: Wilcom's **negative underlay margin at the joining end**, which lets underlay extend past the cover stitching for smooth column joins. We have `UNDERLAY_INSET_MM=1.0` flat, one value, no per-end control.

---

### Stage 6a — Fill

**What they do.**

*Angle selection by fragment minimization.* US8219238B2 claim 1, expired. A **fragment** is a maximal sub-region fillable at one angle with a single fill operation — **no needle repositioning**. Try **sixteen candidate scan angles**; for each, fully fragment the region and store the count; **choose the angle yielding the fewest fragments.** Stated motivation: *"thread cuts impose a significant sewing time penalty."*

*Fragmentation and travel.* Each fragment is marked with **how it was created** (e.g. split from an existing fragment, joined at its start edge) — that provenance is what makes the recursive path planner work. Each fragment's **mid-line** is computed through the midpoints of its marked left/right vertices, and **the mid-line is the travel path** to the next fragment's entry.

*Path generation.* Entry/exit may be any point on an exterior contour. Traversal is **recursive, starting from the fragment containing the exit point**, emitting control points as calls unwind — it plans backwards from the exit. Between fragments, emit **running stitches inside the region** rather than trims: *"the needle is always down (i.e., leaving a trail of stitching behind it)"*, and the fill covers them later. Dead-end policy, verbatim: *"it may occur that such an ordering is impossible … the algorithm is forced to sew itself into a corner"* — either insert a trim, or **further fragment**. Stated cost of over-fragmenting: material shift and buckling → *"fragments becoming misaligned … causing noticeable spaces within the fill region."*

*Brother's global direction chooser* (US5576968A, verified Expired-Lifetime): pick the end point (lowest point), erect a boundary line through it perpendicular to the embroidering direction, choose the **principal partial region** as the one whose remotest point is farther from that line (variant: greater area), pick the direction optimal for the principal region, apply it to the whole region — so no seam shows at the partial-region boundary.

*Wilcom's curved fill* (US6587745B1, expired 2019): polygonalise the outline; take one or two **stitch definition curves**; build **quadrilateral slices** between them; affine-map each quad **XY → UT** where U = distance along the first SD curve and T = distance along the straight line joining both curves' first points; run **ordinary straight-line complex fill in UT**; map back. Straight lines in UT become curves in XY, spacing in UT ≈ spacing in XY. The load-bearing idea: **curvature is decoupled from the boundary.** Contour-parallel offsets vary density and produce discontinuities; this doesn't, because density is enforced in the flattened space.

*Wilcom's turning complex fill* (WO2005061774A1, never granted): one SD line bounding a sub-shape ⇒ fill lines are parallel copies of it; two or more ⇒ **interpolate the fill lines between the bounding curves**. Decomposition into simple sub-shapes by an **ordered, extensible heuristic bank** — classify the sub-shape, walk the technique list, apply the first suitable one. Technique A: **level sets** of a piecewise-linear function that is constant on each boundary SD line; **cut lines are the level sets at the local minimum and maximum values the function takes on any boundary**, given **finite width** so polygonalisation wiggles don't register as spurious extrema. Technique B, for straight fill: sample candidate cuts at **concave vertices by equal angular divisions of the vertex angle**, classify into **separation classes**, build a compatibility **graph and find cliques**, rank cuts by an evaluation function and **eliminate the lower-scoring cut of each pairwise conflict** until only compatible sets remain. Claim 17: *"the most important criteria is minimising stitch shortening."*

**What we do.** `stage6_fill.py`. Row spans at an angle, cut into **monotone columns** (a fork ends a column) so boustrophedon is exact and every awkward move becomes an explicit travel decision. `FILL_STAGGERS=4`. Angle = `principal_angle_deg` (per-region PCA) unless `fill_angle_deg` forces one. Travel = straight-if-inside → follow an inset ring (`TRAVEL_INSET_MM=0.6`) → needle up, capped at `max(20 mm, 4× direct)` because travel over finished fill shows worse than a trim. `FILL_STITCH_MM=3.0` and `FILL_ROW_MM=0.40`, both corpus-measured.

**Verdict: BEHIND on angle, PARITY on decomposition, BEHIND on travel routing, far BEHIND on curvature.**

- BEHIND, badly: **per-region PCA angle is our biggest measured quality defect and we already know it.** On Kent's benchmark logo, `satin=False` + `fill_angle_deg=45` beat the default because every letter filling at its own PCA angle reads as visible patchwork. Fragment-count minimization over 16 angles fixes this *automatically and per-region*, using the objective that actually matters. Gap **G3**.
- PARITY: monotone columns are a legitimate fragmentation. Ours are angle-aligned rather than provenance-tagged, but the decomposition is equivalent for convex-ish regions. Where it loses is that we don't record how a column was created, so the sequencer can't plan backwards from an exit.
- BEHIND: our travel is a fixed policy (inside → inset ring → lift). Theirs is a **planned path over fragment mid-lines with a re-fragmentation escape hatch**. And Ink/Stitch's weighting (§3) is better than both.
- FAR BEHIND: we have **no curved fill and no direction-field fill**. Every fill is one straight angle. Wilcom's UT-space mapping is expired and free; the turning complex fill is unencumbered worldwide. On any curved emblem this is the visible difference between "machine did this" and "a person did this."

---

### Stage 6b — Satin columns

This is the deepest section of the Goldman disclosure and the most directly reusable.

**What they do.**

*Anchors.* Classify contour vertices: **end-point anchors** at degree-1 skeletal terminals, **junction-point anchors** at concavities where branches meet. Anchors bound the "simple continuous column-like regions" — the *regularities* — that compose a thin object.

*Serif merging, exact three-part rule.* (1) a skeletal node of degree 3 with **two sufficiently short branches terminating at degree-1 nodes**; (2) the left end-point anchor of one branch is **directly connected to the right end-point anchor of the other via a single contour line segment**; (3) the associated junction anchors **do not represent a sharp or acute concavity**. Action: delete the two short serif branches and redefine the surviving branch's endpoint anchors to the left/right endpoint anchors of the eliminated ones. The patent is candid that these are *"static rules, formulated by a human expert."*

*Singularity bridging.* At skeletal junctions, regular regions interfere and their mutual continuity is occluded. Strategy: **match appropriate pairs of regular regions entering the singularity** under energy minimization *"so that joining the two regions does not result in any sharp discontinuity or area of high energy"*, then **reconstruct the occluded boundaries** so the pair sews as one continuous column. Worked example (a crossing): stroke 1010 continues through to 1050 by connecting contour points A→B and D→C; stroke 1020 connects to 1040 with A→D and B→C. **One extended regularity replaces two strokes.** (US7587256B2 claim 1, expired.)

*Rail pairing by least squares.* Compute inward edge normals at consecutive contour points between anchors. The first stroke normal is the segment between the left and right anchors at the originating node; its angle is the stroke angle. Then, verbatim:

> "The next edge point that lies closest to the previous st[r]oke normal is then found by traversing the left and right contours of the stroke. The contour point is then connected to an opposite edge contour point. The coding mechanism calculates for a **least squares minimum between the angle of this newly cr[e]ated stroke segment and the corresponding contour normals it connects**. Included in this least squares computation is also a **measurement of the stroke normal's length proportional to the average column width at that point**. The result is that a stroke normal of minimal length connects two edge points at which **the gradient is approximately equal but opposite**."

Skipped vertices get **placeholders**, matched in a later pass, constrained so their normals lie within the bounds of the normals created before and after them.

*Column smoothing.* Iterative, three consecutive normals at a time. If the three centre points are collinear *"within a small variation proportional to the column's thickness"*, examine the middle normal; if the 1st and 3rd imply a trend the 2nd doesn't, adjust the middle normal's angle and add an extra normal if that orphans a contour point. First and last normals are always examined and adjacent ones adjusted for a smooth end transition — *"most needed when generating columns which begin or end with serifs."*

*Sharp corners, verbatim:*

> "Stitching continuously around such areas of sharpness may produce unfavorable results. This is usually due to **excessive interpolation of associated stitching causing a sparseness on one side of the column and a bunching or overstitching on the opposite side**. To remove this problem, the column smoothing mechanism **breaks the column into two separately sewable regions that meet at the area of sharpness** … the **diagonal line region would be extended on either end** and made into a single column of satin stitches. Subsequently, **the two vertical lines would be shortened slightly** at the area where they meet the diagonal."

Threshold: **45°**. Policy: **one member runs through and is extended; the others butt into it and are shortened.**

*Turning-satin density.* Pulse US6390005B1 (expired 2018-05-14) — the single most transferable piece of geometry in the survey. Prior industry practice was a **fixed inset of 25 % or 33 %**; the patent shows three prior approaches failing, all because one fixed inset cannot serve a shape whose curvature varies. The invention: **hold interstitch distance constant and let the inset float.** Rails are parametric cubics; the spacing metric is the **perpendicular distance from the new end point to the previous stitch's line segment**, reducing to `isd = sqrt(p·x1 + q·y1 + r)`, composed into `isd² + (pa+qe)t³ + (pb+qf)t² + (pc+qg)t + (pd+qh+r)` and **solved directly for t**. Cheap path: degrade to a quadratic or linear in t. Published calibration at density **0.4 mm**:

| stitch length | stitch angle | derived density inset |
|---|---|---|
| 0.40 mm | 30° | **26.8 %** |
| 0.28 mm | 45° | **58.6 %** |
| 0.23 mm | 60° | **100 %** |

**The fixed 25–33 % industry default is only correct near 30°.**

**What we do.** `stage6_satin.py`. Adaptive raster (≥8 px across the wall) → `medial_axis(rng=0)` → crossing-number nodes → spur prune → walk stopping at node neighbours → **weld collinear arms through junctions** (tangent dot < −0.5; T = through-bar plus yielding stem with a 0.4 mm tuck; X = one through-diagonal plus two tucked arms) → per stroke, extend free ends to cap, **rails by ray-cast capped to the local corridor** (floor 0.75× half-width, because the distance transform reads 0 at caps), rail smoothing may only **shorten**, short-stitch guard on curves. `_round_corners` spreads each apex over one column width — a gradual spoke fan — with split demoted to a >90° fallback, **because the corpus says pros sew through corners 1436:18 against splits.** Split satin above 5.0 mm at `k = ceil(W/3.0)`, penetrations staggered on a 4-station wave at ±0.23 segments. Travel between columns is Dijkstra over **unsewn** stroke spines only (travel over finished satin shows).

**Verdict: PARITY on rails, AHEAD on splits and corners, BEHIND on junctions, BEHIND on turning density.**

- PARITY-ish: ray-cast-with-corridor-cap and least-squares normal matching solve the same problem. Ours is cheaper; theirs is better-conditioned. Note the known symptom: the spray defect's remaining suspect is **rail construction** — the 1.6× cap on one side and 0.75× floor on the other tilts the cross when only one side clamps. Goldman's objective (minimal-length normal connecting points where the gradient is equal and opposite) is symmetric by construction and would not tilt. Gap **G11**, medium confidence that it's the fix.
- AHEAD: **split satin with a corpus-fitted stagger wave.** Wilcom publishes only a recommended 7.00 mm min length. We measured the actual crossover across 36 pro files (14 % split at 3.0 mm, 53 % at 5.0, 92 % at 7.0, ~100 % from 7.5) and the stagger phase (offset from mid-cross median 0.117 of the cross, station-to-station shift 0.214) — and the instrument finding that `study_pro.classify` is **blind** to splits is why earlier studies wrongly reported pro wide satin as unsplit.
- AHEAD: our corner policy is **corpus-validated against theirs.** Goldman splits at <45° bends; we spread the apex and only split past 90°, because the corpus counted 1436 through-sewn corners against 18 splits. Their rule is a 1998 human expert's static rule; ours is a census. Keep ours. **But steal their mitre policy for the cases where we do split** — extend one member through, shorten the others — because we currently split without a run-through member.
- BEHIND: **`weld through junctions` is a topology hack; singularity bridging is a geometry solution.** We weld skeleton arms by tangent dot and tuck the losers 0.4 mm. Goldman reconstructs the **occluded boundary** so two crossing strokes sew as complete overlapping columns. The corpus already told us this is right — *"script strokes CROSS as overlapping whole columns (star = 5 crossing strokes)"* — and we recorded it as a finding without acting on it. Three hypotheses were tested and refuted chasing the spray; **this is the untested one.** Gap **G4**.
- BEHIND: our short-stitch guard is a fixed distance trigger (`SATIN_SHORT_STITCH_AT_MM=0.3`) with a fixed pull fraction (0.35) capped at 0.6 mm. Pulse's dynamic inset is the principled version and it comes with published calibration points we can check the corpus against. Also flagged: machine-physics **Law 17 says the needle blade is 0.75 mm and two penetrations within ~0.5 mm share a hole and shred** — our 0.3 mm trigger is *inside* that radius. That is a standing review item and Pulse's formulation is how to close it properly. Gap **G8**.

---

### Stage 6c — Underlay

**What they do.** Melco selects by **size band**: 0–20 pt (0–2 mm) → centre walk; 50–90 pt (5–9 mm) → zigzag primary + edge-walk secondary. Types: centre walk, edge walk, zigzag, fill. Wilcom/Hatch publish the lettering rules explicitly — **letters under 5 mm get no underlay; 6–10 mm get centre-run; over 10 mm get edge-run**; large letters get a second layer, sometimes double-zigzag for loft. Wilcom exposes **three underlay margin fields** on columns (one on complex fill), and a **negative margin at the joining end** so underlay extends past the cover for smooth column joins. Underlay scope is selectable "by segment or by shape."

Melco also builds **continuous underlay across a group** by graph: connectors between every element pair, delete connectors above a threshold, add a **centre-walk edge** per element, join connectors to centre walks with **link-lines**, **duplicate every edge** so every node has even degree, then **Euler tour** the doubled graph. Zero-trim underlay under an entire letter. **This one is live** — see §5.

**What we do.** `SATIN_ZIGZAG_ABOVE_MM=2.5`, empirically confirmed by the phase census (columns with zigzag median 2.71 mm, without 1.33). Fill underlay style from the fabric preset: edge run / lattice / centre run, `UNDERLAY_INSET_MM=1.0`, `UNDERLAY_STITCH_MM=2.5`, `UNDERLAY_ZIGZAG_MM=2.0`, `UNDERLAY_LATTICE_MM=2.5`.

**Verdict: AHEAD on the satin threshold, BEHIND on everything else.**

- AHEAD: our zigzag-above threshold is measured off a phase census that segments each run into layers, because pros chain centre-walk + zigzag + column into **one needle-down run** and per-run labels hide the layers. That instrument does not exist anywhere else in this survey.
- BEHIND: **fill underlay type is a fabric constant, not a size decision.** A 3 mm shape and a 40 mm shape get the same underlay. Melco's size chart is the missing conditioning. Gap **G13**.
- BEHIND: no per-end margins, no negative joining margin, no second layer on large objects, no underlay-by-segment scope.
- BEHIND: no continuous group underlay. Every shape underlays itself and lifts.

---

### Stage 7 — Sequencing

**What they do.** Goldman's satin path generation: several candidate orderings are produced, and *"at least one of these paths is guaranteed to generate embroidery data for the thin object without requiring any thread cuts."* The recursive algorithm takes a start node, traverses skeletal branches emitting run-stitch control points, and **a recursive call at a node completes only when all other branches at that node have been traversed**; the column's satin points are emitted as its call completes. **Loops are special-cased to sew continuously** — a cursive lowercase "l" is one stroke, not "an upside down v stroke with a second connected oval stroke on its top."

And the objective, which is the best-specified sequencing metric in the whole patent record: avoiding thread cuts can force a long column to be interrupted mid-way. **Magnitude of interruption = "the combined length of other columns that are sewn before sewing returns or continues along the initial long column."** If a large interruption is detected, re-plan; *"the computational efficiency of this technique may degrade to the point of computing all possible paths"*; **the chosen path is the one where the combined magnitude of interruptions is minimal.**

**What we do.** `stage7_sequence.py`. Per colour group: rank by bounds, start at the shape **farthest from the group centroid** (nearest-neighbour from the middle strands the far end and pays 42 mm of flight at the finish on eight letters), then greedy nearest-**shape** (distance to the polygon, not to an arbitrary point on it — picking on a start point the shape hadn't chosen yet sent the needle to every shape's top-left corner: 112 mm and nine trims on eight letters). Ties: `TIE_STITCH_MM=0.8` × 3. Jump vs. trim at `TRIM_AT_MM=3.0`. Needle-down links where the hop stays inside the shape.

**Verdict: PARITY on heuristic quality, BEHIND on formulation.**

Our extreme-then-nearest sweep is a good greedy and the two measured fixes behind it are real. But it is a greedy over shapes with no objective function. Goldman's interruption metric names the thing we are actually trying to avoid, and can be *measured* on our output today with no code change to the planner. Corpus benchmark: **trims/1k median 0.8 (range 0.1–4.1)**; ours went 37 → 20 with the travel graph and the benchmark still grades TRIM_HEAVY at 8.1/1k against pro 4.1. Gap **G9**.

---

### Where we are simply not in the game

| Their capability | Source | Us |
|---|---|---|
| Photo → per-pixel angle field, line segments, exposure culling | Brother US8200357B2 (**ACTIVE ~2028**) | Nothing. Per-input-class ceilings documented in `docs/photo-digitizing-plan-2026-07-31.md` |
| Motif / program-split / patterned / embossed fills | Wilcom, Hatch, Embird — all ship them | Nothing |
| Contour, spiral, Florentine, stipple fills | Wilcom, Hatch, Embird | Nothing |
| Stitch processor (re-density an imported design) | Wilcom US4821662A (**expired**) | Nothing — on the parking list |
| Gradient / colour-blend fills | Wilcom, Hatch, Ink/Stitch | Nothing |
| Auto letter spacing table + per-pair kerning | Wilcom (2–6+ char matrix, 0.10–100 mm) | Lettering side; separate track |

---

## 2. The gap table

Ranked by **customer-visible impact** — what Kent sees on the garment or in the review screen — not by intellectual interest.

Effort is engineer-days on the existing Python pipeline. FTO column: **FREE** = expired or never granted; **LIVE** = in force, design around; **METHOD** = not patented, but the reference implementation is GPL, so clean-room only.

| # | Gap | What it does | Source | FTO | Effort |
|---|---|---|---|---|---|
| **G3** | **Fill angle by fragment-count minimization** | Try 16 candidate scan angles, fully fragment at each, pick the angle with the fewest fragments. Replaces per-region PCA. Directly kills the patchwork-angle defect Kent saw, and minimizes the thing that costs quality: needle repositioning. | US8219238B2 cl.1 | **FREE** (expired ~2018-08-17) | **2–3 d.** We already fragment into monotone columns; wrap the existing `_columns` call in a 16-angle sweep and count. |
| **G1** | **DT-variance satin/fill test** | Replace `2·area/perimeter ≤ 5.0` with skeletal-DT statistics: `2σ < μ < ½·max` ⇒ predominantly regular ⇒ satin. Keys on uniformity of thickness, which is what makes a region satin-able. Rejects tapering wedges our mean-width gate accepts. | US6804573B2 §DT eval, US7016757B2 cl.1 | **FREE** | **3–4 d.** Needs the DT hoisted out of `stage6_satin` into a shared stage (see G10). Every classification golden moves — budget re-pinning. |
| **G5** | **Push compensation** | End cutback along the stitch axis. We model pull and not push; the physics is **+10 % along the stitch axis, −5 % across**. Table keyed by end width (−0.4 to −0.7 mm), **suppressed where the end intersects a neighbour**, gated by end height so curved and short ends are excluded. | Melco US9702070B2 **specification** (claims are on underlay); Ink/Stitch v3.3.0 | **LIVE patent, but the granted claims are the underlay graph — the push method is disclosed, not claimed.** Implement from the physics, not the text. See §5. | **3 d.** Isolated post-pass on emitted runs. |
| **G4** | **Singularity bridging at satin junctions** | Match pairs of regular regions entering a junction under energy minimization, then **reconstruct the occluded boundary** so the pair sews as one continuous column. Replaces `_merge_through_junctions`' tangent-dot weld + 0.4 mm tuck. The corpus already says pros sew crossings as overlapping whole columns; this is how you get there. | US7587256B2 cl.1 | **FREE** | **5–8 d.** Hardest item here and the one most likely to close the spray defect. |
| **G8** | **Dynamic density inset on turning satin** | Hold interstitch distance constant, let the inset float; advance by perpendicular distance from the new endpoint to the previous stitch segment, solving `isd² = cubic(t)` (or its linear/quadratic degradation). Calibration at 0.4 mm density: inset 26.8 % @ 30°, 58.6 % @ 45°, 100 % @ 60°. Also the principled home for the **Law 17 review** — our 0.3 mm short-stitch trigger sits inside the 0.5 mm same-hole radius. | US6390005B1 | **FREE** (expired 2018-05-14) | **3–4 d.** Rails are already parametric-ish; the cheap linear solve is a day, the calibration check against the corpus is the rest. Two open mid-bend intervals at 0.98/1.00 mm vs. the 0.40 target are the test case. |
| **G6** | **Directional pull compensation** | Compensate perpendicular to the stitch direction only, instead of `poly.buffer(pull)`. Our own stage-5 docstring flags this as wrong; machine-physics Law 22-24 confirms. Two-term while we're in there: absolute mm **plus** percent-of-width (0.2 mm is 13 % of a 1.5 mm column and 2.5 % of an 8 mm one). | Pulse US5343401A (% model); Ink/Stitch (two-term) | **FREE** / **METHOD** | **4 d.** Needs the fill angle available at stage 5, which today it is not — that's the real cost. |
| **G2** | **Per-branch tier assignment** | DT statistics **per skeletal branch** instead of per object, so one shape can be satin in its thin arms and fill in its thick body. Goldman explicitly flags this as possible and **never claims it**. No shipping auto-digitizer does it. | US6804573B2 §DT eval (unclaimed) | **FREE and unclaimed** | **5 d**, after G1. This is the differentiator, not just a fix. |
| **G7** | **Penetration-point knockout** | Resolve overlap per candidate penetration point (Bresenham along the fill line, MRU region cache) instead of by boolean geometry. No corridor radius to tune — we already had to halve one — and no boolean robustness failures. | US5809921A | **FREE** (expired 2017-02-03) | **4–5 d.** Replaces a working system, so it needs an A/B against the same-thread corridor before it lands. |
| **G13** | **Underlay by size band** | Select fill underlay type from measured object size, not from the fabric preset. Melco's bands (0–2 mm centre walk, 5–9 mm zigzag + edge walk) and Wilcom's lettering rules (<5 mm none, 6–10 mm centre run, >10 mm edge run) are both published. | Melco US9702070B2 spec; Wilcom Hatch docs | **LIVE spec / published docs** — bands are facts, not claims | **2 d.** We already do this for satin zigzag; generalize the same pattern. |
| **G9** | **Interruption-magnitude sequencing objective** | Define interruption = combined length of other columns sewn before returning to an interrupted one; minimize it. Turns our greedy into an optimization with a stated objective, and it is **measurable on today's output without changing the planner.** | US6804573B2 §path gen | **FREE** | **1 d to measure, 4 d to optimize.** Measure first. Benchmark is TRIM_HEAVY 8.1/1k vs. pro 4.1. |
| **G14** | **Curved fill (UT-space mapping)** | Quadrilateral slices between guide curves, affine XY↔UT map, run ordinary straight fill in UT, map back. Density preserved; curvature decoupled from the boundary. The visible difference on curved emblems between machine output and hand digitizing. | US6587745B1 / WO2000014319A1 | **FREE** (expired 2019-09-07) | **6–8 d**, plus the question of where the guide curves come from (medial axis, or the direction field in §3). |
| **G10** | **Hoist the distance transform to a shared stage** | Compute the (3,4) chamfer DT and skeleton **once**, early, alongside contours — not inside `stage6_satin` after the tier decision. Prerequisite for G1, G2 and G11; also gives the border tier and the run tier a free local-width signal. | US6804573B2 §208 | **FREE** | **3 d.** Pure refactor, byte-identical output achievable, high leverage. |
| **G11** | **Least-squares rail pairing** | Pair rails by minimizing a least-squares objective over normal angle vs. contour normals **plus** normal length proportional to local column width, with placeholders for skipped vertices bounded by their neighbours. Symmetric by construction — cannot tilt the way an asymmetric corridor cap does. | US6804573B2 §coding | **FREE** | **5 d.** Replaces working code; needs the spray metric (cross angles compared **two apart**) as the acceptance test. |
| **G12** | **Fixed vertices at shared borders** | Plant fixed vertices where an adjacent object changes, so two colour regions' common edge cannot drift under independent simplification. Makes the 0.25 mm underlap constant honest instead of partly paying for a vectorize defect. | US9200397B2 cl.4 | **FREE** (expired fee-related, 1998 anchor) | **2 d.** |
| **G15** | **Continuous underlay across a group** | One trim-free underlay under a whole letter or logo group instead of per-shape underlay + lift. Melco duplicates every graph edge to force even degree, then Euler-tours. | Melco US9702070B2 cl.1 | **LIVE ~2029 — design around.** Use a minimal T-join / Chinese-postman duplication (fewer edges, shorter underlay) over **our own skeleton graph**, not centre-walk edges and link-lines. | **4 d** including the design-around. |
| **G16** | **Mitre policy on split columns** | When a column does split at a bend, **extend one member through and shorten the others into it** rather than butting two independently-generated columns. We split at >90° with no run-through member. | US6804573B2 §column smoothing | **FREE** | **2 d.** |
| **G17** | **Serif absorption rule** | Degree-3 node + two short degree-1 branches + single-segment anchor connection + non-acute junction concavity ⇒ absorb the serifs into the surviving branch. More precise than our spur-length prune. | US6804573B2 §merging | **FREE** | **2 d.** |
| **G18** | **Underlay margins per end, incl. negative at joins** | Three margin fields per column; a **negative** margin at the joining end so underlay runs past the cover and column joins don't show. We have one flat inset. | Wilcom Hatch docs | **published docs** | **2 d.** Feeds the open #4380-class complaint (satin joins gap on soft fabric). |
| **G19** | **Density as a function of column width** | Wilcom ships an **editable length/spacing pair table** with auto-spacing on by default; each length must exceed the preceding. Plus thread-denier offsets: 40d +0.01, 30d +0.03, 80d −0.03, 100d −0.06. We hold 0.40 flat everywhere. | Wilcom docs | **published docs** | **3 d** to build, and the table itself is a corpus measurement, not a copy. |
| **G20** | **Stitch processor / inverse digitizing** | Read a stitch-by-stitch design, **analyse each run to recover its implied stitch type, region, lengths and spacings**, and regenerate at a new density or size. Two uses: re-density imported DSTs (already on the parking list), and — more valuable — **as the corpus-mining primitive**, fitting our priors against real files automatically. | US4821662A (Wilcom, expired) | **FREE** | **5 d.** Our `study_pro.py` and `census_pro.py` are already 60 % of this. Formalizing it turns every future constant into a measurement. |

**If only three land:** G3 (fill angle), G1+G10 (DT tier decision), G5 (push comp). Those are the three where a customer looking at a sew-out can point at the difference.

---

## 3. Worth stealing from academia and open source

**License discipline first.** Ink/Stitch is **GPL-3.0**. Algorithms are not copyrightable; we may study and reimplement its *methods* clean-room, but no Ink/Stitch source may be copied, paraphrased line-by-line, or placed on disk next to EMB-Bot. The open-source lens read it entirely through a fetch layer for exactly this reason — keep that discipline. **PEmbroider** is GPL-3 **plus the Anti-Capitalist Software License v1.4**, which expressly prohibits commercial software development: *more* restrictive than GPL for us, ideas only, and the brief that called it "permissive" was wrong. **libembroidery** is zlib but has **no generation side at all** — format I/O only, and still v1.0-alpha. **stitch_generator** is **MIT** — the only permissively-licensed generation library found, and the only one whose code we may actually reuse. **pyembroidery** is MIT and we already use it.

### 3.1 The one to build first

**Interior-biased travel weighting** (Ink/Stitch method, GPL source — reimplement). Build a *separate* travel graph from three gratings oblique to the fill angle (+45°, −45°, −90°, at 2 mm / 2 mm / √2 mm), then weight:

- boundary edges: `3 × length`
- interior edges: `length / (distance_to_outline + 0.1)`

The inverse-distance term pulls travel toward the middle of the shape where later rows bury it; the ×3 pushes it off the silhouette where travel is most visible. Our travel today follows an inset ring at 0.6 mm — i.e. it deliberately hugs the *most* visible path available. This is the single highest-ROI import in the open-source lens and it is pure method: a weighting scheme, no code.

### 3.2 Fill rows as an Eulerian circuit

Nodes = grating-segment endpoints on the boundary; edges = `segment` / `outline` / `extra`. **Duplicate every other outline edge** so every node has even degree, then Hierholzer with an edge chooser **biased toward `segment` edges** — which is what turns an arbitrary Euler tour into natural back-and-forth boustrophedon. Provable single-pass row coverage with no ad-hoc row pairing, O(n log n), with `networkx.eulerize()` only as a fallback. Our monotone columns are correct but hand-rolled; this is the same result with a proof.

### 3.3 Tolerance-sleeve running stitch (Zhao-Saalfeld)

For the run tier and the border tier. Split the path at corners (dot-product test, ~45°), then maintain an **angle sleeve** of admissible directions, intersecting it with the admissible cone of each new point at `tolerance` mm; emit a stitch when the sleeve collapses or `stitch_length` is hit. Then redistribute so the last stitch is never a stub: `stitch_len = d / ceil(d / stitch_length)`.

Why it matters: a fixed-length resampler puts the same stitch count on a straight as on a tight curve, so curves facet and straights over-stitch. A tolerance sleeve makes density a function of curvature with **one user-facing knob that maps directly to visible chord error** — and that knob is corpus-fittable. Our `BEAN_STITCH_MM=0.73` is a fixed length.

### 3.4 Direction fields and stripe patterns — the principled replacement for guided fill

Knöppel, Crane, Pinkall, Schröder, **"Stripe patterns on surfaces"**, ACM TOG 34(4), 2015, [10.1145/2767000](https://doi.org/10.1145/2767000). Given a direction field and a desired spacing, solve for a complex phase function whose **level sets are evenly spaced stripes aligned to the field**. Singularities appear exactly where the field's index forces them, rather than as offset-curve garbage. Companion: **"Globally Optimal Direction Fields"** (TOG 2013) — the smoothest n-RoSy field is the smallest eigenvector of a complex Laplacian, one sparse eigensolve, no local minima. *(Metadata unverified this session — confirm before citing.)*

This is the modern form of Wilcom's UT-space trick (G14) and it gives constant row spacing **everywhere**, not just near a guide curve. Pipeline: region → boundary-aligned direction field → eigensolve smoothing → stripe phase solve at target row spacing → level sets are the fill rows → Eulerian graph over rows → travel graph with interior bias.

The embroidery-specific instantiation exists: **Liu, Piovarči, Hafner, Charrondière, Bickel, "Directionality-Aware Design of Embroidery Patterns"**, CGF 42(2), Eurographics 2023, [10.1111/cgf.14770](https://doi.org/10.1111/cgf.14770) — divergence field → sources and sinks → streamline tracing → connected, machine-fabricable pattern. Mine its 43 references.

### 3.5 Medial-axis pruning that beats spur-length thresholding

Our prune is a length threshold. Three families beat it, each with one monotone knob:

- **AFMM** — Telea & van Wijk, VisSym 2002, [10.2312/VisSym/VisSym02/251-259](https://doi.org/10.2312/VisSym/VisSym02/251-259). Propagate the boundary arc-length parameter alongside the DT; a skeleton point's importance is the **length of boundary collapsed onto it**. Thresholding that one scalar gives a monotone, connected, hierarchical family — no spurs, no disconnection, O(n log n). Best fit for a raster pipeline.
- **DCE-first** — Bai, Latecki, Liu, TPAMI 29(3), 2007, [10.1109/TPAMI.2007.59](https://doi.org/10.1109/TPAMI.2007.59). Simplify the *contour* first; spurious branches are never created. Provably connected.
- **Set the threshold by reconstruction error, not by length** — Shen, Bai, Yang, Latecki, *Science China Inf. Sci.*, 2013, [10.1007/s11432-012-4715-3](https://doi.org/10.1007/s11432-012-4715-3). Prune until the shape reconstructed from the pruned MAT deviates past a tolerance. **Set that tolerance to half a stitch width and pruning stops being a tuned constant.** That is exactly our house style.

And for the rails themselves: **Zhu, Sun, Choi, Jüttler, Wang**, arXiv [1307.0118](https://arxiv.org/abs/1307.0118) — prune at a user-defined Hausdorff threshold, then fit the stable MAT with **splines in (x, y, r)**. That object *is* a satin rail: centreline plus half-width profile, with a certified shape error. Strongest single academic recommendation for our satin tier.

### 3.6 Crossing strokes: skeletons are the wrong tool

**Bessmeltsev & Solomon, "Vectorization of Line Drawings via PolyVector Fields"**, ACM TOG 2019, [10.1145/3202661](https://doi.org/10.1145/3202661). Fit a polyvector field (**two** independent directions per point) and trace curves aligned to it. Two strokes crossing at an X stay two strokes; a skeleton gives you a star-shaped blob. Follow-up: Puhachov et al., TOG 2021, [10.1145/3478513.3480529](https://doi.org/10.1145/3478513.3480529), adds learned junction keypoints.

This is the same problem G4 solves from the other end. Goldman fixes it by reconstructing occluded boundaries after the fact; polyvector fields never create the artifact. Worth evaluating both — our star and script-crossing cases are the test set.

### 3.7 Path planning is CNC pocket machining

A zigzag pocket toolpath and a tatami fill are the same object; a tool retraction and a trim are the same cost. That literature is deep, old, and free:

- **Arkin, Held, Smith, "Optimization Problems Related to Zigzag Pocket Machining"**, *Algorithmica* 2000, [10.1007/s004539910010](https://doi.org/10.1007/s004539910010) — the complexity results. Your jump-minimization heuristic is up against an NP-hard problem; that is engineering reality, not a compromise.
- **Kim, Park, Lee, Kim, "Determination of Cutting Direction for Minimization of Tool Retraction Length"**, ICCSA 2003, [10.1007/3-540-44842-X_69](https://doi.org/10.1007/3-540-44842-X_69) — **literally G3 with travel cost as the objective instead of fragment count.** Worth running both objectives and comparing.
- **Held & Spielberger 2009** ([10.1016/j.cad.2009.04.002](https://doi.org/10.1016/j.cad.2009.04.002)) and **Abrahamsen 2019** ([10.1016/j.jcde.2018.01.003](https://doi.org/10.1016/j.jcde.2018.01.003)) — spiral toolpaths **with islands**, the case Ink/Stitch's spiral fill throws geometry away to avoid.
- **Abu Mansor, Hinduja, Owodunni**, *CAD* 2006, [10.1016/j.cad.2005.09.001](https://doi.org/10.1016/j.cad.2005.09.001) — **uncut-material detection via the Voronoi diagram**, i.e. "where does my fill leave a gap" as a geometric query rather than a rasterized coverage mask. Direct upgrade for preflight.

### 3.8 The negative result worth acting on

**There is no published end-to-end learned vector-art → machine-stitch system.** Every ML-and-embroidery paper from 2017–2026 the academic lens could surface is **appearance synthesis** — making an image look embroidered. MSEmbGAN, the LoRA work, the GAN translation papers: all output pixels. The single exception producing machine-fabricable output is Liu et al. 2023, and it is classical vector-field math, not learning. The closest thing to learned stitch *placement* is Ma & Sun's Markov-chain random-needle work.

**Classical CV plus measured constants is the literature's state of the art for this problem.** Our architecture is not behind the field. That is worth saying out loud before anyone proposes replacing the pipeline with a model.

### 3.9 Small, concrete, immediately useful

- **Sew a repeated satin as running stitch and let the later satin cover it** (Ink/Stitch method). Makes doubled Eulerian traversals free underlay instead of visible double-stitching. Directly applicable to our sequencer.
- **Redwork edge-doubling**: every edge exactly twice ⇒ Eulerian circuit by construction ⇒ zero jumps, returns to origin. With **near-miss intersection snapping at ~50 px**, which is what makes it survive real tracer output where "intersections" rarely coincide exactly. This is the correct algorithm for our border and run tiers and it is embarrassingly simple.
- **Progressive short-stitch inset levels**: the inset index **increments on each consecutive short stitch and resets on a long one**, with a per-level inset value. On a tight inside curve that gives a graded sawtooth rather than a hard step. Ours is one fixed pull fraction with one cap — this is the better shape and it's a small change.
- **Anti-moiré randomization with phase memory**: carry the previous shortening ratio forward rather than IID jitter per row. Naive per-row jitter does not desynchronize phase and does not kill banding.
- **Gradient blending by √n row-ownership interleave at constant spacing** — never by density ramp. Varying density changes fabric tension and reads as a defect. Relevant the moment we blend between quantized regions.
- **CCSE dataset** ([arXiv 2210.13826](https://arxiv.org/abs/2210.13826)) — CCSE-Kai is built from **font outlines**, i.e. exactly our clean-vector input class, with ground-truth stroke decomposition. Useful as a benchmark for a classical stroke splitter even if we never train on it.
- **"Decompose into strokes first, thin second"** — He & Yan, PRL 2000, [10.1016/S0167-8655(00)00039-8](https://doi.org/10.1016/S0167-8655(00)00039-8). An explicit published inversion of our current pipeline order, producing far fewer junction artifacts. Cheap to test.

### 3.10 What the Ink/Stitch tracker says users actually want

Four years open, still unbuilt: **cross-object fill routing** (#1677). Also open: unified routing across stitch types (#3531), push compensation for fill (#4491), satin join gaps on soft fabric (#4380), controlled randomness for a hand-made look (#4433, #4207).

Read: users are **not** asking for better fill interiors. They are asking for (a) automatic routing and sequencing across objects, (b) compensation that prevents visible gaps, and (c) controlled randomness. All three are sequencing and compensation problems — which is precisely where a corpus-measured-constants approach has the most leverage.

---

## 4. Parameter census: what our automation turns, and what it should turn next

### 4.1 The benchmark

From the vendor docs, the complete set of knobs a *guided* Hatch/Wilcom auto-digitize turns:

| Turned by automation | Left to the fabric preset |
|---|---|
| Colour → fill / detail / omit | spacing (density) |
| Stitch type per class (3 options) | pull compensation |
| Outlines on/off + colour | underlay type, margins, spacing, length |
| Border on/off + colour | short stitches / stitch shortening |
| Colour sequence ("fills first, details last") | auto-split min/max |
| Sequencing by closest join | corner fraction |
| Background omitted | tatami offset fractions A/B, backstitch type, random factor |
| Colour-matching method (3 options) | tie/trim, travel run length |

Six categorical decisions. Everything continuous is a global constant chosen by the user picking a fabric. Hatch's "Instant" mode turns *nothing* — one click, default settings.

**Vendors do not publish defaults.** Wilcom and Hatch document what a field means and almost never what it defaults to; defaults live in binary fabric presets and object templates. Where a number *is* published it is usually a recommendation to a human, not a software default (Wilcom's 7.00 mm auto-split min length is the example). The knob list is fully recoverable from docs. The values are not — they must come from our corpus. **That division of labour is correct and it is our moat.**

### 4.2 What we turn today

Per shape, conditioned on geometry:

| Knob | Rule | Where |
|---|---|---|
| satin vs. fill | ribbon width ≤ 5.0 mm **and** length ≥ 3× width, on the **artwork** polygon | `stage6_satin.is_satin_candidate` |
| zigzag underlay on satin | column width > 2.5 mm (phase-census confirmed: with-Z median 2.71, without 1.33) | `SATIN_ZIGZAG_ABOVE_MM` |
| split satin + segment count | cross > 5.0 mm, `k = ceil(W / 3.0)`, stagger wave period 4 at ±0.23 segments | `SPLIT_*` |
| run tier vs. drop | area < `min_detail_mm²`, floored at loop ≥ 2.2 mm **and** area ≥ 0.16 mm² (one thread-width squared) | `run_outline`, `RUN_MIN_*` |
| border on/off | per-shape `Region.meta["border"]` overrides a global mode; mode defaults **off**, measured (corpus: 18 borders vs. 21 fills vs. 150 satins) | `stage6_border` |
| fill angle | per-region PCA principal axis | `principal_angle_deg` |
| sew order | colours by descending pixel weight; within a colour, start at the extreme then greedy nearest-**shape** | `stage5_overlap`, `stage7_sequence` |
| travel vs. jump vs. trim | straight-if-inside → inset ring → lift; trim above 3.0 mm | `travel_path`, `TRIM_AT_MM` |
| thread assignment | CIEDE2000 nearest in the operator's chosen brand chart; unknown brand **raises** rather than substituting | `threads.py` |
| same-thread separation | hold open the bare-fabric lens within one pull of both neighbours | `stage5_overlap` |

**Nine geometry-conditioned decisions against their six categorical ones.** Plus the invariant nobody else states: classification runs on artwork, so the same logo sews the same structure on a polo and on a towel.

Not conditioned — taken from the fabric preset or held flat: pull comp amount, fill density, fill stitch length, underlay type for fills, underlay inset, short-stitch trigger and pull, corner apex spread, tie length and count, travel stitch length.

### 4.3 What it should learn to turn next

Ranked by value per unit of work, and each one is a **measurement task before it is a code task** — the constant has to come off the corpus.

1. **Fill angle → fragment count** (G3). Replace PCA. The one knob we turn badly.
2. **Density → column width.** Wilcom ships an editable length/spacing pair table with auto-spacing **on by default**; we hold 0.40 flat. Measure the corpus's width→spacing relation first; the table is the deliverable, the code is trivial. Thread-denier offsets are published (40d +0.01, 30d +0.03, 80d −0.03, 100d −0.06) and give the axis a second dimension for free.
3. **Underlay type → object size**, for fills, not just satin (G13). We already prove the pattern works on satin's zigzag threshold.
4. **Pull comp → f(width, angle)**: two-term (absolute mm + percent of width) and directional (G6). One fabric constant cannot serve a 1.5 mm column and an 8 mm one.
5. **Short-stitch trigger → f(curvature)** via the floating-inset formulation (G8) — and settle the Law 17 question (0.3 mm trigger vs. 0.75 mm needle blade) in the same pass.
6. **Corner apex spread → f(turn angle).** We spread every apex over exactly one column width regardless of how sharp the turn is. Wilcom exposes a "corner fraction" for precisely this and publishes no default, which means the corpus owns the answer.
7. **Push comp end cutback → f(end width), suppressed on intersecting ends, gated by end height** (G5).
8. **Underlay margin per end**, negative at joins (G18).
9. **Density as a per-region budget summed over overlapping objects** (machine-physics Law 27: `coverage_units = Σ 0.4/spacing`, safe stack ~2.5). Our preflight measures **per object** and would miss stacked-layer failure entirely. This is a preflight gap, not a planner gap, and it is the kind of thing that shows up as a puckered sew-out with no warning.

**The framing for the review screen:** every item above is a continuous knob that commercial tools leave to a global preset. Turning them per-shape from measured geometry is not a feature we're catching up on — it is the thing their architecture cannot do without a rewrite.

---

## 5. Freedom to operate — engineering notes

**These are engineering notes for planning purposes, not legal advice, and nothing here should be relied on as a clearance opinion.** Expiry dates below are largely *computed* from filing and grant dates, not read from a verified status line, and maintenance-fee lapses could have ended several earlier. Google Patents' "anticipated expiration" fields are informational. Before shipping anything claim-adjacent, re-verify status and maintenance history on USPTO PatentCenter and put an hour of counsel on it — the same hour already earmarked for the CC-BY-SA `.embf` question.

### 5.1 Free — build without hesitation

**The entire Goldman / SoftSight → Vistaprint → Cimpress family.** US6836695, US6804573B2, US6947808B2, US7016756B2, US7016757B2, US7587256B2, US8219238B2, US8532810B2, US9200397B2. All anchored to the 1998-08-17 root application, all expired ~2018-08-17. US9200397 shows "Expired – Fee Related." **This family is the entire canonical pipeline** — segmentation, chain-code, chamfer DT, the satin/fill variance test, triangular filtering, 16-angle fragment minimization, fragment provenance and mid-lines, recursive path planning, anchors, serif merging, singularity bridging, least-squares rails, column smoothing, the 45° corner rule, branch traversal, the interruption metric. Gaps G1, G2, G3, G4, G9, G10, G11, G12, G16, G17 all draw from it.

**All Wilcom patents.** US4821662A (stitch processor, G20), US6587745B1 / WO2000014319A1 (curved fill, G14 — expired 2019-09-07, "Expired – Fee Related"), EP0075490A2. Their tufting patents are a different company and irrelevant.

**WO2005061774A1 — free and unusually valuable.** Ceased at non-entry into national phase; granted in no jurisdiction. The level-set cut lines, the angle-bisector sampling at concave vertices, the separation-class clique construction, the conflict-elimination ranking, and the "minimise stitch shortening" objective are all unencumbered worldwide **and** function as prior art against anyone who tries to claim them later. If we implement the decomposition, publish a note.

**Pulse US5809921A** (penetration-point knockout, G7 — expired 2017-02-03), **US6390005B1** (dynamic density inset, G8 — expired 2018-05-14, pre-AIPA so no PTA), **US5343401A** (the punch data model and the percentage pull-comp convention — expired), **US5270939A** (stitch-file → outline conversion, expired).

**Brother US5386789A** (background band + island rescue, expired ~2014), **US5576968A** (global direction chooser — the only patent in the survey whose status was *directly verified*: "Expired - Lifetime"), **US5558031A** (outline enlargement, ~2016), **US5899154A / US5934209A** (split self-intersecting outlines at their self-intersections before generating stitches — worth having, ~2017), **US6202001B1** (motif tiling, ~2018).

### 5.2 Live — design around, or read for physics only

**Melco US9702070B2** — filed 2014-09-02 as a divisional of an application filed **2009-01-16**, so the term runs from 2009-01-16: **in force to ~2029 + PTA.**

- **Claim 1 is the underlay graph**: identify a group, identify connectors, create a **centre walk edge** per element, create **link-lines** between each centre walk edge and each connector, determine sewing order from the graph. The embodiment duplicates every edge and runs an Euler tour.
- **Design-around for G15:** the Eulerian construction itself is textbook and unclaimed. What is claimed is that specific graph. Build the graph from **our existing skeleton and branch structure** — not from centre-walk edges plus connectors plus link-lines — and duplicate a **minimal T-join / Chinese-postman edge set** rather than every edge. That is both outside the claim and a *better* result: shorter underlay. Combine with Goldman's expired branch-traversal recursion.
- **Push compensation (G5) is described in the specification; the granted claims are directed to the underlay method.** The physical constants it discloses — +10 % along the stitch axis, −5 % across, end cutbacks of 0.4–0.7 mm scaling with end width — are facts about thread and fabric, not patentable subject matter, and they are exactly the kind of thing our corpus should be validating anyway. Implement from the physics and our own measurements. Have counsel confirm the claim scope before it ships.

**Brother US8200357B2** (photo → per-pixel angle field) — **active to ~2028**. Read for architecture only: luminance = `(max+min)/2`, high-pass, four directional difference sums → normal angle → stitch angle = normal + 90°, intensity `ΣT·(255−v)/(255·(N·4)²)`, weak-pixel angle re-estimation by vector averaging, segment pruning by angle-within-±θ-and-lower-intensity, colour chosen so the local average of the stitched result equals the local average of the source, exposure-ratio culling. Sibling **US8473090B2** (frequency/angle area split, hybrid detail-vs-flat) **active to ~2031**. Our photo track is documented separately with per-input-class ceilings; when it resumes, this is the shape of the thing to design around.

**Pulse US10590580B2** ("Vector defined embroidery", ~2038) and **WO2022082296A1** ("Embroidery color transition") — both active, both unread. If we build gradient or colour-transition fills, read these first.

**VSM Group AB US8108062B2** (freehand simulated-needle digitizer) — **~2026 + PTA, borderline.** Not on our roadmap; note it only because manual draw tools are on the parking list.

### 5.3 Licence, not patent

- **Ink/Stitch — GPL-3.0.** Methods yes, code never, source never on disk beside ours. Applies to §3.1, §3.2, §3.3, §3.9.
- **PEmbroider — GPL-3 + Anti-Capitalist v1.4.** Commercially unusable. Its hatching taxonomy (PARALLEL / CROSS / CONCENTRIC / SPIRAL / PERLIN / VECFIELD / DRUNK) is a useful catalogue of *what to build*; nothing else is takeable.
- **stitch_generator — MIT.** Code reusable. Its abstraction is worth adopting whole: a **Path = shape function + width function + direction function**, a stitch effect consumes a Path and returns mm coordinates, subdivision functions sample lengths independently of geometry. Width-as-first-class-input makes variable-width satin fall out naturally and composes directly with a medial axis whose radius function **is** the width function — see G10 and §3.5.
- **pyembroidery — MIT.** In use. **libembroidery — zlib but no generation side**, I/O reference only, still v1.0-alpha.
- **Our own standing rules:** permissive-only dependencies, no GPL; thread-chart data kept under the facts doctrine but **no charts from companies selling embroidery software or machines**. Both hold here unchanged.

### 5.4 Open verification items

Carry these to the IP hour rather than resolving them in engineering:

- Exact PTA-adjusted expiry of **US9702070B2**, and whether the push-compensation disclosure sits outside the granted claims as read.
- Exact grant date of **US8532810B2**.
- Assignee of **US6390005B1** — the inventors are the Pulse team but the Justia record shows no assignee line.
- Legal status of **EP1102881A1** (Softfoundry, grain-structure stitch selection) and Wilcom's AU provisional **AUPQ977000A0** (raised embroidery).
- Whether **US6968255B1** (Pulse auto-stippling, ~2024) has actually lapsed.
- **Bernina / OESD (Fritz Gegauf) was never properly searched** — the query endpoint 503'd. Redo before relying on the completeness of this survey.

### 5.5 One-line summary

**Everything in the gap table except G5 and G15 is free to implement today.** G5 is a physics constant we should measure ourselves regardless. G15 has a design-around that produces a shorter underlay than the patented method. There is no patent blocking us from building the canonical commercial pipeline — the barrier was never IP, it was that the values were never published, and that is a corpus problem, which is the problem we are already set up to solve.