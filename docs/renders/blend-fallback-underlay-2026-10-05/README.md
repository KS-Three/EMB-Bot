# `blend_fallback_underlay`, OFF beside ON — 2026-10-05

Underlay only. Red is every `UNDERLAY` run in the plan; grey is the top
stitching (fill, satin, border) drawn faint so the shapes can be placed. The
Studio preview and the eye-pairs sheets draw underlay beneath the top thread,
so neither can show this: with the flag ON or OFF they look the same.

| file | what it shows |
|---|---|
| `fremont_off.jpg` / `fremont_on.jpg` | Hotel Fremont patch, 80 mm, `patch` |
| `bridge_off.jpg` / `bridge_on.jpg` | Bridge Bar, 80 mm, `left_chest` |
| `drone_off.jpg` / `drone_on.jpg` | drone thermal badge, 80 mm, `left_chest` |

OFF, the only red is satin's centre run under the lettering and the borders.
ON, each fill that sews as ordinary tatami gets the fabric preset's fill
underlay — on these three garments `edge_run`, one walk 1.0 mm inside the
edge. **The interior of a fill is still empty ON.** That is the knit preset
(corpus law 26), not this flag; see `docs/underlay-research-2026-10-05.md`
§3 and option 2.

## Numbers

Nine `REAL_ART` logos (`tools/thin_strokes.corpus_cases`), 80 mm, the case's
garment, `max_colors=6`, commit `838c3451` plus this change. "Bare fills" is
shapes with `FILL` runs and no `UNDERLAY` run of their own.

| case | class | stitches | trims | bare fills | underlay stitches under fills |
|---|---|---|---|---|---|
| becker | flat | 6557 → 6557 | 38 → 38 | 0/1 → 0/1 | 9 → 9 (plan identical) |
| tires | photo_scene | 2654 → 2654 | 7 → 7 | 0/1 → 0/1 | 11 → 11 (plan identical) |
| enthusiast | flat | 2484 → 2484 | 15 → 15 | 0/1 → 0/1 | 9 → 9 (plan identical) |
| fremont | gradient | 13292 → 13779 | 37 → 43 | 5/5 → 0/5 | 0 → 371 |
| bridge | gradient | 17744 → 18083 | 98 → 98 | 8/8 → 0/8 | 0 → 321 |
| golden_tee | gradient | 8474 → 8482 | 45 → 45 | 1/1 → 0/1 | 0 → 12 |
| gaulke | gradient | 4205 → 4212 | 34 → 32 | 3/3 → 0/3 | 0 → 41 |
| drone | gradient | 18975 → 19283 | 139 → 131 | 12/12 → 3/12 | 0 → 371 |
| screenshot | gradient | 7949 → 7988 | 70 → 72 | 4/4 → 2/4 | 0 → 81 |

The six gradient-class designs together: stitches 70,639 → 71,827 (+1.7%),
trims 423 → 421, bare fills 33 of 33 → 5 of 33. Fremont pays six trims.
The five fills still bare ON were not broken down here; the research note
(§1.1, cases 3 and 4) names the two ways a fill stays bare under any style —
a shape under 2 mm wide, which the 1.0 mm inset empties, and a true ramp
band, which this flag leaves alone on purpose.

Not sewn. Nothing here says what the underlay does on cloth.
