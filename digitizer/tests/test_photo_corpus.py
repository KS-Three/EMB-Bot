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
            "design": {"stitches": [], "colors": [{"r": i, "g": 0, "b": 0} for i in range(colors)]},
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


def test_summarise_counts_distinct_threads_not_colour_blocks():
    """`design.colors` is the colour-BLOCK sequence (one entry per colour change,
    the same thread repeating), not the thread list: architecture on main had
    14 blocks over 6 threads and must read 6/6, cap kept."""
    out = _output(colors=6)
    out["design"]["colors"] = [{"r": c, "g": 0, "b": 0, "name": f"t{c}"} for c in (1, 2, 3, 4, 5, 6, 2, 1, 3, 1, 2, 3, 4, 1)]
    out["stats"]["color_changes"] = 13
    row = pc.summarise(out, cap=6)
    assert row["colors_used"] == 6 and row["cap_kept"] is True and row["color_changes"] == 13


def test_capture_resummarises_an_existing_worker_output_instead_of_rerunning(tmp_path, monkeypatch):
    """A row whose `<slug>.json` exists but whose `.row.json` was deleted is
    re-summarised from that output (the slow part is the worker; the
    summary is derived) — so an instrument fix re-reads an hours-long capture
    in seconds."""
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    photos, out = _photos(tmp_path), tmp_path / "run"
    pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    (out / "a.row.json").unlink()
    monkeypatch.setattr(pc, "WORKER", "raise SystemExit('must not run')")
    run = pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    assert run["rows"]["a"]["stitches"] == 3 and (out / "a.row.json").exists()


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


# ------------------------------------------------------------------ Task 4: capture
STUB_OK = (
    "import json,sys; s=json.loads(sys.argv[1]); open(s['out'],'w').write(json.dumps({"
    "'state':'done','stats':{'stitch_count':3,'trims':0,'color_changes':0,'size_mm':[80,40],'thread_m_total':0.1},"
    "'warnings':[],'preflight':{'grade':'A','score':100,'metrics':{'raw_score':100}},"
    "'design':{'stitches':[{'x':0,'y':0},{'x':10,'y':0},{'x':10,'y':10}],'colors':[{'r':0,'g':0,'b':0}]},"
    "'_meta':{'elapsed_s':0.1,'stamps':{},'class':'photo_subject','class_conf':0.8}}))")
STUB_HANG = "import time; time.sleep(30)"


def _photos(tmp_path):
    import cv2
    photos = tmp_path / "p"
    photos.mkdir()
    cv2.imwrite(str(photos / "a.jpg"), np.zeros((20, 30, 3), np.uint8))
    return photos


def test_run_row_writes_timeout_output(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_HANG)
    out = tmp_path / "a.json"
    res = pc.run_row(tmp_path, tmp_path / "a.jpg", out, {}, timeout=1.0)
    assert res["state"] == "timeout"
    assert json.loads(out.read_text(encoding="utf-8"))["state"] == "timeout"


