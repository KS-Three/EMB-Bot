"""A permanent guard for the fix in `conftest.py`'s `client` fixture.

`digitizer_service.app` holds `registry = JobRegistry(workers=1)` as a
module-level singleton, and the app's `lifespan` shuts that pool down
permanently on exit. So the SECOND `TestClient(app)` context to close in a
process leaves every later job stuck in `queued`, and any module that builds
its own client breaks the modules scheduled after it in the same xdist worker.

That was not hypothetical: two modules had byte-identical `scope="module"`
client fixtures, and CI went red twice in a row (13 failures in
`test_service.py`, `RuntimeError: cannot schedule new futures after shutdown`
and `assert 'queued' == 'done'`) while every serial run stayed green.

The fix is one session-scoped `client` in `conftest.py`. It is invisible while
it holds, which is exactly why it needs a tripwire: re-adding a per-module
client would reintroduce an INTERMITTENT failure that depends on how xdist
happens to distribute modules that day. Add users to the shared fixture
instead.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CONFTEST = TESTS_DIR / "conftest.py"
SELF = Path(__file__).name


def _modules():
    """Every test module except this guard, parsed."""
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name == SELF:
            continue
        yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _builds_testclient(tree):
    """A real `TestClient(...)` CALL — parsed, so prose about it does not count.

    The first draft of this guard matched the source text and failed on its own
    docstring. Reading the AST is the difference between "this module builds a
    client" and "this module mentions one".
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if name == "TestClient":
            return True
    return False


def _defines_client_fixture(tree):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != "client":
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            attr = getattr(target, "attr", None) or getattr(target, "id", None)
            if attr == "fixture":
                return True
    return False


def test_only_conftest_builds_a_testclient():
    offenders = [p.name for p, tree in _modules() if _builds_testclient(tree)]
    assert offenders == [], (
        "These modules build their own TestClient: "
        + ", ".join(offenders)
        + ". Use the shared session-scoped `client` fixture in conftest.py — a "
        "per-module client shuts down the app's singleton job-registry pool for "
        "every module that runs after it in the same xdist worker."
    )


def test_only_conftest_defines_a_client_fixture():
    offenders = [p.name for p, tree in _modules() if _defines_client_fixture(tree)]
    assert offenders == [], (
        "These modules define their own `client` fixture, shadowing the shared "
        "one in conftest.py: " + ", ".join(offenders)
    )


def test_the_shared_fixture_is_session_scoped():
    """Scope is the whole point — module scope here is the original bug."""
    src = CONFTEST.read_text(encoding="utf-8")
    m = re.search(r"@pytest\.fixture\(([^)]*)\)\s*def\s+client\b", src)
    assert m is not None, "conftest.py no longer defines a `client` fixture"
    assert 'scope="session"' in m.group(1), (
        "conftest.py's `client` fixture must stay session-scoped; found: "
        + m.group(1).strip()
    )
