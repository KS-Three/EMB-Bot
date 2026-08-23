# Region identification — what a region is today, and what it would have to become

**Status: DIAGNOSIS COMPLETE, DIRECTION IS KENT'S.** This doc builds nothing.
Five independent measurement passes on 2026-08-23 (four portraits + the
committed corpus, all at HEAD `706e7cf`) converged on one picture; the options
at the end carry measured costs and the bars that apply to each.

## The one-sentence diagnosis

A region today is **a spatially coherent patch of merely-similar colour**
(`MERGE_DELTAE00_THRESH = 26.0` ΔE00, `stage2_photo_segment.py:271`) that the
embroidery contract then **forces to be one thread** — against the pipeline's
own "more tone than one thread can show" line of **18.0**
(`TONAL_SPLIT_MIN_DELTAE`, same file, line 1229).

The region former is licensed to merge what the project's own constant says
cannot be sewn as one thread. Everything below follows from that gap.

## Both routes are one segmenter and one boolean

`photo_subject`, `photo_scene` AND `gradient` all dispatch to
`stage2_photo_segment.segment` (pipeline.py:428-437) — same SEEDS
oversegmentation, same RAG merge, same constants, same pixels. The only
region-count-relevant difference is `effective_split_tonal` (pipeline.py:86).

Measured funnel, identical up to the fork:

| stage | sparkler toggle | sparkler default | face toggle | face default |
|---|---|---|---|---|
| SEEDS superpixels | 950 | 950 | 910 | 910 |
| post-merge labels | 23 | 23 | **6** | **6** |
| after tonal split | 53 | — | 15 | — |
| stage-3 connected components | 705 | 23 | 888 | 6 |
| final regions | **100** | **30** | **33** | **6** |

So "110 regions vs 24" was never two segmenters disagreeing.

## Failure mode 1 — the default route ships the contradiction

With the split off, the merge's output goes straight to the needle:

- **91% of sewn area (74/92 regions) exceeds the 18 ΔE00 one-thread line;
  67% of area sews a spool more than 10 ΔE00 from its own pixels.**
- `face_closeup_blur` is **one region covering 94.8% of the design
  (8,054.8 mm²) spanning 55.2 ΔE00** — roughly six shade-steps on one thread.
- The route's designated tonal carrier does not catch it: the blend tier
  decomposed **zero** regions on all four portraits (best r² 0.437-0.524
  against its 0.5 floor), and no shape on any default-route plan sews under
  more than one thread.

### Why a blurred face collapses to six regions

Not the superpixels (910 present), not prep (stage 1.5 never runs — `photo_prep`
defaults False on both acceptance routes), not the palette, not the floors.
**It is the merge, and the guard built to stop exactly this is structurally
blind to defocus.**

`_boundary_contrast_initial_adjust` protects an edge whose boundary contrast
clears `BOUNDARY_CONTRAST_HARD_LAB = 6.0` — calibrated on the measured
separation between a drawn edge (18-40 Lab) and gradient interior (~0.5). On
this photo the **99th percentile** of boundary contrast is **2.33** (median
0.36). The guard fires **zero times**. 99.0% of adjacent-superpixel pairs sit
below the 26 threshold on colour alone, so 904 merges run to 6 labels.

The guard's premise — that content destruction happens at drawn edges — is
false for blur. **A soft boundary does not imply same content.**

And the default sits on a plateau: 6 regions at both threshold 26 and 30; the
last content-bearing structure dissolves between 22 and 26. A small retune
would do nothing, and retuning that constant is already a recorded
measured-negative (MASTER_SCOPE, "Leave `MERGE_DELTAE00_THRESH` at 26.0").

## Failure mode 2 — the toggle route's granularity is mostly residue

The split shatters 2-5 large regions into parts, but **two thirds of what
comes out is confetti a floor was supposed to bar**:

- 22 of 33 face regions and 69 of 100 sparkler regions are under 40 mm².
- `split_tonal_regions` glues each sub-floor leftover onto the largest part's
  *mask* — but region identity is re-derived at stage 3 as connected
  components per spool label, so every glued crumb not 8-connected to the main
  blob comes back. The face's main split mask contains **878 connected
  components**.
