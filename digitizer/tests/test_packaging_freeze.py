"""The release build's own logic (packaging/build_freeze.py, freeze_check.py)
and the rules its workflow must keep. Nothing here freezes anything: the
frozen exe is proved on `windows-latest` by `.github/workflows/windows-app.yml`.

`packaging/` holds scripts, not a package (a `digitizer/packaging/__init__.py`
would shadow PyPI's `packaging`, which the engine's own dependencies import),
so the modules are loaded by path.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = DIGITIZER.parent
WORKFLOW = REPO / ".github" / "workflows" / "windows-app.yml"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_packaging_{name}", DIGITIZER / "packaging" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_after_siblings(name: str):
    """For a script that imports its sibling scripts by bare name."""
    sys.path.insert(0, str(DIGITIZER / "packaging"))
    try:
        return _load(name)
    finally:
        sys.path.remove(str(DIGITIZER / "packaging"))


build_freeze = _load("build_freeze")
freeze_check = _load("freeze_check")


# ------------------------------------------------------------- build script

def test_packaging_is_not_a_package():
    assert not (DIGITIZER / "packaging" / "__init__.py").exists()


def test_every_data_file_the_engine_opens_is_bundled():
    """Discovered, not listed: the spike's three hand-typed `--add-data`
    lines are exactly what a fourth data directory would have slipped past."""
    files = build_freeze.package_data_files()
    dirs = {p.parts[1] for p in files if p.parts[0] == "digitizer_core" and len(p.parts) > 2}
    assert {"chart_data", "outline_fonts", "model_data"} <= dirs
    assert all(p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts for p in files)
    on_disk = {p.relative_to(DIGITIZER) for pkg in build_freeze.PACKAGES
               for p in (DIGITIZER / pkg).rglob("*.ttf")}
    assert on_disk and on_disk <= set(files)


def test_the_stamp_names_are_the_ones_the_service_reads(tmp_path, monkeypatch):
    from digitizer_service import app as _app_object  # noqa: F401
    service = sys.modules["digitizer_service.app"]
    assert build_freeze.BUILD_STAMP == service.BUILD_STAMP

    stamp = build_freeze.make_stamp(commit="a" * 40, release="v9.9.9")
    assert stamp["commit"] == "a" * 40 and stamp["release"] == "v9.9.9"
    (tmp_path / service.BUILD_STAMP).write_text(json.dumps(stamp), encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(service, "_ENGINE_DIR", tmp_path)
    got = service._read_engine_checkout()
    assert (got["commit"], got["release"]) == ("a" * 40, "v9.9.9")


def test_a_build_with_no_release_name_is_named_after_its_commit():
    assert build_freeze.make_stamp(commit="0123456789abcdef" + "0" * 24)["release"] == "dev-01234567"
    with pytest.raises(SystemExit):
        build_freeze.make_stamp(commit="v1.0.0")           # a tag is not a commit
    with pytest.raises(SystemExit):
        build_freeze.make_stamp(commit="a" * 40, release="claude/some-branch")   # it becomes a file name


def test_the_build_refuses_a_work_directory_inside_the_checkout():
    with pytest.raises(SystemExit, match="inside the checkout"):
        build_freeze.main(["--work", str(DIGITIZER / "build" / "freeze")])


def test_a_hidden_import_is_harmless_only_when_the_tested_env_lacks_it_too():
    out = ('123 WARNING: Hidden import "scipy.special._cdflib" not found!\n'
           "456 WARNING: Hidden import 'tzdata' not found!\n"
           "789 INFO: Analyzing hidden import 'uvicorn.loops.auto'\n")
    names = build_freeze.missing_hidden_imports(out)
    assert names == ["scipy.special._cdflib", "tzdata"]
    judged = build_freeze.judge_hidden_imports(names, importable=lambda n: n == "tzdata")
    assert [(j["module"], j["in_tested_env"]) for j in judged] == [
        ("scipy.special._cdflib", False), ("tzdata", True)]
    assert judged[0]["verdict"].startswith("harmless") and judged[1]["verdict"].startswith("LOST")


def test_the_spikes_two_warnings_are_modules_the_pinned_set_does_not_have():
    """Why both are harmless, as a fact about requirements.txt rather than a
    sentence: neither can be imported by the interpreter the suite runs on,
    so a freeze without them is missing nothing the tested engine had. If a
    pin ever brings one in, this fails and the build has to bundle it."""
    assert not build_freeze.importable_here("scipy.special._cdflib")
    assert not build_freeze.importable_here("tzdata")
    assert build_freeze.importable_here("scipy.special")


def test_nothing_the_service_imports_reads_time_zones_by_name():
    """`tzdata` is what `zoneinfo` needs on Windows. Nothing pins it, so
    nothing here may need it: a `ZoneInfo("...")` would fail on a customer's
    PC, frozen or not."""
    users = [p.relative_to(DIGITIZER).as_posix()
             for pkg in build_freeze.PACKAGES for p in (DIGITIZER / pkg).rglob("*.py")
             if re.search(r"^\s*(import|from)\s+zoneinfo\b", p.read_text(encoding="utf-8"), re.M)]
    assert users == []


def test_the_pth_line_puts_the_pinned_wheels_ahead_of_the_throwaway_venvs(tmp_path, monkeypatch):
    """pip installs PyInstaller's own `packaging` into the throwaway venv; an
    APPENDED path would freeze that copy in place of the pinned one."""
    monkeypatch.setattr(sys, "path", ["/throwaway/site-packages", "/stdlib"])
    exec(build_freeze.pth_line(["/pinned/site-packages"]))  # noqa: S102 -- what `site` does with a .pth line
    assert sys.path == ["/pinned/site-packages", "/throwaway/site-packages", "/stdlib"]
    exec(build_freeze.pth_line(["/pinned/site-packages"]))  # noqa: S102
    assert sys.path.count("/pinned/site-packages") == 1


def test_data_reaches_pyinstaller_at_the_path_it_has_in_the_checkout(tmp_path):
    stage = tmp_path / "stage"
    (stage / "digitizer_core" / "chart_data").mkdir(parents=True)
    (stage / "tessdata").mkdir()
    (stage / build_freeze.BUILD_STAMP).write_text("{}", encoding="utf-8")
    args = build_freeze.pyinstaller_args("app", tmp_path / "entry.py", stage, tmp_path / "dist-studio", tmp_path)
    sep = build_freeze.os.pathsep
    data = [args[i + 1] for i, a in enumerate(args) if a == "--add-data"]
    assert f"{stage / 'digitizer_core'}{sep}digitizer_core" in data
    assert f"{stage / 'tessdata'}{sep}tessdata" in data
    assert f"{stage / build_freeze.BUILD_STAMP}{sep}." in data          # beside the packages
    assert f"{tmp_path / 'dist-studio'}{sep}studio" in data
    assert "--onedir" in args and "--onefile" not in args
    assert args[-1] == str(tmp_path / "entry.py")


def test_prune_removes_only_what_its_table_names(tmp_path):
    internal = tmp_path / "_internal"
    (internal / "cv2").mkdir(parents=True)
    (internal / "cv2" / "opencv_videoio_ffmpeg500_64.dll").write_bytes(b"x" * 10)
    (internal / "cv2" / "cv2.pyd").write_bytes(b"y" * 5)
    cut = build_freeze.prune(internal)
    assert [(c["file"], c["bytes"]) for c in cut] == [("cv2/opencv_videoio_ffmpeg500_64.dll", 10)]
    assert [p.name for p in (internal / "cv2").iterdir()] == ["cv2.pyd"]
    assert build_freeze.prune(internal) == []
    assert all(why for _, why in build_freeze.PRUNE)


def test_the_engine_opens_no_video_so_the_video_plugin_can_go():
    users = [p.relative_to(DIGITIZER).as_posix()
             for pkg in build_freeze.PACKAGES for p in (DIGITIZER / pkg).rglob("*.py")
             if re.search(r"VideoCapture|VideoWriter", p.read_text(encoding="utf-8"))]
    assert users == []


def test_measure_and_zip_keep_the_folder_as_the_zips_top_level(tmp_path):
    folder = tmp_path / "dist" / "embbot-digitizer"
    (folder / "_internal" / "cv2").mkdir(parents=True)
    (folder / "embbot-digitizer.exe").write_bytes(b"a" * 3)
    (folder / "_internal" / "cv2" / "cv2.pyd").write_bytes(b"b" * 7)
    (folder / "_internal" / "base.zip").write_bytes(b"c" * 2)
    size = build_freeze.measure(folder)
    assert (size["bytes"], size["files"]) == (12, 3)
    assert size["largest_entries"][0] == {"entry": "_internal/cv2", "bytes": 7}
    dest = tmp_path / "out.zip"
    assert build_freeze.zip_folder(folder, dest) == dest.stat().st_size
    with zipfile.ZipFile(dest) as z:
        assert sorted(z.namelist()) == ["embbot-digitizer/_internal/base.zip",
                                        "embbot-digitizer/_internal/cv2/cv2.pyd",
                                        "embbot-digitizer/embbot-digitizer.exe"]


def test_the_installer_is_compiled_from_the_build_report_and_keeps_its_identity():
    build_installer = _load_after_siblings("build_installer")
    report = {"name": "embbot-digitizer", "folder": "W/dist/embbot-digitizer",
              "exe": "W/dist/embbot-digitizer/embbot-digitizer.exe", "stamp": {"release": "v1.2.3"}}
    args, setup = build_installer.iscc_args(report, Path("W"))
    assert setup == Path("W") / "embbot-digitizer-v1.2.3-setup.exe"
    assert "/DSourceDir=W/dist/embbot-digitizer" in args and "/DAppVersion=v1.2.3" in args
    assert "/DExeName=embbot-digitizer.exe" in args and args[-1].endswith("installer.iss")
    iss = (DIGITIZER / "packaging" / "installer.iss").read_text(encoding="utf-8")
    # Every define the script demands is one the builder passes.
    assert set(re.findall(r"#ifndef (\w+)\s+#error", iss)) <= {a[2:].split("=")[0] for a in args if a.startswith("/D")}
    # The AppId is the installer's identity across upgrades: changing it
    # installs a second copy beside the first. Pinned so that takes a decision.
    assert "AppId={{E5D491C7-8B84-4FE9-84CF-3737653A83ED}" in iss
    assert "PrivilegesRequired=lowest" in iss


# --------------------------------------------------------------- instrument

def test_the_suite_uses_only_committed_fixtures_and_covers_every_lane():
    routes = [c["route"] for c in freeze_check.SUITE]
    assert {"digitize", "lettering", "digitize-manual"} == set(routes)
    forced = {(c.get("config") or {}).get("forced_class") for c in freeze_check.SUITE if c["route"] == "digitize"}
    assert forced == {None, "gradient", "photo_subject"}
    for case in freeze_check.SUITE:
        if "image" in case:
            assert (DIGITIZER / case["image"]).is_file(), case["image"]
            assert case["image"].startswith("testdata/")
    assert freeze_check.SHIPPED_FORMATS == ("dst", "pes", "exp", "jef", "xxx", "vp3")


def test_jef_is_compared_with_its_clock_zeroed_and_nothing_else_forgiven():
    a = bytes(range(8)) + b"20261112093016" + b"stitches"
    later = bytes(range(8)) + b"20261112093018" + b"stitches"
    moved = bytes(range(8)) + b"20261112093016" + b"stitchez"
    assert freeze_check.comparable_sha("jef", a) == freeze_check.comparable_sha("jef", later)
    assert freeze_check.comparable_sha("jef", a) != freeze_check.comparable_sha("jef", moved)
    assert freeze_check.comparable_sha("dst", a) != freeze_check.comparable_sha("dst", later)


def _export(fmt: str, data: bytes = b"x" * 40) -> dict:
    return {"status": 200, "bytes": len(data), "sha": freeze_check._sha(data),
            "cmp": freeze_check.comparable_sha(fmt, data), "verified": "true"}


def _good_run() -> dict:
    rows = {}
    for case in freeze_check.SUITE:
        row = {"state": "done", "job_s": 1.0, "stitches": 100, "design_sha": "d", "review_sha": "r",
               "warnings": [], "blended_shapes": 3 if case["name"] == "gradient" else 0,
               **{f: _export(f) for f in freeze_check.SHIPPED_FORMATS}}
        if case["route"] == "digitize":
            row["class"] = (case["config"] or {}).get("forced_class") or "flat"
        rows[case["name"]] = row
    return {"capabilities": {"background_removal": False, "ocr": True, "face_priors": True, "sam2": False},
            "engine": {"commit": "a" * 40, "release": "v1", "dirty": False}, "outline_fonts": 33,
            "studio": {"served": True, "status": 200, "app_root": True, "files": 32, "scripts": 30, "bad": []},
            "fixtures": rows}


def test_a_good_frozen_run_has_no_failures_and_compares_equal_to_itself(capsys):
    run = _good_run()
    assert freeze_check.release_failures(run, expect_commit="a" * 40, expect_release="v1") == []
    assert freeze_check.compare(run, json.loads(json.dumps(run))) == 0


@pytest.mark.parametrize("break_it, says", [
    (lambda r: r["engine"].update(commit="f" * 40), "engine.commit"),
    (lambda r: r["engine"].update(release=None), "engine.release"),
    (lambda r: r["capabilities"].update(ocr=False), "tessdata"),
    (lambda r: r["capabilities"].update(face_priors=False), "face model"),
    (lambda r: r.update(outline_fonts=0), "outline fonts"),
    (lambda r: r.update(studio={"served": False, "status": 404}), "not the Studio"),
    (lambda r: r["studio"].update(bad=["engine/dst.js: HTTP 200, text/plain, 9 B"]), "engine/dst.js"),
    (lambda r: r["fixtures"].pop("photo"), "photo: not run"),
    (lambda r: r["fixtures"]["lettering"].update(state="error", error="boom"), "lettering: error, boom"),
    (lambda r: r["fixtures"]["gradient"].update(blended_shapes=0), "blend tier"),
    (lambda r: r["fixtures"]["gradient"].update({"class": "flat"}), "classified 'flat'"),
    (lambda r: r["fixtures"]["manual"]["vp3"].update(verified="false"), "manual: vp3"),
    (lambda r: r["fixtures"]["flat"]["xxx"].update(status=500), "flat: xxx"),
])
def test_each_way_a_frozen_run_can_be_wrong_is_named(break_it, says):
    run = _good_run()
    break_it(run)
    failures = freeze_check.release_failures(run, expect_commit="a" * 40, expect_release="v1")
    assert len(failures) == 1 and says in failures[0], failures


@pytest.mark.parametrize("break_it", [
    lambda r: r["capabilities"].update(ocr=False),
    lambda r: r["fixtures"]["photo"].update(design_sha="other"),
    lambda r: r["fixtures"]["photo"].update(warnings=["NEW"]),
    lambda r: r["fixtures"]["flat"]["pes"].update(cmp="other"),
    lambda r: r["fixtures"]["flat"]["jef"].update(bytes=41),
    lambda r: r["fixtures"].pop("manual"),
])
def test_compare_counts_every_kind_of_difference(break_it, capsys):
    a, b = _good_run(), _good_run()
    break_it(b)
    assert freeze_check.compare(a, b) >= 1


def test_two_failed_jobs_are_not_two_identical_designs(capsys):
    a, b = _good_run(), _good_run()
    for run in (a, b):
        run["fixtures"]["photo"] = {"state": "error", "job_s": 1.0, "error": "same crash"}
    assert freeze_check.compare(a, b) >= 1


# ----------------------------------------------------------------- workflow

def _workflow() -> dict:
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # YAML 1.1 reads the bare key `on` as the boolean True.
    return {"on": doc.get("on", doc.get(True)), **{k: v for k, v in doc.items() if k not in ("on", True)}}


def test_the_windows_build_runs_on_a_version_tag_or_by_hand_and_never_on_a_pr():
    """An hour of a Windows runner per push is not a PR check, and a job that
    never reports on a PR must never become a required one. This also keeps
    a temporary branch trigger (how the workflow was proved before it was on
    main) from being merged."""
    on = _workflow()["on"]
    assert set(on) == {"push", "workflow_dispatch"}
    assert set(on["push"]) == {"tags"}
    assert on["push"]["tags"] == ["v*"]


def test_the_windows_build_is_windows_python_312_and_the_two_scripts():
    wf = _workflow()
    (job,) = wf["jobs"].values()
    assert job["runs-on"] == "windows-latest"
    assert job["timeout-minutes"] <= 90
    assert wf["permissions"] == {"contents": "read"}
    steps = job["steps"]
    py = next(s for s in steps if str(s.get("uses", "")).startswith("actions/setup-python@"))
    assert str(py["with"]["python-version"]) == "3.12"
    runs = [s["run"] for s in steps if "run" in s]
    assert any("packaging/build_freeze.py" in r for r in runs)
    assert any("packaging/release_smoke.py" in r for r in runs)
    # PowerShell reports only the LAST command's exit code, so a step that ran
    # two commands could go green over a failed first one (the `pytest | tail`
    # trap in another shell). One command per step.
    for r in runs:
        commands = [ln for ln in r.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]
        assert len(commands) == 1, r


def test_the_shipped_exe_is_the_launcher_and_is_proved_to_keep_one_origin():
    """Saved designs are localStorage, keyed by origin: the app a customer
    starts must come back on the one port. Since 2026-11-13 the launcher IS the
    frozen entry (Kent: "Swap in follow-up PR"), so the job proves the folder it
    ships with `one_origin_smoke.py`, before anything is uploaded."""
    assert build_freeze.parser().get_default("entry") == build_freeze.DIGITIZER / "embbot_launcher.py"
    assert not (DIGITIZER / "packaging" / "freeze_entry.py").exists()
    steps = _workflow()["jobs"]["windows-app"]["steps"]
    runs = [s.get("run", "") for s in steps]
    freezes = [i for i, r in enumerate(runs) if "packaging/build_freeze.py" in r]
    smoke = next(i for i, r in enumerate(runs) if "packaging/one_origin_smoke.py" in r)
    uploads = [i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/upload-artifact@")
               and s.get("if") != "always()"]
    assert len(freezes) == 1 and "--entry" not in runs[freezes[0]], "one folder, the one that ships"
    assert r"freeze\build_report.json" in runs[smoke] and freezes[0] < smoke
    assert uploads and smoke < min(uploads), "a zip whose app strands saved designs must not be uploaded"


def test_the_release_checks_start_the_shipped_exe_as_its_own_service():
    release_smoke = _load_after_siblings("release_smoke")
    assert release_smoke.frozen_service(Path("app.exe"), 8732) == ["app.exe", "--serve", "--port", "8732"]
    for script in ("release_smoke", "build_installer"):
        text = (DIGITIZER / "packaging" / f"{script}.py").read_text(encoding="utf-8")
        assert "[str(exe), str(" not in text, f"{script} still starts the exe as `<exe> <port>`"


def test_the_origin_smoke_names_every_check_in_its_summary():
    smoke = _load_after_siblings("one_origin_smoke")
    assert smoke.L.PORT == 8721
    rec = {"port": 8721, "origin": "http://127.0.0.1:8721", "token": "t",
           "first": {"ready_s": 2.0, "service_pids": [1], "app_ports": [8721], "commit": "abc", "port_freed_s": 0.6},
           "write": {"channel": "msedge", "projectIds": ["p"], "origin": "http://127.0.0.1:8721"},
           "other_origin": {"origin": "http://127.0.0.1:9", "projectIds": [], "marker": None},
           "second": {"exit": 0, "seconds": 0.7, "service_pids": [1], "first_alive": True},
           "restart": {"ready_s": 2.0, "commit": "abc", "service_pids": [2]},
           "read": {"origin": "http://127.0.0.1:8721", "marker": "t", "projectIds": ["p"]},
           "busy": {"exit": 3, "seconds": 0.9, "foreign_pid": [9], "holder_after": [9], "new_ports": [],
                    "message": "EMB-Bot could not start"}}
    text = smoke.summary_markdown([], rec, 30)
    assert "**PASS**" in text and "marker found" in text and "launcher exit 3" in text
    assert "EMB-Bot could not start" in text
    assert "**FAIL**" in smoke.summary_markdown(["x"], rec, 30)


def test_the_shipped_exe_is_built_for_the_gui_subsystem():
    """A `--console` build opens a console window on every double-click, and it
    stays open behind the browser. `--windowed` is the GUI subsystem; the
    launcher's `--console` re-attaches the terminal it was started from."""
    args = build_freeze.pyinstaller_args("app", Path("entry.py"), Path("."), Path("studio"), Path("."))
    assert "--windowed" in args and "--console" not in args


