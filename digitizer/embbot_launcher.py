"""The EMB-Bot launcher: what a customer double-clicks.

Step 3 of `docs/packaging-freeze-spike-2026-11-10.md`. It starts the digitizer
service with the built Studio mounted, waits for `/health`, opens the browser,
and stays up as the thing the customer quits. Run it from a checkout with

    digitizer/.venv/bin/python digitizer/embbot_launcher.py [--console]

Standard library only, ON PURPOSE. `import digitizer_service` builds the whole
app (cv2, scipy: about 3 s, and a missing DLL is an ImportError). That happens
in a CHILD process whose output goes to the log, so the launcher is still
standing to say "could not start, here is the log" when the engine is not.

The rules, each pinned in `tests/test_launcher.py`:

  - ONE PORT, 8721, and one address, `http://127.0.0.1:8721/`. Saved projects
    live in the browser's localStorage, keyed by origin. Port 8722 is a
    different, empty Studio, and so is `http://localhost:8721/`. There is no
    `--port` on the launcher and no "next free port".
  - PORT BUSY. A trial bind says whether it is; `/health` says who holds it.
    Our own Studio: open the browser at it and exit (a second double-click is
    not an error). Anything else: stop with a message naming the port.
    Nothing on the port is ever killed.
  - THE PORT IS THE LOCK. Two launchers started together both find it free and
    both start a service; one service loses the bind and exits. Its launcher
    then finds our Studio on the port and steps aside instead of reporting a
    failure.
  - NO ORPHAN. The service holds a pipe from the launcher and exits when it
    closes, which the OS does however the launcher ends (Quit, Task Manager,
    a crash). Without it a killed launcher leaves a service the next launch
    would reuse and nobody could quit.
  - PROBES GO STRAIGHT TO LOOPBACK. `urllib` honours the machine's proxy
    settings (on Windows, the registry's), and a proxy cannot reach this
    machine's 127.0.0.1; `http.client` asks no one.

FROZEN LAYOUT the build script has to produce (PyInstaller, this file as the
entry point): the built Studio at `<bundle>/studio` (`--add-data
"<app/dist>;studio"`) and Tesseract's data at `<bundle>/tessdata`, where
`<bundle>` is `sys._MEIPASS`. The frozen exe starts ITSELF with `--serve` as
the service, so there is one exe to build. The window needs `tkinter`; with
none (or `--console`) it prints to the terminal instead.

Windows-only pieces, none of which the logic above depends on: the log
directory (`user_log_dir`), `CREATE_NO_WINDOW` on the child, the message
box used when there is neither a window toolkit nor a console, and
`attach_console`.

NO CONSOLE WINDOW. The frozen exe is built for the Windows GUI subsystem
(`--windowed` in `packaging/build_freeze.py`). Built `--console` it got a
console window of its own on every double-click, which stayed open behind the
browser for as long as the app ran; the service child already had none
(`CREATE_NO_WINDOW`). A GUI exe has no stdout when started from a terminal,
so `--console` asks `attach_console` for the terminal that started it.

THE LOG, one file, appended across launches: a "started" line when the app is
up (version, port, time to ready, new or reused instance) and a "stopped" line
on the way out. It is moved aside at `LOG_MAX_BYTES` and kept once, so the
two files together never pass about twice that.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

APP_NAME = "EMB-Bot"
HOST = "127.0.0.1"
#: The only port. See ONE PORT above before adding a way to change it.
PORT = 8721

EXIT_OK = 0
EXIT_STUDIO_MISSING = 2
EXIT_PORT_BUSY = 3
EXIT_START_FAILED = 4
EXIT_STOPPED = 5

#: Launch to first `/health` measured about 3.5 s frozen on Kent's laptop
#: (the spike doc). A first run on a slow disk with a virus scanner reading
#: 430 new files is the case this allows for.
START_TIMEOUT_S = 120.0
PROBE_TIMEOUT_S = 3.0
LOG_NAME = "emb-bot.log"
LOG_MAX_BYTES = 1 << 20
#: Set for the child the launcher starts: "exit when your stdin closes".
PIPE_ENV = "EMBBOT_LAUNCHER_PIPE"

# What holds the port.
FREE = "free"        # connection refused: nothing is listening
OURS = "ours"        # a digitizer that also serves the Studio at /
BARE = "bare"        # a digitizer with no Studio (a developer's service)
FOREIGN = "foreign"  # something else, or something that will not answer


def studio_url(port: int = PORT) -> str:
    return f"http://{HOST}:{port}/"


# ---- who is on the port -----------------------------------------------------

#: Winsock's `SIO_TCP_INITIAL_RTO` (Windows 10 1607 and later).
_SIO_TCP_INITIAL_RTO = 0x98000011


def fast_refusal(sock: socket.socket) -> bool:
    """Windows: make a refused connect on `sock` fail at once, not after two
    SYN retransmissions. A closed loopback port answers with a reset, and
    Windows reads a reset to a SYN as possibly spurious and tries again twice:
    `connect` to a port nobody listens on took 2.03 s (median of 20, any
    address, `127.0.0.1` included) and `localhost` took 4.07 s, measured
    2026-11-13 on Kent's laptop. Asking for no retransmission brings it to
    15 ms and changes nothing for a port that is listening. Best effort: False
    where the call does not exist (not Windows, an old Windows), and then a
    refusal is merely slow, which `probe` copes with."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        # TCP_INITIAL_RTO_PARAMETERS { USHORT Rtt; UCHAR MaxSynRetransmissions; }:
        # TCP_INITIAL_RTO_UNSPECIFIED_RTT, TCP_INITIAL_RTO_NO_SYN_RETRANSMISSIONS.
        params = ctypes.create_string_buffer(struct.pack("HBx", 0xFFFF, 0xFE))
        ws2 = ctypes.WinDLL("ws2_32")
        ws2.WSAIoctl.argtypes = [ctypes.c_size_t, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                 ctypes.c_void_p, ctypes.c_void_p]
        ws2.WSAIoctl.restype = ctypes.c_int
        returned = wintypes.DWORD(0)
        return ws2.WSAIoctl(sock.fileno(), _SIO_TCP_INITIAL_RTO, params, len(params.raw), None, 0,
                            ctypes.byref(returned), None, None) == 0
    except Exception:  # noqa: BLE001 -- an optimisation, never a reason to fail a probe
        return False


