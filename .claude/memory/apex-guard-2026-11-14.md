---
name: apex-guard-2026-11-14
description: "2026-11-14 — `lettering_columns_apex_guard` (cfg.extra, built OFF): apex_cut's losing tips are hairline strokes (< SATIN_MIN_CROSS_MM) or crosses the walk found only by sliding below the crotch to >= 0.9 of its limit; the share alone separates nothing; and_pizza's Z cure goes with it"
metadata:
  type: project
---

# Apex-cut guard — 2026-11-14

The Director's brief. The apex_cut corpus table
(`docs/apex-cut-corpus-2026-11-14.md`, 43 designs) found 10 better, 4 worse
(outline_lineart_logo badly, k_line, precision_drone, mfab_lc) and 1 mixed
(and_pizza). The guard is to keep the gains and send the losses back to OFF.

**Read tip by tip, not design by design.** The corpus pickles hold each
design's regions and runs. The tool re-ran the letter cut on every changed
shape with apex ON and looked at each merged tip (`apex-guard-1114/tips/`).
**A cross through the crotch is TWO "apex" records:** summing them per tip
changes every number (Becker's M is 1.69 W and 6.4 mm, not 0.52 + 1.17).

**What the losses share.** The guard (`outline_cut._apex_guard_refuses`)
refuses two kinds of tip:
- **A stroke under one satin cross** (`machine.SATIN_MIN_CROSS_MM`).
  Outline_lineart's white outline rings are 0.18-0.19 mm wide and tagged as
  text. Their notches walked long bars across the black letter inside.
- **A cross found only by SLIDING.** The cut sits below the crotch (an
  `apex_stub`) at 0.9 of the limit or more (`APEX_GUARD_SHARE`). Every loss
  reads 0.96-1.00. The gains that slid read 0.39-0.76.
- **The share alone separates nothing:** crosses through the crotch sit at
  0.9-1.0 too, Becker's and ProSeal's gains among them.

A refused crotch tries no other tip, so the letter cuts exactly as OFF:
k_line ON+guard has the OFF md5.

**The cost:** and_pizza goes back to OFF, its Z-joint cure included. Each
Z's two joints are one shape turned 180 deg, and only the top-right one
fans. That is the sewing order there (the Column lane's walk, owned by the
jag-source lane), not the tip.

Related: [[jag-source-2026-11-13]], [[fat-ink-ledger-2026-11-14]].
