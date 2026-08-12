"""Writing a StitchPlan out as a machine file.

pystitch (MIT, pure Python — pyembroidery's actively maintained Ink/Stitch
fork, same API and conventions; swap vetted in
`docs/pystitch-evaluation-2026-08-11.md`) does the format work. Build step 8
turns this into the universal export adapter every EMB-Bot design goes
through; here it exists so a plan can be sewn and judged.

**Coordinate convention, verified rather than assumed.** pystitch's stitch
space is 0.1 mm units with y pointing DOWN — the same direction stage 4 chose.
So the conversion is a scale and nothing else: no flip, no transpose. That was
established (under pyembroidery, whose convention pystitch inherits — eval doc
§4.1) by reading a professionally digitized third-party file
(`beckers logo hat.DST`) and rendering it y-down, which produced upright,
correctly proportioned artwork; rendering it any other way did not. Do not
"fix" this without repeating that test.

Note for whoever wires up build step 10: the browser engine's own DST codec in
`src/dst.js` does NOT agree with this convention — see the step-3 findings note
in the repo README. Round-trip through pystitch, not through assumptions.
"""
from __future__ import annotations

import io
from pathlib import Path

import pystitch

from . import stitches
from .stitches import StitchPlan

# Plan units are mm; DST and pystitch both count in 0.1 mm.
_UNITS_PER_MM = 10.0


def _to_units(pt: tuple[float, float]) -> tuple[int, int]:
    return int(round(pt[0] * _UNITS_PER_MM)), int(round(pt[1] * _UNITS_PER_MM))


def plan_to_pattern(plan: StitchPlan) -> pystitch.EmbPattern:
    """StitchPlan -> EmbPattern, preserving jumps, trims and color changes.

    The trim/jump/stitch decisions — including which near-coincident
    penetrations are deduped, and where the dedupe must NOT apply (after a
    jump, a trim, or a block boundary) — live in
    `stitches.iter_machine_commands`, the same stream `StitchPlan.stats`
    counts. This function only scales mm to 0.1 mm units and encodes.
    """
    pattern = pystitch.EmbPattern()
    for block in plan.blocks:
        thread = pystitch.EmbThread()
        thread.set_color(*block.rgb)
        thread.description = block.thread_number
        pattern.add_thread(thread)

    for cmd, pt in stitches.iter_machine_commands(plan):
        if cmd == stitches.CMD_STITCH:
            x, y = _to_units(pt)
            pattern.add_stitch_absolute(pystitch.STITCH, x, y)
        elif cmd == stitches.CMD_JUMP:
            x, y = _to_units(pt)
            pattern.add_stitch_absolute(pystitch.JUMP, x, y)
        elif cmd == stitches.CMD_TRIM:
            pattern.trim()
        elif cmd == stitches.CMD_COLOR_CHANGE:
            pattern.color_change()

    pattern.end()
    return pattern


def export_dst(plan: StitchPlan, label: str = "EMBBOT") -> bytes:
    """-> DST file bytes."""
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", label[:16])
    buf = io.BytesIO()
    pystitch.write_dst(pattern, buf)
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
    pattern = pystitch.read_dst(buf)
    return [
        (s[0] / _UNITS_PER_MM, s[1] / _UNITS_PER_MM)
        for s in pattern.stitches
        if s[2] == pystitch.STITCH
    ]
