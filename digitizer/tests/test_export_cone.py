"""A service PES/PEC/JEF names each colour's CIEDE2000-nearest chart cone.

PES, PEC and JEF do not carry a colour; they carry an index into a fixed
manufacturer chart (64 Brother cones, 78 Janome), and the machine asks the
operator for that cone. pystitch picks the index with its own metric, which
sent the Studio's default near-black (20,20,20) to a dark brown — while the
browser's `src/pes.js` (CIEDE2000 since 2026-10-08) picks Black from the same
chart (tools/export-audit.mjs). Kent ruled the same day that the service
snap with CIEDE2000 too, the metric `digitizer_core/threads.py` and
`app/src/lib/colorMatch.js` already use.
"""
from __future__ import annotations

import numpy as np
import pystitch
import pytest
from pystitch import EmbThreadJef, EmbThreadPec
from skimage.color import deltaE_ciede2000

from digitizer_core.adapter import design_to_pattern
from digitizer_core.threads import rgb_to_lab
from digitizer_service import formats

CHARTS = {"pes": EmbThreadPec, "pec": EmbThreadPec, "jef": EmbThreadJef}

# The default lettering colour, then a spread a digitized logo carries.
COLOURS = [(20, 20, 20), (30, 60, 200), (200, 30, 30), (214, 214, 216), (240, 200, 40)]


def _nearest_hex(chart_mod, rgb):
    chart = [t for t in chart_mod.get_thread_set() if t is not None]
    lab = rgb_to_lab(np.array([[c.get_red(), c.get_green(), c.get_blue()] for c in chart]))
    d = deltaE_ciede2000(rgb_to_lab(np.array([rgb])), lab)
    return chart[int(np.argmin(d))].hex_color().lower()


def _design():
    st, x = [], 0
    for i, _ in enumerate(COLOURS):
        if i:
            st.append({"x": x, "y": 0, "type": "color"})
        for _ in range(3):
            st.append({"x": x, "y": 0, "type": "stitch"})
            x += 20
    st.append({"x": 0, "y": 0, "type": "end"})
    return {"stitches": st, "colors": [{"r": r, "g": g, "b": b} for r, g, b in COLOURS]}


@pytest.mark.parametrize("fmt", ["pes", "pec", "jef"])
def test_each_block_names_its_ciede2000_nearest_cone(fmt, tmp_path):
    path = tmp_path / f"out.{fmt}"
    path.write_bytes(formats.write(design_to_pattern(_design()), fmt))
    got = [t.hex_color().lower() for t in pystitch.read(str(path)).threadlist]
    want = [_nearest_hex(CHARTS[fmt], c) for c in COLOURS]
    assert got == want


def test_near_black_is_black(tmp_path):
    path = tmp_path / "out.pes"
    path.write_bytes(formats.write(design_to_pattern(_design()), "pes"))
    assert pystitch.read(str(path)).threadlist[0].hex_color().lower() == "#000000"
