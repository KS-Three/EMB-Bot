"""Cache stage 4 inputs (masks, thread_indices, prep, cfg) for Becker at 1.8/3/5 px/mm."""
import pickle
import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(WT / "digitizer")]
from digitizer_core import pipeline  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402

OUT = Path(sys.argv[1])
BECKER = WT / "digitizer" / "testdata" / "becker_marine_logo.png"
for width in [float(w) for w in sys.argv[2:]]:
    cap = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, c):
        cap.update(masks=masks, ti=ti, p=p, cfg=c)
        return orig(masks, ti, p, c)

    pipeline.vectorize = wrap
    try:
        pipeline.build_generation(str(BECKER), PipelineConfig(target_width_mm=width))
    finally:
        pipeline.vectorize = orig
    (OUT / f"becker_{width:g}.pkl").write_bytes(pickle.dumps(cap))
    print(width, cap["p"].input_px_per_mm, cap["p"].px_per_mm, cap["p"].upscale, len(cap["masks"]), flush=True)
