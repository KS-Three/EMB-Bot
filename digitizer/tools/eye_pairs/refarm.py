"""Run an OLDER engine without importing it beside today's.

Two engines cannot share one interpreter, so the ref arm is a subprocess: the
main checkout's python, working directory = the old ref's `digitizer/`, and a
driver that writes the Design dict to a file. Only that dict comes back —
which is why the ref arm gets the Design-only metrics and nothing else.

`guard_scratch` exists because of a real loss: `git worktree add` with an
EMPTY path variable, run from inside a lane, emptied that lane's checkout
(memory `worktree-add-empty-var-wipes-cwd`). The path is validated before git
ever sees it, and it may never be inside the repository.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

DRIVER = r"""
import json, os, sys
root = os.path.normcase(os.path.realpath(os.getcwd()))
sys.path.insert(0, root)
import digitizer_core
found = os.path.normcase(os.path.realpath(digitizer_core.__file__))
if not found.startswith(root + os.sep):
    sys.exit("REFUSED: digitizer_core resolved to %s, not the ref engine under %s"
             % (found, root))
from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
image, out, width, garment, colors = sys.argv[1:6]
cfg = PipelineConfig(target_width_mm=float(width), garment_id=garment,
                     max_colors=int(colors))
_result, plan = digitize(image, cfg)
with open(out, "w", encoding="utf-8") as fh:
    json.dump(plan_to_design(plan), fh)
"""


def guard_scratch(dest, repo_root) -> Path:
    if dest is None or not str(dest).strip():
        raise ValueError("worktree path is empty — refusing to call git")
    path = Path(str(dest).strip())
    if not path.is_absolute():
        raise ValueError(f"worktree path must be absolute, got {dest!r}")
    path, repo = path.resolve(), Path(repo_root).resolve()
    if path == repo or repo in path.parents:
        raise ValueError(f"worktree path {path} is inside the repository {repo}")
    if path in repo.parents:
        # The other direction: a dest the repo is INSIDE of. The default
        # runner rmtree's the dest it is handed, so this is the difference
        # between a scratch dir and every checkout under it.
        raise ValueError(f"worktree path {path} contains the repository {repo}")
    return path


def add_worktree(repo_root, ref: str, dest) -> Path:
    path = guard_scratch(dest, repo_root)
    subprocess.run(["git", "-C", str(repo_root), "worktree", "add", "--detach",
                    str(path), ref], check=True, capture_output=True, text=True)
    return path


def remove_worktree(repo_root, dest) -> None:
    path = guard_scratch(dest, repo_root)
    subprocess.run(["git", "-C", str(repo_root), "worktree", "remove", "--force",
                    str(path)], check=False, capture_output=True, text=True)


def rembg_venv_present(digitizer_dir) -> bool:
    """Would the engine under this `digitizer/` find its isolated rembg
    interpreter? The same two paths `stage1_photo_prep` looks at — restated
    rather than imported, because the question is also asked of ANOTHER
    checkout's tree. A fresh `git worktree add` never has one: the venv is
    untracked, so an old engine run from a worktree skips photo prep for an
    environment reason, not an engine one."""
    venv = Path(digitizer_dir) / "rembg_isolated" / "venv"
    return any((venv / rel).exists() for rel in ("bin/python", "Scripts/python.exe"))


def requirements_differ(repo_root, ref: str) -> bool:
    """Has `digitizer/requirements.txt` changed between `ref` and HEAD? The
    ref arm runs the old commit's SOURCE under today's venv, so changed pins
    mean the old engine ran against libraries it was not written for."""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--quiet", ref, "HEAD", "--",
         "digitizer/requirements.txt"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    # 0 = same, 1 = differs. Anything else (128: no such ref) is NOT an
    # answer, and reading it as one would turn a typo into a measured fact.
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"could not compare requirements.txt at {ref!r} with HEAD: "
                           + (proc.stderr or "").strip()[-300:])
    return proc.returncode == 1


def ref_environment(repo_root, ref: str, *, main_digitizer, ref_digitizer) -> dict:
    """The facts that decide whether a ref arm differs from today's for a
    reason that is not the engine. Measured when the ref worktree exists and
    stored on each row it produces; `analysis.ref_confound` reads them."""
    return {"ref": ref,
            "rembg_venv_main": rembg_venv_present(main_digitizer),
            "rembg_venv_ref": rembg_venv_present(ref_digitizer),
            "requirements_differ": requirements_differ(repo_root, ref)}


def run_ref_design(python, engine_dir, image, width_mm: float, garment: str,
                   max_colors: int, timeout_s: float = 3600.0) -> dict:
    fd, out = tempfile.mkstemp(suffix=".json", prefix="eye_pairs_ref_")
    os.close(fd)
    try:
        proc = subprocess.run(
            [str(python), "-c", DRIVER, str(image), out, str(width_mm), garment,
             str(max_colors)],
            cwd=str(engine_dir), capture_output=True, text=True, timeout=timeout_s)
        if proc.returncode != 0:
            raise RuntimeError("ref engine failed: " + (proc.stderr or proc.stdout)[-600:])
        return json.loads(Path(out).read_text(encoding="utf-8"))
    finally:
        Path(out).unlink(missing_ok=True)
