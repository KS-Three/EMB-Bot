"""Export read-back: re-read the bytes `formats.write` produced and refuse to
hand the file out if they disagree with the design that was written.

Kent, 2026-11-05: BLOCK the download on a mismatch. A file that fails its own
read-back is broken, not low quality, so the 2026-10-02 "no warnings reach
readouts" ruling does not apply and a plain "Export failed" is allowed.

**Independent on purpose.** The bytes are read with pystitch's reader for that
format, a code path separate from the writer (the writers are ours plus
pystitch's; the readers are pystitch's alone). The expected values come from the
in-memory pattern BEFORE `formats.write`, by arithmetic on its stitches. They do
not call `split_sewn_moves` or any writer, so a splitter, a record packer or a
header field that drifts shows up as a mismatch instead of agreeing with itself.

**The checks** (units are 0.1 mm, 121 units is 12.1 mm):

* ``stitch_count``   sewn records vs the pattern's stitches plus the
  intermediates a chained move over 121 units must split into
* ``stitch_positions``   every pattern stitch lands where the pattern put it, in
  order (counts and a box alone miss a stitch that moved inside the design)
* ``trim_count`` / ``trim_order``   trims, and the sewn count each follows
* ``color_count`` / ``color_order``   colour changes, and the sewn count before each
* ``longest_stitch``   no sewn move that continues a sewn run exceeds 121 units
* ``bounding_box``   the sewn stitches' extents equal the pattern's
* DST only: ``header_bbox``, the +X -X +Y -Y fields against the extents of the
  records in the file

**What pystitch does to a pattern, which the expectation has to know** (measured
2026-11-05 on over 15,000 random write/read cycles over the 8 formats, all at zero
disagreements; ``tests/test_export_readback.py`` keeps a seeded slice of it):

* DST has no trim opcode: a trim is a run of N jump records after a stitch, read
  with ``trim_at=N`` (N is the caller's ``trim_jumps``). A trim with no stitch
  since the last cut or colour change is not written, and neither is a colour
  change before the first stitch.
* A colour change never moves the needle: its own coordinates are nowhere in the
  file. A PES/PEC colour change between two identical cones reads as a STOP.
* JEF and VP3 report trims the design never asked for (JEF writes three cut
  moves per trim; VP3 ends every file on a trim), so ``trim_count`` there is an
  AT LEAST and says so (``mode``). U01 writes a colour stop as a needle change.
* VP3 and XXX lose something the reader cannot give back, listed per result in
  ``skipped`` (see ``_SKIPPED``) rather than dropped silently.
* SVG is a drawing, not a stitch file: ``verified: false`` with a reason.

Only ``formats.FORMATS`` machine formats are read; nothing is silently skipped.
"""
from __future__ import annotations

import io
import json
import math

import pystitch
from pystitch.EmbConstant import COMMAND_MASK

from digitizer_service import formats

MAX_SEWN_UNITS = formats.SEWN_BAR  # 121 = 12.1 mm, one DST record

_READERS = {
    "dst": pystitch.read_dst,
    "pes": pystitch.read_pes,
    "jef": pystitch.read_jef,
    "exp": pystitch.read_exp,
    "pec": pystitch.read_pec,
    "vp3": pystitch.read_vp3,
    "xxx": pystitch.read_xxx,
    "u01": pystitch.read_u01,
}

# Formats whose reader reports MORE trims than the design has, by construction.
_TRIMS_AT_LEAST = {"jef", "vp3"}
# VP3 stores positions in a coarser unit: the documented one-unit shift at the
# third and later colour blocks (app/src/lib/exporters.js, 2026-09-12 ruling).
_BOX_TOLERANCE = {"vp3": 1}
_DST_WIGGLE = 4

# Checks whose answer pystitch's reader cannot give for a format, by name, with the
# reason. Reported on every result (`skipped`), never silently dropped.
_SKIPPED = {
    "vp3": {"longest_stitch": "VP3 stores each colour block from its own start point, so the reader joins "
                              "the end of one block to the start of the next as a stitch and no sewn move can be measured."},
    "xxx": {c: "XXX stores the first stitch of a run after long travel as a move, so the stitches that "
               "follow cannot be lined up one for one." for c in ("trim_order", "color_order", "bounding_box", "stitch_positions")},
}

CHECK_LABEL = {
    "readable": "the file does not read back",
    "stitch_count": "stitch count",
    "trim_count": "trim count",
    "trim_order": "trim order",
    "color_count": "colour block count",
    "color_order": "colour block order",
    "stitch_positions": "stitch positions",
    "longest_stitch": "longest stitch",
    "bounding_box": "design size",
    "header_bbox": "size in the file header",
}

NO_READER_REASON = {
    "svg": "SVG is a picture of the design, not a stitch file; there is nothing to read back.",
}


