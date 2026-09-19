---
name: exposed-travel-is-the-fill-tier-2026-09-19
description: travel_cover.py's 245 mm of exposed travel on the nine logos is NOT a new gate-3 finding — 97.7% is the fill tier's column bridges on their own finished fill (defect 21's residual, read by fill_bridges.py on 09-11), 0.0 mm on bare fabric; the 1 mm grid under-reads it by a third; one arm priced (per-bridge cut at Kent's 25:2 rate, 244.6 -> 139.5 mm for +6 trims), not built
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
ordering arm are already priced out. The one arm NOT yet tried was priced
here and is Kent's call: `emit` sews any in-shape route however exposed and
only lifts when no route exists, so `_score`'s ratified 25 : 2 rate is never
asked about a single BRIDGE. Lifting a bridge whose own cost exceeds a cut
(gap over `trim_at`) takes the nine logos 244.6 -> 139.5 mm exposed for
587 -> 593 trims, uncovered unchanged — but Fremont's tagline OCR read-back
falls 0.50 -> 0.27 (it sat exactly on the warn line) with no mechanism
established, so render before any flip. Full record: `docs/scope-history.md`,
2026-09-19, "the exposed travel legs".
