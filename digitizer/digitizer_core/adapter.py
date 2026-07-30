"""The browser adapter: `StitchPlan` <-> EMB-Bot `Design`.

**This module owns the y-axis flip, and it is the only place one happens.**

Two coordinate conventions meet here:

  * A `StitchPlan` is **millimetre floats, origin at the artwork bbox center,
    y-axis DOWN** (stage 4's choice, documented in `stitches.py`).
  * An EMB-Bot `Design` is **integer 0.1 mm units, origin at design center,
    y-axis UP** — see `T()` in `src/digitize.js`, which computes `cy - q.y`
    precisely to invert image-space y.

So the conversion is `y_design = -y_plan * 10`, and nothing else.

**Why a Design and not a DST file.** The obvious wiring — service writes a DST,
browser reads it with `decodeDST` — is broken in this project. `src/dst.js`
puts x in the high nibble of a DST record where pyembroidery and the published
Tajima table put y, so a file written by one and read by the other comes back
transposed. That disagreement is real, measured, and deliberately unresolved
(it needs a sew-out on Kent's machine to settle; see the repo README and the
step-8 plan). Handing the browser a `Design` sidesteps it completely: no DST
crosses this boundary, Studio treats a digitized result exactly like a
lettering or imported design, and if it wants a baked DST for offline
persistence it writes one with its own encoder, which round-trips with its own
decoder.

**Origin is NOT recentered.** The design keeps the plan's origin — the artwork
bbox center — so the `Design` and the review screen's region polygons share one
coordinate system and overlay exactly. Pull compensation can leave the stitch
bbox up to a few tenths of a millimetre off-center from the artwork bbox as a
result; `widthMM`/`heightMM` report the true stitch extents regardless, so hoop
clamping stays honest.
"""
from __future__ import annotations

import math

import pyembroidery

from .stitches import StitchPlan

UNITS_PER_MM = 10.0

# Record types in the Design contract, matching src/digitize.js exactly.
STITCH = "stitch"
JUMP = "jump"
TRIM = "trim"
COLOR = "color"
END = "end"


def _u(x_mm: float, y_mm: float) -> tuple[int, int]:
    """mm y-down -> integer 0.1 mm units y-up. The one flip."""
    return int(round(x_mm * UNITS_PER_MM)), int(round(-y_mm * UNITS_PER_MM))


def plan_to_design(plan: StitchPlan, name: str = "Digitized design") -> dict:
    """`StitchPlan` -> the EMB-Bot `Design` dict.

    Record order mirrors `buildQualityDesign`'s: a run that the machine has to
    travel to emits a `jump` at its first point and then a `stitch` at that same
    point; a run that is cut away from emits a zero-travel `trim` at the
    PREVIOUS position first; a color change is a trim then a `color`, both at
    the last sewn position.
    """
    stitches: list[dict] = []
    colors: list[dict] = []
    last: tuple[int, int] | None = None

    for bi, block in enumerate(plan.blocks):
        r, g, b = block.rgb
        colors.append(
            {
                "r": int(r),
                "g": int(g),
                "b": int(b),
                "name": f"{block.thread_number} {_thread_name(plan, bi)}".strip(),
            }
        )

        if bi > 0 and last is not None:
            # The thread is always cut coming out of a color, and the change
            # itself is marked at the same standing position.
            stitches.append({"x": last[0], "y": last[1], "type": TRIM})
            stitches.append({"x": last[0], "y": last[1], "type": COLOR})

        # A color change already cut the thread; the first run of the block must
        # not emit its own trim on top of it (that is two cuts in one place).
        just_changed = bi > 0

        for run in block.runs:
            if not run.points:
                continue
            first = _u(*run.points[0])

            if run.trim and last is not None and not just_changed:
                stitches.append({"x": last[0], "y": last[1], "type": TRIM})
            just_changed = False

            # The needle has to get there. `last is None` is the file's very
            # first run, where the machine stands at the origin — JS's pushRun
            # emits that jump unconditionally and so do we, rather than leaving
            # the encoder to synthesize one out of an oversized first delta.
            if (run.jump or run.trim or last is None) and first != last:
                stitches.append({"x": first[0], "y": first[1], "type": JUMP})

            for pt in run.points:
                x, y = _u(*pt)
                stitches.append({"x": x, "y": y, "type": STITCH})
                last = (x, y)

    stitches.append({"x": 0, "y": 0, "type": END})

    # Size is measured from the records actually emitted, not from the plan it
    # came from: Studio clamps to the hoop and labels the size panel with these
    # numbers, and they should describe the design in hand rather than its
    # pre-quantization ancestor.
    design = {
        "stitches": stitches,
        "colors": colors,
        "stitchCount": sum(1 for s in stitches if s["type"] == STITCH),
        "colorCount": len(colors),
        "name": name,
    }
    w_mm, h_mm = design_size_mm(design)
    design["widthMM"] = round(w_mm, 3)
    design["heightMM"] = round(h_mm, 3)
    return design


