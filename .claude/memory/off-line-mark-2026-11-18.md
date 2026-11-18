---
name: off-line-mark-2026-11-18
description: MFab's pointed mark at the big M's inner V was tagged into the AND row and sewed as 2 crossing lane satin pieces; lettering_columns_off_line_mark sews a stacked, close, off-line cluster member as fill; ON 11-18 (Kent "Flip ON"); 1 of 35 runs moves
metadata:
  type: project
---

2026-11-18, prime grader scorecard (`mfab_hat`, pins 16.0/21.5 and the N at 16.0/27.5).
PR #1656, lane `claude/prime-fix2-mfab-inner-v`.

- **Stage:** stage 4 text tagging, then the Column lane. The mark's polygon is fine (11 vertices,
  12.4 mm^2). The tagger put it in the "AND" cluster (letters y 24.8-33.3, mark centre 23.8); the
  lane sewed two satin pieces at different angles that cross and overshoot onto the white legs.
  Handed back to the ladder alone it is still satin (`classify_ribbon`: ribbon_w 1.22, aspect 7.3),
  so the tag also sets tier fill.
- **Existing flags:** `lettering_columns_cover_handback` leaves the stitches byte-identical;
  `photo_work_grid` moves the fault (stays OFF).
- **Fix:** `lettering_columns_off_line_mark`: a cluster member that shares no line with any mate
  (< 50% vertical overlap), is glyph-sized, is stacked over a mate (>= 50% of its width) within 0.25
  of the mates' median height, and is not a centred dot takes fill. ON by Kent's flip ("Flip ON
  (Recommended)"); `conftest.OFF_LINE_MARK_2026_11_18_OFF` pins it.
- **The first version was withdrawn:** a median-band rule moved 8 of 35 (Gaulke 20 shapes, phone
  screenshot 31); the per-mate line test moved 2, but one was Toat Machine's i-dot (an oval, lost its
  lean). Separation measured: MFab 0.99 mm from the N it stacks over (0.12 of mates' height), Toat's
  tittle 13.6 mm from the nearest cluster member (2.0).
- **Caveats:** rests on one logo; the 0.25 threshold comes from two measurements; the classic-dot
  exemption is unit-tested only; not sewn on cloth; MFab rendered without `rembg_isolated`.
- Sweep: `python -m tools.off_line_mark_sweep`. Evidence: `docs/renders/lettering-columns-off-line-mark-2026-11-18/`.
Related: [[thin-arm-stop-2026-11-17]], [[lettering-ribbon-handback-2026-11-16]].
