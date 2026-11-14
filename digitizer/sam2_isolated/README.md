# Isolated SAM2 venv (photo region former — SAM2 lane)

SAM2 cannot be installed into the shared `digitizer/.venv`: it needs PyTorch
>= 2.5.1 and torchvision >= 0.20.1 (Meta's own `INSTALL.md`), a
multi-gigabyte dependency stack with its own numpy expectations. The shared
venv exists to run a deterministic, offline, CPU-only geometry pipeline
against exact-pinned `numpy==2.5.1` and `opencv-contrib-python-headless==5.0.0.93`
that feed golden tests — pins `pyproject.toml` says to "bump deliberately,
never by accident". Putting torch next to them hands that resolution to
torch's own transitive graph.

Same fix as `rembg_isolated/`, for the same reason: run SAM2 in its OWN venv
and talk to it as a subprocess. Nothing in `digitizer/.venv` changes.

`digitizer_core/stage2_sam2_segment.sam2_segment_seam` shells out to
`digitizer_core/sam2_worker.py` (a standalone script — no `digitizer_core`
imports, so it needs nothing installed here but torch, sam2 and their own
deps), running it under THIS directory's venv's python interpreter, never
the shared one.

## Build it

From the repo's `digitizer/` directory. Three pip commands, in this order —
they are separate on purpose (see `requirements.txt`'s own comment) — plus a
required fourth step to populate the checkpoint cache before this lane is
ever used for a real job.

```
python3.14 -m venv sam2_isolated/venv
```

Verified with Python 3.14 (Task 6's live acceptance run on this repo's own
machine, which had no 3.12 interpreter installed — see
`docs/sam2-segmentation-live-acceptance-2026-08-10.md` §3). The interpreter
version is not a hard pin; PyTorch's CPU wheel index just needs a matching
build for whatever `python3.X` you use. Before assuming a different version
is blocked, check the index the same way that acceptance run did:
`pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5.1" --dry-run`.

1. CPU-only torch, from PyTorch's own CPU wheel index (NOT PyPI — on Linux
   the PyPI wheel bundles CUDA and is several GB larger, and this machine
   has no GPU):

```
sam2_isolated/venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.5.1" "torchvision>=0.20.1"                                    # POSIX
sam2_isolated\venv\Scripts\pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5.1" "torchvision>=0.20.1"   # Windows
```

2. SAM2 itself, from **Meta's own GitHub repo**. `SAM2_BUILD_CUDA=0` skips
   the optional CUDA extension, which needs a matching CUDA toolkit and a
   compiler and buys nothing on a CPU-only box — Meta's `INSTALL.md`
   documents both the env var and that skipping it "shouldn't affect the
   results in most cases".

```
SAM2_BUILD_CUDA=0 sam2_isolated/venv/bin/pip install \
    "git+https://github.com/facebookresearch/sam2.git"                      # POSIX
$env:SAM2_BUILD_CUDA=0; sam2_isolated\venv\Scripts\pip install "git+https://github.com/facebookresearch/sam2.git"   # Windows PowerShell
```

**Never `pip install sam2`.** The PyPI package with that exact name is an
unrelated third-party project. Meta's distribution is named `SAM-2` and is
only published on GitHub; the import package it provides is `sam2`.

3. The one remaining dependency SAM2's core install leaves out:

```
sam2_isolated/venv/bin/pip install -r sam2_isolated/requirements.txt        # POSIX
sam2_isolated\venv\Scripts\pip install -r sam2_isolated\requirements.txt    # Windows
```

No `digitizer_core` install needed in this venv (the worker script is
standalone by design). `stage2_sam2_segment.py` looks for the interpreter at
`sam2_isolated/venv/bin/python` (POSIX) or `sam2_isolated/venv/Scripts/
python.exe` (Windows) by default; nothing else to configure.

4. **Required — populate the checkpoint cache**, before this lane is used
   for any real job. Use `sam2_worker.py`'s dedicated `--prewarm` mode, NOT
   the 5-argument job-mode invocation shown in step 5 below: job mode
   deliberately REFUSES to download (see the note below), so on a machine
   that does not already have the checkpoint cached — e.g. a fresh checkout,
   with no `~/.cache/sam2/sam2.1_hiera_tiny.pt` yet — job mode cannot be
   used to populate the cache in the first place. `--prewarm` is the one
   invocation that bypasses that refusal and actually downloads:

```
sam2_isolated/venv/bin/python digitizer_core/sam2_worker.py --prewarm tiny        # POSIX
sam2_isolated\venv\Scripts\python.exe digitizer_core\sam2_worker.py --prewarm tiny   # Windows
```

   Exit code 0 and `sam2_worker: checkpoint cached at ...` on stdout means
   the checkpoint downloaded (or was already present) and the venv can
   import `sam2`/`torch` enough to run this far. A nonzero exit here means
   either an unknown tier (exit 2) or the download itself failed (exit 4,
   with the underlying error on stderr — e.g. no route to
   `dl.fbaipublicfiles.com`).

   This is NOT optional advice: `sam2_worker.py` deliberately refuses to
   attempt a download on the timed, real-job path when the checkpoint
   isn't already cached (exit code 4, an honest reason) — job mode never
   downloads, no matter what `photo_segment_sam2_timeout_s` is set to —
   so skipping this step means every real job falls back to the classical
   segmenter until someone runs `--prewarm` by hand. The current 240s
   default would in fact cover a from-scratch checkpoint download plus
   torch's own cold import (measured 155.98s, Task 6 — see
   `docs/sam2-segmentation-live-acceptance-2026-08-10.md`): Task 5
   re-sized it off that cold baseline after the original 90s default
   proved too short for a real job even with a warm checkpoint cache
   (full history in the `photo_segment_sam2_timeout_s` comment in
   `digitizer_core/config.py`). The refusal on a cache miss is a design
   decision, not a race against the timeout. This first run here also
   pays for that same download and torch's cold import, so time it
   separately from a second run — see step 5 below for the actual
   job-mode smoke test, which runs against the warm cache this step
   populates.

