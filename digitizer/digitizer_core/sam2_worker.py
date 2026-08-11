"""Standalone SAM2 automatic-mask-generation worker.

RUNS IN THE ISOLATED VENV documented at digitizer/sam2_isolated/README.md —
never under the shared digitizer/.venv, and never imported for its heavy
dependencies by the main digitizer_core package. SAM2 needs PyTorch and
torchvision (>= 2.5.1 / >= 0.20.1 per Meta's INSTALL.md); the shared venv
exists to run a deterministic, offline, CPU-only geometry pipeline against
exact-pinned numpy/OpenCV that feed golden tests, and dropping a
multi-gigabyte deep-learning stack into it would put those pins at the mercy
of torch's own transitive resolution. Same isolation, same reason, and the
same subprocess bridge as rembg_worker.py — see that file and
digitizer/rembg_isolated/README.md for the pattern this mirrors.

This script is invoked as a subprocess by
`stage2_sam2_segment.sam2_segment_seam`, pointed at the isolated venv's own
python interpreter. It must import NOTHING from digitizer_core, only the
standard library plus the isolated venv's own installed packages (numpy,
torch, PIL, sam2), so it runs standalone with no digitizer_core install
there.

Usage — two invocation modes, never confused with each other:

  Job mode (run by `stage2_sam2_segment.sam2_segment_seam`, timed by the
  caller's own subprocess timeout). The checkpoint MUST already be cached;
  this mode never downloads — see pre-warm mode below to populate the
  cache. A cache miss here is refused fast and honestly (exit 4) rather
  than raced against a timeout that a from-scratch download cannot win:

    <isolated venv python> sam2_worker.py \\
        <input_image> <output_npz> <checkpoint_tier> \\
        <points_per_side> <min_mask_region_area>

  * <checkpoint_tier> is a key of CHECKPOINTS below ("tiny" is the shipped
    default: smallest disk footprint and fastest CPU inference, which is
    what an embroidery-scale flat-region split needs — not fine-grained
    natural-scene accuracy).
  * <points_per_side> is SAM2's own prompt-grid density.
  * <min_mask_region_area> is a PIXEL area floor handed straight to SAM2's
    `min_mask_region_area` — pixels in <input_image> AS GIVEN to this
    script, which the caller may have already downscaled
    (`photo_segment_sam2_max_side_px`). There is no full-resolution image
    anywhere in this process, so this script applies the floor exactly as
    handed to it with no further scaling. The caller derives it from the
    same `(cfg.min_detail_mm * px_per_mm) ** 2` formula every other "too
    small to sew" floor in this codebase uses, corrected by the downscale
    ratio when one was applied — see `stage2_sam2_segment.sam2_segment_seam`
    for that correction.

  Pre-warm mode (the one-time setup step required by
  `sam2_isolated/README.md`'s "Build it" §4, run BY HAND, with no
  subprocess timeout racing it). Downloads the checkpoint if it is not
  already cached — this is the ONLY invocation of this script that is
  allowed to attempt a download, since job mode's cache-check-and-refuse
  gate exists specifically to keep a doomed, timeout-killed download out
  of a real job:

    <isolated venv python> sam2_worker.py --prewarm <checkpoint_tier>

Output (job mode only): a compressed .npz at <output_npz> with
  * labels           (H, W) int32 — per-pixel label id, -1 where no SAM2
                     mask covered the pixel. SAM2's automatic generator
                     returns OVERLAPPING instance masks and does not tile
                     the image; this array is the resolved, non-overlapping
                     assignment (see _paint_labels for the priority rule).
  * area             (N,) int64   — SAM2's own reported mask area, by label id
  * predicted_iou    (N,) float32 — SAM2's own quality estimate, by label id
  * stability_score  (N,) float32 — SAM2's own stability score, by label id
  * raw_mask_count   int64 scalar — how many masks the generator returned
                     before overlap resolution

Exit code 0 = success (job mode: npz written; pre-warm mode: checkpoint now
cached — no npz). Any other exit code means failure and the reason is on
stderr: 2 = bad arguments (either mode), 3 = import failed (job mode only —
pre-warm mode never imports torch/sam2, only urllib), 4 = checkpoint
problem (job mode: not cached, refused before any download attempt;
pre-warm mode: the download itself failed), 5 = mask generation failed (job
mode only), 6 = writing the output failed (job mode only). In job mode the
caller treats ANY nonzero exit code, and any timeout, as "unavailable" and
degrades silently to the classical SLIC+RAG segmenter — never a hard
pipeline error, since the isolated venv's presence, network status and
checkpoint cache are environment facts, not caller mistakes. Pre-warm mode
is run by hand, not by that caller, so its exit code is for a human (or a
deploy script) to read directly.
"""
from __future__ import annotations

