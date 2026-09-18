import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import server as sv  # noqa: E402
from tools.eye_pairs.pairs import load_picks  # noqa: E402


@pytest.fixture()
def site(tmp_path):
    (tmp_path / "img").mkdir()
    pairs = [{"pair": pid, "left": f"{pid}_L.jpg", "right": f"{pid}_R.jpg",
              "art": f"{pid}_art.png"} for pid in ("P001", "P002")]
    (tmp_path / "pairs.json").write_text(json.dumps(pairs))
    for pid in ("P001", "P002"):
        for name in (f"{pid}_L.jpg", f"{pid}_R.jpg", f"{pid}_art.png"):
            (tmp_path / "img" / name).write_bytes(b"bytes-of-" + name.encode())
    (tmp_path / "arms.json").write_text('{"P001": {"fixture": "becker"}}')
    (tmp_path / "features.json").write_text("{}")
    (tmp_path / "designs").mkdir()
    (tmp_path / "designs" / "becker__base.json").write_text("{}")
    httpd = sv.make_server(tmp_path, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield tmp_path, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


def test_the_page_and_the_public_pairs_are_served(site):
    _out, base = site
    status, html = get(base + "/")
    assert status == 200 and b"ArrowLeft" in html
    _status, body = get(base + "/pairs")
    data = json.loads(body)
    assert data["pairs"][0]["pair"] == "P001" and data["picked"] == []


def test_the_page_guards_against_held_keys_and_failed_posts(site):
    """Review findings 4 and 5 (2026-09-17): the keydown handler fired on OS
    auto-repeat, so a held arrow burned through pairs Kent never saw; and
    pick() advanced the queue before the POST resolved, so a dropped
    connection left the old images on screen while the next click was
    recorded against the next pair. The page is inline JS, so the testable
    surface is that the guards are present in what is served."""
    _out, base = site
    html = get(base + "/")[1].decode()
    assert "if(e.repeat)return;" in html
    assert "if(!r.ok)throw" in html
    assert "busy" in html and "if(busy" in html
    # The queue advances AFTER the POST succeeds, not before it is sent.
    assert html.index("await send(") < html.index("queue.shift()")
    assert "Not saved" in html                      # the visible failure banner


def test_picked_is_reported_in_click_order_so_undo_after_a_reload_is_right(site):
    _out, base = site
    post(base + "/pick", {"pair": "P002", "choice": "L", "ms": 5})
    post(base + "/pick", {"pair": "P001", "choice": "R", "ms": 5})
    assert json.loads(get(base + "/pairs")[1])["picked"] == ["P002", "P001"]
    post(base + "/pick", {"pair": "P002", "choice": "tie", "ms": 5})   # re-picked: now last
    assert json.loads(get(base + "/pairs")[1])["picked"] == ["P001", "P002"]


def test_only_listed_images_are_served(site):
    _out, base = site
    assert get(base + "/img/P001_L.jpg")[1] == b"bytes-of-P001_L.jpg"


@pytest.mark.parametrize("path", ["/arms.json", "/features.json", "/pairs.json",
                                  "/designs/becker__base.json",
                                  "/img/../arms.json", "/img/%2e%2e/arms.json",
                                  "/img/nope.jpg"])
def test_everything_sealed_is_a_404(site, path):
    _out, base = site
    with pytest.raises(urllib.error.HTTPError) as err:
        get(base + path)
    assert err.value.code == 404


def test_a_pick_lands_on_disk_before_the_reply(site):
    out, base = site
    assert post(base + "/pick", {"pair": "P001", "choice": "L", "ms": 812})[1] == {"ok": True}
    assert load_picks(out / "picks.jsonl")["P001"]["choice"] == "L"
    assert json.loads(get(base + "/pairs")[1])["picked"] == ["P001"]


def test_undo_puts_the_pair_back(site):
    out, base = site
    post(base + "/pick", {"pair": "P001", "choice": "R", "ms": 5})
    post(base + "/pick", {"pair": "P001", "undo": True, "ms": 0})
    assert load_picks(out / "picks.jsonl") == {}


@pytest.mark.parametrize("body", [{"pair": "P999", "choice": "L", "ms": 1},
                                  {"pair": "P001", "choice": "left", "ms": 1}])
def test_a_bad_pick_is_a_400_and_writes_nothing(site, body):
    out, base = site
    with pytest.raises(urllib.error.HTTPError) as err:
        post(base + "/pick", body)
    assert err.value.code == 400
    assert not (out / "picks.jsonl").exists()
