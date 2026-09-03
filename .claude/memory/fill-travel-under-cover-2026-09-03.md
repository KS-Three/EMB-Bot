---
name: fill-travel-under-cover-2026-09-03
description: defect 21 fixed default-on (`fill_travel_under_cover`) — routing alone did nothing, the ORDER decides exposure; cover-aware column order + routing through the unsewn remainder took Fremont's fill-phase exposed travel 286 → 92 mm, gaulke 209 → 8, sunset trims 53 → 30; two diagnostic traps (footprint slivers, containment at the bridge start), one profiling find (`_ring_route` rebuilt its arc table per call), goldens re-pinned via the pre-change worktree
metadata:
  type: reference
---

Full record: `docs/fill-travel-under-cover-2026-09-03.md`. Kent's pick after
the Hotel Fremont notes; the in-fill complaint was 22 of 27 fill-phase travel
runs laid on top of finished columns.

## The finding that reordered the work

**Routing alone moves nothing.** Two routing attempts (shape's own inset
ring both ways; the unsewn remainder's own rings) each measured Fremont
**286 → 286 mm**. The inset ring runs through sewn columns, and by the time
a bridge is built there is no unsewn ground between its ends — **exposure is
decided by the column ORDER**. The cover-aware order (`_reorder_for_cover`,
nearest column whose straight bridge is off the fill laid so far, scored by
`_order_cost` = cuts × 25 + travel + exposed × 2, never accepted worse, last
path pinned) is the lever: 286 → 164 → 92 mm with shorter-way-first.

## Diagnostic traps that cost an hour

- A **half-row buffer of a zigzag path leaves slivers** between the legs;
  `cover − sewn` came back as 110–230 parts and every candidate route failed.
  Full-row buffer of a half-row-simplified path.
- **Containment fails at the bridge's first point**: `a` is the last
  penetration of the column just sewn, inside `sewn` by construction. Allow
  one travel stitch around each endpoint (`_EXPOSED_TOLERANCE_MM` =
  `TRAVEL_STITCH_MM`).
- "ahead"/"back" is not "shorter"/"longer" — `_ring_ways` orders them.

## Profiling find, independent of the feature

`_ring_route` rebuilt its cumulative arc table on every call: **34.8 s of a
90 s profile** on `photo_sunset_backlit`, the hottest function in stage 6
before this change existed. Cached per ring (`_ring_arc`, lru on the
geometry). Sunset still costs +49% with the flag on (33.6 → 50 s; the covered
scoring pass twice per shape); logos +7–11%.

## Numbers to quote

Fremont 286 → 92 mm (stitches 6473 → 6394, trims 47 flat); gaulke 209 → 8
(trims 24 → 21); drone 546 → 61 (stitches −6%, trims 86 → 90 — the score
bought 570 fewer travel stitches for 4 cuts); sunset 711 → 291, trims 53 →
30; meadow 691 → 301, trims 33 → 27. Flag off md5-identical to main.
Goldens: `logo_whitebg` 2166 → 2162 (travel only), re-pinned with
`recapture_flat_lane_key.py --pre-change-tree` (machine OK, control OK) and
`GOLDEN_FLAG_OFF[left_chest]`; `towel` unchanged by this engine, still the
known red. Suite failure set: the three platform goldens only.

See also [[hotel-fremont-fine-details-2026-09-02]], [[real-artwork-trim-truth]]
(the trim-side framing), [[first-physical-sewout-2026-09-01]] (travel over
finished work seen on cloth).
