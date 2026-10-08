"""Digitize real artwork into Design JSON for tools/export-audit.mjs.

Runs the SAME stage chain the service's `/digitize` route runs
(`build_generation` -> `finish_generation` -> `plan_stitches` ->
`plan_to_design`), minus HTTP and the job registry, with the Studio's own
default parameters (`app/src/lib/project.js` DEFAULT_DIGITIZE_PARAMS). The
output is the `design` the service returns, which the Studio stores on a
digitized element as `element.result` and generates from offline.

Usage (repo root):
    digitizer/.venv/bin/python tools/export_audit_digitize.py OUT.json IMG [IMG ...]
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "digitizer"))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402

# app/src/lib/project.js DEFAULT_DIGITIZE_PARAMS, minus the keys that are
# PipelineConfig defaults already.
STUDIO_DEFAULTS = {"target_width_mm": 80, "max_colors": 6, "satin": True, "edge_cap": "bean"}


def digitize(path: str) -> dict:
    with open(path, "rb") as fh:
        data = fh.read()
    # The service decodes with cv2 first (`app._decode`, a size guard); the
    # pipeline's own `stage1_prep._load` reads raw bytes identically, so the
    # bytes go straight in.
    cfg = PipelineConfig(**STUDIO_DEFAULTS)
    gen = build_generation(data, cfg, exif_source=data)
    result = finish_generation(gen, cfg)
    plan = plan_stitches(result, cfg)
    return plan_to_design(plan, name="Digitized design")


def main(argv: list[str]) -> None:
    out, imgs = argv[0], argv[1:]
    designs = {os.path.splitext(os.path.basename(p))[0]: digitize(p) for p in imgs}
    with open(out, "w") as fh:
        json.dump(designs, fh)


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main(sys.argv[1:])