import os
import sys
import tempfile
import urllib.request
from pathlib import Path

# SAM 2.1 checkpoints, from Meta's own release host. tier -> (checkpoint
# filename, hydra config name). The config names are resolved by hydra
# against the `sam2` package's own config module, which `sam2/__init__.py`
# registers on import — they are NOT filesystem paths and must be passed to
# build_sam2 exactly as written, extension included.
CHECKPOINTS: dict[str, tuple[str, str]] = {
    "tiny": ("sam2.1_hiera_tiny.pt", "configs/sam2.1/sam2.1_hiera_t.yaml"),
    "small": ("sam2.1_hiera_small.pt", "configs/sam2.1/sam2.1_hiera_s.yaml"),
    "base_plus": ("sam2.1_hiera_base_plus.pt", "configs/sam2.1/sam2.1_hiera_b+.yaml"),
    "large": ("sam2.1_hiera_large.pt", "configs/sam2.1/sam2.1_hiera_l.yaml"),
}
CHECKPOINT_BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/"

# Seconds allowed for the FIRST-use checkpoint download. Deliberately shorter
# than the caller's own subprocess timeout so a stalled download reports a
# specific reason (exit 4) instead of dying anonymously as a timeout.
DOWNLOAD_TIMEOUT_S = 240


def _cache_dir() -> Path:
    """Where checkpoints live between runs. Outside the repo, and outside
    both venvs, so rebuilding either does not re-download ~150 MB. Honors
    SAM2_CHECKPOINT_DIR the way rembg honors U2NET_HOME."""
    env = os.environ.get("SAM2_CHECKPOINT_DIR")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "sam2"


def _checkpoint_path(tier: str) -> Path:
    return _cache_dir() / CHECKPOINTS[tier][0]


def _checkpoint_is_cached(tier: str) -> bool:
    """True if `tier`'s checkpoint is already fully downloaded — read-only,
    never touches the network, never mutates the cache.

    Callers that are racing a `subprocess.run(timeout=)` (see
    `stage2_sam2_segment.sam2_segment_seam`) MUST check this before doing
    anything else, not just before calling `_ensure_checkpoint`: the
    caller's timeout (measured 90s default) is shorter than a from-scratch
    checkpoint download plus torch's own cold import (measured 155.98s, see
    docs/sam2-segmentation-live-acceptance-2026-08-10.md), so a first-use
    download started under that timeout is guaranteed to be killed
    mid-transfer. Worse: `subprocess.run(timeout=)` kills the child via
    SIGTERM/TerminateProcess, which does NOT run `_ensure_checkpoint`'s own
    `finally: tmp.unlink()` — the download is orphaned as a `.part` file,
    and EVERY subsequent job repeats the same doomed download-and-timeout
    cycle forever, never actually finishing the cache. Checking this FIRST
    and refusing to start a download the timeout cannot let finish turns
    that permanent, silent degradation into one fast, honest failure that
    names the real fix (pre-warm the cache; see `main`'s exit-4 message).
    """
    dest = _checkpoint_path(tier)
    return dest.is_file() and dest.stat().st_size > 0