class _LoopbackConnection(http.client.HTTPConnection):
    """`HTTPConnection` whose connect asks `fast_refusal` first. The address is
    already a literal IPv4 one, so there is no name to resolve."""

    def connect(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            fast_refusal(sock)
            sock.connect((self.host, self.port))
        except BaseException:
            sock.close()
            raise
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = sock


def _get(port: int, path: str, timeout: float) -> tuple[int, str, bytes]:
    conn = _LoopbackConnection(HOST, port, timeout=timeout)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        return r.status, r.getheader("content-type") or "", r.read(4 << 20)
    finally:
        conn.close()


def probe(port: int = PORT, timeout: float = PROBE_TIMEOUT_S) -> str:
    """FREE, OURS, BARE or FOREIGN. Asks 127.0.0.1 by number: that is the
    address the service binds, and on Windows `localhost` can resolve to ::1
    first, where nothing is listening (the 2026-08-26 `start-emb-bot.ps1`
    fix was this same mistake in the other direction).

    A refused connection means FREE however long it took. A timeout does not
    say that, but it does not say FOREIGN either when the connect was a
    refusal that was merely slow (2 s on Windows without `fast_refusal`, over
    a 1 s timeout): nothing holds the port then, and the bind says so."""
    try:
        status, _, body = _get(port, "/health", timeout)
    except ConnectionRefusedError:
        return FREE
    except (OSError, http.client.HTTPException) as exc:
        if isinstance(exc, TimeoutError) and bind_error(port) is None:
            return FREE
        return FOREIGN
    try:
        health = json.loads(body) if status == 200 else None
    except ValueError:
        health = None
    if not (isinstance(health, dict) and health.get("service") == "digitizer"):
        return FOREIGN
    try:
        status, kind, _ = _get(port, "/", timeout)
    except (OSError, http.client.HTTPException):
        return BARE
    return OURS if status == 200 and kind.startswith("text/html") else BARE


def identify(port: int = PORT, timeout: float = PROBE_TIMEOUT_S, tries: int = 3) -> str:
    """`probe`, asked again before settling on FOREIGN: our own service that
    was slow to answer once must not be reported as another program."""
    for attempt in range(tries):
        state = probe(port, timeout)
        if state != FOREIGN:
            return state
        if attempt + 1 < tries:
            time.sleep(0.2)
    return FOREIGN


def bind_error(port: int = PORT) -> OSError | None:
    """Why the service could not bind the port, or None when it can. This, not
    `probe`, decides that the port is free: it is the very thing the service
    is about to do, it answers at once on every platform, and it sees what no
    request can: a port held by something that is not listening, and a port
    Windows has reserved (Hyper-V and WSL exclude ranges; the bind then fails
    with "access forbidden" while nothing at all is listening)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "posix":
            # What asyncio (so uvicorn) sets on POSIX and not on Windows.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port))
    except OSError as exc:
        return exc
    finally:
        s.close()
    return None


# ---- the log ----------------------------------------------------------------

def user_log_dir(env=None, platform: str | None = None) -> Path:
    """The per-user directory the log goes in. Never beside the program: an
    installed app's own folder is not writable by the person running it."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    if platform == "win32":
        base = env.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / APP_NAME / "logs"
    if platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    base = env.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / "emb-bot" / "logs"


class Log:
    """One file holding the launcher's own lines and everything the service
    prints. Appended to across launches (three failed starts in a row is
    something support wants to see); past 1 MB the old file is kept once as
    `emb-bot.previous.log`. A log that cannot be opened is never the reason
    the app does not start: `handle` is then None and `path` says so.

    The service does NOT get this file as its stdout. Windows has no append
    mode on a handle (the C runtime seeks before each of its OWN writes), so a
    child writing through an inherited handle writes at its own position, over
    whatever a second launcher appended meanwhile. Its output comes back
    through a pipe (`follow`) and every byte is written from here."""

    def __init__(self, directory: Path):
        self.handle = None
        self.path: Path | None = None
        self._lock = threading.Lock()
        self._size = 0
        for folder in (Path(directory), Path(tempfile.gettempdir()) / APP_NAME):
            try:
                folder.mkdir(parents=True, exist_ok=True)
                self._open(folder / LOG_NAME)
            except OSError:
                continue
            return

    def _open(self, path: Path) -> None:
        """Open `path` for appending, first moving a file past the limit
        aside. Called at start and again whenever this session's own writing
        passes the limit: the service logs every request, and an app left
        running for a month must not fill a disk."""
        try:
            self._size = path.stat().st_size
        except OSError:
            self._size = 0  # no file yet
        if self._size > LOG_MAX_BYTES:
            try:
                os.replace(path, path.with_name("emb-bot.previous.log"))
            except OSError:
                pass  # another launcher has it open (Windows): try again a megabyte on
            self._size = 0
        self.handle = open(path, "a", encoding="utf-8", errors="replace", buffering=1)
        self.path = path

    def write(self, text: str, who: str = "launcher") -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            if self.handle is None:
                return
            for line in str(text).splitlines() or [""]:
                self._size += self.handle.write(f"{stamp} {who}: {line}\n")
            if self._size > LOG_MAX_BYTES:
                self.handle.close()
                self.handle = None
                try:
                    self._open(self.path)
                except OSError:
                    pass  # no log from here on; never a reason to stop the app

    def follow(self, stream) -> threading.Thread:
        """Copy a child's output into the log, a line at a time, until the
        child closes it. Runs even with no file open: an unread pipe fills,
        and the service would block on its own logging."""
        def copy() -> None:
            for raw in stream:
                self.write(raw.decode("utf-8", "replace").rstrip("\r\n"), "service")

        thread = threading.Thread(target=copy, name="service-log", daemon=True)
        thread.start()
        return thread

    def close(self) -> None:
        with self._lock:
            if self.handle is not None:
                self.handle.close()
                self.handle = None


# ---- what the user is told --------------------------------------------------
# Plain ASCII: a Windows console on an OEM code page raises on a curly quote.

def _log_line(log_path) -> str:
    return f"\n\nLog file: {log_path}" if log_path else ""


def port_busy_message(port: int, state: str, log_path=None) -> str:
    if state == BARE:
        who = (f"a digitizer service is already running on port {port}, but it is not "
               "serving the Studio (a developer's service started without --studio)")
        fix = f"Stop that service, then open {APP_NAME} again."
    else:
        who = f"another program on this computer is already using port {port}"
        fix = f"Close the other program, or restart the computer, then open {APP_NAME} again."
    return (f"{APP_NAME} could not start: {who}.\n\n"
            f"{APP_NAME} always uses port {port}, because your saved designs are tied to it. "
            "It will not move to a different port, so your designs are where you left them.\n\n"
            f"{fix}{_log_line(log_path)}")


def port_unavailable_message(port: int, error: OSError, log_path=None) -> str:
    return (f"{APP_NAME} could not start: port {port} is not available on this computer "
            f"({error.strerror or error}).\n\n"
            f"{APP_NAME} always uses port {port}, because your saved designs are tied to it. "
            "It will not move to a different port, so your designs are where you left them.\n\n"
            f"Restart the computer, then open {APP_NAME} again.{_log_line(log_path)}")


def start_failed_message(code, log_path=None) -> str:
    return (f"{APP_NAME} could not start: its service stopped while starting up "
            f"(exit code {code}).\n\nWhat went wrong is written in the log file."
            f"{_log_line(log_path)}")


def start_timeout_message(seconds: float, log_path=None) -> str:
    return (f"{APP_NAME} could not start: its service was not ready after "
            f"{seconds:.0f} seconds, so it was stopped.\n\n"
            f"Open {APP_NAME} again. If this keeps happening, the log file says why."
            f"{_log_line(log_path)}")


def stopped_message(code, log_path=None) -> str:
    return (f"{APP_NAME} has stopped unexpectedly (exit code {code}).\n\n"
            f"Open {APP_NAME} again to carry on.{_log_line(log_path)}")


def studio_missing_message(studio, log_path=None) -> str:
    fix = (f"Install {APP_NAME} again." if getattr(sys, "frozen", False)
           else "Build it with: cd app && npm run build")
    return (f"{APP_NAME} could not start: its Studio files are missing from\n{studio}\n\n"
            f"{fix}{_log_line(log_path)}")


def unexpected_message(log_path=None) -> str:
    return (f"{APP_NAME} ran into a problem it did not expect and has stopped.\n\n"
            f"What went wrong is written in the log file.{_log_line(log_path)}")


# ---- the service, as a child process ----------------------------------------

def bundled(name: str) -> Path | None:
    """`<bundle>/<name>` inside a frozen build, else None."""
    root = getattr(sys, "_MEIPASS", None)
    return Path(root) / name if root else None


def default_studio() -> Path:
    return bundled("studio") or Path(__file__).resolve().parents[1] / "app" / "dist"


def app_version(root=None) -> str:
    """What the log calls this build: the release the build stamped (a tag, or
    `dev-<commit>`; `build_stamp.json` beside the code), else "checkout"."""
    root = root if root is not None else getattr(sys, "_MEIPASS", None)
    if root:
        try:
            stamp = json.loads((Path(root) / "build_stamp.json").read_text(encoding="utf-8"))
            for key in ("release", "commit"):
                if isinstance(stamp.get(key), str) and stamp[key]:
                    return stamp[key][:40]
        except (OSError, ValueError, AttributeError):
            pass
    return "checkout"


def service_command(studio, port: int = PORT) -> list[str]:
    """This same program with `--serve`: the frozen exe when frozen, this file
    under the running interpreter otherwise."""
    me = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
    return [*me, "--serve", "--studio", str(studio), "--port", str(port)]


def service_env(tessdata=None, base=None) -> dict:
    """The child's environment. `TESSDATA_PREFIX` is the first place
    `digitizer_core.ocr.tessdata_dir()` looks, so bundled data needs no
    Tesseract install; a folder that is not there is not named."""
    env = dict(os.environ if base is None else base)
    if tessdata and Path(tessdata).is_dir():
        env["TESSDATA_PREFIX"] = str(tessdata)
    env[PIPE_ENV] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def start_service(studio, port: int, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        service_command(studio, port), env=env, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        # Windows: no second console window for the service.
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def stop_service(child: subprocess.Popen, wait: float = 10.0) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(wait)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(wait)
    if child.stdin is not None:
        try:
            child.stdin.close()
        except OSError:
            pass


#: How often the Windows watcher asks whether the launcher's end is still open.
PIPE_POLL_S = 0.5


def _watch_blocking(fd: int) -> None:
    """POSIX: park in a read; it returns b"" the moment the launcher is gone."""
    # `os.read`, not `sys.stdin.buffer.read()`: a daemon thread parked
    # inside the buffered reader holds its lock, and an interpreter that
    # then exits (an ImportError in the service) aborts on that lock,
    # turning exit code 1 into a core dump (-6, seen 2026-11-12).
    try:
        while os.read(fd, 4096):
            pass
    except OSError:
        return
    os._exit(0)


def _watch_polling(fd: int, interval: float = PIPE_POLL_S) -> None:
    """Windows: ask the pipe, never wait on it. A thread parked in a read on
    the stdin pipe stops the main thread loading `libscipy_openblas64` (so
    every `import numpy`): the service printed nothing, never bound its port,
    and the launcher gave up after 120 s (measured 2026-11-12 on Kent's
    laptop: `import numpy` 0.45 s with no watcher, over 20 s with one; the
    DLL's own load hangs, nothing of ours is involved). `PeekNamedPipe`
    returns at once and fails with ERROR_BROKEN_PIPE once the launcher's end
    has closed, which is the same signal."""
    import ctypes
    import msvcrt
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                  wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD]
    k32.PeekNamedPipe.restype = wintypes.BOOL
    k32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                             wintypes.LPDWORD, wintypes.LPVOID]
    k32.ReadFile.restype = wintypes.BOOL
    broken = 109  # ERROR_BROKEN_PIPE
    try:
        handle = msvcrt.get_osfhandle(fd)
    except OSError:
        return
    sink = ctypes.create_string_buffer(4096)
    while True:
        available = wintypes.DWORD(0)
        if not k32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None):
            if ctypes.get_last_error() == broken:
                os._exit(0)
            return  # not a pipe (a file, a console): there is nothing to watch
        if available.value:
            got = wintypes.DWORD(0)  # something was written: drain it, it never blocks
            k32.ReadFile(handle, sink, min(available.value, len(sink)), ctypes.byref(got), None)
            continue
        time.sleep(interval)


