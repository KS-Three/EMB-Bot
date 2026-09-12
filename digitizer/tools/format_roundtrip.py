"""Round-trip every format the service advertises, and print the table.

**Why this exists.** `digitizer_service/formats.py` declares nine writers and
`/health` advertises all of them, but the Studio only puts buttons on four
(DST, PES, EXP, JEF). "The writer exists" is not "the writer works", and the
scope call on shipping the rest — VP3 is Husqvarna Viking / Pfaff, XXX is
Singer — needs evidence that an independent read gets back what we handed the
writer. This script produces that evidence on demand, so the answer stops
being a number in a doc that quietly goes stale.

**The path measured is the real `/export` path**, minus HTTP:

    design dict  ->  adapter.design_to_pattern  ->  formats.write(fmt)
                 ->  bytes on disk  ->  pystitch.read  ->  counts + bbox

`app.py`'s `/export` route is exactly `design_to_pattern` then
`formats.write`, so everything up to the disk write is production code rather
than a re-implementation of it. pystitch is the read side: the same library,
but a format's reader and its writer are separate code paths, and a format
whose own reader disagrees with its own writer is certainly not shippable.

**Read the verdict column like this.**
  identity    — stitch count, colour changes, thread count and bbox all match.
  off by N    — geometry differs by N units (1 unit = 0.1 mm). A format that
                stores coarser than 0.1 mm shows its quantisation here.
  lossy: ...  — something structural did not survive. Read the detail before
                concluding a button is unsafe: a format can encode the same
                intent a different way (U01 writes a colour stop as a needle
                change, not a COLOR_CHANGE record), which is a reader/format
                convention rather than lost information.

**Bounding boxes are measured over STITCH records only**, on both sides, so
the comparison is apples to apples — a format whose writer emits an extra
travel jump would otherwise look like it moved the design. `--bounds-all`
switches both sides to pystitch's own `bounds()` over every record.

Usage (from the repo root, Linux venv layout):
    digitizer/.venv/bin/python digitizer/tools/format_roundtrip.py
    ... --json                 machine-readable, for a diff or a test
    ... --colors 3             more colour blocks, to lean on colour handling
    ... --shape zigzag         large per-stitch deltas instead of two rows
    ... --bounds-all           bbox over every record, not just STITCH
    ... --detail               per-format record census and thread colours
    ... --keep DIR             leave the written files behind to inspect

The default probe is deliberately the 2026-09-08 one — 70 stitches, one
colour change, 1725 x 200 units — so a re-run is comparable with what
`docs/scope/4-export-formats.md` records, not merely self-consistent.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIGITIZER = os.path.dirname(_HERE)
if _DIGITIZER not in sys.path:
    sys.path.insert(0, _DIGITIZER)

import pystitch  # noqa: E402
from pystitch.EmbConstant import COMMAND_MASK  # noqa: E402

from digitizer_core.adapter import design_to_pattern  # noqa: E402
from digitizer_service import formats  # noqa: E402

UNITS_PER_MM = 10.0

# What the Studio puts a download button on today — `app/src/lib/exporters.js`,
# SERVICE_EXPORT_FORMATS {dst, exp, pes} + SERVICE_ONLY_FORMATS {jef}.
SHIPPING = {"dst", "pes", "exp", "jef"}

# Advertised by /health, but not a machine file and pystitch has no SVG
# reader, so there is no round trip to measure. Skipped on purpose.
NO_READER = {"svg"}

# Formats that carry no thread palette at all — the file has nowhere to put
# one, so reading back zero threads is the format working as specified, not a
# writer defect. DST and EXP are both in this set and both already ship, which
# is the proof that a missing palette is not by itself a reason to withhold a
# button: the machine operator loads the cones by the worksheet.
NO_PALETTE = {"dst", "exp", "u01"}

_CMD_NAMES = {
    0: "STITCH", 1: "JUMP", 2: "TRIM", 3: "STOP", 4: "END",
    5: "COLOR_CHANGE", 6: "SEQUIN_MODE", 7: "SEQUIN_EJECT",
    9: "NEEDLE_SET", 11: "SLOW", 12: "FAST",
}


# --------------------------------------------------------------------------
# the probe design
# --------------------------------------------------------------------------

PALETTE = [
    {"r": 220, "g": 30, "b": 40, "name": "red"},
    {"r": 20, "g": 60, "b": 200, "name": "blue"},
    {"r": 240, "g": 190, "b": 20, "name": "gold"},
    {"r": 30, "g": 150, "b": 70, "name": "green"},
]


def build_design(n_stitches: int = 70, pitch: int = 25, amplitude: int = 200,
                 colors: int = 2, shape: str = "rows") -> dict:
    """A wide, deliberately LANDSCAPE probe in `colors` blocks.

    Landscape matters. A transposed axis is invisible on square art, which is
    how EMB-Bot's own DST codec hid a swapped nibble for months (CLAUDE.md
    footgun #1). 70 stitches at a 25-unit pitch span 1725 units; the design
    is `amplitude` units tall.

    shape="rows"    each colour block is a horizontal run, offset in y. Small
                    per-record deltas, so no format has to split a stitch into
                    several records — which is what makes the byte counts
                    comparable between formats.
    shape="zigzag"  y alternates every stitch, so every record is a 200-unit
                    move. Formats with a small max delta (EXP: 127) must split
                    each one, roughly tripling the file. Useful as a second
                    opinion, not as the headline number.
    """
    colors = max(1, min(colors, len(PALETTE)))
    block = max(1, n_stitches // colors)

    stitches: list[dict] = []
    last: tuple[int, int] | None = None
    for i in range(n_stitches):
        bi = min(i // block, colors - 1)
        if i and colors > 1 and i % block == 0 and i // block < colors:
            # A colour change is a trim then a colour record at the standing
            # position — the shape `plan_to_design` emits for a real design.
            stitches.append({"x": last[0], "y": last[1], "type": "trim"})
            stitches.append({"x": last[0], "y": last[1], "type": "color"})
        x = i * pitch
        y = (amplitude if i % 2 else 0) if shape == "zigzag" \
            else (amplitude * bi // max(1, colors - 1) if colors > 1 else 0)
        stitches.append({"x": x, "y": y, "type": "stitch"})
        last = (x, y)
    stitches.append({"x": 0, "y": 0, "type": "end"})

    return {
        "name": "roundtrip probe",
        "stitches": stitches,
        "colors": [dict(c) for c in PALETTE[:colors]],
        "stitchCount": n_stitches,
        "colorCount": colors,
    }


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------

def measure(pattern: pystitch.EmbPattern, bounds_all: bool = False) -> dict:
    counts: dict[str, int] = {}
    sewn: list[tuple[int, int]] = []
    for x, y, cmd in pattern.stitches:
        c = cmd & COMMAND_MASK
        name = _CMD_NAMES.get(c, "CMD_%d" % c)
        counts[name] = counts.get(name, 0) + 1
        if c == pystitch.STITCH:
            sewn.append((int(x), int(y)))

    if bounds_all:
        try:
            x0, y0, x1, y1 = pattern.bounds()
            w, h = int(x1 - x0), int(y1 - y0)
        except Exception:
            w = h = 0
    elif sewn:
        xs = [p[0] for p in sewn]
        ys = [p[1] for p in sewn]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
    else:
        w = h = 0

    return {
        "stitches": counts.get("STITCH", 0),
        "color_changes": counts.get("COLOR_CHANGE", 0),
        "needle_sets": counts.get("NEEDLE_SET", 0),
        "stops": counts.get("STOP", 0),
        "jumps": counts.get("JUMP", 0),
        "trims": counts.get("TRIM", 0),
        "threads": len(pattern.threadlist),
        "thread_rgb": ["#%02x%02x%02x" % (t.get_red(), t.get_green(), t.get_blue())
                       for t in pattern.threadlist],
        "width_u": w,
        "height_u": h,
        "width_mm": round(w / UNITS_PER_MM, 2),
        "height_mm": round(h / UNITS_PER_MM, 2),
        "counts": counts,
    }


def verdict(src: dict, out: dict, fmt: str = "") -> str:
    if out.get("error"):
        return "UNREADABLE: " + out["error"]

    lost = []
    notes = []
    if out["stitches"] != src["stitches"]:
        lost.append(f"stitches {src['stitches']}->{out['stitches']}")
    if out["color_changes"] != src["color_changes"]:
        # A colour stop re-encoded as a needle change is not the same thing as
        # a colour stop thrown away. Say which one happened.
        if out["needle_sets"] >= src["color_changes"] + 1:
            notes.append(f"{src['color_changes']} COLOR_CHANGE -> "
                         f"{out['needle_sets']} NEEDLE_SET (stop kept, "
                         f"re-encoded)")
        else:
            lost.append(
                f"colour changes {src['color_changes']}->{out['color_changes']}")
    if out["threads"] != src["threads"]:
        if fmt in NO_PALETTE and out["threads"] == 0:
            notes.append("no palette in format")
        else:
            lost.append(f"threads {src['threads']}->{out['threads']}")
    elif out["thread_rgb"] != src["thread_rgb"]:
        notes.append("threads snapped to chart")

    dw = out["width_u"] - src["width_u"]
    dh = out["height_u"] - src["height_u"]
    geom = ""
    if dw or dh:
        parts = []
        if dw:
            parts.append(f"w {dw:+d}u")
        if dh:
            parts.append(f"h {dh:+d}u")
        n = max(abs(dw), abs(dh))
        geom = f"off by {n}u ({n / UNITS_PER_MM:.1f} mm): " + ", ".join(parts)

    parts = []
    if lost:
        parts.append("lossy: " + ", ".join(lost))
    if geom:
        parts.append(geom)
    if not parts:
        parts.append("identity")
    if notes:
        parts.append("[" + "; ".join(notes) + "]")
    return " ".join(parts)


def roundtrip(design: dict, fmt: str, keep_dir: str | None = None,
              bounds_all: bool = False) -> dict:
    pattern = design_to_pattern(design, label="RTPROBE")
    src = measure(pattern, bounds_all)

    row: dict = {"format": fmt, "label": formats.FORMATS[fmt]["label"],
                 "shipping": fmt in SHIPPING, "src": src}
    try:
        data = formats.write(pattern, fmt)
    except Exception as exc:            # a writer that raises is its own answer
        row["bytes"] = 0
        row["out"] = {"error": f"write failed: {type(exc).__name__}: {exc}"}
        row["verdict"] = row["out"]["error"]
        return row
    row["bytes"] = len(data)

    target = keep_dir or tempfile.mkdtemp(prefix="fmt-roundtrip-")
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, f"probe.{fmt}")
    with open(path, "wb") as fh:
        fh.write(data)
    row["path"] = path

    try:
        back = pystitch.read(path)
    except Exception as exc:
        row["out"] = {"error": f"read raised {type(exc).__name__}: {exc}"}
    else:
        row["out"] = ({"error": "pystitch.read returned None"} if back is None
                      else measure(back, bounds_all))
    row["verdict"] = verdict(src, row["out"], fmt)
    return row


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

def render_table(rows: list[dict]) -> str:
    head = ("  ", "format", "label", "bytes", "stitches", "colour chg",
            "threads", "bbox units", "bbox mm", "verdict")
    body = []
    for r in rows:
        s, o = r["src"], r["out"]
        tag = "ship" if r["shipping"] else ""
        if o.get("error"):
            body.append((tag, r["format"], r["label"], str(r["bytes"]),
                         f"{s['stitches']} -> ?", f"{s['color_changes']} -> ?",
                         f"{s['threads']} -> ?", "?", "?", r["verdict"]))
            continue
        body.append((
            tag, r["format"], r["label"], str(r["bytes"]),
            f"{s['stitches']} -> {o['stitches']}",
            f"{s['color_changes']} -> {o['color_changes']}",
            f"{s['threads']} -> {o['threads']}",
            f"{s['width_u']}x{s['height_u']} -> {o['width_u']}x{o['height_u']}",
            f"{s['width_mm']}x{s['height_mm']} -> {o['width_mm']}x{o['height_mm']}",
            r["verdict"],
        ))

    cols = list(zip(*([head] + body)))
    widths = [max(len(c) for c in col) for col in cols]
    out = []
    for i, vals in enumerate([head] + body):
        out.append("  ".join(v.ljust(w) for v, w in zip(vals, widths)).rstrip())
        if i == 0:
            out.append("  ".join("-" * w for w in widths))
    return "\n".join(out)


def colour_sweep(shape: str = "rows", n_stitches: int = 70,
                 bounds_all: bool = False) -> tuple[list[str], str]:
    """Same probe at 1..4 colour blocks — the axis a single run hides.

    This exists because VP3 is EXACT on a two-colour design and drops one
    unit on a three-colour one. A harness whose default probe hides that is
    worse than no harness, so the sweep runs every time.

    Reports the largest per-stitch deviation between the pattern handed to
    the writer and the pattern read back, which catches a drift that a
    bounding box can hide (every stitch shifted the same way moves the box
    not at all).
    """
    order = [f for f in formats.FORMATS if f not in NO_READER]
    order.sort(key=lambda f: (f not in SHIPPING, f))
    counts = [1, 2, 3, 4]

    grid: dict[str, list[str]] = {}
    for fmt in order:
        cells = []
        for n in counts:
            design = build_design(n_stitches=n_stitches, colors=n, shape=shape)
            pattern = design_to_pattern(design, label="RTPROBE")
            src = [(int(x), int(y)) for x, y, c in pattern.stitches
                   if (c & COMMAND_MASK) == pystitch.STITCH]
            tmp = tempfile.mkdtemp(prefix="fmt-sweep-")
            path = os.path.join(tmp, f"probe.{fmt}")
            with open(path, "wb") as fh:
                fh.write(formats.write(pattern, fmt))
            back = pystitch.read(path)
            out = [(int(x), int(y)) for x, y, c in back.stitches
                   if (c & COMMAND_MASK) == pystitch.STITCH]
            if len(out) != len(src):
                cells.append(f"n={len(out)}")
                continue
            dev = max((max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                       for a, b in zip(src, out)), default=0)
            cells.append("0" if dev == 0 else f"{dev}u")
        grid[fmt] = cells

    head = ["format"] + [f"{n} colour{'s' if n > 1 else ''}" for n in counts]
    body = [[f] + grid[f] for f in order]
    cols = list(zip(*([head] + body)))
    widths = [max(len(c) for c in col) for col in cols]
    lines = []
    for i, vals in enumerate([head] + body):
        lines.append("  ".join(v.ljust(w) for v, w in zip(vals, widths)).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    return lines, "max per-stitch deviation, in 0.1 mm units (0 = exact)"


def render_detail(rows: list[dict]) -> str:
    out = []
    for r in rows:
        o = r["out"]
        if o.get("error"):
            out.append(f"{r['format']}: {o['error']}")
            continue
        census = ", ".join(f"{k}={v}" for k, v in sorted(o["counts"].items()))
        out.append(f"{r['format']:4s} records: {census}")
        out.append(f"     threads: {o['thread_rgb'] or '(none carried)'}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--detail", action="store_true",
                    help="per-format record census and thread colours")
    ap.add_argument("--colors", type=int, default=2)
    ap.add_argument("--stitches", type=int, default=70)
    ap.add_argument("--shape", choices=("rows", "zigzag"), default="rows")
    ap.add_argument("--bounds-all", action="store_true",
                    help="bbox over every record, not STITCH only")
    ap.add_argument("--keep", metavar="DIR", default=None)
    ap.add_argument("--no-sweep", action="store_true",
                    help="skip the 1..4 colour-block sweep")
    args = ap.parse_args(argv)

    design = build_design(n_stitches=args.stitches, colors=args.colors,
                          shape=args.shape)
    order = [f for f in formats.FORMATS if f not in NO_READER]
    order.sort(key=lambda f: (f not in SHIPPING, f))
    rows = [roundtrip(design, f, args.keep, args.bounds_all) for f in order]

    sweep_lines: list[str] = []
    sweep_caption = ""
    if not args.no_sweep:
        sweep_lines, sweep_caption = colour_sweep(args.shape, args.stitches,
                                                  args.bounds_all)

    if args.json:
        print(json.dumps({
            "probe": {"shape": args.shape, "stitches": design["stitchCount"],
                      "colors": design["colorCount"],
                      "bounds_all": args.bounds_all},
            "rows": rows,
            "colour_sweep": sweep_lines,
        }, indent=2))
        return 0

    s = rows[0]["src"]
    print(f"probe   : shape={args.shape}  {s['stitches']} stitches, "
          f"{s['color_changes']} colour change(s), {s['threads']} threads, "
          f"{s['width_u']} x {s['height_u']} units "
          f"({s['width_mm']} x {s['height_mm']} mm)")
    print("path    : design -> design_to_pattern -> formats.write -> "
          "pystitch.read")
    print(f"bbox    : {'all records' if args.bounds_all else 'STITCH records only'}"
          f", both sides")
    print("skipped : svg (advertised by /health, no reader to round-trip with)")
    print()
    print(render_table(rows))
    if sweep_lines:
        print()
        print(f"colour-block sweep — {sweep_caption}")
        print("\n".join(sweep_lines))
    if args.detail:
        print()
        print(render_detail(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
