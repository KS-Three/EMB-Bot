---
name: logo-batch-2026-11-16
description: Kent 11-16 autonomy batch, 10 Commons logos — two more flags built OFF (silhouette_underfill_rim_fabric_edges, group_consistent_border_by_size); 6 of 10 designs change, 4 do not; arc small text, AA-blend thread and satin-floor faults seen and NOT fixed
metadata:
  type: project
---

Kent, 2026-11-16, after the NASA insignia trial
([[underfill-ground-guard-2026-11-16]]): "Let's do 10 more ... Save the
time/effort of explaining each image change to me. I only need to see the
FINAL before and after improvements." He wants the batch run without
per-image write-ups and one before | after at the end. (My reading: that is
how he wants this KIND of autonomous batch reported, not a change to the
flip-with-pictures rule.)

Ten public-domain logos from Wikimedia Commons, 960 px PNGs, Studio request,
left chest: NASA worm 100 mm, NOAA 90, Forest Service 80, National Park
Service arrowhead 75, Energy Star 85, EPA seal 90, USGS 100, FEMA 110, Python
80, recycling symbol 80. None of the art or renders is in the repo.

**Built, both OFF, PR #1608:**

- `silhouette_underfill_rim_fabric_edges`: the under-fill host's 1.75 mm satin
  rim skips every stretch of its visible outline another sewn shape shares
  and sews the rest as open arcs (`border_runs`). The rim was read off MFab
  and Fremont, whose outlines are the design's edge; among other shapes it
  made a raised halo (the arrowhead's orange ground round its tree).
- `group_consistent_border_by_size`: the size ring decided once per line of
  like shapes (`like_lines` + `follow` on the 6.0 mm floor). The worm's three
  shapes read 6.19 / 6.26 / 5.92 mm and sewed two ringed, one bare.

**Measured, before (main) -> after (guard ON + both flags ON), stitches:**
worm 8,293 -> 8,909; Forest Service 25,704 -> 24,223; arrowhead 30,074 ->
25,336 (trims 69 -> 71); Energy Star 29,637 -> 27,218; EPA 26,774 -> 25,291;
FEMA 9,657 -> 9,009. NOAA, USGS, Python and the recycling symbol are
byte-identical. The ground guard itself moved none of the ten.

**Seen and not fixed (real faults, each its own piece of work):**

- Small text on an arc: NOAA's 3.5 mm ring text loses N and E strokes in the
  Column lane; EPA's ring text sews as thin bean lines where the art is bold.
- An anti-alias blend sewn as a thread: Forest Service's gaps between letters
  quantize to a third colour ("Green Dust", about 30 slivers of 1.6-5 mm2,
  run stitch, one extra colour stop). The arrowhead has the same cone.
- Fat small caps: Energy Star's 1.1 mm strokes sew at the satin floor.
- FEMA's 35 mm seal is under what thread can draw; its eagle and ring text
  are noise at that size.
- Colour revisits: the arrowhead sews seven blocks for five threads.

**How to apply:** the flip of the two flags is Kent's, from the ten-logo
art | before | after sheet. A trap from this session: `r.jump` is True on a
real run reached by a jump, so a per-kind stitch census that skips
`r.jump` runs loses whole borders.
