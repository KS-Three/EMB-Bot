"""Wrap the frozen folder in a Windows installer, then prove the installer.

    python packaging/build_installer.py --build-report <work>/build_report.json

Windows only, after `build_freeze.py` and a green `release_smoke.py`. Needs
Inno Setup 6 (`choco install innosetup`). It:

  1. compiles `packaging/installer.iss` into `<work>/<name>-<release>-setup.exe`
     (LZMA2, solid: the spike left this size unmeasured);
  2. INSTALLS it, silently and per user, into a directory under `<work>`;
  3. starts the INSTALLED exe (PATH cut down, as the smoke does) and requires
     `/health` to carry the build's commit and `/` to be the Studio;
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
import release_smoke  # noqa: E402

ISS = Path(__file__).resolve().parent / "installer.iss"
MB = 1024 * 1024


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
        with release_smoke.Service([str(exe), str(args.port)], work, release_smoke.bare_env(),
                                   work / "installed-service.log"):
            health, waited = freeze_check._wait_health(base, 120)
            page = httpx.get(base + "/", timeout=30)
        got = (health.get("engine") or {}).get("commit")
        if got != stamp["commit"]:
            failures.append(f"installed /health engine.commit is {got!r}, the build stamped {stamp['commit']!r}")
        if page.status_code != 200 or '<div id="app">' not in page.text:
            failures.append(f"installed GET / is not the Studio (HTTP {page.status_code})")

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
        "- The installed exe answered `/health` with the build's commit and served the Studio at `/`."
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