def _exit_when_launcher_goes() -> None:
    """In the child: stdin is a pipe only the launcher holds the other end of.
    It reads as closed when the launcher is gone, by any route."""
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, OSError, ValueError):
        return  # no stdin at all (a windowed exe started by hand)

    target = _watch_polling if sys.platform == "win32" else _watch_blocking
    threading.Thread(target=target, args=(fd,), name="launcher-pipe", daemon=True).start()


#: The child writes every thread's stack to its own output when it is still not
#: listening this long after it began. Shorter than START_TIMEOUT_S, so the
#: stack is in the log BEFORE the launcher stops the service and says "not
#: ready". Without it a service stuck loading a DLL says nothing at all, and
#: the log held only the launcher's two lines (the 2026-11-12 hang).
SLOW_START_DUMP_S = START_TIMEOUT_S - 20.0


def _dump_stacks_if_slow(port: int, after: float = SLOW_START_DUMP_S, out=None) -> threading.Thread:
    import faulthandler

    def watch() -> None:
        deadline = time.monotonic() + after
        while time.monotonic() < deadline:
            try:
                socket.create_connection((HOST, port), 0.5).close()
                return  # listening: nothing to report
            except OSError:
                time.sleep(0.5)
        stream = out or sys.stderr
        print(f"service not listening on port {port} after {after:.0f} s; stacks of every thread:",
              file=stream, flush=True)
        try:
            faulthandler.dump_traceback(file=stream, all_threads=True)
        except (OSError, ValueError, AttributeError):  # a stream with no file descriptor
            for ident, frame in sys._current_frames().items():
                print(f"Thread {ident:#x} (most recent call first):", file=stream)
                print("".join(traceback.format_stack(frame)[::-1]), file=stream)
        stream.flush()

    thread = threading.Thread(target=watch, name="slow-start-dump", daemon=True)
    thread.start()
    return thread


