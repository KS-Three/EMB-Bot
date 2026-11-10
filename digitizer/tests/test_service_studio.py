"""`digitizer_service.studio`: the built Studio served by the service itself.

The mount is opt-in and sits at `/`, so the things that can go wrong are all
about what it must NOT do: answer for an API route, hand a module script back
as `text/plain`, let a browser keep an old engine file, or exist at all when
nobody asked for it.
"""
from __future__ import annotations

import mimetypes
import os
import subprocess
import sys
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from digitizer_service import studio  # noqa: E402

DIGITIZER = Path(__file__).resolve().parents[1]


@pytest.fixture
def dist(tmp_path):
    """A stand-in for `app/dist`: the three kinds of file the real bundle has
    (the page, a hashed asset, an engine file copied under its own name), and
    one file OUTSIDE it that must never be reachable."""
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "engine").mkdir()
    (root / "index.html").write_text("<!doctype html><title>studio</title>", encoding="utf-8")
    (root / "assets" / "index-abc123.js").write_text("export const a = 1;", encoding="utf-8")
    (root / "assets" / "index-abc123.css").write_text("body{}", encoding="utf-8")
    (root / "engine" / "units.js").write_text("var EMB = {};", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not served", encoding="utf-8")
    return root


@pytest.fixture
def served(dist, make_client):
    """A throwaway app with one API route registered BEFORE the mount, the
    order `app.py` uses."""
    app = fastapi.FastAPI()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/export")
    def export() -> dict:
        return {"wrote": True}

    studio.mount_studio(app, dist)
    return make_client(app)


def test_the_page_is_served_at_the_root(served):
    r = served.get("/")
    assert r.status_code == 200
    assert "<title>studio</title>" in r.text
    assert r.headers["content-type"].startswith("text/html")


def test_api_routes_registered_first_still_answer(served):
    assert served.get("/health").json() == {"status": "ok"}
    # A POST the mount would answer 405 ("static files are GET only").
    assert served.post("/export").json() == {"wrote": True}


def test_a_mount_added_before_the_routes_shadows_them(dist, make_client):
    """The failure `app.py`'s last line exists to prevent, shown happening:
    this is what the ordering rule costs when it is broken."""
    app = fastapi.FastAPI()
    studio.mount_studio(app, dist)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    assert make_client(app).get("/health").status_code == 404


@pytest.mark.parametrize("path, kind", [
    ("/assets/index-abc123.js", "text/javascript"),
    ("/engine/units.js", "text/javascript"),
    ("/assets/index-abc123.css", "text/css"),
])
def test_content_type_does_not_come_from_the_machine(dist, make_client, path, kind):
    """A Windows registry that maps `.js` to `text/plain` is the real case: a
    browser refuses a module script served that way. Poison the table the way
    such a machine would, then mount."""
    before = {ext: mimetypes.types_map.get(ext) for ext in (".js", ".css")}
    mimetypes.add_type("text/plain", ".js")
    mimetypes.add_type("text/plain", ".css")
    try:
        app = fastapi.FastAPI()
        studio.mount_studio(app, dist)
        r = make_client(app).get(path)
        assert r.status_code == 200
        assert r.headers["content-type"].split(";")[0] == kind
    finally:
        for ext, was in before.items():
            if was:
                mimetypes.add_type(was, ext)


@pytest.mark.parametrize("path", ["/", "/engine/units.js", "/assets/index-abc123.js"])
def test_every_file_must_be_revalidated(served, path):
    """`engine/*.js` keeps its name across releases, so a heuristically cached
    copy is an old engine under a new Studio."""
    assert served.get(path).headers["cache-control"] == "no-cache"


def test_an_unchanged_file_is_a_304(served):
    first = served.get("/engine/units.js")
    again = served.get("/engine/units.js", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


@pytest.mark.parametrize("path", ["/nope.js", "/%2e%2e/secret.txt", "/assets/%2e%2e/%2e%2e/secret.txt"])
def test_nothing_outside_the_bundle_is_served(served, path):
    r = served.get(path)
    assert r.status_code == 404
    assert "not served" not in r.text


def test_a_directory_that_is_not_a_build_is_refused(tmp_path):
    with pytest.raises(studio.StudioMissing, match="npm run build"):
        studio.mount_studio(fastapi.FastAPI(), tmp_path)


def test_the_real_app_has_no_studio_unless_asked():
    if os.environ.get(studio.STUDIO_DIR_ENV):
        pytest.skip(f"{studio.STUDIO_DIR_ENV} is set in this environment")
    from digitizer_service.app import app

    assert studio.MOUNT_NAME not in [getattr(r, "name", None) for r in app.routes]


def _run(code_or_args: list[str], env_extra: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra)
    return subprocess.run([sys.executable, *code_or_args], cwd=DIGITIZER, env=env,
                          capture_output=True, text=True, timeout=120)


def test_the_real_app_mounts_it_last_when_asked(dist):
    """A fresh process, because the choice is read once at import. LAST is the
    claim: the name of the final route, after every API route the module
    registers."""
    r = _run(["-c", "from digitizer_service.app import app; "
                    "names = [getattr(r, 'name', None) for r in app.routes]; "
                    "print(names[-1], names.count('studio'), 'health' in names)"],
             {studio.STUDIO_DIR_ENV: str(dist)})
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.split() == ["studio", "1", "True"]


def test_the_real_app_refuses_to_start_on_a_bad_directory(tmp_path):
    r = _run(["-c", "import digitizer_service.app"], {studio.STUDIO_DIR_ENV: str(tmp_path)})
    assert r.returncode != 0
    assert "is not a built Studio" in r.stderr


def test_the_command_line_names_a_bad_directory_in_one_line(tmp_path):
    r = _run(["-m", "digitizer_service", "--studio", str(tmp_path)], {})
    assert r.returncode == 2
    assert r.stderr.startswith("error: --studio:")
    assert "Traceback" not in r.stderr


def test_the_command_line_really_serves_the_page(dist):
    """The whole path a launcher takes, in a real process on a real port.

    Found by driving it, 2026-11-10: `--studio` printed its URL and `/` was a
    404. `digitizer_service/__init__.py` imports `app`, so under `python -m`
    the app is BUILT before `__main__` has parsed a single flag, and an
    environment variable set there arrives after the one moment `app.py`
    reads it. Every test above passed while that was true: they set the
    variable from outside, which is not what the command line does."""
    import socket
    import time
    import urllib.error
    import urllib.request

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop(studio.STUDIO_DIR_ENV, None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "digitizer_service", "--port", str(port), "--studio", str(dist)],
        cwd=DIGITIZER, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 90
        while True:
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=2) as r:
                    assert r.status == 200
                break
            except (urllib.error.URLError, OSError):
                assert proc.poll() is None, "the service exited before answering /health"
                assert time.monotonic() < deadline, "no /health in 90 s"
                time.sleep(0.25)
        with urllib.request.urlopen(f"{base}/", timeout=5) as r:
            assert r.status == 200
            assert "<title>studio</title>" in r.read().decode("utf-8")
    finally:
        proc.terminate()
        proc.wait(timeout=30)


def test_mounting_twice_adds_one_route(dist):
    app = fastapi.FastAPI()
    studio.mount_studio(app, dist)
    studio.mount_studio(app, dist)
    assert [getattr(r, "name", None) for r in app.routes].count(studio.MOUNT_NAME) == 1
