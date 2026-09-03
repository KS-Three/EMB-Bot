---
name: fill-travel-under-cover-2026-09-03
description: defect 21 FIXED, default ON by Kent's flip (`fill_travel_under_cover`), 2:25 weight ratified — routing alone did nothing, the ORDER decides exposure; cover-aware column order + routing through the unsewn remainder took Fremont's fill-phase exposed travel 286 → 90 mm at 5 more trims, gaulke 204 → 8, sunset trims 53 → 42; two diagnostic traps (footprint slivers, containment at the bridge start), one review catch (unclipped endpoint allowance let routes leave the shape), one profiling find (`_ring_route` rebuilt its arc table per call); goldens untouched with the default off, the re-pin procedure proven
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

## The review catch, and the default

The endpoint allowance around a covered route's ends was unioned in
UNCLIPPED — a route could leave the shape by up to 2.5 mm and the scorer
rewarded it as a bridge (1.48 mm across a 1.5 mm slot, measured). Clipped +
hard shape containment on every covered route. A few cuts came back.

**Built OFF, flipped ON the same session by Kent** on the numbers below,
weight 2.0 ratified. The whitebg re-pins were done, reverted with the OFF
default, then redone for the flip — the recapture tool's pre-change guard
passed both times.

## Numbers to quote (after the clip fix, flag ON)

Fremont 286 → 90 mm (st 6473 → 6385, trims 47 → 52); gaulke 204 → 8 (24 →
26); drone 546 → 89 (86 → 91); sunset 711 → 344 (trims 53 → 42); meadow 691
→ 324 (33 → 35). The returning trims are the 2 : 25 exposed-vs-cut weight
buying hidden travel — the 2.0 is unanchored, Kent's to price. Flag off
md5-identical to main; suite failure set the three platform goldens only.

See also [[hotel-fremont-fine-details-2026-09-02]], [[real-artwork-trim-truth]]
(the trim-side framing), [[first-physical-sewout-2026-09-01]] (travel over
finished work seen on cloth).