def bundled_tessdata_wins(env=None) -> None:
    """In a frozen build, point `TESSDATA_PREFIX` at the bundled data, over
    whatever the machine set: the shipped app's OCR is its own, as the
    launcher's `service_env` already makes it for the child it starts. This
    covers `<exe> --serve` started directly, which is how the release smoke
    and the installer check start the shipped exe on a port of their own."""
    env = os.environ if env is None else env
    data = bundled("tessdata")
    if data is not None and data.is_dir():
        env["TESSDATA_PREFIX"] = str(data)


def serve(argv: list[str]) -> None:
    """The child: `python -m digitizer_service --studio DIR --port N`, by
    calling that command's own `main` (the route its tests cover; setting the
    environment variable alone once printed a URL and served a 404).
    `--studio` defaults to the bundled Studio (or app/dist in a checkout), so
    `<exe> --serve --port N` is the whole command for a check that wants the
    shipped service on a port other than 8721."""
    ap = argparse.ArgumentParser(prog="embbot_launcher --serve")
    ap.add_argument("--studio", default=None)
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)
    if args.studio is None:
        args.studio = str(default_studio())
    bundled_tessdata_wins()
    for name in ("stdout", "stderr"):
        # A windowed exe started with no handles has None here, and uvicorn's
        # log setup calls `sys.stderr.isatty()`.
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    if os.environ.get(PIPE_ENV):
        _exit_when_launcher_goes()
        _dump_stacks_if_slow(args.port)
    sys.argv = ["digitizer_service", "--studio", args.studio, "--port", str(args.port)]
    from digitizer_service.__main__ import main as service_main

    service_main()


