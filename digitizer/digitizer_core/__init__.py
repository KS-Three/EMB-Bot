"""digitizer-core — Fritsch's Stitches auto-digitizing engine.

Build step 1: stages 1-4 (preprocess/background, quantize/thread-snap,
segment, vectorize). Build step 3: stages 5-7 (sew order and underlap, fill
and underlay, sequencing and ties) plus DST export. Satin is build step 4.
"""
from .config import PipelineConfig
from .export import export_dst, write_dst
from .fabrics import FABRICS, Fabric, fabric_for_garment, get_fabric
from .pipeline import (
    BackgroundInfo,
    PipelineResult,
    digitize,
    plan_stitches,
    run_stages,
)
from .regions import Region
from .stage3_segment import ClassicalSegmenter, Segmenter
from .stitches import PlanStats, StitchBlock, StitchPlan, StitchRun
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
    "Fabric",
    "FABRICS",
    "get_fabric",
    "fabric_for_garment",
    "StitchPlan",
    "StitchBlock",
    "StitchRun",
    "PlanStats",
    "run_stages",
    "plan_stitches",
    "digitize",
    "export_dst",
    "write_dst",
]
