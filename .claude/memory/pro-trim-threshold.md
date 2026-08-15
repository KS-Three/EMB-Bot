---
name: pro-trim-threshold
description: Corpus measurement of where the pro actually cuts thread vs floats it; fabrics.py trim_at_mm=3.0 is ~4x tighter than the pro, but distance is not the pro's decision variable
metadata:
  type: project
---

Measured 2026-08-15 across all 23 pro designs (910 needle-up moves, colour
changes excluded), decoding each machine file's own TRIM/JUMP commands:

```
CUT (trim)      n=542  p50= 7.9mm  p90=34.8mm  min= 1.9mm
NOT CUT (float) n=368  p50= 9.1mm  p90=11.5mm  max=16.1mm
```

Two things follow, and the second matters more than the first:

1. **The pro floats up to 16.1 mm without cutting.** `fabrics.py` sets
   `trim_at_mm` 3.0-4.0 for every fabric with no derivation comment, so we
   would cut all 368 of those. At 12 mm only 12 of the pro's floats would be
   cut and 345 of our cuts spared.
2. **The distributions overlap heavily** — the pro also cuts at 1.9 mm. No
   single threshold reproduces this pro. That is the same conclusion
   `chain_links`' comment in `config.py` already reached from the other
   direction: *"Distance stops being the decision variable — coverage is."*

So raising `trim_at_mm` is evidence-backed but treats the wrong variable, and
it trades cuts for floats on real garments — sew-out territory, like every
other physical-output constant in that table.

**Caveat on the float set:** it is censored below 7.5 mm. `prep_all.decode`
only opens a new run at an implied hop >= `TRAVEL_MM`, so sub-7.5 mm floats are
invisible to it. The 16.1 mm upper bound is real; the p50 is not.

Reproduce: decode each file in `prep_all.DESIGNS`, walk consecutive runs in sew
order, and label each gap by the break kind `decode` returns.

Related: [[fill-density-convention]] (the other constant this corpus settled),
[[emb-bot-digitizer]].
