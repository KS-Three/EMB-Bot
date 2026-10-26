"""Print a failed md5 / sha256 comparison with both values whole.

pytest cuts each side of a failed ``assert a == b`` to ~30 characters in the
headline and the ``FAILED`` summary line::

    FAILED tests/t.py::test_pin - assert 'bc28d37bc555...9cca8aed4db69' == '4793dc521a2e...b8a80a7e5cb2f'

so a pin captured on another machine cannot be re-pinned from the log line
(the ``- / +`` diff block under it does carry them, but only for a plain
str == str). This hook answers a ``==`` between two hex digests -- 32 characters
(md5) or 64 (sha256) -- with the headline written out in full, and that is the
line the summary shows. Anything else falls through to pytest's own output.

Registered by ``[tool.pytest.ini_options] addopts = "-p tests._hexrepr"`` in
pyproject.toml, not by conftest.py: several open PRs edit that file.
``tools/ci_repin.py`` reads what this prints.
"""
from __future__ import annotations

import re

import pytest

_DIGEST = re.compile(r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{64})")


def is_digest(value) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


@pytest.hookimpl(tryfirst=True)
def pytest_assertrepr_compare(config, op, left, right):
    if op != "==" or not (is_digest(left) and is_digest(right)):
        return None
    return [
        # pytest puts the `assert ` in front of the first line itself
        f"{left!r} == {right!r}",
        "hash mismatch, both values in full:",
        f"  left : {left}",
        f"  right: {right}",
    ]
