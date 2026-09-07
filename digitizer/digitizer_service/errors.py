"""Turn an engine exception into something a customer can act on.

The upload gate already does this well — *"That file isn't an image the engine
can read. PNG, JPEG, WebP and TIFF all work; PDF and SVG don't."*, *"Artwork is
19 MB; the limit is 12 MB. Export it smaller and try again."* Both name the
problem and the next move.

**The failure path did not.** `jobs.py` set `job.error` to
`f"{type(exc).__name__}: {exc}"`, and `digitizer.js` throws that string
straight at the user. Driven 2026-09-07 with a 1x1 PNG, the panel said:

    ValueError: no foreground pixels — the whole image reads as background

A class name, and "foreground pixels", to somebody who uploaded a logo — three
lines after two sentences written for exactly that person. The condition is
real and common: **any artwork whose subject the background detector eats**
reaches `stage1_prep`'s raise, not just a pathological one-pixel file.

## Why this is an allowlist and not a blanket rewrite

The first cut replaced EVERY unmatched exception with one generic sentence.
Three service tests said no, and they were right:

  - `boundary_override` with a hole poking outside fails with a message
    naming `boundary_override` and the hole;
  - a `merge_shape_ids` of two regions 13.8 mm apart fails with *"does not
    touch or overlap"*.

Those are not the engine leaking — they are **the caller being told exactly
which of its own edits was wrong**, which is the only thing that lets the
Studio (or the person who made the edit) undo it. A generic there destroys
information and breaks a documented posture the service calls "a clean JOB
error".

So: **an unmatched exception passes through UNCHANGED.** The known
artwork-caused failures get a sentence; everything else keeps the behaviour it
has always had. That leaves `KeyError: thread_index` reachable in principle,
which is the status quo and not a regression — and buying its way out costs
three real contracts, which is not a trade worth making at 5am or at all.

**Nothing is lost either way.** `job.detail` already carried the traceback and
now carries the raw `Type: message` too, so a developer reading a failed job
sees strictly more than before.
"""
from __future__ import annotations

# (substring of the exception text, customer sentence). Matched in order on a
# lowercased haystack, so the most specific pattern goes first. ONLY failures
# caused by the ARTWORK belong here — see the module docstring on why a
# caller's own bad edit must keep its own message.
_KNOWN: tuple[tuple[str, str], ...] = (
    ("no foreground pixels",
     "The whole image read as background, so there was nothing to stitch. "
     "This usually means the art blends into its backdrop — try a version "
     "with the subject on a clearly different colour, or crop tighter."),
    ("could not decode image",
     "That file isn't an image the engine can read. PNG, JPEG, WebP and TIFF "
     "all work; PDF and SVG don't."),
)


def raw(exc: BaseException) -> str:
    """What `job.error` has always been — kept for `job.detail` and the log."""
    return f"{type(exc).__name__}: {exc}"


def customer_message(exc: BaseException) -> str:
    """A sentence for the panel where one exists; otherwise the raw form.

    Falling back to `raw` rather than to a generic is deliberate and is the
    whole subtlety here — see the module docstring.
    """
    text = str(exc).lower()
    for needle, sentence in _KNOWN:
        if needle in text:
            return sentence
    return raw(exc)
