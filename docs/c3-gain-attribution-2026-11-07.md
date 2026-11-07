# Satin/fill C3: where the oracle-split gain sits, 2026-11-07

**Question.** PR #1284's oracle ground-splitter moved mean satin/fill cell kappa
0.381 -> 0.482 over 21 jobs, between its pre-registered 0.45 (close) and 0.55
(build) bars (`docs/satin-fill-oracle-split-2026-11-06.md`). Which jobs, and how
many regions, carry the +0.10? Does it sit behind one detectable layering
pattern, such as a contained dark piece or a keyline? **Measurement only.** No
engine file, flag or default touched.

**All figures are chance-corrected kappa (ROADMAP gate 4).** The chance floor
rides in brackets beside every kappa, and every interval is a bootstrap 95%
interval.

## Done-test

1. **Top 3 jobs: 49% of the +0.10, on #1284's own 21 jobs.** They are
   `bridge_lc` (+0.40), `hotel_fremont_patch` (+0.33) and `bridge_hat` (+0.31).
   **Two of the three are not layering at all.** The Bridge pair gains by the
   per-region relabel (+0.36 and +0.31). Its blob cut adds +0.04 and +0.00.
   Re-measured on today's main (17 jobs), the top 3 carry **57%** of the gain
   (`becker_hat_large`, `hotel_fremont_patch`, `toat_machine_beanie`) and
   **55%** of the cut term.
2. **The gain is not one term.** On #1284's 21 jobs, +0.101 = relabel -0.016 +
   cut +0.117. On today's 17 it is +0.074 = relabel -0.070 + cut +0.145.
   **The cut alone, laid on today's routing (no relabel), is worth +0.052
   [0.009, 0.081], and 70% of that is one artwork family:** the three To a T
   jobs, all on the same field region.
3. **13 regions carry the whole cut term, and 3 of them carry half.** The top
   region, Fremont patch's field, carries 31% by itself.
4. **One geometric pattern, but not a layering pattern.** All 36 cut blobs are
   rims. Each lies along an edge of its region, none is more than about 4 cells
   (8 mm) across, and **none is a contained piece**. 83% of the cut term is in
   the ground's own thread colour block, so flat art shows no colour edge there
   to detect. A darker-thread keyline, the "dark piece" case, carries 7.5%
   (13% for all darker rims).
5. **Build/close call: close the layering direction.** This is a decision for
   Kent (below). The pre-registered number sits between the bars, and its
   intervals straddle both. The attribution says what the number is made of: a
   same-colour edge band of the ground. That is the rule's own close-branch
   content ("edge caps and border tiers"), not something to infer by layering.

## Inputs, and what could not be re-run

- **Today's main `5762602`**, OFF arm re-digitized from scratch. Main moved after
  #1284 (`5caccdc8`): #1301 turned `stage0_scale_relative_grad` and the
  flat-fringe cure ON. On the 17 jobs re-run here, routing moved 0.424 -> 0.437
  (`toat_machine_hat` 0.32 -> 0.42). Oracle-split reproduced exactly: 0.511 on
  both. *(measured 2026-11-07, `python -m tools.satin_fill_census oracle-split`)*
- **Bridge (2 jobs) and ProSeal (2 jobs) are #1284's point values only.** The
  Bridge pro files live in a folder above the checkout, and the ProSeal artwork
  is not in the committed `Embroidery Files.zip`. Their rows below carry no
  interval. `tires_hat_3d` is degenerate (the pro sews one type) and is left
  out, as in #1284.
- Pro files came from the committed `Embroidery Files.zip`, unpacked into the
  gitignored `scratch_kent/`. Nothing third-party was added, and no render was
  written.

## Method (`satin_fill_census.py attribute`)

Four maps on `cell_census`'s grid, all scored with the same `_kappa_of`:

| map | what it is |
|---|---|
| `routing` | ours, today |
| `plain` | the per-region oracle: each of our regions gets the pro's majority type |
| `split` | #1284's oracle-split: `plain`, then each pro minority-type blob of >= 10 cells gets its type |
| `routing_blobs` | ours, with ONLY those blobs given the pro's type: the layering term today's engine could buy, with no relabel riding along |

