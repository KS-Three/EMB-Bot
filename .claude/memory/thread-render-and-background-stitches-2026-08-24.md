# The renderer that made the real defect visible — 2026-08-24/25

Read this before proposing photo-route work, and before trusting any prior
sheet, contact sheet, or "Kent judged it" claim dated before 2026-08-24.

## The instrument was the bug

Kent, looking at a contact sheet: *"it's hard to picture how these shape
recognition features would be turned into a digitized or embroidered
product."* He was right, and it was not a failure of imagination.

Every sheet up to that point embedded pystitch's `write_svg` output —
hairline polylines tracing where the needle went. That answers *did the
geometry come out*. It cannot answer *will this read as a face*, because
thread has width, overlaps, and covers cloth. **Every tonal ruling this
project asked Kent for had been made from a picture that could not show the
thing being judged.**

`digitizer_core/stitchviz.py` (PR #234) draws stitches as round-capped
strokes at real thread width, in sew order so later stitches cover earlier
ones. Jumps and trims lay nothing — drawing through travel paints it as
coverage, which is exactly what makes a sparse design look solid.

**The first thread render found the defect in one look.** The subject was
about a quarter of the frame; the rest was deck boards, rendered in thread.

## The defect: 72.2% of the design sewed removed background

`photo_prep_background_removal` cuts the subject out with rembg, and stage 2
respects it (background pixels get label -1 and never become regions). The
FDoG **detail layer** did not, because it does not read regions at all — it
runs over the whole raster.

Measured on `baby_deck_laugh` (subject = 10.0% of the frame), every stitch
point mapped through `SourcePixels.to_px` against the pipeline's own mask:

| | in subject | in removed background |
|---|---|---|
| blocks 0-15 (regions) | 4,278 | 301 (6.6%) |
| **block 16 (FDoG detail)** | 1,022 | **10,813 (91.4%)** |

The regions were always clean. One block was 97.3% of the problem.
`SourcePixels.subject_mask` fixed it (PR #235): 10,813 -> 537, and the 537
are the deliberate silhouette slack — verified by distance transform, worst
1.79 working px outside the subject, **zero beyond 3**.

## Why nobody had seen it

**No acceptance arm had ever set `photo_prep_background_removal`.** Every
sheet judged to date sewed the whole frame, so "the background is being
embroidered" was never on screen as a thing to notice — it *was* the
picture. The `subject_cutout` arm now exists, gated on the isolated venv.

Generalise this: *a defect that is present in every column of a comparison
harness is invisible to that harness.* The arms differ from each other, so
nothing differs.

## Kent's rulings, 2026-08-24

1. **The cutout pair ships ON** (`photo_prep` + `photo_prep_background_
   removal`), never singly — prep alone is the worst arm on the sheet, worse
   than doing nothing on all four portraits.
2. **The fallback was failing in the expensive direction** and now skips prep
   entirely, landing byte-identically on `classical`. A fallback is supposed
   to be the safe direction to fail in; this one degraded onto the most
   expensive result the harness measures, on the machines least able to
   absorb it.
3. **rembg is a DEPLOY REQUIREMENT.** CI does not build it, so CI exercises
   the fallback — a green CI run says nothing about the cutout path.
4. **Ships knowingly inert for real uploads.** All four acceptance photos
   classify `gradient` at confidence **1.00**, and `gradient` is not in
   `PHOTO_CLASSES`, so the gate never opens for them. Live only for a forced
   photo class. Revisit at ROADMAP gate 2 — NOT by widening the gate, since
   `gradient` is also the class for genuine gradient logos where rembg would
   invent a subject that is not there.

## Numbers, in thread, subject_cutout vs its one-flag control

| photo | shapes | cones | stitches | trims |
|---|---|---|---|---|
| baby_deck_laugh | 175 -> 29 | 12 -> 7 | 33,371 -> 5,190 | 690 -> 96 |
| boat_dog_toddler | 100 -> 41 | 15 -> 12 | 16,200 -> 4,581 | 361 -> 120 |
| sparkler_dusk | 107 -> 36 | 12 -> 12 | 19,902 -> 6,194 | 483 -> 117 |
| face_closeup_blur | 52 -> 49 | 12 -> 12 | 13,885 -> 12,740 | 218 -> 172 |

The last row is the honest shape of the feature, not a defect in it: a tight
face crop has almost no background to remove, so the cutout buys almost
nothing while prep still costs.

## THE NEXT PROBLEM, in Kent's words (2026-08-25)

Shape and feature recognition is *"getting VEERY good"*. **His main concern
is now how the stitching LOOKS WITHIN each shape.** That is not region
identification — it is fill quality, and the renderer already measured it:

| route | covers its own footprint |
|---|---|
| streamline thread-paint (every photo arm) | **0.55 - 0.59** |
| gradient blend (`default_stock`) | **0.99** |

Nearly half the cloth inside a photo-route shape is bare. The streamline
tier's *fabric-as-value* intent is documented and deliberate — but it is a
DIFFERENT PRODUCT from a filled one, and no sheet ever said so.

**The mechanism is already mapped** (two read-only agents, 2026-08-25):
coverage is `THREAD_MM / d_sep`, and `STREAMLINE_D_SEP_DARK_MM = 0.8` is
exactly TWO thread widths — so **0.50 is a hard analytic ceiling at pure
black, by construction**. Blend reaches 0.99 because `FILL_ROW_MM = 0.40` is
exactly ONE thread width. Full brief, gate-1 triage of every constant, three
findings that were not previously written down, and four suggested agent
lanes: `docs/superpowers/plans/2026-08-25-fill-coverage-team-brief.md`.
**Read it before spawning a team** — the sweep is done, do not pay for it
twice.

## Traps re-hit or newly found

- **`.gitignore` entries with a trailing slash do not match symlinks.**
  `rembg_isolated/venv/` ignores a real directory; a symlink at that path
  shows up untracked, one `git add -A` from being committed to a PUBLIC repo.
- **A worktree has no `.venv`.** Run its suite with
  `PYTHONPATH=<wt>/digitizer /home/user/EMB-Bot/digitizer/.venv/bin/python -m pytest`
  — PYTHONPATH beats the editable-install finder (verified, not assumed).
- **Aborting a merge under a running pytest invalidates the run**; the files
  change mid-collection. Kill the suite first.
- **Coverage measured against a sentinel colour is wrong both ways** — tight
  scores anti-aliased fringe as bare (read 99.9% on a design visibly
  two-thirds cloth), loose counts it as solid. Render twice, on black and on
  white, and read the difference.
- **A coverage number that moves with display scale is not evidence.** The
  same design read 0.75 at 8 px/mm and 0.67 at 14 before it was pinned.

## A segfault that is NOT in the shipped code — do not chase it again

Running the digitizer suite in the PRIMARY checkout after a long session of
service/sheet work produced **21 failures**, including hard `Segmentation
fault` (exit 139) in `stage2_photo_segment._seeds_superpixels` (OpenCV
contrib SEEDS). It looks alarming and it is not a regression. Bounded on
2026-08-25:

- **CI on `main` is green** — run 919, `6b1ccdf`, clean checkout, success.
  That is the authoritative answer.
- The same test passes in a **clean worktree** with the **same venv**.
- In the primary checkout, with byte-identical source (md5-verified) in the
  same directory: the identical `run_stages` call **succeeds via direct
  Python and segfaults under pytest**.
- Ruled out: memory (14 GB free), xdist contention (reproduces serially),
  stale `__pycache__`/`.pytest_cache` (cleared, still crashes),
  `OPENCV_NUM_THREADS=1`, `-p no:faulthandler`, and egg-info entry points
  (the egg-info has none).

So: environmental, pytest-only, primary-checkout-only, cause unidentified.
The nine `test_service.py` failures in the same run are the documented
loaded-box class, and two "worker crashed" entries are this segfault
cascading through xdist.

**If you see this: run the suite from a fresh worktree, and believe CI.**
Do not "fix" tests against it.

*(PRs #234, #235, #236, all merged to main 2026-08-25; four family photos,
never committed — they live in the session upload dir and are staged
gitignored at `digitizer/testdata/photo/acceptance/`)*
