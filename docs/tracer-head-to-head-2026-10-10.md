# Tracer head-to-head: stage 4 vs vtracer, measured — 2026-10-10

**Question (Kent, 2026-10-10):** would a photo-to-SVG converter in front of the
digitizer have done better than our own tracing, and was that ever tested on
anything hard?

**Why it was open.** `docs/vtracer-evaluation-2026-08-17.md` tried vtracer on
three synthetic PNGs (a ring, two pairs of touching circles) and rejected it on
integration grounds. `docs/tooling-research-2026-09-12.md` lists its quality as
"unmeasured". `docs/pipeline-flow-and-foundation-review-2026-09-17.md` names a
curve-fitting tracer as the right foundation for low-resolution sources. Nobody
had put the two side by side on real artwork.

> **Corrected the same evening — read "Addendum" at the bottom first.** Three
> things in the first pass were wrong or incomplete: (1) "resolution sets the
> error" overstated it — the **hard mask** sets it, and reading the source's
> coverage directly is about three times closer on alpha-only art; (2) vtracer
> 1.0.0-alpha **is** on PyPI and has now been measured; (3) arm A in the main
> tables is the region set as it leaves stages 0–4, not bare stage 4.

## Answer

**No. An off-the-shelf tracer would not have helped, and the reason is
upstream of tracing.**

1. **Edge error is set by the mask the tracer is handed, not by the tracer.**
   That mask already sits about 0.10 mm from the true edge at 1.8 px/mm,
   0.055 at 3, 0.033 at 5, 0.023 at 8. No arm that starts from the mask beats
   the mask's own outline by a meaningful margin at any rung. (First pass
   called this a resolution limit. It is not — see the addendum.)
2. **Tracer choice moves the median by at most 0.019 mm** — over 26 cases,
   stage 4 as shipped is closer in 13, vtracer in 5, 8 tie inside 0.005 mm.
   Thread is 0.4 mm wide.
3. **The smooth-looking option is the least accurate.** vtracer run on the
   source's own pixel grid draws the cleanest curves (a quarter to a half of
   the turning and about a quarter of the nodes at 1.8 px/mm) and lands
   0.08–0.25 mm off — two to three times every other arm — with a bad tail. It
   thresholds away the coverage ramp, which is the only sub-pixel information
   a low-resolution file has.
4. **On alpha-only art (Becker's class) vtracer at defaults does nothing.** It
   reproduces the 4-pixel stairs of the mask exactly: same error as the raw
   outline, same roughness.

So the 08-17 rejection stands, now for a measured reason rather than a
packaging one. The 09-17 "outside read" — a curve-fitting tracer for
low-resolution sources — is not supported by this measurement for the binary
tracer that is actually installable.

## Two things this turned up about our own stage 4

- **The curve + sub-pixel work pays from about 3 px/mm up, and not at
  1.8.** Shipped vs plain Douglas-Peucker, median error: 0.033 vs 0.062 mm at
  5 px/mm, 0.059 vs 0.071 at 3 — but 0.114 vs 0.115 at 1.8 on the logos and
  0.108 vs 0.100 on the alpha-only cases. `subpixel_edges_upscaled` shows no
  gain at Becker's resolution on this yardstick.
- **Shipped stage 4 throws spikes on Becker.** Visible in
  `becker-real.png` (panel "A stage 4 shipped"): diagonals are straightened,
  and several vertices overshoot into zigzags that plain DP does not have.
  Not scored — Becker has no truth — but a satin column would follow them.
  Worth a look on its own.

## One side finding

vtracer's keyword-argument call **works on Python 3.12.10** (exit 0, 9,788
masks traced). The crash the 08-17 doc recorded is specific to 3.14, which is
what `digitizer/.venv` on Kent's laptop runs.

## Method

- **Truth.** Golden Tee and Hotel Fremont at their native 21.8 and 31.3 px/mm
  (80 mm target), pipeline stages 0–3, the label map's pixel-exact edges.
  No tracer is involved in the truth. Read on a 2× grid: about 0.01–0.02 mm
  of floor.
- **Test rungs.** The same file brought down with `INTER_AREA` to 1.8, 3, 5,
  8 and 12 px/mm, then run through stages 0–3 as shipped. Stage 1 enlarges
  the low rungs to the 8 px/mm working grid, as it does for a customer.