5. **Optional — smoke-test job mode itself** (the same invocation the real
   seam uses), now that the cache from step 4 is warm:

```
sam2_isolated/venv/bin/python digitizer_core/sam2_worker.py \
    testdata/photo/drone_render.png /tmp/sam2.npz tiny 16 36
```

   Exit code 0 and an `.npz` at `/tmp/sam2.npz` means the venv and the
   checkpoint cache are both working. Inspect it from the SHARED venv:

```
.venv/Scripts/python -c "import numpy as np; d=np.load('/tmp/sam2.npz'); print(d['labels'].shape, d['labels'].dtype, int(d['raw_mask_count']), sorted(set(d['labels'].ravel().tolist()))[:5])"
```

   Expect the label array to match the input image's `(H, W)`, dtype
   `int32`, a raw mask count in the tens-to-low-hundreds, and `-1` present
   (SAM2 does not tile the image; uncovered pixels are normal and the seam
   handles them).

**This venv is NOT committed** (see `digitizer/.gitignore`) and is a
workstation/deploy-time setup step, the same shape as building
`digitizer/.venv` or `rembg_isolated/venv`. Without it built,
`photo_segment_sam2` degrades to the documented fallback
(`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`): the photo lane uses the classical
SLIC+RAG region former, exactly as it does today. Every other part of the
pipeline is unaffected.

## GPU opt-in (workstation only)

Default is CPU, and nothing below changes it: with neither variable set, the
seam runs this directory's venv and the worker builds SAM2 on `cpu`, exactly
as before (worker output re-checked array-for-array against the unmodified
worker on 2 images, 2026-11-13). A deployed service is CPU-only, and every
test and golden was measured on CPU.

Two environment variables, both read only when set:

- `EMB_SAM2_DEVICE=cuda` — read by `sam2_worker.py` (job mode). Unset or
  empty means `cpu`; any value other than `cpu`/`cuda` exits 2. If `cuda` is
  asked for and the venv's torch cannot see a GPU it exits 3 with the reason
  — it never falls back to CPU silently (the seam then falls back to the
  classical segmenter and says why, as for any worker failure).
- `EMB_SAM2_VENV=<venv dir>` — read by `stage2_sam2_segment.py` at import:
  run the worker under that venv instead of `sam2_isolated/venv`. Same
  availability checks apply. Set both before starting the service.

A CUDA venv, kept OUTSIDE the repo (built 2026-11-13 on an RTX 4070, driver
565.90 = CUDA 12.7, Python 3.14.8). `cu126` is the newest index whose wheels
this driver can run: torch 2.15.0 is only on `cu132`, which needs a CUDA 13
driver, so this venv is on 2.14.1 while the CPU venv is on 2.15.0.

