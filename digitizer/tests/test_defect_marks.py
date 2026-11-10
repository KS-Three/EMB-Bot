"""`tools.defect_marks`: the pure helpers and the localhost server, no engine.

The two properties that matter: the PAGE never receives the yardstick's
reading (Kent's marks must be blind to it), and an answer outside the page's
own vocabulary is refused rather than stored.
"""
import json
import threading
import urllib.error
import urllib.request

import pytest

from tools import defect_marks as dm


def _item(iid="L_x", grade="B", findings=()):
    return {"id": iid, "group": "pro_logo", "title": "x", "size": "80 x 40 mm on hat_front",
            "art": f"{iid}_art.jpg", "render": f"{iid}_render.png", "pro": None, "pro_colours": False,
            "img_w": 1008, "img_h": 528, "px_per_mm": 12.0, "pad_mm": 2.0, "tree_sha": "abc",
            "yardstick": {"grade": grade, "score": 82, "findings": list(findings), "metrics": {"m": 1},
                          "fidelity_cc": 0.1}}


def _kit(items=None):
    return {"kit_sha256": "k" * 64, "px_per_mm": 12.0, "skipped": [], "items": items or [_item()]}


def test_mark_mm_undoes_the_render_pad():
    # 1008 px wide at 12 px/mm = 84 mm, of which 2 mm each side is pad
    assert dm.mark_mm(0.0, 0.0, 1008, 528) == (-2.0, -2.0)
    assert dm.mark_mm(0.5, 0.5, 1008, 528) == (40.0, 20.0)
    assert dm.mark_mm(1.0, 1.0, 1008, 528) == (82.0, 42.0)


def test_page_is_blind_to_the_yardstick():
    kit = _kit([_item(findings=[{"code": "THREAD_MATCH_POOR", "severity": "block", "message": "m", "extra": {}}])])
    pub = dm.public_kit(kit)
    text = json.dumps(pub) + dm.page_html(kit)
    for leak in ("yardstick", "THREAD_MATCH_POOR", "fidelity_cc", "tree_sha", '"score"'):
        assert leak not in text
    assert pub["items"][0]["render"] == "L_x_render.png"
    assert set(pub["whats"]) == set(dm.WHATS) and pub["grades"] == list(dm.GRADES)


def test_clean_item_keeps_a_valid_answer_and_adds_mm():
    rec = dm.clean_item({"grade": "Bad", "whole": ["too_busy"], "reason": "letters",
                         "pins": [{"x": 0.5, "y": 0.5, "what": "blob", "severity": "ruins", "note": "in the M"}]},
                        _item())
    assert rec["grade"] == "Bad" and rec["whole"] == ["too_busy"] and not rec["nothing_wrong"]
    assert rec["pins"] == [{"x": 0.5, "y": 0.5, "x_mm": 40.0, "y_mm": 20.0, "what": "blob",
                            "severity": "ruins", "note": "in the M"}]


@pytest.mark.parametrize("body", [
    {"grade": "Fine"},
    {"whole": ["nope"]},
    {"pins": [{"x": 1.2, "y": 0.5}]},
    {"pins": [{"x": 0.2, "y": 0.5, "what": "smudge"}]},
    {"pins": [{"x": 0.2, "y": 0.5, "severity": "awful"}]},
])
def test_clean_item_refuses_what_the_page_cannot_send(body):
    with pytest.raises(ValueError):
        dm.clean_item(body, _item())


def test_answered_needs_a_grade_and_something_said():
    assert not dm.answered(None)
    assert not dm.answered({"grade": "Good", "pins": [], "whole": [], "nothing_wrong": False})
    assert not dm.answered({"grade": None, "pins": [{}], "whole": [], "nothing_wrong": False})
    assert dm.answered({"grade": "Great", "pins": [], "whole": [], "nothing_wrong": True})


