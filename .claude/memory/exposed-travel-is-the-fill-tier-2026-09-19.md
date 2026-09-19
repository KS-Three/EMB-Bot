---
name: exposed-travel-is-the-fill-tier-2026-09-19
description: travel_cover.py's 245 mm of exposed travel on the nine logos is NOT a new gate-3 finding — 97.7% is the fill tier's column bridges on their own finished fill (defect 21's residual, read by fill_bridges.py on 09-11), 0.0 mm on bare fabric; the 1 mm grid under-reads it by a third; `cfg.fill_bridge_cut` BUILT OFF (per-bridge cut at Kent's 25:2 rate, single-pass fills, 246.3 -> 141.1 mm for +6 trims); Fremont's OCR drop under it is judge noise
metadata:
  type: project
---

`tools/travel_cover.py` (2026-09-19, PR #516) read ~245 mm of travel with no
later thread over it and its write-up called that *"a pre-existing finding
this instrument is the first to read"*. Traced leg by leg the same day
(`digitizer/tools/travel_legs.py`): it is [[fill-travel-under-cover-2026-09-03]]'s
residual, already in MASTER_SCOPE defect 21 with its cause established.

- **Emitter:** 239.1 of 244.8 mm is `stage6_fill.stitch_shape`'s `emit`
  (the bridge between two fill columns of one shape). 5.7 mm is
  `satin_shape`'s `_graph_travel` walk. Stage 7's `_chain` and the
  `_junction_cover_runs` walk emit nothing — `chain_links` and
  `satin_patch_junctions` are both OFF. A TRAVEL run carries no tier;
  `travel_legs.py` reads the emitter off the construction call stack.
- **What it lies on:** every exposed fill sample is on that shape's own
  FINISHED fill, same thread. 0.0 mm on bare fabric, 0.0 on unsewn artwork,
  0.0 on another colour. So it is thread on top of tatami (defect 21), not
  DOCTRINE gate 3's letter.
- **The instrument under-reads.** "No later sewn segment within half a thread
  width" gives 375.0 mm where the 1 mm grid gives 239.1: a cell credits a leg
  running along a finished column's edge with the next column's thread.
  `fill_bridges` reads 432.3 on the same plans (full-row footprint). Also a
  bridge's two END steps belong to no run, so a 7.1 mm bridge can show as
  2.4 mm of travel.
- **Becker's 22.9 mm leg:** the straight 8.4 mm hop leaves the traced outline
  for 0.20 mm (a sliver notch), so `travel_path` laps the finished right leg
  on the inset ring, 24.5 mm on top.

**Why:** the next session reading "245 mm exposed" beside "gate 3" would
reasonably go hunting for bare-fabric thread in the satin or stage-7 code.
There is none; the work is in `stage6_fill`.

**How to apply:** before proposing anything for exposed travel, read DOCTRINE's
"last third of exposed fill travel" entry — three routing fixes and an
ordering arm are already priced out. The one arm not yet tried was priced
and then BUILT the same day, **`cfg.fill_bridge_cut`, DEFAULT OFF, Kent's
flip**: `emit` sewed any in-shape route however exposed and only lifted when
no route existed, so `_score`'s ratified 25 : 2 rate was never asked about a
single BRIDGE. Lifting a bridge whose own cost exceeds a cut (gap over
`trim_at`) takes the nine logos 246.3 -> 141.1 mm exposed for 471 -> 477
trims on the shipped euler order (244.6 -> 139.5, 587 -> 593 under
nearest), uncovered unchanged, OFF plan-md5-identical on all nine
(`tests/test_fill_bridge_cut.py`, 15, on shapely fixtures — Becker's leg
depends on a 0.20 mm notch in a trace, and traces differ by platform). Read
it with `tools/travel_legs.py --set fill_bridge_cut=true`.

**Two things the review round found, both about where a per-bridge rule
stops being true.** (1) Once the scorer lifts dear bridges, "nothing
exposed" no longer means "nothing to win": `_reorder_for_cover`'s early exit
kept a plan scoring 86.0 where flag-OFF's order scored 40.1 by the same
scorer. A flag justified by a rate must be checked for buying a DEARER plan
at that rate — price ON's result with ON's scorer against OFF's. (2)
Two-pass fills (crosshatch, density boost): the sewn footprint cannot tell
pass-one fill that pass two will cover from finished fill, so every pass-two
bridge read as exposed (trims 0 -> 2 on a plate, hiding nothing). The rule
is single-pass only; exposure per pass is unmeasured, and that — not the
flag — is the open item for the photo lane.

**The trap that nearly went in the record as a cost:** Fremont gains
`LETTERING_ILLEGIBLE` under the flag (tagline OCR 0.50 -> 0.27). The
tagline's own 13 runs are byte-identical; two of the white FIELD's bridges
ran through the tagline band and are now cut, and tesseract swapped one
noise string for another on lettering lost under both arms (`VAT] CY § Pw`
at confidence 46 scored exactly 0.50 and PASSED a `>=` line). Drone moved
the other way. When the OCR judge moves, diff the cluster's own runs and
dump its crops (`legibility.measure(..., dump=)`) before believing it — and
read logs with Python, not `grep`: the `§` made grep call the log binary and
silently drop the one line that mattered, which looked like state leaking
between arms. Full record: `docs/scope-history.md`, 2026-09-19, "the
exposed travel legs" and its addendum.
