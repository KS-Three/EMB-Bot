# A polygon-native width profile for the satin/fill gates — measured negative #9 (2026-11-06)

Defect 26: the satin/fill classifier flips borderline shapes when only the
polygon's boundary detail changes. The 2026-09-03 record
(`docs/classifier-stability-2026-09-03.md`) measured eight cures negative and
left the item open "only as a different construction: a margin with memory,
or a polygon-native width profile". This is the second one, built and
measured. **It does not beat the incumbent (`cfg.classify_area_weighted`) on
either number, so no engine flag ships.** The instrument does:
`tools/polygon_profile.py` and `tools/ribbon_stability.py --variant profile`
(and `profile:raw`, `area_flag`).

Measured on `5777f91c` (main, 2026-11-06), the ten `tools/curve_tiers.py`
fixtures at 80 mm, Windows. No threshold was retuned and no default moved.

## Verdict up front

| reading | boundary-detail flips | shipped verdicts changed | archetypes / serrated discs |
|---|---|---|---|
| shipped raster classifier | **3** | — | hold |
| `classify_area_weighted`, the incumbent (`area_flag`) | **3** | **7** (all promotions) | hold |
| polygon profile, pixel floor (`profile`) | **3** | **21** (17 promotions, 4 demotions) | hold |
| polygon profile, no floor (`profile:raw`) | 4 | 32 | hold |

The done-test asked for flips 0 or 1 and at most 4 changed verdicts. The
profile reaches neither, and on changed verdicts it is three times the
incumbent. **Negative #9.** The defect-5 kappa re-measure was not run: the
brief gated it on the stability numbers clearing, and they did not.

## 1. Today's baseline is not the 09-03 one

The DT gates now judge **461** shapes across the ten fixtures, not 219
(Fremont alone is 159). Of the five 09-03 flips, the drone ribbon's
spur-inflation flip no longer happens. Three flips are left:

| fixture | shape | area | shipped → refined | what crossed |
|---|---|---|---|---|
| becker | `Sfbfc76fb` | 238.0 mm² | `dt_p90_cap` → `satin` | p90 **5.08 → 5.00 mm** against `SATIN_MAX_WIDTH_MM` 5.0 |
| gaulke | `Saab2077e` | 6.4 mm² | `satin` → `aspect` | the PERIMETER aspect gate, before any DT number |
| meadow | `Scedac1b7` | 25.9 mm² | `dt_irregular` → `satin` | cv **0.53 → 0.50** against 0.5 |

Two things follow before any construction is tried:

- **The gaulke flip is out of reach of every DT reading.** The aspect gate
  reads `2·area/perimeter` and the raw perimeter, and runs before the DT.
  The gates are not to be changed, so one flip is the floor for any
  variant measured this way.
- **The incumbent keeps all three on today's polygons.** Its 09-16 "3 → 0"
  was measured on that day's polygons. Today the becker flip sits on the
  unweighted p90 (deliberately unweighted, its doc §1), and its scope guard
  sends meadow back to the plain raster cv. Its changed count is 7, not 16.

## 2. The construction, and why this one

**(a) was chosen, not (b).** `polygon_axis.skeleton_for` /
`extract_strokes` both PRUNE: the generator-arc rule at 1.6 radii. A pruned
axis was measured first, on the archetypes. At a hard cut of 3.2 or 2.2
radii it **satins the 0.3 mm serrated disc** (cv 0.33, p90 0.37 mm). The
rule correctly finds that a disc's spokes are insignificant, prunes the disc
body away, and leaves only the tooth twigs, which read as a thin regular
ribbon. That is the 09-03 lesson again, on a different axis: on a compact
shape the twigs ARE the medial axis, and the blob detector needs them.

So nothing is pruned (`tools/polygon_profile.py`):

