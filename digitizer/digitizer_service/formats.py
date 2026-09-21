"""The universal export adapter's format table.

pystitch (pyembroidery's actively maintained fork — swap vetted in
`docs/pystitch-evaluation-2026-08-11.md`) writes twenty-plus formats; these are
the ones a customer's machine actually reads, plus SVG for a vector proof.
Exposing the rest would be a menu of ways to hand someone a file their machine
rejects.

**Convention note.** Everything here is written by pystitch, which uses the
published Tajima bit-weight table — **X in the LOW nibble, Y in the HIGH**
(measured 2026-09-13 by encoding a unit move on each axis and reading the byte:
`+1 X` sets `0x01`, `+1 Y` sets `0x40`). `src/dst.js` matches it bit-for-bit
since 2026-09-08, so the two implementations AGREE and there is nothing here to
settle.

*This paragraph said the opposite until 2026-09-13, and it had been false for
five days across fifty-odd merges: that `src/dst.js` "uses the transposed
table", that the two "produce geometry a quarter turn apart", and that the
disagreement "needs a sew-out on the shop's Tajima to settle" — while also
getting the nibble backwards. A session reading it would refuse work that is
not blocked, which is exactly how the axis bug cost six weeks in the first
place. ROADMAP gate 1's own carve-out covers this: a file format is not a
physical constant.*

The browser's DST stays the default for lettering/manual designs, but that is
now a ROUTING choice — it is the one combination with actual sewn evidence
behind it — and no longer a correctness one.
Studio also now sends purely-digitized designs (auto-digitize output) through
THIS service's pystitch-convention path instead — the browser encoder
never had sew evidence for that combination to begin with, so there is no
existing trust to protect by keeping it there. Every response says which
convention wrote the file so nobody has to guess.

PES and JEF, the two formats this service exists to unlock, have no competing
implementation and therefore no conflict.
"""
from __future__ import annotations

import io

import pystitch

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
    "dst": pystitch.write_dst,
    "pes": pystitch.write_pes,
    "jef": pystitch.write_jef,
    "exp": pystitch.write_exp,
    "pec": pystitch.write_pec,
    "vp3": pystitch.write_vp3,
    "xxx": pystitch.write_xxx,
    "u01": pystitch.write_u01,
    "svg": pystitch.write_svg,
}


def supported() -> list[dict]:
    return [{"format": k, **v} for k, v in FORMATS.items()]


def write(pattern: pystitch.EmbPattern, fmt: str) -> bytes:
    fmt = fmt.lower().lstrip(".")
    writer = _WRITERS.get(fmt)
    if writer is None:
        raise KeyError(fmt)
    buf = io.BytesIO()
    writer(pattern, buf)
    return buf.getvalue()
