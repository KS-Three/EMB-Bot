---
name: lettering-thread-2026-11-01
description: Drone's lettering gap was thread, not construction -- `lettering_stray_word_thread` + `lettering_contrast_floor` built OFF, stray ON 11-02 (Kent); AND DRONE 0.00 -> +1.00, PRECISION +0.05 -> +0.58 on a light hat, no new cone; letters on sewn ground exempt (MFab)
metadata:
  type: project
---

Kent 2026-11-01: Precision Drone's hat is LIGHT; "Build both OFF". `digitizer_core/lettering_thread.py`, called in
`finish_generation` before the cap's second pass. Thread only, on the region, as the cap does.

**Proof before code.** Recolouring ours.json's blocks, every stitch untouched: PRECISION 204 -> 135 grey cc +0.05 ->
+1.00; A's thread merged into its word AND DRONE 0.00 -> +1.00. Real digitize with both ON (`garment_rgb` 235,232,223)
is PRECISION +0.58 / reach 3.89 (pro +0.82 / 3.74), AND DRONE +1.00 / 2.32 (pro +1.00 / 3.16); it lands on 140 grey,
paler than the 135 trial, because the floor prefers a cone already on the design. 7 cones before and after.

**What it was not.** Not a word split across a cluster: all 16 pairs' clusters are one thread bar a dE 8.5 sliver. The
A alone was a `small_text_stray`, the only stray on the board (18.2 dE00 off its word). Counters already stay open.

**Floor trap.** First build moved MFab's white letters: they sit on the black badge, not fabric (+1 cone, AND WELDING
0.44 -> 0.00). `_on_sewn_ground`: covered 1.00 on every MFab cluster, 0.05-0.14 on Drone's. After it MFab and Fremont
are unchanged. 15 dE00 is one line of evidence (PRECISION 7.7; Fremont tan reads at 21.4). The other 12 pairs were
not digitized with the flags. The pro's thread colours are mostly unknown (DST), so this is ours, not his rule.

**Flip, Kent 2026-11-02 "Stray only".** `lettering_stray_word_thread` ON; `PRE_FLIP` pins it False. All 16 pairs, both
garments (natural 235,232,223 and black 20,20,20): only Drone moves (AND DRONE cc 0.00 -> +1.00, reach 0 -> 2.32);
columns, trims, stitches, widths identical. The floor stays OFF: on black it recoloured dark letters off the art
(Becker beanie 10+ cc 1.00 -> 0.59, +6 trims in letters); cause not traced.
Related: [[lettering-board-v3-2026-10-31]].
