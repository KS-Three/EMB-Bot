"""digitizer-core — Fritsch's Stitches auto-digitizing engine.

Build step 1: stages 1-4 (preprocess/background, quantize/thread-snap,
segment, vectorize). Stitch planning and export land in later steps.
"""
from .config import PipelineConfig
from .pipeline import BackgroundInfo, PipelineResult, run_stages
from .regions import Region
from .stage3_segment import ClassicalSegmenter, Segmenter
from .threads import CHART, Thread

__all__ = [
    "PipelineConfig",
    "PipelineResult",
    "BackgroundInfo",
    "Region",
    "Segmenter",
    "ClassicalSegmenter",
    "Thread",
    "CHART",
    "run_stages",
]
