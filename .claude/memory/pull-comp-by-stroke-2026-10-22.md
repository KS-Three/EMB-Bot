---
name: pull-comp-by-stroke-2026-10-22
description: The pro's hat pull is not fixed — his addition to a satin column FALLS with the drawn stroke (+0.58 at 0.85 mm, +0.42 at 2.6, nothing at 4); `pull_comp_by_stroke` built OFF on hat/LC/beanie; the grown small text is NOT this rule's business (small_bold's share stays)
metadata:
  type: project
---

2026-10-22, PR `pull_comp_by_stroke` (branch `claude/pull-comp-by-stroke-61868c`),
from the card v4 sew-out gap (`card-v4-sewout-letter-size-2026-10-20`: a fixed
0.4 mm hat pull sews a 0.85 mm stroke at ~1.65) and audit row 8
(`docs/settings-vs-pro-2026-10-21.md`: ours +0.15 to +0.27 wider than the pro on
wide hat strokes).

**Measured** (scratch script, pro files from `Embroidery Files.zip` read with
pystitch; letters by colour block / connected pieces in each side's own frame;
sewn = median needle-to-needle satin cross on the piece, 12 mm cap — the
`small_text_columns.crosses` reader caps at 4 mm and TRUNCATES Becker; drawn =
2 x EDT on the art piece's skeleton, the art scaled to the pro's design width;
letters the pro kept at the art's size only, per-job medians):

| job (preset) | letters | drawn | sewn | add |
|---|---|---|---|---|
| Fremont hat + patch (hat) | HOTEL FREMONT, 12 | 0.85 | 1.43 | +0.58 |
| Drone (hat) | THERMAL, 8 | 1.29 | 1.80 | +0.59 |
| Proseal (hat) | PROSEAL + mark, 16 | 2.61 | 3.02 | +0.42 |
| Becker hat small (hat) | MARINE, 9 | 4.22 | 4.00 | -0.22 (art 0.53 mm/px, +/-0.6) |
| Becker hat large (hat) | MARINE, 9 | 5.62 | 5.20 | -0.50 (above our 5.0 satin ceiling) |
| Becker LC large (LC) | MARINE, 9 | 5.28 | 4.90 | -0.45 |
| Proseal beanie (beanie) | PROSEAL, 9 | 2.28 | 2.60 | +0.36 |
| Becker beanie (beanie) | MARINE, 7 | 4.40 | 4.01 | -0.40 |

MFab has no art in the repo (white-on-black preview only): sewn columns 1.40-1.90
on its 7-9 mm letters, no drawn width to pair. Roofing's art is a phone panel:
no piece pairs. Drone's PRECISION is gradient art (stroke reads 0.16): dropped.

**Fit** on the four hat job medians: sewn = 0.77 x drawn + 0.835 (residuals
+0.06 / +0.03 / -0.17 / +0.08). Per rail: pull = add/2 + `RAIL_REACH_INSET_MM`
0.11, scaled to another preset by its pull / 0.4, clamped to [0, preset pull]:
0.40 at 0.85 mm (today's hat value — the pro sews HOTEL FREMONT at exactly our
width), 0.38 at 1.3, 0.23 at 2.6, 0.07 at 4.0, 0 from 4.6. Beanie check: Proseal
beanie predicts 2.52 against 2.60 sewn.

**The finding that matters for the card v4 gap:** at the grown letters' 0.85 mm
stroke this rule returns the preset's own 0.4 — the pro's 0.9 mm columns on his
~4 mm re-set text are NOT a stroke-width effect, he REDRAWS those letters (pro
rules R4). So `lettering_columns_small_bold`'s 0.15 share stays the small-text
rule, and under both flags a small letter's columns are capped at that share.
`pull_comp_by_stroke` is audit row 8's arm (wide strokes), nothing more.

**Built OFF:** `cfg.pull_comp_by_stroke`; `columns.pull_for_width`,
`columns.column_width` (median station cross = the column's own drawn width),
`column_runs(pull_of=)` pushes each column's rails by its own pull; the
letter-level pull (merge, tuck, link buffers) is the fit of the letter's mean
stroke; `min_detail_mm`'s counter hold unchanged; hat/LC/beanie only
(`fabrics.PULL_BY_STROKE_FABRICS`). Read at digitize time on the drawn stroke
(ruling 12 intact). OFF pins untouched. A physical constant — gate 1, Kent flips
after a sew-out. Tests: `tests/test_pull_comp_by_stroke.py` (synthetic 0.85 and
2.5 mm columns within 0.1 of the fit; an H's bar and stems get different pulls).

**Proof on the grown Fremont text at 92.5 mm Hat** (`docs/renders/pull-comp-by-stroke-2026-10-23/`):
OFF and ON IDENTICAL on EST / 1895 / THE / tagline (0.80-0.90 sewn against the
pro's 0.90-0.92) because small_bold's cap wins at 0.85 mm; by-stroke alone (no
small_bold) is the 1.40 blob, as the fixed pull is. `columns_unsewn`: 0 under
small_bold on both fixtures, 2 (two S's of the re-set fixture) without it, the
same with either pull. The flag's work is on strokes over ~1 mm: a 2.5 mm
column sews 2.76 ON against 3.08 OFF.

Related: [[card-v4-sewout-letter-size-2026-10-20]], [[small-text-reset-2026-10-21]],
[[column-width-on-resize-2026-10-01]], [[lettering-architecture-2026-10-07]].
