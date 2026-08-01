# Research partials — harvested from capped workflow runs (2026-07-31)

Six research workflows were killed mid-flight by the session usage cap (reset
2am America/Chicago). Their completed agents' returns are preserved here
VERBATIM so the resume starts from data rather than repeating the work — the
runs themselves also replay these from cache via `resumeFromRunId`, but a
cache is not a record, and this is the record.

Nothing below has been through a synthesis pass or an adversarial check. It is
raw agent output: treat every number in it as unverified until the synthesis
runs and the claims get sourced. Do NOT wire any constant in here into the
engine on the strength of this document.

Run IDs for resume:
| Workflow | Run ID | Completed / total |
|---|---|---|
| corpus-chaining-laws | `wf_e3ee1b76-143` | 2 of 8 |
| autodigitizing-masters-teardown | `wf_858d3495-b2f` | 3 of 6 |
| corpus-round3-exhaustive | `wf_10182ca1-7d4` | 2 of 7 |
| fill-technique-expansion | `wf_d7d76bc9-5ae` | 0 of 5 |
| lettering-monogram-mastery | `wf_06b01027-983` | 0 of 6 |
| specialty-techniques-mastery | `wf_05aee14a-061` | 0 of 6 |

Completed and already committed as real docs: photo-digitizing plan
(`docs/photo-digitizing-plan-2026-07-31.md`) and the machine-physics playbook
(`docs/machine-physics-playbook-2026-07-31.md`).


---

## Corpus chaining laws (2 of 6 batches mined)

Inter-element transitions measured in the pro corpus: 59 transitions, 36 needle-down links vs 23 trims. Synthesis never ran — these are the raw batch returns.


### Agent return 1 (949 chars)

["rose-hand-free-embroidery-design.dst","summer-umbrella-free-embroidery-design.dst","cat-and-girl-sketch-free-embroidery-design.dst","christmas-sleigh-reindeer-free-embroidery-design1.dst","bunny-star-free-embroidery-design.dst","snowman-christmas-colors-free-embroidery-design.dst","corgi-sketch-free-embroidery-design.dst","teddy-bear-vintage-sketch.dst","chamomile-love.dst","creative-free-embroidery-design.dst","enjoy-coffee-free-embroidery-design.dst","think-positive.dst","hello-spring.dst","little-romeo.dst","hope-christmas-inscription.dst","be-joy.dst","breathe-feathers.dst","boy-mama.dst","mom-smile-free-embroidery-design.dst","i-love-pets-free-embroidery-design.dst","jolly-af.dst","autumn-time.dst","miss.dst","i-love-pumpkin.dst","gather.dst","bridesman.dst","hello-summer.dst","sweet-heart.dst","enjoy-moment-script.dst","welcome.dst","hello-fall.dst","future-mrs.dst","smile.dst","best-friend.dst","birthday-squad.dst","anna.dst"]


### Agent return 2 (14,452 chars)

