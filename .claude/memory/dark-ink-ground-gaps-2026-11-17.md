---
name: dark-ink-ground-gaps-2026-11-17
description: dark_ink_refuse_ground_gaps (cfg.extra, built OFF 11-17) - the field between light letters was read as dark pen strokes and sewn as a bean in a second thread; Forest Service 3 -> 2 threads, Energy Star 3 -> 2 blocks; Fremont and hed p.e. keep every stroke; flip is Kent's
metadata:
  type: project
---

Kent, 2026-11-17: "Do whatever you think needs to be done ... digitize the
logo flawlessly." Picked up the 11-16 logo batch's "seen and not fixed" list
([[logo-batch-2026-11-16]]) on the same ten Commons logos (960 px PNG, Studio
request, left chest).

**The 11-16 note's cause was wrong.** It called Forest Service's third thread
"an anti-alias blend sewn as a thread". Stage 2 is clean there: two kept
colours, four blend clusters at edge fraction 1.0, all dissolved. The third
thread comes from `thin_ink.carve_flat_dark_ink` (`flat_light_text_runs`, ON
since 11-07). Its lightness read keeps a thin dark component ringed by one
lighter ground. Light lettering on a dark field is that picture inside out:
the strip of field between two letters, and a letter's counter, are thin,
dark and ringed by one lighter colour. Thirteen were carved as pen strokes,
re-snapped from their edge pixels (5643 Green Dust beside the field's 5324
Bright Green) and sewn as bean lines.

**Built OFF: `cfg.extra["dark_ink_refuse_ground_gaps"]`**
(`thin_ink.refuse_ground_gaps`, `tests/test_dark_ink_ground_gaps.py`). A
component is the ground, not a stroke, when on the quantiser's label map
(1) its majority label is not its ring's label, (2) the ring's shapes are
themselves surrounded mostly by the component's label, and (3) the largest
body of that label there is larger than those shapes together. No new
constant.

**Measured, OFF -> ON:**
- Forest Service 80 mm: 3 -> 2 threads, 24,223 -> 23,860 stitches, trims
  41 -> 22.
- Energy Star 85 mm: 3 blocks -> 2 (the blue spool was revisited for 57
  stitches), 27,218 -> 26,969 stitches, trims 14 -> 12.
- The other eight of the ten: byte-identical renders and counts.
- Stage-2 census, flag ON, 80 mm, repo logos: Fremont patch 34 read / 34
  kept, hed p.e. 3 / 3; the other 13 (Golke, MFab x2, To a T x2, the Commons
  lettering set) have no dark read. So none of them moves.

**Catches.**
- Energy Star's top field changes fill angle (rows ~100 deg -> ~55 deg; its
  two sibling fields are at 0 and 175). It was already off from its siblings
  before; the flag hands it back two 1.8 mm2 corner slivers and the angle
  picker lands elsewhere. A fill-angle fault of its own, not fixed.
- `testdata/reference/becker_*.jpg` (the pro's preview pictures, not customer
  art) do move: one thread fewer on each, trims 99 -> 95 and 49 -> 47, and
  the A of MARINE's counter shows bare where a bean loop sat. Not a job the
  product is asked for; look before a flip all the same.
- The paired corpus in `scratch_kent/` is not in a cloud checkout: the 22-job
  combined check was NOT run.

**Also this session:** `plan_stitches` held 21 managers in one `with`;
Python 3.12.3 (every cloud container) allows 20 nested blocks, so the engine
did not import there while CI's later 3.12 stayed green. Now one
`ExitStack` (PR #1615, `tests/test_with_nesting.py`). Add a scope as one
`_enter(...)` line; `floor_scopes` no longer needs to fold two.

**Not fixed, seen again:** small lettering on an arc sews fat and fuses
(Forest Service's DEPARTMENT, 4.5 mm caps); NOAA / EPA ring text.
