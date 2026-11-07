# Lagging area 2: satin-vs-fill routing — external sourcing (2026-11-06)

Legend: **[V]** verified at the primary source this session (GitHub API, PyPI JSON, paper page) · **[U]** not verified. Clean-room rule held: no GPL/AGPL source read; Ink/Stitch, filum, Lilo, openstitch appear by docs and licence line only.

## (a) Verdict

**No external repo or library fixes this, and most of the gap is not a classifier gap.** Kappa 0.387 sits against a 0.650 instrument ceiling, and the per-region oracle (0.365) shows any per-REGION router, learned or hand-built, tops out at or below today's number. That kills the learned-classifier direction (REJECT) and every width-table digitizer (they score 0.13). What remains is (1) *inside* regions: layering/ground decomposition, where no usable code exists (LayerPeeler has no licence and needs a diffusion model; LIVE is a per-image optimiser) so the only lever is internal; and (2) defect 26's instability, which touches ~2% of shapes (5 of 219), so even a perfect cure buys maybe +0.00 to +0.02 kappa. The one genuinely new construction is **theory, not code**: the λ-medial axis / (λ,α)-medial axis (Chazal–Lieutier; Lieutier–Wintraecken) is the literature's answer to "medial axis stable under boundary perturbation", and the repo already owns the polygon-native Voronoi axis it would prune (`polygon_axis.py`). Trap: `polygon_axis` exists and is **HELD** (Kent's M ruling, DOCTRINE 2026-09-16) because of its stroke decomposition; a width profile built on it must reuse its radii only. Also re-verified: the 11-06 claim "no maintained permissive straight-skeleton port" is **false in general** (a maintained MIT TypeScript one exists) but true for Python, and a straight skeleton is the wrong object for width anyway.

## (b) Verdict table

| Candidate | Licence | Stars / last push | Verdict | Serves |
|---|---|---|---|---|
| λ / (λ,α)-medial axis (papers; own code on shapely) | concept | arXiv 2303.04014; SM 2004 [V] | **PROTOTYPE** | Defect 26: polygon-native width profile |
| Vote-over-perturbation classifier (own code) | concept | randomized smoothing, Cohen 2019 [U] | **PROTOTYPE** (cheap) | Defect 26: "margin with memory" |
| Oracle ground-splitter bound (own measurement) | n/a | n/a | **PROTOTYPE** (measure only, no build) | Layering / inside-region gap |
| shapely 2.1.2 (already pinned) | BSD-3 | 4,538 / 2026-11-06; cp314 win_amd64 wheel [V] | USE (exists) | Voronoi, CDT, inscribed-circle primitives |
| `centerline` 1.1.1 | MIT | 297 / 2026-11-05; pure py wheel, release 2024-05 [V] | REJECT | Already built as `polygon_axis.py` |
| `pygeoops` 0.6.0 | BSD-3 | 36 / 2026-10-26; py>=3.10 pure wheel [V] | REJECT | Same: centerline + branch pruning |
| `skan` 0.13.1 | BSD-3 | 153 / 2026-10-26 [V] | WATCH (unchanged) | Plumbing, not a discriminator |
| `pyefd` 1.8.0 | MIT | 97 / 2026-07-21 [V] | WATCH | Descriptors, only if intra-region learning ever revives |
| StrandedKitty/straight-skeleton (TS) | MIT | 90 / 2026-03-24 [V] | WATCH | JS-engine need only; wrong tool for width |
| Botffy/polyskel (+ ladybug fork) | LGPL-3.0 | 88 / 2020-10-12 [V] | REJECT | Dead; LGPL |
| scikit-geometry (CGAL) | LGPL-3.0 | 452 / 2024-01-31 [V]; wheels [U] | REJECT | Stale, LGPL |
| bpypolyskel, Lichtso/straight_skeleton | GPL-3.0 | 63 / 2026-03; 48 / 2020 [V] | REJECT | GPL |
| visioncortex/vtracer (`stacked`) | MIT | 7,475 / 2026-10-22 [V] | WATCH | Layering by stacking at trace time |
| LIVE (Picsart) | Apache-2.0 | 634 / 2024-02-26 [V] | REJECT | Differentiable optimiser per image, GPU |
| kingnobro/LayerPeeler | none (blank on GitHub) | pushed 2025-12-29 [V] | REJECT | No licence; VLM + diffusion; flat icons only |
| heatstitch | MIT | 4 / 2026-11-02 [V] | REJECT as source | Width table, kappa 0.13 |
| openstitch | GitHub reads NOASSERTION (11-04 survey: AGPL-3.0+) | 0 / 2026-11-05 [V] | REJECT | Docs only; same width table |

## (c) PROTOTYPE sections

### C1. λ-medial width profile into `classify_ribbon`

