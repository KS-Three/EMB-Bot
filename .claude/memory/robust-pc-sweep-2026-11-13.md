---
name: robust-pc-sweep-2026-11-13
description: "2026-11-13 — a 77-image sweep on both photo lanes (rembg venv present / absent) on a 28-core Windows desktop: the cutout runs on 14 and changes all 14; CI measures the other lane; THREAD_MATCH_POOR false blocks, tone pass OFF, faulthandler crash, SAM2 GPU negative"
metadata:
  type: project
---

# Robust-PC sweep: two photo lanes (2026-11-13)

The heavy runs went on a 28-core Windows desktop with both isolated venvs
built (`digitizer/rembg_isolated/venv` and the SAM2 one). That is the first
machine in a while to run the photo lane the way a deployed service does, and
most of what follows came out of the difference.

**Two lanes.** With the rembg venv a photo-class job attempts the cutout and,
if accepted, runs photo prep. CI has no venv: the cutout fails and prep is
skipped with it; `photo_prep=False` reproduces that lane exactly. A full
suite there gave 8 failures; 5 were MFab tests whose pins came from the CI
lane. PR #1439 pinned them to `photo_prep=False` and added
`tests/test_mfab_cutout_lane.py` (skips without the venv) for the other lane.

**The sweep.** 77 images (39 Commons corpus + 38 in-repo), the Studio's
request (80 mm, left_chest, 6 colours), both lanes, commit 2489ac48:

- 63 byte-identical on both lanes: 47 never attempt the cutout, 16 attempt it
  and are refused (`PHOTO_CUTOUT_REFUSED`).
- All 14 where the cutout ran differ, 0.4% to 64% fewer stitches on the
  cutout lane. No class or route change between lanes.
- So DOCTRINE's 2026-08-24 "knowingly inert for real uploads" no longer held;
  corrected in place.

**What the 14 showed.**

- `THREAD_MATCH_POOR` blocked 9 of 14 (B → F): preflight graded threads
  against the raw re-read while stage 2 matched spools to the prepped raster.
  PR #1460 grades on the pipeline's raster and keeps the
  raw gap as metrics `thread_raw_worst_delta_e` / `thread_raw_median_delta_e`:
  0 thread-match findings on all 14, stitches unchanged. MASTER_SCOPE item 28
  had been closed on the CI lane.
- Photo prep's tone pass (foreground contrast stretch + CLAHE) moved threads
  away from the photo: area-weighted region dE00 10.54 on against 5.16 off,
  lightness order reversed on 4 of 14 against 0, black ink and black fur sewn
  as greys. Kent: "Switch it off by default". `cfg.photo_prep_tone`, OFF, PR #1461
  (`docs/photo-prep-tone-off-2026-11-13.md`); frozen 2026-10-27 engine keeps
  it on.
- `photo_enclosed_rim` (still OFF): PR #1451 reads a rim piece by its median
  Lab; cutout-lane MFab 60 mm 2 fields / 10 riders → 1 / 15. 113.5 mm still
  loses one rider to text clustering (strict xfail). On the LIVE engine
  (11-13, both lanes) ON reads the small line at 30 and 60 to 113.5 mm but
  sews one black patch at 35 to 40 mm (order flips to White, Black) and white
  M-FAB faces at 45 and 50 mm; 3 of 77 other images get worse. Kent 11-14:
  "Keep off, fix the collapse". Tables: the rim doc's 11-14 addendum.

**Second round (merged 11-14).** Reviews of the browser engine and the Studio
gave PRs #1463 to #1475: browser satin, undo, lettering, canvas rotate and
resize, Reshape. Two rulings worth knowing before touching those areas: an
auto-routed browser satin with a stitch over 12.1 mm goes to fill ("Narrow it
to the stitch limit", #1471), and border-connected background removal is
built OFF (`knockoutBackground` option `connected`, #1470; DOCTRINE has why).
Stage 6 has no byte-identical 2x for `stained_glass` (DOCTRINE; #1472 took
the 4% that was exact).

**A crash that was the tool.** 6 sweep row-runs died 0xC0000005 at exactly
120 s with a shapely frame on top of a truncated dump. It was the corpus
worker's `faulthandler.dump_traceback_later(repeat=True)`, which walks the
main thread's frames without the GIL; about 1 dump in 6 was fatal on Windows
CPython 3.12. PR #1459 samples from a Python thread. Not GEOS; the shipped
service never used the call.

**SAM2 on the GPU (RTX 4070), shelved.** Inference 10-12x faster (about 3.2 s
→ 0.3 s), masks within 0.99999 IoU of CPU, but a fresh worker per job pays
about 3 s more to import CUDA torch, so per-job wall is 6.4-6.7 s CPU against
7.0-7.6 s GPU. Only a long-lived worker would pay. Opt-in on unmerged
`feat/sam2-device-opt-in` (102854dc); Kent shelved it.

**Practical notes for the next session on that machine.**

- Worktrees have no isolated venvs. Point them at the main checkout's with a
  directory junction, and remove the junction with a NON-recursive directory
  delete, or the delete follows it into the real venv.
- Bring a pushed branch up to date by merging `main`, never by rebasing: the
  force-push hook blocks the push a rebase needs.

Related: [[photo-cutout-no-subject-2026-10-28]], [[thread-match-leftovers-2026-11-10]],
[[worktree-venv-and-baselines]].
