"""`/export` re-reads every file it writes and refuses to hand out one that
disagrees with the design (Kent, 2026-11-05: a file that fails its own
read-back is broken, not low quality, so the download is blocked).

Three layers, each pinned here:

* the verifier (`digitizer_service.readback`): every check fails on bytes that
  break it, and passes on what the real writers produce, for all 8 machine
  formats, with the DST jumps-per-trim setting the writer used;
* the route: a clean file adds `X-Export-Verified` headers and changes no byte;
  a file that fails answers **500** with a JSON body naming the check and both
  values, and no file;
* the status choice: 500, not 422 or 400. The service reports a caller's bad
  input as 400 (`could not write`, `unsupported format`) and a defect of its own
  as 500 (the unhandled-exception handler). A mismatch here is the second kind.
"""
from __future__ import annotations

import io
import json
import random

import pystitch
import pytest

from digitizer_core.adapter import design_to_pattern
from digitizer_service import formats, readback

pytest.importorskip("fastapi", reason="service extra not installed")

MACHINE = ["dst", "pes", "jef", "exp", "pec", "vp3", "xxx", "u01"]
COLORS = [{"r": 200, "g": 30, "b": 30}, {"r": 20, "g": 60, "b": 200}, {"r": 30, "g": 150, "b": 70}]


def st(x, y, kind="stitch"):
    return {"x": x, "y": y, "type": kind}


def sample_design():
    """Three colour blocks, a trim between parts, a far jump, and one chained
    move (370 units) that must split into four sewn records."""
    return {
        "stitches": [
            st(0, 0, "jump"), st(0, 0), st(30, 0), st(30, 40), st(400, 40),
            st(400, 40, "trim"), st(500, 100, "jump"), st(500, 100), st(520, 110),
            st(520, 110, "trim"), st(520, 110, "color"), st(540, 130), st(560, 130),
            st(560, 130, "trim"), st(560, 130, "color"), st(300, -50), st(310, -50),
            st(0, 0, "end"),
        ],
        "colors": COLORS,
    }


def write_and_verify(design, fmt, trim_jumps=None):
    pattern = design_to_pattern(design, label="T")
    expected = readback.expect(pattern, fmt, trim_jumps)
    data = formats.write(pattern, fmt, trim_jumps=trim_jumps)
    return data, readback.verify(expected, data, fmt, trim_jumps)


def failed_checks(result):
    return {f["check"] for f in result["failed"]}


# ---- the verifier passes what the writers produce ---------------------------

@pytest.mark.parametrize("fmt", MACHINE)
def test_every_machine_format_reads_back_clean(fmt):
    data, r = write_and_verify(sample_design(), fmt)
    assert r["verified"] and r["ok"], r["failed"]
    assert r["stitches"] >= 13  # 10 design stitches + 3 split intermediates
    assert r["colors"] == 2
    assert r["longest_mm"] <= 12.1 or fmt == "vp3"


@pytest.mark.parametrize("n", [1, 2, 3, 5, 10])
def test_dst_reads_back_at_the_jumps_per_trim_the_writer_used(n):
    _, r = write_and_verify(sample_design(), "dst", trim_jumps=n)
    assert r["ok"], r["failed"]
    # Three trims; the first is followed by the far jump, which joins its run. At
    # 1 every jump record is a trim, so the jumps count as well.
    assert r["trims"] == 3 or n == 1


def test_svg_is_labelled_unverified_with_a_reason():
    pattern = design_to_pattern(sample_design(), label="T")
    r = readback.verify(readback.expect(pattern, "svg"), formats.write(pattern, "svg"), "svg")
    assert r["verified"] is False and r["ok"] is True
    assert "not a stitch file" in r["reason"]


def _realistic(rng):
    st_ = [st(0, 0, "jump")]
    x = y = 0
    for blk in range(rng.randint(1, 4)):
        if blk:
            if rng.random() < 0.8:
                st_.append(st(x, y, "trim"))
            st_.append(st(x, y, "color"))
        if rng.random() < 0.7:
            x += rng.randint(-400, 400)
            y += rng.randint(-400, 400)
            st_.append(st(x, y, rng.choice(["jump", "trim"])))
        for _ in range(rng.randint(1, 25)):
            sc = 700 if rng.random() < 0.08 else 40
            x += round((rng.random() - 0.5) * sc)
            y += round((rng.random() - 0.5) * sc)
            st_.append(st(x, y))
    st_.append(st(0, 0, "end"))
    return {"stitches": st_, "colors": COLORS + [{"r": 5, "g": 5, "b": 5}]}


