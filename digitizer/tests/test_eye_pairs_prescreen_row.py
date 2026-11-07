"""The display-only vision pre-screen row on the eye-pairs sitting page
(Kent 2026-11-06). The row is a line of text; these tests pin that it is
only that: the class rule, the blind payload, and a default page that is
byte-identical to the one served before the option existed."""
import hashlib
import json
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import server as sv  # noqa: E402
from tools.eye_pairs import vlm_judge as vj  # noqa: E402
from tools.eye_pairs.__main__ import main  # noqa: E402
from tools.eye_pairs.pairs import sealed_hash  # noqa: E402

PAIR_IDS = ("P001", "P002", "P003")


def build_site(out: Path) -> None:
    """What `--pair` leaves behind, for three pairs."""
    (out / "img").mkdir()
    pairs = [{"pair": pid, "left": f"{pid}_L.jpg", "right": f"{pid}_R.jpg",
              "art": f"{pid}_art.png"} for pid in PAIR_IDS]
    (out / "pairs.json").write_text(json.dumps(pairs))
    for pid in PAIR_IDS:
        for name in (f"{pid}_L.jpg", f"{pid}_R.jpg", f"{pid}_art.png"):
            (out / "img" / name).write_bytes(b"bytes-of-" + name.encode())
    sealed = {pid: {"fixture": "becker"} for pid in PAIR_IDS}
    (out / "arms.json").write_text(json.dumps(sealed))
    (out / "sitting.json").write_text(json.dumps(
        {"sealed_sha256": sealed_hash(sealed), "n_pairs": len(PAIR_IDS), "built_ts": "t"}))


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())

# sha256 of server.PAGE as it stood on main before this option (b68b5f37).
PAGE_SHA256 = "c413f90d389e946cbd0bddf1837bfcfd856932c4d0c3d039e6efe645bf107e8e"


# ------------------------------------------------------------ the rule ----

@pytest.mark.parametrize("row,cls", [
    ({"choice": "tie", "confidence": 1}, vj.PRESCREEN_NOTHING),     # tie, any confidence
    ({"choice": "tie", "confidence": 5}, vj.PRESCREEN_NOTHING),
    ({"choice": "L", "confidence": 5}, vj.PRESCREEN_DAMAGED),
    ({"choice": "R", "confidence": 4}, vj.PRESCREEN_DAMAGED),       # the boundary: 4 is in
    ({"choice": "L", "confidence": 3}, vj.PRESCREEN_LOOK),          # 3 is out
    ({"choice": "R", "confidence": 1}, vj.PRESCREEN_LOOK),
    ({"choice": "L", "confidence": None}, vj.PRESCREEN_LOOK),
    ({"choice": "L", "confidence": "5"}, vj.PRESCREEN_LOOK),
    ({"choice": "L", "confidence": True}, vj.PRESCREEN_LOOK),
    ({"choice": None, "confidence": 5}, vj.PRESCREEN_LOOK),         # no choice
    ({}, vj.PRESCREEN_LOOK),
    (None, vj.PRESCREEN_LOOK),
])
def test_prescreen_class_is_the_registered_rule(row, cls):
    assert vj.prescreen_class(row) == cls


def test_the_threshold_is_four_and_only_four():
    assert vj.PRESCREEN_THRESHOLD == 4


def test_labels_cover_every_class():
    assert set(vj.PRESCREEN_LABELS) == {vj.PRESCREEN_NOTHING, vj.PRESCREEN_DAMAGED, vj.PRESCREEN_LOOK}


# ---------------------------------------------------------- verdict file ----