1. Sample the boundary at half a classifier pixel (`polygon_axis`'s pitch).
2. Take the Voronoi ridges inside the shape whose two generators do not sit
   on one polygon edge (those are artefacts of sampling a straight edge).
3. Each ridge is an arc-length station. Its radius is the exact shapely
   distance from its midpoint to the boundary. It counts for its length times
   its **object-angle significance** `s = |p − q| / 2r`: the half-chord
   between its two generators, over the radius.
4. The six `_DtStats` fields are computed the shipped way, with "pixel" read
   as "weighted length". The gates and thresholds are untouched.

`s` is 1 on a spine between opposite walls. It is cos(t/2) on the twig into
a convex corner of interior angle t, so 0.71 for a square corner, which the
raster keeps too. A near-flat vertex's twig reads ~0. Splitting a corner
into two gentler ones splits its weight between them, so the twig weight
follows the boundary's turning, not its vertex count. On the archetypes it
lands where the raster does (`profile:raw`): the 24 × 2 mm bar reads a
spine of 25.8 mm against the raster's 26.2, cv 0.22 against 0.22; the T
reads cv 0.26 against 0.27. All three serrated discs are refused.

**The pixel floor (`profile`).** `profile:raw` carries every corner twig to
r = 0. The raster's skeleton never sees a radius under one pixel. So on
small shapes raw cv reads 0.03–0.13 higher: Fremont's seven 0.8 mm² marks
went from cv 0.37–0.47 to 0.51–0.56, satin → `dt_irregular`. `profile` drops
stations under one pixel of `_rasterize`'s own adaptive grid (`max(6, 8 /
wall)` px/mm, capped at 900 px across). That is the raster's resolution, not
a new constant. It takes the changed count from 32 to 21 and the flips from 4 to 3, and leaves the
calibration gap of §4.

Also measured on the same paired polygons offline, not shipped as
variants (sampled at wall / 16 rather than half a pixel): the unweighted
polygon medial axis (2 flips, **42** changed: every gentle vertex grows a
full-length twig), and weighted cv with an unweighted spine length (5, 30).
The offline scorer reproduced `profile` and `area_flag` exactly (3 / 21,
3 / 7).

## 3. It is stable. That is not what fails

The same 2.5 mm curved ribbon, its walls drawn with more and more vertices
(`tests/test_polygon_profile_tool.py`):

| reading | cv, 48 → 384 vertices | spread | `explained` spread |
|---|---|---|---|
| raster | 0.211 / 0.186 / 0.213 / 0.203 | 0.026 | 0.017 |
| `profile` | 0.140 / 0.141 / 0.144 / 0.149 | 0.009 | 0.012 |
| `profile:raw` | 0.173 / 0.174 / 0.175 / 0.177 | 0.004 | 0.012 |

From about 48 vertices up, the profile converges where the raster jitters.
Under that, the faceted arc really is a different shape, and both readings
move with it.

## 4. Why it still fails: the shipped verdicts are on the knife edge

Over the 461 DT-judged shapes on the shipped polygons:

- The raster's own numbers barely move under refinement today: |Δcv|
  median **0.000**, p90 **0.022**; |Δexplained| p90 **0.024**. Most shapes
  keep their id and their polygon.
- The profile disagrees with the raster on the SAME polygon by |Δcv|
  median **0.047** (p90 0.108) and |Δexplained| median **0.102** (p90 0.189).
- **74 shipped verdicts sit within 0.05 of cv 0.5**, 28 within 0.02.

Any reading that differs from the raster by its own construction re-decides
edge shapes like these by construction. On the regularity edge that is a
coin per shape, and the 21 are mostly just that: drone `S787d58d0` cv 0.55 →
0.41, `S80bb4c96` 0.57 → 0.47, enthusiast `S314ad2f1` 0.54 → 0.47.
`explained` moves further, because the significance weighting makes it read
area over its own sweep: 0.96–1.00 on the four archetypes, against
the raster's 0.85–1.06. So elongated shapes with raster `explained` 0.70–0.79
cross the 0.80 promotion floor (drone `S6edce285` 0.70 → 0.85).

**So the done-test's two numbers are close to mutually exclusive for any
re-measured statistic** while the thresholds stay where the raster put
them. Fewer flips need a reading that differs from the raster's jitter.
Few changed verdicts need one that reproduces it, to well under the 0.05 at
which 74 verdicts change. The thresholds were tuned on the raster
(0.80 / 1.25 / 10 on `scratch_kent`; 0.5 and 5.0 are frozen), so a profile
could only take over with a retune against it: a 15-design corpus sweep,
Kent's call, and ROADMAP gate 1 for the 5.0 mm cap.

## 5. Every shipped verdict `profile` changes (21)

Reason before → after, the raster's numbers → the profile's, region area.

| fixture | shape | area mm² | shipped → profile | cv | explained | elongation |
|---|---|---|---|---|---|---|
| becker | `Sfbfc76fb` | 238.0 | `dt_p90_cap` → `satin` | 0.25 → 0.25 | 0.90 → 0.89 | 15.9 → 17.4 (p90 5.08 → 4.93) |
| fremont | `S78e6cd01` | 1605.7 | `dt_irregular` → `promoted_ribbon` | 0.78 → 0.74 | 0.69 → 0.83 | 648 → 515 |
| drone | `S2492f28b` | 3.6 | `dt_irregular` → `satin` | 0.51 → 0.45 | 1.09 → 1.02 | 5.1 → 5.3 |
| drone | `Sf5882f8b` | 1.0 | `promoted_ribbon` → `dt_irregular` | 0.78 → 0.62 | 0.97 → 1.03 | 12.1 → 7.6 |
| drone | `Se680e8f4` | 2.9 | `dt_irregular` → `satin` | 0.58 → 0.48 | 0.80 → 0.93 | 9.9 → 8.2 |
| drone | `S6edce285` | 36.9 | `dt_irregular` → `promoted_ribbon` | 0.69 → 0.60 | 0.70 → 0.85 | 27.4 → 19.4 |
| drone | `S68387d18` | 38.7 | `dt_irregular` → `promoted_ribbon` | 0.65 → 0.55 | 0.72 → 0.87 | 28.7 → 22.3 |
| drone | `Sc8d707b2` | 14.0 | `dt_irregular` → `satin` | 0.52 → 0.44 | 0.89 → 1.00 | 4.6 → 3.8 |
| drone | `S3bf43597` | 3.1 | `dt_irregular` → `promoted_ribbon` | 0.65 → 0.59 | 0.79 → 0.98 | 16.1 → 13.1 |
| drone | `Sf976c922` | 4.0 | `promoted_ribbon` → `dt_irregular` | 0.76 → 0.60 | 0.84 → 1.01 | 10.4 → 6.5 |
| drone | `Sadf04438` | 9.3 | `dt_irregular` → `promoted_ribbon` | 0.64 → 0.53 | 0.73 → 0.83 | 17.6 → 14.1 |
| drone | `S3df49a44` | 3.2 | `promoted_ribbon` → `dt_irregular` | 0.72 → 0.66 | 0.83 → 0.97 | 11.5 → 8.1 |
| drone | `S37491305` | 2.6 | `dt_irregular` → `satin` | 0.51 → 0.45 | 0.97 → 1.01 | 4.2 → 3.7 |
| drone | `S6c65c000` | 1.1 | `dt_irregular` → `promoted_ribbon` | 0.71 → 0.66 | 0.78 → 0.96 | 21.4 → 17.0 |
| drone | `S787d58d0` | 3.3 | `dt_irregular` → `satin` | 0.55 → 0.41 | 1.00 → 1.00 | 7.1 → 5.3 |
| drone | `S80bb4c96` | 2.1 | `dt_irregular` → `satin` | 0.57 → 0.47 | 0.81 → 0.90 | 6.3 → 5.0 |
| drone | `S495d0b11` | 1.7 | `dt_irregular` → `satin` | 0.57 → 0.48 | 0.87 → 0.96 | 8.8 → 7.2 |
| enthusiast | `S314ad2f1` | 19.7 | `dt_irregular` → `satin` | 0.54 → 0.47 | 0.95 → 0.87 | 8.2 → 9.3 |
| sunset | `Sacda1c3b` | 6.6 | `satin` → `photo_width_floor` | 0.45 → 0.39 | 0.72 → 0.87 | 20.0 → 19.6 (p90 1.10 → 0.96) |
| meadow | `Scedac1b7` | 25.9 | `dt_irregular` → `satin` | 0.53 → 0.46 | 0.80 → 0.76 | 4.8 → 6.2 |
| meadow | `S1ecbdcc8` | 13.9 | `dt_irregular` → `promoted_ribbon` | 0.67 → 0.65 | 0.77 → 0.90 | 34.0 → 29.0 |

Five of the 21 are the incumbent's own promotions: the drone strips
`S6edce285`, `S68387d18`, `S3bf43597`, `Sadf04438` and `S6c65c000`. They are
the same long, varying-width edge strips area-weighting rescues. The other
16 are not. Nine of those are compact shapes (elongation under 10) that
move to plain `satin` on a cv crossing, which the incumbent's scope guard
exists to refuse (its doc: Fremont's 33.1 mm² blob and enthusiast's star
sewed a criss-cross). Three are demotions of shapes the `explained` path
promoted, and one is a satin the photo width floor now takes (sunset, p90
1.10 → 0.96 mm). The other three: becker's 238 mm² shape comes under the cap
(p90 5.08 → 4.93), and Fremont's 1,605.7 mm² ground and a meadow strip are
promoted on `explained`. The profile's three flips are a cv knife edge (drone `Sb9e57a54`,
0.50 → 0.50), the photo width floor at p90 exactly 1.00 mm (meadow
`S230534aa`), and the gaulke aspect flip that nothing here can reach.

## 6. What this leaves

- **A margin with memory** is now the only open construction on 09-03's
  list. It is not a single-digitize property (the verdict takes the tier it
  had in the last run), so it is a product change: Kent's.
- **A profile with retuned thresholds** would be a different item: the four
  promotion and regularity numbers re-swept on `scratch_kent` against the
  profile, with the 5.0 mm cap left alone (gate 1). It would be judged on
  the corpus, not on these ten fixtures.
- **Not reopened here:** the size cliff (area-weighting doc §3) is three
  thresholds crossed by under 1%. A stabler statistic moves the knife edge;
  it does not remove it.

## 7. Reproduce

    cd digitizer
    .venv/Scripts/python tools/ribbon_stability.py --variant area_flag --variant profile --variant profile:raw
    .venv/Scripts/python -m pytest -q tests/test_polygon_profile_tool.py

Windows, same-machine figures (DOCTRINE 2026-09-15). The run digitizes each
fixture twice: about 45 minutes on a quiet laptop, and longer under load.
