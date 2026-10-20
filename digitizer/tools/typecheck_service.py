"""Advisory mypy run over digitizer_service only (not wired into CI).

    python -m pip install -e ".[service,typecheck]"
    python tools/typecheck_service.py

Config lives in pyproject.toml ([tool.mypy]). Always exits 0 so it can never
block anything; read the output, and the printed mypy status line.
"""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rc = subprocess.run([sys.executable, "-m", "mypy"], cwd=root).returncode
print(f"mypy exit code {rc} (advisory; this script exits 0)")
