"""Is a digitize slower the second time, or after a Cancel? (2026-11-13)

The 2026-11-12 build walkthrough (`docs/build-walkthrough-2026-11-12.md`,
"What did not work" item 5) timed one artwork at 12-15 s, then 44 s "right
after a Cancel", on a laptop running two other digitize jobs. This tool
separates the candidate causes with measurements against a service it starts
itself on its own port.

Two halves, one file:

  --serve PORT LOG   the probe service: the real `digitizer_service.app`, with
                     `digitizer_core.deadline.check` wrapped to write a line per
                     stage-label change per thread (monotonic wall clock AND
                     that thread's CPU time) to LOG, plus the start and end of
                     every queued job's work. Nothing in the pipeline changes:
                     `check` still does exactly what it did, the wrapper only
                     records when it was called.
  (default)          the client: starts the probe, then per repetition runs
                     A  digitize (cold: bytes never seen),
                     A' the identical request again (the job cache),
                     B  digitize again (cold: same pixels, new bytes),
                     X  digitize + Cancel mid-run,
                     C  the cancelled request resubmitted at once (what the
                        Studio does), queue wait and run time split,
                     R  digitize with a /recount of other bytes in flight,
                     Xe/Ce  as X/C, but cancelled early, inside stages 0-4,
                        so no generation is cached for Ce,
                     K  digitize while --load-procs other processes run the
                        same full digitize (`--load`): contention on purpose,
                     and writes one JSON record per run as it goes (arms are
                     picked with --arms; Xe and K are not in the default).
  --load IMAGE W     the K arm's background load, looping until killed.

"Cold, same pixels, new bytes": a PNG text chunk keyed by run name changes the
sha256 the caches key on and nothing the decoder hands the pipeline, so every
cold run does identical work.

Usage (repo's digitizer/ folder, Kent's laptop):
  .venv/Scripts/python -m tools.second_digitize_timing --image testdata/x.png \
      --width 96 --reps 3 --port 8799 --out <dir>
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import zlib
from pathlib import Path

# --------------------------------------------------------------------------
# probe service


def serve(port: int, log_path: str) -> None:
    from digitizer_core import deadline
    import digitizer_service.app  # noqa: F401
    svc = sys.modules["digitizer_service.app"]
    from digitizer_service.jobs import JobRegistry
    import uvicorn

    fh = open(log_path, "a", buffering=1, encoding="utf-8")
    lock = threading.Lock()
    last: dict[int, str] = {}

    def emit(rec: dict) -> None:
        rec["t"] = round(time.monotonic(), 4)
        rec["cpu"] = round(time.thread_time(), 4)
        rec["pcpu"] = round(time.process_time(), 4)   # every thread of the probe
        rec["th"] = threading.current_thread().name
        with lock:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")

    real_check = deadline.check

    def check(stage: str) -> None:
        tid = threading.get_ident()
        if last.get(tid) != stage:
            last[tid] = stage
            emit({"ev": "chk", "s": stage})
        try:
            real_check(stage)
        except deadline.Abandoned:
            emit({"ev": "abandon", "s": stage})
            raise

    deadline.check = check

    real_submit = JobRegistry.submit

    def submit(self, key, work):
        tag = key[:12]

        def wrapped():
            last.pop(threading.get_ident(), None)
            emit({"ev": "work_start", "key": tag})
            ok = False
            try:
                out = work()
                ok = True
                return out
            finally:
                emit({"ev": "work_end", "key": tag, "ok": ok})

        job, cached = real_submit(self, key, wrapped)
        emit({"ev": "submit", "key": tag, "job": job.id, "cached": cached})
        return job, cached

    JobRegistry.submit = submit

    @svc.app.get("/_probe")
    def _probe() -> dict:
        """Is anything still running? The probe's process CPU clock, its
        live threads, and the registry's in-flight count."""
        return {"t": time.monotonic(), "pcpu": time.process_time(),
                "threads": sorted(t.name for t in threading.enumerate()),
                "jobs": svc.registry.stats()}

    # The route must come before the Studio/static catch-alls, if any.
    svc.app.router.routes.insert(0, svc.app.router.routes.pop())
    import digitizer_core
    emit({"ev": "start", "core": digitizer_core.__file__, "pid": os.getpid()})
    uvicorn.run(svc.app, host="127.0.0.1", port=port, log_level="warning")


