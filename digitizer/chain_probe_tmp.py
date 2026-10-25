import sys
sys.path.insert(0, '.')
from pathlib import Path
from digitizer_core import PipelineConfig
from digitizer_core.pipeline import run_stages, plan_stitches
from tests.conftest import FLIP_2026_10_23
from tests.test_chaining import _thread_bare_mm
T = Path('testdata')
res = run_stages(T/'photo'/'enthusiast_logo.png', PipelineConfig(target_width_mm=93.0))
def floor(kw):
    plan = plan_stitches(res, PipelineConfig(target_width_mm=93.0, garment_id="left_chest", chain_links=False, **kw))
    return round(_thread_bare_mm(plan)[2], 2)
print("all15off", floor(FLIP_2026_10_23), flush=True)
for k in FLIP_2026_10_23:
    kw = dict(FLIP_2026_10_23); kw.pop(k)
    print("only", k, "ON ->", floor(kw), flush=True)