**What.** The λ-medial axis keeps a medial point only if the smallest ball enclosing its nearest boundary points has radius ≥ λ. Chazal–Lieutier show it is stable under small Hausdorff perturbations for suitable λ; its weakness is discontinuity at singular λ, which the (λ,α) refinement (Lieutier–Wintraecken, arXiv 2303.04014) repairs, with Hausdorff and Gromov–Hausdorff stability [V from abstracts and search summaries; proofs not read]. For a polygon: take the Voronoi edges `polygon_axis.py` already builds; each has two generators a chord `c` apart and a radius `r`; keep the edge when `c ≥ 2λ`. The existing arc-length twig test is the Ogniewicz relative of this, so expect heavy overlap. The new part is the second ingredient.

**Second ingredient, the real change.** Stop weighting radii by skeleton *pixels*. `_dt_stats` (`stage6_satin.py:632`) pools `field.dist[field.skel]`, a 1-px thinning whose pixel count changes when the boundary gains detail (the DOCTRINE mechanism). Compute `mean`, `std`, `p90` and `spine_len` as **arclength-weighted** statistics over the pruned Voronoi edges. Boundary jitter then moves each statistic by its amplitude, not by a count of spur pixels. That is the "polygon-native width profile" the dashboard names.

**Plugs in.** New `_dt_stats_polygon(poly)` beside `_dt_stats`, returning the same `_DtStats`, selected by a new default-OFF `cfg.classify_polygon_axis`; reuses `polygon_axis.py`'s Voronoi build, **not** its stroke decomposition (what Kent held). shapely 2.1.2 and scipy are already pinned; no new dependency; Windows 3.14 wheel exists [V].

**Cost.** 2 sessions: 1 to build with parity tests on the four archetypes and the serrated disc; 1 to measure.

**The catch.** (i) A fixed-mm λ deletes strokes thinner than λ; start near 0.25 mm and sweep. (ii) Thresholds (cv 0.5, aspect 3, explained 0.80) were tuned on pixel statistics; arclength-weighted numbers land elsewhere, so expect retuning, i.e. the "new constant" DOCTRINE warns about. (iii) Voronoi on a densely sampled boundary has its own twigs, which is why `polygon_axis` has a pruning test at all. (iv) Defect 26 covers ~2% of shapes.

**First experiment.** Add a `polygon_axis` variant to `python -m tools.ribbon_stability`. Pass criteria, in order:
1. Flips ≤ 2 of 219 (today 5; best of eight cures 3) **and** shipped verdicts changed ≤ 10 (the cures changed 2–48); archetypes (bar, T, H, serrated disc) hold.
2. Becker cliff (satin share 42.5 to 12.8 across 87 to 88 mm): swing ≤ 10 points per 1 mm step over 85–90 mm.
3. Only then `satin_fill_census`: mean kappa over 21 jobs **≥ 0.40** (0.387 + 0.013; `satin_per_stroke` managed +0.002), no job down more than 0.03, bare cloth not up. ≥ 0.42 is a win; the ceiling is 0.650 and the honest expectation is +0.00 to +0.02. Fail at step 1: stop and record the ninth negative.

### C2. A verdict that remembers: vote over perturbations

**What.** The eight cures all changed the *statistic*. A pure function has no state, but it can have memory of neighbouring views of the same shape: classify the polygon at k boundary-detail levels (raw, `simplify(0.5 px)`, `simplify(1 px)`, plus half-pixel raster phase shifts) and return the majority verdict, reporting median metrics. This is the randomized-smoothing idea (Cohen et al. 2019, majority vote under noise) [U, not fetched] applied to a threshold classifier. The pruning cures failed through the spur mechanism; here each vote is the unmodified shipped classifier, so that mechanism is not touched.

**Plugs in.** Wrapper `classify_ribbon_voted` around `classify_ribbon` (`stage6_satin.py:396`), default-OFF flag. **Cost.** 1 session; run views 1 and 2 first, a third only when they disagree, and only for shapes past the width and aspect gates.

**The catch.** It hides rather than fixes: a shape truly on the threshold still gets *some* verdict, just a stable one. Extra DT cost on borderline shapes. It does not touch the size-parametric Becker cliff unless scale (±0.5%) is among the perturbations; add that arm to test.

**First experiment.** Same harness. Pass: flips ≤ 1 of 219, shipped verdicts changed ≤ 5 (a vote over the unmodified classifier should change almost nothing), then census kappa ≥ 0.39. If C1 and C2 both clear, ship C2 first (cheaper, lower risk).

### C3. Oracle ground-splitter: a bound, not a build

