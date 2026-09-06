"""Every field a finding EMITS is named in its `extra:` header comment.

`preflight.py` documents each code's payload in a comment beside the constant.
Nothing checked it, so the comment drifted the moment anyone added a field —
and it did, twice, one of them within hours of the field landing:

  THREAD_MATCH_POOR   never picked up `worst_shape_area_mm2` /
                      `worst_shape_area_frac` (added the same day)
  COLOR_STOPS_HEAVY   still read `{color_changes, max_stops}` after four
                      fields were added
  LETTERING_TOO_SMALL omitted `satin_total`, the denominator its own message
                      depends on ("38 of 46" reads very differently from 38)

That comment is the only place a reader learns what a review screen can sort
on, so a stale one sends them to read the whole function.

**Substring, not brace-parsing.** The comments legitimately use nested
notation (`shapes: [{shape_id, column_mm, extent_mm}]`) and trailing prose
(`(+ technique, band_mm on a tonal fill)`), and a parser that splits on commas
reports both as defects — measured, it produced two false positives out of
four hits. Asking only "does this field name appear in the comment at all"
catches the real failure (a field mentioned NOWHERE) without inventing the
other two.
"""

import ast
import pathlib
import re

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "digitizer_core" / "preflight.py"
TEXT = SRC.read_text(encoding="utf-8")

# CODE constant -> the text of its `# extra:` comment
_DOC = {m.group(1): m.group(2) for m in
        re.finditer(r'^([A-Z_]+) = "[A-Z_]+"\s*#\s*extra:\s*(.+)$', TEXT, re.M)}


def _emitted() -> dict[str, set[str]]:
    """CODE constant -> every kwarg any `finding(CODE, ...)` call passes."""
    out: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(TEXT)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "finding" and node.args
                and isinstance(node.args[0], ast.Name)):
            out.setdefault(node.args[0].id, set()).update(
                k.arg for k in node.keywords if k.arg)
    return out


EMITTED = _emitted()


def test_the_scan_finds_something_to_check():
    """A guard on the guard: if `finding(...)` is ever called differently this
    file would silently check nothing and pass."""
    assert len(_DOC) >= 10, sorted(_DOC)
    assert len(EMITTED) >= 10, sorted(EMITTED)
    assert set(EMITTED) & set(_DOC), "no documented code is emitted anywhere"


@pytest.mark.parametrize("code", sorted(set(EMITTED) & set(_DOC)))
def test_every_emitted_field_is_named_in_the_extra_comment(code):
    comment = _DOC[code]
    undocumented = sorted(f for f in EMITTED[code]
                          if not re.search(rf"\b{re.escape(f)}\b", comment))
    assert not undocumented, (
        f"{code} emits {undocumented} but its `extra:` comment does not name "
        f"them — add them to the comment beside the constant.\n  {comment}")
