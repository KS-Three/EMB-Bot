---
name: sew-white-areas-2026-10-21
description: Rule R11 built OFF as a customer option — "Sew white areas" (Studio Advanced) / `cfg.sew_enclosed_white`; counter vs field rule; Becker matches the pro, Machine's field doubles trims
metadata:
  type: project
---

Built 2026-10-21 (one of four builds Kent asked for with "All of them" on the pro-rules
doc). Write-up: `docs/sew-white-areas-2026-10-21.md`; code `digitizer_core/enclosed_white.py`.

- **Counter vs field is decided by tags, not shape.** Counter = untagged enclosed white
  whose immediate encloser (the region whose HOLE holds it) is a text-cluster letter
  (`text_candidate`, or `word_id` under `lettering_words`). Hollow-letter bodies (Becker)
  are themselves `text_candidate` → field. `lettering_group` alone is NOT a letter: it
  tagged Golden Tee's ball-arc outline. Geometry (thickness ratio, solidity) cannot tell
  a thin-stroke O's counter from a hollow letter; the tags could, on all 4 jobs.
- A counter inside a sewn field sews with it (Machine's script counters, MFab's A/B).
- Option areas go to new FRONT layers (repeated cone, pro's R12/R13).
- **Open catch:** Machine badge 49 → 109 trims: the field is cut round 26 letters and
  sews in pieces. The pro lays one fill under the letters. The fix is in stage 5 (a sewn
  field ignores the holes that later layers cover), not in this option.
- Fremont needs nothing: the gradient lane already sews its hexagon field.
- **Trap hit:** a mutation test on an UNTRACKED file cannot be undone with
  `git checkout`, and a background `pro_pair` that started during the window imported the
  mutant (Becker's md5 differed). Back up the file first, and rerun anything that started
  during the window.

**How to apply:** the default thread (white) and the UI wording are Kent's, asked at the
end of the PR. Do not flip this to default-on: it changes the design (Kent, 2026-10-21).