def _ensure_checkpoint(tier: str) -> Path:
    """Return the cached checkpoint path, downloading it on first use.

    Downloads to a sibling .part file and renames on success, so an
    interrupted or truncated download is never left behind wearing the real
    filename — the failure mode that would otherwise poison every later run
    with an unloadable cache entry.

    This function is the ONE place that actually downloads — deliberately
    called only from `main`'s `--prewarm` mode (driving the pre-warm step
    documented in `sam2_isolated/README.md`'s "Build it" §4) and from
    tests, never reached from the job-mode argv path in `main` below,
    which checks `_checkpoint_is_cached` first and refuses to start a
    download the caller's subprocess timeout would just kill.
    """
    dest_dir = _cache_dir()
    dest = _checkpoint_path(tier)
    if dest.is_file() and dest.stat().st_size > 0:
        return dest

    filename = CHECKPOINTS[tier][0]
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = CHECKPOINT_BASE_URL + filename
    handle, tmp_name = tempfile.mkstemp(dir=str(dest_dir), suffix=".part")
    os.close(handle)
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
            with tmp.open("wb") as out:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        if tmp.stat().st_size == 0:
            raise OSError(f"downloaded 0 bytes from {url}")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    return dest


def _paint_labels(records, shape, np):
    """Resolve SAM2's overlapping instance masks into one non-overlapping
    label array, plus its per-label stat arrays.

    PRIORITY RULE: paint in DESCENDING area order, so a smaller mask always
    lands on top of any larger mask it sits inside. This is the convention
    SAM's own visualizations use, and it is the right one for embroidery:
    the nested detail (an eye inside a face, a badge inside a jacket) is
    exactly the region that must survive as its own sewable shape, while the
    enclosing region loses only the pixels it can most afford. Ranking by
    `predicted_iou` instead would let one large confident mask erase every
    small feature inside it — the opposite failure. Ties break on
    `predicted_iou` descending, then on the generator's own ordering, so the
    output is deterministic for a fixed input.

    Label ids are assigned in paint order, so label 0 is the largest mask.
    """
    order = sorted(
        range(len(records)),
        key=lambda i: (
            -int(records[i]["area"]),
            -float(records[i]["predicted_iou"]),
            i,
        ),
    )
    labels = np.full(shape, -1, np.int32)
    area = np.zeros(len(order), np.int64)
    predicted_iou = np.zeros(len(order), np.float32)
    stability_score = np.zeros(len(order), np.float32)
    for new_id, i in enumerate(order):
        record = records[i]
        labels[np.asarray(record["segmentation"], bool)] = new_id
        area[new_id] = int(record["area"])
        predicted_iou[new_id] = float(record["predicted_iou"])
        stability_score[new_id] = float(record["stability_score"])
    return labels, area, predicted_iou, stability_score


