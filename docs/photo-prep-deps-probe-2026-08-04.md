# Photo prep dependency stack — install/download probe, 2026-08-04

Build step 3 of `docs/photo-digitizing-plan-2026-07-31.md` (§2 rows 1–4)
needs four things: rembg background removal, YuNet face detection, CLAHE,
and a texture-kill filter. This memo records what was actually probed in
this sandbox (Claude Code Remote container, outbound HTTPS through the
agent proxy), what worked, what failed with what error, and what Kent
would need to run locally to finish the stack. Everything was probed in a
**throwaway venv** (`/usr/bin/python3.12 -m venv`, matching the shared
venv's Python 3.12.3); the shared `digitizer/.venv` was not modified in
any way.

The CLAHE + zero-dep texture-kill slice needed none of the new
dependencies and shipped in this same branch (`stage1_photo_prep.py`,
plus the `photo_prep*` config block and `tests/test_photo_prep.py`).

## Summary table

| Component | Wheel install | Model download | Runs? | Blocker |
|---|---|---|---|---|
| CLAHE (row 3) | n/a — already in cv2 | n/a | ✅ shipped this branch | none |
| bilateral / meanshift texture kill (row 4 fallback) | n/a — already in cv2 | n/a | ✅ shipped this branch | none |
| rollingGuidanceFilter (row 4 real tier) | ✅ `opencv-contrib-python-headless==5.0.0.93` | n/a | ✅ in probe venv | ~~golden gate (see below) — swap not applied~~ **swap APPLIED later 2026-08-04, see addendum** |
| YuNet (row 2) | n/a — `cv2.FaceDetectorYN` already in shipped cv2 | ✅ via LFS media endpoint | ✅ loads + detects in shipped venv | none technical — just cache policy + wiring |
| rembg (row 1) | ✅ `rembg==2.0.77`, `onnxruntime==1.28.0` | ✅ isnet-general-use (178 MB) | ❌ | **numba requires numpy<2.5; repo venv pins 2.5.1 — `import rembg` fails** |

## 1. opencv-contrib swap (texture-kill real tier)

* The repo pins `opencv-python-headless==5.0.0.93` (exact-pinned because
  cv2 kmeans/contours feed the goldens). The correct swap target is the
  **headless contrib twin at the same pin**:
  `opencv-contrib-python-headless==5.0.0.93` — not the plan's
  `opencv-contrib-python` name, which pulls GUI deps this service doesn't
  want.
* Install: **works** through the proxy (69.5 MB manylinux_2_28 wheel from
  PyPI). Imports as cv2 5.0.0; `cv2.ximgproc.rollingGuidanceFilter` and
  `cv2.ximgproc.l0Smooth` both present.
* **Golden gate** (the plan's own step-3 acceptance): the full digitizer
  suite was run against a probe venv that is version-identical to the
  shared venv (numpy 2.5.1, scipy 1.18.0, shapely 2.1.2, scikit-image
  0.26.0, pyembroidery 1.5.1, pillow 12.3.0) except cv2 = the contrib
  wheel. Result: **618 tests — 615 passed, 3 failed, and the 3 failures
  are exactly the 3 known container-environment goldens**
  (`test_flat_lane_byte_identical[logo_alpha.png]`,
  `test_pushcomp[logo_whitebg.png-towel]`,
  `test_stage2_photo_segment[logo_alpha.png]` — COOKBOOK.md's standing
  note), matching the same-day baseline run on the real venv
  byte-for-byte in pass/fail identity. **The swap is verified golden-safe
  in this environment.** Per this lane's instructions the shared venv was
  still NOT modified — applying the swap is the coordinator's call.
  When applied, it is a one-line `pyproject.toml` change
  (`opencv-python-headless==5.0.0.93` →
  `opencv-contrib-python-headless==5.0.0.93`) plus an uninstall/install in
  the venv (the two wheels both claim the `cv2` module and must never be
  co-installed). **→ Applied later the same day — see the addendum at the
  bottom of this doc.**
* Until the swap lands, `photo_prep_texture_kill="rolling_guidance"`
  falls back to `"bilateral"` at runtime and says so in the
  PHOTO_PREP_APPLIED warning — tested in both directions
  (`tests/test_photo_prep.py`, one test per branch; the contrib-side test
  auto-skips in the shipped venv and ran green in the probe venv).

## 2. rembg (background removal)

* `pip install rembg onnxruntime`: **works** through the proxy —
  `rembg 2.0.77`, `onnxruntime 1.28.0` (cp312 wheels).
* Model download: **works**. The 178 MB `isnet-general-use.onnx`
  downloaded from rembg's GitHub release URL
  (`github.com/danielgatis/rembg/releases/download/...`) through the
  proxy with a plain HTTPS GET — release-asset URLs are NOT blocked (only
  in-repo raw file access is, see YuNet below).
* **The actual blocker is a version conflict, not the network**:
  `rembg/bg.py` unconditionally does
  `from pymatting.alpha.estimate_alpha_cf import estimate_alpha_cf`,
  pymatting imports numba, and pip resolved `numba 0.66.0`, which refuses
  numpy ≥2.5 at import time:

  ```
  ImportError: Numba needs NumPy 2.4 or less. Got NumPy 2.5.
  ```

  The shared venv pins `numpy 2.5.1`. pip itself flagged it during
  install: `numba 0.66.0 requires numpy<2.5, but you have numpy 2.5.1`.
  So in a venv matching this repo, `import rembg` fails outright, and
  the isnet session could not be exercised end-to-end here.
* Paths out (pick one when wiring row 1):
  1. Wait for / pin a numba release supporting numpy 2.5 (numba tracks
     numpy closely; check `numba.readthedocs.io` support matrix).
  2. Run rembg in an isolated venv/subprocess harness (its own numpy),
     talking to the digitizer over the existing service seam — heavier
     but decouples the pin forever, and matches the plan's "rembg …
     harness" framing.
  3. Downgrade the shared venv to numpy 2.4.x — **only** behind the same
     full-suite golden gate as the contrib swap, and NOT recommended
     sight-unseen: nothing else in the repo needs it and the goldens'
     exact pins outrank a cutout dependency.
* The alpha-matting machinery that drags numba in is unused by our plan
  (thread can't render partial alpha — §2 row 1 says binary mask +
  morphology), which makes option 2's harness (or even a surgical
  lazy-import patch upstream) the honest fit.
* Wiring seam in code: `stage1_photo_prep.remove_background_seam`
  (documented no-op; this probe's results are condensed in its
  docstring).

## 3. YuNet (face priors)

* **No wheel work needed**: `cv2.FaceDetectorYN` exists in the shipped
  venv's `opencv-python-headless` 5.0.0 — the plan's "[M present]" holds.
* Model file `face_detection_yunet_2023mar.onnx` (232,589 bytes) is
  **Git-LFS-stored** in `opencv/opencv_zoo`, and that changes which URLs
  work:
  * `github.com/opencv/opencv_zoo/raw/main/...` → **403** from the agent
    proxy ("GitHub access to this repository is not enabled for this
    session") — in-repo file access needs the repo attached, and
    `add_repo` refuses cross-owner adds in a session keyed to kent746.
  * `raw.githubusercontent.com/opencv/opencv_zoo/main/...` → 200 but
    returns the **131-byte LFS pointer**, not the model.
  * `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx`
    → **200, real model**, sha256
    `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
    (matches the LFS pointer's oid — integrity verified).
* Functional check in the **shipped** venv:
  `cv2.FaceDetectorYN.create(model_path, "", (320,320), ...)` constructs
  and `.detect()` runs end-to-end (0 faces on `photo_subject_stub.png`,
  which contains no face — the repo still has no committed face fixture;
  plan step 3's F3/F4 fixtures remain to be sourced).
* Remaining work is policy, not feasibility: where the .onnx lives
  (suggest `digitizer_core/model_data/` or an env-var cache dir + sha256
  check), who downloads it, and the elliptical importance masks. Wiring
  seam: `stage1_photo_prep.detect_faces_seam`.

## 4. CLAHE + zero-dep texture kill — shipped, this branch

No dependency work (both "[M present]"). See `stage1_photo_prep.py`:
CLAHE on L of Lab (clip 2.5, 8×8, config-exposed) + foreground-measured
percentile contrast stretch; texture kill at the physical scale
`min_detail_mm × px_per_mm`, techniques `bilateral` (default, 3 iterated
passes @ sigmaColor 40 — sweep-tuned, figures in the module) /
`meanshift` (sr 25) / `rolling_guidance` (contrib seam w/ fallback) /
`none`. Double-gated: `cfg.photo_prep` (default False) AND a
photo_subject/photo_scene classification. Flat/gradient byte-identity
re-pinned with the flag ON in `tests/test_photo_prep.py`.

Measured cost (per plan step 3's "per-stage CPU time logged" — the
PHOTO_PREP_APPLIED warning carries `tone_ms`/`texture_ms` on every run):
on `region_blobs.png` at 80 mm (post-upscale raster, kill scale 11 px),
tone 170 ms + bilateral 2.27 s in this container. Meanshift on a 200×300
synthetic: 69 ms. The service accepts the new fields with zero changes —
`_CONFIG_FIELDS` derives from the dataclass.

## Addendum, later 2026-08-04 — contrib swap APPLIED and re-verified

The §1 swap is no longer pending: `digitizer/requirements.txt` and
`digitizer/pyproject.toml` now pin `opencv-contrib-python-headless==5.0.0.93`
(the plain `opencv-python-headless` pin is gone from both; CI installs from
requirements.txt, so CI gets the contrib wheel too). No code change was
needed — `stage1_photo_prep._texture_kill` feature-detects `cv2.ximgproc`.

Re-verified fresh, same day, in a NEW throwaway venv (python3.12.3,
`pip install -r requirements.txt` — not the §1 probe venv):

* `import cv2` → 5.0.0, `hasattr(cv2, 'ximgproc')` → True,
  `rollingGuidanceFilter` present.
* Full suite from this branch's worktree: **632 tests — 628 passed,
  3 failed, 1 skipped** (10:57). The 3 failures are exactly the 3 known
  container-environment goldens (`test_flat_lane_byte_identical
  [logo_alpha.png]`, `test_pushcomp[logo_whitebg.png-towel]`,
  `test_stage2_photo_segment[logo_alpha.png]`); the 1 skip is
  `test_photo_prep.py`'s fallback-branch test, which by design cannot fire
  with contrib installed. Its contrib-branch twin
  (`test_rolling_guidance_with_contrib_takes_the_real_path`) now PASSES in
  the requirements.txt environment — i.e. it runs in CI from here on.
* Live-warning check: `photo_prep` with
  `photo_prep_texture_kill="rolling_guidance"` emits PHOTO_PREP_APPLIED
  with `technique='rolling_guidance', fallback=False` (no "fell back"
  text) — the seam takes the real path.

Still true from §1: the two wheels both claim `cv2` — an EXISTING venv
(including the shared `digitizer/.venv`, which was again not touched by
this lane) must `pip uninstall opencv-python-headless` before installing
the contrib pin; a fresh `pip install -r requirements.txt` needs nothing
special. Kent's local item 1 below stands, now with the repo pins already
updated for him.

## What Kent needs to run locally (open egress, his machine)

1. **Contrib swap** (verified golden-safe here, apply when ready):
   `pip uninstall opencv-python-headless && pip install opencv-contrib-python-headless==5.0.0.93`
   in `digitizer/.venv`, update the `pyproject.toml` pin, re-run the full
   suite, expect only his machine's known failures (goldens were pinned
   on a different machine than this container — his counts may differ).
2. **YuNet model**: download the LFS media URL above (or any clone of
   opencv_zoo), verify the sha256, drop it where the cache policy
   decides.
3. **rembg**: decide among the three paths in §2 — nothing to download
   was blocked, but `rembg` cannot import next to numpy 2.5.1 as of
   numba 0.66.0. `pip index versions numba` / the numba release notes
   are the first check; if a numpy-2.5-compatible numba exists, plain
   `pip install rembg onnxruntime` + one smoke run
   (`rembg.remove(..., session=new_session("isnet-general-use"))`)
   finishes this row (first use downloads to `~/.u2net/`).
