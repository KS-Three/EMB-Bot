"""marine_match_figs: stitches, trims, jumps, needle-up travel and the preflight grade/metrics
of one design under several flag arms (2026-11-18), for the MARINE match flags.

  python -m tools.marine_match_figs --out FILE.json --job SLUG [--width MM] [--arms name=flag,flag ...]

`--job` is a `tools.pro_baseline.JOBS` slug (its art, width and garment); `--width` overrides
the width (Becker at 114 mm). Each arm is `extra.lettering_columns_<flag>` keys turned ON; `base`
is main (block_butt ON since #1684). Numbers only."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

ALL = "r_bowl,block_butt_small,a_bar,block_lean"
DEFAULT_ARMS = ["base=", "r_bowl=r_bowl", "block_butt_small=block_butt_small", "a_bar=a_bar",
                "block_lean=block_lean", "all=" + ALL]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--width", type=float)
    ap.add_argument("--arms", nargs="*", default=DEFAULT_ARMS)
    a = ap.parse_args(argv)
    from digitizer_core.export import write_dst
    from tools import pro_pair
    from tools.flag_sweep import measure_dst
    from tools.pro_baseline import JOBS, resolve
    garment, width, art = JOBS[a.job][0], float(a.width or JOBS[a.job][1]), Path(resolve(JOBS[a.job][2]))
    res = {"job": a.job, "width_mm": width, "garment": garment, "arms": {}}
    for arm in a.arms:
        name, _, flags = arm.partition("=")
        extra = {}                     # block_butt is ON by default since #1684
        extra.update({f"extra.lettering_columns_{f}": True for f in flags.split(",") if f})
        d = pro_pair.digitize(art, width, garment, extra)
        with tempfile.TemporaryDirectory() as t:
            dst = Path(t) / "x.dst"
            write_dst(d.plan, dst)
            fig = measure_dst(dst)
        from digitizer_core.preflight import run_preflight
        pf = run_preflight(d.result, d.plan, d.cfg)
        res["arms"][name] = {**fig, "preflight": {k: pf.get(k) for k in ("grade", "score", "metrics")}}
        print(a.job, name, fig["stitches"], flush=True)
    a.out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