- **The effective part floor is therefore `min_detail_mm²` (2.25 mm²), not the
  40 mm² `TONAL_SPLIT_MIN_PART_MM2`'s docstring claims.**
- 59% of regions and 71% of area still exceed the 18 line afterwards: the
  split's 150 mm² area floor exempts most offenders and its 4-part cap cannot
  bring a 75-78 ΔE00 span under 18.
- The boundaries it adds are the **smoothest in the design** (estimated mean
  0.8-8.5 Lab) — L\* quantile cuts, not feature-following ones.

Production cost, against the repo's own ceilings (`TRIMS_PER_1000_MAX = 4.1`,
`COLOR_STOPS_MAX = 10`): **246 stops across four portraits (62/image), 22.5
trims per 1,000 (5.5x the ceiling), 38 distinct spools off a 12-cone palette.**
All four portraits break every ceiling.

## No single granularity control exists — this is a design job

Measured across 108 sweep points:

- **Default route** has one dominant monotone knob (`MERGE_DELTAE00_THRESH`:
  face 5→75 regions, sparkler 18→119) — but it was tuned on two commissioned
  logos against a magic 20-80 accept band **with zero photographs in the
  tuning corpus**, it acts purely in colour space (region count is nearly
  invariant to physical output size), and it is pinned by the gradient lane's
  own suites.
- **Toggle route** is **non-monotone**: sparkler final count is U-shaped, with
  a *minimum* of 67 at threshold 18 against 100 at 26 and 119 at 6. Raising the
  threshold *increases* the final count, because bigger merged regions carry
  wider spans → more parts → far more glued-crumb components (316 → 1071).
- `TONAL_SPLIT_MIN_DELTAE` is **dead across its plausible range** (real regions
  span 37-61 ΔE00, far past the 18 gate). `TONAL_SPLIT_MIN_AREA_MM2` is
  **flat**. `TONAL_SPLIT_MAX_PARTS` **flips sign between the two photos**
  (face 11→45, sparkler 91→68).
- `target_width_mm` — the only knob a *user* holds — changes toggle-route
  granularity 2.4x without being called a granularity control. **At the spec's
  own 5x7 hoop scale, sparkler yields ~242 regions, not 100.**

Nothing in the system states a granularity objective in embroidery units.

## What the craft does instead — the kind-level divergence

From the corpus laws, the Hatch/Wilcom/Melco sources, and a 23-design census of
the professional's own files:

1. **The unit is a design element with a sewing job**, not a colour cluster.
   In the pro corpus one colour block covers a median of exactly **1**
   contiguous coverage element.
2. **The pro's regions are not a partition.** Adjacent fills *overlap*
   0.4-0.8 mm; the base colour runs **continuous underneath** rather than
   being knocked out (77% median backing share). Any segmentation emitting a
   pixel-partition has already diverged in kind.
3. **One thread returns many times.** 55% of colour stops are returns to a
   thread already used (n=14 designs, 92 blocks over 41 threads). EMB-Bot
   emits one block per thread and cannot express this.
4. **Order encodes layering**, background→foreground (77% of overlapping pairs
   put the smaller block later).
5. **Existence is decided against the garment**, not the artwork — the pro
   filled a banner and left the letters as *bare fabric*.

Pro vs us on genuine artwork: `logo_script_tires.png` — ours 6 regions / 2
threads / 9 cut paths against the pro's 2 blocks / 2 threads / 9 cut paths.
**On clean input we already converge.** On render-derived input the flat lane
produces 187-246 regions and 6-8 threads for a two-thread logo, which points at
a large share of the gap being *input normalization*, not segmentation. (n=1
clean control — hypothesis, not finding.)

## Options, with measured costs and the bars that apply

**A. Element-level instrument first.** Extend `tools/pro_parity/` with a
block/element census: does a grouping of our regions reproduce the pro's block
structure, layering order and thread returns? Days. No gates. The current
scorecard cannot see element structure at all, so B and F are unmeasurable
without it. Catch: it measures conformance to one digitizer — pair every number
with the 75-84 pro-vs-pro ceiling.

