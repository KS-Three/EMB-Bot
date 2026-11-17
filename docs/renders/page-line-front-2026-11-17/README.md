# `page_line_front`: ORIGINAL | BEFORE (OFF) | AFTER (ON), 2026-11-17

Prime grader fault, `gaulke_roofing_hat` (114 x 48 mm hat): the art's hairline white gap
under the inner roof sews as a wide white satin bar laid over the thin black line beneath it.

**Cause (traced by eye, stage by stage):** stage 1.3 `two_tone.keep_lines` (2026-10-08, built
so this same art's roof lines do not close to one black mass) hands a thin white channel
back as light ink and widens it to the satin floor into the ink either side. That white
then sews as a layer AFTER the black, so it covers the black line's edge and leaves a fringe.
The flag only changes the order: those regions take a front layer, so the black lays over
their edges. No width or fabric number moves.

**Sweep:** the 9 committed pro jobs (`tools.prime_grader.population()`), flag OFF vs ON.
**1 of 9 moved** (`gaulke_roofing_hat`, 7475 -> 7516 stitches); the other 8 are byte-identical
(becker_hat_large, hotel_fremont_hat, mfab_hat, precision_drone, tires_hat_3d, goldentee_hat,
toat_machine_hat, toat_beanie). **1 of 1 moved design is pictured**
(`gaulke_roofing_hat.png`, with `gaulke_roofing_hat_zoom.png` on the roof).

| design | verdict by eye |
|---|---|
| gaulke_roofing_hat | **Better, with a catch.** The fat white bar is gone on both slopes and the thin black line beneath is whole and separate. But the white gap is now a hairline that is broken in places, nearly closed along the slopes, where the art (and the pro's file) keep a clear thin white line. None got worse than OFF's fat bar by eye; it swaps "too much white" for "almost no white". |

Reproduce: OFF/ON via `pro_pair.digitize(art, width, garment, {"page_line_front": True})`,
rendered with `digitizer_core.stitchviz.render_design`.

## Second sweep: the 26 corpus fixtures, Studio request at 80 mm (director's check)

`tools.corpus_scorecard.FIXTURES` (26) at `studio_request(80.0)`, garment `left_chest`, flag
OFF vs ON, md5 of `design["stitches"]`. **1 of 26 moved**: `photo/logo_gaulke_roofing.png`
(5123 -> 5012 stitches). The other 25 are byte-identical. **1 of 1 moved pictured**:
`fixtures/photo_logo_gaulke_roofing.png`. Per-fixture rows: `fixtures/sweep26.json`.

| fixture | verdict by eye |
|---|---|
| photo/logo_gaulke_roofing | **Better.** OFF: the white roof bar, and the window's cross sewn as a white mass over the panes. ON: roof bar gone, black line whole, the window reads as four dark panes with a thin cross gap, as in the art. Same catch as the hat: the thin white gaps are hairlines, nearly closed in places. Not worse anywhere. |

## Sibling flag `page_line_open` (built OFF): leave the channel as bare fabric

**What the pro's light line IS** (read off `c golke logo hat.DST`, rendered at 30 px/mm): the file has
**0 colour-change commands** (one thread, black), so the light line is **bare fabric between two black
shapes**, not white thread. Measured across the chevron it is **0.73-0.83 mm** wide, between the roof
mass and a **1.17 mm** black line. The art's own gap is the same size (our white region measured 0.87 mm).

`page_line_open` therefore stops sewing the channel `keep_lines` found (default `stitched` False; a review
`stitched` still wins). No width, tolerance or satin-floor number is added or touched. OFF is byte-identical.

Sweeps (flag OFF vs `page_line_open` ON, md5 of stitches), pictures in `open/`:
- **9 pro jobs: 1 moved** (gaulke_roofing_hat, 7475 -> 6703 st), 8 byte-identical; 1 of 1 pictured
  (`open/gaulke_roofing_hat.png`, `open/gaulke_roofing_hat_zoom.png`).
- **26 fixtures at 80 mm: 1 moved** (photo/logo_gaulke_roofing, 5123 -> 4589 st), 25 byte-identical; 1 of 1
  pictured (`open/fixtures/photo_logo_gaulke_roofing.png`).

| design | verdict by eye |
|---|---|
| gaulke_roofing_hat | **Better than `page_line_front`, closer to the pro.** Fat bar gone, black line whole, and a fabric-coloured hairline now shows along both slopes and the window's cross. **Catch:** it is thinner than the pro's 0.73-0.83 mm line and broken in places: the black fills' own pull compensation eats into the channel. Widening it back would mean changing pull compensation, a physical constant (gate 1), so it is not done here. |
| photo/logo_gaulke_roofing | **Better.** Roof bar and white window cross gone; four dark panes with a thin cross gap. Same catch. |
