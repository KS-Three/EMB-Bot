"""Wrap the frozen folder in a Windows installer, then prove the installer.

    python packaging/build_installer.py --build-report <work>/build_report.json

Windows only, after `build_freeze.py` and a green `release_smoke.py`. Needs
Inno Setup 6 (`choco install innosetup`). It:

  1. compiles `packaging/installer.iss` into `<work>/<name>-<release>-setup.exe`
     (LZMA2, solid: the spike left this size unmeasured);
  2. INSTALLS it, silently and per user, into a directory under `<work>`;
  3. starts the INSTALLED exe (PATH cut down, as the smoke does) and requires
     `/health` to carry the build's commit and `/` to be the Studio: once as
     the bare service (`--serve`) on a port of its own, and once the way the
     Start-menu shortcut starts it, as the launcher, which must come up on
     http://127.0.0.1:8721/ and let go of the port when it is ended;
  4. UNINSTALLS it and requires the directory to be gone.

An installer nobody has run is a guess; steps 2-4 are the difference. What
they do not show: a PC that is not a build machine (no VC++ runtime, other
antivirus), and what SmartScreen says about an unsigned setup.exe when a
person downloads it. Both need a human at a second machine.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freeze_check  # noqa: E402
import one_origin_smoke  # noqa: E402
import release_smoke  # noqa: E402

ISS = Path(__file__).resolve().parent / "installer.iss"
MB = 1024 * 1024


def installed_launcher(exe: Path, work: Path, expect_commit: str) -> list[str]:
    """The installed exe started as the shortcut starts it (no arguments but
    `--console --no-browser`): it must serve the Studio on the launcher's one
    port with the build's commit, and free that port once it is ended."""
    L = one_origin_smoke.L
    if L.bind_error(L.PORT) is not None:
        return [f"port {L.PORT} was already held before the installed launcher was started"]
    env = release_smoke.bare_env()
    env["LOCALAPPDATA"] = str(work / "installed-localappdata")
    launch = one_origin_smoke.Launch([str(exe)], work, env, "installed-launcher").start()
    try:
        up = one_origin_smoke.wait_until(lambda: L.probe(L.PORT) == L.OURS or launch.proc.poll() is not None, 150)
        commit = ((one_origin_smoke.health(L.PORT) or {}).get("engine") or {}).get("commit")
        if up is not True or launch.proc.poll() is not None:
            return [f"the installed launcher did not serve the Studio on {L.PORT} "
                    f"(exit {launch.proc.poll()}): {launch.text()[-1500:]}"]
        if commit != expect_commit:
            return [f"the installed launcher's /health commit is {commit!r}, the build stamped {expect_commit!r}"]
    finally:
        launch.kill()
    if not one_origin_smoke.wait_until(lambda: L.bind_error(L.PORT) is None, 30):
        return [f"port {L.PORT} still held 30 s after the installed launcher was ended"]
    return []


def find_iscc() -> Path | None:
    found = shutil.which("iscc") or shutil.which("ISCC.exe")
    if found:
        return Path(found)
    for var in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(var)
        if base and (Path(base) / "Inno Setup 6" / "ISCC.exe").is_file():
            return Path(base) / "Inno Setup 6" / "ISCC.exe"
    return None


def iscc_args(report: dict, out_dir: Path) -> tuple[list[str], Path]:
    """The compiler's arguments and the setup.exe they produce."""
    base = f"{report['name']}-{report['stamp']['release']}-setup"
    args = ["/Qp", f"/DSourceDir={report['folder']}", f"/DOutputDir={out_dir}", f"/DOutputBase={base}",
            f"/DAppVersion={report['stamp']['release']}", f"/DExeName={Path(report['exe']).name}", str(ISS)]
    return args, out_dir / f"{base}.exe"