**B. A block layer between regions and stitching.** Keep colour regions as
geometry; add the pro's actual unit — blocks grouping regions into elements,
sequenced background→foreground, **emitting one thread more than once**. This
is the single loudest corpus finding the engine cannot express. Weeks; largest
blast radius (`sew_index` model, stage 7, sequencing goldens, Layers panel).
Catch: trims will not visibly drop while `chain_links` is gate-1 frozen, and
today's scorecard will not reward it — do it without A and it is unmeasurable.

**C. Flat-lane input normalization.** Collapse antialiasing/JPEG/texture noise
to the artwork's true small palette before clustering, or make Studio's
existing Flatten step the enforced entry for logo-class inputs (Hatch *blocks*
digitizing until artwork is prepped). Modest code, heavy golden churn. Note
`stage2_quantize.merge_delta_e = 6.0` is a *different* constant from the
ruled-on `MERGE_DELTAE00_THRESH`, so tuning it is not barred — but the tires
control suggests the flat lane may already be adequate on clean input, so
**normalize the input rather than retune the cluster**.

**D. Review-screen colour-role controls.** Per-palette-entry "fill / detail /
omit / stitch-as-garment-colour" — the Hatch model, and the only place the
garment-colour decision *can* live. Studio UI + service contract; no gates.
Catch: manual, not engine intelligence.

**E. Boundary engineering pair.** (1) Shared-border vertex pinning at vectorize
so adjacent regions' common edge cannot drift under independent simplification
(~2 days, pure geometry, no gate). (2) `overlap_mm` 0.25 → 0.40 per the
measured pro median — but that changes thread on fabric, so it is **gate 1**
and needs cloth.

**F. Blocked, named so nobody re-proposes it.** Scale-aware region identity is
phase 2 (gate 2). Per-branch mixed satin/fill inside one shape is currently
unmeasurable — its instrument's straddle population is 95.8% noise. Region-level
surgery for the satin/fill straddle has a measured ceiling of ≤2.1% and is
already recommended against.

## Defects found along the way, worth their own small changes

1. **`_shade_lab_colors` buckets on the raw absolute darkness axis** with
   centres pinned at 0…1, while measured per-shape darkness spans are median
   0.21-0.38. A span under 0.5 cannot populate both end buckets, so empty
   buckets are structurally guaranteed — **45.3% of all decomposed shades are
   mean-fallback duplicates**. Min-max normalising would leave zero empty
   buckets on every shape measured. It also minted one spurious cone-and-stop.
2. **`logo_drone_thermal_badge.png` is byte-identical to `drone_render.png`**
   (md5 `adb0a79f25ff43a54c77957cc03e1bef`). Both are in the scorecard's
   `FIXTURES`, so every aggregate double-counts one image — and one copy is
   filed under "real customer artwork".
3. **Stage 2 peaked at 9.1 GB RSS on a 4.8 MP scan** (OOM-killed twice under
   co-tenancy). The decode ceiling landed in PR #214 caps the long side, not
   total pixels; a real customer scan can still exhaust the box.
4. **Latent inversion footgun:** `BOUNDARY_CONTRAST_MERGE_FACTOR` is
   `13.0/MERGE_DELTAE00_THRESH` and `FACE_MERGE_FACTOR` is
   `5.0/MERGE_DELTAE00_THRESH`. Both exceed 1.0 if the base threshold is ever
   set below 13.0 (resp. 5.0), turning the protections into merge
   *accelerants*.
5. **Four code-vs-comment disagreements** beyond those: the part-floor
   docstring (above), `resolve_small_regions`' chain-rescue lane claim
   (half-implemented), the module docstring's "CIEDE2000 edge-weight" (initial
   RAG weights are Euclidean Lab), and `stage4_vectorize`'s "single connected
   component" invariant (transiently violated by glued split masks).

## Reproducibility

All measurement scripts and per-run JSON are in this session's scratchpad and
are read-only against the repo; no private photo was copied and every number
here is derived. The five passes were: region quality profile (26 runs), the
granularity knob map (108 sweep points), SAM2-for-embroidery, the craft/pro
census (23 pro designs), and the thread-chart floor sweep (68 charts).
