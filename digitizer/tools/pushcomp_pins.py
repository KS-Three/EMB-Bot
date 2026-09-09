"""Print `tests/test_pushcomp.GOLDEN_FLAG_OFF`'s tuples as THIS tree computes
them — (sha256[:20] of the DST, stitch count, DST bytes) for each fixture and
garment — so a re-pin can be made with the same proof
`recapture_flat_lane_key.py` demands: run it in a worktree at the pre-change
commit first, and only where that reproduces the committed tuple may the new
tuple be written. Usage: `python tools/pushcomp_pins.py [label]`."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import PipelineConfig, plan_stitches, run_stages  # noqa: E402
from digitizer_core.export import export_dst  # noqa: E402

TESTDATA = HERE.parent / "testdata"
CASES = (("logo_whitebg.png", "left_chest"), ("logo_whitebg.png", "towel"),
         ("ribbon_curve.png", "left_chest"), ("ribbon_curve.png", "hat_front"))


def pins() -> dict[tuple[str, str], tuple[str, int, int]]:
    out = {}
    for fixture, garment in CASES:
        base = run_stages(TESTDATA / fixture, PipelineConfig(target_width_mm=80.0))
        plan = plan_stitches(base, PipelineConfig(target_width_mm=80.0, garment_id=garment))
        blob = export_dst(plan)
        n = sum(len(r.points) for b in plan.blocks for r in b.runs)
        out[(fixture, garment)] = (hashlib.sha256(blob).hexdigest()[:20], n, len(blob))
    return out


def main(argv: list[str]) -> int:
    label = argv[0] if argv else "this tree"
    for (fixture, garment), tup in pins().items():
        print(f"{label:>12} {fixture:18} {garment:10} {tup!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
