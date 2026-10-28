"""tools/photo_corpus.py -- the cross-genre Commons corpus and its side-by-side
scorecard (Kent, 2026-10-27: "This digitizer needs to be building tools that
help and improve ALL photos"; spec docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md).

No network and no pipeline here: `fetch` takes an injected API callable,
`capture` runs a stub worker, `sxs` reads tiny synthetic runs. Digitizing the
real corpus is hours of work and belongs to the tool's own CLI.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tools import photo_corpus as pc


# ------------------------------------------------------------------ Task 1: the list
def test_corpus_rows_are_complete_unique_and_licence_clean():
    rows = pc.load_corpus()
    assert len(rows) >= 18
    assert len({r["slug"] for r in rows}) == len(rows)
    for r in rows:
        assert set(r) >= {"slug", "kind", "genre", "title", "page", "author", "licence"}
        assert r["kind"] in {"photo", "logo"}
        assert r["title"].startswith("File:")
        assert pc.licence_ok(r["licence"]), r["slug"]


def test_no_image_is_tracked_under_the_corpus_dir():
    out = subprocess.run(["git", "ls-files", str(pc.CORPUS_DIR)], capture_output=True, text=True,
                         cwd=pc.DIGITIZER).stdout
    names = {Path(p).name for p in out.split()}
    assert names <= {"corpus.json", "README.md"}


def test_licence_ok_is_a_lowercase_substring_match():
    assert pc.licence_ok("CC BY-SA 4.0")
    assert pc.licence_ok("Public domain")
    assert not pc.licence_ok("CC BY-NC 2.0")
    assert not pc.licence_ok("")


def test_load_corpus_rejects_duplicate_slugs(tmp_path):
    p = tmp_path / "c.json"
    row = {"slug": "a", "kind": "photo", "genre": "g", "title": "File:x.jpg", "page": "u",
           "author": "me", "licence": "cc0"}
    p.write_text(json.dumps([row, row]), encoding="utf-8")
    with pytest.raises(ValueError):
        pc.load_corpus(p)


# ------------------------------------------------------------------ Task 2: fetch
ROW = {"slug": "a", "kind": "photo", "genre": "g", "title": "File:x.jpg", "page": "u",
       "author": "Someone", "licence": "cc by-sa 4.0"}


def _fake_api(licence="CC BY-SA 4.0", mime="image/jpeg", width=2000):
    def get(params):
        return {"query": {"pages": {"1": {"title": params["titles"], "imageinfo": [{
            "url": "https://x/orig.jpg", "thumburl": "https://x/1600.jpg", "width": width,
            "height": 1000, "mime": mime, "descriptionurl": "https://commons/x",
            "extmetadata": {"LicenseShortName": {"value": licence},
                            "Artist": {"value": "<a href='u'>Someone</a>"}}}]}}}}
    return get


def test_fetch_writes_image_and_manifest_with_stripped_author(tmp_path):
    r = pc.fetch([ROW], tmp_path, get=_fake_api(), download=lambda url: b"\xff\xd8jpegbytes")
    assert r["fetched"] == ["a"]
    assert (tmp_path / "a.jpg").read_bytes().startswith(b"\xff\xd8")
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["a"]
    assert m["author"] == "Someone" and m["licence"] == "cc by-sa 4.0"
    assert m["file_url"] == "https://x/1600.jpg"
    assert m["sha256"] == hashlib.sha256(b"\xff\xd8jpegbytes").hexdigest()


def test_fetch_refuses_row_whose_live_licence_left_the_set(tmp_path):
    called = []
    r = pc.fetch([ROW], tmp_path, get=_fake_api(licence="CC BY-NC 4.0"),
                 download=lambda url: called.append(url) or b"")
    assert r["fetched"] == [] and "licence" in r["skipped"]["a"]
    assert called == [] and not (tmp_path / "a.jpg").exists()


def test_fetch_skips_a_row_already_on_disk(tmp_path):
    pc.fetch([ROW], tmp_path, get=_fake_api(), download=lambda url: b"\xff\xd8")
    r = pc.fetch([ROW], tmp_path, get=_fake_api(),
                 download=lambda url: pytest.fail("downloaded again"))
    assert r["skipped"] == {"a": "cached"}


def test_retry_recovers_from_transient_errors_then_gives_up():
    """Commons answered 503 on 17 of 18 titles on the first live fetch (2026-10-27)."""
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise OSError("503")
        return "ok"
    assert pc._retry(flaky, tries=4, sleep=lambda s: None) == "ok" and len(calls) == 3
    with pytest.raises(OSError):
        pc._retry(lambda: (_ for _ in ()).throw(OSError("503")), tries=2, sleep=lambda s: None)


def test_strip_html():
    assert pc.strip_html("<a href='u' class='x'>Wilfredor</a>") == "Wilfredor"
    assert pc.strip_html("") == "see Commons page"


# ------------------------------------------------------------------ Task 3: row numbers
FABRIC = (223, 232, 235)  # BGR of garment_rgb 235,232,223


def _output(stitches=10, colors=2, warnings=(), state="done", size=(80.0, 50.0)):
    return {"state": state,
            "stats": {"stitch_count": stitches, "trims": 1, "color_changes": colors - 1,
                      "size_mm": list(size), "thread_m_total": 1.0},
            "warnings": list(warnings),
            "preflight": {"grade": "F", "score": 0, "metrics": {"raw_score": -38}},
            "design": {"stitches": [], "colors": [{"r": 0, "g": 0, "b": 0}] * colors},
            "_meta": {"elapsed_s": 12.5, "stamps": {"plan_stitches": 9.0},
                      "class": "photo_scene", "class_conf": 0.9}}


def test_summarise_reads_counts_cap_and_route():
    warnings = [{"code": "FACE_ROUTED_FLAT"},
                {"code": "PHOTO_BACKGROUND_REMOVED", "background_frac_before": 0.1,
                 "background_frac_after": 0.6}]
    row = pc.summarise(_output(colors=7, warnings=warnings), cap=6)
    assert row["colors_used"] == 7 and row["cap_kept"] is False and row["route"] == "faces_flat"
    assert row["cutout_removed_frac"] == pytest.approx(0.5)
    assert row["score_raw"] == -38 and row["grade"] == "F"
    assert row["st_per_cm2"] == pytest.approx(10 / 40)
    assert row["class"] == "photo_scene" and row["wall_s"] == 12.5


def test_summarise_route_without_faces_follows_the_class():
    assert pc.summarise(_output(), cap=6)["route"] == "photo"
    out = _output()
    out["_meta"]["class"] = "flat"
    assert pc.summarise(out, cap=6)["route"] == "graphic"


def test_summarise_handles_an_empty_design():
    row = pc.summarise(_output(stitches=0, size=(0.0, 0.0)), cap=6)
    assert row["stitches"] == 0 and row["st_per_cm2"] is None


def test_summarise_timeout_row():
    row = pc.summarise({"state": "timeout", "_meta": {"elapsed_s": 1200.0}}, cap=6)
    assert row["state"] == "timeout" and row["stitches"] is None and row["wall_s"] == 1200.0


def test_fidelity_cc_is_one_for_a_perfect_render_and_zero_for_blank():
    rng = np.random.default_rng(0)
    photo = rng.integers(0, 255, (64, 96, 3)).astype(np.uint8)
    pad = int(pc.PAD_MM * pc.PXMM)
    frame = np.full((64 + 2 * pad, 96 + 2 * pad, 3), FABRIC, np.uint8)
    frame[pad:-pad, pad:-pad] = photo
    f = pc.fidelity(photo, frame, FABRIC)
    assert f["fidelity_cc"] == pytest.approx(1.0, abs=1e-6) and f["ssim"] == pytest.approx(1.0, abs=1e-6)
    blank = np.full_like(frame, FABRIC)
    g = pc.fidelity(photo, blank, FABRIC)
    assert g["fidelity_cc"] == pytest.approx(0.0, abs=1e-6) and g["ssim_null"] == pytest.approx(g["ssim"])
