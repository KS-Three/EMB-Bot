"""Every script in `digitizer/tools/` and the `.py` files in `tools/` answers `--help` with its usage text and
exits 0, without doing the tool's work.

Before this, 61 of them had a `__main__` block that ignored the flag, so
`tool.py --help` quietly ran the whole census (and some write files).
The check is a subprocess per tool: it proves the script parses, its
top-level imports resolve, and the help guard fires before any work.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

DIGITIZER = Path(__file__).resolve().parent.parent
TOOLS = sorted(
    [p for p in (DIGITIZER / "tools").glob("*.py") if p.name != "_console.py"]
    + list((DIGITIZER.parent / "tools").glob("*.py"))
)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_tool_help_exits_zero(tool, tmp_path):
    env = dict(os.environ, PYTHONPATH=str(DIGITIZER), PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, str(tool), "--help"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
    )
    assert r.returncode == 0, r.stderr[-800:]
    assert r.stdout.strip(), f"{tool.name} --help printed nothing"
    assert list(tmp_path.iterdir()) == [], "--help wrote files"
