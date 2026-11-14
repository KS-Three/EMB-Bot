"""`embbot_launcher`: the thing a customer double-clicks.

What can go wrong here is all about the one port. The launcher must never
move to another (saved projects are keyed by origin), never start over
something else, never call a lost race a failure, never leave a service behind
it, and never show a traceback. Every test but the two marked REAL runs
against stand-in servers on throwaway ports; those two start the service
itself, because "the command printed a URL and served a 404" is a bug this
repo has already shipped once (`test_service_studio.py`).
"""
from __future__ import annotations

import http.server
import json
import re
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import embbot_launcher as L

DIGITIZER = Path(__file__).resolve().parents[1]
HEALTH = (200, "application/json", json.dumps({"status": "ok", "service": "digitizer"}).encode())
PAGE = (200, "text/html; charset=utf-8", b"<!doctype html><title>studio</title>")
OURS = {"/health": HEALTH, "/": PAGE}
BARE = {"/health": HEALTH}
NOT_A_DIGITIZER = {"/health": (200, "application/json", b'{"service": "printer"}'), "/": PAGE}
NOT_JSON = {"/health": (200, "text/html", b"<h1>router admin</h1>"), "/": PAGE}
NO_HEALTH = {"/": PAGE}


def free_port() -> int:
    with socket.socket() as s:
        s.bind((L.HOST, 0))
        return s.getsockname()[1]