- **Both lanes.** Stage 0 routes all three "photo" logos `gradient` at
  confidence 1.00 (the 09-17 review's F3, reproduced). Every rung was run
  forced `gradient` (as shipped) and forced `flat`.
- **Same masks for every arm.** `pipeline.vectorize` is wrapped; each arm
  traces exactly the masks stage 4 kept.
- **Becker-shaped cases with a known answer.** Becker is one colour with its
  shape entirely in alpha, and stage 1 enlarges that mask with NEAREST on
  purpose (`stage1_prep.py`, measured 2026-10-01), so stage 4 receives
  4-pixel stairs. To score that class, the busiest colour layer of each
  hi-res logo was written as a single-colour alpha-only PNG and run through
  the same rungs.
- **Registration.** Each rung's millimetre frame is fitted onto the truth's
  (scale + shift) using the mask's own outline, so no arm is favoured. Fitted
  scale stayed within 0.7%, shift within 0.25 mm.
- **Score.** Median distance arm-edge → truth-edge (precision) and
  truth-edge → arm-edge (recall), in mm; turning in degrees per mm of
  boundary; node count.

| Arm | What it is |
|---|---|
| M | the mask's pixel-exact outline — the floor any tracer starts from |
| A0 | stage 4, plain Douglas-Peucker (`subpixel_edges` off, `curve_turn_deg` off) |
| A | stage 4 as shipped |
| B1 | vtracer 0.6.15, binary, spline, defaults, on the work-grid mask |
| B2 | same, `corner_threshold` 120 |
| B3 | vtracer defaults on the mask brought back to the source's pixel grid |

## Numbers

Median edge error, mm, arm → truth. Lower is better. Mean over the four logo
cases (2 logos × 2 lanes); B3 only exists where stage 1 enlarged.

| px/mm | M | A0 | A | B1 | B2 | B3 |
|---|---|---|---|---|---|---|
| 1.8 | 0.104 | 0.115 | 0.114 | 0.107 | 0.105 | 0.185 |
| 3 | 0.055 | 0.071 | 0.059 | 0.065 | 0.065 | 0.137 |
| 5 | 0.033 | 0.062 | 0.033 | 0.042 | 0.047 | 0.084 |
| 8 | 0.023 | 0.050 | 0.033 | 0.042 | 0.046 | – |
| 12 | 0.014 | 0.034 | 0.024 | 0.029 | 0.031 | – |

Alpha-only single-colour cases (mean of two):

| px/mm | M | A0 | A | B1 | B2 | B3 |
|---|---|---|---|---|---|---|
| 1.8 | 0.108 | 0.100 | 0.108 | 0.107 | 0.114 | 0.146 |
| 3 | 0.065 | 0.067 | 0.061 | 0.065 | 0.067 | 0.205 |
| 5 | 0.036 | 0.046 | 0.050 | 0.045 | 0.054 | 0.110 |

Turning, degrees per mm (lower is smoother), same alpha-only cases:

| px/mm | M | A0 | A | B1 | B2 | B3 |
|---|---|---|---|---|---|---|
| 1.8 | 73.1 | 66.2 | 66.4 | 73.1 | 74.5 | 16.9 |
| 3 | 119.5 | 60.7 | 57.1 | 114.2 | 115.9 | 33.9 |
| 5 | 191.7 | 40.8 | 41.9 | 115.8 | 117.8 | 41.1 |

Every case, both directions, 90th percentiles, node and region counts:
`docs/renders/tracer-head-to-head-2026-10-10/tables-logos.txt`,
`tables-alpha-only.txt`, and the two `results-*.json`.

## Pictures

In `docs/renders/tracer-head-to-head-2026-10-10/`, six panels each, a
14 × 9 mm window on the busiest part of the art:

- `becker-real.png` — the real Becker file. No truth; read for shape only.
- `fremontsil-flat-r1.8.png` — alpha-only at 1.8 px/mm. B3's straight lines
  are in the wrong place.
- `fremont-gradient-r5.png` — 5 px/mm as shipped. Stage 4 holds the
  parallelograms' corners; vtracer rounds them and keeps the outer stairs.
- `golden-flat-r1.8.png` — the flat lane at 1.8 px/mm. Every arm is a mess,
  because the masks are.

## What this does not show

- **No stitches, no sew-out.** Edge distance and smoothness only. Whether a
  smoother-but-shifted outline sews better is not answered here, and a
  physical question would need fabric.
- **Two logos and two derived cases.** One run each, no spread. Read
  differences under about 0.01 mm as nothing.
- **Truth is our own segmentation at native resolution.** It fixes where
  edges are; it does not judge whether the colour split is right.
- **`INTER_AREA` models a clean low-res export.** JPEG ringing is not modelled.
  Becker and bridge_bar, the real low-res files, have no truth and were only
  pictured.
- **vtracer 0.6.15, three settings, not a sweep** in the main tables; 1.0.0a4
  is in the addendum. Potrace was not run (GPL, could not ship).
- **Arm A is the region list after the pipeline's post-vectorize steps**, not
  bare `vectorize()` output: the harness kept a reference to a list the
  pipeline goes on editing. Bare stage 4 was re-run on eight scored cases and
  differs by at most 0.004 mm in the median, so the tables stand; on the real
  Becker file bare stage 4 is spikier than what the first picture shows
  (turning 47.4 against 34.4 degrees per mm).

## Addendum — same evening: the floor is the mask, not the pixels

Four more measurements, same harness, same truth.

### 1. Reading coverage directly beats everything on alpha-only art

Arm C skips the mask. It takes the source's own alpha as a coverage field,
interpolates it up 8× and cuts it at one half (a marching-squares
iso-contour), then Douglas-Peucker at 0.2 mm. No tracer, no new dependency.

Median edge error, mm, the two alpha-only truth cases:

| px/mm | case | mask | stage 4 | vtracer 0.6 src grid | **C coverage, DP 0.2** | C raw |
|---|---|---|---|---|---|---|
| 1.8 | fremont layer | 0.112 | 0.123 | 0.139 | **0.041** | 0.041 |
| 1.8 | golden layer | 0.103 | 0.094 | 0.152 | **0.046** | 0.031 |
| 3 | fremont layer | 0.067 | 0.060 | 0.155 | **0.041** | 0.028 |
| 3 | golden layer | 0.064 | 0.061 | 0.254 | **0.057** | 0.055 |
| 5 | fremont layer | 0.037 | 0.046 | 0.101 | **0.039** | 0.037 |
| 5 | golden layer | 0.034 | 0.053 | 0.120 | **0.048** | 0.052 |

At 1.8 px/mm it is two to three times closer than shipped, about a third of
the turning (15–25 against 64–69 degrees per mm) and a quarter of the nodes.
By 5 px/mm the advantage is gone. On the real Becker file it draws clean
straight edges with no spikes in 405 nodes against 1,683
(`becker-real-iso.png`; no truth, picture only).

So the 0.10 mm at 1.8 px/mm is **quantisation from the hard mask**, not a
resolution limit. Stage 1 enlarges the alpha mask with NEAREST
(`stage1_prep.py:521-528`, a 2026-10-01 measurement on other grounds), and
stage 4 then tries to repair 4-pixel stairs. The independent literature pass
(`docs/low-res-vectorization-research-2026-10-10.md`) reaches the same place
from the other side: published sub-pixel edge accuracy is hundredths of a
pixel on a clean edge, and 0.10 mm here is 0.18 px.

**What it costs.** A stroke thinner than about one source pixel never reaches
half coverage and vanishes (`goldensil-flat-r1.8-iso.png`, the thin diagonal).
The mask-based arms mostly lose it too, but they keep a stub.

### 2. On multi-colour art the same idea is promising and unfinished

Arm D estimates per-colour coverage by unmixing each pixel between the two
colours confidently present nearby, then cuts each field at one half. A
one-evening prototype, flat lane only.

| px/mm | logo | stage 4 | **D, DP 0.2** | D, DP 0.05 | D truth-edge miss (median) vs stage 4 |
|---|---|---|---|---|---|
| 1.8 | fremont | 0.118 | **0.099** | 0.094 | 0.160 vs 0.064 |
| 3 | fremont | 0.063 | **0.044** | 0.029 | 0.080 vs 0.045 |
| 5 | fremont | 0.033 | **0.023** | 0.007 | 0.045 vs 0.032 |
| 1.8 | golden | 0.109 | **0.086** | 0.086 | 0.133 vs 0.092 |
| 3 | golden | 0.062 | **0.052** | 0.038 | 0.073 vs 0.069 |
| 5 | golden | 0.045 | **0.039** | 0.023 | 0.050 vs 0.050 |

Where it draws an edge it is closer at every rung, most at 3–5 px/mm. But it
**drops features** — fewer regions, and truth edges with nothing near them —
worst at 1.8 px/mm. Not a result to build on yet; a reason to do it properly.

### 3. The Becker spikes come from the native-resolution edge read

Bare `vectorize()` under five configs, same masks
(`tables-stage4-flags.txt`, `becker-real-variants.png`). Spikes = vertices
turning more than 120°, per 100 mm of boundary.

| case | shipped | `subpixel_edges_upscaled` off |
|---|---|---|
| Becker (real, 1.8 px/mm) | 7.1 spikes, 1,897 nodes | **0.0** spikes, 1,548 nodes |
| fremont layer 1.8 | 0.121 mm, 1.4 spikes | 0.115 mm, 0.0 |
| golden layer 1.8 | 0.094 mm, 1.8 | 0.085 mm, 0.0 |
| fremont logo 1.8 | 0.116 mm, 5.0 | 0.107 mm, 2.1 |
| golden logo 1.8 | 0.108 mm, 6.8 | 0.113 mm, 3.8 |
| fremont layer 3 | 0.062 mm, 6.3 | 0.075 mm, 5.4 |
| golden logo 3 | 0.051 mm, 6.3 | 0.067 mm, 5.0 |

At 1.8 px/mm the native read is no more accurate in three cases of four and
adds every spike. At 3 px/mm it earns its keep in three of four. Curve
refinement adds a few more spikes on top (Becker 4.8 → 7.1) and rides on the
native read: with the read off, the resolution gate turns curves off too.

### 4. vtracer 1.0.0a4 does not change the verdict

It is on PyPI (the 08-17 doc's "not published" is out of date) with a
`watershed` mode its changelog says snaps anti-aliased pixels to the
mid-colour line. Run on the source grid of the alpha-only cases, six
settings (`tables-vtracer-1.0a4.txt`): 0.09–0.12 mm at 1.8 px/mm with long
stretches of truth edge missed (90th percentile 2.5–6 mm), 0.05–0.09 at 3,
about 0.05 at 5. No better than stage 4, far from arm C. Six settings is not a tuning
effort; it is alpha software and behaved like it.

## Built 2026-10-11 — `cfg.coverage_edges`, default OFF

Arm C is in stage 4 as `stage4_vectorize._coverage_parts`, behind
`cfg.coverage_edges`. It applies to one class of source only: a single ink
with its shape in alpha, enlarged by stage 1. Enclosed transparent regions
are read from the same contour's other side; the existing arc refinement runs
on the result. Anything else keeps today's polygon whole.

The implementation, not the prototype, against the same truth
(`tables-coverage-edges-in-pipeline.txt`), median edge error in mm:

| px/mm | case | shipped | `coverage_edges` | turning °/mm | vertices |
|---|---|---|---|---|---|
| 1.8 | fremont layer | 0.121 | **0.053** | 67 → 29 | 2,737 → 1,788 |
| 1.8 | golden layer | 0.094 | **0.042** | 69 → 25 | 452 → 208 |
| 3 | fremont layer | 0.062 | **0.037** | 66 → 50 | 3,401 → 2,763 |
| 3 | golden layer | 0.061 | **0.047** | 49 → 15 | 425 → 209 |
| 5 | fremont layer | 0.046 | 0.042 | 67 → 50 | 3,741 → 3,367 |
| 5 | golden layer | 0.049 | 0.046 | 18 → 12 | 219 → 234 |

On the real Becker file at 50 mm: outline reversals 37 → 7, vertices
736 → 601, ink area +1.4% (`becker-flag-outlines.png`).

**Two things it does not do, both found building it.**

- **On a clean synthetic the shipped polygon is better.** A sharp-cornered
  bar at 1.6 px/mm: shipped 0.03 mm at worst in 4 vertices, the contour 0.22
  (half coverage cuts across a corner; the native read fits the two sides).
  A disc: level. Pinned in `tests/test_coverage_edges.py` as the stated cost.
- **The sewn result on Becker is mixed** (`becker-flag-stitches.png`, 80 mm,
  6,843 against 7,052 stitches). The outer BECKER band is continuous where
  shipped breaks it at the top left; MARINE's letters are not better, and M
  and A read messier. One new warning, `HOLE_NEARLY_CLOSED`. The satin
  decomposition downstream was tuned on the polygons it has been given.

That second point is why the flag ships OFF and stays there until its own
instrument says otherwise: a closer outline is not yet a better sew-out.

## Reproduce

Scripts are in `docs/renders/tracer-head-to-head-2026-10-10/scripts/`. They
were run from a scratch folder outside the repo; nothing in `digitizer/` was
changed and vtracer was installed only into its own Python 3.12 venv.

```bash
cd digitizer && export PYTHONPATH=$PWD
.venv/Scripts/python S/capture.py <image> <run-dir> <width-px|0> <class|-> default
.venv/Scripts/python S/native_masks.py <run-dirs...>
<py312-venv>/python S/trace_vt.py <run-dirs...>          # pip install vtracer
.venv/Scripts/python S/analyze.py <runs-dir> <out-dir>
.venv/Scripts/python S/table.py <out-dir>/results.json
```

Run directories are named `<fixture>-<lane>-truth` and
`<fixture>-<lane>-r<px/mm>`; `analyze.py` pairs them by name.
