---
name: flip-proof-pins-2026-10-27
description: "2026-10-27 — W5-06b: FLAT_GOLDEN_MD5 derived from the golden json, a dated frozen-engine snapshot tests/engine_2026_10_27.json spread by frozen_cfg(), and test_pins_are_frozen.py refusing an unfrozen md5 pin"
metadata:
  type: project
---

# Flip-proof pins (W5-06b) — 2026-10-27

A default flip used to cost hours of CI: #1112's first round failed 128 tests, 79
of them ONE moved flat-lane golden pasted as a literal into 16 files; #1057 took
86 commits re-pinning OFF tests that landed meanwhile. Test-only; no engine
change, zero hash values moved (CI green with no pin edits was the proof).

**What exists now.**
- `conftest.FLAT_GOLDEN_MD5`: md5 of `testdata/flat_lane_golden.json`'s
  `stitch_coords`, three fixtures, derived at import. The 17 files that held the
  literal read it (`GOLDEN_MD5 = FLAT_GOLDEN_MD5`). The tests that compare the
  SHIPPED engine to it ride the defaults on purpose: a flip that recaptures the
  golden moves them in one place.
- `tests/engine_2026_10_27.json`: `PipelineConfig`'s DECLARED defaults
  (`dataclasses.fields`), a FILE, never computed. NOT `asdict()`: that records the
  seven `SMALL_TEXT_TRUE_SIZE` fills, and a later `setattr(small_text_true_size=
  False)` could no longer clear them. `frozen_cfg(**kw)` spreads it (a bare
  `PipelineConfig(**ENGINE, k=v)` raises when `k` is in the snapshot).
- `tests/test_pins_are_frozen.py`: refuses a test file that pins a 32-hex digest of
  an engine run and spreads no frozen dict (`frozen_cfg`, `ENGINE_*`, `PRE_FLIP`,
  `FLIP_*`, `*_OFF`). A pin ABOUT the default carries `# pin-rides-defaults: why`
  or an entry in `RIDES_DEFAULTS`. It also fails when a snapshot lacks, or
  names a stale, `PipelineConfig` field.

**Roll-forward rule.** A new field (a flag built OFF, or a flip that makes one
default-on) goes into `tests/engine_*.json` with its PRE-flip value in the same PR;
the guard fails loudly until it does (#1127 landed first and made
`small_text_reset_grow_away` a field defaulting True; the guard caught it on the
merge and the snapshot gained `false`). After a flip wave write a NEW dated file
from `dataclasses.fields` (never edit in place), point new pins at it, and leave old
pins on theirs.

**The trade.** After a flip, a converted pin no longer runs the engine that ships.
Only the default-riding goldens prove the shipped path: `test_flat_lane_byte_
identical`, `test_photo_lane_byte_identical`, and every test comparing a run to
`FLAT_GOLDEN_MD5`. Keep at least one of those per lane.

**Not covered.** Truncated pins (`digest[:8]`, tuples) have no md5 literal for the
scanner to see; re-pin them with `tools.ci_repin RUN_ID` (see
[[ci-pin-hygiene-2026-10-25]]) and spread `frozen_cfg` when next editing one.
Earlier partial freezes: [[flip-eight-2026-10-23]].
