"""Build the one-folder app: the digitizer service, the built Studio and the
OCR data, frozen with PyInstaller. Step 4 of the local Windows app
(PRODUCT.md launch row 8; docs/packaging-freeze-spike-2026-11-10.md "Recipe").

    cd app && npm ci && npm run build
    cd digitizer && python packaging/build_freeze.py --work <a scratch dir OUTSIDE the checkout>

Run it with the interpreter that holds the pinned wheels (`requirements.txt`
on Python 3.12, the one CI tests). It leaves, all under `--work`:

    dist/<name>/                 the folder a customer gets (`<name>.exe` + `_internal/`)
    <name>-<release>-<os>.zip    that folder, zipped
    build_report.json            sizes, what was pruned, the hidden-import verdicts
    pyinstaller.log              the whole PyInstaller output

It freezes whatever OS it runs on. The product is Windows, and the release
build is `.github/workflows/windows-app.yml` on `windows-latest`; a Linux run
of this script is a rehearsal of the script, not a deliverable.

What it does that the spike's hand-typed recipe did not:

  - DATA IS DISCOVERED, NOT LISTED. Every non-Python file under
    `digitizer_core/` and `digitizer_service/` is bundled at its own path, so
    a new data directory cannot be forgotten here and fail only on the route
    that reads it (the spike's warning about its three `--add-data` lines).
  - THE VERSION STAMP. `build_stamp.json` (commit, dirty, release, built_at)
    goes in beside the packages; a frozen `/health` reads it and never runs
    git (`digitizer_service/app.py`, "the engine stamp").
  - THE STUDIO AND TESSDATA GO IN. `app/dist` as `studio/`, and
    `eng.traineddata` as `tessdata/`: the tessdata_fast 4.1.0 file, pinned by
    sha256, the same bytes `apt install tesseract-ocr` gives the Linux CI.
  - A HIDDEN IMPORT PYINSTALLER CANNOT FIND IS CHECKED, NOT WAVED AT. Each is
    looked up in the interpreter the tests ran on. Absent there too: nothing
    is missing from the freeze that the tested engine had. Importable there:
    the freeze lost something, and the build fails.
  - PRUNE, then MEASURE: folder and zip against the spike's 415 MB / 167 MB.

PyInstaller itself goes in a throwaway venv under `--work`, as in the spike:
the project's wheels reach it through a `.pth` line, so nothing is installed
beside the pinned set and the frozen binaries are the files the tests ran on.
The line PREPENDS the project's site-packages, because pip brings PyInstaller's
own dependencies (`packaging`, for one, which the engine also imports) into
the throwaway venv, and an appended path would freeze those copies instead.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parents[1]
REPO = DIGITIZER.parent
PACKAGES = ("digitizer_core", "digitizer_service")

#: The spike froze with this one (docs/packaging-freeze-spike-2026-11-10.md).
PYINSTALLER_VERSION = "6.22.3"

#: Must match `digitizer_service.app.BUILD_STAMP` (pinned by a test).
BUILD_STAMP = "build_stamp.json"

#: tessdata_fast 4.1.0 `eng.traineddata`, 4,113,088 bytes, Apache-2.0. The
#: hash was taken from Ubuntu's `tesseract-ocr-eng 1:4.1.0-2` package, which
#: ships this file: it is what the Linux CI's OCR reads.
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/eng.traineddata"
TESSDATA_SHA256 = "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"

#: Never in the product. The recipe's four.
EXCLUDED_MODULES = ("pytest", "_pytest", "xdist", "pip")

#: Files deleted from the frozen folder, with the reason each is safe. A glob
#: that matches nothing (another OS, another wheel layout) prunes nothing.
#: The proof that a prune is safe is the smoke run AFTER it
#: (`packaging/release_smoke.py`), never this table.
PRUNE = (
    ("**/opencv_videoio_ffmpeg*.dll",
     "OpenCV's video I/O plugin (29 MB in the spike). cv2 loads it only when a "
     "VideoCapture or VideoWriter is opened, and the engine opens neither: it "
     "decodes still images."),
)

#: What the spike measured, unpruned (same doc, "Numbers").
SPIKE = {"folder_mb": 415, "files": 430, "zip_mb": 166.9}

MB = 1024 * 1024


class BuildError(SystemExit):
    """One sentence, exit 1. Not a traceback: these are things to go and fix."""

    def __init__(self, message: str):
        super().__init__(f"build_freeze: {message}")


# ---------------------------------------------------------------- the stamp

def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=DIGITIZER, capture_output=True,
                              text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def make_stamp(commit: str | None = None, release: str | None = None) -> dict:
    """What a frozen `/health` will say it is. `dirty` is the service's own
    definition: a tracked change under the two packages it imports."""
    dirty = None
    if commit is None:
        commit = _git("rev-parse", "HEAD")
        if not commit:
            raise BuildError("cannot read the commit from git here; pass --commit <40-hex sha>.")
        changed = _git("status", "--porcelain", "--untracked-files=no", "--", *PACKAGES)
        dirty = None if changed is None else bool(changed)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise BuildError(f"--commit must be a full 40-hex sha, got {commit!r}.")
    release = release or f"dev-{commit[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", release):
        raise BuildError(f"--release {release!r} must be a plain name like v1.0.0: it becomes a file name.")
    return {
        "commit": commit,
        "dirty": dirty,
        "release": release,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "pyinstaller": PYINSTALLER_VERSION,
    }


# ------------------------------------------------------------- the staging

def package_data_files(root: Path = DIGITIZER) -> list[Path]:
    """Every file under the two packages that is not Python source, relative
    to `root`: the thread charts, the outline fonts, the face model, and
    whatever is added next."""
    out = []
    for pkg in PACKAGES:
        for p in sorted((root / pkg).rglob("*")):
            if p.is_file() and p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts:
                out.append(p.relative_to(root))
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_tessdata(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(TESSDATA_URL, timeout=120) as r, dest.open("wb") as f:
            shutil.copyfileobj(r, f)
    except OSError as exc:
        raise BuildError(f"could not download {TESSDATA_URL} ({exc}); "
                         "pass --tessdata <path to eng.traineddata>.") from exc
    got = sha256_file(dest)
    if got != TESSDATA_SHA256:
        dest.unlink()
        raise BuildError(f"{TESSDATA_URL} is not the pinned file: sha256 {got}, "
                         f"expected {TESSDATA_SHA256}.")


def stage(stage_dir: Path, stamp: dict, tessdata: Path | None) -> dict:
    """Lay out everything that rides beside the code, at the path it will
    have inside the frozen folder. Returns what went in."""
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    data = package_data_files()
    for rel in data:
        (stage_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DIGITIZER / rel, stage_dir / rel)
    eng = stage_dir / "tessdata" / "eng.traineddata"
    if tessdata is None:
        fetch_tessdata(eng)
    else:
        if not tessdata.is_file():
            raise BuildError(f"--tessdata {tessdata} is not a file.")
        eng.parent.mkdir(parents=True)
        shutil.copy2(tessdata, eng)
    tess_sha = sha256_file(eng)
    (stage_dir / BUILD_STAMP).write_text(json.dumps(stamp, indent=1), encoding="utf-8")
    return {"package_data_files": len(data),
            "package_data_dirs": sorted({rel.parent.as_posix() for rel in data}),
            "tessdata_sha256": tess_sha, "tessdata_pinned": tess_sha == TESSDATA_SHA256}


# -------------------------------------------------------------- pyinstaller

def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def pth_line(site_dirs: list[str]) -> str:
    """One executable `.pth` line that puts the project's site-packages AHEAD
    of the throwaway venv's own (module docstring, last paragraph)."""
    return "import sys; sys.path[:0] = [p for p in %r if p not in sys.path]\n" % (site_dirs,)


