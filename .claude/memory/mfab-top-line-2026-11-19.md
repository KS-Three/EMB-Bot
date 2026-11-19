---
name: mfab-top-line-2026-11-19
description: MFab hat top line (M-FAB) nine grader faults sorted: 3 misreads, 1 gate-1 (A counter vs 5.0 mm satin ceiling), 5 one cause (satin-ladder junction: two offset bars where the art has one 3 mm block); `satin_overlap_run` (extra, OFF) drops hidden re-sewn satin, picture unchanged
metadata:
  type: project
---

2026-11-19, prime grader card `L_mfab_hat`, top line only. Evidence and table: `docs/mfab-top-line-faults-2026-11-19.md`.

- **Not the Column lane.** The white M-F-A-B is one enclosed-white field `S1a1cc475` sewn by the satin ladder
  (satin runs 563 / 252 + 310 / 426 / 532 points); the lane only sews the black small letters. The built-OFF lane flags
  (connectors_buried, junction_square, cover_handback, corner_fold_cap_flared, apex_pro(_joints)) leave MFab byte-identical.
- **Fault 5 is not a stray travel:** one 2.46 mm satin stitch of the F stem bridging a 1.65 mm gap where the dash bars join.
- **Real cause (1, 3, 4, 5, 8), NOT fixed:** a junction the art draws as one ~3.0 mm block is sewn as two 1.9 mm bars 0.5 mm apart plus fans.
- **Gate 1:** fault 6, the A counter's fill, is the 5.0 mm satin ceiling refusing `counter_fan_satin` at 104.9 mm: sew-out row 16.
- **Built OFF:** `cfg.extra["satin_overlap_run"]` (`column_overlap.py`): -126 stitches hat, -209 LC, trims unchanged, no bare cloth, the picture is identical (the hidden layer goes). Not a flip candidate; the sweep was not run.
- The pro file is in the committed zip. Like for like his density is about ours (B stem mean layers 5.3 vs 4.9; both two passes at 5-7 crossings/mm); an earlier "twice as dense" was a measurement error (midpoint step read as pitch). F4: ours 15 layers max (mean 4.8) vs his 9 (3.6). Junction build needs a satin-piece census of his file first. Sew-out row 17.
Related: [[counter-fan-2026-11-14]], [[off-line-mark-2026-11-18]].