def test_capture_writes_row_png_and_run_json(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    out = tmp_path / "run"
    run = pc.capture([ROW], _photos(tmp_path), tmp_path, out, tree_sha="abc", timeout=10, procs=1)
    assert (out / "a.png").exists() and (out / "a.row.json").exists() and (out / "run.json").exists()
    assert run["tree_sha"] == "abc" and run["rows"]["a"]["stitches"] == 3
    assert "fidelity_cc" in run["rows"]["a"] and run["rows"]["a"]["genre"] == "g"


def test_capture_resumes_past_finished_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    photos, out = _photos(tmp_path), tmp_path / "run"
    pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    monkeypatch.setattr(pc, "WORKER", "raise SystemExit('must not run')")
    run = pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    assert run["rows"]["a"]["stitches"] == 3


def test_capture_row_without_a_photo_is_an_error_row_with_a_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    photos = tmp_path / "p"
    photos.mkdir()
    run = pc.capture([ROW], photos, tmp_path, tmp_path / "run", "abc", 10, 1)
    assert run["rows"]["a"]["state"] == "error" and (tmp_path / "run" / "a.png").exists()


def test_request_config_is_the_studio_request_on_left_chest():
    cfg = pc.request_config()
    assert cfg["target_width_mm"] == 80.0 and cfg["garment_id"] == "left_chest"
    assert cfg["garment_rgb"] == [235, 232, 223] and cfg["max_colors"] == 6


# ------------------------------------------------------------------ Task 5: sxs
def _run(tmp_path, name, sha, slugs=("a",), state="done"):
    import cv2
    d = tmp_path / name
    d.mkdir()
    rows = {s: {"slug": s, "kind": "photo", "genre": "g", "state": state,
                "stitches": 5 if state == "done" else None, "trims": 1, "wall_s": 3.0,
                "colors_used": 2, "cap": 6, "cap_kept": True, "grade": "F", "score_raw": -10,
                "fidelity_cc": 0.2, "ssim": 0.3, "dE": 20.0} for s in slugs}
    (d / "run.json").write_text(json.dumps({"tree_sha": sha, "date": "2026-10-27", "config": {},
                                            "timeout_s": 1, "procs": 1, "rows": rows}), encoding="utf-8")
    for s in slugs:
        cv2.imwrite(str(d / f"{s}.png"), np.zeros((8, 8, 3), np.uint8))
    return pc.load_run(d)


def test_sxs_has_a_row_per_corpus_slug_with_buttons_and_export(tmp_path):
    html = pc.build_sxs(_run(tmp_path, "b", "aaa1111"), _run(tmp_path, "h", "bbb2222"), [ROW],
                        _photos(tmp_path), {"a": {"author": "Someone", "licence": "cc0", "page": "https://commons/x"}})
    assert 'data-slug="a"' in html and html.count('data-verdict=') == 3
    assert "sxs:aaa1111:bbb2222" in html and "instrument readings" in html
    assert "Someone" in html and "https://commons/x" in html
    assert html.count("data:image/png;base64") == 3


def test_sxs_row_with_a_missing_or_failed_side_still_renders(tmp_path):
    before = _run(tmp_path, "b", "aaa1111", state="timeout")
    after = _run(tmp_path, "h", "bbb2222", slugs=())
    html = pc.build_sxs(before, after, [ROW], _photos(tmp_path), {})
    assert 'data-slug="a"' in html and "timeout" in html and "missing" in html


def test_sxs_refuses_identical_tree_shas(tmp_path):
    photos = _photos(tmp_path)
    with pytest.raises(SystemExit):
        pc.build_sxs(_run(tmp_path, "b", "same"), _run(tmp_path, "h", "same"), [ROW], photos, {})
    html = pc.build_sxs(_run(tmp_path, "b2", "same"), _run(tmp_path, "h2", "same"), [ROW],
                        photos, {}, allow_same_sha=True)
    assert 'data-slug="a"' in html


# ------------------------------------------------------------------ Task 6: tally
V = {"before": "aaa1111", "after": "bbb2222", "date": "2026-10-27",
     "rows": {"a": {"verdict": "worse", "note": "halo"}}}
ROWS = [ROW, {**ROW, "slug": "b", "kind": "logo"}]


def test_tally_counts_by_kind_and_lists_worse_slugs():
    t = pc.tally_counts(V, ROWS)
    assert t["photo"] == {"better": 0, "same": 0, "worse": 1, "unjudged": 0, "worse_slugs": ["a"]}
    assert t["logo"]["unjudged"] == 1 and t["logo"]["worse_slugs"] == []


def test_tally_is_idempotent_per_sha_pair(tmp_path):
    pc.file_verdicts(V, ROWS, tmp_path)
    pc.file_verdicts(V, ROWS, tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.count("aaa1111") == 1 and (tmp_path / "2026-10-27-aaa1111-bbb2222.json").exists()
    assert "instrument readings" in readme and "| 0 / 0 / 1 |" in readme and "halo" not in readme


# --- logo rows: PNG by mime, alpha composited onto the fabric ------------------

def test_fetch_names_a_png_row_by_its_mime(tmp_path):
    r = pc.fetch([ROW], tmp_path, get=_fake_api(mime="image/png"), download=lambda url: b"\x89PNGbytes")
    assert r["fetched"] == ["a"]
    assert (tmp_path / "a.png").read_bytes().startswith(b"\x89PNG") and not (tmp_path / "a.jpg").exists()
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["a"]
    assert m["file"] == "a.png"


def test_photo_path_finds_png_or_jpg(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"x")
    assert pc.photo_path(tmp_path, "a") == tmp_path / "a.png"
    assert pc.photo_path(tmp_path, "b") == tmp_path / "b.jpg"
    assert pc.photo_path(tmp_path, "c") is None


def test_load_photo_composites_alpha_onto_the_fabric(tmp_path):
    import cv2
    rgba = np.zeros((4, 4, 4), np.uint8)
    rgba[:, :, :3] = (0, 0, 255)      # red ink everywhere ...
    rgba[1:3, 1:3, 3] = 255           # ... but opaque only in the middle
    cv2.imwrite(str(tmp_path / "a.png"), rgba)
    bgr = pc.load_photo(tmp_path / "a.png", fabric_bgr=(10, 20, 30))
    assert bgr.shape == (4, 4, 3)
    assert tuple(bgr[0, 0]) == (10, 20, 30) and tuple(bgr[1, 1]) == (0, 0, 255)


def test_baseline_summary_keeps_numbers_and_drops_images(tmp_path):
    run = _run(tmp_path, "r", "abc1234", slugs=("a", "b"))
    out = pc.baseline_summary(run)
    assert out["tree_sha"] == "abc1234" and set(out["rows"]) == {"a", "b"}
    assert "png" not in out and "dir" not in out
    row = out["rows"]["a"]
    assert row["state"] == "done" and "stitches" in row and "design" not in row
