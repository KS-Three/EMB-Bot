# Defect 28 leftovers: three chart limits, nothing built (2026-11-10)

Main 333147fd, Windows, 80 mm, `corpus_scorecard` fixtures, `digitize` then
`run_preflight`. Picked by Kent 2026-11-10 after `blend_shade_median`
(`docs/blend-shade-median-2026-11-09.md`). Reproduce with
`digitizer/tools/thread_chart_floor.py` (default fixtures, `--garment hat_front`).

## Result

Every `THREAD_MATCH_POOR` block left on these three is a **chart limit**: on each
judged row, no spool on the whole 398-spool Isacord chart gets under the 10 dE00
block line. The grader scores each row with the median of per-pixel CIEDE2000.
On these rows the pixels themselves spread 20-40 dE00, so even the best possible
single thread sits past 10. **No flag was built**, because no thread change
clears a single block.

Both garments give the same rows, shape ids and numbers.

| target | blocks / garment | thread | row (footprint) | assigned dE00 | best loaded | best on chart | pixel L* p5/50/95 | verdict |
|---|---|---|---|---|---|---|---|---|
| `logo_bridge_bar` (flat) | 3 | 0020 Black | S4fdc326d (10.1 mm2) | 19.3 | 0020 19.3 | 1375 11.4 | 4 / 20 / 55 | chart limit |
| | | 3830 Surfs' Up | S02f2a28d (9.6 mm2) | 11.6 | 3830 11.6 | 4410 11.1 | 45 / 54 / 81 | chart limit |
| | | 4442 Deep Sea Blue | Se7155129 (5.0 mm2) | 10.6 | 4442 10.6 | 4442 10.6 | 46 / 57 / 86 | chart limit |
| `screenshot_phone_ui_golke` (flat) | 1 | 0111 Whale | Sa076f56d (8.4 mm2) | 19.8 | 0111 19.8 | 1776 12.2 | 2 / 35 / 77 | chart limit |
| `photo_subject_stub` (photo_subject) | 1 | 0722 Khaki | S83d298e8 shade 0722 (1,237 mm2) | 33.7 | 0722 33.7 | 0111 29.4 | 23 / 57 / 89 | chart limit |

The brief's "2 blocks" for `0722` is the two garments: one per garment. Bridge's
fourth eligible row (`Sce6e83e2`, 3830, 10.2) already wears the best chart spool.

## Cause, per target

**`logo_bridge_bar`, 0020 Black.** Row S4fdc326d is part of the black wheel ring,
on the side that touches the yellow disc. The JPEG's chroma subsampling bleeds
yellow into it: b* p50 17.7, p95 36. The pixels' median colour is 9.3 from
1375 Dark Charcoal, but per pixel the best any thread can do is 11.4. The art
means black, the quantizer kept it black, and the region carries no
`thread_resnapped_de00` stamp, so no stage changed its thread. This is a
grader-versus-JPEG floor, not a wrong thread.

**`logo_bridge_bar`, 3830 / 4442.** These rows are the thin cyan "BAR &
RESTAURANT" letters and the teal waves, laid on yellow. Anti-aliased edges carry
L* from 45 to 86 inside a 5-10 mm2 eroded footprint. The assigned spool is the
chart's best per pixel (4442), or 0.5 dE00 off it (3830 against 4410, which is
not loaded). The colour cap stage holds 4410 out, but loading it would leave the
row at 11.1, still a block.

**`screenshot_phone_ui_golke`, 0111 Whale.** Row Sa076f56d is the truck's
pen-hatched shading: black strokes on white, L* 2 to 77 inside one region. Its
median colour is 1.0 from 4174 Charcoal, which is not loaded. The region sits in
the grey cluster that snaps to Whale, and no resnap stamp is set. Per pixel no
thread gets under 12.2 (1776 Blackberry). Whale is also the closer match to the
hatch's optical average, which is lighter than its median pixel. So a darker
re-snap would cut the dE00 and still leave the block, and it might read worse
in thread.

**`photo_subject_stub`, 0722 Khaki.** The fixture is uniform RGB noise, a
synthetic stage-0 classifier stub (`tests/test_stage0_classify.py`), not
artwork. It sews one spool, so the photo route's excess yardstick has no
alternative and falls back to raw (`len(loaded) > 1`). Khaki is the nearest
thread to the noise's median colour (6.0-6.8). Per pixel the best spool on the
chart is 0111 at 29.4. No single thread can match noise, and this is what the
finding should say.

## What was not built, and why

- **A re-snap flag** (each row to its best-chart or median-colour thread). It
  lowers the reported dE00 (bridge 0020 19.3 to 11.4, screenshot 19.8 to 12.2)
  and clears 0 blocks. It also adds cones above the colour cap and, on the
  screenshot, darkens a tone whose optical average is lighter. Fails "fix what
  moves a block".
- **Flat-lane yardstick scored on excess over the best CHART thread.** This
  would clear all six flat blocks: bridge 0020 becomes a warn at 7.9, the
  screenshot a warn at 7.6, and 3830/4442 go silent. On the stub's raw path it
  would leave 4.4, under the warn line. It reverses Kent's ruling that the flat
  lane stays on raw distance (`thread-match-excess-gradient-2026-10-29`
  memory). That is a yardstick decision for Kent, priced here and not proposed
  by this note.

## Open

The message these findings print says *"Pick a closer thread or a different
brand"*, and on all five rows no closer thread exists on this brand. Saying so
in the finding would be a wording change only; `corpus_scorecard` diffs
`code:severity`. Not done here.
