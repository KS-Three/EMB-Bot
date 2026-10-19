---
name: detail-spokes-on-2026-10-18
description: detail_spokes flipped ON (Kent, "ON tightened"): MIN_TIPS 4, spoke floor scaled by design width; the per-platform md5 pin was a misdiagnosis (test-order leak), guard is counts-only until the leak is found
metadata:
  type: project
---

# The Wisconsin star sews as the pro's asterisk — ON since PR #983 (main 897460d6, 2026-10-18)

**What shipped.** `cfg.detail_spokes` defaults True (PR #983, Kent's call 2026-10-16: "ON, tightened").
A sub-floor region of another colour enclosed nine tenths by one shape, with >= `detail_spokes.MIN_TIPS`
= **4** tips, sews as one out-and-back spoke run on top of its host, in the first later block of its
thread (Fremont: the white edge cap, no colour change). Spoke floor =
`machine.DETAIL_SPOKE_MIN_MM` 1.45 x width / `machine.DETAIL_SPOKE_REF_WIDTH_MM` 92.6
(`stage7_sequence.spoke_floor_mm`): 1.25 mm at Kent's 80 mm, every spoke end inside the state
(ENE 0.13 mm inside; the fixed 1.45 floor of #980 put it 0.04 mm past the edge). Fremont Hat 80 mm:
14,824 / 43 OFF -> 14,843 / 44 ON, +19 stitches, one trim. MIN_TIPS 3 -> 4 refused the one false
positive (a 3-tipped tyre-tread speck on the phone screenshot); 14 of 17 corpus designs byte-identical.
Renders: `docs/renders/detail-spokes/`. Both constants are read from the pro's sewn Hat PES
(gate 1 candidate, unsewn); the width scaling is Kent's ruling, not the pro's.

**The md5 pin that was wrong twice.** #980 pinned the OFF stream's md5 per `sys.platform`
(Windows `75f44f90`, Linux `027d14e6`) because CI read a different value than Kent's box. Then
main went red at the #982 squash (a diff touching only `.claude/skills/`): Linux now read the
WINDOWS value. Same runner image (ubuntu-24.04 20261012.334.1), same CPython 3.12.15, same wheels,
same Python code as the green run before it. So the hash depends on which tests ran earlier in the
same xdist worker, not on the platform. Counts never move (14,824 / 43); the difference is
coordinates or order. #983 replaced the pin with a counts-only guard so main could go green; the
leak itself was still unfound on 2026-10-19 (hunt dispatched as its own session, branch
`stream-order-leak`).

**Why:** a per-platform pin is the easy story when CI disagrees with a laptop, and it was wrong
here; the tell was one platform reading both values on identical code.

**How to apply:** when a stream md5 differs between CI and local, compare two CI runs on the
same code before pinning per platform. If one platform reads two values, it is shared mutable
state under xdist (or in the long-lived service), never the OS. The counts-only guard in
`test_fremont_80_off_is_byte_identical` is a stopgap: restore the single-value md5 once the leak
is fixed. Related: [[the-80mm-ink-link-2026-10-15]], [[bean-holds-on-2026-10-15]],
[[windows-goldens-fail-locally]].
