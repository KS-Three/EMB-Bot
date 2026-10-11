"""Time Auto Digitize per real-art fixture; write a JSON file and a markdown table.

`artfidelity_self` answers "is the output faithful"; this answers "how long did
it take". It runs the same tracked fixture set (`artfidelity_self.FIXTURES`)
through `digitize()` + `plan_to_design()` — the work the service does for one
Auto Digitize request — and records wall-clock seconds, route and stitch count.

Timings are machine-specific. Compare a run only with another from the same
runner class (the CI job uses `ubuntu-latest`); never against a laptop.

Usage (from `digitizer/`):
    python -m tools.bench_digitize                      # all fixtures
    python -m tools.bench_digitize --repeat 3           # best/median of 3
    python -m tools.bench_digitize --json bench.json --md bench.md
    python -m tools.bench_digitize logo_alpha.png photo/summit_badge.png

Without --json/--md the markdown table goes to stdout. Progress goes to stderr.
A fixture that raises is recorded with its error and does not stop the run; the
exit code is 0 either way, because this is an instrument, not a gate.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from tools.artfidelity_self import FIXTURES  # noqa: E402


def time_fixture(path: Path, repeat: int) -> dict:
    row: dict = {"fixture": path.name, "route": None, "stitches": None,
                 "seconds": None, "seconds_all": [], "error": None}
    for _ in range(repeat):
        t0 = time.perf_counter()
        try:
            result, plan = digitize(path, PipelineConfig())
            plan_to_design(plan)
        except Exception as e:  # noqa: BLE001 — record, keep benchmarking
            row["error"] = f"{type(e).__name__}: {e}"
            return row
        row["seconds_all"].append(round(time.perf_counter() - t0, 3))
        row["route"] = result.design_class
        row["stitches"] = int(plan.stats.stitch_count)
    row["seconds"] = round(statistics.median(row["seconds_all"]), 3)
    return row


def markdown(rows: list[dict], repeat: int) -> str:
    lines = [f"| fixture | route | stitches | seconds (median of {repeat}) |",
             "|---|---|---:|---:|"]
    for r in rows:
        if r["error"]:
            lines.append(f"| {r['fixture']} | ERROR | | {r['error']} |")
        else:
            lines.append(f"| {r['fixture']} | {r['route']} | "
                         f"{r['stitches']} | {r['seconds']:.2f} |")
    ok = [r["seconds"] for r in rows if r["seconds"] is not None]
    if ok:
        lines.append(f"| **total** | | | **{sum(ok):.2f}** |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("images", nargs="*",
                    help="paths, or names under digitizer/testdata; default: all")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    args = ap.parse_args(argv)

    names = args.images or list(FIXTURES)
    paths = [Path(n) if Path(n).exists() else ROOT / "testdata" / n
             for n in names]
    rows = []
    for p in paths:
        print(f"timing {p.name} ...", file=sys.stderr, flush=True)
        rows.append(time_fixture(p, max(1, args.repeat)))
    md = markdown(rows, max(1, args.repeat))
    if args.json:
        args.json.write_text(json.dumps({
            "python": platform.python_version(),
            "platform": platform.platform(),
            "repeat": max(1, args.repeat),
            "rows": rows,
        }, indent=2) + "\n")
    if args.md:
        args.md.write_text(md)
    if not (args.json or args.md):
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
