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


# The photo lane's prep (rembg, `stage1_photo_prep`) shells out to a venv
# the primary checkout carries under `digitizer/rembg_isolated/venv`,
# gitignored -- so a worktree of an older commit has none, and a photo-class
# fixture's ref design SKIPS prep while today's runs it. Found 2026-09-30 on
# the evening sitting: tires (photo_scene) read 2,500 stitches from the ref
# worktree and 2,646 from the same commit with the venv linked, and Kent's
# one "before better" of the night was that pair -- the un-prepped lane's
# clean cartoon edges against the prepped lane's ragged matte. The link
# makes the ref engine run the same lane as today's; where it cannot be
# made (no venv here, or a filesystem without symlinks) the runner says so
# and the page keeps its confound badge.
PHOTO_PREP_VENV = Path("digitizer") / "rembg_isolated" / "venv"


def link_photo_prep(repo_root, worktree) -> bool:
    """Symlink the primary checkout's photo-prep venv into `worktree`; ->
    whether the ref engine there now has one. Never copies, never fails a
    run: an OSError (Windows without symlink rights) reads as False."""
    src = Path(repo_root).resolve() / PHOTO_PREP_VENV
    dst = Path(worktree).resolve() / PHOTO_PREP_VENV
    if not src.is_dir():
        return False
    if dst.exists():
        return True
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src, target_is_directory=True)
    except OSError:
        return False
    return True


def add_worktree(repo_root, ref: str, dest) -> Path:
    path = guard_scratch(dest, repo_root)
    subprocess.run(["git", "-C", str(repo_root), "worktree", "add", "--detach",
                    str(path), ref], check=True, capture_output=True, text=True)
    return path


def remove_worktree(repo_root, dest) -> None:
    path = guard_scratch(dest, repo_root)
    subprocess.run(["git", "-C", str(repo_root), "worktree", "remove", "--force",
                    str(path)], check=False, capture_output=True, text=True)


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
