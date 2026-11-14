"""Start the frozen app and prove it: the release build's smoke test.

    python packaging/release_smoke.py --build-report <work>/build_report.json --work <work>/smoke

Run it with the interpreter that holds the pinned wheels, after
`packaging/build_freeze.py`. It starts and stops both services itself, one at
a time (two digitizes at once move the job times), and does four things:

  1. THE VENV SIDE. `python -m digitizer_service` from the checkout, with
     `TESSDATA_PREFIX` on the SAME tessdata the freeze bundled, so both sides
     run the same pipeline (OCR on changes what a job does). The release
     suite (`freeze_check.SUITE`) runs against it.
  2. THE FROZEN SIDE. The exe, from a directory outside the checkout, with
     `PATH` cut to the operating system's own directories (no git, no
     Tesseract, no Python) and every variable that could point it at the
     checkout removed. The same suite runs against it.
  3. COMPARE the two (`freeze_check.compare`: design, review, warnings, and
     the bytes of every export), then JUDGE the frozen side alone
     (`freeze_check.release_failures`: the stamp, OCR, the Studio page, every
     lane done, every export verified).
  4. THE WRONG-STAMP CHECK the spike could only reason about: put the frozen
     folder INSIDE a git checkout whose HEAD is some other commit, with git
     on `PATH`, and require `/health` to still report the build's own commit.

Exit 0 only if nothing differs and nothing fails. The markdown table it
prints is what the PR or the release notes quote.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freeze_check  # noqa: E402  (a sibling script, not a package: see tests/test_packaging_freeze.py)

DIGITIZER = Path(__file__).resolve().parents[1]

#: Variables that could hand a frozen app something from this machine instead
#: of from its own folder. A customer's PC sets none of them.
#: Every `PYTHON*` variable goes too (the CI job sets PYTHONUTF8 for itself).
SCRUBBED = ("TESSDATA_PREFIX", "EMBBOT_STUDIO_DIR", "VIRTUAL_ENV", "EMB_OCR_ENGINE", "EMBBOT_SERVICE_TOKEN")


def scrubbed_env() -> dict:
    return {k: v for k, v in os.environ.items()
            if k.upper() not in SCRUBBED and not k.upper().startswith("PYTHON")}


def bare_env() -> dict:
    """This process's environment as a PC without the toolchain would have it."""
    env = scrubbed_env()
    if os.name == "nt":
        root = os.environ.get("SystemRoot", r"C:\Windows")
        env["PATH"] = f"{root}\\System32;{root}"
    else:
        env["PATH"] = "/usr/bin:/bin"
    return env


def frozen_service(exe: Path, port: int) -> list[str]:
    """The shipped exe as the bare service on `port`, without the launcher's
    one-port rule (that rule is `one_origin_smoke.py`'s to prove, on 8721):
    the launcher's own `--serve` child, with the bundled Studio and the
    bundled tessdata as its defaults."""
    return [str(exe), "--serve", "--port", str(port)]


class Service:
    """One child process and its log. Stopped on exit, whatever happened."""

    def __init__(self, cmd: list[str], cwd: Path, env: dict, log: Path):
        self.cmd, self.cwd, self.env, self.log = cmd, cwd, env, log

    def __enter__(self):
        self._out = self.log.open("w", encoding="utf-8")
        print("+ " + " ".join(self.cmd), flush=True)
        self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, env=self.env,
                                     stdout=self._out, stderr=subprocess.STDOUT)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=30)
        self._out.close()
        if exc_type is not None:
            tail = self.log.read_text(encoding="utf-8", errors="replace")[-3000:]
            print(f"--- {self.log.name} (tail) ---\n{tail}\n---", flush=True)
        return False


def _rmtree(path: Path) -> None:
    def writable(func, p, _):
        os.chmod(p, stat.S_IWRITE)      # git's object files are read-only on Windows
        func(p)
    shutil.rmtree(path, onerror=writable)


def stamp_inside_a_checkout(exe: Path, port: int, expect_commit: str, log: Path) -> dict:
    """Step 4 of the module docstring. `ran: False` (with why) when git is
    not on this machine: then the check did not happen, and says so."""
    git = shutil.which("git")
    if not git:
        return {"ran": False, "why": "git is not on PATH here"}
    around = exe.parent.parent              # dist/, the directory holding the frozen folder
    made = around / ".git"
    if made.exists():
        return {"ran": False, "why": f"{around} is already a git checkout"}
    quiet = {"capture_output": True, "text": True, "check": True}
    try:
        subprocess.run([git, "init", "-q", str(around)], **quiet)
        subprocess.run([git, "-C", str(around), "-c", "user.name=smoke", "-c", "user.email=smoke@localhost",
                        "commit", "-q", "--allow-empty", "-m", "not the build's commit"], **quiet)
        # Ask exactly as the service's probe does: git, run in the folder that holds the packages.
        head = subprocess.run([git, "rev-parse", "HEAD"], cwd=exe.parent / "_internal", **quiet).stdout.strip()
        # Full PATH here, on purpose: git has to stay findable for this to prove anything.
        with Service(frozen_service(exe, port), around, scrubbed_env(), log):
            health, _ = freeze_check._wait_health(f"http://127.0.0.1:{port}", 120)
    finally:
        if made.exists():
            _rmtree(made)
    got = (health.get("engine") or {}).get("commit")
    return {"ran": True, "checkout_head": head, "reported": got,
            "ok": bool(head) and head != expect_commit and got == expect_commit}