# ---- what the user sees -----------------------------------------------------

def _windows_message_box(text: str, error: bool) -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x10 if error else 0x40)


def attach_console() -> bool:
    """Windows, GUI-subsystem exe asked for `--console`: give `sys.stdout` and
    `sys.stderr` a terminal to write to. A GUI exe started from a terminal
    has no standard handles (they are None), unless the shell redirected them
    to a file or a pipe, which is left alone. First the terminal that started
    this process; with none (started from an icon or a shortcut), a console
    of its own, because `--console` is the request for one. Best effort:
    False when there was nothing to do or it could not be done."""
    if sys.platform != "win32":
        return False
    wanted = [n for n in ("stdout", "stderr") if getattr(sys, n) is None]
    if not wanted:
        return False
    try:
        import ctypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not k32.AttachConsole(-1) and not k32.AllocConsole():  # ATTACH_PARENT_PROCESS
            return False
        for name in wanted:
            setattr(sys, name, open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1))
        return True
    except Exception:  # noqa: BLE001 -- the terminal is a convenience, never a reason to fail
        return False


class ConsoleUI:
    """Lines in a terminal. Ctrl+C, or closing the terminal, quits."""

    def status(self, text: str) -> None:
        print(text, flush=True)

    def note(self, text: str) -> None:
        """A line that is only for someone watching a terminal: the window
        has nothing to add to the app opening in the browser."""
        print(text, flush=True)

    def pump(self) -> bool:
        return True

    def message(self, text: str, error: bool = False) -> None:
        stream = sys.stderr if error else sys.stdout
        if stream is None and sys.platform == "win32":
            _windows_message_box(text, error)  # a windowed build with no tkinter
        else:
            print(text, file=stream, flush=True)

    def run(self, url: str, alive, reopen) -> None:
        print(f"{APP_NAME} is running at {url}\nPress Ctrl+C, or close this window, to quit.", flush=True)
        try:
            while alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    def close(self) -> None:
        pass