```
uv venv --python 3.14 $env:USERPROFILE\.cache\embot-sam2-cuda-venv
uv pip install --python $env:USERPROFILE\.cache\embot-sam2-cuda-venv\Scripts\python.exe --index-url https://download.pytorch.org/whl/cu126 "torch==2.14.1+cu126" "torchvision==0.29.1+cu126"
$env:SAM2_BUILD_CUDA=0; uv pip install --python $env:USERPROFILE\.cache\embot-sam2-cuda-venv\Scripts\python.exe --no-build-isolation "sam-2 @ git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4" "opencv-python-headless==5.0.0.93"
```

Measured 2026-11-13, tiny checkpoint, `points_per_side` 12, on the inputs
the seam actually sends (8 `testdata/photo/` images, 520-1024 px long side),
fp32 on both devices (no autocast):

- **Inference (`generate()`, model already loaded, warm-up excluded,
  median of 3), machine quiet (3-10 % CPU load):** CPU 3.05-3.47 s (one
  outlier 4.83 s), GPU 0.25-0.35 s — about 10-12x.
- **Per job, which is what the seam pays (a fresh worker process each
  time), machine quiet: GPU is NOT faster.** Worker wall, median of 3, on
  three images: CPU 6.5 / 6.4 / 6.7 s against GPU 7.0 / 7.1 / 7.6 s; the
  whole pipeline on `owl_kent.jpg`, 4 runs each, CPU 8.3 s against GPU
  8.9 s. Process start eats the saving: importing CUDA torch costs 5.2 s
  against 2.3 s for CPU torch, plus 0.5 s model load and a 0.3-0.6 s first
  call, against the ~2.9 s of inference it saves. (Under heavy load from
  other jobs the GPU did come out ahead, 1.3-1.5x, because only the CPU
  side competes for cores.) The inference ratio would only pay with a
  worker that stays alive between jobs, which this does not add.
- **VRAM:** 289 MiB after model load, 2.37-2.39 GiB peak allocated, 3.95 GiB
  reserved by torch's caching allocator. Fits beside other GPU users on a
  12 GB card, but not beside one holding more than ~8 GB.
- **GPU masks are NOT identical to CPU.** On 7 of 8 images the `.npz` differs:
  same mask count every time, but 0-3 label pixels differ per image (out of
  ~300-800 k) and the scores differ in the 5th-6th decimal. After the seam's
  own floor and merge the kept-region count, final region count and thread
  count matched on all 8, but on 4 of them two kept regions trade 1-18 pixels.
  Each device was deterministic across 4 runs of its own.

## Disk

Budget roughly 2-3 GB for this venv on top of the checkpoint. The machine
this was written on had 13.5 GB free (measured 2026-08-10) — enough, but not
by a comfortable margin. **Check `df -h` / free space again immediately
before building**, since other work may have consumed it since.

## The checkpoint

`sam2.1_hiera_tiny.pt` (the shipped default tier) is **not committed** — it
is far past the "couple hundred KB" line `digitizer_core/model_data/README.md`
draws for committed inference models. `sam2_worker.py` downloads it itself,
from Meta's own release host
(`https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt`)
into `~/.cache/sam2/`, or wherever the `SAM2_CHECKPOINT_DIR` env var points —
but only when run WITHOUT a subprocess timeout racing it, i.e. only during
"Build it" step 4's required pre-warm above. Every call after that reuses
the cached file, no network needed. The download goes to a `.part` file and
is renamed only on success, so an interrupted download never poisons the
cache.

Available tiers, smallest first: `tiny`, `small`, `base_plus`, `large`
(`cfg.photo_segment_sam2_checkpoint`). `tiny` is the default and the only
one this integration has been built around: CPU-only inference makes the
larger tiers slow enough to be self-defeating against the caller's timeout,
and embroidery-scale regions (floored at `cfg.min_detail_mm`, 1.5 mm) do not
need fine-grained natural-scene accuracy.

If the machine has no route to `dl.fbaipublicfiles.com`, "Build it" step 4
above (which you must run anyway) is where that shows up — loudly, during
setup, not silently during a real job. `sam2_worker.py`'s real-job path does
NOT attempt a download at all when the checkpoint isn't already cached: it
refuses fast (exit code 4, an honest reason) instead — at any
`photo_segment_sam2_timeout_s` value — because a download racing that
timeout and losing would be killed mid-transfer and silently orphan a
partial `.part` file. See step 4 for why pre-warming the cache by hand is
required, not optional.
