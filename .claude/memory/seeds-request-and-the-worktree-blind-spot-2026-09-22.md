---
name: seeds-request-and-the-worktree-blind-spot-2026-09-22
description: The intermittent native SEEDS crash was an unservable superpixel request, and a worktree could not reproduce it because rembg_isolated/venv is gitignored — so a worktree tests a DIFFERENT pipeline than the main checkout
metadata:
  type: project
---

Two findings, 2026-09-22. The second is the one that will cost a session again.

**A worktree runs a different pipeline than the main checkout.**
`rembg_isolated/venv` (and `sam2_isolated/venv`) are gitignored, so a
worktree or a fresh clone has NO subject cutout: `remove_background_seam`
degrades to its no-op, `pipeline.build_generation` skips the entire
photo-prep block, and every photo-lane test silently exercises the
FALLBACK rather than the path Kent's main checkout runs. Nothing warns.
A full suite run is green in the worktree and red on the main checkout
from the same tree.

To reproduce the main-checkout condition from a worktree, point the
module constant at the main checkout's interpreter — it is read at call
time, so a pytest plugin (`-p …`) loaded off PYTHONPATH is enough:

    import digitizer_core.stage1_photo_prep as pp
    pp.REMBG_VENV_PYTHON = Path(r"…\EMB-Bot\digitizer\rembg_isolated\venv\Scripts\python.exe")

That flipped `test_underresolved_photo_input_warns` and
`test_flag_off_emits_no_prep_and_flag_on_emits_one` from green to the
reported crash on the first try, after 60/60 clean standalone runs of the
same SEEDS call had said the input was fine.

**The crash itself: an unservable request, not a bad image.**
`_seeds_superpixels` scales `num_superpixels` by `1 / bbox_fg_frac`,
floored at `SEEDS_MIN_FG_FRAC` 0.05. With the cutout available
`region_blobs.png` leaves a 222x214 bbox holding 7.85% foreground →
**15,292 superpixels over 47,508 px**. `SuperpixelSEEDSImpl::initialize`
halves its block hierarchy until a block is 1 px wide; at that density
`seeds_nr_levels` collapses to 1, `initImage` sets `seeds_current_level =
-1`, the block-update loop never runs and `iterate()` goes out of bounds.
Upstream opencv_contrib issue #2023, open since 2019.

Three outcomes, all measured: **access violation** (280x280/20,000,
40x40/1,200) which the Python bindings also surface as `cv2.error:
Unknown C++ exception from OpenCV code`; **an all-zero label array** —
no exception, the whole photo becomes one region (200x200/20,000,
64x64/1,200); and a **hang** on any 1-px-wide crop. The silent one is the
one a green suite hides.

Fixed by clamping to one superpixel per 4 crop pixels and refusing SEEDS
below 16 px a side — see `SEEDS_MIN_PX_PER_SUPERPIXEL` in
`stage2_photo_segment.py` for the sweeps. **When sweeping a guard like
this, vary the REQUEST per shape, not one request per shape**: the
one-per-shape pass reported the density cap alone as clean and missed the
elongated crops, where `num_superpixels_h = sqrt(N*H/W)` reaches 0.

**And it hid a second defect.** `test_flag_off_emits_no_prep_and_flag_on
_emits_one`'s "off" arm stopped setting `photo_prep` when the default
flipped ON in `fe007e7c` (2026-08-24); it had been passing on the
unavailable-cutout fallback ever since. With the crash fixed it failed
honestly on `assert not True`. A test that only passes because an
optional dependency is missing is not testing its gate.

Related: [[worktree-venv-and-baselines]], [[digitizer-local-env]],
[[windows-goldens-fail-locally]].
