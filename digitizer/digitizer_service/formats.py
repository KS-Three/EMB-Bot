"""The universal export adapter's format table.

pyembroidery writes nineteen formats; these are the ones a customer's machine
actually reads, plus SVG for a vector proof. Exposing the rest would be a menu
of ways to hand someone a file their machine rejects.

**Convention note, and it matters.** Everything here is written by pyembroidery,
which uses the published Tajima bit-weight table (y in the low nibble). EMB-Bot's
own `src/dst.js` uses the transposed table, so for **DST specifically** the two
implementations disagree and produce geometry a quarter turn apart. The
disagreement is unresolved by design — it needs a sew-out on the shop's Tajima
to settle. Until it is, the browser's DST stays the default for lettering/
manual designs, the one combination with actual sewn evidence behind it.
Studio also now sends purely-digitized designs (auto-digitize output) through
THIS service's pyembroidery-convention path instead — the browser encoder
never had sew evidence for that combination to begin with, so there is no
existing trust to protect by keeping it there. Every response says which
convention wrote the file so nobody has to guess.

PES and JEF, the two formats this service exists to unlock, have no competing
implementation and therefore no conflict.
"""
from __future__ import annotations

import io

import pyembroidery

TAJIMA_STANDARD = "tajima-standard"

# extension -> (label, mime, convention, note)
FORMATS: dict[str, dict] = {
    "dst": {
        "label": "Tajima DST",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "Studio's own encoder is the default for DST on lettering/manual designs; purely-digitized designs use this service instead — see the module docstring.",
    },
    "pes": {
        "label": "Brother PES",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "jef": {
        "label": "Janome JEF",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "exp": {
        "label": "Melco EXP",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "pec": {
        "label": "Brother PEC",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "vp3": {
        "label": "Husqvarna Viking / Pfaff VP3",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "xxx": {
        "label": "Singer XXX",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "u01": {
        "label": "Barudan U01",
        "mime": "application/octet-stream",
        "convention": TAJIMA_STANDARD,
        "note": "",
    },
    "svg": {
        "label": "SVG (vector proof)",
        "mime": "image/svg+xml",
        "convention": TAJIMA_STANDARD,
        "note": "Not a machine file — a proof for review or printing.",
    },
}

_WRITERS = {
    "dst": pyembroidery.write_dst,
    "pes": pyembroidery.write_pes,
    "jef": pyembroidery.write_jef,
    "exp": pyembroidery.write_exp,
    "pec": pyembroidery.write_pec,
    "vp3": pyembroidery.write_vp3,
    "xxx": pyembroidery.write_xxx,
    "u01": pyembroidery.write_u01,
    "svg": pyembroidery.write_svg,
}


def supported() -> list[dict]:
    return [{"format": k, **v} for k, v in FORMATS.items()]


def write(pattern: pyembroidery.EmbPattern, fmt: str) -> bytes:
    fmt = fmt.lower().lstrip(".")
    writer = _WRITERS.get(fmt)
    if writer is None:
        raise KeyError(fmt)
    buf = io.BytesIO()
    writer(pattern, buf)
    return buf.getvalue()
