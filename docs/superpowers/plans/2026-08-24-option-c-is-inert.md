# Option C targets a code path its own motivating fixture never runs

**Date:** 2026-08-24
**Status:** measurement only. No engine change proposed, and none should be
made on the reasoning this corrects.

Fix 3 of [`2026-08-24-divergence-ranking.md`](2026-08-24-divergence-ranking.md)
reads:

> **Logo palette discipline / input normalization (option C):** golden 13→~3
> threads, −42% phantom area; **kappa gain ≤ +0.08 on one fixture (measured
> minority), ~0 elsewhere** — its value is structure (stops/spools/trims), not
> kappa. `stage2_quantize.merge_delta_e=6.0` explicitly not barred.

The named lever is `stage2_quantize.merge_delta_e`. The named fixture is
`logo_golden_tee.jpg`. **That fixture never reaches that lever**, so tuning it
would move nothing on the evidence that motivated it.

## The check

`stage2_quantize.quantize` is called **zero times** for golden_tee.
`stage2_photo_segment.kept_masks_to_quant` is called once:

```
golden_tee quantizer calls: {'quantize': 0, 'kept_masks_to_quant': 1}
```

Stage 0 classifies it `CLASSIFIED_GRADIENT`, which routes to the photo/gradient
palette path. `merge_delta_e` governs the **flat** lane only.

## The flat lane is already clean

Measured across every committed flat-lane fixture — threads carrying under 1%
of sewn area, the phantom signature option C exists to remove:

| fixture | route | threads | threads under 1% of area |
|---|---|---|---|
| becker_marine_logo.png | flat | 1 | 0 |
| bg_uncertain.png | flat | 1 | 0 |
| logo_alpha.png | flat | 6 | 0 |
| logo_whitebg.png | flat | 6 | 0 |
| enthusiast_logo.png | flat | 3 | 1 |
| logo_script_tires.png | photo | 2 | 0 |
| fur_ramp.png | photo | 5 | 0 |

There is no phantom-thread population on the flat lane to normalise away.

## Where the phantoms actually live

Every fixture stage 0 sends down the **gradient** route carries them:

| fixture | route | threads | threads under 1% of area |
|---|---|---|---|
| drone_render.png | gradient | 19 | **11** |
| logo_drone_thermal_badge.png | gradient | 19 | **11** |
| logo_bridge_bar.jpg | gradient | 18 | **11** |
| logo_golden_tee.jpg | gradient | 17 | **7** |
| logo_gaulke_roofing.png | gradient | 6 | **4** |
| gradient_ramp_linear.png | gradient | 2 | 0 |
| gradient_ramp_radial.png | gradient | 2 | 0 |

The two synthetic ramps are clean; every real **logo** routed to gradient is
not. golden_tee's own tail is a gold ladder — Sunset 7.5%, Orange Peel 5.9%,
Bright Yellow 4.9%, Candlelight 4.6%, Champagne 1.5%, Buttercream 0.2%,
Buttercup 0.2%, Cream 0.1% — eight spools reproducing the gradient fill on
"GOLF" that the divergence ranking already recorded the pro flattening to one
thread.

(`drone_render.png` and `logo_drone_thermal_badge.png` reporting identical
19/11 is the byte-identical-duplicate defect the region-identification
diagnosis logged separately; it is not two independent confirmations.)

## What this means for the fix ranking

Fix 3 is not wrong about the *problem* — golden_tee really does sew 17 threads
where the pro used 3, and the value really is structure rather than kappa. It
is wrong about the *lever*. The phantom threads are a **gradient-route palette**
question, and two routes to them are visible:

1. **Stage 0 sends logos to the gradient route.** golden_tee, bridge_bar,
   thermal_badge and gaulke_roofing are logos, not gradient photographs.
   Correcting that classification is **barred by ROADMAP gate 2** (no stage-0
   recalibration without real tonal artwork; four approaches measured and
   rejected). Reported as position, proposing nothing.
2. **Palette discipline on the gradient route itself** — an eight-step ladder
   inside one gradient fill is the mechanism, and capping or consolidating it
   is a quality trade about how a gradient should be reproduced. That is a
   decision for Kent from a picture, not an engineering default (spec
   decision 1).

## Reproducing

```bash
cd digitizer
.venv/bin/python - <<'PY'
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from collections import Counter
res = run_stages("testdata/photo/logo_golden_tee.jpg", PipelineConfig())
areas = Counter()
for r in res.regions:
    areas[r.thread_index] += r.area_mm2
tot = sum(areas.values())
print(len(areas), "threads;", sum(1 for a in areas.values() if a/tot < 0.01), "under 1%")
PY
```

The call-count check monkeypatches `stage2_quantize.quantize` and
`stage2_photo_segment.kept_masks_to_quant` through the names `pipeline` binds,
then runs the same fixture.

## Limits

- "Under 1% of sewn area" is this document's own phantom proxy, chosen to be
  reproducible from a finished result. The divergence ranking used a different
  and stricter one (dE00 > 10 to every pro thread), which needs the pro file;
  the two agree on direction, not on counts.
- Thread counts here are distinct `region.thread_index` values, not the block
  counts the census reports, so they do not line up digit-for-digit with fix
  3's "13 threads".
- Nothing here measures whether flattening the gradient ladder would look
  better. It measures only that the lever fix 3 names cannot reach it.
