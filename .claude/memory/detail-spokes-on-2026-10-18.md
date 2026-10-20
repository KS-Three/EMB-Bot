---
name: detail-spokes-on-2026-10-18
description: detail_spokes flipped ON (Kent, "ON tightened"): MIN_TIPS 4, spoke floor scaled by design width; the Fremont OFF md5 depends on the host's SIMD (AVX-512 vs AVX2), not platform or test order; pin keyed on numpy AVX512F (PR #987)
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

**The md5 pin that was wrong THREE times.** #980 pinned the OFF stream's md5 per `sys.platform`
(Windows `75f44f90`, Linux `027d14e6`) because CI read a different value than Kent's box. Then
main went red at the #982 squash (a diff touching only `.claude/skills/`): Linux now read the
WINDOWS value on the same image, CPython and wheels. That was read as a test-order leak under
xdist, and #983 made the guard counts-only. **Also wrong** (PR #987, 2026-10-19): every shard 5/6
file run ahead of the digitize in one process, both worker orders, hash seeds, and four requests
through one service process all left the laptop's stream at `75f44f90`. No leak, no product
defect. The first CI run that recorded its CPU settled it: AMD EPYC 9V45 with numpy AVX512F/SKX/ICL
read `027d14e6`; AVX2 hosts (Kent's Ryzen 7 4700U, the other runners) read `75f44f90`. Hosted
runners draw different CPUs, and numpy/OpenCV dispatch AVX-512 kernels where present.
Pinning the TEST environment to AVX2 (`NPY_DISABLE_CPU_FEATURES`, `OPENCV_CPU_DISABLE` in
conftest) was tried and did NOT take: an EPYC 9V74 still enabled numpy AVX512F and OpenCV
AVX512-SKX and read `027d14e6`. So the pin holds two md5s keyed on numpy's AVX512F flag.

**Why:** two stories in a row fitted the evidence (platform, then test order) because no log
recorded the one variable that moved: the host CPU.

**How to apply:** when a stream md5 differs between CI runs of one image and one tree, record the
host CPU and its enabled SIMD before theorising (the pin test's junit properties do). Unexplained
"platform numerics" elsewhere (the three deselected goldens) may be the same cause. Related:
[[the-80mm-ink-link-2026-10-15]], [[bean-holds-on-2026-10-15]], [[windows-goldens-fail-locally]].
