"""`digitizer_core/sam2_worker.py`'s contract, tested WITHOUT a SAM2 install.

The worker's real work (loading SAM2, running automatic mask generation)
cannot run in the shared venv by design — that is the whole point of
`digitizer/sam2_isolated/`. What IS testable here, and what this file pins,
is everything the caller depends on that happens before any heavy import:
the argv contract, the exit codes for every argument-level failure, the
checkpoint table, and the isolation guarantee itself (zero digitizer_core
imports, so the script runs standalone in a venv with no digitizer_core
installed). The real end-to-end run is Task 6's manual acceptance step.
"""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from digitizer_core import sam2_worker

WORKER = Path(sam2_worker.__file__).resolve()


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(WORKER), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_wrong_argument_count_exits_2():
    proc = _run("in.png", "out.npz")
    assert proc.returncode == 2
    assert "usage: sam2_worker.py" in proc.stderr


def test_unknown_checkpoint_tier_exits_2():
    proc = _run("in.png", "out.npz", "enormous", "16", "9")
    assert proc.returncode == 2
    assert "unknown checkpoint tier" in proc.stderr


def test_non_numeric_grid_argument_exits_2():
    proc = _run("in.png", "out.npz", "tiny", "sixteen", "9")
    assert proc.returncode == 2
    assert "bad numeric argument" in proc.stderr


def test_zero_points_per_side_exits_2():
    proc = _run("in.png", "out.npz", "tiny", "0", "9")
    assert proc.returncode == 2
    assert "points_per_side must be >= 1" in proc.stderr


@pytest.mark.skipif(
    importlib.util.find_spec("sam2") is not None,
    reason="sam2 is importable in this interpreter, so the import cannot fail",
)
def test_missing_sam2_dependency_exits_3():
    """Run under the SHARED venv, where sam2/torch are deliberately absent:
    the worker must report an honest import failure with exit code 3, not
    a traceback, so the seam can turn it into one plain-English reason.

    Relies on the "tiny" checkpoint already being cached on this machine
    (Task 6's manual acceptance run populated it) so the new fail-fast
    checkpoint-cache check below does not short-circuit this case at exit 4
    instead — see test_missing_checkpoint_cache_exits_4_before_import for
    that case, forced deterministically via SAM2_CHECKPOINT_DIR."""
    proc = _run("in.png", "out.npz", "tiny", "16", "9")
    assert proc.returncode == 3
    assert "sam2_worker: import failed" in proc.stderr


def test_missing_checkpoint_cache_exits_4_before_import(tmp_path):
    """The Task-6 timeout fix (I3): when the checkpoint has never been
    cached, the worker must refuse fast with the honest, actionable exit 4
    reason — NOT attempt a download that the caller's subprocess timeout
    would kill mid-transfer (orphaning a `.part` file and repeating the
    same doomed cycle on every later job forever). Forces "not cached"
    deterministically via SAM2_CHECKPOINT_DIR pointed at an empty
    directory, independent of this machine's real cache state."""
    import os

    env = {**os.environ, "SAM2_CHECKPOINT_DIR": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(WORKER), "in.png", "out.npz", "tiny", "16", "9"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 4
    assert "checkpoint not cached" in proc.stderr
    assert "pre-warm" in proc.stderr
    assert "sam2_isolated/README.md" in proc.stderr
    # Never got as far as trying to read the (nonexistent) input image or
    # importing torch — the honest, fast-failure guarantee this test pins.
    assert "import failed" not in proc.stderr


def test_checkpoint_is_cached_reads_the_real_cache_state(tmp_path, monkeypatch):
    monkeypatch.setattr(sam2_worker, "_cache_dir", lambda: tmp_path)
    assert sam2_worker._checkpoint_is_cached("tiny") is False

    dest = tmp_path / sam2_worker.CHECKPOINTS["tiny"][0]
    dest.write_bytes(b"")
    assert sam2_worker._checkpoint_is_cached("tiny") is False, (
        "a zero-byte file must not count as cached"
    )

    dest.write_bytes(b"not empty")
    assert sam2_worker._checkpoint_is_cached("tiny") is True


def test_worker_imports_nothing_from_digitizer_core():
    """The isolation guarantee: this script runs under a venv that has no
    digitizer_core installed, so a single package-relative or absolute
    digitizer_core import would break it at runtime in exactly the
    environment it exists to serve. Same guarantee rembg_worker.py's own
    docstring makes."""
    tree = ast.parse(WORKER.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in a standalone worker script"
            imported.append(node.module or "")
    assert not [m for m in imported if m.split(".")[0] == "digitizer_core"]


def test_checkpoint_table_is_meta_hosted_and_self_consistent():
    """Guards the one substitution this integration must never suffer: the
    unrelated third-party PyPI package named `sam2`, or a mirror of its
    weights. Meta's own release host is the only allowed source."""
    assert sam2_worker.CHECKPOINT_BASE_URL.startswith(
        "https://dl.fbaipublicfiles.com/segment_anything_2/"
    )
    assert sam2_worker.CHECKPOINTS["tiny"] == (
        "sam2.1_hiera_tiny.pt",
        "configs/sam2.1/sam2.1_hiera_t.yaml",
    )
    for tier, (filename, config_name) in sam2_worker.CHECKPOINTS.items():
        assert filename.endswith(".pt"), tier
        assert config_name.startswith("configs/sam2.1/"), tier
        assert config_name.endswith(".yaml"), tier
