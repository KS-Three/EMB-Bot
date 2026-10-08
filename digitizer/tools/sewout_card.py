"""The sew-out gate card — command line. The card itself lives in
`digitizer_core.calibration.card` since 2026-09-30 (so the service can build
the customer card without importing a tool); this writes its files.

Usage (from digitizer/):
  PYTHONPATH=. .venv/bin/python tools/sewout_card.py            # generate
  PYTHONPATH=. .venv/bin/python tools/sewout_card.py --check-dst \\
      debug_out/sewout/EMBBOT_SEWOUT_CARD.dst                   # pystitch sanity

Then, from the repo root:
  node tools/sewout_bridge.mjs   # encode with the browser codec + verify + preview
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitizer_core.adapter import design_size_mm, plan_to_design   # noqa: E402
from digitizer_core.calibration.card import OUT, build_card         # noqa: E402


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    plan, report = build_card()
    stats = plan.stats
    design = plan_to_design(plan, name="EMBBOT SEWOUT CARD 2026-07-31")

    (OUT / "EMBBOT_SEWOUT_CARD.design.json").write_text(
        json.dumps(design), encoding="utf-8")
    (OUT / "EMBBOT_SEWOUT_CARD.colors.json").write_text(
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
    (OUT / "EMBBOT_SEWOUT_CARD.report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], indent=2))
    print("design ->", OUT / "EMBBOT_SEWOUT_CARD.design.json")
    print("next   -> node tools/sewout_bridge.mjs   (from the repo root)")


def check_dst(path: str) -> None:
    """pystitch sanity read of the finished DST. Since the 2026-09-08 codec
    fix this agrees with the browser decode: size upright, colour changes
    counted."""
    import pystitch
    pat = pystitch.read_dst(path)
    xs = [s[0] for s in pat.stitches]
    ys = [s[1] for s in pat.stitches]
    colors = sum(1 for s in pat.stitches if s[2] == pystitch.COLOR_CHANGE)
    print(json.dumps({
        "pystitch_size_mm": [round((max(xs) - min(xs)) / 10.0, 1),
                             round((max(ys) - min(ys)) / 10.0, 1)],
        "pystitch_color_changes": colors,
        "records": len(pat.stitches),
    }, indent=2))


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--check-dst":
        check_dst(sys.argv[2])
    else:
        main()
