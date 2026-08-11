"""Probe 3 — full digitize with debug artifacts + per-region tier report."""
import sys
from pathlib import Path
from collections import Counter

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
cfg = PipelineConfig(target_width_mm=80.0, debug_dir=OUT)
res, plan = digitize("testdata/photo/repro_gradient_white_icon.png", cfg)

print(f"regions={len(res.regions)}")
print("warnings:", [f"{w['code']}" for w in plan.warnings])
print(f"blocks={len(plan.blocks)}")
tiers = Counter()
stitches = 0
for b in plan.blocks:
    for r in b.runs:
        tiers[r.kind] += 1
        stitches += len(r.points)
print("run kinds:", dict(tiers), "total stitch points:", stitches)
for b in plan.blocks:
    n = sum(len(r.points) for r in b.runs)
    print(f"  block thread={b.thread_index} runs={len(b.runs)} pts={n}")
