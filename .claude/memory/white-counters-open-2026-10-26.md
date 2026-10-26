---
name: white-counters-open-2026-10-26
description: sew_enclosed_white sewed white into Tires' e loops and ProSeal's gun slot — holes in UNTAGGED shapes it called fields. A hole <= 1.5 holder strokes wide, or a holder-less speck < 2.5 mm2, is a counter (open) unless inside another sewing field. MFab/Becker byte-identical under the recipe.
metadata:
  type: project
---

D3 of Kent's 2026-10-26 ruling ("Gate to MFab art first"): the MFab recipe's
`sew_enclosed_white` put white where the pro leaves fabric. Rule in
`enclosed_white.py` (`COUNTER_MAX_STROKES` 1.5, `SPECK_MM2` 2.5,
`_counter_like`), on the option's ON path only; tests in
`tests/test_sew_enclosed_white.py` (the Tires strict xfail now passes).

- **The miss was the HOLDER, not the hole:** Tires' joined "ires" and
  ProSeal's gun body carry no letter tag, so their holes read as fields.
  Width of the hole (2 x inradius) over the holder's stroke (2A/P) splits the
  census cleanly: open/covered at 1.28 and under (Tires 1.28/0.80, Golden
  Tee S04c12d7a 1.04, ProSeal slot 1.28); white at 1.78 and up (Machine's
  badge hole, MFab's band hole 2.87, Golden Tee arc 7.59, bands 7.5-71).
- **Keep holes inside a sewing field as they were:** MFab's band pinholes
  (0.1-0.3 strokes) stay "field" — silhouette_underfill and stage 7 read
  `sew_enclosed_white == "field"` literally; relabelling them moved bytes.
- **Census without new digitizes:** `enclosed_pro_census.analyse_job` over
  OFF cells built from the bystander study's defaults runs (regions.pkl +
  DST). Kappa (coverage) 0.895 -> 0.896, n 77; without ProSeal hat (DST-only,
  colour unreadable) 0.909 -> 1.0, n 67. BEANIES ARE UNREADABLE: the pro's
  knockdown covers every enclosed row (all read 1.0). The census misread
  ProSeal's 2 mm slot as sewn (0.95): the render shows it open — read the
  picture before trusting a small hole's coverage share.
- **Gaulke LC/beanie (#1105's finding):** the option sewed ONE 0.4 mm2 speck, and
  its white FRONT layer pulled the roof line and window cross ahead of the black,
  which buried them. Speck left open -> nothing re-layers: recipe output is
  byte-identical to defaults (LC 427097bf, beanie 836d635b). Their remaining gap
  vs the pro (white satin vs open garment) is the DEFAULTS' (gate 1), not this file's.
- ProSeal's SPRAY P/A white in the bystander images does not reproduce on
  main d36ff80e+ (small text re-set); the speck rule is preventive there.
- Proof: MFab hat/LC and four Becker sizes md5-identical under the full
  recipe; Tires 7,747/10 -> 8,169/9 (loops open, pro 10 trims), ProSeal hat
  6,798/46 -> 6,460/40 (white 7 areas -> the handle highlight only).

**Why:** Kent's MFab-first gate needs the white option to stop damaging
non-MFab art before the recipe can widen.
**How to apply:** the colour question ("covered by the body's thread" vs
white) is beyond the coverage census; use the pro's PES or a render.
Related: [[enclosed-white-like-pro-2026-10-23]], [[sew-white-areas-2026-10-21]].