@pytest.mark.parametrize("fmt", MACHINE)
def test_random_designs_never_false_alarm(fmt):
    """The verifier must not refuse a good file: a false alarm blocks a real
    customer's download. 40 random multi-block designs per format, the DST ones
    at every jumps-per-trim."""
    rng = random.Random(2026_11_05)
    for _ in range(40):
        design = _realistic(rng)
        for n in ([None, 1, 2, 3, 5, 10] if fmt == "dst" else [None]):
            _, r = write_and_verify(design, fmt, n)
            assert r["ok"], (fmt, n, r["failed"])


# ---- every check fails on bytes that break it --------------------------------

def _bytes_of(design, fmt):
    return formats.write(design_to_pattern(design, label="T"), fmt)


def _expect(design, fmt):
    return readback.expect(design_to_pattern(design, label="T"), fmt)


def test_a_missing_stitch_fails_stitch_count():
    full = sample_design()
    short = sample_design()
    del short["stitches"][3]  # drops (30, 40)
    r = readback.verify(_expect(full, "dst"), _bytes_of(short, "dst"), "dst")
    assert "stitch_count" in failed_checks(r)
    f = next(f for f in r["failed"] if f["check"] == "stitch_count")
    assert f["expected"] == 13 and f["read"] == 12


def test_a_lost_trim_fails_trim_count_and_a_lost_colour_fails_color_count():
    base = sample_design()
    no_trim = sample_design()
    no_trim["stitches"] = [s for s in no_trim["stitches"] if s["type"] != "trim"]
    r = readback.verify(_expect(base, "exp"), _bytes_of(no_trim, "exp"), "exp")
    assert "trim_count" in failed_checks(r)
    no_color = sample_design()
    no_color["stitches"] = [s for s in no_color["stitches"] if s["type"] != "color"]
    r = readback.verify(_expect(base, "pes"), _bytes_of(no_color, "pes"), "pes")
    assert "color_count" in failed_checks(r)


def test_a_colour_change_in_the_wrong_place_fails_color_order():
    base = sample_design()
    moved = sample_design()
    # the first colour change one stitch later
    i = next(k for k, s in enumerate(moved["stitches"]) if s["type"] == "color")
    moved["stitches"][i], moved["stitches"][i + 1] = moved["stitches"][i + 1], moved["stitches"][i]
    r = readback.verify(_expect(base, "dst"), _bytes_of(moved, "dst"), "dst")
    assert "color_order" in failed_checks(r)


def test_a_trim_in_the_wrong_place_fails_trim_order():
    base = sample_design()
    moved = sample_design()
    s = moved["stitches"]
    i = next(k for k, v in enumerate(s) if v["type"] == "trim")
    s[i], s[i + 3] = s[i + 3], s[i]  # trim now follows later stitches
    r = readback.verify(_expect(base, "exp"), _bytes_of(moved, "exp"), "exp")
    assert failed_checks(r) & {"trim_order", "trim_count", "bounding_box", "stitch_count"}


def test_a_sewn_move_over_12_1_mm_fails_longest_stitch():
    """pystitch's own PES writer leaves an over-length chained move as ONE long
    stitch (formats.py `split_sewn_moves`); reading those bytes against the
    split design is exactly the break the check exists for."""
    design = sample_design()
    pattern = design_to_pattern(design, label="T")
    expected = readback.expect(pattern, "pes")
    buf = io.BytesIO()
    pystitch.write_pes(design_to_pattern(design, label="T"), buf)
    r = readback.verify(expected, buf.getvalue(), "pes")
    assert "longest_stitch" in failed_checks(r)
    f = next(f for f in r["failed"] if f["check"] == "longest_stitch")
    assert f["read"] == "37.0 mm"


def test_a_shifted_design_fails_bounding_box():
    base = sample_design()
    moved = sample_design()
    moved["stitches"][12]["x"] += 60  # the stitch at x = 560, the design's right edge
    r = readback.verify(_expect(base, "dst"), _bytes_of(moved, "dst"), "dst")
    assert "bounding_box" in failed_checks(r)


def test_a_wrong_dst_header_fails_header_bbox():
    design = sample_design()
    data = bytearray(_bytes_of(design, "dst"))
    at = data.index(b"+X:") + 3
    data[at:at + 5] = b"00001"
    r = readback.verify(_expect(design, "dst"), bytes(data), "dst")
    assert failed_checks(r) == {"header_bbox"}
    f = r["failed"][0]
    assert f["read"][0] == 1 and f["expected"][0] != 1


def test_bytes_the_reader_cannot_open_fail_readable_not_raise():
    design = sample_design()
    for fmt in ("dst", "pes", "jef", "exp"):
        r = readback.verify(_expect(design, fmt), b"\x00\x01garbage" * 10, fmt)
        assert not r["ok"], fmt  # a tolerant reader (DST) reads nonsense, which fails the counts
    for fmt in ("pes", "jef"):
        r = readback.verify(_expect(design, fmt), b"\x00\x01garbage" * 10, fmt)
        assert failed_checks(r) == {"readable"}, fmt


