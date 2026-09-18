import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import refarm  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("bad", ["", "   ", None, "relative/path"])
def test_an_empty_or_relative_worktree_path_is_refused(bad):
    with pytest.raises(ValueError):
        refarm.guard_scratch(bad, REPO)


def test_a_worktree_inside_the_repo_is_refused():
    with pytest.raises(ValueError, match="inside"):
        refarm.guard_scratch(REPO / ".claude" / "worktrees" / "x", REPO)
    with pytest.raises(ValueError, match="inside"):
        refarm.guard_scratch(REPO, REPO)


def test_an_ancestor_of_the_repo_is_refused_too():
    """Review finding 14 (2026-09-17): the guard rejected a path INSIDE the
    repo but not one the repo is inside of — and the default runner rmtree's
    whatever the guard accepts. Memory `worktree-add-empty-var-wipes-cwd`
    records what that class of path costs."""
    with pytest.raises(ValueError, match="contains"):
        refarm.guard_scratch(REPO.parent, REPO)
    with pytest.raises(ValueError, match="contains"):
        refarm.guard_scratch(REPO.parents[1], REPO)


def test_a_scratch_path_outside_the_repo_is_accepted(tmp_path):
    assert refarm.guard_scratch(tmp_path / "wt", REPO) == (tmp_path / "wt").resolve()


def git(repo: Path, *args: str) -> str:
    """Real git in a THROWAWAY repo under tmp_path — never the checkout the
    tests run from, which may have a live render holding a ref worktree."""
    import subprocess
    proc = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip()