def load(image: str, width: float) -> None:
    """The contention arm's background load: the same full digitize the
    service runs (stages 0-7 + preflight), in its own process, in a loop until
    the client terminates it. Stands in for "two other digitize jobs"."""
    import digitizer_service.app  # noqa: F401
    svc = sys.modules["digitizer_service.app"]
    data = Path(image).read_bytes()
    pixels = svc._decode_bounded(data)
    while True:
        cfg = svc.PipelineConfig(target_width_mm=width)
        gen = svc.build_generation(pixels, cfg, exif_source=data)
        result = svc.finish_generation(gen.fork(), cfg)
        plan = svc.plan_stitches(result, cfg)
        svc.run_preflight(result, plan, cfg, image=pixels)


# --------------------------------------------------------------------------
# client


def png_variant(png: bytes, tag: str) -> bytes:
    """`png` with a tEXt chunk after IHDR: new sha256, same pixels."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "PNG only"
    ihdr_end = 8 + 4 + 4 + 13 + 4
    body = b"Comment\x00" + tag.encode()
    chunk = struct.pack(">I", len(body)) + b"tEXt" + body
    chunk += struct.pack(">I", zlib.crc32(b"tEXt" + body) & 0xFFFFFFFF)
    return png[:ihdr_end] + chunk + png[ihdr_end:]


def _form(fields: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    b = "----x" + uuid.uuid4().hex
    out = bytearray()
    for name, (fname, data, ctype) in fields.items():
        out += f"--{b}\r\n".encode()
        disp = f'form-data; name="{name}"' + (f'; filename="{fname}"' if fname else "")
        out += f"Content-Disposition: {disp}\r\n".encode()
        if ctype:
            out += f"Content-Type: {ctype}\r\n".encode()
        out += b"\r\n" + data + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


class Client:
    def __init__(self, port: int):
        self.base = f"http://127.0.0.1:{port}"

    def _req(self, method: str, path: str, body: bytes | None = None,
             ctype: str | None = None, timeout: float = 900) -> dict:
        req = urllib.request.Request(self.base + path, data=body, method=method)
        if ctype:
            req.add_header("Content-Type", ctype)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def post_art(self, path: str, img: bytes, cfg: dict) -> dict:
        body, ctype = _form({"image": ("art.png", img, "image/png"),
                             "config": ("", json.dumps(cfg).encode(), "")})
        return self._req("POST", path, body, ctype)

    def job(self, jid: str) -> dict:
        return self._req("GET", f"/jobs/{jid}")

    def cancel(self, jid: str) -> dict:
        return self._req("POST", f"/jobs/{jid}/cancel", b"")

    def health(self) -> dict:
        return self._req("GET", "/health")


def poll(c: Client, jid: str, t_submit: float, *, cancel_after: float | None = None,
         dt: float = 0.05) -> dict:
    """Poll a job to a terminal state. Times are seconds from `t_submit`."""
    rec = {"t_running": None, "t_end": None, "state": None, "t_cancel_sent": None,
           "t_cancel_reply": None, "n_stitches": None}
    while True:
        j = c.job(jid)
        now = time.monotonic() - t_submit
        if j["state"] == "running" and rec["t_running"] is None:
            rec["t_running"] = round(now, 3)
        if (cancel_after is not None and rec["t_running"] is not None
                and rec["t_cancel_sent"] is None and now - rec["t_running"] >= cancel_after):
            rec["t_cancel_sent"] = round(time.monotonic() - t_submit, 3)
            c.cancel(jid)
            rec["t_cancel_reply"] = round(time.monotonic() - t_submit, 3)
        if j["state"] in ("done", "error", "cancelled"):
            rec["t_end"] = round(now, 3)
            rec["state"] = j["state"]
            if j["state"] == "done":
                rec["n_stitches"] = len(j.get("design", {}).get("stitches", []))
                rec["generation_cache"] = j.get("generation_cache")
            if j["state"] == "error":
                rec["error"] = j.get("error")
            return rec
        time.sleep(dt)


PS_SNAPSHOT = r"""
$a = @{}; Get-Process | % { if ($_.CPU) { $a[$_.Id] = $_.CPU } }
Start-Sleep -Milliseconds 2000
$cores = 0.0; $top = @()
Get-Process | % { if ($_.CPU -and $a.ContainsKey($_.Id)) { $d = ($_.CPU - $a[$_.Id]) / 2.0; $cores += $d;
  if ($d -gt 0.15) { $top += [pscustomobject]@{id=$_.Id; name=$_.Name; cores=[math]::Round($d,2)} } } }
$py = Get-CimInstance Win32_Process -Filter "Name like 'python%'" | % {
  [pscustomobject]@{id=$_.ProcessId; cmd=($_.CommandLine -replace '\s+',' ').Substring(0,[Math]::Min(160,($_.CommandLine -replace '\s+',' ').Length))} }