{"files": ["C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\think-positive.dst", "C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\enjoy-coffee-free-embroidery-design.dst", "C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\creative-free-embroidery-design.dst", "C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\chamomile-love.dst", "C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\corgi-sketch-free-embroidery-design.dst", "C:\\Users\\EE-LT-11030\\EMB-Bot\\scratch_corpus\\teddy-bear-vintage-sketch.dst"], "links": [{"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 1.21, "nStitches": 1, "runStitchMm": 1.21, "routing": "under_next_element; cov_later=100%, on_earlier=100%, in_next_bbox=100%, dev=0.00mm"}, {"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 1.39, "nStitches": 1, "runStitchMm": 1.39, "routing": "under_next_element; cov_later=100%, on_earlier=100%, in_next_bbox=100%, dev=0.00mm"}, {"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 6.81, "nStitches": 4, "runStitchMm": 1.99, "routing": "baseline/shared-edge band (letter stem line), fully covered by later satin; cov_later=100%, dev=0.69mm"}, {"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 8.99, "nStitches": 5, "runStitchMm": 2.05, "routing": "under_later_stitching (runs along path of satin sewn after); cov_later=100%, dev=0.28mm"}, {"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 12.13, "nStitches": 7, "runStitchMm": 2.12, "routing": "under_later_stitching; cov_later=100%, dev=0.65mm"}, {"file": "think-positive.dst", "kind": "needle_down_link", "gapMm": 13.95, "nStitches": 6, "runStitchMm": 2.41, "routing": "under_later_stitching; cov_later=100%, on_earlier=100%, dev=0.69mm"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.58, "nStitches": 1, "runStitchMm": 1.58, "routing": "shared-edge band, covered later; cov_later=100%, dev=0.00mm"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.9, "nStitches": 1, "runStitchMm": 1.9, "routing": "under_next_element (covered by next element's own stitching); cov_later=100%, next_el=100%"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 2.4, "nStitches": 1, "runStitchMm": 2.4, "routing": "under_next_element; cov_later=100%, in_next_bbox=100%"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 4.73, "nStitches": 4, "runStitchMm": 1.47, "routing": "baseline band (ymin edge shared by both clusters), covered later; cov_later=100%, dev=0.62mm"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 10.44, "nStitches": 18, "runStitchMm": 2.41, "routing": "under_later_stitching, path curves to follow future column (dev 9.6mm from chord); cov_later=100%"}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 28.45, "nStitches": 14, "runStitchMm": 2.2, "routing": "under_later_stitching: verified visually - runs up the SPINE of a satin stroke sewn after it; cov_later=100%, dev=3.04mm"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.06, "nStitches": 1, "runStitchMm": 1.06, "routing": "under_next_element; cov_later=100%, in_next_bbox=100%"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.12, "nStitches": 1, "runStitchMm": 1.12, "routing": "baseline band + under next element; cov_later=100%, in_next_bbox=100%"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.24, "nStitches": 1, "runStitchMm": 1.24, "routing": "baseline band + under next element; cov_later=100%, next_el=100%"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.41, "nStitches": 1, "runStitchMm": 1.41, "routing": "under_next_element; cov_later=100%, next_el=100%"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 2.98, "nStitches": 2, "runStitchMm": 1.49, "routing": "under_later_stitching, straight (dev 0.04mm); cov_later=100%"}, {"file": "creative-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 61.7, "nStitches": 34, "runStitchMm": 2.47, "routing": "under_later_stitching: verified visually - travel run traces the script word's connecting baseline path, satin letters sew over it afterwards; cov_later=100%, dev=9.84mm"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 1.08, "nStitches": 1, "runStitchMm": 1.08, "routing": "under_next_element; cov_later=100%, next_el=100%"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 1.2, "nStitches": 1, "runStitchMm": 1.2, "routing": "shared-edge band + under next (flower-center hatching, not lettering); cov_later=100%"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 1.6, "nStitches": 1, "runStitchMm": 1.6, "routing": "shared-edge band + under next; cov_later=100%"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 1.82, "nStitches": 1, "runStitchMm": 1.82, "routing": "shared-edge band + under next; cov_later=100%"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 3.55, "nStitches": 2, "runStitchMm": 2.04, "routing": "under_later_stitching; cov_later=100%, dev=0.99mm"}, {"file": "chamomile-love.dst", "kind": "needle_down_link", "gapMm": 20.03, "nStitches": 9, "runStitchMm": 2.26, "routing": "along_earlier_stitching_edge: exposed (cov_later=0%) but 100% of path within 0.9mm of already-sewn threads; dev=1.45mm"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.33, "nStitches": 1, "runStitchMm": 1.33, "routing": "along_earlier_stitching_edge (hop inside sketch art); cov_later=0%, on_earlier=100%"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 1.9, "nStitches": 1, "runStitchMm": 1.9, "routing": "under_next_element; cov_later=100%, next_el=100%"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 2.2, "nStitches": 1, "runStitchMm": 2.2, "routing": "along_earlier_stitching_edge; cov_later=0%, on_earlier=100%"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 5.41, "nStitches": 3, "runStitchMm": 1.77, "routing": "under_later_stitching, straight; cov_later=100%, dev=0.01mm"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 10.62, "nStitches": 7, "runStitchMm": 1.66, "routing": "under_later_stitching; cov_later=100%, dev=1.36mm"}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "needle_down_link", "gapMm": 27.64, "nStitches": 20, "runStitchMm": 1.5, "routing": "along_earlier_stitching_edge: verified visually - follows the body silhouette contour of previously sewn shading, exposed but reads as a sketch line; cov_later=0%, on_earlier=100%, dev=4.65mm"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 1.08, "nStitches": 1, "runStitchMm": 1.08, "routing": "shared-edge band + under next; cov_later=100%"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 1.28, "nStitches": 1, "runStitchMm": 1.28, "routing": "baseline band + under next element; cov_later=100%, next_el=100%"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 1.98, "nStitches": 1, "runStitchMm": 1.98, "routing": "under_later_stitching; cov_later=100%"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 2.31, "nStitches": 2, "runStitchMm": 1.17, "routing": "baseline band (ymin shared edge), covered later; cov_later=100%, dev=0.20mm"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 6.87, "nStitches": 4, "runStitchMm": 2.25, "routing": "under_later_stitching; cov_later=100%, dev=1.88mm"}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "needle_down_link", "gapMm": 17.08, "nStitches": 15, "runStitchMm": 1.21, "routing": "along_earlier_stitching_edge: exposed but rides existing sketch stitching; cov_later=0%, on_earlier=100%, dev=3.03mm"}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 1.2}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 2.32}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 4.43}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 9.72}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 15.08}, {"file": "think-positive.dst", "kind": "trim", "gapMm": 57.16}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "trim", "gapMm": 1.32}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "trim", "gapMm": 2.98}, {"file": "enjoy-coffee-free-embroidery-design.dst", "kind": "trim", "gapMm": 5.59}, {"file": "creative-free-embroidery-design.dst", "kind": "trim", "gapMm": 2.33}, {"file": "creative-free-embroidery-design.dst", "kind": "trim", "gapMm": 4.08}, {"file": "chamomile-love.dst", "kind": "trim", "gapMm": 2.2}, {"file": "chamomile-love.dst", "kind": "trim", "gapMm": 3.39}, {"file": "chamomile-love.dst", "kind": "trim", "gapMm": 11.33}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "trim", "gapMm": 2.3}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "trim", "gapMm": 10.59}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "trim", "gapMm": 17.2}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "trim", "gapMm": 30.99}, {"file": "corgi-sketch-free-embroidery-design.dst", "kind": "trim", "gapMm": 52.36}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "trim", "gapMm": 2.44}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "trim", "gapMm": 6.03}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "trim", "gapMm": 14.61}, {"file": "teddy-bear-vintage-sketch.dst", "kind": "trim", "gapMm": 32.84}], "notes": "CORPUS TOTALS (6 files, 60,537 stitches): 211 inter-element transitions inside color blocks: 138 needle_down_link, 73 trim, 0 jump_no_trim. The 59 entries above are a gap-spread sample; full set (all 211 + per-transition metrics) in scratchpad transitions_out.json.\n\nSYSTEMATIC FINDINGS:\n1. jump_no_trim does not exist in this corpus. Every needle-up move between elements is a trim (explicit trim + typically exactly 3 jumps; 4-7 chained jumps for 30-57mm moves since DST jumps max 12.1mm). The only 1-2-jump runs without trims (6 corpus-wide) are block-start positioning moves, never inter-element travel. Between elements the choice is binary: walk needle-down or cut.\n2. No distance threshold separates link from trim - the ranges overlap completely. Links span 1.06-61.7mm gap (med 2.0, p90 13.3); trims span 1.2-57.2mm (med 4.4 lettering, 17.2 sketch). think-positive trims at 1.2mm; creative walks 61.7mm. The decider is CONCEALMENT: 127/138 links (92%) have >=60% of their path within 0.6mm of a thread sewn AFTER them (most are 100%); the other 11 (8%, all in sketch-style contexts) ride within 0.9mm of already-sewn stitching edges where they read as sketch lines. Zero links cross fabric that stays bare. Rule extracted: if a path exists that later stitching will cover (or that blends into sketch art), walk it needle-down at any length; otherwise trim - even for a 1.2mm hop.\n3. Routing split (138 links): under_later_stitching 50 (path traces geometry a later column/pass covers - visually verified: the 28.4mm enjoy-coffee link runs up the spine of a satin stroke sewn after it; the 61.7mm creative link traces the script word's connecting baseline under letters sewn after), shared-edge/baseline band 40 (hugs the common bbox edge of the two clusters, nearly all also covered later; in lettering this is the letter baseline/stem line, in chamomile flower centers just edge-hugging), under_next_element 36 (hop lands inside next element's future stitch area), along_earlier_stitching_edge 11 (exposed, follows silhouette/contour of earlier stitching - corgi's 27.6mm body-contour travel). No link classified straight-across-bare-fabric.\n4. Link anatomy: ~half are single-stitch hops (nStitches=1, gap 1.0-2.4mm) straight into the next element. Multi-stitch links use 1.5-2.5mm running stitches (corpus med 1.66, p10 1.12, p90 2.26 - slightly under the 1.5-3mm prior). Long links curve to follow the covering geometry (deviation from chord up to ~10mm over 60mm). nStitches = thread segments along link; penetrations between elements = nStitches-1.\n5. Style split: script/connected fonts (creative, chamomile-love, enjoy-coffee) barely trim inside a block (3-8 trims vs 23-38 links) - letters chain needle-down under the next stroke. Block/print lettering (think-positive) inverts: 23 trims vs 11 links, trimming even 1.2-2.3mm inter-letter gaps where a link would sit exposed between parallel satin letters. Sketch files (corgi, teddy) mix: needle-down travel along silhouettes up to 27.6mm, trims for cross-design moves (corgi trim med 17.2mm, max 52.4mm).\n6. Needle-down walks WITHIN one element (flanking clusters spatially overlapping: satin section joins, fill hops) are common - 51 corpus-wide - excluded from the counts above. Zero trims returned to the same element (trim always means departure). Zero travels with intermediate lone penetrations.\n7. Method/caveats: elements = color block split at trims/needle-up gaps, plus in-chunk splits where a sparse non-reversing run (segs >=1.05mm) bridges two clusters whose local 50mm-core bboxes overlap <0.5 - so a few links join sections/strokes of one glyph rather than whole letters (e.g. one enjoy-coffee 4.1mm mid-column hop). Sketch files' continuous run-art chains make art-vs-travel ambiguous; conservative flank rules mean links inside pure running-stitch chains are under-counted. Coverage = distance to nearest later-sewn thread SEGMENT <=0.6mm sampled on link interior points. gapMm = straight line, last penetration of A to first of B. baseline_* labels are geometric (shared-bbox-edge band), axis orientation not verified against hoop. pyembroidery synthesizes TRIM from this corpus's 3+-consecutive-jump convention (confirmed: jump-run length histogram peaks at exactly 3).\nARTIFACTS: probe scripts transition_census.py + render_links.py, full JSON transitions_out.json, and 46 link-overlay PNGs (render/) in C:\\Users\\EE-LT-~1\\AppData\\Local\\Temp\\claude\\C--Users-EE-LT-11030\\b845a108-6467-4184-b54f-1f888a276bca\\scratchpad"}


---

## Commercial auto-digitizer teardown (3 of 5 lenses)

Patent and open-source research into how market-leading auto-digitizers work internally. Missing: Wilcom patents lens, parameter-census lens, synthesis.


### Agent return 1 (15,711 chars)

Research complete. Findings below.

# Academic + adjacent-field literature for graphic-art auto-digitizing (EMB-Bot lens)

## 1. The one complete academic-grade pipeline is in expired patents: the Goldman / Soft Sight family
Soft Sight Inc. (David A. Goldman; acquired by VistaPrint 2011) patented what is essentially the full classical-CV auto-digitizer, and the core patents are expired — free pipeline documentation that maps 1:1 onto EMB-Bot's stages:

- **US6947808 "Automatically generating embroidery designs from a scanned image"** (Soft Sight, priority 1998) — pipeline: color segmentation into contiguous objects → chain-coded contours + distance-transform (DT) skeleton → **DT-statistics classifier splits objects into thin (satin) vs thick (fill)** → thin path: label junctions/end anchors, merge artifacts (serifs, bifurcations), reconstruct occluded boundaries at intersections, smooth column discontinuities, order columns to minimize trims → thick path: **test 16 candidate stitch angles, pick the one minimizing fragment count**, fragment region into continuously-sewable sub-areas, recursive traversal ordering to avoid trims. Continuations: US7016756, US7016757, US6804573, US6836695, US7587256, US8219238 (all same family, USPTO PDFs at image-ppubs.uspto.gov, e.g. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6947808). Summary verified via https://www.freepatentsonline.com/6947808.html.
- **US6397120 "User interface and method for manipulating singularities for automatic embroidery data generation"** (Goldman/Soft Sight, filed 1999, **expired 2019**, https://patents.google.com/patent/US6397120B1/en) — the deepest treatment I found of the hardest sub-problem: **junctions where stroke-like regions cross ("singularities")**. Detects them as skeletal junction nodes; enumerates *ordered interpretation sets* by pairing interfering stroke regions and reconstructing occluded boundaries via energy minimization; extracts metrics (count/direction of characteristic edge points, concavity angles, DT thickness) and **indexes past singularities in a database so accepted human corrections re-rank future interpretations**. Directly relevant to EMB-Bot's satin-spine splitting at crossings.
- Related surfaced Goldman-era items: **US6370442 "Automated embroidery stitching"** (https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6370442) [details unverified — Google Patents returned 503 repeatedly during this session], and Vistaprint follow-ons US8532810 / US9200397 ("Automatically generating embroidery designs"), US8706286 (image-suitability detection), US9163343/US9683322/US8095232/US8660683/US10047463 (printer-driver auto-digitizing family).

Other expired algorithm patents surfaced: **US5510994** (auto chain stitches) and **US5541847/US5506784** (chenille fill — builds concentric offsets from boundary toward **medial axis computed by angle-bisector rays**, i.e., a straight-skeleton-style construction), **US6587745** "Curved line fill stitching" (fill rows follow a user/auto curve, not straight lines), **US5880963** (Brother, embroidery data creating device), **US5954004** (stitch pattern per region). URLs same image-ppubs pattern with the patent number.

## 2. Medial-axis pruning that beats naive spur removal
- **Bai, Latecki, Liu, "Skeleton Pruning by Contour Partitioning with Discrete Curve Evolution," IEEE TPAMI 29(3) 2007** — prune by keeping only skeleton points whose generating contour points lie in different DCE-simplified contour segments; claim: **never produces spurious branches**, stable under heavy boundary noise. PDF: https://cis.temple.edu/~latecki/Papers/skeletonPAMI07.pdf. This is the standard replacement for spur-length thresholding.
- **Solís Montero & Lang, "Skeleton pruning by contour approximation and the integer medial axis transform," Computers & Graphics 36(5) 2012** — contour approximation + IMA; preserves connectivity/topology, robust to noise and rigid transforms. https://dl.acm.org/doi/10.1016/j.cag.2012.03.029, project http://www.solism.ca/projects/pruning.html.
- **Delta Medial Axis** (Marie, Béarée et al. 2016?) — fast filtered skeleton via a local reconstruction-error threshold delta [details unverified]: https://www.researchgate.net/publication/297727182_The_Delta_Medial_Axis_A_fast_and_robust_algorithm_for_filtered_skeleton_extraction.
- **Cosine-Pruned Medial Axis (Patiño-Cortés et al., 2021)** — DCT-smoothed shape ensemble scores branches; isometric-equivariant, noise-free MA: https://arxiv.org/pdf/2012.02910, https://dipaco.github.io/assets/pdf/papers/Patino2021_cpma.pdf.
- Design takeaway: all serious pruners score branches by **reconstruction error of the shape without the branch** (or cross-scale stability), not by branch length — EMB-Bot's satin spine extraction should adopt that criterion.

## 3. Line-drawing vectorization = the robust centerline literature (junction-correct skeletons)
This is the mature adjacent field that solved "stroke recovery from raster graphic art":
- **Noris, Hornung, Sumner, Simmons, Gross, "Topology-Driven Vectorization of Clean Line Drawings," ACM TOG 32(1) 2013** (Disney/ETH) — gradient-based pixel clustering + topology analysis to resolve junction ambiguity; centerline accuracy emphasized. https://media.disneyanimation.com/uploads/production/publication_asset/2/asset/Topology-Driven_Vectorization_of_Clean_Line_Drawings.pdf
- **Favreau, Lafarge, Bousseau, "Fidelity vs. Simplicity: a Global Approach to Line Drawing Vectorization," SIGGRAPH 2016** — global MRF selecting curves that balance fit vs curve count/degree: https://www-sop.inria.fr/reves/Basilic/2016/FLB16/
- **Bessmeltsev & Solomon, "Vectorization of Line Drawings via PolyVector Fields," ACM TOG 2018** — frame fields (PolyVector) allow **two independent directions per pixel**, so X-junctions and T-junctions get correct connectivity where naive skeletons collapse; extracts centerline-following curve network. Paper: https://arxiv.org/abs/1801.01922; **reference C++ implementation: https://github.com/bmpix/PolyVectorization**.
- **Puhachov, Neveu, Chien, Bessmeltsev, "Keypoint-Driven Line Drawing Vectorization via PolyVector Flow," SIGGRAPH Asia 2021** — learned keypoints (junction/endpoint) + "reverse drawing" to pick most likely stroke configuration, then PolyVector flow aligns curves: https://dl.acm.org/doi/10.1145/3478513.3480529.
- **Yan, Li, Aneja, Fisher, Simo-Serra, Gingold, "Deep Sketch Vectorization via Implicit Surface Extraction," SIGGRAPH 2024**: https://cragl.cs.gmu.edu/sketchvector/ (PDF on that page). Also **"End-to-End Line Drawing Vectorization" (AAAI 2022)**: https://cdn.aaai.org/ojs/20379/20379-13-24392-1-2-20220628.pdf.
- Takeaway for EMB-Bot: for run/satin extraction from line art, frame-field centerlines (PolyVectorization repo) are the current robustness ceiling; the failure mode they fix (junction topology) is exactly what makes naive medial-axis satin spines branch wrongly.

## 4. Font stroke recovery from outlines (satin lettering math, pre-solved)
- **Berio, Fol Leymarie, Asente, Echevarria, "StrokeStyles: Stroke-based Segmentation and Stylization of Fonts," ACM TOG 41(3) 2022** — training-free geometric decomposition of glyph outlines into **overlapping strokes** using medial axis + convex/concave outline features + concavity "links" + a taxonomy of **seven junction types**; works across scripts. https://dl.acm.org/doi/10.1145/3505246, open PDF https://research.gold.ac.uk/id/eprint/31944/1/strokestyles-opt.pdf. This is arguably the best published algorithm for "glyph → satin columns."
- Chinese-character stroke extraction literature (mature, directly transferable): model-based stroke extraction & matching (Liu/Kim/et al., Pattern Recognition 2001, https://www.sciencedirect.com/science/article/abs/pii/S0031320300001655); FCN-skeletonization + query-pixel-guided stroke extraction (Pattern Recognition 2022, https://www.sciencedirect.com/science/article/abs/pii/S0031320321005926); ambiguous-zone-aware skeletonization (IET Image Processing 2024, https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/ipr2.13044) — the "fuzzy/ambiguous zone at junctions, process separately, reconnect" pattern recurs and matches Goldman's singularity approach.
- Patents: **US7437384** (outline-font display via stroke centerlines + per-stroke reference data), **US6151032** (stroke-based glyph-outline font generation). Practice: single-line CNC fonts are hand-made centerline fonts (https://www.high-logic.com/font-editor/fontcreator/tutorials/how-to-make-single-line-fonts-for-engraving-and-cutting, https://github.com/isdat-type/Relief-SingleLine) — no strong academic auto-conversion paper surfaced; StrokeStyles is the closest.

## 5. Region decomposition for stitching (satin-ability + fill regions)
- **"Shape decomposition algorithm in embroidery"** (ResearchGate record 291506839; authors/venue not fully verifiable this session — likely the Zhejiang CAD&CG group) — decomposes an arbitrary region into **stroke-like sub-regions each symmetric about a poly-line axis** using a straight-skeleton variant; candidate partition lines from **fork points of the pruned skeleton**; two filters discard partitions caused by boundary noise and partitions that split a large region into two small ones. This is precisely the satin-vs-fill tiering decision. https://www.researchgate.net/publication/291506839_Shape_decomposition_algorithm_in_embroidery
- **Tănase & Veltkamp, "Polygon Decomposition Based on the Straight Line Skeleton," SoCG 2003** — principled decomposition events from straight-skeleton arcs: https://dl.acm.org/doi/10.1145/777792.777802.
- **Yang/…, "Spiral-fashion embroidery path generation in embroidery CAD systems," Computer-Aided Design 37(13) 2005** (https://www.sciencedirect.com/science/article/abs/pii/S0010448505001636, ACM mirror https://dl.acm.org/doi/10.1016/j.cad.2005.08.004) — contour-parallel spiral fill: decompose region into **ring-shaped sub-regions organized as a binary tree**, connect per-ring spirals into one continuous path (basic path + inward linking + contour-parallel linking). Template for EMB-Bot contour-fill tier.

## 6. Stitch-angle selection and fill path planning (CNC pocketing solved the same math)
- Goldman: enumerate 16 angles, minimize fragment count (Section 1).
- **Park & Choi, "Tool-path planning for direction-parallel area milling," Computer-Aided Design 32(1) 2000** — optimal sweep inclination chosen from region shape + path interval; **monotone-chain + plane-sweep** computation of path elements; then path linking. Direct analog of fill-angle + row generation: https://www.sciencedirect.com/science/article/abs/pii/S0010448599000809.
- **Arkin, Held, Smith, "An algorithm for reducing tool retractions in zigzag pocket machining"** (CAD 1997) — retraction (≙ trim/jump) minimization is NP-hard; provable approximation via region decomposition: https://www.sciencedirect.com/science/article/abs/pii/S001044859700064X.
- **Zhao et al., "Connected Fermat Spirals for Layered Fabrication," SIGGRAPH 2016** — decompose region into sub-regions each fillable by one continuous low-curvature Fermat spiral, then connect into a single global path: https://haisenzhao.github.io/CFS/index.html. Candidate for EMB-Bot's continuous curved fill without travel runs.
- **Liu Zhenyuan, Piovarči, Hafner, Charrondière, Bickel, "Directionality-Aware Design of Embroidery Patterns," Computer Graphics Forum (Eurographics) 2023** — the standout modern academic stitch-generation paper: input image + user direction field → **extract sources/sinks from the divergence field → trace streamlines → optimize for smooth, connected, machine-fabricable stitching**; explicit color-vs-direction tradeoff slider; **code: https://github.com/desmondlzy/embroidery-streamlines**; project page https://desmondlzy.me/publications/embroidery/. Best available reference for stitch-angle fields with singularity handling done via vector calculus rather than heuristics.

## 7. Sequencing / jump minimization
Academic literature is thin; practice is documented in open source: Jon Howell's inkscape-embroidery (Ink/Stitch's ancestor) explicitly uses a **greedy TSP + hill-climbing patch ordering** (http://www.jonh.net/~jonh/inkscape-embroidery/); Ink/Stitch routing docs: https://inkstitch.org/tutorials/routing/, auto-route satin design discussion (graph of satin columns, Eulerian-path-style traversal with running-stitch travel): https://github.com/inkstitch/inkstitch/issues/214. Arkin/Held (above) is the rigorous anchor. Treat sequencing as: build adjacency/containment graph, Eulerize with travel runs, then TSP-order connected components.

## 8. 2015–2026 ML on vector-art-to-stitch: appearance only — a real gap
- **Beg & Yu, "Generating Embroidery Patterns Using Image-to-Image Translation," arXiv 2003.02909 (2020)** — style transfer/CycleGAN; outputs embroidery-look **images**, not stitches: https://arxiv.org/abs/2003.02909.
- **Hu, Yang, Fang, Huang, Li, Sheng, Lee, "MSEmbGAN: Multi-Stitch Embroidery Synthesis via Region-Aware Texture Generation," IEEE TVCG 2024** (Wuhan Textile Univ. + NCKU) — region-aware stitch-type classifier (satin/random/cross?) + per-region texture GAN + dataset; again **pixels, not needle points**. https://ieeexplore.ieee.org/document/10643390/, paper PDF http://graphics.csie.ncku.edu.tw/TVCG_MSEmbGAN/MSEmbGAN_paper.pdf, dataset https://hyper.ai/en/datasets/34570.
- One-shot embroidery customization via contrastive LoRA modulation (arXiv 2509.18948, 2025) — diffusion appearance: https://arxiv.org/abs/2509.18948.
- Random-needle series (Zhou et al.: FITEE 2015 controllable stitch layout https://link.springer.com/article/10.1631/jzus.C1400099; StitchGeneration Markov-chain MTAP 2019 https://link.springer.com/article/10.1007/s11042-019-08053-7; multilayered stitch generating 2021 https://www.researchgate.net/publication/352834945) do emit real stitch layouts but target artistic photo-embroidery (parallel effort's territory).
- **Conclusion: no published 2015–2026 ML system emits machine-ready stitch coordinates from graphic vector art.** The learning-augmented classical pipeline (Puhachov's learned keypoints feeding geometric optimization; Goldman's indexed-singularity corrections) is the only demonstrated pattern. EMB-Bot's classical + corpus-constants approach matches the state of the art; the useful ML slot is junction/keypoint detection and stitch-type classification, not end-to-end generation.

## 9. Reference implementations worth reading
- **Ink/Stitch** (https://inkstitch.org, satin docs https://inkstitch.org/docs/satin-tools/, https://inkstitch.org/docs/stitches/satin-column/) — production-grade Python: auto-fill row-graph traversal, auto-satin from paired rails/rungs, routing.
- **PEmbroider** (CMU Studio for Creative Inquiry, https://github.com/CreativeInquiry/PEmbroider) — many fill/hatch algorithms, modified-TSP path ordering, multi-format writers.
- **PolyVectorization** (https://github.com/bmpix/PolyVectorization) and **embroidery-streamlines** (https://github.com/desmondlzy/embroidery-streamlines) — the two research codebases most directly liftable.
- **Chen, McCool, Kitamoto, Mann, "Embroidery modeling and rendering," Graphics Interface 2012** — auto layout of long-short/satin/stem stitches **from line drawings**: https://graphicsinterface.org/proceedings/gi2012/gi2012-17/.

Unverified items flagged: US6370442 contents; "Shape decomposition algorithm in embroidery" authorship/venue; Delta Medial Axis author list; exact expiry dates of the US6947808 continuations (priority 1998 implies the whole family is now expired, but per-patent term adjustments were not checked).


### Agent return 2 (18,075 chars)

# Auto-Digitizer Patent Intelligence: How Commercial Systems Work Inside

Verification legend: **[V]** = full patent text fetched and read; **[P]** = verified via search-result snippets only, not full text; **[U]** = lead only, unverified.

---

## 1. The Soft Sight / Vistaprint family — the most complete expired documentation of a full auto-digitizing pipeline

This is the closest thing to free source-level documentation of a commercial "image in, stitches out" engine that exists. Original assignee Soft Sight Inc (later Vistaprint/Cimpress). Directly parallel to EMB-Bot's pipeline stage-for-stage.

### US6804573B2 — "Automatically generating embroidery designs from a scanned image" **[V]**
https://patents.google.com/patent/US6804573 — filed 2001-09-10, granted 2004-10-12, **expired 2018-12-03**. Free to use.

Pipeline (mirrors EMB-Bot's quantize→segment→vectorize→tier→sequence):

- **Input/quantize:** 24-bit color, 300 DPI. Selective smoothing kills salt-and-pepper noise while preserving edges: low-contrast areas get weighted-average smoothing, high-contrast areas untouched. Segmentation by region growing seeded at low-contrast points, expanding to similar-color neighbors; unclassified pixels merged into adjacent objects by proximity + color similarity. **Objects < 6 pixels discarded as noise.**
- **Vectorize:** single-pass raster scan emits 8-direction chain codes for every contour; simultaneously computes a **(3,4) chamfer distance transform** on interior pixels (normalize DT by dividing by 3 to get approximate pixel distance to boundary).
- **Satin-vs-fill decision (thin-region detection):** compute skeleton pixel DT statistics — max, mean μ, stddev σ. **Classified thin/regular if σ < 0.5·μ** (constant thickness ⇒ low variance); else thick. Thin ⇒ satin columns; thick ⇒ fill rows.
- **Thin-object (satin) pipeline:** (1) polygon fit contours via triangular filtering (drop vertices below height threshold); (2) label skeleton: degree-1 nodes = end anchors, junction nodes = junction anchors; (3) localize end anchors by extending skeleton ends and searching contour for acute vertices (**~30° threshold**) within a distance proportional to local thickness (DT value); (4) merge serif-like features (degree-3 node with two short terminating branches) via hard-coded rules (empirical constant 10 in bifurcation heuristics); (5) reconstruct occluded boundaries at junctions via **energy minimization**, pair left/right contours with stroke normals orthogonal to the skeleton; (6) smooth consecutive stroke normals; **split the region wherever bend angle < 45°**; (7) generate stitch path by recursive skeleton-branch traversal minimizing thread cuts — measures "interruption magnitude" (combined length of intermediate columns) and regenerates paths to minimize it.
- **Thick-object (fill) pipeline:** test **16 candidate stitch angles**, pick the one producing the fewest fragments; a **modified scan-line fill** partitions the region into maximal single-angle sewable fragments; recursive traversal from the exit region orders fragments to minimize/eliminate trims; entry/exit points are chosen on exterior contours.
- Output: x,y stitches + control points (satin columns / fill rows) + entry/exit + angles.

### US6397120B1 — "User interface and method for manipulating singularities" **[V]**
https://patents.google.com/patent/US6397120 — filed 1999-12-30, granted 2002-05-28, **expired 2019-12-30**.

"Singularity" = junction area where multiple constant-thickness regions converge and boundary continuity is lost (the hard part of skeleton-based satin). The Singularity Processing Mechanism generates **ranked interpretation sets** by examining directional vectors from skeleton nodes to characteristic edge points, computing angular differences and occluded-boundary reconstructions via energy minimization; a one-click UI cycles interpretations; user corrections are stored in a structurally-indexed database to reprioritize similar future singularities (a learned prior — directly analogous to EMB-Bot's corpus-measured constants). Satin columns derived as stroke normals at skeleton-contour intersections, smoothed to remove normal-to-normal discontinuity.

### Family continuations **[P]**
US7016756B2 (granted 2006, same mechanisms — stitch-angle determination "minimizes needle repositioning", fragment = maximal area fillable at one angle in one operation): https://patents.google.com/patent/US7016756. Later: US6836695, US7587256 (2009), US8219238, US8532810, US9200397 (2015, Vistaprint "Automatically generating embroidery designs"): https://patents.google.com/patent/US9200397 — later members may still be in force; check before copying claims verbatim (not necessary anyway — you're reimplementing ideas, and the core family is expired). Related: US8095232B2 "Printer driver systems... automatic generation of embroidery designs" **[P]** (line segments → polygons → control points → stitch endpoints → any machine format): https://patents.google.com/patent/US8095232.

---

## 2. Brother Industries — thin/thick decision and image→data patents (1990s, expired)

### US5563795A — "Embroidery stitch data producing apparatus and method" **[V]**
https://patents.google.com/patent/US5563795 — Brother; filed 1995-04-06, granted 1996-10-08, **expired 2008 (fee-related)**. Inventors Futamura/Muto/Mizuno.

The cheapest published satin-vs-outline-stitch classifier — much simpler than Soft Sight's:
1. Binary scan → bitmap. 2. Border-trace connected black regions → outline pixel chain. 3. **Linearization test:** iteratively erode outer pixels toward a 1-px centerline, **capped at N cycles (example N=3)**.
- Embodiment 1: if region fully thins within N cycles ⇒ it's a line ⇒ **zigzag stitches along the extracted centerline** (uniform width regardless of sloppy input line width); if not ⇒ it has real area ⇒ **satin stitches over the border-line region**.
- Embodiment 2: same decision via distance transform — **if max DT value ≤ threshold (example 3 px) ⇒ linear ⇒ zigzag on centerline; if > threshold ⇒ satin fill**.
This is an erosion-count / DT-max threshold classifier: for EMB-Bot, this validates a corpus-tunable "max centerline depth" constant as the entire thin-region detector.

### US5751583A — "Embroidery data processing method" **[P]**
https://patents.google.com/patent/US5751583A — Brother, granted 1998-05-12 (Futamura, Kyuno, Mizuno, Muto). From snippets: image reader produces image data; a first device produces **outline sewing data** (stitches along region outlines) and a second produces **area sewing data** (stitches filling the interior) — i.e., Brother patented the fill+border two-pass structure per region. Full text not retrieved (Google Patents 503'd repeatedly); worth a re-fetch. Expired by age (filed mid-1990s) — **[U]** on exact date.

### US5299514 — "Process and apparatus for producing underlying stitch sewing data" **[P]**
PDF: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5299514 — filed 1990-10-23. Automatic **underlay generation** from a region. A citing patent (US5823127) reveals a key edge case: when the contracted (offset-inward) underlay outline self-intersects, **split the underlay area into segmental areas and generate underlay data per segment**. Assignee and full algorithm unverified — expired by age regardless (pre-1995 filing ⇒ 17-years-from-grant regime, long dead). High-value re-fetch target for EMB-Bot's missing underlay stage.

### US8473090B2 — "Embroidery data creation apparatus" (photo → line-segment stitches) **[V]**
https://patents.google.com/patent/US8473090B2/en — Brother; filed 2011-10-31, granted 2013-06-25, **status: Expired–Fee Related** (lapsed for non-payment; nominal term ran to 2032 — since it lapsed, it's free unless revived; verify current status before relying on this).

Brother's photo-stitch color-separation machinery:
- Split image into **Area 1 (gradual color change)** and **Area 2 (high-frequency / abrupt edges)**.
- Area 1: **median-cut color reduction into m partitions**; per-pixel compute an **angle characteristic** = direction of maximum color continuity + a strength magnitude; per color area compute a **representative angle** (strength-weighted average); lay **equally-spaced parallel line segments at the representative angle**, endpoints clipped to the color-area boundary; map each area's representative color to the **nearest available thread color in RGB distance**; chain same-color segments by **nearest-endpoint routing** into continuous runs.
- Area 2: short per-pixel segments oriented by local angle characteristic, colored by local reference-area average (detail/edge pass).
- Sequence: Area 1 (fills) sewn before Area 2 (details). Second embodiment merges adjacent color areas sharing a representative angle to cut thread-color count.

### Other Brother leads **[U]**
- US5520126 (mat-type stitches, 1995): blocks + stitch order, then **checks whether terminal ends of consecutive blocks are adjacent** — entry/exit continuity enforcement. https://patents.google.com/patent/US5520126
- US5227976 / US5255198 (1992-93): dividing a closed outline's interior into **quadrangular/triangular blocks** (triangles as degenerate quads), stitch data per block — the classical "block punching" fill representation.
- US5927220 (contour extraction *from stitch data* — inverse problem): https://patents.google.com/patent/US5927220
- US5592891 (embroidery data processing apparatus/product): https://patents.google.com/patent/US5592891
- US6247420 "Method of recognizing embroidery outline and conversion to a different data format": PDF https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6247420

---

## 3. Pulse Microsystems — the Tajima DG lens

Tajima itself (Tokai Industrial Sewing Machine) surfaced **no English-language auto-digitizing algorithm patents** in searches — Tajima's digitizing software (DG/ML by Pulse, now Tajima DG16) is written by **Pulse Microsystems**, so Pulse's portfolio *is* the Tajima-software lens. Tajima's own patents are machine-hardware side.

### US5343401A — "Embroidery design system" **[V]**
https://patents.google.com/patent/US5343401A/en — Pulse Microsystems; filed 1992-09-17, granted 1994-08-30, **expired 2012-10-29**.

The foundational **outline-format** patent: convert stitch-level NC codes into a condensed hierarchical outline format (points → segments unified by stitch type → groups), edit at outline level, regenerate stitches. Stitch engines: line types (Run, 2-Ply, **Bean = 3 passes per stitch**, Manual, NeedleUp); region types (Satin/Curved Satin with **automatic jump insertion when a column exceeds max stitch length**; Tatami/Curved Tatami with **offset patterns expressed as percentage of stitch length, optionally randomized** — this is the fill split-line pattern; "Boot" parallel-run fill). **Density stored as mm between adjacent stitches; pull compensation as a percentage applied to satins and tatamis** — regenerated at output time, not baked in. Three-reference-point calibration for scaling/alignment. This is the architecture argument for EMB-Bot keeping plan-level (outline) IR separate from stitch emission.

### US5510994A — "Method for automatically generating chain stitches" **[P]**
https://patents.google.com/patent/US5510994 — Pulse; filed 1994-10-14, granted 1996-04-23, expired ~2014. Complex polygon → **medial axis → construct and sort concentric (offset) polygons → place stitches along their perimeters** to fill.

### US5541847A — "...chenille filled embroidery stitch pattern" **[P]**
https://patents.google.com/patent/US5541847 — Pulse; filed 1995-09-11, granted 1996-07-30, expired. Uses the **spine of the medial axis of the Voronoi diagram**; concentric polygons **clipped within a clip-width of the spine**; **spirals** placed along modified polygons, stitches along spirals "to minimize bald spots." Continuation: US5771173 (Divinsky) **[U]**. Together these document Pulse's core geometric machinery: Voronoi/medial-axis + offset-polygon families — the same math EMB-Bot needs for spiral/contour fills and corridor detection.

### US6968255B1 — stippling **[P]**
https://patents.google.com/patent/US6968255 — Pulse, granted 2005: fractal-based pathway defined in a symmetric boundary, **conformed to an arbitrary polygon**, emitted as run stitching (meander/stipple fill). Status unverified — likely expired 2023-2025 window; check.

---

## 4. Melco — modern parameter-automation layer (mostly still ACTIVE — ideas only, do not copy claims)

### US8851001B2 — "Method for improved stitch generation" **[V]** — **ACTIVE until ~2032-09-23. Not free documentation; treat as competitive insight only.**
https://patents.google.com/patent/US8851001 — Melco International; filed 2009-01-16, granted 2014-10-07.

What it reveals about commercial practice (facts, not claim language, are unprotectable):
- **Measurement-first stitch selection:** generate temporary stitches, measure element width via average/median/**70th-percentile** stitch width, then look up stitch type in a **size→type chart**: satin for **0–60 points** (1 pt = 0.1 mm, so ≤6 mm), step-fill above 60 pt; underlay chart maps size→{center walk, edge walk, zigzag, fill} modulated by fabric type. EMB-Bot's corpus-measured constants are exactly this chart.
- **Continuous underlay via graph theory:** proximate elements → graph (elements = vertices, shortest connectors = edges, connectors over threshold deleted), **duplicate every edge to force even degree, run an Euler tour**, stitch the underlay as one unbroken traversal (BFS/DFS/Dijkstra cited as substitutes).
- **Push compensation** (the perpendicular twin of pull-comp): end width = avg of last 5 / median of last 10 stitches; table indexed by width × fabric: **0–20 pt → −4 pt, 20–35 → −5, 35–50 → −6, 50+ → −7**; skipped when the element end intersects another element; applied by deleting stitches or shifting coordinates.
- **Lock stitches** stored at fixed digitized size, immune to design scaling.

### EP1102881A1 — "Automated embroidery stitching" (AutoStitch) **[P]**
https://patents.google.com/patent/EP1102881A1/en — Melco's 1999-era auto-digitizing application (text/image/scanner/CAD input, automatic outline calculation). Could not fetch full text (rate-limited); EP application from 1999 is expired/lapsed as a patent right. US sibling: US6983192 "Computerized stitching including embroidering" (granted 2006) **[U]**: https://patents.justia.com/patent/6983192.

---

## 5. Bernina/OESD — negative result **[P]**

No in-house auto-digitizing algorithm patents surfaced. BERNINA Embroidery Software (incl. auto-digitize) is an OEM of **Wilcom** (Australia); OESD is a Bernina design-house subsidiary, not an algorithm shop. If you want that lens, the search target is "Wilcom Pty Ltd" / "Wilcom International" as assignee — not covered in this pass.

---

## 6. Direct takeaways for EMB-Bot's pipeline

1. **Thin-region detector, two independent expired formulations:** Brother's max-DT ≤ 3 px / erosion-cycles ≤ 3 (US5563795) and Soft Sight's skeleton-DT σ < 0.5·μ (US6804573). Melco confirms the commercial satin/fill width boundary sits at ~6 mm. All three converge: a corpus-tuned DT-statistic threshold is the industry answer.
2. **Fill angle selection = fragment minimization:** try 16 angles, keep the one that yields fewest scan-line fragments (US6804573/7016756) — cheap, classical-CV, and directly implementable in the fill tier.
3. **Entry/exit + sequencing:** recursive traversal ordered backwards from the desired exit region, minimizing "interruption magnitude"; entry/exit constrained to exterior contours (US6804573). Block-terminal adjacency check (US5520126).
4. **Junction handling for satin (the branch problem):** energy-minimized occluded-boundary reconstruction + ranked interpretations + learned reprioritization (US6397120) — expired and describes exactly the hard corner of skeleton-based satin.
5. **Underlay stage (currently absent from EMB-Bot's stage list):** US5299514 (offset-inward with self-intersection splitting) is the expired starting point; Euler-tour continuous underlay is Melco's active-patent territory — implement the 1990 approach, not the 2009 one.
6. **Pull/push comp:** percentage-based pull comp at regeneration time (Pulse US5343401, expired); width-indexed push-comp end tables are claimed in an active Melco patent — if EMB-Bot adds push comp, derive its own corpus constants and mechanism.
7. **Color separation:** median-cut + per-region representative stitch angle from a color-continuity tensor + nearest-thread RGB mapping + nearest-endpoint chaining (Brother US8473090, lapsed fee-related — verify non-revival).

**Retry queue (Google Patents 503'd; re-fetch later):** US5751583A full text, US5299514 full text, US5592891, US5227976/US5255198, EP1102881A1 full text, US6247420, Wilcom assignee sweep.

Sources: [US6804573](https://patents.google.com/patent/US6804573), [US6397120](https://patents.google.com/patent/US6397120), [US7016756](https://patents.google.com/patent/US7016756), [US9200397](https://patents.google.com/patent/US9200397), [US8095232](https://patents.google.com/patent/US8095232), [US5563795](https://patents.google.com/patent/US5563795), [US5751583](https://patents.google.com/patent/US5751583A), [US5299514 PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5299514), [US8473090](https://patents.google.com/patent/US8473090B2/en), [US5520126](https://patents.google.com/patent/US5520126), [US5927220](https://patents.google.com/patent/US5927220), [US5343401](https://patents.google.com/patent/US5343401A/en), [US5510994](https://patents.google.com/patent/US5510994), [US5541847](https://patents.google.com/patent/US5541847), [US6968255](https://patents.google.com/patent/US6968255), [US8851001](https://patents.google.com/patent/US8851001), [EP1102881A1](https://patents.google.com/patent/EP1102881A1/en), [US6983192](https://patents.justia.com/patent/6983192), [US6247420 PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6247420)


### Agent return 3 (16,467 chars)

# Open-Source Auto-Digitizer Internals — Research Writeup

**Licensing ground rule stated up front:** Ink/Stitch is GPL-3.0. Everything below describes METHOD (algorithms, graph constructions, constants, parameter semantics) learned by reading docs and source as literature. No code may be copied, translated line-by-line, or derivative-ported into EMB-Bot. Same applies to PEmbroider, which — contrary to the task brief calling it "permissive" — is actually **GPLv3 + Anti-Capitalist Software License v1.4**, with an explicit prohibition on using it to build commercial embroidery software ([github.com/CreativeInquiry/PEmbroider](https://github.com/CreativeInquiry/PEmbroider)). Treat it as method-study-only too. Note: local clone `C:\Users\EE-LT-11030\EMB-Bot\scratch_ink` is the Ink/Stitch FONT repo (letterforms only); all findings below come from the main `inkstitch/inkstitch` GitHub repo and inkstitch.org, fetched fresh.

---

## 1. Ink/Stitch — the deepest free reference implementation

### 1.1 Fill routing (modern "tatami" auto-fill) — `lib/stitches/tatami_fill.py`
Read from source (single-source, unverified against runtime, but consistent with docs):

- **Grating:** shape ∩ family of parallel lines at fill angle/spacing produces row segments (`intersect_region_with_grating` lineage from legacy `fill.py`).
- **Fill-stitch graph (`build_fill_stitch_graph`):** nodes = points where grating segments meet the shape outline (outer boundary and holes). Edges = (a) the grating segments themselves (key `"segment"`), (b) outline sections between adjacent nodes, (c) **duplicates of every other outline section**. This doubling makes every node degree-4 (even), which **guarantees an Eulerian path exists** — that is the core trick. Validated with `networkx.is_eulerian()`; if invalid, `networkx.eulerize()` duplicates edges to fix parity.
- **Path finding (`find_stitch_path`):** adapted **Hierholzer's algorithm** with a vertex stack, terminating once every *segment* edge is visited (outline edges need not all be used). `pick_edge()` prefers segment edges over outline edges, producing long back-and-forth row runs.
- **Travel/underpath graph (`build_travel_graph`, `build_travel_edges`):** separate graph for moving between sections. With underpath enabled, an interior cross-hatch of three gratings at fill-angle ±45° and −90° is added. **Edge weighting:** boundary edges get a 3× length penalty; interior edges get a bonus inversely proportional to distance from the outline — so travel runs through the shape's center where it gets covered by later stitching. Travel = `networkx.shortest_path(weight='weight')`, then smoothed and clamped inside the shape. Raises `NoGratingsError` for too-small shapes; `fallback()` = running-stitch perimeter.
- **Gap repair (`fill_gaps`):** where travel interrupts back-and-forth rows, the last row is repeated offset by row spacing an even number of times (`round_to_multiple_of_2`) to close visible density gaps.
- **Start/end (`insert_node`):** user start/end points are projected onto the outline and spliced into the graph by splitting outline edges.
- **Stagger:** phase-based row offset, `num_staggers` rows before the pattern repeats; **fractional stagger cycles supported** (v3.0) and produce less-visible diagonals than integers ([inkstitch.org/docs/stitches/fill-stitch/](https://inkstitch.org/docs/stitches/fill-stitch/)).
- **Other fill parameters** (same doc page): default underlay = on, 90° offset from top-stitch angle, wider spacing, own inset (negative inset ⇒ knockdown effects); multiple underlay layers via space-separated angle list; pull comp as fixed mm AND percentage, asymmetric via space-separated pair; "expand"; min-stitch-length culling.

### 1.2 Auto-satin routing — `lib/stitches/auto_satin.py` + `lib/stitches/utils/autoroute.py`
Read from source (unverified constants flagged):

- Satin columns are **chopped into ~1 mm segments**; nodes = segment endpoints (stringified coords, since Shapely points aren't hashable); edges carry the segment object.
- Shared `autoroute.py` algorithm: (1) **Dijkstra shortest backbone path** start→end; (2) **DFS from each backbone node** to sweep branches; (3) **on backtrack, edges are traversed bidirectionally — the second pass becomes running-stitch underpathing** that later satin covers. Segments hit twice in pathfinding are demoted to running stitch to avoid double-sewing satin.
- Sequential surviving segments are re-merged (`collapse_sequential_segments`); re-routed satins **retain all original params** (underlay, zigzag spacing).
- **Jumps between disconnected components:** ordered mode connects sequentially preserving XML order; unordered mode uses **`networkx.k_edge_augmentation`** over Euclidean-weighted candidate jumps to find the minimal-weight connection set — a clean, principled answer to "connect N islands with minimal jump length."
- `preserve_order=True` switches to a DiGraph with explicit reverse edges: order kept, but satins may still be split/rearranged internally.
- Defaults: start = leftmost extreme, end = rightmost; overridable by marker commands ([inkstitch.org/docs/satin-tools/](https://inkstitch.org/docs/satin-tools/), PR [#330](https://github.com/inkstitch/inkstitch/pull/330)).
- **Satin underlay** (docs): three kinds usable simultaneously — center-walk (down-and-back run), contour (edge walk), zigzag; odd repeat counts reverse direction so column starts/ends at same point ([inkstitch.org/docs/stitches/satin-column/](https://inkstitch.org/docs/stitches/satin-column/)).

### 1.3 Other generation modules worth stealing methods from
- **Contour fill** (`contour_fill.py`): Shapely `offset_curve` rings → containment tree in `networkx.DiGraph` → inner-to-outer DFS joining parent/child rings at nearest entry points (thresholds 1.5× and 2.05× the offset — unverified constants); **single spiral** built by resampling consecutive rings to equal point counts and linearly blending; **double spiral** from alternating rings forward+reversed.
- **Meander fill** (`meander_fill.py`): tile pattern → connectivity graph → initial shortest path → **iterative edge replacement with longer detour paths** (edge paths ≤ length 7, edge-pair paths ≤ 10; seeded RNG) until space is consumed; disconnected bits attached via minimum edge augmentation; then smoothing, optional perpendicular zigzag offsetting, bean repeats.
- **Redwork extension** (v3.1): reorders running stitch so **every path is stitched exactly twice** — doubling every edge makes the multigraph Eulerian by construction, guaranteeing one continuous no-jump circuit ([inkstitch.org/docs/stroke-tools/](https://inkstitch.org/docs/stroke-tools/)). Cheap, bulletproof trick for our run tier.
- **Autoroute Running Stitch:** same autoroute core; can add nodes at intersections; trim-instead-of-jump option.
- **Fill to Stroke:** centerline extraction from fill shapes (comparable to centerline tracing, with optional cut lines at intersections) — exactly the "narrow region → demote fill to run/satin spine" primitive our tier classifier wants.
- **Auto sequencing default** (since v3.2.1): each fill/satin auto-picks start/end as **closest points to previous/next element** ([inkstitch.org/en/2025-06-07-3.2.1](https://inkstitch.org/en/2025-06-07-3.2.1)).

### 1.4 Release trajectory 2023–2026 (auto-digitizing-relevant)
- **v3.0.0, 2023-05-26** ([inkstitch.org/en/2023-05-26-v3.0.0](https://inkstitch.org/en/2023-05-26-v3.0.0)): meander fill, circular/spiral fill with target-point centers, satin randomization (length/spacing/split), pull comp in mm+% and asymmetric, auto-detection of reversed rails, stitch-plan caching for speed.
- **v3.1.0, 2024-07-27** ([inkstitch.org/en/2024-07-27-v3.1.0](https://inkstitch.org/en/2024-07-27-v3.1.0)): linear-gradient fill, tartan fill, S-stitch and zigzag satin variants, split-stitch stagger, **smooth underpath**, "prevent fill going outside shape", **proportional pull compensation**, Redwork, multicolor satin, nearest-thread-palette recolor extension.
- **v3.2.x, 2025**: font/lettering focus (RTL fonts, batch lettering), closest-point auto start/end routing.
- **v3.3.0, 2026-07-31** ([inkstitch.org/en/2026-07-31-v3.3.0](https://inkstitch.org/en/2026-07-31-v3.3.0)): cross-stitch fill + Cross Stitch Assistant (images/charts → crosses), plain strokes >1 mm usable directly as satin columns, multiple short-stitch insets, **push compensation (shortens satin at specified ends — the complement to pull comp; we should have both)**, guided-fill buffer strategy tolerating self-intersecting guide paths, knockdown fill stitch-length control, break-apart size threshold.
- Notable absence: **Ink/Stitch still has no raster auto-digitizer** — input is hand-drawn vectors; the "auto" is per-element stitch generation + routing, not image→design.

### 1.5 What its issue tracker says users hate
- Auto-route satin fragility: crashes (`NoneType.getparent` [#2328](https://github.com/inkstitch/inkstitch/issues/2328); closed-path failure [#1173](https://github.com/inkstitch/inkstitch/issues/1173); `Polygon.geoms` [#623](https://github.com/inkstitch/inkstitch/issues/623); v3.2.1 error [#4144](https://github.com/inkstitch/inkstitch/issues/4144)), unit/transform scaling bugs ([#376](https://github.com/inkstitch/inkstitch/issues/376)), and **over-fragmentation — unwanted satin cuts and jump stitches on simple shapes** ([#1439](https://github.com/inkstitch/inkstitch/issues/1439)).
- Fill routing opacity: no user control of subpath order ([discussion #2503](https://github.com/inkstitch/inkstitch/discussions/2503)); no continuous Eulerian routing for motif/pattern stitching even when one exists ([#1383](https://github.com/inkstitch/inkstitch/issues/1383)).
- Performance: params dialog freezes 14–15 min on designs >~11k stitches ([#474](https://github.com/inkstitch/inkstitch/issues/474), [#546](https://github.com/inkstitch/inkstitch/issues/546)) — Python + full re-render per tweak. EMB-Bot lesson: incremental/cached per-element regeneration is a competitive feature, not a nicety.

---

## 2. libembroidery / Embroidermodder — generation side
Strength is **format I/O breadth**, not generation. Its own docs describe satin as "sweepable zig-zag fill with turn corrections" and a planned fill class (zig-zag, Z, E, parallel-line fills with underpathing connecting non-monotone polygon parts), but the tracker admits **satin fill methods are planned, not implemented** ([libembroidery #137](https://github.com/Embroidermodder/libembroidery/issues/137); docs at [libembroidery.org/docs](https://www.libembroidery.org/docs/index.html)). Recommended programmatic route is their CSV stitch format. Verdict: nothing to learn for our generation stages; possibly useful later as a C reference for exotic format writers.

---

## 3. PEmbroider (Processing / Java) — method notes
([github.com/CreativeInquiry/PEmbroider](https://github.com/CreativeInquiry/PEmbroider), cheat sheet [PEmbroider_Cheat_Sheet.md](https://github.com/CreativeInquiry/PEmbroider/blob/master/PEmbroider_Cheat_Sheet.md)) — **GPLv3+ACSL, not permissive; method study only.**
- Hatch modes: CONCENTRIC / PARALLEL / SATIN ("really solid" per their own docs), SPIRAL / PERLIN / CROSS (admitted buggy). Stroke modes TANGENT vs PERPENDICULAR; `strokeLocation` inside/center/outside (−1..1 float).
- **`setStitch(minLength, desiredLength, noise)` — deliberate random jitter of stitch length to dither needle penetrations.** Cheap anti-moiré/anti-perforation trick we don't have; maps directly onto our fill sampler.
- `beginRepeatEnd/endRepeatEnd` tie knots; render-order control (stroke-over-fill vs fill-over-stroke).
- `optimize()` = modified **TSP solver over stitch-block connection order**, self-described "VERY SLOW" but "essential". Confirms: block-order TSP matters, and doing it naively is the known pain point.
- No underlay, no pull/push comp, no density-by-fabric logic — it's a generative-art tool, not a production digitizer (assessment, not cited).

---

## 4. Turtlestitch
Snap!-based educational tool: turtle pen path → running stitch (plus a small set of stitch-type blocks), exports machine formats; density/stitch-size sanity range users cite is ~8–12 units ([edutechwiki.unige.ch/en/Turtlestitch](https://edutechwiki.unige.ch/en/Turtlestitch), [turtlestitch.org](https://www.turtlestitch.org/page/whatsnew/)). No shape fill, no auto-digitizing, no comp. Not relevant to our pipeline beyond test-corpus generation.

---

## 5. PyPI / small Python libraries
- **pyembroidery** (EmbroidePy) — the de-facto Python format I/O layer (reads/writes DST/PES/JEF/EXP/…, 1/10 mm units); originally written for Ink/Stitch ([github.com/EmbroidePy/pyembroidery](https://github.com/EmbroidePy/pyembroidery)). Ink/Stitch now maintains its own fork **pystitch** ([github.com/inkstitch/pystitch](https://github.com/inkstitch/pystitch), [pypi pystitch](https://libraries.io/pypi/pystitch)) — worth diffing against our DST codec re: the known axis/bit-table discrepancy.
- **stitch-generator** (bastanja, v0.1.0 Jan 2023, ~7 stars, license listed "Other" — check before even method-citing in docs): path+width model with composable "stitch effects" producing numpy mm arrays; satin/meander/motif/decorative chains; delegates file I/O to pyembroidery ([libraries.io/pypi/stitch-generator](https://libraries.io/pypi/stitch-generator), [github.com/bastanja/stitch_generator](https://github.com/bastanja/stitch_generator)). The "effects as pure functions over (path, width) → points" architecture is a tidy pattern for our motif tier.
- **python-embroidery** (CatherineH, unmaintained, license unverified): `digitizer.py` is a full toy pipeline — potrace raster→vector, then selectable fills: scan-line zigzag (default), grid, **Voronoi-based medial-axis spine**, polygon decomposition into triangles/trapezoids; satin faked as perpendicular offset duplicates; block ordering by nearest-start; trims/color-changes inserted between color blocks ([github.com/CatherineH/python-embroidery/blob/master/digitizer.py](https://github.com/CatherineH/python-embroidery/blob/master/digitizer.py)). Closest existing thing to EMB-Bot's ambition in Python; quality reportedly far below commercial (assessment).

---

## 6. Techniques we lack — concrete adoption candidates (method-level, re-implement from scratch)
1. **Eulerian-guaranteed fill routing:** duplicate every other boundary section so all nodes are degree-4, then Hierholzer terminating at full segment coverage. Replaces heuristic row-chaining in our fill tier; zero-jump fills of arbitrary multiply-connected regions.
2. **Weighted interior travel graph** (±45°/−90° cross-grating, 3× boundary penalty, center-distance bonus) for underpath travel — slots between our overlap/pull-comp and sequencing stages.
3. **Satin chain routing:** 1 mm segmentation + Dijkstra backbone + DFS with bidirectional backtrack (second pass = underpath run), `k_edge_augmentation` for minimal jump sets, preserve-order as DiGraph variant. Directly addresses branching-letterform satin (our lettering pain).
4. **Redwork double-pass Eulerization** for the run/border tier: guaranteed single continuous path, trivially correct.
5. **Fill-to-stroke centerline extraction** for narrow-region demotion (fill→satin/run tier reassignment).
6. **Push compensation** (shorten satin at ends) alongside pull comp — Ink/Stitch only got this in v3.3.0 (July 2026); commercial parity item.
7. **Fractional stagger cycles** and **gap-fill row repetition** (even-count offset repeats after travel interruptions).
8. **Stitch-length noise dithering** (PEmbroider `setStitch` noise) against needle-hole banding.
9. **Closest-point auto start/end chaining** between consecutive elements as the sequencing default.
10. **Meander via detour-expansion on a tile graph** and **contour-tree spirals** as low-stitch-count fill styles (differentiators for large areas).

**Verification status:** Ink/Stitch parameter/tool behavior cross-checked between docs and release notes (high confidence). Algorithm internals come from single-pass source reads via summarizer (function names and structures high confidence; specific numeric constants — 1.5×/2.05× contour thresholds, 3× boundary weight, meander path-length caps 7/10, 1 mm satin segmentation — **unverified, re-read source before relying on them**). PEmbroider TSP claim is from its own README (unbenchmarked). stitch-generator and python-embroidery licenses unverified.


---

## Corpus round 3 (2 of 6 dimensions)

Further law extraction from the 36-file corpus. Missing: density scaling, color sequencing, entry/exit, overlaps. Synthesis never ran.


### Agent return 1 (5,686 chars)

All measurements complete. Final answer follows.

FILL ANGLE CENSUS — 36 corpus DSTs + 4 commissioned (40 files, dedup'd: the two Duplicates/HOTEL FREMONT are byte-identical, "(2)" differs)

INSTRUMENT (C:\Users\EE-LT-~1\AppData\Local\Temp\claude\C--Users-EE-LT-11030\b845a108-6467-4184-b54f-1f888a276bca\scratchpad\fill_angle_probe.py + fill_angle_agg.py, fill_angle_deep.py, xval.py)
- Per needle-down run: length-weighted doubled-angle (axial) mean of segments >=1.2mm, refined after dropping segments >25 deg off axis (kills underlay-walk contamination); rows split on along-axis sign flips; accept as tatami only if rows>=6, row-gap in [0.55, 2.0]mm, coherence>=0.75, stitch med>=1.5mm, and NOT (<=2 penetrations/row AND <8mm along rows) — that last guard is the split-satin trap filter.
- Validation: synthetic tatami at 0/30/45/72/117.5 deg with perimeter-underlay contamination recovered exactly (<=0.1 deg error); synthetic split satin at 0 and 60 deg correctly rejected (satin-density gap). Cross-validated against study_pro.fill_stats (independent 5-deg histogram method): 4/4 comparable regions agree within 5.7 deg (only 4 comparable because study_pro.classify tags few whole runs as fill — pro files chain phases).
- Angle convention: pyembroidery/Tajima y-up frame, mod 180 (0=horizontal, 90=vertical). Screen renders mirror theta -> 180-theta; all deltas/consistency stats are mirror-immune.

HEADLINE NUMBERS
- 64 tatami regions, ~116k fill stitches, in only 10/40 files. All 30 fill-free files' rejects are 100% satin-density rejections — the corpus is satin-lettering-heavy.
- CRITICAL CORPUS FACT: Kent's commissioned files contain ZERO tatami. PRECISION DRON HAT.DST (58 runs), beckers logo hat.DST (14), both HOTEL FREMONT.DST (20/21) are entirely satin (incl. split satin — the "2-pen rows + narrow" rejects). The pro answer for cap logos of this genre is "don't fill, satin everything." Fill evidence below comes from sketch-style decorative designs (bunny-star, cat-and-girl, corgi, teddy-bear, snowman, chamomile, rose-hand, summer-umbrella, christmas-sleigh, hello-spring).

Q1: ONE GLOBAL ANGLE PER DESIGN? No. 0/8 multi-fill designs share one angle at 10-deg tolerance. Dominant-angle-cluster stitch share: med 0.46, p10 0.37, max 0.93. But ~46 of 153 overlapping same-design pairs differ by 60-90 deg = deliberate CROSSHATCH (two passes over the same area, in 7/8 multi-fill designs — a sketch-style signature). Folding perpendicular mates into one "axis family": still 2-4 families per design; dominant family share med 0.55. Two designs are effectively single-angle: rose-hand (68 deg carrying 93% of fill stitches, per-element wobble 61-86) and summer-umbrella (117 deg, 93%, wobble 114-117 plus small counter-angle accents at 28/92).

Q2: DO ADJACENT SAME-COLOR FILLS SHARE AN ANGLE? Mostly no in this corpus. Same-block non-overlapping pairs: n=21, med diff 22.8 deg, only 24% within 10 deg. Nearby pairs (<15mm apart, n=7): teddy-bear 2.1, bunny-star 3.0 (shared) vs corgi 16.0/18.5/49.7 and cat-and-girl 25.4/29.0 (deliberately varied). Sketch designs vary angle per element as an aesthetic; the cleaner solid-fill designs (rose-hand, summer-umbrella) hold one angle within ~3-10 deg.

Q3: ANGLE VS ELEMENT ASPECT RATIO — ALIGNED, ACROSS, OR FIXED 45? Not fixed 45. Region angle within +-7 of canonical: 0 deg 6%, 45 deg 6%, 90 deg 17%, 135 deg 0%, OTHER 70% (76% stitch-weighted). Big regions (n>=1000 st, n=28) sit at: 11,28,35,61,68,77,82,88,89,89,91,92,92,95,103,112,114,117,119,147,152,153,155,162,164,164,171,174 — loose clusters near-vertical-tilted (88-119) and shallow-near-horizontal (147-174); exact canonical angles are rare, 10-30-deg-off tilts are the norm. Alignment with region long axis (delta 0=with, 90=across): AR 1-1.5: med 30, with-axis(<=30 deg) 55%; AR 1.5-2.5: med 29, with 51% / across 31%; AR>2.5: med 28, with 67% / across 33%, oblique 0%, and only 1/9 elongated regions uses a canonical angle. Tendency: follow the long axis, or run perpendicular to it — almost never an unrelated oblique on elongated shapes.

REGION QUALITY (context): row gap med 0.83mm (p10 0.62, p90 1.13), stitch med 2.20mm (p90 3.05), coherence med 0.90 — these sketch fills are lighter and shorter-stitched than classic 0.65mm/4mm tatami.

ENGINE IMPLICATIONS
- The 45-deg default matches pro practice ~6% of the time; retire it as a default. Per-region PCA aligned to the long axis matches the dominant pro tendency (67% on elongated shapes) — keep per-region PCA but snap nearby same-color regions to a shared angle (pros hold +-3-10 deg within an element group when the design is a solid-fill piece), which also matches the wordmark lesson.
- Consider a perpendicular-second-pass (crosshatch) mode for sketch/decorative styles — 7/8 multi-fill pro designs use it.
- No corpus evidence on fill LETTERING angle: pro lettering here is always satin. The "one shared angle on lettering rows" rule stands on the wordmark lesson alone, unrefuted but also unconfirmed by this corpus.

INSTRUMENT LIMITS (honest)
- Region = needle-down run: a fill area sewn in N sections counts as N observations; the crosshatch detector is coarse centroid/extent overlap.
- Narrow fills (<8mm along rows, <=2 penetrations/row) are rejected by the split-satin guard — narrow tatami is underrepresented by design.
- Contour/spiral fills would fail the coherence gate; none appeared (no low-coherence rejects), so no claim about them.
- Cross-validation n=4 (study_pro's whole-run classifier is phase-blind); synthetic validation is the stronger leg.
- Absolute angles carry the y-up/mirror ambiguity (theta vs 180-theta on screen); every comparative stat is unaffected.


### Agent return 2 (6,431 chars)

All measurements complete. Final report follows.

---

# UNDERLAY RECIPES PER ELEMENT CLASS — professional corpus measurement

**Corpus**: 36 DSTs in `C:\Users\EE-LT-11030\EMB-Bot\scratch_corpus` + 3 commissioned (`C:\Users\EE-LT-11030\Downloads\PRECISION DRON HAT.DST`, `C:\Users\EE-LT-11030\Downloads\Other\2024\beckers logo hat.DST`, `C:\Users\EE-LT-11030\Downloads\Duplicates\HOTEL FREMONT .DST`; the other two FREMONT copies are byte-dup MD5 `3DA32F...` / near-dup, excluded from aggregates). Total measured: **1,476 satin columns, 65 fills** (dedup run: 1,389 cols).

**Instrument**: `probe_underlay.py` (scratchpad; phase segmentation per census_pro with 3 fixes: split-satin desplit requiring reversals on BOTH sides of a collinear pair; turn-based (cos<0.45) zigzag detection because sparse zigzag at ~90° segment angles has zero reversals and reads "R" under census logic; row-level forensics for fills because chained needle-down edge-run/grid/top form ONE low-turn phase that windows cannot split). **Validated on synthetic fixture first** — all four planted constructs read exact: split 6mm satin → w=6.00 `R_edge+ZZ`; 3mm → `R_center+Z` (run stitch 2.50, zig period 4.0); 1mm → `none`; fill → gap 0.39, stitch 3.50, `edge_run+grid` (spacing 2.00, 89° delta). FREMONT duplicate pair reads 87 vs 88 cols with identical recipe mix (stability check).

## 1. SATIN: underlay class share by column width (deduped corpus, multi-count)

| width mm | n | none | center run | edge run | zigzag(any) | double-Z |
|---|---|---|---|---|---|---|
| <1.0 | 152 | 67% | 12% | 18% | 5% | 1% |
| 1.0–1.5 | 242 | 55% | 23% | 8% | 19% | 1% |
| 1.5–2.0 | 234 | 40% | 30% | 9% | 37% | 5% |
| 2.0–3.0 | 359 | 28% | 40% | 6% | **65%** | 17% |
| 3.0–4.0 | 214 | 35% | 31% | 8% | 56% | 12% |
| ≥4.0 | 188 | 29% | 33% | 9% | **63%** | 18% |

**The width gates pros actually use**: under ~1.5mm → mostly bare or a center walk; zigzag arrives at 1.5–2mm (37%) and becomes majority practice ≥2mm. Double-zigzag is a ≥2mm phenomenon (17–18%), and much heavier in the commissioned cap files: **27% at 2–3mm, 29% at 3–4mm, 37% ≥4mm** (beckers logo, 4.4mm med columns, is the ZZ+R_edge outlier). Dominant full recipes ≥2mm: `Z`, `R_center+Z`, `R_center+Z+R_center` (walk out, zig back, walk center, column), `ZZ`. Edge-run walk is a niche (~6–9%) except: commissioned wide columns (33% ≥4mm — beckers) and sub-1mm (18% — summer-umbrella.dst's 12 edge cases, sketch-style rails).

## 2. SATIN: underlay class measurements (mm)

| class | n | med | p10 | p90 |
|---|---|---|---|---|
| zigzag period (same-rail; advance = period/2) | 706 | 2.95 | 1.82 | 4.12 |
| zigzag zig length | 706 | 2.33 | 1.30 | 4.30 |
| center-run stitch | 532 | 1.94 | 1.12 | 2.39 |
| edge-run stitch | 144 | 1.58 | 0.76 | 2.18 |

- Zigzag **advance ≈ 1.5mm/stitch (period ~3.0) and does NOT scale with width** (med 3.01/3.04/3.01/2.86 across 1.5→4+ buckets); narrow 1.0–1.5 columns use tighter ~1.0mm advance (period 1.96).
- Zig length ≈ column width (zig/width med → 0.99 at ≥4mm): back-solving hypot(uw, adv) gives **underlay inset ≈ 0.35–0.5mm per side**.
- Underlay run stitch ~2.0mm, shorter than travel runs.
- Top column density flat at **0.40–0.42mm** everywhere except <1mm bucket (0.58 med, p90 1.30 — contaminated, see limits).

## 3. SMALL LETTERING (proxy: col len ≤8mm AND w ≤2mm; corpus col len med 7.6, p10 2.6)

| width | n | none | center | edge | zigzag |
|---|---|---|---|---|---|
| <1.0 | 139 | 70% | 9% | 17% | 4% |
| 1.0–1.5 | 175 | 59% | 17% | 7% | 19% |
| 1.5–2.0 | 119 | 55% | 18% | 11% | 21% |

Commissioned hat lettering (FREMONT w med 1.40, PRECISION w med 1.36): none 49–58%, center-run 26–28%, zigzag ~22%. **Pro small lettering: at most a center run; zigzag only once strokes reach ~1.5mm+.**

## 4. FILLS (65 fills, presence deduped per fill)

| underlay class | share |
|---|---|
| edge run (contour) | **66%** |
| center run | 49% (inflated — includes travel; see limits) |
| sparse zigzag pass | 43% |
| grid/lattice | 42% |
| dense same-angle prefill | 14% |
| sparse same-angle | 12% |
| none | 6% |

- **Grid angle vs top stitching: strongly perpendicular** — histogram 90°:24, 75°:9, 60°:9 vs ≤45°:7. Grid spacing med **1.59** (p10 0.78, p90 3.00), grid stitch 2.90.
- Fill edge-run stitch med 2.30 (p10 1.30, p90 3.71).
- Top fill: row gap med 0.23, stitch med 3.35. **Commissioned cap fills are denser and tightly controlled: gap 0.18–0.19 (p10=p90=0.19!), stitch 3.45** vs freebies gap med 0.31, p90 0.65.
- Commissioned fills all carry full stacks (`center_run+edge_run+grid+zigzag…`); "none" fills come from freebie sketch files (bunny-star, think-positive).

## 5. Verdict vs shipped presets
- `center_run/zigzag` under satin: matches pro practice **but needs the width gate** — none/center-only <1.5mm, zigzag ≥ ~1.8–2mm at **1.5mm advance, 0.4mm/side inset**; consider double-Z ≥2.5–3mm for caps (Kent's commissioned digitizers use it 27–37%).
- `edge_lattice` under fill: matches — edge run (2.3mm stitch) + lattice ~1.6mm spacing **perpendicular to top angle** is exactly the modal pro stack; a sparse zigzag pass (43%) is a common third layer.

## Instrument limits (honest)
1. **"none" is an upper bound**: walk-back attribution stops at any earlier satin phase, so one shared whole-letter underlay is credited to only the first column above it; underlay in a separate run behind low-overlap travel is also missed.
2. Narrow sparse zigzag (two-apart ≤1.4mm) is indistinguishable from a thin column → Z undercounted in <1.5mm buckets and the <1mm bucket's "columns" are partly contaminated (its adv p90 1.30 says so).
3. `R_center` cannot distinguish deliberate center-run underlay from needle-travel along the column (kept only if path ≥0.45× column length).
4. Desplit handles single-split crosses only; a double-split (>~7mm) column would fragment — corpus widths make this low-impact.
5. Fill elements are bbox union-find groups: multi-patch elements pool pre-rows, so per-fill part *counts* (grid+grid+zigzag×5) are inflated — only deduped presence percentages are trustworthy; n=65 fills is modest.
6. Fill detection requires ≥8 dense trailing rows (gap ≤0.9); sparse decorative fills are excluded by design.

Scripts: `C:\Users\EE-LT-~1\AppData\Local\Temp\claude\C--Users-EE-LT-11030\b845a108-6467-4184-b54f-1f888a276bca\scratchpad\probe_underlay.py` and `summarize.py` (scratchpad only, nothing written into the repo).
