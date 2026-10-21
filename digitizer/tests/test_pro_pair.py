"""`tools/pro_pair.py`: ours beside the pro's file, one instrument for every
session. The end-to-end test runs ONE digitize of a committed pair (Becker's
marine logo against the pro's left-chest DST, no client file outside the
repo) at the pro's own width, read off the DST's extents."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pystitch
import pytest
from shapely.geometry import box

from tools import pro_pair

DIGITIZER = Path(__file__).resolve().parent.parent
ART = DIGITIZER / "testdata" / "becker_marine_logo.png"
PRO = DIGITIZER / "testdata" / "reference" / "becker_hat_polo_large_beckers_logolc.dst"


def _reg(sid, x0, y0, x1, y1):
    return SimpleNamespace(shape_id=sid, polygon=box(x0, y0, x1, y1))


def test_band_selects_regions_lying_in_the_band():
    # region extent y 0..100; band 0.8..1.0 is top >= 80 and bottom <= 100
    regs = [_reg("top", 0, 0, 10, 20), _reg("mid", 0, 40, 10, 60),
            _reg("low", 0, 82, 10, 100), _reg("straddle", 20, 70, 30, 90)]
    got = [r.shape_id for r in pro_pair.select_regions(regs, band=(0.8, 1.0))]
    assert got == ["low"]
    got = [r.shape_id for r in pro_pair.select_regions(regs, band=(0.3, 0.7))]
    assert got == ["mid"]
    # no window: everything
    assert len(pro_pair.select_regions(regs)) == 4


def test_crop_selects_regions_whose_box_meets_the_window():
    regs = [_reg("a", 0, 0, 10, 10), _reg("b", 20, 20, 30, 30), _reg("c", 9, 9, 12, 12)]
    got = [r.shape_id for r in pro_pair.select_regions(regs, crop=(8, 8, 15, 15))]
    assert got == ["a", "c"]
    with pytest.raises(ValueError):
        pro_pair.select_regions(regs, band=(0.1, 0.2), crop=(0, 0, 1, 1))


def test_pro_counts_read_with_pystitch():
    got = pro_pair.pro_counts(PRO)
    pat = pystitch.read(str(PRO))
    m = pystitch.COMMAND_MASK
    assert got["stitches"] == sum(1 for *_, c in pat.stitches if c & m == pystitch.STITCH)
    assert got["trims"] == sum(1 for *_, c in pat.stitches if c & m == pystitch.TRIM)
    assert got["colour_changes"] == sum(1 for *_, c in pat.stitches if c & m == pystitch.COLOR_CHANGE)
    assert got["width_mm"] == pytest.approx(95.7, abs=0.05)


@pytest.fixture(scope="module")
def becker(tmp_path_factory):
    """ONE digitize, two output passes: the band sheet and the crop+shapes
    sheet, so the suite pays for a single pipeline run."""
    w = pro_pair.pro_counts(PRO)["width_mm"]
    base = ["--art", str(ART), "--pro", str(PRO), "--width", str(w), "--garment", "left_chest"]
    band_out = tmp_path_factory.mktemp("pro_pair_band")
    args = pro_pair.parse_args(base + ["--out", str(band_out), "--band", "0.5", "1.0"])
    dig = pro_pair.digitize(args.art, args.width, args.garment)
    assert pro_pair.run(args, dig) == 0
    rows = [json.loads(line) for line in
            (band_out / "band_meta.jsonl").read_text(encoding="utf-8").splitlines() if line]
    crop_out = tmp_path_factory.mktemp("pro_pair_crop")
    sid = rows[0]["id"]
    args2 = pro_pair.parse_args(base + ["--out", str(crop_out), "--crop", "0", "0", "40", "30",
                                        "--shapes", sid])
    assert pro_pair.run(args2, dig) == 0
    return band_out, crop_out, sid


@pytest.fixture(scope="module")
def becker_out(becker):
    return becker[0]


def test_end_to_end_writes_the_sheets_and_stats(becker_out):
    for name in ("sheet_whole.png", "sheet_band.png", "stats.json", "band_meta.jsonl"):
        assert (becker_out / name).stat().st_size > 0, name
    st = json.loads((becker_out / "stats.json").read_text(encoding="utf-8"))
    for k in ("width_mm", "garment_id", "stitches", "trims", "colours", "regions",
              "warnings", "preflight", "pro"):
        assert k in st, k
    assert st["garment_id"] == "left_chest"
    assert st["stitches"] > 0 and st["regions"] > 0
    assert "grade" in st["preflight"] and "findings" in st["preflight"]
    # the pro side is pystitch's own count; this DST carries no thread
    # colours, so the render took the greys fallback and still made a sheet
    assert st["pro"] == pro_pair.pro_counts(PRO)


def test_band_meta_rows_carry_the_fields(becker_out):
    rows = [json.loads(line) for line in
            (becker_out / "band_meta.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert rows
    for r in rows:
        for k in ("id", "thread", "bbox", "area", "holes", "bean_spines", "meta", "runs"):
            assert k in r, k


def test_crop_and_shapes_write_spines_and_runs(becker):
    _band, out, sid = becker
    assert (out / "sheet_crop.png").stat().st_size > 0
    assert (out / f"spines_{sid}.png").stat().st_size > 0
    txt = (out / f"runs_{sid}.txt").read_text(encoding="utf-8")
    assert sid in txt and "role=" in txt


def test_studio_request_keeps_the_studio_shape():
    from tools.fremont_triage import studio_request
    req = pro_pair.request(85.9, "left_chest")
    want = studio_request(85.9)
    want["garment_id"] = "left_chest"
    assert req == want
    assert pro_pair.request(85.9) == studio_request(85.9)
