# SAM2 segmentation — live acceptance, 2026-08-10

Task 6 of `docs/superpowers/plans/2026-08-10-sam2-segmentation.md`: build the
real isolated venv, run real SAM2 on real hardware, measure the corpus
before/after, and replace the plan's own "principled starting point, not
measured" placeholders with real numbers. Everything through Task 5 already
ships and passes without this — `photo_segment_sam2` defaults `False` and the
classical SLIC+RAG segmenter is untouched. This note is the go/no-go on
whether to change that default, and the source of the two numbers now in
`digitizer_core/config.py`.

Machine: Windows 11, CPU-only (no GPU), Python 3.14.6, this worktree's
`sam2-segmentation` branch, `dae995f` at the start of this task.

## 0. The verdict, up front

**SAM2 works — the venv builds, the worker runs, the seam wires up exactly
as designed, and its documented fallback fires cleanly on a real timeout in
this same session. But on the only corpus material available to test it
against, it is a tie with the classical segmenter, not a win, at a real cost
of ~40s of CPU per job. Recommendation: `photo_segment_sam2` stays `False`.**

That is not a verdict on SAM2's merits so much as on this corpus's coverage.
The three committed fixtures that classify `photo_subject`/`photo_scene` —
the only classes this lane ever runs on — are `photo_subject_stub.png`
(synthetic RGB static, built to exercise the stage-0 classifier, not to
depict a subject), `photo_scene_stub.png` (a smooth, blurred, low-contrast
texture with no discrete objects), and `fur_ramp.png` (eight flat-color
circles on a flat background — a trivial case classical SLIC+RAG already
solves perfectly). Kent's two real production photos, `drone_render.png` and
`enthusiast_logo.png`, classify `gradient` and `flat` respectively and never
reach this lane at all. So the question this module's own docstring poses —
does SAM2's learned visual saliency beat SLIC+RAG's color/space clustering on
a subject whose interior varies smoothly, a face, a jacket, a dog — was
never actually exercised. Nothing here says SAM2 would lose that test; the
corpus just doesn't contain it yet.

## 1. Disk

Checked immediately before building, per the plan's own instruction (time
had passed since the plan's 13.5 GB figure and 15.3 GB measured moments
before this task started): **15.3 GB free**. After the full venv, the
checkpoint, and every corpus run in this note: **13.9 GB free** — 1.4 GB
consumed, comfortably inside the plan's 2-3 GB budget:

* `sam2_isolated/venv/`: **0.80 GB** (torch 2.13.0+cpu + torchvision
  0.28.0+cpu + SAM-2 + opencv-python-headless + their transitive deps) —
  under the plan's own 2-3 GB estimate, not over it.
