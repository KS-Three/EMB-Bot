"""`tools/edge_truth_ladder.py` (ANALYTIC vector truth, synthetic art) at
1.8 / 3 / 5 px/mm, native read OFF / ON / ON with the floor at 3.0.

The ladder's rungs are fixed widths (whole 4x supersamples of the
generator's 800-px frame), each read at 80 mm. Here the 200, 400 and 600 px
rungs are read at the design width that puts stage 1 at the nominal
px/mm (never under it), by setting the module's TARGET_MM — the truth is
mapped analytically into the prepped frame, so it follows. Flat lane, as
the ladder runs by default. Reported per shape: rms and hausdorff distance
to the analytic edge, mm, and reversals per 100 mm (`variants.spikes`).

usage (from digitizer/):
    .venv/Scripts/python ../docs/renders/subpixel-res-gate-2026-10-11/scripts/ladder_gate.py OUT.json
"""
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "digitizer"), str(ROOT / "digitizer" / "tools")]

import edge_truth_ladder as el  # noqa: E402

PLAN = ((1.8, 200), (3.0, 400), (5.0, 600))
FLAGS = {"off": ["subpixel_edges_upscaled=false"], "on": None,
         "gate3": ["subpixel_edges_min_px_per_mm=3.0"]}


def main(out):
    work = Path(tempfile.mkdtemp(prefix="ladder_gate_"))
    rows = []
    for fixture in el.FIXTURES:
        for ppm, w in PLAN:
            el.TARGET_MM = 80.0
            base = el.measure_rung(fixture, w, "flat", work, None)["input_px_per_mm"]
            el.TARGET_MM = math.floor(80.0 * base / ppm * 10.0) / 10.0
            for name, flag in FLAGS.items():
                r = el.measure_rung(fixture, w, "flat", work, flag)
                for row in r["rows"]:
                    rows.append({"fixture": fixture, "rung_px": w, "target_mm": el.TARGET_MM,
                                 "nominal": ppm, "input_px_per_mm": r["input_px_per_mm"],
                                 "config": name, **{k: row.get(k) for k in
                                 ("shape", "produced", "vertices", "rms_mm", "hausdorff_mm",
                                  "spread_mm", "offset_mm")}})
                print(fixture, w, f"{el.TARGET_MM} mm in {r['input_px_per_mm']:.3f}", name,
                      [(x["shape"], x.get("rms_mm") and round(x["rms_mm"], 3)) for x in r["rows"]], flush=True)
    Path(out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