def test_detail_names_the_first_check_and_both_values():
    full = sample_design()
    short = sample_design()
    del short["stitches"][3]
    r = readback.verify(_expect(full, "dst"), _bytes_of(short, "dst"), "dst")
    detail = readback.failure_detail(r)
    assert detail.startswith("Export failed: stitch count (expected 13, read back 12)")


# ---- what pystitch's reader cannot give back is labelled, not hidden ---------

def test_formats_with_a_reader_limit_say_so():
    _, vp3 = write_and_verify(sample_design(), "vp3")
    assert [s["check"] for s in vp3["skipped"]] == ["longest_stitch"]
    _, xxx = write_and_verify(sample_design(), "xxx")
    assert {s["check"] for s in xxx["skipped"]} == {"trim_order", "color_order", "bounding_box", "stitch_positions"}
    _, jef = write_and_verify(sample_design(), "jef")
    trims = next(c for c in jef["checks"] if c["check"] == "trim_count")
    assert trims["mode"] == "at_least"
    for fmt in ("dst", "pes", "exp", "pec", "u01"):
        assert write_and_verify(sample_design(), fmt)[1]["skipped"] == []


# ---- the route ----------------------------------------------------------------

def _post(client, fmt, **extra):
    return client.post("/export", json={"design": sample_design(), "format": fmt, "label": "t", **extra})


@pytest.mark.parametrize("fmt", MACHINE)
def test_a_good_export_reports_it_was_verified_and_the_bytes_are_unchanged(client, fmt):
    r = _post(client, fmt)
    assert r.status_code == 200
    assert r.headers["X-Export-Verified"] == "true"
    counts = json.loads(r.headers["X-Export-Readback"])
    assert counts["stitches"] >= 13 and counts["colors"] == 2
    # verifying never alters what is written
    assert r.content == formats.write(design_to_pattern(sample_design(), label="t"), fmt)


def test_svg_export_says_it_is_unverified_and_still_returns_the_file(client):
    r = _post(client, "svg")
    assert r.status_code == 200
    assert r.headers["X-Export-Verified"] == "false"
    assert "not a stitch file" in r.headers["X-Export-Verify-Reason"]
    assert r.content


def test_dst_jumps_per_trim_is_read_back_at_the_same_n(client):
    for n in (1, 2, 5):
        r = _post(client, "dst", trim_jumps=n)
        assert r.status_code == 200, (n, r.text)
        assert r.headers["X-Export-Verified"] == "true"


def test_a_file_that_fails_its_read_back_is_a_500_with_the_check_named(client, monkeypatch):
    """The writer is made to drop the second stitch: the route must answer 500,
    name `stitch_count` with both numbers, and return no file."""
    real = formats.write

    def lossy(pattern, fmt, trim_jumps=None):
        lossy_pattern = design_to_pattern(
            {"stitches": [s for i, s in enumerate(sample_design()["stitches"]) if i != 3],
             "colors": COLORS}, label="t")
        return real(lossy_pattern, fmt, trim_jumps=trim_jumps)

    monkeypatch.setattr(formats, "write", lossy)
    r = _post(client, "dst")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["detail"].startswith("Export failed: stitch count (expected 13, read back 12)")
    assert body["readback"]["verified"] is False and body["readback"]["format"] == "dst"
    failed = {f["check"]: f for f in body["readback"]["failed"]}
    assert failed["stitch_count"]["expected"] == 13 and failed["stitch_count"]["read"] == 12
    assert "Content-Disposition" not in r.headers


def test_the_failure_body_keeps_the_detail_key_every_other_error_uses(client, monkeypatch):
    monkeypatch.setattr(formats, "write", lambda pattern, fmt, trim_jumps=None: b"\x00" * 600)
    r = _post(client, "dst")
    assert r.status_code == 500
    assert isinstance(r.json()["detail"], str) and r.json()["detail"].startswith("Export failed:")


def test_a_stitch_that_moved_inside_the_design_fails_stitch_positions():
    """Counts and the box both pass when one interior stitch lands elsewhere;
    only the positions check sees it."""
    base = sample_design()
    moved = sample_design()
    moved["stitches"][8]["x"] += 3  # (520, 110) -> (523, 110), well inside the design
    r = readback.verify(_expect(base, "dst"), _bytes_of(moved, "dst"), "dst")
    assert failed_checks(r) == {"stitch_positions"}
    f = r["failed"][0]
    assert f["expected"].startswith("10 stitches") and f["read"] == "5 found in order"  # the matching stops at the first stitch that is not there