class WindowUI:
    """A small window: what is happening, Open, Quit. Constructing it raises
    when there is no tkinter or no display; `make_ui` then uses the console.
    It stays hidden until there is something to say, so a second launch that
    only opens the browser never flashes a window."""

    def __init__(self) -> None:
        import tkinter
        from tkinter import messagebox

        self._messagebox = messagebox
        self._quit = False
        self.root = root = tkinter.Tk()
        root.withdraw()
        root.title(APP_NAME)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._text = tkinter.StringVar(master=root)
        tkinter.Label(root, textvariable=self._text, justify="left", wraplength=380,
                      padx=24, pady=18).pack()
        row = tkinter.Frame(root)
        row.pack(pady=(0, 16))
        self._open = tkinter.Button(row, text=f"Open {APP_NAME}", width=16, state="disabled")
        self._open.pack(side="left", padx=6)
        tkinter.Button(row, text="Quit", width=10, command=self._on_quit).pack(side="left", padx=6)

    def _on_quit(self) -> None:
        self._quit = True
        self.root.quit()

    def status(self, text: str) -> None:
        self._text.set(text)
        self.root.deiconify()
        self.pump()

    def note(self, text: str) -> None:
        pass  # a second launch just brings the app up; the window stays hidden

    def pump(self) -> bool:
        """Let the window draw and take clicks; False once Quit was pressed."""
        self.root.update()
        return not self._quit

    def message(self, text: str, error: bool = False) -> None:
        self.root.withdraw()
        (self._messagebox.showerror if error else self._messagebox.showinfo)(APP_NAME, text)

    def run(self, url: str, alive, reopen) -> None:
        self._open.config(state="normal", command=reopen)
        self.status(f"{APP_NAME} is running. It opened in your browser at\n{url}\n\n"
                    f"Keep this window open while you work. Quit closes {APP_NAME}.")

        def watch() -> None:
            if not alive():
                self.root.quit()
            else:
                self.root.after(500, watch)

        watch()
        # `quit()` before `mainloop()` is forgotten by Tk, hence the flag.
        if not self._quit and alive():
            self.root.mainloop()

    def close(self) -> None:
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001 -- already gone
            pass