def test_report_step_is_signed_yardstick_kinder_positive():
    kit = _kit([_item("L_a", grade="A", findings=[{"code": "TRIM_HEAVY"}, {"code": "TRIM_HEAVY"}]),
                _item("L_b", grade="F"), _item("L_c", grade="C")])
    marks = {"items": {
        "L_a": {"grade": "Bad", "nothing_wrong": False, "whole": [], "reason": "r",
                "pins": [{"what": "blob", "severity": "ruins"}, {"what": "blob", "severity": "nitpick"},
                         {"what": None, "severity": None}]},
        "L_b": {"grade": "Good", "nothing_wrong": True, "whole": [], "reason": "", "pins": []},
        "L_c": {"grade": None, "nothing_wrong": False, "whole": [], "reason": "", "pins": []}}}
    rows = {r["id"]: r for r in dm.report_rows(kit, marks)}
    assert set(rows) == {"L_a", "L_b"}                       # L_c has no grade: not answered
    assert rows["L_a"]["step"] == 3 and rows["L_b"]["step"] == -3
    assert rows["L_a"]["pins"] == {"blob": 2, "unnamed": 1} and rows["L_a"]["ruins"] == 1
    assert rows["L_a"]["codes"] == {"TRIM_HEAVY": 2}
    assert "L_a" in dm.report_text(kit, marks)


@pytest.fixture
def served(tmp_path):
    kit = _kit()
    (tmp_path / "img").mkdir()
    (tmp_path / "img" / "L_x_render.png").write_bytes(b"png")
    (tmp_path / "img" / "secret.png").write_bytes(b"no")
    (tmp_path / "kit.json").write_text(json.dumps(kit), encoding="utf-8")
    srv = dm.make_server(tmp_path, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield tmp_path, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=10).read()


def test_server_saves_marks_and_serves_only_listed_images(served):
    kit_dir, base = served
    page = urllib.request.urlopen(base + "/", timeout=10).read().decode("utf-8")
    assert "yardstick" not in page and "L_x_render.png" in page
    assert urllib.request.urlopen(base + "/img/L_x_render.png", timeout=10).read() == b"png"
    for path in ("/img/secret.png", "/kit.json", "/img/../kit.json"):
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + path, timeout=10)
    _post(base + "/mark", {"id": "L_x", "grade": "Okay", "nothing_wrong": False, "whole": [], "reason": "",
                           "pins": [{"x": 0.25, "y": 0.5, "what": "wavy", "severity": "noticeable", "note": ""}]})
    saved = json.loads((kit_dir / "marks.json").read_text(encoding="utf-8"))
    assert saved["kit_sha256"] == "k" * 64
    assert saved["items"]["L_x"]["pins"][0]["x_mm"] == 19.0
    assert json.loads(urllib.request.urlopen(base + "/marks", timeout=10).read())["items"]["L_x"]["grade"] == "Okay"
    for bad in ({"id": "nope", "grade": "Okay"}, {"id": "L_x", "grade": "Fine"}):
        with pytest.raises(urllib.error.HTTPError):
            _post(base + "/mark", bad)


def test_server_follows_a_rebuilt_kit_without_a_restart(served):
    """`kit` is re-run as capture rows finish; a page reload must show the new
    item and accept its answer, and the earlier answer must still be there."""
    import os
    kit_dir, base = served
    _post(base + "/mark", {"id": "L_x", "grade": "Good", "nothing_wrong": True})
    with pytest.raises(urllib.error.HTTPError):
        _post(base + "/mark", {"id": "P_new", "grade": "Bad", "nothing_wrong": True})
    bigger = _kit([_item("L_x"), _item("P_new")])
    bigger["kit_sha256"] = "n" * 64
    path = kit_dir / "kit.json"
    path.write_text(json.dumps(bigger), encoding="utf-8")
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))   # a coarse-mtime filesystem
    assert "P_new_render.png" in urllib.request.urlopen(base + "/", timeout=10).read().decode("utf-8")
    _post(base + "/mark", {"id": "P_new", "grade": "Bad", "nothing_wrong": True})
    saved = json.loads((kit_dir / "marks.json").read_text(encoding="utf-8"))
    assert set(saved["items"]) == {"L_x", "P_new"} and saved["kit_sha256"] == "n" * 64