def summary_markdown(venv: dict, frozen: dict, differ: int, failures: list[str], stamp_check: dict) -> str:
    caps = frozen.get("capabilities") or {}
    eng = frozen.get("engine") or {}
    studio = frozen.get("studio") or {}
    lines = [
        "## Frozen app smoke",
        "",
        f"**{'PASS' if not differ and not failures else 'FAIL'}**: {differ} compared field(s) differ between "
        f"the venv service and the frozen exe, {len(failures)} failure(s) on the frozen side.",
        "",
        f"- `/health` from the frozen exe after {frozen.get('health_wait_s')} s: commit `{eng.get('commit')}`, "
        f"release `{eng.get('release')}`, dirty `{eng.get('dirty')}`; capabilities "
        + ", ".join(f"{k} {str(v).lower()}" for k, v in caps.items()) + ".",
        f"- Studio at `/`: {'served' if studio.get('served') else 'NOT served'}, "
        f"{studio.get('files')} files named by the page ({studio.get('scripts')} scripts), "
        f"{len(studio.get('bad') or [])} bad.",
    ]
    if stamp_check.get("ran"):
        lines.append(f"- Frozen folder placed inside a checkout at `{stamp_check['checkout_head'][:12]}` with git on "
                     f"PATH: `/health` reported `{str(stamp_check['reported'])[:12]}` "
                     f"({'the build stamp, correct' if stamp_check['ok'] else 'WRONG'}).")
    else:
        lines.append(f"- Wrong-stamp check NOT run: {stamp_check.get('why')}.")
    fmts = freeze_check.SHIPPED_FORMATS
    lines += ["",
              "| Job | Stitches (venv / frozen) | Seconds (venv / frozen) | Design | Review | Warnings | "
              + " | ".join(f.upper() for f in fmts) + " |",
              "|---|---|---|---|---|---|" + "---|" * len(fmts)]
    for case in freeze_check.SUITE:
        a = venv["fixtures"].get(case["name"], {})
        b = frozen["fixtures"].get(case["name"], {})

        def same(key):
            return "same" if key in a and a.get(key) == b.get(key) else "DIFFERS"

        cells = []
        for f in fmts:
            fa, fb = a.get(f) or {}, b.get(f) or {}
            ok = fa and all(fa.get(k) == fb.get(k) for k in ("status", "bytes", "cmp", "verified"))
            cells.append(f"{'same' if ok else 'DIFFERS'}, {fb.get('bytes', 0):,} B"
                         + ("" if fb.get("verified") == "true" else " UNVERIFIED"))
        lines.append(f"| {case['name']} | {a.get('stitches')} / {b.get('stitches')} | "
                     f"{a.get('job_s')} / {b.get('job_s')} | {same('design_sha')} | {same('review_sha')} | "
                     f"{same('warnings')} | " + " | ".join(cells) + " |")
    lines += ["",
              "Every export cell is the frozen file against the venv's for the same design; JEF with its "
              "14-byte clock field zeroed (`freeze_check.py`). Each was also re-read by the service "
              "(`X-Export-Verified`)."]
    if failures:
        lines += ["", "Failures:", ""] + [f"- {f}" for f in failures]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-report", type=Path, required=True,
                    help="build_report.json from build_freeze.py: names the exe, the tessdata and the stamp")
    ap.add_argument("--work", type=Path, required=True, help="where the logs and result files go")
    ap.add_argument("--venv-port", type=int, default=8731)
    ap.add_argument("--frozen-port", type=int, default=8732)
    ap.add_argument("--summary", type=Path, default=None,
                    help="append the markdown summary to this file (CI: $GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)

    report = json.loads(args.build_report.read_text(encoding="utf-8"))
    exe, stamp = Path(report["exe"]), report["stamp"]
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)

    venv_env = {**os.environ, "TESSDATA_PREFIX": report["tessdata_dir"]}
    venv_env.pop("EMBBOT_STUDIO_DIR", None)
    with Service([sys.executable, "-m", "digitizer_service", "--port", str(args.venv_port)],
                 DIGITIZER, venv_env, work / "venv-service.log"):
        venv = freeze_check.run(f"http://127.0.0.1:{args.venv_port}", work / "venv.json", [], suite=True)

    with Service(frozen_service(exe, args.frozen_port), work, bare_env(), work / "frozen-service.log"):
        frozen = freeze_check.run(f"http://127.0.0.1:{args.frozen_port}", work / "frozen.json", [], suite=True)

    differ = freeze_check.compare(venv, frozen)
    failures = freeze_check.release_failures(frozen, expect_commit=stamp["commit"],
                                             expect_release=stamp["release"])
    stamp_check = stamp_inside_a_checkout(exe, args.frozen_port, stamp["commit"], work / "frozen-in-checkout.log")
    if stamp_check.get("ran") and not stamp_check["ok"]:
        failures.append(f"inside a checkout at {stamp_check['checkout_head']}, the frozen /health reported "
                        f"{stamp_check['reported']!r} instead of the build's {stamp['commit']}")

    text = summary_markdown(venv, frozen, differ, failures, stamp_check)
    (work / "smoke.md").write_text(text, encoding="utf-8")
    (work / "smoke.json").write_text(json.dumps(
        {"differ": differ, "failures": failures, "stamp_check": stamp_check}, indent=1), encoding="utf-8")
    print("\n" + text, flush=True)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 1 if differ or failures else 0


if __name__ == "__main__":
    sys.exit(main())
