"""Print a failed md5 / sha256 comparison with both values whole.

pytest cuts each side of a failed ``assert a == b`` to ~30 characters in the
headline and the ``FAILED`` summary line::

    FAILED tests/t.py::test_pin - assert 'bc28d37bc555...9cca8aed4db69' == '4793dc521a2e...b8a80a7e5cb2f'

so a pin captured on another machine cannot be re-pinned from the log line
(the ``- / +`` diff block under it does carry them, but only for a plain
str == str). This hook answers a ``==`` between two hex digests -- 32 characters
(md5) or 64 (sha256) -- with the headline written out in full, and that is the
line the summary shows. Anything else falls through to pytest's own output.

A tuple, list or dict is cut the same way, and worse (the digest is one element
among counts)::

    FAILED tests/test_pushcomp.py::test_flag_off[...] - assert ('d26d5feef28..., 5380, 16733) == ('e9daab81cc9..., 4726, 14765)

A ``==`` between two of the same container type that holds at least one digest
(or the first 20+ hex characters of one -- test_pushcomp pins ``sha256[:20]``) is
answered with the headline's digests whole, then every CHANGED element on its own
line with its path, then both sides whole when they are short enough to be a
literal. ``tools/ci_repin.py`` reads those lines::

    ('d26d5feef28c2116e23e', 5380, 16733) == ('e9daab81cc92f282e9eb', 4726, 14765)
    hash mismatch inside a tuple, every changed element in full:
      [0] left : 'd26d5feef28c2116e23e'
      [0] right: 'e9daab81cc92f282e9eb'
      [1] left : 5380
      ...
      whole left : ('d26d5feef28c2116e23e', 5380, 16733)
      whole right: ('e9daab81cc92f282e9eb', 4726, 14765)

A container with no digest in it (a stitch-count tuple, a list of shape ids) is
left to pytest.

Registered by ``[tool.pytest.ini_options] addopts = "-p tests._hexrepr"`` in
pyproject.toml, not by conftest.py: several open PRs edit that file.
"""
from __future__ import annotations

import ast
import re

import pytest

_DIGEST = re.compile(r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{64})")
# A digest or a cut of one. Inside a container only: there a 20+ hex string is a pin,
# where a bare 16-hex string compared on its own is just a string.
_DIGEST_LIKE = re.compile(r"[0-9a-fA-F]{20,64}")
_CONTAINERS = (tuple, list, dict)

_HEADLINE_ITEMS = 12        # elements shown per container in the headline
_HEADLINE_LEAF = 40         # characters of a non-digest element in the headline
_LEAF_CAP = 200             # characters of a changed element's own line
_MAX_CHANGED = 40           # changed elements listed; the rest are counted
_WHOLE_CAP = 800            # a side longer than this is not written out whole


class _Missing:
    """One side has no element where the other has one (a length or key difference)."""

    def __repr__(self):
        return "<missing>"


MISSING = _Missing()


def is_digest(value) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def is_digest_like(value) -> bool:
    """A digest, or the first 20+ hex characters of one (inside a container)."""
    return isinstance(value, str) and _DIGEST_LIKE.fullmatch(value) is not None


def has_digest(value) -> bool:
    if type(value) is dict:
        return any(has_digest(v) for v in value.values())
    if type(value) in (tuple, list):
        return any(has_digest(v) for v in value)
    return is_digest_like(value)


def changed_leaves(left, right, path=()):
    """[(path, left element, right element)] for every element two containers of one
    type differ at. A path is the indices and keys that lead there; an element one side
    lacks is MISSING there. Anything not a tuple / list / dict is a leaf."""
    if type(left) is type(right) and type(left) in (tuple, list):
        out = []
        for i in range(max(len(left), len(right))):
            a = left[i] if i < len(left) else MISSING
            b = right[i] if i < len(right) else MISSING
            out += _compare(a, b, path + (i,))
        return out
    if type(left) is type(right) is dict:
        out = []
        for k in [*left, *(k for k in right if k not in left)]:
            out += _compare(left.get(k, MISSING), right.get(k, MISSING), path + (k,))
        return out
    return [(path, left, right)] if left != right else []


def _compare(a, b, path):
    if a is MISSING or b is MISSING:
        return [(path, a, b)]
    return changed_leaves(a, b, path)


def where(path) -> str:
    """``['flat'][1]``: how a path reads in the log, and in the ledger."""
    return "".join(f"[{key!r}]" for key in path)


def _short(text: str, cap: int) -> str:
    return text if len(text) <= cap else text[:cap - 3] + "..."


def _show(value) -> str:
    """The headline's rendering: every digest whole, anything else shortened."""
    if isinstance(value, str):
        return repr(value) if is_digest_like(value) else _short(repr(value), _HEADLINE_LEAF)
    kind = type(value)
    if kind in (tuple, list):
        items = [_show(v) for v in value[:_HEADLINE_ITEMS]]
        if len(value) > _HEADLINE_ITEMS:
            items.append("...")
        body = ", ".join(items) + ("," if kind is tuple and len(value) == 1 else "")
        return f"({body})" if kind is tuple else f"[{body}]"
    if kind is dict:
        items = [f"{_show(k)}: {_show(v)}" for k, v in list(value.items())[:_HEADLINE_ITEMS]]
        if len(value) > _HEADLINE_ITEMS:
            items.append("...")
        return "{" + ", ".join(items) + "}"
    return _short(repr(value), _HEADLINE_LEAF)


def _whole(value):
    """repr(value) when it is short and reads back as the same literal, else None."""
    text = repr(value)
    if len(text) > _WHOLE_CAP:
        return None
    try:
        return text if ast.literal_eval(text) == value else None
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


def nested_explanation(left, right):
    """The explanation lines for a ``==`` of two like containers holding a digest, else None.
    The first line is the headline (pytest puts ``assert `` in front of it)."""
    if type(left) is not type(right) or type(left) not in _CONTAINERS:
        return None
    if not (has_digest(left) or has_digest(right)):
        return None
    changes = changed_leaves(left, right)
    out = [f"{_show(left)} == {_show(right)}",
           f"hash mismatch inside a {type(left).__name__}, every changed element in full:"]
    for path, a, b in changes[:_MAX_CHANGED]:
        here = where(path)
        out.append(f"  {here} left : {_short(repr(a), _LEAF_CAP)}")
        out.append(f"  {here} right: {_short(repr(b), _LEAF_CAP)}")
    if len(changes) > _MAX_CHANGED:
        out.append(f"  ... {len(changes) - _MAX_CHANGED} more changed elements not shown")
    for label, value in (("left ", left), ("right", right)):
        text = _whole(value)
        if text is not None:
            out.append(f"  whole {label}: {text}")
    return out


@pytest.hookimpl(tryfirst=True)
def pytest_assertrepr_compare(config, op, left, right):
    if op != "==":
        return None
    if is_digest(left) and is_digest(right):
        return [
            # pytest puts the `assert ` in front of the first line itself
            f"{left!r} == {right!r}",
            "hash mismatch, both values in full:",
            f"  left : {left}",
            f"  right: {right}",
        ]
    try:
        return nested_explanation(left, right)
    except Exception:      # a plugin must never hide the failure it was asked to explain
        return None
