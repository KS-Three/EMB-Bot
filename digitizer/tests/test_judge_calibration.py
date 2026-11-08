"""The calibrated judge's phase A (`tools.eye_pairs.judge_calibration`): the
split is deterministic and disjoint, the committed manifest is the one the
code makes, the kit builder never reads the held-out list, and the page loads.

Kent 2026-11-07: "a side by side camparison of ambiguous photos that can point
you in the right direction." The protocol is
`docs/eye-pairs-2026-11-04/calibrated-judge/PRE-REGISTRATION.md`.
"""
from __future__ import annotations

import json
from collections import Counter

import pytest

from tools.eye_pairs import judge_calibration as jc
from tools.eye_pairs import vlm_judge as vj

PREREG = jc.OUT / "PRE-REGISTRATION.md"


@pytest.fixture(scope="module")
def committed_pool():
    return jc.pool()


# ---------------------------------------------------------------- the split ----

def test_the_pre_registration_pins_seed_fraction_bar_and_manifest(committed_pool):
    text = " ".join(PREREG.read_text(encoding="utf-8").split())
    assert f"Seed {jc.SEED}, fraction {jc.CAL_FRACTION:.2f}" in text
    assert f"kappa >= +{jc.PASS_KAPPA:.2f}" in text and f"> +{jc.PASS_CI_LOWER:.2f}" in text
    assert jc.pool_sha(committed_pool) in text
    assert vj.prompt_sha() in text
    assert f"up to {jc.KIT_MAX}" in text
    sp = jc.split(committed_pool)
    assert f"CALIBRATION {len(sp['calibration'])}" in text and f"HELD-OUT {len(sp['held_out'])}" in text
    assert f"The pool is **{len(committed_pool)}**" in text


def test_the_pool_is_the_two_judged_sets_without_a_duplicate(committed_pool):
    by_set = Counter(r["set"] for r in committed_pool)
    assert by_set == {jc.SET_1104: 54, jc.SET_1106: 99}
    assert len({r["id"] for r in committed_pool}) == len(committed_pool)
    assert {r["kent"] for r in committed_pool} <= set(vj.SIDES)


def test_the_rebuilt_1106_key_reproduces_the_committed_analysis():
    """The 11-06 kit's arms.json is gone; `pro100_sealed` rebuilds it. Scoring
    the committed verdicts through it must give the committed table."""
    sealed = vj.pro100_sealed()
    verdicts = vj.load_verdicts(vj.PRO100_OUT)["claude-opus-5-5-session"]["A"]
    table = [[0] * 3 for _ in vj.SIDES]
    for pid, s in sealed.items():
        if s["kind"] == "live":
            j = vj.to_label(verdicts[pid]["choice_frame_a"], s)
            table[vj.SIDES.index(s["kent"])][vj.SIDES.index(j)] += 1
    committed = json.loads((vj.PRO100_OUT / "analysis.json").read_text(encoding="utf-8"))
    live = committed["models"]["claude-opus-5-5-session"]["orders"]["A"]["reads"]["live"]
    assert table == live["table_kent_rows_judge_cols"]
    opp = committed["models"]["claude-opus-5-5-session"]["orders"]["A"]["opposite_side"]
    assert all((sealed[d["pair"]]["fixture"], sealed[d["pair"]]["arm"]) == (d["fixture"], d["arm"]) for d in opp)
    assert all(verdicts[p]["choice"] == "tie" for p, s in sealed.items() if s["kind"] == "identical")


def test_the_split_is_deterministic_disjoint_and_complete(committed_pool):
    a, b = jc.split(committed_pool), jc.split(list(reversed(committed_pool)))
    assert a == b
    cal, held = set(a["calibration"]), set(a["held_out"])
    assert not cal & held
    assert cal | held == {r["id"] for r in committed_pool}
    assert abs(len(cal) - round(jc.CAL_FRACTION * len(committed_pool))) <= 1
    # every stratum gets its share to within one pair
    for key in {jc.stratum(r) for r in committed_pool}:
        ids = [r["id"] for r in committed_pool if jc.stratum(r) == key]
        n_cal = sum(i in cal for i in ids)
        assert abs(n_cal - jc.CAL_FRACTION * len(ids)) < 1 + 1e-9, key
    assert jc.split(committed_pool, seed=jc.SEED + 1) != a


def test_the_committed_manifest_is_the_one_the_code_makes(committed_pool):
    for name, payload in jc.manifest_payloads(committed_pool).items():
        on_disk = json.loads((jc.OUT / name).read_text(encoding="utf-8"))
        assert on_disk == payload, name
        assert set(on_disk) == {"seed", "fraction", "n_pool", "pool_sha256", "rule", "part", "ids"}
        text = (jc.OUT / name).read_text(encoding="utf-8")
        for word in ("before", "after", "tie", "base", "kent"):     # ids only: no label, no side
            assert word not in text.lower().replace("held_out", ""), (name, word)


