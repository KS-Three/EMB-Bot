"""gate_table.py's harness, configs ON (today) vs ON + subpixel_corner_runs,
then add_stairs. usage: truth_run.py RUNS OUT"""
import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(WT / "docs/renders/subpixel-res-gate-2026-10-11/scripts")]
import gate_table as G  # noqa: E402
import add_stairs  # noqa: E402

G.CONFIGS = {"on": {}, "runs": {"subpixel_corner_runs": True}}
runs, out = Path(sys.argv[1]), Path(sys.argv[2])
G.main(runs, out)
add_stairs.main(runs, out / "results.json")
print("done")