- **gain** = split - routing = **relabel** (plain - routing) + **cut** (split - plain).
- **Per-job intervals.** A region-cluster bootstrap with 1,000 replicates. Each of
  our sewn regions is one cluster, and unowned cells go in 16 mm tiles. One set
  of replicate weights serves all four maps, so differences carry PAIRED
  intervals. 2 mm cells are not independent, and a cell bootstrap would print
  intervals several times too narrow. A replicate whose chance floor is
  degenerate is undefined, not "agreement 1". That hit 51 of 1,000 on Golden
  Tee and 1 on Gaulke LC.
- **Pooled intervals.** A two-stage bootstrap. Resample jobs (17), or whole
  artworks (7, since the Becker five are one logo), then take one of each
  picked job's own replicates. **The artwork interval is the honest one.**
- **Regions.** The cut term per region is the add-one gain on top of `plain`,
  summed over the region's blobs. Those add-ones sum to 0.149 against the
  measured 0.145, so interaction is small.
- **Blob pattern, from OUR owner map.** A blob is a *keyline* when at least 80%
  of it lies within 2 cells of the region's outline, a *halo* when that much
  lies within 2 cells of one of our pieces sewn on the region, and a *band*
  when it is near both. A *contained* blob is not a rim and does not touch the
  outline. *Edge* is the rest.
- **Blob colour.** The pro's dominant DST colour block in the blob, against the
  block over the rest of the region. *Darker* or *lighter* means a Rec. 601
  luma step of at least 25, read from his PES threads where the colour count
  matches.

## Per job, today's main

*(measured 2026-11-07, main `5762602`, `python -m tools.satin_fill_census attribute --runs OFF`; kappa (chance) [95%])*

