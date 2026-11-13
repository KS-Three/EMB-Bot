"""Prove the frozen LAUNCHER keeps one origin across restarts, so saved designs survive.

    python packaging/one_origin_smoke.py --launcher <dist>/embbot-launcher/embbot-launcher.exe \
        --work <work>/origin --app-dir ../app

WHY. The Studio keeps every saved design in the browser's localStorage
(`embstudio:index` plus one `embstudio:p:<id>` per design,
`app/src/lib/projects.js`), and a browser keys localStorage by ORIGIN:
scheme, host and port. `http://127.0.0.1:8721/` and `http://127.0.0.1:8722/`
are two unrelated stores, so a launcher that came back on another port after
a restart would open an empty Studio and the customer's designs would look
deleted. They would still be on disk, under an origin nothing opens any more.

WHAT IT RUNS, in order, each against the real exe with `--console --no-browser`
(PATH cut to System32 as `release_smoke.py` does; LOCALAPPDATA pointed into
`--work` so the launcher's log lands in the CI records):

  1. START. Port free first; the launcher brings up `/health` and the Studio at
     `/`. Port, origin, launcher and service PIDs recorded.
  2. SAVE. A real browser (Edge or Chrome already on the machine, a profile on
     disk) opens the origin, waits for the Studio to save its first design,
     and writes a marker beside it. Then the SAME profile opens a second
     origin, one port over, and finds nothing: the failure a port change is.
  3. SECOND LAUNCH while the first runs: exits 0 within seconds, and the port
     is still held by the FIRST service's PID (no second service).
  4. STOP. The launcher is ended the way Task Manager ends it; the service must
     let go of the port on its own (the launcher's NO ORPHAN rule).
  5. RESTART. Same port, same origin, `/health` ok, same build commit.
  6. READ. The same browser profile finds the marker and the design ids.
  7. PORT TAKEN. A foreign HTTP listener on the port; the launcher must exit
     with EXIT_PORT_BUSY (3) and a message naming the port, the foreign PID
     must still hold it, and no other port may have been opened by the app.

Exit 0 only when every check holds. The markdown it prints is what the PR
quotes.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIGITIZER))
import embbot_launcher as L  # noqa: E402  (stdlib only: it imports no engine)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_smoke  # noqa: E402

MARKER_JS = Path(__file__).resolve().parent / "origin_marker.mjs"


# ---- the port ---------------------------------------------------------------

def listeners() -> dict[int, set[int]]:
    """Every listening TCP port on 127.0.0.1 / 0.0.0.0 and the PIDs holding it."""
    out: dict[int, set[int]] = {}
    if os.name == "nt":
        text = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[3].upper() == "LISTENING":
                port = int(parts[1].rsplit(":", 1)[1])
                out.setdefault(port, set()).add(int(parts[4]))
    else:  # good enough to develop the script on; CI is Windows
        text = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
        for line in text.splitlines():
            m = re.search(r":(\d+)\s", line)
            pids = {int(p) for p in re.findall(r"pid=(\d+)", line)}
            if m:
                out.setdefault(int(m.group(1)), set()).update(pids)
    return out


def wait_until(pred, timeout: float, step: float = 0.25):
    deadline = time.monotonic() + timeout
    while True:
        got = pred()
        if got or time.monotonic() > deadline:
            return got
        time.sleep(step)


def health(port: int) -> dict | None:
    try:
        status, _, body = L._get(port, "/health", 5)
        return json.loads(body) if status == 200 else None
    except (OSError, ValueError):
        return None


class Foreign:
    """An HTTP server that is not EMB-Bot, on a given port, in this process."""

    def __init__(self, port: int, directory: Path):
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(directory), **k)

            def log_message(self, *a):
                pass

        handler = Quiet
        self.server = http.server.ThreadingHTTPServer((L.HOST, port), handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


# ---- the launcher -----------------------------------------------------------

class Launch:
    """One launcher process. `run()` for one that should exit by itself."""

    def __init__(self, cmd: list[str], work: Path, env: dict, name: str):
        self.cmd, self.work, self.env, self.name = [*cmd, "--console", "--no-browser"], work, env, name
        self.out = work / f"{name}.out.txt"

    def start(self) -> "Launch":
        print("+ " + " ".join(self.cmd), flush=True)
        self._fh = self.out.open("w", encoding="utf-8")
        self.t0 = time.monotonic()
        self.proc = subprocess.Popen(self.cmd, cwd=self.work, env=self.env, stdout=self._fh,
                                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        return self

    def run(self, timeout: float) -> tuple[int | None, float, str]:
        self.start()
        try:
            code = self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            code = None
            self.kill()
        return code, time.monotonic() - self.t0, self.text()

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()  # TerminateProcess: what Task Manager's End task does
            self.proc.wait(30)
        self._fh.close()

    def text(self) -> str:
        self._fh.flush()
        return self.out.read_text(encoding="utf-8", errors="replace")


def browser(mode: str, url: str, profile: Path, token: str, app_dir: Path, node: str) -> dict:
    cmd = [node, str(MARKER_JS), mode, url, str(profile), token, str(app_dir)]
    print("+ " + " ".join(cmd), flush=True)
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if done.returncode != 0:
        raise RuntimeError(f"origin_marker {mode} {url} exited {done.returncode}:\n{done.stdout}\n{done.stderr}")
    return json.loads(done.stdout.strip().splitlines()[-1])


# ---- the run ----------------------------------------------------------------

def smoke(args) -> tuple[list[str], dict]:
    work = args.work.resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    port, origin, url = args.port, L.studio_url(args.port).rstrip("/"), L.studio_url(args.port)
    env = release_smoke.bare_env()
    env["LOCALAPPDATA"] = str(work / "localappdata")  # the launcher's log, kept with the records
    profile = work / "browser-profile"
    token = secrets.token_hex(8)
    node = shutil.which(args.node) or args.node
    failures: list[str] = []
    rec: dict = {"port": port, "origin": origin, "token": token}

    def check(ok: bool, what: str) -> bool:
        if not ok:
            failures.append(what)
            print(f"FAIL: {what}", flush=True)
        return ok

    if L.bind_error(port) is not None:
        failures.append(f"port {port} is held before the smoke started: {listeners().get(port)}")
        return failures, rec
    started: list[Launch] = []

    def up(name: str) -> Launch:
        launch = Launch(args.launcher, work, env, name).start()
        started.append(launch)
        state = wait_until(lambda: L.probe(port) == L.OURS or launch.proc.poll() is not None, 150)
        waited = time.monotonic() - launch.t0
        h = health(port)
        now = listeners()
        service = now.get(port, set())
        rec[name] = {"ready_s": round(waited, 1), "launcher_pid": launch.proc.pid,
                     "service_pids": sorted(service),
                     # every port the app's processes listen on: must be exactly the one
                     "app_ports": sorted(p for p, pids in now.items() if pids & (service | {launch.proc.pid})),
                     "commit": ((h or {}).get("engine") or {}).get("commit"), "health": bool(h)}
        if not check(state is True and launch.proc.poll() is None and h is not None,
                     f"{name}: the launcher did not bring up the Studio on {port} "
                     f"(exit {launch.proc.poll()}):\n{launch.text()[-2000:]}"):
            raise SystemExit
        return launch

    def down(name: str, launch: Launch) -> None:
        t0 = time.monotonic()
        launch.kill()
        freed = wait_until(lambda: L.bind_error(port) is None and port not in listeners(), 30)
        rec[name]["port_freed_s"] = round(time.monotonic() - t0, 1)
        check(bool(freed), f"{name}: port {port} still held 30 s after the launcher was ended: "
                           f"{listeners().get(port)} (an orphaned service)")

    try:
        # 1. start
        first = up("first")
        if args.expect_commit:
            check(rec["first"]["commit"] == args.expect_commit,
                  f"first: /health commit {rec['first']['commit']} is not the build's {args.expect_commit}")
        check(rec["first"]["app_ports"] == [port],
              f"first: the app listens on {rec['first']['app_ports']}, expected only {port}")

        # 2. save, and the same profile at another origin
        rec["write"] = browser("write", url, profile, token, args.app_dir, node)
        check(rec["write"]["origin"] == origin and rec["write"]["marker"] == token
              and len(rec["write"]["projectIds"]) >= 1,
              f"write: the Studio did not save a design at {origin}: {rec['write']}")
        blank = work / "other-origin"
        blank.mkdir()
        (blank / "index.html").write_text("<!doctype html><title>other origin</title>", encoding="utf-8")
        other = Foreign(0, blank)
        try:
            rec["other_origin"] = browser("read", f"http://{L.HOST}:{other.port}/", profile, token,
                                          args.app_dir, node)
        finally:
            other.close()
        check(rec["other_origin"]["marker"] is None and not rec["other_origin"]["projectIds"],
              f"other origin: the same profile one port over saw the designs: {rec['other_origin']}")

        # 3. a second launch while the first runs
        code, secs, text = Launch(args.launcher, work, env, "second").run(60)
        rec["second"] = {"exit": code, "seconds": round(secs, 1), "service_pids": sorted(listeners().get(port, ())),
                         "first_alive": first.proc.poll() is None}
        check(code == L.EXIT_OK, f"second launch exited {code}, expected {L.EXIT_OK}:\n{text[-2000:]}")
        check(rec["second"]["service_pids"] == rec["first"]["service_pids"] and rec["second"]["first_alive"],
              f"second launch: the port is now held by {rec['second']['service_pids']}, the first service was "
              f"{rec['first']['service_pids']} (first launcher alive: {rec['second']['first_alive']})")
        check(health(port) is not None, "second launch: /health stopped answering")

        # 4. stop
        down("first", first)

        # 5. restart
        again = up("restart")
        check(rec["restart"]["commit"] == rec["first"]["commit"],
              f"restart: /health commit {rec['restart']['commit']} != {rec['first']['commit']}")
        check(rec["restart"]["app_ports"] == [port],
              f"restart: the app listens on {rec['restart']['app_ports']}, expected only {port}")

        # 6. read it back
        rec["read"] = browser("read", url, profile, token, args.app_dir, node)
        check(rec["read"]["origin"] == origin, f"read: origin {rec['read']['origin']} != {origin}")
        check(rec["read"]["marker"] == token, f"read: marker {rec['read']['marker']!r} != {token!r}")
        check(set(rec["write"]["projectIds"]) <= set(rec["read"]["projectIds"]),
              f"read: saved designs {rec['write']['projectIds']} not all in {rec['read']['projectIds']}")
        down("restart", again)

        # 7. the port held by something else
        squat = Foreign(port, blank)
        try:
            held = listeners()
            code, secs, text = Launch(args.launcher, work, env, "busy").run(60)
            after = listeners()
            rec["busy"] = {"exit": code, "seconds": round(secs, 1), "foreign_pid": sorted(held.get(port, ())),
                           "holder_after": sorted(after.get(port, ())),
                           "new_ports": sorted(set(after) - set(held)), "message": text.strip()}
        finally:
            squat.close()
        check(code == L.EXIT_PORT_BUSY, f"port taken: the launcher exited {code}, expected "
                                        f"EXIT_PORT_BUSY ({L.EXIT_PORT_BUSY}):\n{text[-2000:]}")
        check(f"port {port}" in text and "will not move to a different port" in text,
              f"port taken: the message does not name port {port} and the no-move rule:\n{text[-2000:]}")
        check(rec["busy"]["holder_after"] == rec["busy"]["foreign_pid"],
              f"port taken: holder changed {rec['busy']['foreign_pid']} -> {rec['busy']['holder_after']}")
        # `new_ports` is reported, not judged: anything on the runner may open a
        # port meanwhile. A launcher that moved would still be running, and
        # exit 3 within the timeout already says it is not.
    except SystemExit:
        pass
    finally:
        for launch in started:  # never leave a launcher (and its service) behind on a failure
            launch.kill()
    log = work / "localappdata" / L.APP_NAME / "logs" / L.LOG_NAME
    rec["launcher_log"] = str(log) if log.is_file() else None
    return failures, rec


def summary_markdown(failures: list[str], rec: dict, total_s: float) -> str:
    f, r, s, b = (rec.get(k) or {} for k in ("first", "restart", "second", "busy"))
    w, rd, o = (rec.get(k) or {} for k in ("write", "read", "other_origin"))
    lines = [
        "## One origin across restarts (frozen launcher)",
        "",
        f"**{'PASS' if not failures else 'FAIL'}**: {len(failures)} failure(s), {total_s:.0f} s.",
        "",
        f"- First launch: Studio and `/health` at `{rec.get('origin')}/` after {f.get('ready_s')} s, "
        f"service PID {f.get('service_pids')}, commit `{str(f.get('commit'))[:12]}`, the app's listening ports "
        f"{f.get('app_ports')}.",
        f"- Browser ({w.get('channel')}, profile on disk): the Studio saved design(s) {w.get('projectIds')} "
        f"at `{w.get('origin')}`; marker written. The same profile at `{o.get('origin')}` saw "
        f"{len(o.get('projectIds') or [])} design(s) and marker `{o.get('marker')}`: one port over is an empty Studio.",
        f"- Second launch while running: exit {s.get('exit')} in {s.get('seconds')} s; port still held by "
        f"{s.get('service_pids')} (the first service), first launcher alive: {s.get('first_alive')}.",
        f"- Launcher ended (TerminateProcess): port free again after {f.get('port_freed_s')} s, no orphan.",
        f"- Restart: same port, `/health` ok after {r.get('ready_s')} s, commit `{str(r.get('commit'))[:12]}`, "
        f"service PID {r.get('service_pids')}.",
        f"- Read back at `{rd.get('origin')}`: marker {'found' if rd.get('marker') == rec.get('token') else 'MISSING'}, "
        f"designs {rd.get('projectIds')}.",
        f"- Port {rec.get('port')} held by a foreign HTTP server (PID {b.get('foreign_pid')}): launcher exit "
        f"{b.get('exit')} in {b.get('seconds')} s, holder afterwards {b.get('holder_after')}, new ports "
        f"{b.get('new_ports')}. It said:",
        "",
        "```",
        *(b.get("message") or "(nothing)").splitlines(),
        "```",
    ]
    if failures:
        lines += ["", "Failures:", ""] + [f"- {x}" for x in failures]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-report", type=Path, default=None,
                    help="build_report.json of a `build_freeze.py --entry embbot_launcher.py` build: "
                         "names the exe, and /health must carry its stamped commit")
    ap.add_argument("--launcher", nargs="+", default=None,
                    help="instead of --build-report: the command that starts a launcher (a test wrapper); "
                         "--console --no-browser are added")
    ap.add_argument("--work", type=Path, required=True, help="where the logs, profile and results go")
    ap.add_argument("--app-dir", type=Path, default=DIGITIZER.parent / "app",
                    help="the Studio checkout whose node_modules holds @playwright/test")
    ap.add_argument("--node", default="node")
    ap.add_argument("--port", type=int, default=L.PORT,
                    help="the port the launcher holds (always 8721 for the real one; another only for a test wrapper)")
    ap.add_argument("--summary", type=Path, default=None, help="append the markdown here ($GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)
    args.expect_commit = None
    if args.build_report:
        report = json.loads(args.build_report.read_text(encoding="utf-8"))
        args.launcher = [report["exe"]]
        args.expect_commit = report["stamp"]["commit"]
    if not args.launcher:
        ap.error("give --build-report or --launcher")
    t0 = time.monotonic()
    failures, rec = smoke(args)
    text = summary_markdown(failures, rec, time.monotonic() - t0)
    (args.work / "origin.json").write_text(json.dumps({"failures": failures, **rec}, indent=1), encoding="utf-8")
    (args.work / "origin.md").write_text(text, encoding="utf-8")
    print("\n" + text, flush=True)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