def _thread_name(plan: StitchPlan, block_index: int) -> str:
    """The catalog name for a block, when the palette carries one."""
    if block_index < len(plan.palette):
        return str(plan.palette[block_index].get("name", ""))
    return ""


def design_bbox_units(design: dict) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) over sewn penetrations only, in design units.

    Jump/trim/color records are excluded: they mark where the needle travels,
    not where thread lands, and including them would report a design larger
    than it sews.
    """
    pts = [(s["x"], s["y"]) for s in design.get("stitches", []) if s.get("type") == STITCH]
    if not pts:
        return (0, 0, 0, 0)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def design_to_points_mm(design: dict) -> list[tuple[float, float]]:
    """Sewn penetrations back in plan space (mm, y-DOWN). Inverse of `_u`.

    The round-trip golden's other half.
    """
    return [
        (s["x"] / UNITS_PER_MM, -s["y"] / UNITS_PER_MM)
        for s in design.get("stitches", [])
        if s.get("type") == STITCH
    ]


def design_to_pattern(design: dict, label: str = "EMBBOT") -> pyembroidery.EmbPattern:
    """EMB-Bot `Design` -> pyembroidery pattern, for the universal exporter.

    Flips back to y-DOWN, which is pyembroidery's convention (verified against a
    professionally digitized third-party file during step 3 — see `export.py`).
    Every format pyembroidery writes inherits that convention; the response says
    so, because for DST specifically the browser's own encoder disagrees and it
    is the browser's that has been sewn.
    """
    pattern = pyembroidery.EmbPattern()

    for c in design.get("colors", []) or [{"r": 0, "g": 0, "b": 0}]:
        thread = pyembroidery.EmbThread()
        thread.set_color(int(c.get("r", 0)), int(c.get("g", 0)), int(c.get("b", 0)))
        if c.get("name"):
            thread.description = str(c["name"])
        pattern.add_thread(thread)

    for s in design.get("stitches", []):
        kind = s.get("type", STITCH)
        if kind == END:
            continue
        x, y = int(s["x"]), -int(s["y"])
        if kind == STITCH:
            pattern.add_stitch_absolute(pyembroidery.STITCH, x, y)
        elif kind == JUMP:
            pattern.add_stitch_absolute(pyembroidery.JUMP, x, y)
        elif kind == TRIM:
            pattern.add_stitch_absolute(pyembroidery.TRIM, x, y)
        elif kind == COLOR:
            pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, x, y)

    pattern.metadata("name", str(label)[:16])
    pattern.end()
    return pattern


def design_size_mm(design: dict) -> tuple[float, float]:
    x0, y0, x1, y1 = design_bbox_units(design)
    return ((x1 - x0) / UNITS_PER_MM, (y1 - y0) / UNITS_PER_MM)


def plan_bbox_mm(plan: StitchPlan) -> tuple[float, float, float, float]:
    """Sewn bbox of a plan, in plan space. Mirrors `design_bbox_units`."""
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    for _, run in plan.iter_runs():
        for x, y in run.points:
            x0, y0 = min(x0, x), min(y0, y)
            x1, y1 = max(x1, x), max(y1, y)
    if not math.isfinite(x0):
        return (0.0, 0.0, 0.0, 0.0)
    return (x0, y0, x1, y1)