| job | routing | per-region oracle | oracle-split | routing + blobs only | gain | of which relabel | of which cut | blobs on routing |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 0.290 (0.53) [0.11, 0.41] | 0.441 (0.48) [0.25, 0.57] | 0.543 (0.50) [0.43, 0.59] | 0.359 (0.54) [0.12, 0.49] | +0.253 [+0.16, +0.38] | +0.151 | +0.102 | +0.069 [+0.00, +0.15] |
| hotel_fremont_patch | 0.545 (0.47) [0.05, 0.59] | 0.069 (0.61) [0.01, 0.78] | 0.796 (0.54) [0.55, 0.81] | 0.571 (0.47) [0.05, 0.62] | +0.251 [+0.21, +0.62] | -0.475 | +0.726 | +0.026 [+0.00, +0.03] |
| toat_machine_beanie | 0.390 (0.57) [0.12, 0.53] | 0.252 (0.59) [0.06, 0.56] | 0.606 (0.56) [0.16, 0.72] | 0.646 (0.55) [0.12, 0.75] | +0.217 [-0.07, +0.35] | -0.137 | +0.354 | +0.256 [+0.00, +0.39] |
| becker_lc_large | 0.361 (0.51) [0.18, 0.47] | 0.495 (0.49) [0.32, 0.61] | 0.572 (0.50) [0.45, 0.64] | 0.420 (0.52) [0.19, 0.55] | +0.211 [+0.14, +0.32] | +0.133 | +0.078 | +0.059 [+0.00, +0.14] |
| mfab_hat | 0.563 (0.48) [0.39, 0.74] | 0.555 (0.52) [0.29, 0.80] | 0.720 (0.51) [0.61, 0.80] | 0.563 (0.48) [0.39, 0.74] | +0.157 [+0.04, +0.24] | -0.008 | +0.165 | +0.000 [+0.00, +0.00] |
| mfab_lc | 0.585 (0.49) [0.39, 0.82] | 0.610 (0.53) [0.32, 0.86] | 0.724 (0.53) [0.59, 0.86] | 0.591 (0.49) [0.39, 0.82] | +0.138 [+0.01, +0.29] | +0.025 | +0.114 | +0.005 [+0.00, +0.01] |
| toat_beanie | 0.388 (0.55) [0.00, 0.45] | 0.228 (0.58) [0.00, 0.34] | 0.502 (0.56) [0.09, 0.61] | 0.561 (0.54) [0.01, 0.68] | +0.114 [-0.04, +0.35] | -0.160 | +0.274 | +0.173 [+0.00, +0.25] |
| gaulke_roofing_beanie | 0.307 (0.51) [0.19, 0.43] | 0.403 (0.49) [0.33, 0.48] | 0.403 (0.49) [0.33, 0.48] | 0.307 (0.51) [0.19, 0.43] | +0.096 [+0.01, +0.18] | +0.096 | 0 | 0 |
| becker_hat_small | 0.533 (0.50) [0.34, 0.62] | 0.602 (0.50) [0.40, 0.70] | 0.602 (0.50) [0.40, 0.70] | 0.533 (0.50) [0.34, 0.62] | +0.069 [+0.01, +0.19] | +0.069 | 0 | 0 |
| precision_drone | 0.376 (0.50) [0.30, 0.52] | 0.342 (0.63) [0.10, 0.66] | 0.431 (0.62) [0.26, 0.66] | 0.380 (0.50) [0.30, 0.52] | +0.055 [-0.10, +0.20] | -0.034 | +0.089 | +0.003 [+0.00, +0.01] |
| toat_machine_hat | 0.422 (0.58) [0.18, 0.52] | 0.204 (0.59) [0.04, 0.54] | 0.473 (0.56) [0.12, 0.59] | 0.605 (0.56) [0.18, 0.68] | +0.050 [-0.26, +0.21] | -0.218 | +0.269 | +0.183 [+0.00, +0.26] |
| becker_chest_small | 0.578 (0.50) [0.41, 0.67] | 0.623 (0.50) [0.44, 0.73] | 0.623 (0.50) [0.44, 0.73] | 0.578 (0.50) [0.41, 0.67] | +0.045 [+0.00, +0.11] | +0.045 | 0 | 0 |
| becker_beanie | 0.245 (0.56) [0.10, 0.33] | 0.117 (0.68) [0.01, 0.28] | 0.264 (0.66) [0.13, 0.42] | 0.267 (0.55) [0.12, 0.36] | +0.020 [-0.12, +0.22] | -0.128 | +0.147 | +0.023 [+0.00, +0.09] |
| hotel_fremont_hat | 0.575 (0.48) [0.06, 0.61] | 0.456 (0.47) [0.22, 0.86] | 0.594 (0.48) [0.45, 0.86] | 0.653 (0.48) [0.06, 0.70] | +0.019 [-0.12, +0.70] | -0.120 | +0.138 | +0.078 [+0.00, +0.11] |
| goldentee_hat | 0.868 (0.61) [0.00, 0.92] | 0.835 (0.58) [0.00, 0.94] | 0.835 (0.58) [0.00, 0.94] | 0.868 (0.61) [0.00, 0.92] | -0.033 [-0.11, +0.07] | -0.033 | 0 | 0 |
| gaulke_roofing_hat | 0.115 (0.84) [0.00, 0.24] | 0.000 (0.90) [0.00, 0.00] | 0.000 (0.90) [0.00, 0.00] | 0.115 (0.84) [0.00, 0.24] | -0.115 [-0.24, +0.00] | -0.115 | 0 | 0 |
| gaulke_roofing_lc | 0.286 (0.88) [0.00, 0.46] | 0.000 (0.92) [0.00, 0.00] | 0.000 (0.92) [0.00, 0.00] | 0.286 (0.88) [0.00, 0.46] | -0.286 [-0.46, +0.00] | -0.286 | 0 | 0 |
| **mean of 17** | **0.437** | **0.367** | **0.511** | **0.488** | **+0.074** | **-0.070** | **+0.145** | **+0.052** |
| 95%, 17 jobs resampled | [0.30, 0.50] | [0.26, 0.51] | [0.38, 0.60] | [0.34, 0.54] | [+0.015, +0.177] | [-0.11, +0.08] | [+0.038, +0.202] | [+0.009, +0.081] |
| **95%, 7 artworks resampled** | [0.30, 0.54] | [0.24, 0.53] | **[0.33, 0.66]** | [0.32, 0.59] | **[-0.008, +0.191]** | [-0.13, +0.09] | [+0.027, +0.222] | [+0.002, +0.100] |