def test_split_refuses_to_overwrite_a_different_manifest(tmp_path, monkeypatch):
    rows = [{"id": f"s:P{i:03d}", "set": "s", "pair": f"P{i:03d}", "design": "d", "kent": "tie"}
            for i in range(10)]
    monkeypatch.setattr(jc, "pool", lambda: rows)
    assert jc.main(["split", "--out", str(tmp_path)]) == 0
    assert jc.main(["split", "--out", str(tmp_path)]) == 0          # same bytes: fine
    assert jc.main(["split", "--out", str(tmp_path), "--check"]) == 0
    rows.append({"id": "s:P999", "set": "s", "pair": "P999", "design": "d", "kent": "tie"})
    assert jc.main(["split", "--out", str(tmp_path), "--check"]) == 1
    with pytest.raises(SystemExit, match="REFUSED"):
        jc.main(["split", "--out", str(tmp_path)])


def test_primary_applies_both_halves_of_the_bar():
    perfect = [("before", "before", f"d{i % 5}") for i in range(20)] + \
              [("after", "after", f"d{i % 5}") for i in range(20)] + \
              [("tie", "tie", f"d{i % 5}") for i in range(20)]
    assert jc.primary(perfect)["passes"] is True
    ties_only = [(k, "tie", f"d{i % 5}") for i, (k, _, _) in enumerate(perfect)]
    assert jc.primary(ties_only)["passes"] is False


# ------------------------------------------------------------------ the kit ----

def _fake_world(tmp_path):
    """Two tiny sets, a manifest that puts disagreements in both parts,
    synthetic renders: no real picture, no committed label."""
    import cv2
    import numpy as np
    common = {"repeat_of": None, "design_only": False, "kind": "live"}
    kent = {"P001": "after", "P002": "tie", "P003": "before", "P004": "after", "P005": "tie", "P006": "before"}
    judge = {"P001": "tie", "P002": "L", "P003": "R", "P004": "L", "P005": "tie", "P006": "tie"}
    sets = {name: {pid: {**common, "fixture": "fx", "left_arm": "base", "right_arm": "armA",
                         "kent": k, "design": "d", "key": (name, pid)} for pid, k in kent.items()}
            for name in ("a", "b")}
    vdir = tmp_path / "verdicts"
    vdir.mkdir()
    files = {}
    for name in sets:
        files[name] = vdir / f"{name}.jsonl"
        files[name].write_text("".join(json.dumps({"pair": p, "order": "A", "choice": c, "choice_frame_a": c,
                                                   "confidence": 3, "reason": f"reason {name} {p}"}) + "\n"
                                       for p, c in judge.items()), encoding="utf-8")
    man = tmp_path / "manifest"
    man.mkdir()
    cal = ["a:P001", "a:P002", "a:P003", "a:P005", "b:P004"]
    held = ["a:P004", "a:P006", "b:P001", "b:P002", "b:P003", "b:P005", "b:P006"]
    (man / jc.CALIBRATION_FILE).write_text(json.dumps({"ids": cal}), encoding="utf-8")
    (man / jc.HELD_OUT_FILE).write_text(json.dumps({"ids": held}), encoding="utf-8")
    pics = tmp_path / "pics"
    pics.mkdir()
    base = np.full((120, 200, 3), 255, np.uint8)
    cv2.rectangle(base, (20, 20), (180, 100), (40, 40, 200), -1)
    arm = base.copy()
    cv2.circle(arm, (150, 40), 12, (255, 255, 255), -1)       # the one place they differ
    cv2.imwrite(str(pics / "L.jpg"), base)
    cv2.imwrite(str(pics / "R.jpg"), arm[:, :190])             # a narrower canvas: padded to one
    cv2.imwrite(str(pics / "art.png"), base)
    return sets, files, man, cal, held, pics


def _sources(pics):
    return lambda _row: (pics / "L.jpg", pics / "R.jpg", pics / "art.png")


