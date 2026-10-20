"""Every script in `digitizer/tools/` and the `.py` files in `tools/` answers `--help` with its usage text and
exits 0, without doing the tool's work.

Before this, 61 of them had a `__main__` block that ignored the flag, so
`tool.py --help` quietly ran the whole census (and some write files).
The check is a subprocess per tool: it proves the script parses, its
top-level imports resolve, and the help guard fires before any work.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

#: Seconds a tool gets to answer `--help`. Measured 2026-10-15 on Kent's loaded
#: laptop, all 205 tools one at a time: the slowest honest answer was 4.75 s
#: (3.2 s with the machine quiet), nearly all of it `import digitizer_core`
#: (about 2 s); ~80 tools answer in under 1 s. The one tool far outside that
#: band, `stem_trace.py` (25.9 s, over 120 s when the laptop is busier), was
#: not slow to import: it had no `--help` guard and ran the whole digitize. The
#: old 120 s let that pass for a month. 30 s is 6x the slowest measured
#: answer, so a CI runner twice as slow and four shards in parallel still pass,
#: and it is a quarter of the old figure, so a tool that starts doing real work
#: on `--help` fails here instead of hiding behind the timeout.
HELP_TIMEOUT_S = 30

DIGITIZER = Path(__file__).resolve().parent.parent
TOOLS = sorted(
    [p for p in (DIGITIZER / "tools").glob("*.py") if p.name != "_console.py"]
    + list((DIGITIZER.parent / "tools").glob("*.py"))
)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_tool_help_exits_zero(tool, tmp_path):
    env = dict(os.environ, PYTHONPATH=str(DIGITIZER), PYTHONIOENCODING="utf-8")
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            [sys.executable, str(tool), "--help"],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=HELP_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{tool.name} --help took over {HELP_TIMEOUT_S} s: it is importing something heavy "
            "or running its work before the help guard. Move the heavy imports into main() "
            "or answer -h/--help first."
        )
    print(f"{tool.name} --help {time.monotonic() - t0:.2f}s")
    assert r.returncode == 0, r.stderr[-800:]
    assert r.stdout.strip(), f"{tool.name} --help printed nothing"
    assert list(tmp_path.iterdir()) == [], "--help wrote files"


#: These four parse `argv` by hand and had no `--help` branch, so the flag was
#: read as data: `stem_trace.py` ran the full digitize (25.9 s), the other three
#: treated "--help" as a corpus case name that matched nothing and passed on
#: an empty table. They print their module docstring now; this pins that,
#: because the exit-zero test above cannot tell usage from a quiet no-op.
HAND_PARSED = ["stem_trace.py", "fill_score_agreement.py", "satin_islands.py", "trim_census.py"]


@pytest.mark.parametrize("name", HAND_PARSED)
def test_hand_parsed_tool_prints_its_docstring(name, tmp_path):
    tool = DIGITIZER / "tools" / name
    doc = ast.get_docstring(ast.parse(tool.read_text(encoding="utf-8")), clean=False).strip()
    env = dict(os.environ, PYTHONPATH=str(DIGITIZER), PYTHONIOENCODING="utf-8")
    for flag in ("--help", "-h"):
        r = subprocess.run(
            [sys.executable, str(tool), flag],
            cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8",
            timeout=HELP_TIMEOUT_S, stdin=subprocess.DEVNULL,
        )
        assert r.returncode == 0, r.stderr[-800:]
        # read_text and the captured stdout both fold CRLF to LF, so a plain compare is exact.
        assert r.stdout.strip() == doc
