"""The one-pixel spill guard's spill-makers, read directly on enthusiast at
80 mm (the fixture of `tests/test_lettering_coverage_regression.py`):

  off            lane OFF, `satin_rails_follow_edge=True` (the old guard)
  on_old         lane ON, the same flag only: what the guard read under
                 #837's lane_on_plugin before this change
  on_new         lane ON, the flag + `columns.RAIL_REACH_INSET_MM = 0`
  off_new        lane OFF with both knobs: must equal `off`
  on_shipped     lane ON, no spill-maker (what the headline guard reads)

usage (cwd digitizer/): python guard_teeth.py
"""
import os
import sys

sys.path.insert(0, os.getcwd())
import tools.artfidelity_self as afs  # noqa: E402
from tools.dropped_elements import analyse_design  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
import digitizer_core.columns as columns  # noqa: E402
from pathlib import Path  # noqa: E402

FIX = Path("testdata/photo/enthusiast_logo.png")
LANE = {"lettering_columns": True, "lettering_words": True}
ARMS = {"off": ({"satin_rails_follow_edge": True}, 0.11),
        "on_old": ({**LANE, "satin_rails_follow_edge": True}, 0.11),
        "on_new": ({**LANE, "satin_rails_follow_edge": True}, 0.0),
        "off_new": ({"satin_rails_follow_edge": True}, 0.0),
        "on_shipped": (LANE, 0.11)}
afs.SHIFT_STEP_MM, afs.SHIFT_MM = 0.1, 1.2
designs = {}
for name, (flags, inset) in ARMS.items():
    columns.RAIL_REACH_INSET_MM = inset
    _g, _r, _p, design = digitize_once(FIX, base_cfg(80.0, "left_chest", **flags))
    designs[name] = design
    row = analyse_design(FIX, design)
    print(f"{name:11s} one-pixel lost_frac {row['lost_frac']:.4f}  "
          f"shift ({row['shift_x_mm']:+.1f}, {row['shift_y_mm']:+.1f})", flush=True)
columns.RAIL_REACH_INSET_MM = 0.11
print("off_new == off (byte-identical stitches):",
      designs["off_new"]["stitches"] == designs["off"]["stitches"])