def test_kit_reads_the_calibration_manifest_only(tmp_path, monkeypatch):
    import builtins
    import pathlib
    sets, files, man, cal, held, pics = _fake_world(tmp_path)
    opened: list[str] = []
    real_open = builtins.open
    real_read_text, real_read_bytes, real_popen = (pathlib.Path.read_text, pathlib.Path.read_bytes,
                                                   pathlib.Path.open)

    def spy(fn):
        def wrapped(self, *a, **k):
            opened.append(str(self))
            return fn(self, *a, **k)
        return wrapped

    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_text", spy(real_read_text))
    monkeypatch.setattr(pathlib.Path, "read_bytes", spy(real_read_bytes))
    monkeypatch.setattr(pathlib.Path, "open", spy(real_popen))
    kit = jc.build_kit(tmp_path / "kit", sources=_sources(pics), sets=sets, verdict_files=files,
                       manifest_dir=man)
    assert any(p.endswith(jc.CALIBRATION_FILE) for p in opened)
    assert not [p for p in opened if p.endswith(jc.HELD_OUT_FILE)], "the kit builder read the held-out list"
    ids = [p["id"] for p in kit["pairs"]]
    assert set(ids) <= set(cal) and not set(ids) & set(held)
    # a:P005 agrees (tie / tie); every other CALIBRATION pair is a disagreement
    assert ids == ["a:P001", "a:P002", "a:P003", "b:P004"]
    assert [p["class"] for p in kit["pairs"]] == [jc.CLASS_JUDGE_TIE, jc.CLASS_KENT_TIE,
                                                  jc.CLASS_OPPOSITE, jc.CLASS_OPPOSITE]
    first = kit["pairs"][0]
    assert (first["kent"], first["judge"], first["reason"]) == ("R", "tie", "reason a P001")
    assert kit["per_class"] == {jc.CLASS_JUDGE_TIE: 1, jc.CLASS_KENT_TIE: 1, jc.CLASS_OPPOSITE: 2}
    with pytest.raises(PermissionError):
        jc._kit_read(jc.HELD_OUT_FILE, man)


def test_select_caps_by_class_round_robin_and_stays_in_calibration(tmp_path):
    sets, files, _man, cal, _held, _pics = _fake_world(tmp_path)
    every = [f"{n}:{p}" for n in sets for p in sets[n]]
    rows = jc.select(every, sets, files, k=3)
    assert len(rows) == 3 and {r["class"] for r in rows} == set(jc.CLASSES)
    assert jc.select(every, sets, files, k=3) == rows                      # seeded
    assert {r["id"] for r in jc.select(cal, sets, files)} <= set(cal)


def test_the_diff_window_finds_the_one_place_they_differ():
    import numpy as np
    a = np.full((200, 300, 3), 255, np.uint8)
    b = a.copy()
    b[150:170, 40:60] = 0
    w = jc.diff_window(a, b)
    assert w["differs"] and (w["dx"], w["dy"]) == (0, 0)
    assert w["x"] <= 40 and w["x"] + w["s"] >= 60 and w["y"] <= 150 and w["y"] + w["s"] >= 170
    assert not jc.diff_window(a, a.copy())["differs"]


def test_the_page_loads_and_saves_a_reason(tmp_path):
    import threading
    import urllib.error
    import urllib.request
    import cv2
    sets, files, man, _cal, _held, pics = _fake_world(tmp_path)
    kd = tmp_path / "kit"
    kit = jc.build_kit(kd, sources=_sources(pics), sets=sets, verdict_files=files, manifest_dir=man)
    html = (kd / "index.html").read_text(encoding="utf-8")
    tag = '<script id="kit" type="application/json">'
    start = html.index(tag) + len(tag)
    embedded = json.loads(html[start:html.index("</script>", start)])
    assert embedded["kit_sha256"] == kit["kit_sha256"] and len(embedded["pairs"]) == 4
    for p in kit["pairs"]:
        for s in ("L.jpg", "R.jpg", "Lx3.png", "Rx3.png", "art.png"):
            assert (kd / "img" / f"{p['kit']}_{s}").exists()
    assert cv2.imread(str(kd / "img" / "C01_L.jpg")).shape == cv2.imread(str(kd / "img" / "C01_R.jpg")).shape
    srv = jc.make_server(kd, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(body: dict):
        return urllib.request.urlopen(urllib.request.Request(
            base + "/reason", method="POST", headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode("utf-8")))
    try:
        with urllib.request.urlopen(base + "/") as r:
            assert r.status == 200 and b"Judge calibration" in r.read()
        with urllib.request.urlopen(base + "/img/C01_Lx3.png") as r:
            assert r.status == 200 and r.read()[:4] == b"\x89PNG"
        for bad in ("/kit.json", "/img/../kit.json", "/img/C99_L.jpg"):
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(base + bad)
            assert e.value.code == 404
        with post({"kit": "C01", "reason": " the white dot is a hole "}) as r:
            assert r.status == 200
        saved = jc.read_reasons(kd)
        assert saved["kit_sha256"] == kit["kit_sha256"]
        assert saved["reasons"]["C01"] == {**saved["reasons"]["C01"], "pool_id": kit["pairs"][0]["id"],
                                           "reason": "the white dot is a hole"}
        with urllib.request.urlopen(base + "/reasons") as r:
            assert json.loads(r.read())["reasons"]["C01"]["reason"] == "the white dot is a hole"
        with pytest.raises(urllib.error.HTTPError) as e:
            post({"kit": "C99", "reason": "x"})
        assert e.value.code == 400
    finally:
        srv.shutdown()
        srv.server_close()