**What.** MASTER_SCOPE says do not build a region splitter (grid noise is not the cause); `satin-fill-remeasure` shows 33% of minority cells sit in 10+ cell blobs inside a dozen large grounds where the pro layers pieces on top. No external code serves this on flat raster art: LayerPeeler (VLM plus diffusion, unlicensed, icons only) and LIVE (differentiable optimisation, GPU) are research systems; VTracer's `stacked` mode is the only practical layering convention, MIT, and already in the tracer family. The open question is internal: **what is the ceiling if grounds were split perfectly?**

**Experiment (measurement only, no engine change).** In `tools/satin_fill_census.py`, build an *oracle splitter*: cut each straddled ground along the pro's majority-type blobs (≥ 10 cells), label each part with the pro's majority, re-score cell kappa. It is the 0.365 oracle one level finer. **Decision rule:** oracle-split kappa ≥ 0.55 means a layering inference stage is worth designing (extend `silhouette_underfill`, not a splitter); ≤ 0.45 means the rest is edge caps and border tiers, close the layering direction. **Cost:** 1 session if per-cell maps were kept; otherwise add the 63-minute OFF digitize arm.

**The catch.** An oracle that reads the pro's blobs is optimistic by construction. A high number states a maximum, not what inference from flat art could reach.

## (d) Rejected, one line each

- **Learned satin/fill/run classifier (Hu moments via pinned scikit-image, elliptic Fourier via `pyefd`, shape context)** — REJECT: the per-region oracle (0.365) caps ANY per-region classifier, perfect included, and by-area per-shape kappa is already 0.77 against the labeller's own 0.80. Labels are also noisy (tier reader vs our known plan 0.22 by count). If ever revived: 531 labelled shapes exist, and roughly 10–20 minority-class labels per feature means ≤ 10 features is feasible; it still buys nothing here.
- **Straight skeleton / CGAL, any binding** — REJECT for width: the wavefront follows every vertex, so it is *more* boundary-detail sensitive than the medial axis. Python options are dead or copyleft; the maintained permissive one is TypeScript only.
- **Chordal axis transform on `shapely.constrained_delaunay_triangles`** — stays rejected (09-12): same medial object plus triangulation dependence.
- **`centerline`, `pygeoops`** — REJECT: Voronoi medial axis plus branch pruning, i.e. `polygon_axis.py` without the stability theory.
- **heatstitch / openstitch / filum / Lilo width tables** — REJECT: same width rule everyone copies; heatstitch measured kappa 0.13 on the same pairs. Benchmark DSTs only (GPL clean-room).
- **Scale axis transform (Giesen et al.)** — concept only; I found no stability statement for it [U]; the λ-axis family has the proofs.
- **Canny-style hysteresis** — REJECT as stated: needs a neighbour relation to propagate from, and an isolated shape has none; the measured regularity band (15 verdicts demoted) already showed a two-edge margin just moves the knife edge. C2 is the form of memory that can exist.

## (e) Sources

- Lieutier & Wintraecken, Hausdorff and Gromov–Hausdorff stable subsets of the medial axis: https://arxiv.org/pdf/2303.04014 · https://link.springer.com/article/10.1007/s44007-025-00170-0
- Chazal & Lieutier, The λ-medial axis (SM 2004): https://diglib7.eg.org/bitstream/handle/10.2312/sm20041396/243-248_chazal.pdf
- Discrete λ-medial axis: https://perso.esiee.fr/~chaussaj/Files/Publications/Conference/Discrete_lambda_medial_axis.pdf
- Skeletal representations survey (scale axis): https://arxiv.org/pdf/1301.6809
- LayerPeeler: https://arxiv.org/pdf/2505.23740v2 · https://github.com/kingnobro/LayerPeeler · LIVE: https://github.com/Picsart-AI-Research/LIVE-Layerwise-Image-Vectorization · VTracer: https://github.com/visioncortex/vtracer
- https://github.com/fitodic/centerline · https://pypi.org/project/centerline/ · https://github.com/pygeoops/pygeoops · https://pypi.org/project/pygeoops/
- https://github.com/shapely/shapely · https://pypi.org/project/shapely/2.1.2/ · https://github.com/jni/skan · https://github.com/hbldh/pyefd
- Straight skeletons: https://github.com/Botffy/polyskel · https://github.com/StrandedKitty/straight-skeleton · https://github.com/prochitecture/bpypolyskel · https://github.com/Lichtso/straight_skeleton · https://github.com/scikit-geometry/scikit-geometry
- https://github.com/pfedan/heatstitch · https://github.com/lb2002/openstitch
- Repo: `docs/satin-fill-remeasure-2026-10-29.md`, `docs/classifier-stability-2026-09-03.md`, `digitizer/digitizer_core/stage6_satin.py` (`classify_ribbon` 396, `_dt_stats` 632), `digitizer/digitizer_core/polygon_axis.py`, DOCTRINE 2026-09-16, `docs/external-repo-sourcing-2026-11-06.md`.
