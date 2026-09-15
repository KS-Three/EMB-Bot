#!/usr/bin/env python
"""Which shape carries the two-mask disagreement now?

`test_resnap_mask_matches_grader` pins one shape id (`Se6eddd27` on
`photo/logo_gaulke_roofing.png`) as "the region the flag exists for": the raw
`_region_footprint` raster picks `3971 Silver` on a bimodal near-black +
near-white pixel set, while the grader's eroded, background-excluded mask
scores that same Silver terribly.

Shape ids are derived from centroid + thread (`regions._raw_id`), so cropping
the letterbox bars renames every shape in the design and that constant goes
stale. **Renaming the constant is only legitimate if the PHENOMENON survived**
— otherwise the fixture has stopped carrying the property and the tests need
a different design, not a different string. This prints the evidence either
way: every shape where the two masks choose different spools, with both
pixel counts, so the replacement is chosen on the measurement rather than on
whatever makes the suite green.

Run from digitizer/:  .venv/Scripts/python tools/resnap_shape_relocate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stage1_prep import prep  # noqa: E402
from digitizer_core.stage4_vectorize import _region_footprint  # noqa: E402
from digitizer_core.threads import chart_for, rgb_to_lab  # noqa: E402

try:
    from tests.conftest import PRE_FLIP
except Exception:
    PRE_FLIP = {}

ART = ROOT / "testdata" / "photo" / "logo_gaulke_roofing.png"


def main() -> int:
    for on in (False, True):
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                             **{**PRE_FLIP, "resnap_mask_matches_grader": on})
        result, _plan = digitize(ART, cfg)
        threads = {r.shape_id: r.thread_number for r in result.regions}
        print(f"\n=== resnap_mask_matches_grader={on} : {len(result.regions)} regions ===")
        silver = [s for s, t in threads.items() if t == "3971"]
        print(f"  shapes sewing 3971 Silver: {silver or 'none'}")
        if on is False:
            off_threads = dict(threads)
        else:
            moved = {s: (off_threads.get(s), t) for s, t in threads.items()
                     if off_threads.get(s) != t}
            print(f"  shapes whose thread MOVED when the flag went on: {len(moved)}")
            for s, (a, b) in list(moved.items())[:12]:
                print(f"    {s}: {a} -> {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
