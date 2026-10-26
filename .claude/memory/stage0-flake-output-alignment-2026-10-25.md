---
name: stage0-flake-output-alignment-2026-10-25
description: "2026-10-25 — W3-13: the stage-0 determinism flake was cv2.magnitude (Intel IPP AVX2) following its OUTPUT buffer's 32-byte alignment, not float32 boxFilter/mean or threads; `_magnitude` in float64, no threshold moved"
metadata:
  type: project
---

# Stage-0 flake: the answer followed the heap (W3-13, 2026-10-25)

`test_stage0_classify.py::test_same_input_classified_twice_is_identical[logo_whitebg.png]`
went red on main (run 40137455117) and on a PR (40129814835), both shard 1:
`gradient_smoothness` 0.0005601321504400403 against 0.0005601322072834591 in one
process. The first run had the LOW value on the first call, the second had it on
the SECOND, so it is not a cold-start effect.

**The brief's premise was false, and measuring it is what found the cause.** It
said the float32 `cv2.boxFilter(normalize=False)` and float32 mean drift, and
offered CV_64F or a fixed thread count. Measured (cwd `digitizer/`, conftest's
`OPENCV_IPP=avx2`): 200 loops at 8 threads and 25 each at 1 thread, IPP avx2 /
sse42 / disabled / avx512: `boxFilter` outputs bit-identical every time, at every
input AND output 4-byte alignment; the float32 mean too. Neither moves.

**What moves: `cv2.magnitude`.** Per-op hashes under the three IPP paths differ
only at `mag` (and what is built from it). Then, by handing `cv2.magnitude` an
output buffer at a chosen offset past a 64-byte boundary: IPP's AVX2 kernel gives
one answer at byte offsets 0/4/32/36, another at 12-28 and 44-60, a third at 8/40
(8 distinct over a 32-byte span, repeating). numpy's allocator hands back
16-byte-aligned blocks, so which a call gets is the heap's state, which is what a
loaded xdist worker changes. The two CI values reproduce BIT FOR BIT on the
laptop: ...2072834591 at an aligned buffer, ...1504400403 at a 16-byte one (and
under IPP sse42 / disabled). Windows' allocator happens to align these blocks, so
the loop test cannot go red here by itself; the offset test is the proof.

**Why only this fixture.** Local variance is `mean_sq - mean*mean` in float32; on
a flat logo it is ~5e-7, so one rounding in a few pixels shows in the mean. The
other seven determinism fixtures read identically at every alignment.

**The fix is precision only.** `_magnitude(gx, gy)`: both float32 squares exact in
float64, one rounding for the sum, correctly rounded sqrt, one rounding to
float32, in row blocks of 256. No threshold, constant or rule touched (ROADMAP
gate 2).

**It is NOT value-preserving, and my first draft said it was.** On the 3 fixtures
I tried first it matched the aligned IPP reading exactly, so I wrote "no fixture
reads differently"; the 44-image sweep (every image under `testdata/`, old at an
aligned buffer and at a 16-byte one, new once) showed 9 images move
`gradient_smoothness` by 1e-7 to 3.5e-7 relative (IPP's kernel is not correctly
rounded either). Class: no change on any of the 44. Confidence: only
`bg_uncertain.png` moves, +7.1e-8. Two images were alignment-sensitive before:
`logo_whitebg.png` and `photo/screenshot_phone_ui_golke.jpg` (8.7e-8). Three
fixtures do not licence "no fixture"; sweep them all before writing the sentence.

**What to do next time.**
- A float "nondeterminism" whose two values are far from 1 ulp apart per pixel is
  not summation order — look at WHICH op moves with a per-op hash under
  `OPENCV_IPP=avx2|sse42|disabled` before touching the filter the brief names.
- Control the output buffer (`cv2.op(a, b, dst)` with `dst` at an offset) before
  blaming threads. Reading `useIPP()` is not enough: the same IPP path answers
  differently at two alignments.
- Other IPP-guarded float ops in `digitizer_core` could do the same where their
  output feeds a pin (`cv2.magnitude` was the only one in `digitizer/`; Sobel and
  `boxFilter` were alignment-stable on all fixtures tried). Not audited beyond
  stage 0.
