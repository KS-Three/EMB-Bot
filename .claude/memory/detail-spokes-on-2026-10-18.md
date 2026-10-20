---
name: detail-spokes-on-2026-10-18
description: detail_spokes flipped ON (Kent, "ON tightened"): MIN_TIPS 4, spoke floor scaled by design width; the Fremont OFF md5 follows Intel IPP's code path inside the OpenCV wheel (l9 / k0 / k0-capped), not numpy, OpenCV's kernels, OpenBLAS, platform or test order; the test env is capped at OPENCV_IPP=avx2 (2026-10-20)
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

**The md5 pin that was wrong FOUR times.** #980 pinned the OFF stream's md5 per `sys.platform`
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
AVX512-SKX and read `027d14e6`. So #987 pinned two md5s keyed on numpy's AVX512F flag.
**Wrong a fourth time (2026-10-20):** an Intel Xeon @ 2.80GHz (Cascade Lake class, AVX512F)
read a THIRD value, `050452`, under that key. Measured on an AVX-512 Sapphire Rapids Xeon with
CI's wheels, every candidate forced down in turn: numpy's dispatch (X86_V4 / ICL / SPR off),
OpenCV's own AVX512-SKX kernels (`OPENCV_CPU_DISABLE=AVX512-SKX`, the hyphenated spelling it
accepts; #987's `AVX512_SKX` was ignored as unknown) and OpenBLAS's core type (HASWELL /
SKYLAKEX) all left `027d14e6`. **Intel IPP, bundled in the OpenCV wheel, is the mover:**
`OPENCV_IPP=avx2` read `75f44f90` (Kent's value), `OPENCV_IPP=avx512` (IPP capped at the base
AVX-512 set) read `050452` byte-for-byte, `sse42` and `disabled` read two more. IPP's k0 path
sub-dispatches on the newer AVX-512 extensions, so Zen 4 and Sapphire Rapids agree and Cascade
Lake does not. numpy 2.5 also refuses `NPY_DISABLE_CPU_FEATURES=AVX512F` outright (its groups
are `X86_V3 X86_V4 AVX512_ICL AVX512_SPR`) — the numpy key was a bystander. Kent's call
2026-10-20: `tests/conftest.py` caps the test environment at `OPENCV_IPP=avx2` (OpenCV reads it
lazily, on IPP's first use, so import order cannot defeat it); the pin is ONE md5 again, with
`test_test_environment_caps_ipp_at_avx2` as the tripwire and IPP's path in the junit `host_cpu`
property. The shipped service is not capped.

**Why:** three stories in a row fitted the evidence (platform, test order, "SIMD class") because
no log recorded the variable that moved — first the host CPU, then IPP's path within it — and
the env-pin attempt was judged "did not take" on a misspelled OpenCV name and a numpy switch
that was never the mover.

**How to apply:** when a stream md5 differs between CI runs of one image and one tree, read the
junit `host_cpu` property's IPP line first: `(l9)` means the cap took and the engine moved.
Forcing a library down with an env var proves it is the mover only when the library confirms the
switch took (`cv2.ipp.getIppVersion()`, `cv2.getCPUFeaturesLine()`'s `?` marks, numpy's
`__cpu_features__`), and a switch that "did not take" wants the library's own spelling checked
before a second CI draw. The two deselected enthusiast goldens are NOT the same cause: capped
at Kent's path on the AVX-512 Xeon, a full run still failed exactly those two (2026-10-20, PR #1006).
CI's draws after the cap (runs 3218, 3227) landed the pin on an AVX2 EPYC 7763, so an AMD AVX-512
draw is still owed; the tripwire names the host when it comes. Related:
[[the-80mm-ink-link-2026-10-15]], [[bean-holds-on-2026-10-15]], [[windows-goldens-fail-locally]].