The relabel and cut columns' own paired intervals are in the tool's output. Some
per-job intervals are very wide, such as Fremont patch's relabel. That is
honest: one field region is a third of the job's cells, so the job's kappa
rests on whether that one region is drawn.

### #1284's 21 jobs, point values (the +0.10 as briefed)

*(from the per-job table in `docs/satin-fill-oracle-split-2026-11-06.md`, 2 decimals, so each entry carries +/-0.005 of rounding)*

| | routing | per-region oracle | oracle-split | gain | relabel | cut |
|---|---|---|---|---|---|---|
| mean of 21 | 0.381 | 0.365 | 0.482 | +0.101 | -0.016 | +0.117 |
| bridge_lc | 0.10 | 0.46 | 0.50 | +0.40 | +0.36 | +0.04 |
| hotel_fremont_patch | 0.52 | 0.06 | 0.85 | +0.33 | -0.46 | +0.79 |
| bridge_hat | 0.14 | 0.45 | 0.45 | +0.31 | +0.31 | 0 |
| proseal_hat | 0.17 | 0.05 | 0.05 | -0.12 | -0.12 | 0 |
| proseal_beanie | 0.39 | 0.44 | 0.44 | +0.05 | +0.05 | 0 |

**Top 3 by gain: 0.491 of the +0.101.** Top 3 by cut (Fremont patch, To a T
machine beanie, To a T machine hat) carry 0.541 of the +0.117. The Bridge pair's
+0.71 is relabel, which a layering stage cannot buy. Bridge's routing has
probably moved since: #1299 and #1301 changed what Bridge sews under the
stage-0 flip. It was not re-measured here.

## How many regions carry it

*(measured 2026-11-07, same run)*

13 regions carry the whole cut term: **3 carry 50% and 7 carry 80%.**

| job | region | class | graded mm² | share of cut |
|---|---|---|---|---|
| hotel_fremont_patch | S78e6cd01 (the field) | ground, fill | 2,076 | 0.307 |
| toat_machine_beanie | Sba572771 (the field) | ground, fill | 2,452 | 0.141 |
| toat_machine_hat | Sba572771 | piece, fill | 3,080 | 0.111 |
| toat_beanie | Sba572771 | piece, fill | 2,356 | 0.099 |
| mfab_hat | Sb250f949 | piece, fill | 1,100 | 0.066 |
| hotel_fremont_hat | S78e6cd01 | ground, fill | 2,008 | 0.054 |
| mfab_lc | Sd6a15334 | piece, fill | 1,016 | 0.045 |
| becker_hat_large | S92f2350b | piece, satin | 1,084 | 0.039 |

**By shape class** (our plan tier; *ground* = another sewn region sits inside
it): ground fill 0.50, piece fill 0.32, piece satin 0.11, lettering fill 0.04,
lettering satin 0.03. Eleven of the 13 carriers are regions of 700 mm² or more,
and they carry 0.96. The Fremont and To a T fields (five regions across five
jobs) carry 0.71.

## Is it one detectable layering pattern?

*(measured 2026-11-07, same run; 36 blobs)*

| pattern | blobs | share of cut | share of blobs on routing |
|---|---|---|---|
| halo (a rim round one of our pieces) | 10 | 0.569 | 0.563 |
| band (a strip between the outline and our pieces) | 19 | 0.322 | 0.318 |
| keyline (a rim along the outline) | 7 | 0.110 | 0.119 |
| **contained** | **0** | **0** | **0** |
| edge (a lobe reaching the outline) | 0 | 0 | 0 |

| pro's thread vs the ground's | share of cut | share of blobs on routing |
|---|---|---|
| same colour block | 0.831 | 0.784 |
| darker | 0.129 (keyline 0.075) | 0.162 |
| lighter / other | 0.040 | 0.054 |

- **Every blob is a rim**, at most about 4 cells (8 mm) across (widest
  half-width 1.91 cells).
- The type change runs both ways: the pro's fill in a pro-satin ground carries
  0.535, and the pro's satin in a pro-fill ground carries 0.465.
