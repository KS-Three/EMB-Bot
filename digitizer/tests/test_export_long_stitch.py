"""A sewn stitch longer than one record leaves the service as STITCHES.

The browser encoders settled this in September: `dst.js` and `exp.js` split
an over-length SEWN move into stitches (2026-09-07), and `pes.js` joined them
at a 121-unit bar on Kent's ruling of 2026-09-12 (DOCTRINE, "One design,
three encoders, three different sew-outs"). The service's `/export` never
got the same rule. It hands the pattern to pystitch, whose encoder answers
"this stitch is too long" two other ways:

  - DST, EXP, JEF, XXX, U01 (`max_stitch` 121-127): the default
    `CONTINGENCY_LONG_STITCH_JUMP_NEEDLE` — jumps up to the far end, needle
    down there. The thread the design said to SEW becomes travel: exactly
    the 2026-09-07 defect, on the other route.
  - PES, PEC (`max_stitch` 2047): nothing at all, so a 30 mm move goes out as
    one 30 mm stitch — exactly what the 2026-09-12 ruling outlawed.

Found by `tools/export-audit.mjs` (2026-10-08), whose renders show it: a
hand-drawn satin L, read back from the service DST, has lost its long
cross-stitches. The service route is the one purely-digitized designs take
(DownloadStep's `isPurelyDigitized`), and a digitized logo enlarged on the
field is the case that crosses one record.

The chain rule is the browser's too: a move splits into stitches only when it
CONTINUES a sewn run. A stitch after the start of the file, a jump, a cut or a
colour change is travel-in, and stays pystitch's jump-then-needle.
"""
from __future__ import annotations

import io

import pystitch
import pytest

from digitizer_core.adapter import design_to_pattern
from digitizer_service import formats

BAR = 121  # units; the repo's one-record bar (src/dst.js MAX_DELTA)

# VP3 has no jump record at all — a move IS a stitch there — so it is in the
# sewn-thread case (its long-stitch form starts at 128) and not the travel one.
MACHINE = ["dst", "pes", "exp", "jef", "xxx", "vp3", "pec", "u01"]


def _design(points, travel_in=None):
    st = []
    if travel_in is not None:
        st.append({"x": travel_in[0], "y": travel_in[1], "type": "jump"})
    st += [{"x": x, "y": y, "type": "stitch"} for x, y in points]
    st.append({"x": 0, "y": 0, "type": "end"})
    return {"stitches": st, "colors": [{"r": 200, "g": 30, "b": 30}]}


def _read(design, fmt, tmp_path):
    path = tmp_path / f"out.{fmt}"
    path.write_bytes(formats.write(design_to_pattern(design), fmt))
    return pystitch.read(str(path)).stitches


def _sewn(records):
    """(thread length, longest per-axis sewn delta) over STITCH-to-STITCH pairs."""
    total, worst, prev = 0.0, 0, None
    for x, y, cmd in records:
        if cmd & pystitch.COMMAND_MASK != pystitch.STITCH:
            prev = None
            continue
        if prev is not None:
            dx, dy = x - prev[0], y - prev[1]
            total += (dx * dx + dy * dy) ** 0.5
            worst = max(worst, abs(dx), abs(dy))
        prev = (x, y)
    return total, worst


@pytest.mark.parametrize("fmt", MACHINE)
def test_long_sewn_move_is_sewn_and_split_at_the_bar(fmt, tmp_path):
    # 300 units along x, then a 300 x 200 diagonal, both CONTINUING a run.
    design = _design([(0, 0), (60, 0), (360, 0), (660, 200), (660, 240)])
    total, worst = _sewn(_read(design, fmt, tmp_path))
    want = 60 + 300 + (300 ** 2 + 200 ** 2) ** 0.5 + 40
    assert abs(total - want) < 2, f"{fmt}: sewn thread {total:.1f} vs {want:.1f} — a sewn move left as travel"
    assert worst <= BAR, f"{fmt}: a {worst}-unit sewn record, over the {BAR}-unit bar"


@pytest.mark.parametrize("fmt", [f for f in MACHINE if f != "vp3"])
def test_travel_in_is_not_sewn(fmt, tmp_path):
    # The first stitch of a run 50 mm from where the needle stands: travel.
    design = _design([(500, 300), (530, 300), (530, 330)], travel_in=(500, 300))
    total, _ = _sewn(_read(design, fmt, tmp_path))
    assert abs(total - 60) < 2, f"{fmt}: sewn thread {total:.1f}, expected only the design's own 60"


# Not PES/PEC/JEF: since 2026-10-08 their stitch stream (PES/PEC,
# test_export_cuts.py) or their cone index (all three, test_export_cone.py)
# is ours, so pystitch's writer is no longer the byte reference for them.
@pytest.mark.parametrize("fmt", [f for f in MACHINE if f not in ("pes", "pec", "jef")])
def test_a_design_with_nothing_over_the_bar_is_byte_identical(fmt):
    # Against pystitch's own writer, untouched: the split adds records only
    # where a sewn move is over the bar, and this design has none.
    design = _design([(0, 0), (100, 0), (100, 121), (-21, 121)], travel_in=(0, 0))
    out = io.BytesIO()
    formats._WRITERS[fmt](design_to_pattern(design), out, formats._WRITER_SETTINGS.get(fmt))
    assert formats.write(design_to_pattern(design), fmt) == out.getvalue()