def main(argv: list[str]) -> int:
    # Pre-warm mode: `sam2_worker.py --prewarm <checkpoint_tier>`. Checked
    # FIRST, before the job-mode argument count below, and deliberately
    # calls `_ensure_checkpoint` directly — this is the one invocation that
    # must NOT go through the cache-check-and-refuse gate further down,
    # since its entire purpose is to populate the cache when it is empty.
    # Run by hand (or a deploy script), with no subprocess timeout racing
    # it — see `sam2_isolated/README.md`'s "Build it" §4.
    if len(argv) >= 2 and argv[1] == "--prewarm":
        if len(argv) != 3:
            print(
                "usage: sam2_worker.py --prewarm <checkpoint_tier>",
                file=sys.stderr,
            )
            return 2
        tier = argv[2]
        if tier not in CHECKPOINTS:
            print(
                f"sam2_worker: unknown checkpoint tier {tier!r} "
                f"(known: {sorted(CHECKPOINTS)})",
                file=sys.stderr,
            )
            return 2
        try:
            checkpoint = _ensure_checkpoint(tier)
        except Exception as exc:
            print(f"sam2_worker: checkpoint unavailable: {exc}", file=sys.stderr)
            return 4
        print(f"sam2_worker: checkpoint cached at {checkpoint}")
        return 0

    if len(argv) != 6:
        print(
            "usage: sam2_worker.py <input_image> <output_npz> <checkpoint_tier> "
            "<points_per_side> <min_mask_region_area>   (job mode — the "
            "checkpoint must already be cached; run "
            "'sam2_worker.py --prewarm <checkpoint_tier>' first if not)",
            file=sys.stderr,
        )
        return 2

    in_path, out_path, tier = argv[1], argv[2], argv[3]
    if tier not in CHECKPOINTS:
        print(
            f"sam2_worker: unknown checkpoint tier {tier!r} "
            f"(known: {sorted(CHECKPOINTS)})",
            file=sys.stderr,
        )
        return 2
    try:
        points_per_side = int(argv[4])
        min_mask_region_area = int(argv[5])
    except ValueError as exc:
        print(f"sam2_worker: bad numeric argument: {exc}", file=sys.stderr)
        return 2
    if points_per_side < 1:
        print("sam2_worker: points_per_side must be >= 1", file=sys.stderr)
        return 2

    # Fail fast, BEFORE the slow imports below (torch's own cold import is
    # itself a meaningful chunk of the measured 155.98s cold-start cost) and
    # before touching the network at all, when the checkpoint has never been
    # cached. The caller's subprocess timeout (90s default, always shorter
    # than a from-scratch download) would kill an in-flight download anyway
    # — externally, so `_ensure_checkpoint`'s own cleanup never runs, and the
    # orphaned `.part` file would make every later job repeat the same
    # doomed cycle. Refusing here instead makes the failure fast and the
    # reason honest: this checkpoint tier needs the one-time pre-warm step
    # documented in sam2_isolated/README.md, not a longer timeout.
    if not _checkpoint_is_cached(tier):
        print(
            f"sam2_worker: checkpoint not cached for tier {tier!r} "
            f"(looked for {_checkpoint_path(tier)}) — run the pre-warm step "
            f"(`sam2_worker.py --prewarm {tier}`) documented in "
            "sam2_isolated/README.md before first real use",
            file=sys.stderr,
        )
        return 4

    try:
        import numpy as np
        import torch
        from PIL import Image
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
        from sam2.build_sam import build_sam2
    except Exception as exc:  # environment problem (missing deps), not logic
        print(f"sam2_worker: import failed: {exc}", file=sys.stderr)
        return 3

    try:
        checkpoint = _ensure_checkpoint(tier)
    except Exception as exc:
        print(f"sam2_worker: checkpoint unavailable: {exc}", file=sys.stderr)
        return 4

    try:
        image = np.array(Image.open(in_path).convert("RGB"))
        # CPU-only by construction: this machine has no GPU, and the isolated
        # venv installs CPU torch wheels. No autocast — bfloat16 autocast is a
        # CUDA-path optimization in Meta's own examples and buys nothing here.
        model = build_sam2(CHECKPOINTS[tier][1], str(checkpoint), device="cpu")
        generator = SAM2AutomaticMaskGenerator(
            model,
            points_per_side=points_per_side,
            points_per_batch=64,
            min_mask_region_area=max(0, min_mask_region_area),
            output_mode="binary_mask",
            multimask_output=True,
        )
        with torch.inference_mode():
            records = generator.generate(image)
    except Exception as exc:
        print(f"sam2_worker: mask generation failed: {exc}", file=sys.stderr)
        return 5

    try:
        labels, area, predicted_iou, stability_score = _paint_labels(
            records, image.shape[:2], np
        )
        np.savez_compressed(
            out_path,
            labels=labels,
            area=area,
            predicted_iou=predicted_iou,
            stability_score=stability_score,
            raw_mask_count=np.int64(len(records)),
        )
    except Exception as exc:
        print(f"sam2_worker: writing the output failed: {exc}", file=sys.stderr)
        return 6

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
