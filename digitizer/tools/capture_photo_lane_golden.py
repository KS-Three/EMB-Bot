#!/usr/bin/env python
"""One-off: capture the pre-refactor photo-lane stage-2 golden.

Run ONCE, from `digitizer/`, BEFORE `stage2_photo_segment.segment()`'s
`kept regions -> Quant` tail is extracted into `kept_masks_to_quant()`:

    .venv/Scripts/python tools/capture_photo_lane_golden.py

`tests/test_photo_lane_byte_identical.py` then re-runs the same fixtures
through the post-extraction code and asserts an exact match. Do not re-run
this script to make that test go green — that defeats the invariant it
exists to pin. Re-run it only for a change that deliberately, knowingly
moves stage 2's own output, and say so in the commit message (see
`testdata/flat_lane_golden.json`'s own documented re-captures for the
precedent).

The snapshot helper lives in the test module, not here, so the two can
never drift apart.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_photo_lane_byte_identical import (  # noqa: E402
    FIXTURES,
    GOLDEN_PATH,
    _snapshot,
)


def main() -> None:
    golden = {key: _snapshot(key) for key in FIXTURES}
    GOLDEN_PATH.write_text(json.dumps(golden, indent=1), encoding="utf-8")
    for key, snap in golden.items():
        print(
            f"{key}: {len(snap['thread_indices'])} threads, "
            f"{len(snap['warnings'])} warnings, labels {snap['labels_sha256'][:12]}"
        )


if __name__ == "__main__":
    main()