def _must(cmd: list[str], what: str) -> None:
    print("+ " + " ".join(cmd), flush=True)
    code = subprocess.run(cmd, check=False).returncode
    if code != 0:
        raise SystemExit(f"build_installer: {what} exited {code}.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-report", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8733)
    ap.add_argument("--summary", type=Path, default=None)
    args = ap.parse_args(argv)
    if os.name != "nt":
        raise SystemExit("build_installer: Windows only (Inno Setup).")
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("build_installer: Inno Setup 6 (ISCC.exe) not found. `choco install innosetup`.")

    report = json.loads(args.build_report.read_text(encoding="utf-8"))
    stamp = report["stamp"]
    work = args.build_report.resolve().parent
    target = work / "installed"
    if target.exists():
        raise SystemExit(f"build_installer: {target} already exists; remove it first.")

    t0 = time.perf_counter()
    cmd, setup = iscc_args(report, work)
    _must([str(iscc), *cmd], "the Inno Setup compiler")
    compile_s = time.perf_counter() - t0

    failures = []
    silent = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    _must([str(setup), *silent, "/CURRENTUSER", f"/DIR={target}", f"/LOG={work / 'install.log'}"], "the installer")
    exe = target / Path(report["exe"]).name
    installed = sum(1 for p in target.rglob("*") if p.is_file())
    shipped = report["size"]["files"]
    if not exe.is_file():
        failures.append(f"the installer finished but {exe} is not there")
    else:
        if installed < shipped:
            failures.append(f"{installed} files installed, the frozen folder has {shipped}")
        import httpx

        base = f"http://127.0.0.1:{args.port}"
        with release_smoke.Service(release_smoke.frozen_service(exe, args.port), work, release_smoke.bare_env(),
                                   work / "installed-service.log"):
            health, waited = freeze_check._wait_health(base, 120)
            page = httpx.get(base + "/", timeout=30)
        got = (health.get("engine") or {}).get("commit")
        if got != stamp["commit"]:
            failures.append(f"installed /health engine.commit is {got!r}, the build stamped {stamp['commit']!r}")
        if page.status_code != 200 or '<div id="app">' not in page.text:
            failures.append(f"installed GET / is not the Studio (HTTP {page.status_code})")
        failures += installed_launcher(exe, work, stamp["commit"])

    uninstaller = target / "unins000.exe"
    if uninstaller.is_file():
        _must([str(uninstaller), *silent], "the uninstaller")
        deadline = time.perf_counter() + 60          # the uninstaller's last act is deleting itself
        while target.exists() and time.perf_counter() < deadline:
            time.sleep(1)
        if target.exists():
            left = [p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()][:8]
            failures.append(f"uninstall left {target} behind: {left}")
    else:
        failures.append("no unins000.exe was installed")

    size = setup.stat().st_size
    zipped = report.get("zip_bytes")
    lines = [
        "## Installer",
        "",
        f"**{'PASS' if not failures else 'FAIL'}**: `{setup.name}`, {size / MB:.1f} MB "
        f"(the zip of the same folder: {zipped / MB:.1f} MB; the folder: {report['size']['bytes'] / MB:.1f} MB), "
        f"Inno Setup LZMA2 solid, compiled in {compile_s:.0f} s. Unsigned.",
        "",
        f"- Installed silently, per user, to a scratch directory: {installed} files (the folder has {shipped}, "
        "plus the uninstaller's two).",
        "- The installed exe answered `/health` with the build's commit and served the Studio at `/`, "
        "as the bare service on its own port and as the launcher the shortcut starts, on "
        "`http://127.0.0.1:8721/`, which let go of the port when it was ended."
        if not failures else "- The installed exe did NOT pass; see below.",
        "- Uninstalled silently; the directory is gone." if not target.exists() else "- Uninstall left files behind.",
    ]
    if failures:
        lines += ["", "Failures:", ""] + [f"- {f}" for f in failures]
    text = "\n".join(lines) + "\n"
    (work / "installer.md").write_text(text, encoding="utf-8")
    print("\n" + text, flush=True)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
