"""Standalone rembg background-removal worker (photo plan §2 row 1).

RUNS IN THE ISOLATED VENV documented at digitizer/rembg_isolated/README.md —
never under the shared digitizer/.venv, and never imported by the main
digitizer_core package. rembg's pymatting -> numba dependency needs
numpy<2.5; the shared venv pins numpy==2.5.1 for the k-means goldens, so
`import rembg` fails there outright (full probe record:
docs/photo-prep-deps-probe-2026-08-04.md §2, and stage1_photo_prep.py's
module docstring). This script is invoked as a subprocess by
`stage1_photo_prep.remove_background_seam`, pointed at the isolated venv's
own python interpreter — it must import NOTHING from digitizer_core, only
the standard library and rembg's own direct dependencies (rembg, Pillow), so
it runs standalone with no digitizer_core install in that venv.

Usage:
    <isolated venv python> rembg_worker.py <input_image> <output_mask> [model]

Reads the image at <input_image>, runs it through rembg with the named model
(default "isnet-general-use" — the plan's default tier; first use downloads
the model, ~178 MB, into rembg's own cache dir — see the README), and writes
its alpha channel as an 8-bit grayscale PNG to <output_mask>: 255 =
subject/foreground pixel, 0 = background, per rembg's own matting. The
caller does its own thresholding and morphology on this file — this
script's only job is running the model and hosting the numpy<2.5
environment it needs.

Exit code 0 = success, mask written. Any other exit code means failure; the
reason is on stderr. The caller treats any nonzero exit code, and any
timeout, as "unavailable" and degrades to the documented no-op — never a
hard pipeline error, since the isolated venv's presence, network status and
model cache are environment facts, not caller mistakes.
"""
from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(
            "usage: rembg_worker.py <input_image> <output_mask> [model_name]",
            file=sys.stderr,
        )
        return 2

    in_path, out_path = argv[1], argv[2]
    model_name = argv[3] if len(argv) == 4 else "isnet-general-use"

    try:
        from PIL import Image
        from rembg import new_session, remove
    except Exception as exc:  # environment problem (missing deps), not logic
        print(f"rembg_worker: import failed: {exc}", file=sys.stderr)
        return 3

    try:
        session = new_session(model_name)
        image = Image.open(in_path).convert("RGB")
        cutout = remove(image, session=session)
    except Exception as exc:
        print(f"rembg_worker: background removal failed: {exc}", file=sys.stderr)
        return 4

    try:
        cutout.getchannel("A").save(out_path)
    except Exception as exc:
        print(f"rembg_worker: writing the mask failed: {exc}", file=sys.stderr)
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