def _records_for(dx: int, dy: int, lim: int) -> int:
    return max(1, math.ceil(abs(dx) / lim), math.ceil(abs(dy) / lim))


class _Counter:
    """What a record stream means. DST has no trim opcode, so there a trim is a
    run of `n` or more jump records that follows a stitch (pystitch's
    `interpolate_trims`: a run after a colour change, a trim or the start of the
    file is not read as a trim); everything else writes the trim itself."""

    def __init__(self, explicit_trims: bool, n: int, expecting: bool = False):
        self.expecting = expecting  # True when counting what a design asks for
        self.explicit = explicit_trims
        self.n = n
        self.armed = False  # a stitch has been sewn since the last cut or colour
        self.run = 0
        self.sewn = 0
        self.trim_at: list[int] = []
        self.color_at: list[int] = []
        self.tokens = 0

    def add(self, kind: str, count: int = 1) -> None:
        self.tokens += count
        if kind == "J":
            if not self.explicit:
                self.run += count
            return
        self._flush()
        if kind == "S":
            self.sewn += count
            self.armed = True
        elif kind == "C":
            self.color_at.append(self.sewn)
            self.armed = False
        elif kind == "T":
            # pystitch keeps one cut per stretch of thread: a trim with no stitch
            # since the last cut or colour change is not written (measured).
            if self.armed or not self.expecting:
                self.trim_at.append(self.sewn)
            self.armed = False

    def _flush(self) -> None:
        if not self.explicit and self.run >= self.n and self.armed:
            self.trim_at.append(self.sewn)
            self.armed = False
        self.run = 0

    def finish(self) -> None:
        self._flush()


def _events(pattern: pystitch.EmbPattern):
    """(kind, x, y) per stitch/jump/trim/colour record, stopping at END."""
    out = []
    for x, y, cmd in pattern.stitches:
        c = cmd & COMMAND_MASK
        if c == pystitch.END:
            break
        kind = {pystitch.STITCH: "S", pystitch.JUMP: "J", pystitch.TRIM: "T",
                pystitch.COLOR_CHANGE: "C"}.get(c)
        if kind is not None:
            out.append((kind, int(round(x)), int(round(y))))
    return out


