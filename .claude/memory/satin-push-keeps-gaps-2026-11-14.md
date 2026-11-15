---
name: satin-push-keeps-gaps-2026-11-14
description: Kent's 23 merged-letter fault groups traced on main 66b11432; largest geometry cause = satin rail push into bays / same-thread gaps (counters were held, bays were not); `satin_push_keeps_gaps` built OFF, 0.5 floor lands on the pro at Gaulke's E and S
metadata:
  type: project
---

# Merged letters traced; `satin_push_keeps_gaps` (2026-11-14)

**Trace** (`docs/closed-counters-traced-2026-11-14.md`, evidence
`eye_pairs_out/counters-1114/`): 23 groups / 52 pins of the census's
"merged / closed / spacing" class.
- Trace at 4.4 px/mm (Bridge, 5): counters ~2 px; the pro re-draws the text larger. Arc re-set lane.
- **Satin rail push into a bay or same-thread gap (4): Gaulke E, S, window; TOAT T.**
- Thread width on sub-0.5 mm strokes/gaps (4: k_line, bukit, Bridge i-dot, ProSeal S): gate 1 / raise small text.
- Already cured on main: keyline-as-satin (hed_p_e x2, lineart i-dot) and the silhouette blend rim (30 pins).
- One each: MFab G (stage-5 growth over keyline, `growth_keeps_gaps`), Fremont A (bean spines before re-set), and_pizza (Column-lane joint). Three are not closure (jag, detail, tonal merge).

**Cause.** `_push_rails` (`stage6_satin.py`, used by satin and the Column
lane via `columns.sewn_rails`) held the pull out of a COUNTER (hole) to keep
`cfg.min_detail_mm`, but pushed full pull into bays and neighbour gaps.
Gaulke E 1.00 mm at stage 5 -> 0.00 needle; S 0.73 -> 0.00.

**Flag** `cfg.extra["satin_push_keeps_gaps"]` (OFF): a ray from the rail
that crosses bare fabric back into the shape (bay) or into same-thread ink
(`push_keep` in stage 7) is held like a counter. `true` = counter floor
(1.5); a number = that floor. Thread-drawn gap mm OFF / true / 0.5 / pro:
E 0.10/0.82/0.36/0.36, S 0.00/0.67/0.28/0.36, window 0.22/0.54/0.50/0.73.
Catch: parallel same-thread bars closer than the floor lose pull on facing
sides (TOAT speed lines sew thinner). Sheets: `counters-1114/sheets/`.

**Window, measured:** the horizontal divider is stage-5 growth of the lower
panes (0.7 -> 0.4 at stage 5), owned by `growth_keeps_gaps` (#1485). Both
flags at 0.5: four panes, E 0.36 / S 0.28 / window 0.60 vs pro 0.36 / 0.36 /
0.73, 1.29% of Gaulke moves. Ray test vectorised (`_kept_limits`, numpy
ray-edge, spans as arrays, `deadline.check` per 256 rays): byte-identical,
Gaulke `_push_rails` 0.8-1.0 s OFF -> 1.9 s ON (first build ~10x).

**How to apply:** the floor is Kent's pick; the worker's is 0.5 plus
`growth_keeps_gaps` (true doubles the pro's E/S gaps and thins parallel
bars). Pull magnitude untouched (gate 1). Related:
[[fat-ink-ledger-2026-11-14]], [[space-fault-reader-2026-11-12]].

**Gaulke's window, 11-14 (#1557):** two panes are predicted fill at stage 5 and grown 14.8 -> 20.4 mm2; `compact_solids_satin` then sews them as satin on that grown polygon, closing the horizontal divider (0.7 -> 0.4 at stage 5, 0.1-0.2 at the thread; pro 0.7). `compact_satin_keeps_gaps` (built OFF) applies stage 5's `_kept_gaps` to compact satins only: divider 0.6, 0.11% of Gaulke moves. With `satin_push_keeps_gaps` 0.5 the window has four panes, like the pro.

**Kent 2026-11-15:** "Flip both, value 0.5" (`satin_push_keeps_gaps` at 0.5 and `compact_satin_keeps_gaps`). Ruled ON 11-15, flip pending.
