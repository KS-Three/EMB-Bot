"""Decode stitch files with pyembroidery and dump them as JSON.

Companion to tools/crossval-stitch-formats.mjs (the cross-validation harness
for the browser PES/EXP/DST encoders). This script is deliberately dumb: it
opens each file named on the command line with pyembroidery — an independent,
standard-conformant reader — and prints exactly what a third-party tool would
see, as JSON on stdout. All comparison logic lives on the Node side.

Usage:
    python tools/crossval_decode.py FILE [FILE ...]

Output (one JSON object on stdout):
    { "<basename>": {
        "stitches": [[x, y, "STITCH"|"JUMP"|"TRIM"|...], ...],
        "counts":   {"STITCH": n, "JUMP": n, ...},
        "bounds":   [minx, miny, maxx, maxy],   # pyembroidery convention, +Y down
        "threads":  ["#rrggbb", ...],
      }, ... }

Requires: pyembroidery (the digitizer venv has it).
"""

import json
import os
import sys

import pyembroidery
from pyembroidery.EmbConstant import (
    COLOR_CHANGE,
    COMMAND_MASK,
    END,
    JUMP,
    SEQUIN_EJECT,
    SEQUIN_MODE,
    STITCH,
    STOP,
    TRIM,
)

_NAMES = {
    STITCH: "STITCH",
    JUMP: "JUMP",
    TRIM: "TRIM",
    STOP: "STOP",
    END: "END",
    COLOR_CHANGE: "COLOR_CHANGE",
    SEQUIN_MODE: "SEQUIN_MODE",
    SEQUIN_EJECT: "SEQUIN_EJECT",
}


def _cmd_name(command):
    return _NAMES.get(command & COMMAND_MASK, "CMD_%d" % (command & COMMAND_MASK))


def decode(path):
    pattern = pyembroidery.read(path)
    if pattern is None:
        return {"error": "pyembroidery.read returned None (unreadable file)"}
    stitches = [[int(s[0]), int(s[1]), _cmd_name(s[2])] for s in pattern.stitches]
    counts = {}
    for _, _, name in stitches:
        counts[name] = counts.get(name, 0) + 1
    try:
        bounds = list(pattern.bounds())
    except Exception:  # empty pattern
        bounds = None
    threads = [
        "#%02x%02x%02x" % (t.get_red(), t.get_green(), t.get_blue())
        for t in pattern.threadlist
    ]
    return {
        "stitches": stitches,
        "counts": counts,
        "bounds": bounds,
        "threads": threads,
    }


def main(argv):
    out = {}
    for path in argv[1:]:
        out[os.path.basename(path)] = decode(path)
    json.dump(out, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
