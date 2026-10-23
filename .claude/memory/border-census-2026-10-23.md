---
name: border-census-2026-10-23
description: Border census over every paired logo — our rings on small shapes come from the edge cap and run tier, not stage6_border; the pro rings by SIZE (>= ~4 mm)
metadata:
  type: project
---

Doc: `docs/border-census-2026-10-23.md`; tool `digitizer/tools/border_census.py`;
crops `docs/renders/border-census-2026-10-23/`.

- `stage6_border` fired on ONE shape in all 16 designs (Tires). The Studio sends no
  `border`. The rings Kent saw on ProSeal's bubbles are `edge_cap="bean"` cap pieces
  and the run tier's small-shape outline (bean, not satin).
- Pro rings by size: ~1% of shapes under 2 mm, 7% at 2-4 mm, 29% at 4-6 mm, 49% at
  6 mm and up. Ours: 1% / 10% / 41% / 15%, so we over-ring small and under-ring big
  (we sew big ring-shaped regions whole in satin; the pro fills and borders).
- Contrast is NOT the variable (Becker ringed at 30 dE, ProSeal bubbles bare at 50).

**Why:** Kent's ProSeal observation needed to be a rule, not a one-logo patch.
**How to apply:** gate edge cap / run-tier rings on smallest dimension (~4 mm) — his call,
unsewn. The detector is approximate (single rows noisy, glyph rings read differently
per side); trust a crop over a row. Related: [[border-seam-ownership-2026-09-09]].