@contextmanager
def serving(routes: dict, port: int = 0):
    """A stand-in for whatever holds the port: `routes` maps a path to
    (status, content type, body); every other path is a 404."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 -- the stdlib's name
            status, kind, body = routes.get(self.path, (404, "text/plain", b"not found"))
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer((L.HOST, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def silent():
    """Something that accepts the connection and never says a word."""
    with socket.socket() as s:
        s.bind((L.HOST, 0))
        s.listen(1)
        yield s.getsockname()[1]


@contextmanager
def held_not_listening():
    """A port another program has bound without listening on it."""
    with socket.socket() as s:
        s.bind((L.HOST, 0))
        yield s.getsockname()[1]


class FakeUI:
    def __init__(self, run=None):
        self.statuses, self.messages, self.ran, self.notes = [], [], [], []
        self.keep_going = True
        self._run = run

    def status(self, text):
        self.statuses.append(text)

    def note(self, text):
        self.notes.append(text)

    def pump(self):
        return self.keep_going

    def message(self, text, error=False):
        self.messages.append((text, error))

    def run(self, url, alive, reopen):
        self.ran.append(url)
        if self._run:
            self._run(url, alive, reopen)

    def close(self):
        pass

    @property
    def errors(self):
        return [text for text, error in self.messages if error]


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    root.mkdir()
    (root / "index.html").write_text("<!doctype html><title>studio</title>", encoding="utf-8")
    return root


@pytest.fixture
def go(tmp_path, dist):
    """`launch` with everything outside the process pinned to the test:
    its own log directory, a browser that only records, short probes."""
    opened = []

    def run(port, ui, **kw):
        kw.setdefault("spawn", never_spawn)
        kw.setdefault("studio", dist)
        studio = kw.pop("studio")
        return L.launch(studio, ui, port=port, log_dir=tmp_path / "logs",
                        browser=lambda url: opened.append(url) or True,
                        probe_timeout=1.0, **kw)

    run.opened = opened
    run.log = tmp_path / "logs" / L.LOG_NAME
    return run


def never_spawn(*args, **kwargs):
    raise AssertionError("the launcher started a service it must not start")


def child(code: str) -> subprocess.Popen:
    """A stand-in service process: `python -c code`, wired as the real one is."""
    return subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


# ---- one port, one address ---------------------------------------------------

def test_the_port_and_the_address_are_fixed():
    """localStorage is keyed by origin: 8722 is an empty Studio, and so is
    `localhost` in place of `127.0.0.1`."""
    assert L.PORT == 8721
    assert L.studio_url() == "http://127.0.0.1:8721/"


def test_the_launcher_has_no_port_option(capsys):
    with pytest.raises(SystemExit) as stop:
        L.main(["--port", "8722"])
    assert stop.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


# ---- who is on the port -------------------------------------------------------

def test_a_closed_port_is_free():
    assert L.probe(free_port(), 1.0) == L.FREE


@pytest.fixture
def slow_refusals(monkeypatch):
    """Windows answers a connect to a closed port with a refusal after TWO
    SECONDS (two SYN retransmissions; 2.03 s median on Kent's laptop,
    2026-11-13), where Linux takes microseconds. This is that machine, on any
    machine: a connect whose timeout is shorter than the delay times out, one
    that waits long enough is refused. Nothing real is connected."""
    delay = 2.0

    def connect(self, address):
        timeout = self.gettimeout()
        if timeout is not None and timeout < delay:
            time.sleep(timeout)
            raise TimeoutError("timed out")
        time.sleep(delay)
        raise ConnectionRefusedError(10061, "No connection could be made because the target machine actively refused it")

    monkeypatch.setattr(socket.socket, "connect", connect)


def test_a_slow_refusal_is_still_a_free_port(slow_refusals):
    """The 2026-11-13 bug: a 1 s probe timeout against a 2 s refusal read an
    empty port as "something that will not answer" (FOREIGN), so five tests
    failed on a Windows laptop and passed on every runner that refuses at
    once. A timeout on a port the bind can take is a refusal that has not
    arrived yet."""
    started = time.monotonic()
    assert L.probe(free_port(), 0.3) == L.FREE
    assert time.monotonic() - started < 1.5, "the probe waited out the refusal"


def test_a_slow_refusal_does_not_hide_a_port_that_is_held(slow_refusals):
    """The same timeout on a port the bind CANNOT take is still no answer."""
    with held_not_listening() as port:
        assert L.probe(port, 0.3) == L.FOREIGN


def test_a_refusal_is_free_however_long_it_took(slow_refusals):
    """A refused connection is FREE whatever the timeout: here it arrives
    after 2 s, inside a 5 s allowance."""
    assert L.probe(free_port(), 5.0) == L.FREE


def test_the_probe_asks_for_a_fast_refusal(monkeypatch):
    asked = []
    monkeypatch.setattr(L, "fast_refusal", lambda sock: asked.append(sock) or True)
    assert L.probe(free_port(), 1.0) == L.FREE
    assert len(asked) == 1


def test_fast_refusal_never_raises():
    with socket.socket() as s:
        assert isinstance(L.fast_refusal(s), bool)
    s = socket.socket()
    s.close()  # a dead handle: the call must say False, not raise
    assert L.fast_refusal(s) is False


@pytest.mark.skipif(sys.platform != "win32", reason="the two-second refusal is Windows' own")
def test_real_windows_refuses_a_closed_port_at_once():
    """The cause itself, measured not simulated: with `fast_refusal` the
    reset comes back in milliseconds instead of after two SYN retries, and a
    port that IS listening still answers."""
    started = time.monotonic()
    assert L.probe(free_port(), 5.0) == L.FREE
    assert time.monotonic() - started < 1.0
    with serving(OURS) as port:
        assert L.probe(port, 1.0) == L.OURS


@pytest.mark.parametrize("routes, state", [
    (OURS, L.OURS),
    (BARE, L.BARE),
    (NOT_A_DIGITIZER, L.FOREIGN),
    (NOT_JSON, L.FOREIGN),
    (NO_HEALTH, L.FOREIGN),
])
def test_health_says_who_holds_the_port(routes, state):
    with serving(routes) as port:
        assert L.probe(port, 1.0) == state


def test_something_that_never_answers_is_not_ours():
    with silent() as port:
        assert L.probe(port, 0.3) == L.FOREIGN


def test_the_probe_does_not_go_through_the_machines_proxy(monkeypatch):
    """`urllib` would: it reads these variables (and, on Windows, the
    registry's proxy), and a proxy cannot reach this machine's loopback. The
    launcher would then wait out its whole timeout on a service that was up."""
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    with serving(OURS) as port:
        assert L.probe(port, 1.0) == L.OURS


def test_a_slow_answer_is_asked_again_before_it_is_called_foreign(monkeypatch):
    answers = [L.FOREIGN, L.OURS]
    monkeypatch.setattr(L, "probe", lambda port, timeout: answers.pop(0))
    assert L.identify(1, 0.1) == L.OURS
    asked = []
    monkeypatch.setattr(L, "probe", lambda port, timeout: asked.append(port) or L.FOREIGN)
    assert L.identify(1, 0.1) == L.FOREIGN
    assert len(asked) == 3


def test_a_port_held_without_listening_looks_free_and_cannot_be_bound():
    """Why the bind decides and not `/health`: nothing answers here, so a
    request calls the port free, and the service would die on its bind."""
    assert L.bind_error(free_port()) is None
    with held_not_listening() as port:
        assert L.probe(port, 1.0) == L.FREE
        assert isinstance(L.bind_error(port), OSError)
    with serving(OURS) as port:
        assert isinstance(L.bind_error(port), OSError)


def test_a_free_port_is_decided_by_the_bind_not_by_a_request(go, monkeypatch):
    """A refused connection takes seconds on Windows. If "free" waited on it,
    a timeout would read as "another program has the port" on a machine where
    nothing does, and the app would never start."""
    def no_requests(*args):
        raise AssertionError("the launcher asked /health about a port it could bind")

    monkeypatch.setattr(L, "identify", no_requests)
    ui = FakeUI()
    ui.keep_going = False  # as far as "starting", then quit
    started = []

    def spawn(studio, port, env):
        started.append(child("import time; time.sleep(120)"))
        return started[0]

    assert go(free_port(), ui, spawn=spawn) == L.EXIT_OK
    assert len(started) == 1 and ui.errors == []


# ---- the busy port ------------------------------------------------------------

def test_our_own_running_instance_is_reused(go):
    """A second double-click opens the browser at the first one's Studio."""
    ui = FakeUI()
    with serving(OURS) as port:
        assert go(port, ui) == L.EXIT_OK
    assert go.opened == [L.studio_url(port)]
    assert ui.messages == [] and ui.statuses == [] and ui.ran == []


def test_a_second_launch_says_in_one_line_that_it_reused_the_running_instance(go, capsys):
    """`--console` prints one line saying nothing new started; the window says
    nothing (its Open-in-browser is the whole experience)."""
    ui = FakeUI()
    with serving(OURS) as port:
        assert go(port, ui) == L.EXIT_OK
    (line,) = ui.notes
    assert "already running" in line and L.studio_url(port) in line and "\n" not in line
    assert ui.messages == [] and ui.statuses == []
    L.ConsoleUI().note(line)
    assert capsys.readouterr().out == line + "\n"


def test_the_window_stays_quiet_on_a_second_launch():
    assert L.WindowUI.note(object(), "already running") is None  # no widget is touched


def test_the_busy_port_message_reaches_a_windowed_user_as_a_message_box(monkeypatch):
    """Two routes, both pinned. The window (the build has tkinter) shows the
    error in a message box; a build with no tkinter and no stdout (windowed,
    nothing to print to) hands the same text to Windows' own message box."""
    shown = []
    ui = object.__new__(L.WindowUI)
    ui.root = type("Root", (), {"withdraw": lambda self: None})()
    ui._messagebox = type("Box", (), {
        "showerror": staticmethod(lambda title, text: shown.append(("error", title, text))),
        "showinfo": staticmethod(lambda title, text: shown.append(("info", title, text)))})()
    text = L.port_busy_message(8721, L.FOREIGN, "C:/log")
    ui.message(text, error=True)
    assert shown == [("error", "EMB-Bot", text)] and "port 8721" in text

    boxes = []
    monkeypatch.setattr(L, "_windows_message_box", lambda t, error: boxes.append((t, error)))
    monkeypatch.setattr(L.sys, "platform", "win32")
    monkeypatch.setattr(L.sys, "stderr", None)
    L.ConsoleUI().message(text, error=True)
    assert boxes == [(text, True)]


def test_a_foreign_process_on_the_port_exits_3_with_the_message_for_both_uis(go):
    ui = FakeUI()
    with serving(NOT_A_DIGITIZER) as port:
        assert go(port, ui) == L.EXIT_PORT_BUSY
    (text,) = ui.errors
    assert f"port {port}" in text and "will not move to a different port" in text
    assert ui.notes == [], "a refusal is a message, not the reuse note"


@pytest.mark.parametrize("routes, says", [
    (NOT_A_DIGITIZER, "another program on this computer is already using port"),
    (NO_HEALTH, "another program on this computer is already using port"),
    (BARE, "it is not serving the Studio"),
])
def test_a_port_someone_else_holds_stops_the_launch_with_its_name(go, routes, says):
    ui = FakeUI()
    with serving(routes) as port:
        assert go(port, ui) == L.EXIT_PORT_BUSY
    (text,) = ui.errors
    assert says in text and f"port {port}" in text
    assert "will not move to a different port" in text
    assert str(go.log) in text and "Traceback" not in text
    assert go.opened == []
    assert f"port {port} is" in go.log.read_text(encoding="utf-8")


def test_a_port_that_cannot_be_bound_stops_the_launch_with_its_name(go):
    ui = FakeUI()
    with held_not_listening() as port:
        assert go(port, ui) == L.EXIT_PORT_BUSY
    (text,) = ui.errors
    assert f"port {port} is not available on this computer" in text
    assert "will not move to a different port" in text and str(go.log) in text
    assert go.opened == []


# ---- starting -----------------------------------------------------------------

def test_missing_studio_files_are_named(go, tmp_path):
    ui = FakeUI()
    assert go(free_port(), ui, studio=tmp_path / "nowhere") == L.EXIT_STUDIO_MISSING
    (text,) = ui.errors
    assert "Studio files are missing" in text and str(tmp_path / "nowhere") in text


def test_a_service_that_dies_starting_is_a_sentence_and_a_log_path(go):
    """The traceback belongs in the log. The user gets what happened and
    where the detail is."""
    ui = FakeUI()
    code = ("import sys; sys.stderr.write('Traceback (most recent call last):\\n"
            "ImportError: DLL load failed while importing cv2\\n'); sys.exit(7)")
    assert go(free_port(), ui, spawn=lambda s, p, env: child(code)) == L.EXIT_START_FAILED
    (text,) = ui.errors
    assert "could not start" in text and "exit code 7" in text
    assert f"Log file: {go.log}" in text
    assert "Traceback" not in text and "ImportError" not in text
    assert "DLL load failed while importing cv2" in go.log.read_text(encoding="utf-8")
    assert go.opened == [] and ui.ran == []


def test_a_service_that_never_answers_is_stopped_and_reported(go):
    ui = FakeUI()
    started = []

    def spawn(studio, port, env):
        started.append(child("import time; time.sleep(120)"))
        return started[0]

    assert go(free_port(), ui, spawn=spawn, start_timeout=0.6) == L.EXIT_START_FAILED
    (text,) = ui.errors
    assert "was not ready after 1 seconds" in text and str(go.log) in text
    assert started[0].poll() is not None, "the service that never came up was left running"


def test_losing_the_race_to_another_launcher_is_not_a_failure(go, monkeypatch):
    """Two double-clicks: both launchers saw the port free, the other one's
    service took the bind, ours exited. The Studio is up; say nothing."""
    ui = FakeUI()
    port = free_port()
    # The race, replayed: the port WAS free when this launcher tried it, and
    # the other service is on it by the time ours binds.
    monkeypatch.setattr(L, "bind_error", lambda port: None)
    with serving(OURS, port):
        code = go(port, ui, spawn=lambda s, p, env: child("raise SystemExit(1)"))
    assert code == L.EXIT_OK
    assert ui.errors == [] and go.opened == [L.studio_url(port)]


def test_quit_while_starting_stops_the_service(go):
    ui = FakeUI()
    ui.keep_going = False
    started = []

    def spawn(studio, port, env):
        started.append(child("import time; time.sleep(120)"))
        return started[0]

    assert go(free_port(), ui, spawn=spawn) == L.EXIT_OK
    assert ui.messages == [] and started[0].poll() is not None


def test_an_error_nobody_planned_for_is_a_sentence_too(go):
    ui = FakeUI()

    def spawn(*args):
        raise RuntimeError("the disk is on fire")

    assert go(free_port(), ui, spawn=spawn) == L.EXIT_START_FAILED
    (text,) = ui.errors
    assert "did not expect" in text and str(go.log) in text and "Traceback" not in text
    logged = go.log.read_text(encoding="utf-8")
    assert "Traceback" in logged and "the disk is on fire" in logged


# ---- running ------------------------------------------------------------------

def _held_by_stand_in(port, routes=OURS):
    """A `spawn` whose "service" is a stand-in server in this process plus a
    child that lives until it is killed, and the handle to stop each."""
    stack = {}

    def spawn(studio, p, env):
        stack["server"] = serving(routes, port)
        stack["server"].__enter__()
        stack["child"] = child("import sys; sys.stdin.read()")
        return stack["child"]

    return spawn, stack


def test_a_service_that_dies_while_running_is_reported(go):
    port = free_port()
    spawn, stack = _held_by_stand_in(port)

    def crash(url, alive, reopen):
        assert alive()
        stack["server"].__exit__(None, None, None)
        stack["child"].kill()
        stack["child"].wait(30)
        assert not alive()

    ui = FakeUI(run=crash)
    assert go(port, ui, spawn=spawn) == L.EXIT_STOPPED
    (text,) = ui.errors
    assert "has stopped unexpectedly" in text and str(go.log) in text


def test_stepping_aside_when_another_instance_owns_the_port(go):
    """The other half of the race: `/health` answered, but it was the OTHER
    launcher's service, and ours then lost the bind. Not a crash."""
    port = free_port()
    spawn, stack = _held_by_stand_in(port)

    def lose(url, alive, reopen):
        stack["child"].kill()
        stack["child"].wait(30)

    ui = FakeUI(run=lose)
    try:
        assert go(port, ui, spawn=spawn) == L.EXIT_OK
    finally:
        stack["server"].__exit__(None, None, None)
    assert ui.errors == []


def test_a_browser_that_will_not_open_leaves_the_address_on_screen(tmp_path, dist):
    ui = FakeUI()
    with serving(OURS) as port:
        assert L.launch(dist, ui, port=port, log_dir=tmp_path, browser=lambda url: False,
                        spawn=never_spawn, probe_timeout=1.0) == L.EXIT_OK
    ((text, error),) = ui.messages
    assert L.studio_url(port) in text and not error


# ---- the pieces ---------------------------------------------------------------

def test_bundled_tessdata_reaches_the_service(tmp_path, go):
    data = tmp_path / "tessdata"
    data.mkdir()
    assert L.service_env(data, {"PATH": "x"})["TESSDATA_PREFIX"] == str(data)
    # A folder that is not there must not hide a Tesseract the machine has.
    absent = L.service_env(tmp_path / "nope", {"TESSDATA_PREFIX": "/usr/share/tessdata"})
    assert absent["TESSDATA_PREFIX"] == "/usr/share/tessdata"
    assert "TESSDATA_PREFIX" not in L.service_env(None, {})
    # ...and `launch` hands that environment to the process it starts.
    seen = {}

    def spawn(studio, port, env):
        seen.update(env)
        return child("raise SystemExit(1)")

    go(free_port(), FakeUI(), spawn=spawn, tessdata=data)
    assert seen["TESSDATA_PREFIX"] == str(data) and seen[L.PIPE_ENV] == "1"


def test_the_service_command_is_this_program_with_serve(dist):
    cmd = L.service_command(dist, 8721)
    assert cmd[:2] == [sys.executable, str(DIGITIZER / "embbot_launcher.py")]
    assert cmd[2:] == ["--serve", "--studio", str(dist), "--port", "8721"]


def test_serve_alone_serves_the_bundled_studio_with_the_bundled_ocr(tmp_path, monkeypatch):
    """`<exe> --serve --port N` is how the release smoke and the installer
    check start the shipped exe: no --studio, and a scrubbed environment with
    no TESSDATA_PREFIX. Frozen, both come from the bundle."""
    (tmp_path / "studio").mkdir()
    (tmp_path / "studio" / "index.html").write_text("<div id=app></div>", encoding="utf-8")
    (tmp_path / "tessdata").mkdir()
    monkeypatch.setattr(L.sys, "_MEIPASS", str(tmp_path), raising=False)
    env = {"TESSDATA_PREFIX": "/somewhere/else"}
    L.bundled_tessdata_wins(env)
    assert env["TESSDATA_PREFIX"] == str(tmp_path / "tessdata")
    assert L.default_studio() == tmp_path / "studio"
    seen = {}
    monkeypatch.setenv("TESSDATA_PREFIX", "/somewhere/else")
    monkeypatch.delenv(L.PIPE_ENV, raising=False)
    fake_main = type(sys)("digitizer_service.__main__")
    fake_main.main = lambda: seen.update(argv=list(sys.argv), tess=L.os.environ["TESSDATA_PREFIX"])
    monkeypatch.setitem(sys.modules, "digitizer_service.__main__", fake_main)
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    L.serve(["--port", "8799"])
    assert seen["argv"] == ["digitizer_service", "--studio", str(tmp_path / "studio"), "--port", "8799"]
    assert seen["tess"] == str(tmp_path / "tessdata")


def test_serve_outside_a_frozen_build_leaves_tessdata_alone(monkeypatch):
    monkeypatch.delattr(L.sys, "_MEIPASS", raising=False)
    env = {"TESSDATA_PREFIX": "/usr/share/tessdata"}
    L.bundled_tessdata_wins(env)
    assert env == {"TESSDATA_PREFIX": "/usr/share/tessdata"}


def test_the_log_lives_in_a_per_user_directory(tmp_path):
    win = L.user_log_dir({"LOCALAPPDATA": str(tmp_path)}, "win32")
    assert win == tmp_path / "EMB-Bot" / "logs"
    linux = L.user_log_dir({"XDG_STATE_HOME": str(tmp_path)}, "linux")
    assert linux == tmp_path / "emb-bot" / "logs"
    for platform in ("win32", "darwin", "linux"):
        assert Path.home() in L.user_log_dir({}, platform).parents


def test_a_log_that_cannot_be_opened_does_not_stop_the_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(L.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    blocker = tmp_path / "a-file"
    blocker.write_text("not a directory", encoding="utf-8")
    log = L.Log(blocker / "logs")
    try:
        assert log.path == tmp_path / "tmp" / "EMB-Bot" / L.LOG_NAME
        log.write("still written somewhere")
    finally:
        log.close()
    assert "still written somewhere" in log.path.read_text(encoding="utf-8")


def test_the_log_is_appended_to_and_bounded(tmp_path):
    for line in ("first launch", "second launch"):
        log = L.Log(tmp_path)
        log.write(line)
        log.close()
    assert [ln.split("launcher: ")[1] for ln in (tmp_path / L.LOG_NAME).read_text().splitlines()] == [
        "first launch", "second launch"]
    (tmp_path / L.LOG_NAME).write_bytes(b"x" * (L.LOG_MAX_BYTES + 1))
    log = L.Log(tmp_path)
    log.write("after the big one")
    log.close()
    assert (tmp_path / "emb-bot.previous.log").stat().st_size == L.LOG_MAX_BYTES + 1
    assert (tmp_path / L.LOG_NAME).stat().st_size < 200


def test_one_long_session_cannot_fill_the_disk(tmp_path, monkeypatch):
    """The service logs every request, and nothing restarts the launcher of
    an app that is left open for a month."""
    monkeypatch.setattr(L, "LOG_MAX_BYTES", 2000)
    log = L.Log(tmp_path)
    for n in range(400):
        log.write(f'INFO: 127.0.0.1 - "GET /jobs/{n} HTTP/1.1" 200 OK', "service")
    log.write("the last line")
    log.close()
    sizes = sorted(p.stat().st_size for p in tmp_path.iterdir())
    assert len(sizes) == 2 and max(sizes) < 2200, sizes
    assert "the last line" in (tmp_path / L.LOG_NAME).read_text(encoding="utf-8")


def _launcher_lines(path: Path) -> list[str]:
    return [ln.split(" launcher: ", 1)[1] for ln in path.read_text(encoding="utf-8").splitlines()
            if " launcher: " in ln]


def test_a_new_instance_logs_started_with_version_port_and_time_to_ready_then_stopped(go):
    port = free_port()
    spawn, stack = _held_by_stand_in(port)
    try:
        assert go(port, FakeUI(), spawn=spawn, version="v9.9") == L.EXIT_OK
    finally:
        stack["server"].__exit__(None, None, None)
    lines = _launcher_lines(go.log)
    (started,) = [ln for ln in lines if ln.startswith("started:")]
    assert re.fullmatch(rf"started: EMB-Bot v9\.9, port {port}, ready in \d+\.\d s, new instance, "
                        r"service pid \d+", started), started
    stopped = lines[-1]
    assert re.fullmatch(r"stopped: EMB-Bot v9\.9, exit code 0, up \d+\.\d s", stopped), stopped
    assert lines.index(started) < lines.index("quit") < len(lines) - 1


def test_a_second_launch_logs_that_it_reused_the_running_instance(go):
    with serving(OURS) as port:
        assert go(port, FakeUI(), version="v9.9") == L.EXIT_OK
    lines = _launcher_lines(go.log)
    (started,) = [ln for ln in lines if ln.startswith("started:")]
    assert f"port {port}" in started and "reused the running instance" in started
    assert "new instance" not in started and "service started" not in " ".join(lines)
    assert lines[-1].startswith("stopped: EMB-Bot v9.9, exit code 0")


def test_a_launch_that_failed_logs_stopped_with_its_exit_code_and_no_started(go):
    with serving(NOT_A_DIGITIZER) as port:
        assert go(port, FakeUI()) == L.EXIT_PORT_BUSY
    lines = _launcher_lines(go.log)
    assert not any(ln.startswith("started:") for ln in lines)
    assert lines[-1].startswith(f"stopped: EMB-Bot ") and f"exit code {L.EXIT_PORT_BUSY}" in lines[-1]


def test_the_log_is_appended_to_across_launches_and_the_service_output_stays_in_it(go):
    """Kept from #1419: what the service prints still lands in the file,
    between this launch's started and stopped lines, after the previous one's."""
    port = free_port()
    spawn, stack = _held_by_stand_in(port)
    try:
        go(port, FakeUI(), spawn=spawn)
    finally:
        stack["server"].__exit__(None, None, None)
    with serving(OURS) as other:
        go(other, FakeUI())
    text = go.log.read_text(encoding="utf-8")
    assert text.count("launcher: started:") == 2 and text.count("launcher: stopped:") == 2
    assert text.index("launcher: stopped:") < text.rindex("launcher: started:")


def test_the_log_stays_under_its_cap_across_many_launches(go, monkeypatch):
    """Launch after launch, the file is moved aside past the cap and kept
    once: never more than two files, each within about one cap."""
    monkeypatch.setattr(L, "LOG_MAX_BYTES", 600)
    with serving(OURS) as port:
        for _ in range(40):
            go(port, FakeUI())
    files = sorted(go.log.parent.iterdir())
    assert [f.name for f in files] == ["emb-bot.log", "emb-bot.previous.log"]
    assert all(f.stat().st_size < 600 + 400 for f in files), [f.stat().st_size for f in files]
    assert _launcher_lines(go.log)[-1].startswith("stopped:"), "the newest launch is in the live file"


def test_the_version_is_the_stamp_the_build_wrote(tmp_path):
    assert L.app_version(tmp_path) == "checkout"                      # no stamp
    (tmp_path / "build_stamp.json").write_text(
        json.dumps({"commit": "a" * 40, "release": "v1.2"}), encoding="utf-8")
    assert L.app_version(tmp_path) == "v1.2"
    (tmp_path / "build_stamp.json").write_text(json.dumps({"commit": "b" * 40}), encoding="utf-8")
    assert L.app_version(tmp_path) == "b" * 40
    (tmp_path / "build_stamp.json").write_text("not json", encoding="utf-8")
    assert L.app_version(tmp_path) == "checkout"
    assert L.app_version() == "checkout"                              # not frozen


def test_a_gui_build_attaches_the_terminal_for_console(monkeypatch):
    """The frozen exe has no console subsystem, so `--console` asks for the
    terminal that started it, and leaves a redirected stdout alone."""
    monkeypatch.setattr(L.sys, "platform", "linux")
    assert L.attach_console() is False                                # not Windows: nothing to do
    monkeypatch.setattr(L.sys, "platform", "win32")
    monkeypatch.setattr(L.sys, "stdout", object())
    monkeypatch.setattr(L.sys, "stderr", object())
    assert L.attach_console() is False                                # redirected: kept as it is


@pytest.mark.skipif(sys.platform != "win32", reason="AttachConsole is Windows")
def test_real_attach_console_without_a_terminal_opens_one_and_prints_to_it(tmp_path):
    """A GUI-subsystem process (pythonw) asked for a console gets stdout back."""
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        pytest.skip("no pythonw.exe beside this interpreter")
    out = tmp_path / "out.txt"
    script = tmp_path / "probe.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(DIGITIZER)!r})\n"
        "import embbot_launcher as L\n"
        "sys.stdout = sys.stderr = None  # what a GUI exe has when no shell redirected it\n"
        "ok = L.attach_console()\n"
        "print('reached the terminal', flush=True)\n"
        f"open({str(out)!r}, 'w').write(f'{{ok}} {{sys.stdout is not None}} {{sys.stderr is not None}}')\n",
        encoding="utf-8")
    # DETACHED_PROCESS: no parent console, so this takes the AllocConsole route.
    subprocess.run([str(pythonw), str(script)], timeout=60, stdin=subprocess.DEVNULL,
                   creationflags=0x00000008)
    assert out.read_text(encoding="utf-8") == "True True True"


def test_no_window_means_the_console(monkeypatch):
    def no_display():
        raise RuntimeError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(L, "WindowUI", no_display)
    assert isinstance(L.make_ui(), L.ConsoleUI)
    monkeypatch.setattr(L, "WindowUI", never_spawn)
    assert isinstance(L.make_ui(console=True), L.ConsoleUI)


def test_the_window_shows_status_and_quits():
    """Runs wherever tkinter has a display (Kent's machine; a Linux session
    under xvfb). CI has neither, and the launch logic above does not need it."""
    pytest.importorskip("tkinter")
    try:
        ui = L.WindowUI()
    except Exception as exc:  # noqa: BLE001 -- TclError: no display
        pytest.skip(f"no display for a window: {exc}")
    try:
        assert ui.root.state() == "withdrawn"
        ui.status("Starting EMB-Bot...")
        assert ui.root.state() == "normal" and ui.pump()
        reopened = []
        ui.root.after(50, lambda: ui._open.invoke())
        ui.root.after(150, ui._on_quit)
        ui.run(L.studio_url(), lambda: True, lambda: reopened.append(1))
        assert reopened == [1] and not ui.pump()
        # A service that is already gone must not leave the window waiting.
        ui._quit = False
        ui.run(L.studio_url(), lambda: False, lambda: None)
    finally:
        ui.close()


# ---- the pipe watcher and the silent start ---------------------------------------

def _watcher_child(body: str) -> subprocess.Popen:
    """A real child that starts the production pipe watcher, then runs `body`,
    with the launcher's end of its stdin pipe held open here."""
    code = ("import sys, time; sys.path.insert(0, sys.argv[1]); "
            "import embbot_launcher as L; L._exit_when_launcher_goes(); time.sleep(0.3)\n" + body)
    return subprocess.Popen([sys.executable, "-c", code, str(DIGITIZER)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def test_the_pipe_watcher_does_not_stop_numpy_loading():
    """The 2026-11-12 hang. With a thread parked in a read on the stdin pipe,
    loading `libscipy_openblas64` (any `import numpy`) never returned on
    Kent's Windows laptop: the service printed nothing, never bound its port,
    and the launcher stopped it after 120 s. `import numpy` takes about half a
    second with no watcher. The child prints once the import is done, and the
    pipe stays open the whole time, as it does under the launcher."""
    pytest.importorskip("numpy", reason="numpy not installed")
    child = _watcher_child("import numpy; print('imported', flush=True); time.sleep(60)")
    try:
        got = {}
        reader = threading.Thread(target=lambda: got.setdefault("line", child.stdout.readline()),
                                  daemon=True)
        reader.start()
        reader.join(60)
        assert got.get("line", b"").strip() == b"imported", (
            "importing numpy with the launcher's pipe open did not finish in 60 s")
    finally:
        child.kill()
        child.stdin.close()
        child.stdout.close()


def test_the_pipe_watcher_ends_the_child_when_the_launcher_goes():
    child = _watcher_child("time.sleep(60)")
    try:
        time.sleep(0.5)
        assert child.poll() is None, "the watcher ended the child while the pipe was still open"
        child.stdin.close()  # what the OS does when the launcher dies, however it dies
        assert child.wait(15) == 0
    finally:
        if child.poll() is None:
            child.kill()
        child.stdout.close()


def test_a_service_that_is_still_silent_dumps_every_threads_stack(tmp_path):
    """A service stuck loading a DLL printed nothing, so the log held only the
    launcher's own two lines. Past `after` seconds with nothing listening it
    now writes where each thread is."""
    import io

    out = io.StringIO()
    _dump = L._dump_stacks_if_slow(free_port(), after=1.0, out=out)
    _dump.join(10)
    text = out.getvalue()
    assert "not listening" in text and "Thread" in text and "most recent call first" in text


def test_a_service_that_is_listening_in_time_dumps_nothing():
    import io

    out = io.StringIO()
    with silent() as port:
        L._dump_stacks_if_slow(port, after=1.0, out=out).join(10)
    assert out.getvalue() == ""


# ---- REAL: the service itself ---------------------------------------------------

def test_real_the_launcher_starts_the_service_and_stops_it(go):
    """The whole path on a real port: the Studio at `/`, `/health` from the
    same origin, the browser sent to it once, and nothing left on the port."""
    pytest.importorskip("fastapi", reason="service extra not installed")
    port = free_port()
    seen = {}

    def look(url, alive, reopen):
        assert alive()
        seen["page"] = L._get(port, "/", 10)
        seen["health"] = L._get(port, "/health", 10)

    ui = FakeUI(run=look)
    code = go(port, ui, spawn=L.start_service)
    logged = go.log.read_text(encoding="utf-8")
    assert code == L.EXIT_OK, f"{ui.messages}\n{logged[-3000:]}"
    status, kind, body = seen["page"]
    assert status == 200 and kind.startswith("text/html") and b"<title>studio</title>" in body
    assert json.loads(seen["health"][2])["service"] == "digitizer"
    assert go.opened == [L.studio_url(port)] and ui.ran == [L.studio_url(port)]
    assert ui.statuses == ["Starting EMB-Bot..."] and ui.messages == []
    assert L.probe(port, 1.0) == L.FREE, "the service outlived the launcher's quit"
    assert f"Studio: {L.studio_url(port)}" in logged and "service stopped" in logged


def test_real_a_service_that_refuses_to_start_exits_with_its_own_code(tmp_path):
    """The pipe watcher must not change HOW the service fails. Its first
    version sat in `sys.stdin.buffer.read()`, and a service that exited while
    it was parked there aborted in interpreter shutdown: exit code -6 and a
    "Fatal Python error" in the log where exit 2 and one line belonged
    (found by driving the window, 2026-11-12)."""
    pytest.importorskip("fastapi", reason="service extra not installed")
    out = tmp_path / "service.out"
    # `Popen`, not `run`: `run` closes stdin at once, which IS the signal that
    # the launcher has gone, and the service would exit 0 for that reason.
    with open(out, "w", encoding="utf-8") as sink:
        service = subprocess.Popen(
            L.service_command(tmp_path / "nowhere", free_port()), env=L.service_env(),
            stdin=subprocess.PIPE, stdout=sink, stderr=subprocess.STDOUT)
        try:
            code = service.wait(120)
        finally:
            service.kill()
            service.stdin.close()
    said = out.read_text(encoding="utf-8")
    assert code == 2, said[-2000:]
    assert "error: --studio:" in said and "Fatal Python error" not in said


def test_real_the_service_does_not_outlive_a_killed_launcher(tmp_path, dist):
    """Task Manager, a crash, a logoff: the launcher gets no chance to stop
    anything. A service left behind would be reused by the next launch, with
    no window to quit it from."""
    pytest.importorskip("fastapi", reason="service extra not installed")
    port = free_port()
    code = ("import sys, embbot_launcher as L; "
            "sys.exit(L.launch(sys.argv[1], L.ConsoleUI(), port=int(sys.argv[2]), "
            "log_dir=sys.argv[3], browser=lambda url: True))")
    log_path = tmp_path / "logs" / L.LOG_NAME
    launcher = subprocess.Popen([sys.executable, "-c", code, str(dist), str(port), str(tmp_path / "logs")],
                                cwd=DIGITIZER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def said() -> str:
        return log_path.read_text(encoding="utf-8", errors="replace")[-3000:] if log_path.exists() else ""

    def wait_for(state, seconds, what):
        deadline = time.monotonic() + seconds
        while L.probe(port, 1.0) != state:
            assert time.monotonic() < deadline, f"{what}:\n{said()}"
            time.sleep(0.25)

    try:
        wait_for(L.OURS, 120, "the launcher's service never answered")
        launcher.kill()
        launcher.wait(30)
        wait_for(L.FREE, 30, "the service is still on the port after its launcher was killed")
    finally:
        if launcher.poll() is None:
            launcher.kill()
        # Belt and braces for a FAILING run: do not leave a service behind.
        # The WHOLE log, not `said()`'s tail: thirty seconds of probing is
        # 14 kB of access lines, and the pid is on line two.
        whole = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        pid = re.search(r"service started, pid (\d+)", whole)
        if pid and L.probe(port, 1.0) != L.FREE:
            import os
            import signal

            try:
                os.kill(int(pid.group(1)), signal.SIGTERM)
            except OSError:
                pass
