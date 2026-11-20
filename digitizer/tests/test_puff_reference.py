"""tools.puff_reference measures a professionally digitized puff file (synthetic here)."""
from pathlib import Path

import pystitch

from tools.puff_reference import measure_puff_reference


def _synthetic(path: Path) -> None:
    pat = pystitch.EmbPattern()
    # block 1: 10 tack-down stitches, a run along x (3 mm apart is not satin-wide)
    for i in range(10):
        pat.add_stitch_absolute(pystitch.STITCH, i * 5.0, 0.0)
    pat.add_command(pystitch.COLOR_CHANGE)
    # block 2: 40 satin stitches, 6 mm wide columns advancing 0.18 mm per row
    for i in range(40):
        x = 0.0 if i % 2 == 0 else 60.0
        pat.add_stitch_absolute(pystitch.STITCH, x, 100.0 + i * 1.8)
    pat.add_command(pystitch.END)
    pystitch.write_dst(pat, str(path))


def test_measure_puff_reference_shapes(tmp_path):
    p = tmp_path / "synthetic.dst"
    _synthetic(p)
    r = measure_puff_reference(p)
    assert len(r["blocks"]) == 2
    assert r["blocks"][0]["stitches"] == 10 and r["blocks"][1]["stitches"] == 40
    assert abs(r["satin_spacing_mm"] - 0.18) < 0.02
    assert r["underlay"] is False
    lo, hi = r["column_width_mm"]
    assert 5.5 < lo <= hi < 6.5
