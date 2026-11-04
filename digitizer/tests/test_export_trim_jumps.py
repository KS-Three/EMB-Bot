"""`trim_jumps`: how many consecutive jump records a written .dst uses for a trim.

The browser writer (`src/dst.js`, test/dst-jumps-per-trim.test.js) and the
service's pystitch path both take the setting: an integer 1 to 10, default 3.
Default 3 must leave every existing service file byte-identical.

pystitch's DstWriter writes `trim_at` records per TRIM but never fewer than
two, so 1 is written by `formats` as one zero-length jump instead.
"""
from __future__ import annotations

import os
import tempfile

import pystitch
import pytest

from digitizer_core.adapter import design_to_pattern
from digitizer_service import formats

pytest.importorskip("fastapi", reason="service extra not installed")

SIZES = [1, 2, 3, 5, 10]


def _design():
    st = [{"x": x, "y": y, "type": t} for x, y, t in (
        (0, 0, "stitch"), (30, 0, "stitch"), (60, 0, "stitch"),
        (60, 0, "trim"),
        (90, 0, "stitch"), (120, 0, "stitch"),
    )]
    st.append({"x": 0, "y": 0, "type": "end"})
    return {"stitches": st, "colors": [{"r": 200, "g": 30, "b": 30}]}


def _jump_run_lengths(data: bytes) -> list[int]:
    """Lengths of the runs of consecutive JUMP records in the DST body."""
    runs, cur = [], 0
    for i in range(512, len(data) - 2, 3):
        flag = data[i + 2]
        if (flag & 0xC0) == 0x80:  # jump, not colour change (0xC0) or end
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


def _trims_read_at(data: bytes, n: int) -> int:
    fd, path = tempfile.mkstemp(suffix=".dst")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        pat = pystitch.read(path, {"trim_at": n})
    finally:
        os.unlink(path)
    return sum(1 for s in pat.stitches if (s[2] & pystitch.COMMAND_MASK) == pystitch.TRIM)


@pytest.mark.parametrize("n", SIZES)
def test_writer_writes_n_jumps_per_trim(n):
    data = formats.write(design_to_pattern(_design()), "dst", trim_jumps=n)
    assert _jump_run_lengths(data) == [n]
    assert _trims_read_at(data, n) == 1


def test_default_is_three_and_byte_identical():
    pat = design_to_pattern(_design())
    plain = formats.write(pat, "dst")
    assert formats.write(pat, "dst", trim_jumps=None) == plain
    assert formats.write(pat, "dst", trim_jumps=3) == plain
    assert _jump_run_lengths(plain) == [3]


def test_other_formats_ignore_it():
    pat = design_to_pattern(_design())
    for fmt in ("pes", "exp", "jef"):
        assert formats.write(pat, fmt, trim_jumps=7) == formats.write(pat, fmt)


@pytest.mark.parametrize("bad", [0, 11, -2, 2.5, True, "3", [3]])
def test_invalid_value_is_refused(bad):
    with pytest.raises(ValueError):
        formats.write(design_to_pattern(_design()), "dst", trim_jumps=bad)


@pytest.mark.parametrize("n", SIZES)
def test_export_endpoint_honours_the_setting(client, n):
    r = client.post("/export", json={"design": _design(), "format": "dst", "trim_jumps": n})
    assert r.status_code == 200, r.text
    assert _jump_run_lengths(r.content) == [n]


def test_export_endpoint_default_matches_explicit_three(client):
    a = client.post("/export", json={"design": _design(), "format": "dst"})
    b = client.post("/export", json={"design": _design(), "format": "dst", "trim_jumps": 3})
    assert a.status_code == 200 and a.content == b.content


def test_export_endpoint_rejects_out_of_range(client):
    r = client.post("/export", json={"design": _design(), "format": "dst", "trim_jumps": 11})
    assert r.status_code == 400