def make_pyinstaller_venv(venv: Path) -> Path:
    if venv.exists():
        shutil.rmtree(venv)
    _run([sys.executable, "-m", "venv", str(venv)])
    py = _venv_python(venv)
    _run([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
          f"pyinstaller=={PYINSTALLER_VERSION}"])
    theirs = subprocess.run([str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                            capture_output=True, text=True, check=True).stdout.strip()
    paths = sysconfig.get_paths()
    ours = list(dict.fromkeys([paths["purelib"], paths["platlib"]]))
    (Path(theirs) / "digitizer_wheels.pth").write_text(pth_line(ours), encoding="utf-8")
    return py


def pyinstaller_args(name: str, entry: Path, stage_dir: Path, studio: Path, work: Path) -> list[str]:
    args = ["--noconfirm", "--onedir", "--console", "--name", name,
            "--paths", str(DIGITIZER),
            "--distpath", str(work / "dist"), "--workpath", str(work / "build"),
            "--specpath", str(work)]
    for pkg in PACKAGES:
        args += ["--collect-submodules", pkg]
    # `SRC<sep>DEST`: the separator is the OS's path separator, by PyInstaller's rule.
    for child in sorted(stage_dir.iterdir()):
        args += ["--add-data", f"{child}{os.pathsep}{child.name if child.is_dir() else '.'}"]
    args += ["--add-data", f"{studio}{os.pathsep}studio"]
    for mod in EXCLUDED_MODULES:
        args += ["--exclude-module", mod]
    return [*args, str(entry)]


def _run(cmd: list[str], cwd: Path | None = None, log: Path | None = None) -> str:
    """Run, echoing every line as it comes; return the whole output. A
    non-zero exit stops the build."""
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    lines = []
    for line in proc.stdout:
        lines.append(line)
        print(line, end="", flush=True)
    code = proc.wait()
    out = "".join(lines)
    if log is not None:
        log.write_text(out, encoding="utf-8")
    if code != 0:
        raise BuildError(f"`{Path(cmd[0]).name} {' '.join(cmd[1:4])} ...` exited {code}.")
    return out


# ---------------------------------------------------------- hidden imports

_HIDDEN = re.compile(r"""Hidden import ['"]([^'"]+)['"] not found""")


def missing_hidden_imports(pyinstaller_output: str) -> list[str]:
    return sorted(set(_HIDDEN.findall(pyinstaller_output)))


def importable_here(module: str) -> bool:
    """Can the interpreter running this script (the tested one) import it?"""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def judge_hidden_imports(names: list[str], importable=importable_here) -> list[dict]:
    """A hidden import is a hook's GUESS that a module will be wanted at run
    time. One PyInstaller cannot find is harmless exactly when the tested
    environment cannot import it either: the engine never had it. (The
    spike's two are both this: `tzdata` is not in requirements.txt, and
    scipy 1.18 has no `scipy.special._cdflib` for its stale hook to find.)"""
    return [{"module": n, "in_tested_env": bool(importable(n)),
             "verdict": "LOST: the tested environment has it and the freeze does not"
                        if importable(n) else
                        "harmless: the tested environment does not have it either"}
            for n in names]


# ------------------------------------------------------- prune and measure

def prune(internal: Path, rules=PRUNE) -> list[dict]:
    out = []
    for pattern, why in rules:
        for p in sorted(internal.glob(pattern)):
            if p.is_file():
                out.append({"file": p.relative_to(internal).as_posix(), "bytes": p.stat().st_size, "why": why})
                p.unlink()
    return out


def measure(folder: Path, top: int = 15) -> dict:
    files = [(p.stat().st_size, p.relative_to(folder).as_posix())
             for p in folder.rglob("*") if p.is_file()]
    by_top: dict[str, int] = {}
    for size, rel in files:
        parts = rel.split("/")
        # `_internal/<package or file>`: the level a prune decision is made at.
        key = "/".join(parts[:2]) if len(parts) > 2 else rel
        by_top[key] = by_top.get(key, 0) + size
    return {"bytes": sum(s for s, _ in files), "files": len(files),
            "largest_files": [{"file": r, "bytes": s} for s, r in sorted(files, reverse=True)[:top]],
            "largest_entries": [{"entry": k, "bytes": v}
                                for k, v in sorted(by_top.items(), key=lambda kv: -kv[1])[:top]]}


def zip_folder(folder: Path, dest: Path) -> int:
    """`folder` zipped with itself as the top-level directory, so unzipping
    gives one folder. Deflate at its best level, as the spike's
    `Compress-Archive -CompressionLevel Optimal` was."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, (Path(folder.name) / p.relative_to(folder)).as_posix())
    return dest.stat().st_size


def _mb(n: float) -> str:
    return f"{n / MB:.1f} MB"


def summary_markdown(report: dict) -> str:
    stamp, size, pruned = report["stamp"], report["size"], report["pruned"]
    cut = sum(p["bytes"] for p in pruned)
    lines = [
        f"## Frozen app build: `{stamp['release']}`",
        "",
        f"`{report['platform']}`, Python {stamp['python']}, PyInstaller {stamp['pyinstaller']}, "
        f"commit `{stamp['commit']}`{' (DIRTY tree)' if stamp['dirty'] else ''}, "
        f"build {report['build_s']:.0f} s.",
        "",
        "| | This build | Spike (2026-11-10, unpruned, Python 3.14) |",
        "|---|---|---|",
        f"| Folder | {_mb(size['bytes'])}, {size['files']} files | {SPIKE['folder_mb']} MB, {SPIKE['files']} files |",
        f"| Zip | {_mb(report['zip_bytes']) if report['zip_bytes'] else 'not made'} | {SPIKE['zip_mb']} MB |",
        f"| Pruned | {_mb(cut)} in {len(pruned)} file(s) | nothing |",
        "",
        f"Bundled: the Studio ({_mb(report['studio_bytes'])}), {report['staged']['package_data_files']} engine data "
        f"files from {len(report['staged']['package_data_dirs'])} directories, `eng.traineddata` "
        f"({'the pinned tessdata_fast 4.1.0 file' if report['staged']['tessdata_pinned'] else 'NOT the pinned file'}).",
        "",
    ]
    if pruned:
        lines += ["Pruned:", ""] + [f"- `{p['file']}` ({_mb(p['bytes'])}): {p['why']}" for p in pruned] + [""]
    hidden = report["hidden_imports"]
    if hidden:
        lines += ["Hidden imports PyInstaller could not find:", ""]
        lines += [f"- `{h['module']}`: {h['verdict']}" for h in hidden] + [""]
    else:
        lines += ["No hidden import went unfound.", ""]
    lines += ["Largest entries:", "", "| Entry | Size |", "|---|---|"]
    lines += [f"| `{e['entry']}` | {_mb(e['bytes'])} |" for e in size["largest_entries"]]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------- main

def build(args) -> dict:
    work = args.work.resolve()
    if work == REPO or REPO in work.parents:
        raise BuildError(f"--work {work} is inside the checkout. Use a scratch directory outside it: "
                         "the build leaves a venv, a .spec and several hundred MB behind.")
    studio = args.studio.resolve()
    if not (studio / "index.html").is_file():
        raise BuildError(f"{studio} is not a built Studio (no index.html). "
                         "Run `npm ci && npm run build` in app/ first.")
    entry = args.entry.resolve()
    if not entry.is_file():
        raise BuildError(f"--entry {entry} is not a file.")
    absent = [m for m in ("cv2", "scipy", "skimage", "shapely", "pystitch", "tesserocr",
                          "fastapi", "uvicorn", "multipart") if not importable_here(m)]
    if absent:
        raise BuildError(f"this interpreter ({sys.executable}) cannot import {', '.join(absent)}. "
                         "Run the build with the one that has requirements.txt installed.")

    t0 = time.perf_counter()
    work.mkdir(parents=True, exist_ok=True)
    stamp = make_stamp(args.commit, args.release or os.environ.get("EMBBOT_RELEASE") or None)
    staged = stage(work / "stage", stamp, args.tessdata)
    for stale in (work / "dist" / args.name, work / "build" / args.name):
        if stale.exists():
            shutil.rmtree(stale)

    py = make_pyinstaller_venv(work / "venv")
    output = _run([str(py), "-m", "PyInstaller",
                   *pyinstaller_args(args.name, entry, work / "stage", studio, work)],
                  cwd=work, log=work / "pyinstaller.log")

    folder = work / "dist" / args.name
    internal = folder / "_internal"
    exe = folder / (args.name + (".exe" if os.name == "nt" else ""))
    wanted = [BUILD_STAMP, "tessdata/eng.traineddata", "studio/index.html",
              *(rel.as_posix() for rel in package_data_files())]
    gone = [w for w in wanted if not (internal / w).is_file()]
    if not exe.is_file() or gone:
        raise BuildError(f"the frozen folder is incomplete: exe present {exe.is_file()}, "
                         f"missing under _internal: {gone[:8]}")

    hidden = judge_hidden_imports(missing_hidden_imports(output))
    pruned = [] if args.no_prune else prune(internal)
    report = {
        "name": args.name, "platform": sys.platform, "stamp": stamp, "staged": staged,
        "folder": str(folder), "exe": str(exe), "tessdata_dir": str(internal / "tessdata"),
        "studio_bytes": sum(p.stat().st_size for p in studio.rglob("*") if p.is_file()),
        "hidden_imports": hidden, "pruned": pruned, "size": measure(folder),
        "zip": None, "zip_bytes": None,
    }
    if not args.no_zip:
        os_tag = {"win32": "win64", "darwin": "macos"}.get(sys.platform, sys.platform)
        dest = work / f"{args.name}-{stamp['release']}-{os_tag}.zip"
        report["zip_bytes"] = zip_folder(folder, dest)
        report["zip"] = str(dest)
    report["build_s"] = round(time.perf_counter() - t0, 1)
    (work / "build_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    text = summary_markdown(report)
    print("\n" + text, flush=True)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
    lost = [h["module"] for h in hidden if h["in_tested_env"]]
    if lost:
        raise BuildError(f"hidden import(s) the tested environment has and the freeze lost: {', '.join(lost)}. "
                         "Add them to the PyInstaller command (--hidden-import) before shipping this folder.")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, required=True,
                    help="scratch directory OUTSIDE the checkout; everything is written here")
    ap.add_argument("--studio", type=Path, default=REPO / "app" / "dist",
                    help="the built Studio (default: app/dist)")
    ap.add_argument("--tessdata", type=Path, default=None,
                    help="an eng.traineddata to bundle (default: download the pinned tessdata_fast 4.1.0 file)")
    ap.add_argument("--release", default=None,
                    help="the build's name, e.g. the tag v1.0.0 (default: $EMBBOT_RELEASE, else dev-<commit>)")
    ap.add_argument("--commit", default=None, help="full sha to stamp (default: git HEAD of this checkout)")
    ap.add_argument("--name", default="embbot-digitizer", help="folder and exe name")
    ap.add_argument("--entry", type=Path, default=DIGITIZER / "packaging" / "freeze_entry.py",
                    help="the script to freeze (the launcher, once there is one)")
    ap.add_argument("--no-prune", action="store_true", help="keep every file PyInstaller collected")
    ap.add_argument("--no-zip", action="store_true")
    ap.add_argument("--summary", type=Path, default=None,
                    help="append the markdown summary to this file (CI: $GITHUB_STEP_SUMMARY)")
    build(ap.parse_args(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