def expected_facts(pattern: pystitch.EmbPattern, fmt: str, trim_jumps: int) -> dict:
    ev = _events(pattern)
    # A colour change or a trim before the first stitch has nothing to separate;
    # pystitch drops the colour change outright and keeps only the TRAVEL of a
    # trim (measured, all 8 formats), so the file never has either.
    first_s = next((i for i, e in enumerate(ev) if e[0] == "S"), len(ev))
    ev = [("J", e[1], e[2], True) if (i < first_s and e[0] == "T") else e + (False,)
          for i, e in enumerate(ev) if i >= first_s or e[0] != "C"]
    explicit = fmt != "dst"
    cnt = _Counter(explicit, trim_jumps, expecting=True)
    lx = ly = 0
    prev_s = False
    run_starts = 0
    landings: list[tuple[int, int]] = []
    box = None
    ext = None
    for kind, x, y, lead_trim in ev:
        if kind == "C":
            # A colour change never moves the needle in a file (pystitch writes
            # it where the needle already is), so its coordinates are nowhere.
            cnt.add("C")
            prev_s = False
            continue
        if not lead_trim:  # pystitch's header extents leave a leading trim's own spot out
            ext = [x, y, x, y] if ext is None else [min(ext[0], x), min(ext[1], y), max(ext[2], x), max(ext[3], y)]
        recs = _records_for(x - lx, y - ly, MAX_SEWN_UNITS)
        if kind == "S":
            landings.append((x, y))
            box = [x, y, x, y] if box is None else [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
            if prev_s:
                cnt.add("S", recs)
            else:
                if not explicit and recs > 1:
                    cnt.add("J", recs - 1)
                run_starts += 1
                cnt.add("S", 1)
            prev_s = True
            lx, ly = x, y
            continue
        prev_s = False
        if kind == "T":
            if explicit:
                cnt.add("T")
            else:
                cnt.add("J", max(trim_jumps, recs))
            lx, ly = x, y
        else:
            if not explicit:
                cnt.add("J", recs)
            lx, ly = x, y
    cnt.finish()
    return {
        "stitches": cnt.sewn, "trim_at": cnt.trim_at, "color_at": cnt.color_at,
        "run_starts": run_starts, "sewn_box": box, "landings": landings,
    }


def _dst_header(data: bytes) -> dict:
    out = {}
    for line in data[:512].replace(b"\x1a", b"\r").replace(b"\n", b"\r").split(b"\r"):
        t = line.strip().decode("latin-1")
        if len(t) > 3 and t[2] == ":":
            out.setdefault(t[:2], t[3:].strip())
    return out


def read_facts(data: bytes, fmt: str, trim_jumps: int) -> dict:
    reader = _READERS[fmt]
    # The reader has already turned a DST's jump runs into TRIM records
    # (trim_at=N), so its output is read like every other format's.
    if fmt == "dst":
        back = reader(io.BytesIO(data), {"trim_at": trim_jumps})
    else:
        back = reader(io.BytesIO(data))
    cnt = _Counter(True, trim_jumps)
    needle_sets = 0
    longest = 0
    prev = None
    px = py = 0
    box = None
    sewn: list[tuple[int, int]] = []
    for x, y, cmd in back.stitches:
        c = cmd & COMMAND_MASK
        if c == pystitch.END:
            break
        # STOP: PES/PEC readers turn a colour change between two identical
        # threads into a STOP (`interpolate_duplicate_color_as_stop`), and two
        # nearby colours snap to one cone often enough to matter. Still a block
        # boundary, so it counts as one.
        kind = {pystitch.STITCH: "S", pystitch.JUMP: "J", pystitch.TRIM: "T",
                pystitch.COLOR_CHANGE: "C", pystitch.STOP: "C"}.get(c)
        if c == pystitch.NEEDLE_SET:
            needle_sets += 1
            if fmt == "u01" and needle_sets > 1 and cnt.sewn:
                cnt.add("C")
            prev = None
            px, py = x, y
            continue
        if kind is None:
            prev = None
            px, py = x, y
            continue
        if kind == "C" and cnt.sewn == 0:
            continue  # a colour change before the first stitch separates nothing
        cnt.add(kind)
        xi, yi = int(round(x)), int(round(y))
        if kind == "S":
            sewn.append((xi, yi))
            box = [xi, yi, xi, yi] if box is None else [min(box[0], xi), min(box[1], yi), max(box[2], xi), max(box[3], yi)]
            if prev == "S":
                longest = max(longest, int(round(abs(x - px))), int(round(abs(y - py))))
        prev = kind
        px, py = x, y
    cnt.finish()
    facts = {"stitches": cnt.sewn, "trim_at": cnt.trim_at, "color_at": cnt.color_at,
             "longest": longest, "sewn_box": box, "sewn": sewn}
    if fmt == "dst":
        facts["header"] = _dst_header(data)
        # The header's extents against the records themselves: every record in
        # the file as written (no trims interpolated, no zero jumps clipped), END
        # included, which is what DstWriter measures with `bounds()`. A trim is
        # written as a small wiggle of jumps around its spot (+-4 units) that the
        # header's extents do not include, so a file with trims is compared to
        # within that wiggle (`_DST_WIGGLE`); one without to within a unit, the
        # rounding of a split move's float landing points.
        raw = _READERS["dst"](io.BytesIO(data), {"trim_at": 10 ** 6, "clipping": False})
        xs = [x for x, _, _ in raw.stitches]
        ys = [y for _, y, _ in raw.stitches]
        facts["header_box"] = ([abs(int(max(xs))), abs(int(min(xs))), abs(int(max(ys))), abs(int(min(ys)))]
                               if xs else None)
        facts["header_tol"] = _DST_WIGGLE if cnt.trim_at else 1
    return facts


def _first_diff(a, b) -> int:
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            return i
    return -1


def expect(pattern: pystitch.EmbPattern, fmt: str, trim_jumps: int | None = None) -> dict | None:
    """What the file for `pattern` must say, computed BEFORE `formats.write`.
    None for a format with no reader (SVG)."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in _READERS:
        return None
    n = formats.trim_jumps_of(trim_jumps) if fmt == "dst" else formats.TRIM_JUMPS_DEFAULT
    return expected_facts(pattern, fmt, n)


def verify(expected: dict | None, data: bytes, fmt: str, trim_jumps: int | None = None) -> dict:
    """Read `data` back and compare with `expected` (from `expect`, taken before
    the write). Returns the result dict; never raises on a mismatch.

    ``{"verified": True, "ok": bool, "format", "checks": [...], "failed": [...],
    "stitches", "trims", "colors", "longest_mm"}`` for the eight machine
    formats, ``{"verified": False, "ok": True, "reason"}`` for SVG.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in _READERS or expected is None:
        return {"verified": False, "ok": True, "format": fmt,
                "reason": NO_READER_REASON.get(fmt, f"no reader for {fmt}")}
    n = formats.trim_jumps_of(trim_jumps) if fmt == "dst" else formats.TRIM_JUMPS_DEFAULT
    exp = expected
    try:
        got = read_facts(data, fmt, n)
    except Exception as exc:  # a reader that chokes is itself the finding
        failed = [{"check": "readable", "expected": "a file this format's reader accepts",
                   "read": f"{type(exc).__name__}: {exc}", "ok": False}]
        return {"verified": True, "ok": False, "format": fmt, "checks": failed, "failed": failed,
                "stitches": exp["stitches"], "trims": len(exp["trim_at"]),
                "colors": len(exp["color_at"]), "longest_mm": None}
    checks: list[dict] = []
    skipped = [{"check": c, "reason": r} for c, r in _SKIPPED.get(fmt, {}).items()]
    skip = set(_SKIPPED.get(fmt, {}))

    def add(check, expected, read, ok=None, mode="exact"):
        if check in skip:
            return
        checks.append({"check": check, "expected": expected, "read": read,
                       "ok": (expected == read) if ok is None else bool(ok), "mode": mode})

    if fmt == "xxx":
        low = exp["stitches"] - exp["run_starts"]
        add("stitch_count", f"{low} to {exp['stitches']}", got["stitches"],
            low <= got["stitches"] <= exp["stitches"], mode="run_starts_may_read_as_moves")
    else:
        add("stitch_count", exp["stitches"], got["stitches"])
    et, gt = exp["trim_at"], got["trim_at"]
    if fmt in _TRIMS_AT_LEAST:
        add("trim_count", f"at least {len(et)}", len(gt), len(gt) >= len(et), mode="at_least")
    else:
        add("trim_count", len(et), len(gt))
        if len(et) == len(gt):
            d = _first_diff(et, gt)
            add("trim_order", "same", "same" if d < 0 else f"trim {d + 1} follows {gt[d]} stitches, not {et[d]}", d < 0)
    add("color_count", len(exp["color_at"]), len(got["color_at"]))
    if len(exp["color_at"]) == len(got["color_at"]):
        d = _first_diff(exp["color_at"], got["color_at"])
        add("color_order", "same",
            "same" if d < 0 else f"change {d + 1} follows {got['color_at'][d]} stitches, not {exp['color_at'][d]}", d < 0)
    add("longest_stitch", f"at most {MAX_SEWN_UNITS / 10} mm", f"{got['longest'] / 10} mm", got["longest"] <= MAX_SEWN_UNITS)
    # Every design stitch must land where the design put it, in order (the
    # records between two landings are the splits of a long chained move).
    # Counts and the box alone miss a stitch that moved inside the design.
    tol = _BOX_TOLERANCE.get(fmt, 0)
    want, at = exp["landings"], 0
    for sx, sy in got["sewn"]:
        if at < len(want) and abs(sx - want[at][0]) <= tol and abs(sy - want[at][1]) <= tol:
            at += 1
    add("stitch_positions", f"{len(want)} stitches where the design puts them", f"{at} found in order", at == len(want))
    eb, gb = exp["sewn_box"], got["sewn_box"]
    box_ok = (eb is None and gb is None) or (
        eb is not None and gb is not None and all(abs(a - b) <= tol for a, b in zip(eb, gb)))
    add("bounding_box", eb, gb, box_ok)
    if fmt == "dst" and got["header_box"] is not None:
        h = got["header"]
        try:
            hb = [int(h["+X"]), int(h["-X"]), int(h["+Y"]), int(h["-Y"])]
        except (KeyError, ValueError):
            hb = None
        add("header_bbox", got["header_box"], hb,
            hb is not None and all(abs(a - b) <= got["header_tol"] for a, b in zip(hb, got["header_box"])))
    failed = [c for c in checks if not c["ok"]]
    return {
        "verified": True, "ok": not failed, "format": fmt, "checks": checks, "failed": failed,
        "skipped": skipped, "stitches": got["stitches"], "trims": len(gt),
        "colors": len(got["color_at"]), "longest_mm": got["longest"] / 10,
    }


def failure_detail(result: dict) -> str:
    """The customer's sentence for a failed read-back: names the first check
    and both values. Plain text, one line, safe to show."""
    first = result["failed"][0]
    more = len(result["failed"]) - 1
    tail = f" {more} more check{'s' if more > 1 else ''} failed too." if more else ""
    return (f"Export failed: {CHECK_LABEL[first['check']]} "
            f"(expected {first['expected']}, read back {first['read']}).{tail}")


def success_headers(result: dict) -> dict[str, str]:
    """Additive response headers for a file that read back, or one that cannot be."""
    if not result["verified"]:
        return {"X-Export-Verified": "false", "X-Export-Verify-Reason": result["reason"]}
    counts = {"stitches": result["stitches"], "trims": result["trims"],
              "colors": result["colors"], "longest_mm": result["longest_mm"]}
    # The checks this format's reader cannot give back (``_SKIPPED``), by name,
    # so the Studio can say "re-read, N checks skipped" instead of rounding a
    # partial read up to a full one. Omitted when there are none.
    if result.get("skipped"):
        counts["skipped"] = [s["check"] for s in result["skipped"]]
    return {"X-Export-Verified": "true", "X-Export-Readback": json.dumps(counts, separators=(",", ":"))}
