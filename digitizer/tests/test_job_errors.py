"""A failed job must not throw a class name at the customer — for the failures
the ARTWORK causes. For the ones the CALLER causes, it must keep doing exactly
what it did.

`digitizer.js` does `throw new Error(job.error || "Digitizing failed.")`, so
`job.error` is customer copy whether or not anyone treated it that way. Until
2026-09-07 `jobs.py` set it to `f"{type(exc).__name__}: {exc}"`, and driven
with a 1x1 PNG that day the panel said:

    ValueError: no foreground pixels — the whole image reads as background

Three lines after the upload gate's own two sentences, which are written for
exactly that person. **Not a pathological case**: `stage1_prep` raises it for
any artwork whose subject the background detector eats.

**The first cut of the fix was too broad and three service tests caught it.**
A `boundary_override` whose hole pokes outside, and a `merge_shape_ids` of two
regions 13.8 mm apart, both fail with messages naming the caller's own bad
edit — which is the only thing that lets it be undone. Replacing those with a
generic destroys information. So the map is an ALLOWLIST of artwork failures
and everything else passes through unchanged; `tests/test_service.py` is the
other half of this file's coverage.
"""
from __future__ import annotations

import pytest

from digitizer_service.errors import customer_message, raw

# Words that mean something to whoever wrote the engine and nothing to
# whoever uploaded a logo.
ENGINE_SPEAK = ("valueerror", "runtimeerror", "traceback", "foreground pixel",
                "px_per_mm", "ndarray", "numpy", "cv2", "/home/", "nonetype")

ARTWORK_FAILURES = (
    "no foreground pixels — the whole image reads as background",
    "could not decode image",
)


def test_the_one_a_real_upload_hits_says_what_to_do():
    msg = customer_message(
        ValueError("no foreground pixels — the whole image reads as background"))
    assert "nothing to stitch" in msg
    assert "crop tighter" in msg


def test_a_bad_file_gets_the_same_answer_the_upload_gate_gives():
    """Two ways in, one sentence — a customer must not learn that a file is
    fine at upload and unreadable one screen later."""
    assert customer_message(ValueError("could not decode image")) == (
        "That file isn't an image the engine can read. PNG, JPEG, WebP and "
        "TIFF all work; PDF and SVG don't.")


@pytest.mark.parametrize("text", ARTWORK_FAILURES)
def test_no_artwork_sentence_speaks_engine(text):
    msg = customer_message(ValueError(text))
    low = msg.lower()
    for word in ENGINE_SPEAK:
        assert word not in low, f"customer copy says {word!r}: {msg}"
    assert msg[0].isupper() and msg.rstrip().endswith(".")


def test_a_callers_own_bad_edit_keeps_its_own_message():
    """The correction the service tests forced.

    These name the field the caller got wrong, which is what lets the Studio
    or the person who made the edit undo it. A generic here destroys
    information and breaks the "clean JOB error" posture the service
    documents.
    """
    for text in ("boundary_override for Sa1b2 has a hole outside its shell",
                 "merge_shape_ids: Sa and Sb does not touch or overlap"):
        out = customer_message(ValueError(text))
        assert out == raw(ValueError(text))
        # The words `tests/test_service.py` asserts on must survive verbatim.
        assert text in out


def test_an_unmatched_exception_passes_through_unchanged():
    """Status quo, deliberately — buying `KeyError` out of the panel cost
    three real contracts, which is not a trade worth making."""
    for exc in (RuntimeError("assert self._pool is not None"),
                ZeroDivisionError("division by zero"),
                KeyError("thread_index")):
        assert customer_message(exc) == raw(exc)


def test_the_diagnostic_is_not_lost_only_moved():
    """The whole change is a MOVE. `job.detail` gains the raw form beside the
    traceback, so a developer reading a failed job sees strictly MORE than
    before — the only reason replacing `job.error` is safe at all."""
    exc = ValueError("no foreground pixels — the whole image reads as background")
    assert raw(exc) == (
        "ValueError: no foreground pixels — the whole image reads as background")
    assert raw(exc) != customer_message(exc)


def test_the_matcher_is_case_insensitive_and_substring():
    """Engine messages get reworded; the map must not need updating for a
    capitalisation change or an added clause."""
    for text in ("Could Not Decode Image (after 2 attempts)",
                 "stage 1: NO FOREGROUND PIXELS left"):
        assert customer_message(ValueError(text)) != raw(ValueError(text))


def test_both_arms_are_live():
    """Every assertion above is either "is mapped" or "is not mapped", and an
    empty map or a match-everything map would satisfy exactly one of the two
    groups while quietly breaking the other. Pin that both fire."""
    mapped = {customer_message(ValueError(t)) for t in ARTWORK_FAILURES}
    assert len(mapped) == 2
    assert all(m != raw(ValueError(t))
               for m, t in zip(sorted(mapped), sorted(ARTWORK_FAILURES)))
    assert customer_message(ValueError("zzz")) == raw(ValueError("zzz"))