- **There is no contained dark piece.** The colour-separated keyline (Becker's
  outline, the Becker beanie's two rims) is real, but it carries 7.5% of the
  cut.
- **What the oracle cuts is the pro sewing the margin of a ground in the other
  stitch type, in the ground's own colour.** A strip of 2-8 mm runs beside the
  pieces sewn on the ground, or along its outline. Flat art has no edge there,
  since it is one colour. The cue is geometric (distance to an edge), not a
  layer. The cell type is also an area statistic (`scorecard.cell_stats`, from
  segment length and reversals). A strip where the pro's rows shorten against
  a piece can read as the other type with no change of intent, which is one
  more reason not to read these strips as layers.
- Colour caveat: the To a T machine jobs have only 2-3 pro blocks, and
  `toat_machine_hat` has no PES. "Same block" is weaker evidence there than on
  Fremont (9-11 blocks) or MFab (5).
- **Our routing already sews 58.5% of the blob cells as the pro's type.** On
  MFab the blobs add 0.000 on routing. The cut credit there only repairs the
  damage the per-region relabel did when it painted the whole ground the pro's
  majority. **So the cut column overstates what layering could buy.** The
  honest column is "blobs on routing": +0.052, 70% of it in To a T.

## Build / close against the pre-registered bars

| reading | mean | 95% (artworks) | against 0.45 / 0.55 |
|---|---|---|---|
| #1284, 21 jobs (as briefed) | 0.482 | - | between |
| today's main, 17 jobs | 0.511 | [0.33, 0.66] | between; interval spans both bars |
| same 17, #1284's run (2-decimal entries) | 0.511 | - | between |

**By the number alone: still no verdict, and the intervals show it cannot become
one on these jobs.** A 7-artwork sample cannot place a mean inside a 0.10-wide
window.

**By content: close.** The rule's build branch was "a layering-inference stage
(extend `silhouette_underfill`)". Its close branch was "the rest of the gap is
edge caps and border tiers". The gain is a same-colour edge band, never a
contained piece, and most of the gain on today's engine comes from one artwork's
field. That is the close branch's description, reached by attribution rather
than by the threshold.

## Decisions for Kent

**C3 build/close call.** The number sits between the bars; this doc attributes
what it is made of.

1. **Close the layering direction; re-scope the remainder as an edge-band /
   border-tier question (my pick).** Cost: none now. A follow-up measurement
   would pre-register a geometric rule, "the pro sews a 2-8 mm margin of a
   large ground in the other type", against the pro on the same 17+ jobs.
   Catch: the edge band is the pro's style choice. It may not generalise past
   the few artworks that carry it (Fremont, To a T, MFab, Becker large), and
   the attributable upside on today's engine is about +0.05.
2. **Build the layering stage anyway** (extend `silhouette_underfill`). Cost:
   one or more design-and-build sessions plus a default-OFF flag and its arms.
   Catch: there is no contained piece to infer, 83% of the target has no colour
   edge in the art, and the realistic gain on routing is +0.052 [0.002, 0.100],
   70% of it from one artwork.
3. **Keep "no verdict" and re-run with Bridge and ProSeal on Kent's machine.**
   Cost: about an hour on his box (`digitize`, `measure`, `attribute`). Catch:
   Bridge's gain in #1284 was relabel, not cut, so it cannot change the content
   finding above. It only moves the headline number.

## Rebuild

From `digitizer/`, with `EMB_SCRATCH_KENT` (and `EMB_BRIDGE_PRO` for Bridge) set
as in `tools/pro_baseline.py`:

```
python -m tools.satin_fill_census digitize --runs OFF
python -m tools.satin_fill_census measure --runs OFF
python -m tools.satin_fill_census oracle-split --runs OFF
python -m tools.satin_fill_census attribute --runs OFF     # ~45 s; writes OFF/attribution.json
```

The cloud run here used `--only` with the 18 jobs whose files are in
`Embroidery Files.zip`, unpacked into `scratch_kent/` (the `To a T:Becker
Beanies` folder renamed with a `-`, as `JOBS` spells it). The seed is fixed
(`BOOT_SEED` 1107, salted per job), so the intervals reproduce. The unit tests
are in `digitizer/tests/test_satin_fill_census.py`.
