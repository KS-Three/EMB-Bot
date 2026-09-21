#!/usr/bin/env python
"""Does the shipped GROUND_SEWN check fire on exactly the two grounds?

Run from digitizer/:  .venv/Scripts/python tools/ground_sewn_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.preflight import GROUND_SEWN, run_preflight  # noqa: E402

CASES = [
    ("golke",        "testdata/photo/logo_gaulke_roofing.png", True),
    ("summit",       "testdata/photo/summit_badge.png",        True),
    ("tires",        "testdata/logo_script_tires.png",         False),
    ("logo_whitebg", "testdata/logo_whitebg.png",              False),
    ("logo_alpha",   "testdata/logo_alpha.png",                False),
    ("ribbon_curve", "testdata/ribbon_curve.png",              False),
    ("bg_uncertain", "testdata/bg_uncertain.png",              False),
    ("becker",       "testdata/becker_marine_logo.png",        False),
    ("enthusiast",   "testdata/photo/enthusiast_logo.png",     False),
    ("bridge_bar",   "testdata/photo/logo_bridge_bar.jpg",     False),
    ("golden_tee",   "testdata/photo/logo_golden_tee.jpg",     False),
    ("drone",        "testdata/photo/drone_render.png",        False),
]

bad = 0
print(f"{'case':14s} {'fired':>6s} {'sev':>6s} {'span':>6s} {'dE':>7s} {'area':>6s}  verdict")
print("-" * 68)
for name, rel, truth in CASES:
    path = ROOT / rel
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(path, cfg)
    rep = run_preflight(result, plan, cfg, image=path)
    hit = next((f for f in rep["findings"] if f["code"] == GROUND_SEWN), None)
    m = rep["metrics"]
    ok = bool(hit) == truth
    bad += 0 if ok else 1
    print(f"{name:14s} {str(bool(hit)):>6s} {(hit['severity'] if hit else '-'):>6s} "
          f"{m.get('ground_span_frac')!s:>6s} {m.get('ground_delta_e')!s:>7s} "
          f"{m.get('ground_area_frac')!s:>6s}  "
          f"{'OK' if ok else ('MISS' if truth else 'FALSE POSITIVE')}")

print()
print("PERFECT SEPARATION" if bad == 0 else f"{bad} WRONG")
sys.exit(1 if bad else 0)
