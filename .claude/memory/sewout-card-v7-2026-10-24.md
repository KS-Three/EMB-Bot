---
name: sewout-card-v7-2026-10-24
description: Sew-out card v7 (I5) — only `pull_comp_by_stroke` and `pro_measured_values` still wait on fabric; arms sit on main + Kent's ruled-unmerged flips (BASE); pull does nothing on Fremont, and on Becker's I/N it turns SPLIT satin into plain satin like the pro's
metadata:
  type: project
---

2026-10-24/25, queue item I5 (`docs/superpowers/plans/2026-10-23-opus-team-architecture.md`).
Tool `digitizer/tools/sewout_card_v7.py`, card `docs/sewout/card-v7-2026-10-25/`
(DST, worksheet PNG/PDF, one preview per arm), copy for the machine in
`Claude Personal\Embroidery\Digitized Designs\sewout-card-v7\`.

**What still waits on fabric, measured from main:** only the two flags. Every
other "until a sew-out" hold was settled by a LATER ruling: `fill_turn_slant`
("next card's OFF/ON swatch", 10-22) was flipped from the flip sheet 10-23, as
were `satin_underlay_short_columns`, `fill_underlay_cross`, `trim_bury_under_later`
and the solids-satin pair (#1049 -> #1057, unmerged then). The cross pass's
constants already match the pro (1.0 / 4.0 vs 0.98 / 3.99, settings audit row
15); the short-column zigzag pitch has no knob and no measured pro value
(0.6-1.3 by reader gate). `cut_every_jump` is a construction hold (#1048).

**Why:** a session handed a list of "next card" holds would sew five swatches
Kent had already ruled on. **How to apply:** check each hold against the flip
PRs since it was written (`gh pr list`, flip-sheet PR bodies), not only against
`config.py` defaults -- a ruled flip can sit unmerged and red for days.

**Base = main + ruled-unmerged flips** (`BASE`, 16 flags of #1057/#1070 that
exist on main), so arm (a) is what ships once they land. Card v4 replaced three
cards whose baseline had gone stale. `tie_in_off` / `border_from_outline` are
not flags on main and are absent.

**Pull does nothing on Fremont:** strokes ~0.85 mm, where the fit returns the
hat's own 0.4. On the card's Fremont pieces (b)/(d) are (a)/(c) byte for byte;
across the whole design two tagline letters move <= 0.02 mm, counts unchanged.
So the pull arms sew on Becker MARINE's I and N at 76.5 mm, and **there the
flag changes construction, not just width**: OFF plans SPLIT satin (cross 4.40,
two 2.3 mm stitches, 89% split), ON plain (3.79 / 3.76, 5%). The pro's own DST,
same reader: 4.02 / 3.74, 7% -- plain, like ON.

**Fremont's crop has no long-row fill and no bean cap** (its only cap is the
white outer outline), and under BASE's `border_by_size` a fill of 6 mm+ gets a
satin ring instead of a cap. So the card adds a synthetic plate: 18 mm rows
(fill p75 3.0 -> 3.49) and a 5.5 mm disc (over the 5.0 satin ceiling, under the
ring's 6 mm) that keeps the bean cap (0.73 -> 0.93).

**Readers that misled:** a satin "cross" that reverses on both sides
(`small_text_columns.crosses`) reads split satin as 0.8 mm -- join the half
stitches between reversals. A median fill stitch reads ~2 mm (row ends, short
rows); the p75 is the row's interior stitch. Satin spacing read off a DST is
0.4 whatever it is (0.1 mm grid): read it off the plan.

Speed: both flags are read in stage 7 only, so `build_generation` runs once per
job and each arm forks it (Fremont 7 + 4 x 6.5 min under load, against 27 min
per fresh digitize).

Related: [[pull-comp-by-stroke-2026-10-22]], [[pro-measured-values-2026-10-23]],
[[layout-judged-in-preview-2026-10-22]], [[bean-holds-on-2026-10-15]],
[[card-v4-sewout-letter-size-2026-10-20]].