def test_the_origin_smoke_reads_the_subsystem_from_the_exe_header(tmp_path):
    smoke = _load_after_siblings("one_origin_smoke")

    def pe(subsystem: int, magic: int) -> bytes:
        optional = magic.to_bytes(2, "little") + bytes(66) + subsystem.to_bytes(2, "little") + bytes(30)
        return (b"MZ" + bytes(58) + (64).to_bytes(4, "little") + b"PE\0\0" + bytes(20) + optional)

    for magic in (0x10B, 0x20B):  # PE32, PE32+
        gui, console = tmp_path / "gui.exe", tmp_path / "console.exe"
        gui.write_bytes(pe(smoke.SUBSYSTEM_GUI, magic))
        console.write_bytes(pe(smoke.SUBSYSTEM_CONSOLE, magic))
        assert smoke.pe_subsystem(gui) == 2 and smoke.pe_subsystem(console) == 3
    (tmp_path / "not.exe").write_bytes(b"hello")
    assert smoke.pe_subsystem(tmp_path / "not.exe") is None
    assert smoke.pe_subsystem(tmp_path / "missing.exe") is None


@pytest.mark.skipif(sys.platform != "win32", reason="needs a real Windows exe")
def test_the_header_reader_tells_python_from_pythonw():
    smoke = _load_after_siblings("one_origin_smoke")
    exe = Path(sys.executable)
    assert smoke.pe_subsystem(exe) == smoke.SUBSYSTEM_CONSOLE
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.is_file():
        assert smoke.pe_subsystem(pythonw) == smoke.SUBSYSTEM_GUI


def test_the_origin_smoke_checks_the_exe_subsystem_and_the_log_lines():
    text = (DIGITIZER / "packaging" / "one_origin_smoke.py").read_text(encoding="utf-8")
    for needle in ("pe_subsystem(exe)", "launcher: started:", "new instance",
                   "reused the running instance", "launcher: stopped:", "already running"):
        assert needle in text, needle