* Checkpoint (`~/.cache/sam2/sam2.1_hiera_tiny.pt`): **156,008,466 bytes**
  (~156 MB, matching the README's "~150 MB" figure).
* The remainder is pip's own wheel cache, outside the venv and outside this
  repo.

## 2. Re-verifying the README against Meta's current repo

Per the plan's Global Constraints, re-fetched Meta's own `README.md` and
`INSTALL.md` from `facebookresearch/sam2` on GitHub before building anything,
rather than trusting `sam2_isolated/README.md` at face value.

* **Version floors match**: `python>=3.10`, `torch>=2.5.1`,
  `torchvision>=0.20.1` — identical to what our README already states.
* **Checkpoint URL matches**: the tiny checkpoint is still served from
  `https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt`.
* **`SAM2_BUILD_CUDA=0` confirmed**, but in `INSTALL.md`, not `README.md`
  (`README.md`'s own install example is a `git clone` + `pip install -e .`
  without it) — the env var, its purpose, and Meta's own "shouldn't affect
  the results in most cases" wording all matched our README verbatim.
* **One cosmetic gap, not a functional one**: Meta's docs show
  `git clone ... && pip install -e .`; our README uses
  `pip install "git+https://github.com/facebookresearch/sam2.git"` instead.
  Neither of Meta's own files documents the direct-git-URL form, but it is
  standard pip VCS syntax (pip clones internally) and it worked cleanly here
  — `SAM-2 1.0` installed from commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`
  with no errors. No change made; noted so nobody re-checks this later
  thinking it was skipped.

**Conclusion: the README's build steps still match Meta's current repo.**
Nothing needed to change there.

## 3. Building the venv — one real deviation from the README

`sam2_isolated/README.md` says `python3.12 -m venv sam2_isolated/venv`. This
machine has **no Python 3.12 installed** — `py -0p` lists only Python 3.14.6
(`C:\Python314\python.exe`), the same interpreter the shared `digitizer/.venv`
itself was built with. Rather than blindly follow a stale-on-this-machine
instruction, checked whether PyTorch's CPU wheel index actually has a
`cp314` build before assuming this was a blocker:

```
pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5.1" "torchvision>=0.20.1" --dry-run
```

resolved cleanly to `torch-2.13.0+cpu-cp314-cp314-win_amd64.whl` and
`torchvision-0.28.0+cpu-cp314-cp314-win_amd64.whl` — both real wheels on
PyTorch's own index. Built the venv with the system Python 3.14 instead of
chasing down a 3.12 install, and every later step (torch import, SAM2 import,
the worker, the seam, the corpus) worked without incident. `torch.__version__`
== `2.13.0+cpu` (>= the 2.5.1 floor), `torch.cuda.is_available()` == `False`
(CPU wheel index took, as intended). Recorded here as the honest deviation it
is: `sam2_isolated/README.md`'s `python3.12` is a snapshot of whatever the
plan's own authoring machine had, not a hard requirement, and machines
without exactly that interpreter should check the wheel index the same way
before assuming they're blocked.

Build order followed exactly (torch/torchvision from the CPU index, then
`SAM2_BUILD_CUDA=0 pip install "git+https://github.com/facebookresearch/sam2.git"`,
then `pip install -r sam2_isolated/requirements.txt` for
`opencv-python-headless`) — no other deviation.

## 4. Worker sanity check and timing

Ran `sam2_worker.py` by hand against `testdata/photo/drone_render.png`
(1536x1024), `tiny` checkpoint, `points_per_side=16`,
`min_mask_region_area=36`, exactly as the plan's own Step 3 commands specify
— twice, timed separately:

| Run | Elapsed | What it paid for |
| --- | --- | --- |
| 1 (cold) | **155.98 s** | checkpoint download (~156 MB from `dl.fbaipublicfiles.com`), torch's own cold import, model build, inference |
| 2 (warm) | **39.96 s** | inference only — the number that matters for the timeout |

Both exits were 0. Both runs printed the same benign warning:
`cannot import name '_C' from 'sam2'` — expected and documented: `_C` is the
CUDA post-processing extension `SAM2_BUILD_CUDA=0` deliberately skips
building, and Meta's own `INSTALL.md` says this "shouldn't affect the
results in most cases." Real, first-hand corroboration that the env var
does what the README already claimed.

Inspected the warm run's output from the shared venv:

```
shape: (1024, 1536)   dtype: int32
raw_mask_count: 7
distinct labels: 8   (7 masks + the -1 "uncovered" id)
```

Shape matches the source image, dtype is `int32` as documented. 7 raw masks
on this fixture, run through the raw worker with no downscale, is on the low
side of "tens to low hundreds" — see §6 below for why that number, on THIS
specific fixture, is not evidence of a tuning problem (`drone_render.png` is
explicitly one of the three fixtures this task was told not to use as a
pass/fail bar, and separately: it classifies `gradient`, not
`photo_subject`/`photo_scene`, so it never reaches this lane in production
regardless of what its raw mask count is).

## 5. Setting the timeout

`photo_segment_sam2_timeout_s` moves from the plan's reasoned-but-unmeasured
**180s** to **90s** — roughly 2x the observed warm run (2 x 39.96 = 79.9s),
rounded up to a round number. Full reasoning, including the real trade-off
this creates (90s is now shorter than the measured 156s cold/first-use path,
so a fresh deployment's very first real job will time out and fall back
rather than wait out the download — mitigated by pre-warming the checkpoint
cache, which `sam2_isolated/README.md` already documents as a deploy step),
is recorded directly in `config.py`'s own comment rather than duplicated
here — that is where the next person tuning this will be looking.

The end-to-end seam re-run (`stage2_sam2_segment.sam2_segment_seam` against
`drone_render.png`, real worker, `photo_segment_sam2=True`) came back exactly
as the plan's Step 4 expected: `available: None`, `reason: None`, both
`PHOTO_SEGMENT_REGION_COUNT` and `PHOTO_SAM2_SEGMENTED` present in the
warnings. (`threads: 14` printed higher than `cfg.max_colors` (12) at first
glance — traced this rather than assuming a bug: 14 = 7 main-palette spools,
chart-restricted to the 12-color cap exactly as designed, PLUS 7 more spools
from `drone_render.png`'s separate enclosed-background population, which is
deliberately NOT counted against `max_colors` — see `kept_masks_to_quant`'s
own comment on `main_thread_colors` vs `len(thread_indices)`. Not a defect.)

### `points_per_side`: measured, left unchanged

Swept `points_per_side` 16 -> 32 -> 48 against `photo_scene_stub.png` (the
corpus fixture that came back sparsest at the shipped default) to check
whether 16 is grid-starved:

| `points_per_side` | prompts | raw masks | wall-clock |
| --- | --- | --- | --- |
| 16 (shipped) | 256 | 1 | 40.8 s |
| 32 (SAM2's own library default) | 1024 | 2 | 125.1 s |
| 48 | 2304 | — | **timed out at 180s** (the then-current default), fell back to the classical segmenter cleanly |

Quadrupling the prompt grid bought exactly one more mask for triple the
wall-clock, and doubling it again exceeded the (at-the-time) timeout outright.
This is a content property, not a grid-density problem: `photo_scene_stub.png`
is a smooth, low-contrast, textureless raster with no salient objects for an
instance segmenter to find, and SAM2 is reporting that correctly rather than
under-sampling it. Raising `points_per_side` would spend real CPU time (and,
against the new 90s timeout, real fallback risk) for no corresponding
region-count benefit on this evidence. Left at **16**. The 48-run is also the
first real, first-hand confirmation in this session that the timeout/fallback
path fires correctly under a genuine slow call, not just a synthetic test.

## 6. Corpus measurement — before and after

`tools/corpus_scorecard.py capture` (classical, unmodified `MATRIX`) against
all 14 committed fixtures x 2 garment configs (`left_chest`, `hat_front`) ran
clean — 28/28 scored, no errors. That capture was stashed
(`git stash push digitizer/testdata/corpus_scorecard_baseline.json`) to keep
the committed baseline file untouched by this measurement run, per the
plan's own "measurement tool, not a config change" instruction.

`MATRIX` was then temporarily given `"photo_segment_sam2": True` on both
entries and `tools/corpus_scorecard.py diff` re-run against the same 28
digitize+preflight calls (SAM2 only actually fires on the 3 fixtures that
classify `photo_subject`/`photo_scene` — the flag is a harmless no-op on the
other 11, gated by `pipeline.py`'s own class check, not this script). Full
printed output:

```
photo/photo_scene_stub.png @ 80mm/left_chest:
    link_uncovered_max_mm: 0.19 -> 0.1
    same_hole_fraction: 0.096 -> 0.118
    stitch_count: 892 -> 997
    thread_worst_delta_e: 5.5 -> 5.8
photo/photo_scene_stub.png @ 80mm/hat_front:
    coverage_area_mm2: 318.0 -> 338.0
    coverage_p95: 2.26 -> 2.4
    link_uncovered_mm: 0.19 -> 0.1
    same_hole_fraction: 0.093 -> 0.114
    stitch_count: 918 -> 1023
    thread_worst_delta_e: 5.5 -> 5.8
```

Exit code 0 — no new `block`-severity findings anywhere in the corpus, the
one regression signal this script is willing to call outright.
`photo_subject_stub.png` and `fur_ramp.png` printed **nothing at all**: every
tracked preflight metric landed within the script's 5%-noise band, no score
change, no grade change, no findings changed either direction, at both
garment configs. `photo_scene_stub.png` shifted some downstream stitch
metrics (more stitches, tighter link coverage, a slightly wider worst-thread
delta-E) without moving its score or grade.

**Caveat on this tool, worth recording**: `corpus_scorecard.py`'s tracked
`metrics` dict does not include region count at all, so this diff — on its
own — cannot see criterion 1 (region count vs. the 20-80 accept band). That
had to be measured separately; see below.

### Region count, boundary agreement, per fixture (the real acceptance criteria)

Measured directly (`digitize()` + `run_preflight()`, `target_width_mm=80`,
`garment_id=left_chest`, `debug_dir` set for the boundary renders) since the
scorecard diff above can't see region count on its own:

| Fixture | Classical regions | SAM2 regions | 20-80 band | Score/grade | Boundary agreement (visual) |
| --- | --- | --- | --- | --- | --- |
| `photo_subject_stub.png` (synthetic RGB noise) | 1 | 2 (1 raw mask) | both outside | 100/A, unchanged | both collapse to flat gray — correct on noise, no real difference |
| `photo_scene_stub.png` (smooth blurred texture) | 21 | 24 (1 raw mask, mostly the "-1 uncovered" catch-all fragmenting) | both inside | 52/D, unchanged | 564 of 650,000 pixels differ (0.09%) — visually indistinguishable; a smooth low-contrast texture has no real edges for either segmenter to disagree about |
| `fur_ramp.png` (8 flat-color circles) | 8 | 8 (14 raw masks, resolved to the same 8 kept) | both outside | 52/D, unchanged | pixel-for-pixel indistinguishable — both lanes fit all 8 circles perfectly |

No fixture crossed the 20-80 band in either direction — the brief's own
win/regression rule (SAM2 landing inside when classical doesn't, or vice
versa) fires on none of the three. `photo_scene_stub.png`'s "24 regions"
looks like more granularity than classical's 21, but tracing it (§ above)
shows most of the extra count is the uncovered-background catch-all splitting
into more disconnected fragments, not SAM2 finding more real objects — SAM2
found exactly ONE real salient mask on that image, correctly, because there
is exactly one coherent thing to find in a texture raster.

## 7. Wall-clock cost

**~40 s of CPU per SAM2 job on this hardware** (warm cache, tiny checkpoint,
`points_per_side=16`, single 1536x1024-scale image). Against
`digitizer_service/jobs.py`'s single-worker queue, that is 40s a photo job
is unavailable for anything else — a real, bounded cost (bounded by the 90s
timeout, never a hang), not a hidden one.

## 8. The verdict, in full

Judging against the plan's real criteria, not a fabricated pass/fail number:

1. **Region count vs. 20-80 band** — no fixture moved across the band in
   either direction. Tie.
2. **Boundary agreement** — a human-judgment call, stated honestly as one:
   indistinguishable on two fixtures, perfect-and-tied on the third. Tie.
3. **Preflight score/findings** — zero new findings anywhere in the corpus
   (the scorecard's own regression signal), zero score/grade changes on two
   of three target fixtures, no grade change on the third. Tie, cleanly.
4. **Wall-clock cost** — real: ~40s of CPU per photo job, against a
   single-worker queue. Not free.

Three ties and a real cost is not a case for flipping the default. But the
more important finding is that **this corpus cannot currently answer the
question the plan actually cares about** — whether SAM2's instance-level
saliency beats SLIC+RAG's color/space clustering on a real, complex
photographic subject or scene. Two of the three eligible fixtures are
synthetic stand-ins built to exercise the stage-0 classifier's routing logic,
not to depict anything SAM2 or SLIC+RAG would meaningfully disagree about;
the third is a trivial case classical already solves perfectly. Kent's own
real photos don't reach this lane at all under today's classifier.

**Recommendation: `photo_segment_sam2` stays `False`.** The mechanism is
sound — install, wiring, timeout, and fallback all verified against real
hardware and a real timeout in this session — so turning it on for a
specific job is a safe, cheap experiment any time a genuinely complex
`photo_subject`/`photo_scene` fixture becomes available to test it against
(a real face, jacket, or animal photo, committed to the corpus). Until then,
flipping the shipped default would trade a real ~40s/job cost and a
documented cold-start risk for a benefit that has not been measured to
exist.
