"""The spike's geometry now lives in the engine
(`digitizer_core/letterform_priors.py`, wired behind
`PipelineConfig.letterform_priors_k`, default None). This module re-exports
it so the spike's tools, the sheets and the write-up's commands keep
working from this folder with ONE copy of the code."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]        # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core.letterform_priors import *          # noqa: E402,F401,F403
from digitizer_core.letterform_priors import (          # noqa: E402,F401 - the underscored names the spike reads
    _cap_check, _chords_of, _drop_chamfers, _initial_lines, _invalid_point, _line_residual,
    _merge_arcs, _offenders, _rebuild, _samples_of, _snap_angles, _snap_baseline, _snap_widths,
    _stem_angles, _try_arc, _try_line, _turn_deg, _edge_normal, _dp_open)
