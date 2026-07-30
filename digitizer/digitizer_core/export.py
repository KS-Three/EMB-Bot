"""Writing a StitchPlan out as a machine file.

pyembroidery (MIT, pure Python) does the format work. Build step 8 turns this
into the universal export adapter every EMB-Bot design goes through; here it
exists so a plan can be sewn and judged.

**Coordinate convention, verified rather than assumed.** pyembroidery's stitch
space is 0.1 mm units with y pointing DOWN — the same direction stage 4 chose.
So the conversion is a scale and nothing else: no flip, no transpose. That was
established by reading a professionally digitized third-party file
(`beckers logo hat.DST`) and rendering it y-down, which produced upright,
correctly proportioned artwork; rendering it any other way did not. Do not
"fix" this without repeating that test.

Note for whoever wires up build step 10: the browser engine's own DST codec in
`src/dst.js` does NOT agree with this convention — see the step-3 findings note
in the repo README. Round-trip through pyembroidery, not through assumptions.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

import pyembroidery

from .stitches import StitchPlan

# Plan units are mm; DST and pyembroidery both count in 0.1 mm.
_UNITS_PER_MM = 10.0
# Two positions closer than this are the same needle position, and emitting a
# stitch between them would be a zero-length record the machine skips anyway.
_SAME_POINT_MM = 0.01


def _to_units(pt: tuple[float, float]) -> tuple[int, int]:
    return int(round(pt[0] * _UNITS_PER_MM)), int(round(pt[1] * _UNITS_PER_MM))


def plan_to_pattern(plan: StitchPlan) -> pyembroidery.EmbPattern:
    """StitchPlan -> EmbPattern, preserving jumps, trims and color changes."""
    pattern = pyembroidery.EmbPattern()
    last: tuple[float, float] | None = None

    for bi, block in enumerate(plan.blocks):
        thread = pyembroidery.EmbThread()
        thread.set_color(*block.rgb)
        thread.description = block.thread_number
        pattern.add_thread(thread)
        if bi > 0:
            pattern.color_change()

        for run in block.runs:
            if not run.points:
                continue
            if run.trim:
                pattern.trim()
            if run.jump and last is not None:
                x, y = _to_units(run.points[0])
                pattern.add_stitch_absolute(pyembroidery.JUMP, x, y)
            for pt in run.points:
                if last is not None and math.dist(last, pt) < _SAME_POINT_MM:
                    continue
                x, y = _to_units(pt)
                pattern.add_stitch_absolute(pyembroidery.STITCH, x, y)
                last = pt
            last = run.points[-1]

    pattern.end()
    return pattern


def export_dst(plan: StitchPlan, label: str = "EMBBOT") -> bytes:
    """-> DST file bytes."""
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", label[:16])
    buf = io.BytesIO()
    pyembroidery.write_dst(pattern, buf)
    return buf.getvalue()


def write_dst(plan: StitchPlan, path: str | Path, label: str = "EMBBOT") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(export_dst(plan, label))
    return path


def read_dst_points(data: bytes) -> list[tuple[float, float]]:
    """Decode DST bytes back to needle penetrations in mm, y-down.

    Used by the round-trip test. Reading back with the same library that wrote
    the file only proves self-consistency, which is why the test also renders a
    third-party file through this path.
    """
    buf = io.BytesIO(data)
    pattern = pyembroidery.read_dst(buf)
    return [
        (s[0] / _UNITS_PER_MM, s[1] / _UNITS_PER_MM)
        for s in pattern.stitches
        if s[2] == pyembroidery.STITCH
    ]