[pscustomobject]@{busy_cores=[math]::Round($cores,2); top=$top; python=$py} | ConvertTo-Json -Depth 4 -Compress
"""


def snapshot(skip_pid: int | None = None) -> dict:
    """Cores busy machine-wide over 2 s, processes above 0.15 core, every
    python process with its command line (the probe's own pid marked)."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", PS_SNAPSHOT],
                             capture_output=True, text=True, timeout=60).stdout
        snap = json.loads(out)
        py = snap.get("python") or []
        if isinstance(py, dict):
            py = [py]
        snap["python"] = [p for p in py if "second_digitize_timing" not in (p.get("cmd") or "")]
        top = snap.get("top") or []
        snap["top"] = [top] if isinstance(top, dict) else top
        return snap
    except Exception as exc:                                     # noqa: BLE001
        return {"error": repr(exc)}


class LoadSampler:
    """Machine-wide CPU busy % once a second (`typeperf`, one long-lived
    process), stamped with this process's monotonic clock, so a run's mean
    machine load is read over the run itself, not a 2 s glimpse at its start."""

    def __init__(self):
        self.samples: list[tuple[float, float]] = []
        try:
            self.proc = subprocess.Popen(
                ["typeperf", r"\Processor(_Total)\% Processor Time", "-si", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        except OSError:
            self.proc = None
            return
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            parts = line.strip().split('","')
            if len(parts) == 2:
                try:
                    self.samples.append((time.monotonic(), float(parts[1].strip('"'))))
                except ValueError:
                    pass

    def mean_busy_cores(self, t0: float, t1: float) -> float | None:
        xs = [v for t, v in self.samples if t0 <= t <= t1]
        return round(sum(xs) / len(xs) / 100.0 * (os.cpu_count() or 1), 2) if xs else None

    def stop(self):
        if self.proc:
            self.proc.terminate()


SAMPLER: LoadSampler | None = None


def run_one(c: Client, name: str, img: bytes, cfg: dict, out, *, cancel_after=None,
            recount_img: bytes | None = None, snap: bool = True) -> dict:
    rec = {"run": name, "wall_start": time.strftime("%H:%M:%S")}
    if snap:
        rec["machine"] = snapshot()
    rc_thread = None
    rc_box: dict = {}
    if recount_img is not None:
        def _rc():
            t = time.monotonic()
            r = c.post_art("/recount", recount_img, cfg)
            rc_box.update(elapsed_s=round(time.monotonic() - t, 3), server_ms=r.get("elapsed_ms"))
        rc_thread = threading.Thread(target=_rc)
    t0 = time.monotonic()
    rec["t_submit_mono"] = round(t0, 4)
    if rc_thread:
        rc_thread.start()
    sub = c.post_art("/digitize", img, cfg)
    rec["t_accepted"] = round(time.monotonic() - t0, 3)
    rec["job"] = sub["job_id"]
    rec["cached"] = sub["cached"]
    rec.update(poll(c, sub["job_id"], t0, cancel_after=cancel_after))
    if rc_thread:
        rc_thread.join()
        rec["recount"] = rc_box
    if SAMPLER is not None:
        rec["machine_busy_cores_during"] = SAMPLER.mean_busy_cores(t0, time.monotonic())
    out.write(json.dumps(rec) + "\n")
    out.flush()
    print(f"{name:10s} state={rec['state']:9s} queued->running {rec['t_running']}  end {rec['t_end']}",
          flush=True)
    return rec


def wait_health(c: Client, proc, timeout=180) -> None:
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        if proc.poll() is not None:
            raise SystemExit(f"probe exited {proc.returncode}")
        try:
            c.health()
            return
        except Exception:                                        # noqa: BLE001
            time.sleep(0.5)
    raise SystemExit("probe not ready")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", nargs=2, metavar=("PORT", "LOG"))
    ap.add_argument("--image")
    ap.add_argument("--width", type=float, default=96.0)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--out", default=".")
    ap.add_argument("--cancel-frac", type=float, default=0.4,
                    help="cancel X this fraction of A's run time after it starts running")
    ap.add_argument("--arms", default="A,A',B,X,C,R",
                    help="also K: a digitize under --load-procs other digitizes")
    ap.add_argument("--load-procs", type=int, default=2)
    ap.add_argument("--cancel-early-frac", type=float, default=0.12,
                    help="arm Xe: cancel this fraction of A's run time in (inside stages 0-4)")
    ap.add_argument("--load", nargs=2, metavar=("IMAGE", "WIDTH"))
    args = ap.parse_args()
    if args.serve:
        serve(int(args.serve[0]), args.serve[1])
        return
    if args.load:
        load(args.load[0], float(args.load[1]))
        return

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = out_dir / f"probe-{stamp}.jsonl"
    runs_path = out_dir / f"runs-{stamp}.jsonl"
    png = Path(args.image).read_bytes()
    cfg = {"target_width_mm": args.width}
    arms = args.arms.split(",")

    proc = subprocess.Popen([sys.executable, "-m", "tools.second_digitize_timing",
                             "--serve", str(args.port), str(log_path)],
                            cwd=str(Path(__file__).resolve().parents[1]))
    c = Client(args.port)
    global SAMPLER
    SAMPLER = LoadSampler()
    try:
        wait_health(c, proc)
        print(f"probe pid {proc.pid} on :{args.port}; runs -> {runs_path}", flush=True)
        with open(runs_path, "a", encoding="utf-8") as out:
            out.write(json.dumps({"meta": {"image": args.image, "cfg": cfg, "probe_pid": proc.pid,
                                           "reps": args.reps, "cpu_count": os.cpu_count()}}) + "\n")
            # Warm the imports / numba / font caches once so rep 1's A is not
            # paying process start-up the others do not.
            run_one(c, "warmup", png_variant(png, f"warm-{stamp}"), cfg, out, snap=False)
            for rep in range(1, args.reps + 1):
                v = lambda tag: png_variant(png, f"{stamp}-{rep}-{tag}")   # noqa: E731
                a = None
                if "A" in arms:
                    img_a = v("A")
                    a = run_one(c, f"r{rep}-A", img_a, cfg, out)
                    if "A'" in arms:
                        run_one(c, f"r{rep}-A'", img_a, cfg, out, snap=False)
                if "B" in arms:
                    run_one(c, f"r{rep}-B", v("B"), cfg, out)
                if "X" in arms:
                    img_x = v("X")
                    base = (a["t_end"] - a["t_running"]) if a else 10.0
                    run_one(c, f"r{rep}-X", img_x, cfg, out,
                            cancel_after=max(0.5, args.cancel_frac * base))
                    if "C" in arms:
                        # No snapshot: the Studio resubmits at once, and the
                        # cancelled job's remainder is exactly what is measured.
                        run_one(c, f"r{rep}-C", img_x, cfg, out, snap=False)
                if "Xe" in arms:
                    # Cancel EARLY, inside stages 0-4, so no generation is
                    # cached and Ce is a cold run behind whatever is left.
                    img_xe = v("Xe")
                    base = (a["t_end"] - a["t_running"]) if a else 10.0
                    run_one(c, f"r{rep}-Xe", img_xe, cfg, out,
                            cancel_after=max(0.3, args.cancel_early_frac * base))
                    # Idle check: 3 s with nothing submitted. A cancelled job
                    # still computing would show as probe CPU here.
                    p0 = c._req("GET", "/_probe")
                    time.sleep(3.0)
                    p1 = c._req("GET", "/_probe")
                    idle = {"run": f"r{rep}-idle-after-cancel",
                            "probe_cores": round((p1["pcpu"] - p0["pcpu"]) / (p1["t"] - p0["t"]), 3),
                            "inflight": [p0["jobs"]["inflight"], p1["jobs"]["inflight"]],
                            "threads": p1["threads"]}
                    out.write(json.dumps({"idle": idle}) + "\n")
                    out.flush()
                    print(f"idle after cancel: probe {idle['probe_cores']} cores, "
                          f"inflight {idle['inflight']}", flush=True)
                    run_one(c, f"r{rep}-Ce", img_xe, cfg, out, snap=False)
                if "R" in arms:
                    run_one(c, f"r{rep}-R", v("R"), cfg, out, recount_img=v("Rc"))
                if "K" in arms:
                    # Contention, on purpose: N other full digitizes of the
                    # same art in their own processes, started 3 s ahead so
                    # they are past import when K starts. Ours; killed after.
                    loads = [subprocess.Popen([sys.executable, "-m", "tools.second_digitize_timing",
                                               "--load", args.image, str(args.width)],
                                              cwd=str(Path(__file__).resolve().parents[1]))
                             for _ in range(args.load_procs)]
                    time.sleep(3.0)
                    try:
                        run_one(c, f"r{rep}-K{args.load_procs}", v("K"), cfg, out)
                    finally:
                        for lp in loads:
                            lp.terminate()
                        for lp in loads:
                            lp.wait(30)
            run_one(c, "end", png_variant(png, f"end-{stamp}"), cfg, out)
    finally:
        SAMPLER.stop()
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"done: {runs_path} {log_path}")


if __name__ == "__main__":
    main()
