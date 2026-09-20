"""The sew-out arm for `satin_walk_cursor_reach_mm` — Kent's ruling
2026-09-20: the flag stays OFF until cloth settles it.

The measurement is done (`tools/refused_walks.py`, scope-history 2026-09-20):
widening the cursor's reach onto the travel web buys ~20 fewer trims across
the nine corpus logos and costs ~65 mm of exposed running thread, about
3.3 mm per trim saved, with no knee between 4 and 5 mm to site a default at.
Both sides of that are things the eye judges and no metric here can: a trim
leaves tails to clip and a tie-off bump, a rescued walk leaves a short run of
thread lying on the fabric between letters. So this writes the arms as
machine files for one hooping.

Three cases, chosen because they price the trade differently (the per-case
numbers are in the README this writes):

  becker100   3.0 mm of exposed thread buys three trims — the best ratio
  gaulke      14.7 mm buys five — the worst, and the one to look at hardest
  marine127   0.4 mm buys two — nearly free, and the plan's own yardstick

Each at reach OFF / 4.0 / 5.0 mm, `.dst` and `.pes` through the same
`digitizer_core.export` path the service uses, every file read back through
pystitch and checked against the plan's own stitch count before it is
offered to the machine.

    cd digitizer
    .venv/bin/python -m tools.sewout_walk_reach            # -> .cache/sewout-walk-reach/
    .venv/bin/python -m tools.sewout_walk_reach --out DIR

Nothing here changes the engine: every arm is a `PipelineConfig` field.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pystitch  # noqa: E402

from digitizer_core import export as core_export  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_service import formats  # noqa: E402

from tools.travel_cover import travel_exposure  # noqa: E402

RENDERS = REPO / "docs" / "renders"
CASES = [
    # (name, path, target width mm, garment, why this case is on the sheet)
    ("becker100", ROOT / "testdata" / "becker_marine_logo.png", 100.0, "left_chest",
     "best ratio: 3.0 mm of exposed thread for three trims"),
    ("gaulke", ROOT / "testdata" / "photo" / "logo_gaulke_roofing.png", 80.0, "left_chest",
     "worst ratio: 14.7 mm for five trims — look hardest here"),
    ("marine127", RENDERS / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png", 127.4,
     "left_chest", "nearly free: 0.4 mm for two trims, and the plan's yardstick"),
]
ARMS = [("off", 0.0), ("reach4", 4.0), ("reach5", 5.0)]
FORMATS = ("dst", "pes")


def _readback(data: bytes, fmt: str) -> int:
    """Stitch penetrations the written file decodes to."""
    import io
    reader = {"dst": pystitch.read_dst, "pes": pystitch.read_pes}[fmt]
    pattern = reader(io.BytesIO(data))
    return sum(1 for s in pattern.stitches if s[2] == pystitch.STITCH)


def run(out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for name, path, width_mm, garment, why in CASES:
        if not Path(path).exists():
            print(f"  [skip] {name}: {path} is not in this checkout", file=sys.stderr)
            continue
        base = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
        gen = build_generation(str(path), base)
        for arm, reach in ARMS:
            cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                                 satin_walk_cursor_reach_mm=reach)
            result = finish_generation(gen.fork(), cfg)
            plan = plan_stitches(result, cfg)
            pattern = core_export.plan_to_pattern(plan)
            pattern.metadata("name", f"{name}_{arm}"[:16])
            wrote = {}
            for fmt in FORMATS:
                data = formats.write(pattern, fmt)
                f = out / f"{name}_{arm}.{fmt}"
                f.write_bytes(data)
                # Read it back before it is offered to the machine: a file the
                # writer and the reader disagree about is not a sew-out arm.
                # Measured 2026-09-20: both writers round-trip the plan's
                # penetrations exactly, so this is an equality, not a report.
                got = _readback(data, fmt)
                if got != plan.stats.stitch_count:
                    raise SystemExit(
                        f"{f.name}: wrote {plan.stats.stitch_count} stitches, "
                        f"reads back {got} — not offering this to the machine")
                wrote[fmt] = {"bytes": len(data), "readback_stitches": got}
            tx = travel_exposure(plan)
            rows.append({"case": name, "why": why, "arm": arm, "reach_mm": reach,
                         "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                         "exposed_mm": round(tx["exposed_mm"], 1),
                         "worst_leg_mm": round(tx["worst_leg_mm"], 1), "files": wrote})
            print(f"  {name}/{arm}: {plan.stats.stitch_count:,} stitches, "
                  f"{plan.stats.trims} trims, {rows[-1]['exposed_mm']} mm exposed", file=sys.stderr)
    (out / "README.md").write_text(readme(rows), encoding="utf-8")
    return rows


def readme(rows: list[dict]) -> str:
    out = ["# Sew-out arm — `satin_walk_cursor_reach_mm` (2026-09-20)", "",
           "Kent's ruling the day it was built: **the flag stays OFF until cloth",
           "settles it.** Both sides of the trade are things the eye judges —",
           "a trim leaves tails to clip and a tie-off bump; a rescued walk leaves",
           "a short run of thread lying on the fabric between letters.", "",
           "Sew each case's three arms in one hooping, same thread, same",
           "stabiliser. Then answer **question D** below.", ""]
    out.append("| case | arm | stitches | trims | exposed travel mm | worst leg mm |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        out.append(f"| {r['case']} | {r['arm']} | {r['stitches']:,} | {r['trims']} "
                   f"| {r['exposed_mm']} | {r['worst_leg_mm']} |")
    out += ["", "Why these three cases:", ""]
    for name in dict.fromkeys(r["case"] for r in rows):
        why = next(r["why"] for r in rows if r["case"] == name)
        out.append(f"- **{name}** — {why}")
    out += ["",
            "## Question D — does the rescued walk read better than the trim it saves?",
            "",
            "Look between the letters, where `off` has a trim and `reach4` /",
            "`reach5` have a short run instead.",
            "",
            "1. **Can you see the run at all** on the fabric, at arm's length? At",
            "   reading distance?",
            "2. **Against the trim it replaced:** which looks worse — the run, or",
            "   the tails and tie-off bump where the trim was?",
            "3. **Does the worst case change the answer?** gaulke pays the most",
            "   exposed thread; becker the least. If gaulke reads badly and becker",
            "   reads fine, the flag wants a per-design rule, not one number.",
            "4. **4 vs 5 mm:** is there any visible difference? The measurement",
            "   found no knee, so if the eye finds none either, the cheaper radius",
            "   wins by default.",
            "",
            "What each answer flips:",
            "",
            "- The run is invisible or clearly better than the trim → flip ON at",
            "  the radius that reads the same, and re-price the sheet's other",
            "  trim questions against it.",
            "- The run shows and the trim does not → the flag stays OFF for good,",
            "  and the refused-walk bucket is closed: the census already showed",
            "  three quarters of it is a web that does not reach, where a trim is",
            "  correct.",
            "- It depends on the design → the flag needs a gate (density,",
            "  letter spacing, or thread colour against fabric), and that gate is",
            "  the next measurement.",
            "",
            "*(files written by `digitizer/tools/sewout_walk_reach.py`; every one",
            "read back through pystitch before it was offered to the machine.",
            "Numbers and the full census: scope-history 2026-09-20.)*"]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "sewout-walk-reach")
    a = ap.parse_args(argv)
    rows = run(a.out)
    print(readme(rows))
    print(f"\n{len(rows)} arms written to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
