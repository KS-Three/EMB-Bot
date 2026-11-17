"""No multi-item `with` near CPython's static block limit.

Each manager of `with a, b, c:` is one statically nested block. CPython 3.12.3
(the stock Ubuntu 24.04 build, which every cloud session runs) allows 20;
CI's later 3.12 patch release takes one more. On 2026-11-17 `plan_stitches`
held 21, so `import digitizer_core` raised `SyntaxError: too many statically
nested blocks` on 3.12.3 while CI stayed green. The scopes moved to one
`contextlib.ExitStack`; this keeps a new one from growing back.
"""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
#: Far under the interpreter's 20, so the body keeps room for its own blocks.
MAX_WITH_ITEMS = 10
FILES = sorted(p for d in ("digitizer_core", "digitizer_service")
               for p in (ROOT / d).rglob("*.py"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_with_statement_near_the_block_limit(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    worst = max((len(n.items) for n in ast.walk(tree)
                 if isinstance(n, (ast.With, ast.AsyncWith))), default=0)
    assert worst <= MAX_WITH_ITEMS, (
        f"{path.name}: a `with` enters {worst} managers; use contextlib.ExitStack")
