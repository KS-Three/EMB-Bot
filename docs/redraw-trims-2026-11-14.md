# Why the outline redraw adds trims, and what it costs in CPU (2026-11-14)

Queue item (c) after Kent's 2026-11-14 rulings. `outline_redraw_k` 0.75 shipped in #1515 ("Set 0.75"). Kent saw its trim cost before ruling: on the CI tripwire, Becker hat large went from 11 to 16 trims and MFab hat from 16 to 23. The timing worker then found it the one flip costing more than 15% CPU (To a T machine x1.52, #1546).

All numbers below are local runs at the pro's size and config (`tools.pro_pair`), changing only the flag named. Two baselines were used, and each table names its own.

## Where the extra trims are (main `e1ff49b7`)

- **Becker hat large, 13 -> 17.**
  - All four extra trims are on one shape, the white enclosed field (`Sb7019eaf`), sewn as fill under the keyline loops. Its region is unchanged, because letterform priors refit it.
  - Its fill now joins the letter faces with five long lifts (18.8, 41.2, 10.5, 95.3 and 53.3 mm) where it had one (86.9 mm).
  - The travel router refuses 12 joins against 9, and the refused ones are longer (73.5 and 32.9 mm).
- **MFab hat, 18 -> 24.** +2 on the black host and +1 on each of five small shapes, one of them a 0.2 mm2 sliver that now sews.

## What it is not

| Hypothesis | Test | Result |
|---|---|---|
| New pieces | Becker's field minus what covers it | 7 parts -> 5: fewer, not more |
| A neck closed for travel | The field inset at 0.075 / 0.15 / 0.25 / 0.4 mm | One component at every inset, both arms |
| The redraw's vertex density | Redrawn polygons simplified at 0.01 / 0.03 mm | Becker 15 / 15, MFab 24 / 25 |
| The shapes' net area | Each redrawn shape offset back to its source area | Becker 16, MFab 26 |

## What it is: where the edge sits

The redraw seats edges inside the source. On a 50 mm upscaled disc with `subpixel_edges` (shipped), the edge sits 0.065-0.088 mm inside the true circle (#1515). Growing every redrawn shape back out by about that much brings the trims back. The new option `outline_redraw_grow_mm` (built OFF) does exactly that.

| Job (baseline) | no redraw | redraw 0.75 | redraw + 0.07 mm |
|---|---|---|---|
| Becker hat large (main `cfb24d67`) | 15 | 20 | **15** |
| MFab hat (`cfb24d67`) | 20 | 27 | 21 |
| Becker LC large (`cfb24d67`) | 15 | 18 | 16 |
| Becker beanie (`cfb24d67`) | 17 | 15 | 14 |
| MFab LC (`cfb24d67`) | 23 | 24 | 21 |
| To a T machine hat (`cfb24d67`) | 23 | 24 | 21 |
| Becker hat large (`e1ff49b7`) | 13 | 17 | **13** (+0.035 mm: 14) |
| MFab hat (`e1ff49b7`) | 18 | 24 | 22 (+0.035 mm: 21) |

The same inward seat is the bare-fabric rise Kent accepted with the flag.

## Can the re-fit keep the old piece count? Not as built

By count, yes: the 0.07 mm grow takes every job to or below its no-redraw trims. By eye, no.

Sheets (`digitizer/eye_pairs_out/redraw-trims-1114/sheet_*.png`, primary checkout):
- Becker hat large with the grow reads like the redraw.
- **MFab hat's small line reads worse.** The white keyline round AND WELDING LLC fattens and the black letters thin out: 20,888 -> 20,019 stitches.

A uniform offset grows thin keylines as much as the bodies it was meant for. The next step would correct the fit's bias where the fit put it, along arcs (the disc is where it was measured), and not across every edge. So `outline_redraw_grow_mm` stays at 0.0. It is the instrument this doc measured with, not a candidate.

## CPU: the redraw's cost, cut without moving a number

Profiled on To a T machine hat, 27 of the redraw's 35 s went to 463k shapely `Point` constructions and single distance calls (`_cap_check`, `_worst_breach`, `_offenders`, `_any_far`).

Each now calls `shapely.distance(line, points)` over a 256-point chunk. That is GEOS's own per-pair distance in the same argument order, so every value is the same float. It keeps one Cancel seam per chunk, the 256-sample spacing `test_redraw_fit_seams` pins.

Every region's polygon WKB and redraw outcome is md5-identical on To a T machine hat, Becker hat large, MFab hat and Bridge hat. Generation time on a loaded laptop:

| Job | redraw before | redraw after |
|---|---|---|
| To a T machine hat | 31.8 s | 19.2 s |
| Becker hat large | 20.4 s | 8.3 s |
| MFab hat | 21.0 s | 10.0 s |
| Bridge hat | 19.5 s | 17.2 s |

Without the redraw, To a T machine's generation is 8.1 s, so the redraw's remaining cost is its fit (`densify_ring`, `_try_arc`, `_merge_runs`), not the cap checks.
