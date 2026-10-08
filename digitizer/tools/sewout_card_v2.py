"""Calibration card v2 — command line. The card lives in
`digitizer_core.calibration.card_v2` (the service serves it from there);
this writes the design JSON the bridge encodes.

Usage (from digitizer/):
  PYTHONPATH=. .venv/bin/python tools/sewout_card_v2.py       # generate
Then, from the repo root, the same bridge v1 uses:
  node tools/sewout_bridge.mjs \\
      digitizer/debug_out/sewout/EMBBOT_CALIBRATION_CARD_V2.design.json \\
      digitizer/debug_out/sewout/EMBBOT_CALIBRATION_CARD_V2.dst
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitizer_core.adapter import design_size_mm, plan_to_design          # noqa: E402
from digitizer_core.calibration.card_v2 import LABEL, NAME, OUT, build_card_v2  # noqa: E402


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plan, report = build_card_v2()
    stats = plan.stats
    design = plan_to_design(plan, name=LABEL)
    (OUT / f"{NAME}.design.json").write_text(json.dumps(design), encoding="utf-8")
    (OUT / f"{NAME}.colors.json").write_text(
        json.dumps([list(b.rgb) for b in plan.blocks]), encoding="utf-8")
    w, h = design_size_mm(design)
    report["totals"] = {
        "stitch_count": stats.stitch_count,
        "color_blocks": len(plan.blocks),
        "color_changes": stats.color_changes,
        "trims": stats.trims,
        "size_mm_plan": [round(v, 2) for v in stats.size_mm],
        "size_mm_design": [round(w, 2), round(h, 2)],
        "design_records": len(design["stitches"]),
    }
    (OUT / f"{NAME}.report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({**report["totals"], "hoop": report["hoop"]}, indent=2))
    print("design ->", OUT / f"{NAME}.design.json")
    print("next   -> node tools/sewout_bridge.mjs "
          f"digitizer/debug_out/sewout/{NAME}.design.json digitizer/debug_out/sewout/{NAME}.dst")


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main()
