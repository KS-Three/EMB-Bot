---
name: underlay-under-fills-2026-10-05
description: Kent's "stitching goes straight into the fill" is TRUE — gradient-class designs sewed fills with zero underlay, and knit fills get a perimeter walk only (law 26); his pro files sew a crossing pass
metadata:
  type: project
---

Kent, 2026-10-05: on several images the stitching "just went straight into
the fill layers"; he wants supporting / "back stitch" threading under fills.
His words for underlay are "backing" and "back stitching".

Research: `docs/underlay-research-2026-10-05.md`. Two causes, both real.

1. **Gradient lane sewed every fill bare.** `blend_fill` hardcoded
   `underlay_style="none"` and was never handed stage 7's resolved style.
   10 of 14 real-art fixtures class `gradient`. Kent picked the fix:
   `cfg.blend_fallback_underlay`, built OFF (his flip), fallback path only,
   ramp bands stay bare. Six logos: bare fills 33/33 → 5/33, +1.7% stitches.
   **Kent flipped it ON 2026-10-07** (default True; render of the default:
   `docs/renders/blend-fallback-underlay-on-2026-10-07/`).
2. **Knit presets are `edge_run` only** (corpus law 26, 2026-08-05) — no
   interior pass. NOT changed; gate 1 names fabric presets, so it is Kent's
   ruling. His commissioned Becker files sew a sparse tatami crossing the top
   fill at ~90°, rows ~1.0 mm, ~4 mm stitches. The 27-of-45 count behind
   that came from an unvalidated scratch classifier — validate before
   arguing from it.

**The audit settled cause 2's evidence** (`docs/underlay-audit-2026-10-05.md`):
on a classifier validated against 154 ground-truth fills, 34 of 36 large
commissioned fills carry the pass (8 of 9 folders; one house style), 4 of 35
in the third-party corpus law 26 came from. Pitch 0.98, stitch 3.99, 89°, 16%
of the top thread, and he mostly skips the edge run. Law 26's instrument
"lived in scratchpad" and is LOST — an instrument a ruling rests on belongs
in the repo. Kent then picked `cross_tatami`: that pass as an underlay style,
a picker choice in both engines, in no preset.

**Read your own output with the instrument that read the pro's.** The unit
tests were green and the first DST read back at 2.0 mm stitches:
`stitch_shape` re-split underlay at 2.5 mm. On real logos ours still reads
median 2.4 mm and 5–12% thread against his 3.99 and 16% (lettering cuts rows;
1.0 mm inset; largest-piece-only) — say so before anyone calls it his recipe.

**How to apply:** flag 1 alone will not change what Kent sees in a fill's
interior on a left chest; say so before he flips it. The Studio preview and
eye-pairs sheets draw underlay UNDER the top thread, so underlay is invisible
present or absent — show an underlay-only render
(`docs/renders/blend-fallback-underlay-2026-10-05/`), never a normal pair.
Related: [[hotel-fremont-pro-parity-findings]] (the earlier "missing
backfill" refutation only sampled satin letters),
[[envelope-junction-escapes-2026-09-30]], [[sew-out-accepted-as-is]].