def make_ui(console: bool = False):
    if not console:
        try:
            return WindowUI()
        except Exception:  # noqa: BLE001 -- ImportError, or TclError with no display
            pass
    return ConsoleUI()


# ---- the launch -------------------------------------------------------------

def launch(studio, ui, *, port: int = PORT, tessdata=None, log_dir=None,
           browser=webbrowser.open, spawn=start_service,
           start_timeout: float = START_TIMEOUT_S,
           probe_timeout: float = PROBE_TIMEOUT_S, version: str | None = None) -> int:
    """Start (or find) the app, hold it until the user quits, return the exit
    code. `port` is a parameter for the tests alone; `main` never passes it.
    Every launch ends in one "stopped" line, whatever the way out was."""
    log = Log(Path(log_dir) if log_dir else user_log_dir())
    version = app_version() if version is None else version
    began = time.monotonic()
    code = EXIT_START_FAILED
    try:
        code = _launch(studio, ui, log, port=port, tessdata=tessdata, browser=browser,
                       spawn=spawn, start_timeout=start_timeout, probe_timeout=probe_timeout,
                       version=version, began=began)
        return code
    finally:
        log.write(f"stopped: {APP_NAME} {version}, exit code {code}, "
                  f"up {time.monotonic() - began:.1f} s")
        log.close()