def verdicts(path: Path) -> Path:
    rows = [
        {"pair": "P001", "order": "A", "choice": "tie", "confidence": 4, "reason": "SECRET-REASON-1"},
        {"pair": "P002", "order": "A", "choice": "L", "confidence": 5, "reason": "SECRET-REASON-2"},
        {"pair": "P009", "order": "A", "choice": "R", "confidence": 2, "reason": "not in this sitting"},
        {"pair": "P001", "order": "B", "choice": "L", "confidence": 5, "reason": "order B ignored"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_prescreen_rows_carry_class_label_confidence_and_nothing_else(tmp_path):
    rows = vj.prescreen_rows(verdicts(tmp_path / "v.jsonl"))
    assert rows["P001"] == {"class": "nothing_to_choose", "label": "nothing to choose", "confidence": 4}
    assert rows["P002"] == {"class": "plainly_damaged", "label": "plainly damaged", "confidence": 5}
    assert set(rows["P002"]) == {"class", "label", "confidence"}   # no side, no reason
    assert "SECRET" not in json.dumps(rows)


# ----------------------------------------------------------------- page ----

def serve(out, **kw):
    httpd = sv.make_server(out, port=0, **kw)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


@pytest.fixture()
def plain(tmp_path):
    out = tmp_path / "plain"
    out.mkdir()
    build_site(out)
    httpd, base = serve(out)
    yield out, base
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture()
def screened(tmp_path):
    out = tmp_path / "screened"
    out.mkdir()
    build_site(out)
    httpd, base = serve(out, prescreen=verdicts(tmp_path / "v.jsonl"))
    yield out, base
    httpd.shutdown()
    httpd.server_close()


def test_default_page_is_byte_identical_to_before(plain):
    _out, base = plain
    _s, html = get(base + "/")
    assert sv.PAGE.encode() == html
    assert hashlib.sha256(html).hexdigest() == PAGE_SHA256
    assert b'id="pre"' not in html and b"prescreen" not in html
    _s, body = get(base + "/pairs")
    assert set(json.loads(body)) == {"pairs", "picked", "sitting"}


def test_prescreen_page_adds_the_row_and_changes_nothing_else(screened):
    _out, base = screened
    _s, html = get(base + "/")
    assert html != sv.PAGE.encode()
    text = html.decode()
    assert 'id="pre"' in text and "display only" in text and "not judged" in text
    # every line of the original page survives, in order, in the new one
    rest = text
    for line in sv.PAGE.splitlines():
        i = rest.find(line)
        assert i >= 0, line
        rest = rest[i + len(line):]
    # the recording path is untouched
    for token in ("async function pick(", "async function undo(", "fetch('/pick'", "queue.shift()"):
        assert token in text and token in sv.PAGE


def test_prescreen_payload_is_blind_and_never_reorders_or_filters_pairs(screened, plain):
    _o1, base = screened
    _o2, base_plain = plain
    shown = json.loads(get(base + "/pairs")[1])
    default = json.loads(get(base_plain + "/pairs")[1])
    assert shown["pairs"] == default["pairs"]                 # same pairs, same order, none hidden
    assert shown["picked"] == []                              # nothing pre-filled
    assert set(shown["prescreen"]) == {"P001", "P002"}        # P009 is not this sitting's
    assert "SECRET" not in json.dumps(shown)
    assert all(set(v) == {"class", "label", "confidence"} for v in shown["prescreen"].values())


def test_picking_with_the_row_on_records_exactly_what_it_did_before(screened):
    out, base = screened
    assert post(base + "/pick", {"pair": "P001", "choice": "R", "ms": 5})[0] == 200
    lines = [json.loads(x) for x in (out / "picks.jsonl").read_text().splitlines()]
    assert [(r["pair"], r["choice"]) for r in lines] == [("P001", "R")]   # Kent's pick, not the judge's tie


def test_pair_without_a_verdict_is_listed_without_a_class(screened):
    _out, base = screened
    d = json.loads(get(base + "/pairs")[1])
    assert "P003" not in d["prescreen"]      # the page prints "not judged" for it


def test_verdicts_for_another_sitting_are_refused(tmp_path):
    build_site(tmp_path)
    other = tmp_path.parent / (tmp_path.name + "-other.jsonl")
    other.write_text(json.dumps({"pair": "P500", "order": "A", "choice": "tie", "confidence": 3}) + "\n")
    with pytest.raises(SystemExit, match="judges none"):
        sv.make_server(tmp_path, port=0, prescreen=other)
    with pytest.raises(SystemExit, match="not found"):
        sv.make_server(tmp_path, port=0, prescreen=tmp_path / "nope.jsonl")


def test_the_cli_flag_only_goes_with_serve(tmp_path):
    with pytest.raises(SystemExit):
        main(["--prescreen", str(tmp_path / "v.jsonl"), "--out", str(tmp_path)])
