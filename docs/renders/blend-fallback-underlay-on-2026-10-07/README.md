# `blend_fallback_underlay` ON by default — 2026-10-07

Kent's ruling 2026-10-07: the flag built OFF on 2026-10-05
([`../blend-fallback-underlay-2026-10-05/`](../blend-fallback-underlay-2026-10-05/README.md))
is now the default. This pair checks that the DEFAULT config sews it.

Underlay only. Red is every `UNDERLAY` run in the plan; grey is the top
stitching drawn faint. The Studio preview draws underlay beneath the top
thread and cannot show this.

| file | config |
|---|---|
| `gaulke_off.jpg` | `PipelineConfig(blend_fallback_underlay=False)` — the old default |
| `gaulke_on.jpg` | `PipelineConfig()` — the new default |

Gaulke Roofing (`photo/logo_gaulke_roofing.png`, classes `gradient`), 80 mm,
`left_chest`, `max_colors=6`, on `07393d71` plus this change.

| | OFF | default (ON) |
|---|---|---|
| stitches | 4,583 | 4,590 |
| trims | 34 | 32 |
| bare fills | 3 of 3 | 0 of 3 |
| underlay stitches under fills | 0 | 41 |

The deltas are the 2026-10-05 table's for this case (+7 stitches, trims
34 → 32, 41 underlay stitches); the absolute counts moved with `main` since.
The sun fill gains its perimeter walk; on `left_chest` the preset's style is
`edge_run`, so the interior is still empty. The interior pass on knit presets
is corpus law 26 and a separate gate-1 item, not changed here.

Not sewn.