@pytest.fixture()
def tiny_repo(tmp_path):
    """Three commits: `old` and `same` share a requirements.txt, HEAD does not."""
    repo = tmp_path / "repo"
    (repo / "digitizer").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "digitizer" / "requirements.txt").write_text("numpy==2.5.0\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "old")
    old = git(repo, "rev-parse", "--short", "HEAD")
    (repo / "README").write_text("unrelated\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "same pins")
    same = git(repo, "rev-parse", "--short", "HEAD")
    return repo, old, same


def test_requirements_differ_is_measured_with_git_not_remembered(tiny_repo):
    """Review 2026-09-17: the ref arm runs an old commit's SOURCE under
    today's venv, and the only check that the pins still matched was a
    sentence in the spec written on the day it was true."""
    repo, old, same = tiny_repo
    assert refarm.requirements_differ(repo, old) is False
    (repo / "digitizer" / "requirements.txt").write_text("numpy==2.5.1\n")
    git(repo, "commit", "-q", "-am", "bump numpy")
    assert refarm.requirements_differ(repo, old) is True
    assert refarm.requirements_differ(repo, same) is True
    assert refarm.requirements_differ(repo, "HEAD") is False


def test_an_unknown_ref_is_an_error_not_a_clean_bill(tiny_repo):
    """`git diff --quiet` exits 1 for "differs" and 128 for "no such ref".
    Reading anything non-zero as one answer, or anything but 1 as "same",
    turns a typo into a measured fact."""
    repo, _old, _same = tiny_repo
    with pytest.raises(RuntimeError, match="requirements"):
        refarm.requirements_differ(repo, "0000000")


@pytest.mark.parametrize("rel", ["bin/python", "Scripts/python.exe"])
def test_the_rembg_venv_is_found_where_the_engine_looks_for_it(tmp_path, rel):
    digitizer = tmp_path / "digitizer"
    assert refarm.rembg_venv_present(digitizer) is False
    (digitizer / "rembg_isolated").mkdir(parents=True)          # README only: a fresh worktree
    assert refarm.rembg_venv_present(digitizer) is False
    exe = digitizer / "rembg_isolated" / "venv" / rel
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert refarm.rembg_venv_present(digitizer) is True


def test_the_ref_environment_is_three_measured_facts(tiny_repo, tmp_path):
    repo, old, _same = tiny_repo
    main, ref = tmp_path / "main_digitizer", tmp_path / "ref_digitizer"
    exe = main / "rembg_isolated" / "venv" / "Scripts" / "python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    ref.mkdir()
    assert refarm.ref_environment(repo, old, main_digitizer=main, ref_digitizer=ref) == {
        "ref": old, "rembg_venv_main": True, "rembg_venv_ref": False,
        "requirements_differ": False}


def test_the_default_runner_measures_the_worktree_it_actually_built(tiny_repo, tmp_path):
    """The glue, run for real: a worktree of the throwaway repo, under a
    scratch dir of the test's own."""
    from tools.eye_pairs import __main__ as cli
    repo, old, _same = tiny_repo
    exe = repo / "digitizer" / "rembg_isolated" / "venv" / "Scripts" / "python.exe"
    exe.parent.mkdir(parents=True)                  # untracked, as the real venv is
    exe.write_text("")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    _runner, closer, env = cli._default_ref_runner(old, repo=repo, scratch=scratch)
    dest = scratch / f"eye-pairs-ref-{old}"
    try:
        assert (dest / "digitizer" / "requirements.txt").exists()
        # The checkout has the venv; a fresh worktree of it never does.
        assert env == {"ref": old, "rembg_venv_main": True, "rembg_venv_ref": False,
                       "requirements_differ": False}
    finally:
        closer()
    assert not dest.exists()


def stub_engine(root: Path) -> Path:
    """A fake `digitizer_core` that answers with what it was asked."""
    pkg = root / "digitizer_core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "config.py").write_text(textwrap.dedent("""
        class PipelineConfig:
            def __init__(self, **kw):
                self.kw = kw
    """))
    (pkg / "pipeline.py").write_text("def digitize(image, cfg):\n    return None, (image, cfg.kw)\n")
    (pkg / "adapter.py").write_text(textwrap.dedent("""
        def plan_to_design(plan):
            image, kw = plan
            return {"stitches": [{"x": 0, "y": 0, "type": "end"}], "colors": [],
                    "widthMM": kw["target_width_mm"], "asked": kw, "image": image}
    """))
    return root


def test_the_driver_runs_the_engine_in_its_working_directory(tmp_path):
    engine = stub_engine(tmp_path / "engine")
    design = refarm.run_ref_design(sys.executable, engine, tmp_path / "art.png",
                                   92.5, "patch", 6)
    assert design["asked"] == {"target_width_mm": 92.5, "garment_id": "patch",
                               "max_colors": 6}
    assert design["widthMM"] == 92.5


def test_an_engine_that_dies_writing_undecodable_bytes_still_says_why(tmp_path):
    """Review 2026-09-17, reproduced on Python 3.14.6 / cp1252: `text=True`
    with no `encoding` decodes the child's stderr in a reader THREAD using
    the locale codec. One byte that codec cannot map kills the thread, so
    `proc.stderr` comes back None and the reason the old engine died is
    lost — or the error handler itself dies on `None[-600:]`. 0x81 is
    unmapped in cp1252 and an invalid start byte in UTF-8, so this is red on
    Kent's box and on CI alike."""
    pkg = tmp_path / "engine" / "digitizer_core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "import sys\n"
        "sys.stderr.buffer.write(b'\\x81\\x8d the old engine blew up\\n')\n"
        "sys.stderr.flush()\n"
        "sys.exit(3)\n")
    with pytest.raises(RuntimeError, match="the old engine blew up"):
        refarm.run_ref_design(sys.executable, tmp_path / "engine", tmp_path / "art.png",
                              80.0, "left_chest", 6)


def test_every_child_process_is_decoded_the_same_lenient_way(tiny_repo, tmp_path, monkeypatch):
    """git's messages carry paths, and Kent's contain whatever his folders
    are called. Every call is real; the spy only records how it was asked."""
    import subprocess
    repo, old, _same = tiny_repo
    seen = []
    real = subprocess.run

    def spy(cmd, **kw):
        seen.append((cmd[0] if cmd[0] == "git" else "python", kw))
        return real(cmd, **kw)

    monkeypatch.setattr(refarm.subprocess, "run", spy)
    wt = refarm.add_worktree(repo, old, tmp_path / "wt")
    refarm.requirements_differ(repo, old)
    refarm.remove_worktree(repo, wt)
    refarm.run_ref_design(sys.executable, stub_engine(tmp_path / "engine"),
                          tmp_path / "art.png", 80.0, "left_chest", 6)
    assert len(seen) >= 4
    for who, kw in seen:
        assert (kw.get("encoding"), kw.get("errors")) == ("utf-8", "replace"), who


def test_the_driver_refuses_to_run_todays_engine_by_accident(tmp_path):
    """No `digitizer_core` in the working directory: the import would fall
    through to the INSTALLED package — today's engine — and the '08-27 arm'
    would silently be the base arm again. The driver must refuse instead."""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="REFUSED|No module named"):
        refarm.run_ref_design(sys.executable, empty, tmp_path / "art.png",
                              80.0, "left_chest", 6)
