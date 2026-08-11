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
   for any real job:

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

   This is NOT optional advice: `photo_segment_sam2_timeout_s` (90s
   default) is shorter than a from-scratch checkpoint download plus torch's
   own cold import (measured 155.98s, Task 6 — see
   `docs/sam2-segmentation-live-acceptance-2026-08-10.md`). `sam2_worker.py`
   deliberately refuses to attempt a download on the timed, real-job path
   when the checkpoint isn't already cached (exit code 4, an honest reason)
   rather than race a timeout it cannot win — so skipping this step means
   every real job falls back to the classical segmenter until someone runs
   it by hand. This first run here also pays for that same download and
   cold import, so time it separately from a second run — the second
   (warm) run is the one whose duration should inform
   `photo_segment_sam2_timeout_s`.

**This venv is NOT committed** (see `digitizer/.gitignore`) and is a
workstation/deploy-time setup step, the same shape as building
`digitizer/.venv` or `rembg_isolated/venv`. Without it built,
`photo_segment_sam2` degrades to the documented fallback
(`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`): the photo lane uses the classical
SLIC+RAG region former, exactly as it does today. Every other part of the
pipeline is unaffected.

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
refuses fast (exit code 4, an honest reason) instead, precisely because
`photo_segment_sam2_timeout_s` is too short for a from-scratch download to
finish and a subprocess killed by that timeout would silently orphan a
partial `.part` file. See step 4 for why pre-warming the cache by hand is
required, not optional.
