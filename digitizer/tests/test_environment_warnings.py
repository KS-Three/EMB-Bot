"""The customer must never read the server's filesystem.

Three photo-prep seams degrade to a documented no-op when this machine cannot
run them — rembg background removal, YuNet face detection, SAM2 segmentation —
and each says so in a warning. Each also produces a `reason` for the log, and
all three used to interpolate that reason straight into the human sentence:

    f"Background removal was skipped — {bg_reason}. Tone, texture ..."

`bg_reason` is a DIAGNOSTIC. It carries an absolute path (*"isolated rembg
venv not found at /home/.../rembg_isolated/venv/bin/python"*), or a subprocess
exit code, or the last line of a worker's STDERR. And the delivery chain has
**no severity filter and no translation for any of the three codes** —
`describeWarnings` falls back to `String(w.message)` and `DigitizePanel`
renders it as `<li>{w.text}</li>`. So the sentence reached whoever digitized,
verbatim.

**Measured 2026-09-07** (`digitizer/tools/warning_coverage.py`): the
background-removal one fires on **9 of 26 corpus fixtures**, and that is not a
corpus artefact — `cfg.photo_prep_background_removal` defaults `True`, so it
is every photographic design on any machine where the optional isolated venv
was never built.

**Nothing is dropped, only moved out of the sentence.** The reason rides in
the `reason` payload field exactly as before — where it always belonged, and
where it already WAS: every one of the three passed `reason=` alongside the
message that duplicated it.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from digitizer_core.pipeline import _environment_warning

CORE = pathlib.Path(__file__).resolve().parents[1] / "digitizer_core"

# A reason with one of each thing that must not reach a customer: an absolute
# path, a subprocess exit code, and a line of somebody's STDERR.
_UGLY = ("isolated rembg venv not found at /home/user/EMB-Bot/digitizer/"
         "rembg_isolated/venv/bin/python — worker exited 137: "
         "Traceback (most recent call last): MemoryError")


def _warning():
    return _environment_warning("PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE",
                                "Background removal",
                                "This photo took the plain classical route.",
                                _UGLY)


def test_the_diagnostic_never_reaches_the_customer_sentence():
    msg = _warning()["message"]
    assert "/home/" not in msg and "venv" not in msg, msg
    assert "Traceback" not in msg and "137" not in msg, msg
    # The sentence still has to SAY something. An empty or bare-code message
    # would pass every assertion above and be worse than the leak.
    assert msg.startswith("Background removal could not run here."), msg
    assert "plain classical route" in msg, msg


def test_the_reason_payload_still_carries_the_diagnostic():
    """The whole fix is a MOVE. If this fails the fix became a deletion."""
    assert _warning()["reason"] == _UGLY


def test_no_warning_message_interpolates_a_diagnostic_reason():
    """The tripwire, over the whole package rather than the three known sites.

    Ast-walks every `warn(code, message, ...)` call and rejects a message
    f-string that interpolates a name called `reason` or ending `_reason`.
    Other interpolations are fine and everywhere — counts, millimetres, thread
    numbers. It is specifically the diagnostic-shaped one that must not be in
    a sentence a customer reads.

    **Proved able to fail:** run against `pipeline.py` as it stood before this
    change and it reports exactly three sites — lines 391 (`bg_reason`), 430
    (`reason`) and 494 (`sam2_reason`). A "no hits" assertion over a walker
    that finds nothing would pass just as quietly.
    """
    found = []
    for f in sorted(CORE.rglob("*.py")):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "warn" and len(node.args) >= 2):
                continue
            msg = node.args[1]
            if not isinstance(msg, ast.JoinedStr):
                continue
            names = {n.id for part in msg.values
                     if isinstance(part, ast.FormattedValue)
                     for n in ast.walk(part.value) if isinstance(n, ast.Name)}
            bad = sorted(n for n in names
                         if n == "reason" or n.endswith("_reason"))
            if bad:
                found.append(f"{f.name}:{node.lineno} interpolates {bad}")
    assert not found, (
        "a diagnostic reason is being interpolated into a customer-facing "
        "warning message — pass it as `reason=` and route the sentence "
        "through pipeline._environment_warning:\n  " + "\n  ".join(found))


def test_the_walker_is_not_vacuous():
    """The assertion above is a "no hits" check, so pin that it CAN hit."""
    seen = sum(1 for f in CORE.rglob("*.py")
               for node in ast.walk(ast.parse(f.read_text(encoding="utf-8")))
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == "warn" and len(node.args) >= 2)
    assert seen >= 30, f"only {seen} warn() calls parsed — did the walk break?"


def test_the_reason_itself_still_names_the_missing_path(monkeypatch):
    """The diagnostic must not be softened along with the sentence.

    Whoever installed this needs the exact path; they read it from the
    payload or the log, not from the customer's panel. Monkeypatched rather
    than relying on the venv's absence, which differs per machine — a test
    that only fires where rembg is missing is a test that skips on the
    machines that ship it.
    """
    from digitizer_core import stage1_photo_prep as prep

    missing = pathlib.Path("/nowhere/rembg_isolated/venv/bin/python")
    monkeypatch.setattr(prep, "REMBG_VENV_PYTHON", missing)
    reason = prep.background_removal_unavailable_reason()
    assert reason and str(missing) in reason, reason
    assert "README.md" in reason, "the operator still needs the way out"


@pytest.mark.parametrize("what,consequence", [
    ("Face detection", "Faces in this photo get no protective treatment."),
    ("SAM2 segmentation", "This photo used the classical region former."),
])
def test_the_shape_holds_for_the_other_two_seams(what, consequence):
    w = _environment_warning("CODE", what, consequence, _UGLY)
    assert w["message"] == f"{what} could not run here. {consequence}"
    assert w["reason"] == _UGLY
