"""tools/flip_guard.py: the standing BASE-vs-FLIP check for default-flip PRs.
Two tiny synthetic designs, so the tool cannot rot; no real art, no rembg."""
import cv2
import numpy as np

from tools import flip_guard as fg


def _designs(tmp_path):
    a = np.full((120, 160, 3), 255, np.uint8)
    cv2.circle(a, (80, 60), 40, (200, 30, 30), -1)
    b = np.full((120, 160, 3), 255, np.uint8)
    cv2.rectangle(b, (30, 30), (130, 90), (20, 20, 160), -1)
    out = []
    for name, img in (("disc.png", a), ("block.png", b)):
        p = tmp_path / name
        cv2.imwrite(str(p), img)
        out.append({"name": name, "path": str(p), "garments": ["left_chest"]})
    return out


def test_override_parsing():
    assert fg.parse_override("satin_seam_hold=False") == ("satin_seam_hold", False)
    assert fg.arm_kwargs(["a=1"], ["extra.k=2", "b=x"]) == {"a": 1, "b": "x", "extra": {"k": 2}}
    assert fg.arm_kwargs(["a=1"], None) == {"a": 1}


def test_flags_logic():
    def cell(md5, trims, bare):
        return {"name": "x.png", "garment": "left_chest", "md5": md5, "stitches": 10,
                "trims": trims, "colours": 1, "bare_mm": bare}

    same = fg.compare(cell("a", 1, 0.0), cell("a", 1, 0.0), [])
    assert not same["moved"] and same["flags"] == []
    r = fg.compare(cell("a", 1, 0.0), cell("b", 3, 2.0), [])
    assert r["flags"][0] == "OUTSIDE EVIDENCE" and any(f.startswith("TRIMS +2") for f in r["flags"])
    assert any(f.startswith("BARE THREAD") for f in r["flags"])
    assert fg.compare(cell("a", 1, 0.0), cell("b", 2, 0.0), ["x"])["flags"] == []


def test_end_to_end_two_designs_and_resume(tmp_path):
    designs = _designs(tmp_path)
    out = tmp_path / "out"
    rows = fg.run(out, ["fill_row_mm=1.6"], evidence=["disc"], jobs=1, designs=designs)
    assert {r["name"] for r in rows} == {"disc.png", "block.png"}
    assert all(r["moved"] for r in rows), "a 1.6 mm fill row pitch must move both designs"
    assert [r["flags"] for r in rows if r["name"] == "block.png"][0][0] == "OUTSIDE EVIDENCE"
    assert not any("OUTSIDE EVIDENCE" in r["flags"] for r in rows if r["name"] == "disc.png")
    html = (out / "flip_guard.html").read_text(encoding="utf-8")
    assert html.index("<table>") < html.index("data:image/jpeg;base64,")
    cells = sorted((out / "cells").glob("*.json"))
    assert len(cells) == 4
    stamp = [c.stat().st_mtime_ns for c in cells]
    fg.run(out, ["fill_row_mm=1.6"], evidence=["disc"], jobs=1, designs=designs)
    assert stamp == [c.stat().st_mtime_ns for c in sorted((out / "cells").glob("*.json"))]


def test_unchanged_flip_moves_nothing(tmp_path):
    rows = fg.run(tmp_path / "o", ["extra.not_a_real_key=1"], jobs=1, designs=_designs(tmp_path)[:1])
    assert [r["moved"] for r in rows] == [False]
