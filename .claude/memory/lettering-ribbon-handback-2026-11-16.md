---
name: lettering-ribbon-handback-2026-11-16
description: `lettering_columns_ribbon_handback` (built OFF): a Column-lane member whose ordinary ribbon verdict is fill sews down the ladder. Fixes Texaco disc wedges and Adidas' small bar, but the census says 31 of 39 fill-verdict members are REAL letters (Becker, Visa, Canon, USGS)
metadata:
  type: project
---

Lettering ribbon hand-back, 2026-11-16 (builder worker; flag built OFF, flip is Kent's).

**Fault.** A non-letter tagged into a text cluster (`textcluster.py`) is routed to the Column lane (`columns.is_lettering`), which skips `classify_ribbon`, so a solid sews one fanned satin column. Texaco's red-disc wedges (`dt_p90_cap` 6.2 vs 5.0; `dt_irregular` 0.527/0.518 vs 0.5) and Adidas' smallest bar (`width_cap` 5.601 vs 5.0, 144.9 mm2, split satin with slits).

**Rule.** `stage7_sequence._ribbon_handback`: lane member (`is_lettering`, tier auto) whose `classify_ribbon` at the ORDINARY ceiling (not the lettering split's open one) is fill, and not `photo_width_floor`, takes the ladder as if untagged (`handed_back`, ordinary ceiling, `_border_by_size_width(untagged=True)`). Tags stay. Tests: `tests/test_lettering_ribbon_handback.py` (synthetic slab/wedge).

**Census** (43 jobs: 22 pro_baseline + 21 logos; 34 have lane members): 509 members, 39 fill verdicts (dt_p90_cap 23, width_cap 8, dt_irregular 5, aspect 2, photo_width_floor 1). Real letters by eye: 31 (Becker M N R A E I x5 jobs, Visa S A V I, Canon e m m a o, USGS G U S S). Not letters: Adidas bar 1, Gaulke window bars 2, MFab 2, Texaco 3.

**ON vs OFF** (stitches/trims): Texaco 3771/7 -> 4614/10 (p90-only 4050/8, irr-only 4335/9); Adidas 6829/8 -> 7212/8 (slits gone; p90 and irr change nothing); Visa 4385/5 -> 9550/10; Canon 3344/5 -> 7480/10; Becker hat large 16269/17 -> 19902/26; USGS 7887/19 -> 9764/24. So the plain rule also moves real bold letters off the lane: Kent must see the sheets before any flip; a narrower rule (not letters: e.g. only members whose neighbours are not a word of like size) is untried.
