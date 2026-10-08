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
import math
import threading

import pystitch
from pystitch import PecWriter

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


# Per-format writer settings, where pystitch's default disagrees with the design.
#
# JEF: `JefWriter` defaults `trims=False` and writes NO cut command, so a cut
# lived in the file only if a machine inferred one from a long move (22 of
# Golke's 32 read back, tools/export-audit.mjs 2026-10-08). Kent's ruling the
# same day: write them — three zero-length moves per cut (`trim_at` 3, the
# writer's own default), the convention pystitch's reader cites for a Janome
# MC400E. What a given Janome does with them is gate 1.
_WRITER_SETTINGS = {
    "jef": {"trims": True, "trim_at": 3},
}


def _pec_encode_like_browser(pattern: pystitch.EmbPattern, f) -> None:
    """PEC's stitch stream, one record per command, as `src/pes.js` writes it.

    pystitch's own `PecWriter.pec_encode` writes every jump after the first
    as a TRIM-jump (flag 0x20), ignores the TRIM command itself, and puts the
    needle down at a jump's landing whenever the next stitch is off it on
    both axes. So a design's floats left the service as cuts — 61 against
    Golke's 32 — with an extra penetration at each (tools/export-audit.mjs,
    2026-10-08). Kent's ruling the same day: the service PES matches the
    browser's, where a jump is a jump (0x10) and a cut is a cut (0x20).

    Runs on the pattern pystitch's encoder has already normalised, so long
    moves arrive split within PEC's reach and a cut arrives as a TRIM at the
    needle — written here as a zero-length 0x20 record, as `pes.js` writes a
    `trim`. Colour changes are pystitch's byte for byte.
    """
    xx = yy = 0
    color_two = True
    for x, y, cmd in pattern.stitches:
        data = cmd & pystitch.COMMAND_MASK
        dx = int(round(x - xx))
        dy = int(round(y - yy))
        xx += dx
        yy += dy
        if data == pystitch.STITCH:
            PecWriter.write_stitch(f, dx, dy)
        elif data == pystitch.JUMP:
            PecWriter.write_jump(f, dx, dy)
        elif data == pystitch.TRIM:
            PecWriter.write_trimjump(f, dx, dy)
        elif data == pystitch.COLOR_CHANGE:
            f.write(b"\xfe\xb0")
            f.write(b"\x02" if color_two else b"\x01")
            color_two = not color_two
        elif data == pystitch.END:
            f.write(b"\xff")
            break


# `PecWriter.write_pec_block` calls its module-level `pec_encode` by name, and
# both PES and PEC go through it. Swapped only for the duration of one of
# OUR writes, under a lock — the service writes from a thread pool, and
# anything else in the process that writes PEC keeps pystitch's own.
_PEC_LOCK = threading.Lock()
_PEC_FORMATS = {"pes", "pec"}


def supported() -> list[dict]:
    return [{"format": k, **v} for k, v in FORMATS.items()]


# The repo's sewability bar: one DST record (`src/dst.js` MAX_DELTA). Kent's
# 2026-09-12 ruling made it the bar for every format, PES included.
SEWN_BAR = 121


def _split_steps(dx: int, dy: int, limit: int) -> list[tuple[int, int]]:
    """`splitSteps` from src/dst.js, line for line: n steps along the straight
    line, rounding the RUNNING total so the sum is exact and every landing
    point sits within half a unit of the line; one more step if two adjacent
    roundings land a step at limit+1."""
    n = max(1, -(-abs(dx) // limit), -(-abs(dy) // limit))
    while True:
        steps, ax, ay = [], 0, 0
        for i in range(1, n + 1):
            # JS Math.round: half rounds UP, not to even.
            sx = int(math.floor(dx * i / n + 0.5)) - ax
            sy = int(math.floor(dy * i / n + 0.5)) - ay
            if abs(sx) > limit or abs(sy) > limit:
                break
            steps.append((sx, sy))
            ax += sx
            ay += sy
        else:
            return steps
        n += 1


def split_sewn_moves(pattern: pystitch.EmbPattern, bar: int = SEWN_BAR) -> pystitch.EmbPattern:
    """Split every over-length SEWN move into stitches, the browser's rule.

    A STITCH that directly follows a STITCH and lies more than `bar` units
    away on either axis is preceded by intermediate STITCH records along the
    line. Anything else — the first stitch of the file, or one after a jump,
    a cut or a colour change — is travel-in and is left for pystitch's own
    jump-then-needle. This is `encodeDST`'s chain rule (src/dst.js).

    Left to pystitch, an over-length sewn move became JUMPS in DST, EXP, JEF,
    XXX and U01 (thread the design sews, sent as travel) and one long stitch
    in PES and PEC (a move no machine sews) — found by
    tools/export-audit.mjs, 2026-10-08. A pattern with nothing over the bar
    is returned as it came, so its bytes do not change.
    """
    out, prev, changed = [], None, False
    for x, y, cmd in pattern.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH and prev is not None:
            dx, dy = int(round(x - prev[0])), int(round(y - prev[1]))
            if abs(dx) > bar or abs(dy) > bar:
                px, py = prev
                for sx, sy in _split_steps(dx, dy, bar)[:-1]:
                    px, py = px + sx, py + sy
                    out.append([px, py, cmd])
                changed = True
        out.append([x, y, cmd])
        prev = (x, y) if c == pystitch.STITCH else None
    if not changed:
        return pattern
    split = pystitch.EmbPattern()
    split.threadlist = list(pattern.threadlist)
    split.extras = dict(pattern.extras)
    split.stitches = out
    return split


def write(pattern: pystitch.EmbPattern, fmt: str) -> bytes:
    fmt = fmt.lower().lstrip(".")
    writer = _WRITERS.get(fmt)
    if writer is None:
        raise KeyError(fmt)
    buf = io.BytesIO()
    # SVG is a proof, not a machine file: it draws the design's own segments.
    pattern = pattern if fmt == "svg" else split_sewn_moves(pattern)
    settings = _WRITER_SETTINGS.get(fmt)
    args = (pattern, buf) if settings is None else (pattern, buf, dict(settings))
    if fmt in _PEC_FORMATS:
        with _PEC_LOCK:
            original = PecWriter.pec_encode
            PecWriter.pec_encode = _pec_encode_like_browser
            try:
                writer(*args)
            finally:
                PecWriter.pec_encode = original
    else:
        writer(*args)
    return buf.getvalue()
