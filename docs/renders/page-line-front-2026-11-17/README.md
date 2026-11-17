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
