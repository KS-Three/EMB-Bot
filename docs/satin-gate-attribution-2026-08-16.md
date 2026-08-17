# Which satin gate loses the pro's satin ground — measured, and closed

*2026-08-16. Slice 1 (attribution) and slice 2 (the fix) of
`docs/superpowers/specs/2026-08-16-satin-routing-gate-attribution-design.md`.*

**Verdict up front: the DT regularity term rejects 63.6% of the pro-satin ground
we sew as fill, at a median miss of 0.05 past its own 0.5 limit. Loosening the
limit does not work. Replacing it with a direct measurement of ribbon-ness does:
corpus mean 45.8 -> 48.1, better on 8 designs, worse on 1, unchanged on 5.**

## 1. Population and method

15 real customer designs against their professional digitizations, prepped by
`tools/pro_parity/prep_both.py` with `PRO_PARITY_FORCED_CLASS=flat` — 10 of the
15 are misrouted into the photo lane by stage 0
(`docs/classifier-misroutes-real-logos-2026-08-15.md`) and never reach the
satin/fill ladder otherwise. Kent labelled 14 of the 15 flat, so forcing flat is
honest here and keeps this work off the stage-0 blocker.

Measured in an isolated worktree per the standing ruling, with module resolution
verified to hit the worktree's own `digitizer_core`.

The instrument is `tools/pro_parity/gateprobe.py`: it joins
`stage6_satin.classify_ribbon`'s verdict to the pro's ground truth through
`scorecard.py`'s own 2 mm cells and registration, so a number here reads against
a number the score reports.

## 2. Attribution — which gate fires

Of the pro's satin ground, **2,212 of 4,748 cells (46.6%) are ground our
classifier declines to satin.** By gate:

| gate | shapes | cells | share | median margin (p90) | units |
|---|---|---|---|---|---|
| `dt_irregular` | 62 | 1,406 | 63.6% | 0.05 (0.22) | `dt_cv` over the 0.5 allowed |
| `dt_p90_cap` | 16 | 490 | 22.2% | 0.51 (0.75) | mm over the 5.0 cap |
| `width_cap` | 2 | 283 | 12.8% | 0.40 (0.66) | mm over the 2A/P cap |
| `aspect` | 19 | 33 | 1.5% | 0.48 (0.68) | below the 3.0 demanded |

The regularity term dominates, and the misses cluster at the line rather than
far past it — a taper, a serif or a script stroke's thick-and-thin body spreads
the medial-axis radii without making the shape any less of a ribbon.

## 3. Why the obvious fix is not the fix

Sweeping the regularity limit trades almost one for one:

```
dt_cv limit   recovers pro-satin   leaks pro-fill
0.55                103                 304
0.70                353                 415
0.75                625                 439
```

Same for the width cap: 5.5 mm recovers 316 and leaks 286. This is the placement
defect MASTER_SCOPE said retuning could not fix, reproduced directly.

## 4. The ceiling, before building anything

An ORACLE that knew the pro's own answer for each of our shapes scores **76.6%**
stitch-type agreement against the **55.4%** we sewed. So shape-level routing had
21 points of headroom and was worth working on.

Two facts worth carrying:

- **"Call everything satin" also scores 55.4%.** The shipped classifier added
  nothing over that constant on this population.
- **48.1% of graded cells sit in shapes that are under 75% one type.** Our
  regions straddle the pro's satin/fill boundary, which is what caps the oracle
  at 76.6% and is a segmentation question, not a classifier one.

## 5. The discriminator

Two statistics off the distance transform already being computed:

- **`explained`** = area / (spine length x width). A ribbon IS its spine swept
  by its width. Letterform archetypes read 0.85-0.94, a 60 mm taper 0.90, and
  the serrated disc the DT check exists to catch reads 0.11-0.13. Boundary noise
  moves it the OPPOSITE way to `2*area/perimeter` — that is what makes it safe
  to promote on.
- **`elongation`** = spine length / width, because `explained` alone waves
  through this repo's own benchmark star (`photo/enthusiast_logo.png`'s
  `Sff37b029`, reading 0.974), which satins into the documented starburst. The
  star runs 8.3 against 12-25 for real ribbons.

`explained >= 0.80` was chosen on a plateau, not a knife edge (0.70 and 0.75
give +309 and +316 net cells against 0.80's +333), and it helps 12 designs while
hurting 2. The elongation floor of 10.0 costs 32 of those net cells and buys
exclusion of a rendering defect confirmed by eye.

**Promotion reopens the regularity term only.** The width cap is a physical
limit — a column wider than the machine holds does not become sewable by being
ribbon-shaped.

## 6. Result

Same worktree, same population, both runs forced flat:

| design | before | after | delta |
|---|---|---|---|
| becker_hat_small | 38.4 | 47.7 | +9.3 |
| becker_chest_small | 36.4 | 45.0 | +8.6 |
| becker_hat_large | 35.9 | 42.5 | +6.6 |
| mfab_hat | 56.1 | 60.6 | +4.5 |
| precision_drone | 44.6 | 48.3 | +3.7 |
| becker_beanie | 34.0 | 37.2 | +3.2 |
| bridge_hat | 54.5 | 55.9 | +1.4 |
| mfab_lc | 62.2 | 62.4 | +0.2 |
| bridge_lc | 54.6 | 51.8 | **-2.8** |
| becker_lc_large, gaulke x2, hotel x2, tires | | | unchanged |
| **corpus mean** | **45.8** | **48.1** | **+2.3** |

`direction` moved with it, which is the point rather than a bonus: a column sewn
as satin has its crosses perpendicular to its spine, the way the pro's are. The
Becker designs go from 0.00 to 0.31/0.35/0.38 on that component.

`bridge_lc` is the one regression (type 0.23 -> 0.15) and is not explained. Its
sibling `bridge_hat` gains from the same artwork, so it is the same
same-artwork-opposite-outcome pattern `hotel_fremont_hat` showed in the stage-0
work — part of each delta is which pro file we are compared against.

## 7. What this DISPROVES — the sub-1mm width floor

MASTER_SCOPE live defect 2 proposes rerouting satin under ~1.0 mm to a run
stitch. **On this population that is wrong: of the 64 shapes classifying satin
at a DT p90 width under 1.0 mm, 61 are ground the pro also sewed as satin.**

Defect 2 was measured on photo-class corpus regions — a different population.
The honest form of that fix is therefore "gate it to the photo lane and measure
it there", and it is NOT built here. Nothing about the Law 31 concern is
disproved for photo art; what is disproved is applying the floor to flat logo
art, where professionals satin hairline strokes routinely.

## 8. Reproducing

```
PRO_PARITY_ROOT="G:/My Drive/EMB-Bot/Embroidery Files" \
PRO_PARITY_OUT=<out> PRO_PARITY_FORCED_CLASS=flat \
  python digitizer/tools/pro_parity/prep_both.py
python digitizer/tools/pro_parity/gateprobe.py --features --csv gates.csv <out>/real/*/
python digitizer/tools/pro_parity/scorecard.py <out>/real/*/
```