def _launch(studio, ui, log, *, port, tessdata, browser, spawn, start_timeout,
            probe_timeout, version, began) -> int:
    url = studio_url(port)

    def started(how: str) -> None:
        log.write(f"started: {APP_NAME} {version}, port {port}, ready in "
                  f"{time.monotonic() - began:.1f} s, {how}")

    def reuse(why: str) -> None:
        """A second launch: the running app comes up in the browser. A window
        stays hidden; a terminal is told, in one line, that nothing new started."""
        started("reused the running instance")
        ui.note(f"{APP_NAME} is already running; opened it in your browser at {url}")
        show(why)

    def fail(code: int, text: str) -> int:
        log.write(" ".join(text.split()))
        ui.message(text, error=True)
        return code

    def show(reason: str) -> None:
        log.write(f"{reason}; opening {url}")
        try:
            opened = browser(url)
        except Exception as exc:  # noqa: BLE001 -- whatever a browser hook raises
            log.write(f"browser: {exc!r}")
            opened = False
        if not opened:
            ui.message(f"{APP_NAME} is running. Open this address in your browser:\n{url}")

    child = copying = None

    def settle() -> None:
        """Stop the service and get its last output into the log. Called
        before any message that sends the user to the log, and on the way out;
        a second call does nothing."""
        nonlocal child
        if child is None:
            return
        stop_service(child)
        if copying is not None:
            copying.join(5)
        log.write(f"service stopped (exit code {child.returncode})")
        child = None

    try:
        # WHETHER the port can be had is the bind's answer; `/health` is only
        # asked WHO has it. A refused connection is slow on Windows (2 s, where
        # Linux answers at once; `fast_refusal` shortens it), and "free" must
        # not hang on a timeout.
        refused = bind_error(port)
        state = FREE if refused is None else identify(port, probe_timeout)
        log.write(f"port {port} is {state}" + (f" (bind: {refused!r})" if refused else ""))
        if state == OURS:
            reuse("already running")
            return EXIT_OK
        if state != FREE:
            return fail(EXIT_PORT_BUSY, port_busy_message(port, state, log.path))
        if refused is not None:  # held by nothing that listens, or reserved
            return fail(EXIT_PORT_BUSY, port_unavailable_message(port, refused, log.path))
        if not (Path(studio) / "index.html").is_file():
            return fail(EXIT_STUDIO_MISSING, studio_missing_message(studio, log.path))

        ui.status(f"Starting {APP_NAME}...")
        child = spawn(studio, port, service_env(tessdata))
        if child.stdout is not None:
            copying = log.follow(child.stdout)
        log.write(f"service started, pid {child.pid}")
        deadline = time.monotonic() + start_timeout
        while True:
            code = child.poll()
            if code is not None:
                # THE PORT IS THE LOCK: another launcher's service may have
                # taken the bind this one lost.
                if probe(port, probe_timeout) == OURS:
                    reuse(f"service exited ({code}) but another instance is serving")
                    return EXIT_OK
                settle()  # its last words are in the log before the user is sent there
                return fail(EXIT_START_FAILED, start_failed_message(code, log.path))
            if probe(port, probe_timeout) == OURS:
                break
            if time.monotonic() > deadline:
                settle()  # "it was stopped" is true before the message says so
                return fail(EXIT_START_FAILED, start_timeout_message(start_timeout, log.path))
            if not ui.pump():
                log.write("quit while starting")
                return EXIT_OK
            time.sleep(0.25)

        started(f"new instance, service pid {child.pid}")
        show("ready")
        ui.run(url, lambda: child.poll() is None, lambda: show("reopened"))
        code = child.poll()
        if code is None:
            log.write("quit")
            return EXIT_OK
        if probe(port, probe_timeout) == OURS:
            log.write(f"service exited ({code}); another instance owns the port, stepping aside")
            return EXIT_OK
        return fail(EXIT_STOPPED, stopped_message(code, log.path))
    except KeyboardInterrupt:
        log.write("interrupted")
        return EXIT_OK
    except Exception:  # noqa: BLE001 -- the user gets a sentence, the log gets the traceback
        log.write(traceback.format_exc())
        settle()
        ui.message(unexpected_message(log.path), error=True)
        return EXIT_START_FAILED
    finally:
        settle()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--serve"]:
        serve(argv[1:])
        return EXIT_OK
    if {"--console", "-h", "--help"} & set(argv):
        attach_console()  # before argparse prints anything: a GUI exe has no stdout of its own
    ap = argparse.ArgumentParser(
        prog="embbot_launcher",
        description=f"Start {APP_NAME} on {studio_url()} and open it in the browser.")
    ap.add_argument("--studio", metavar="DIR", default=None,
                    help="the built Studio to serve (default: the bundled one, or app/dist in a checkout)")
    ap.add_argument("--console", action="store_true",
                    help="no window: print to this terminal, Ctrl+C quits")
    ap.add_argument("--no-browser", action="store_true",
                    help="start and hold the service without opening a browser")
    args = ap.parse_args(argv)
    ui = make_ui(args.console)
    try:
        return launch(
            Path(args.studio).expanduser().resolve() if args.studio else default_studio(),
            ui, tessdata=bundled("tessdata"),
            browser=(lambda url: True) if args.no_browser else webbrowser.open)
    finally:
        ui.close()


if __name__ == "__main__":
    raise SystemExit(main())
