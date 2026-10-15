"""Which stitches are hard to sew fast, and what does a file say about speed?

    python -m tools.stitch_difficulty_census file PATH [PATH ...] [--json OUT]
    python -m tools.stitch_difficulty_census corpus [--fixtures a,b] [--json OUT]

Kent, 2026-10-14: "Do we adjust embroidery speeds for more challenging
stitches?" This tool MEASURES; it changes nothing in the engine, chooses no
speed and writes no machine file. It is OFF every path: nothing in
`digitizer_core/`, the service or the Studio imports it.

Two things per design:

1. **The command census** -- every machine command the file carries, including
   pystitch's SLOW (11) and FAST (12). A third-party file read through pystitch
   reports what the reader understood; for Barudan `.u01` / `.dsb` the raw
   control bytes are tallied too (`barudan_controls`), because pystitch's DSB
   reader STOPS at a control code it does not know, so a speed flag there would
   truncate the read rather than show up in the tally.
2. **The difficulty census** -- the stitch population the trade says a machine
   or an operator slows down for, each tied to a playbook law:

   - stitch-length bins (law 18 floors; law 36: firmware slows for stitches
     over 3-4 mm): `<0.5`, `0.5-1`, `1-4`, `4-7`, `>=7` mm, plus p50/p95/max;
   - `long_satin`: a sewn stitch >= 7 mm that reverses the previous one by
     more than 150 degrees -- a wide satin column's swing (law 31);
   - `sharp_turn`: a sewn stitch >= 1 mm turning 60-150 degrees from the
     previous one -- neither straight nor a satin swing (law 37's "jerky
     geometry"; no primary source gives a threshold, so this is a census,
     not a cutoff);
   - `near_hole`: a penetration within 0.5 mm of one of the 3rd..20th
     penetrations before it (law 17's same-hole radius; the two immediate
     predecessors are skipped so an ordinary satin or fill neighbour is not
     counted);
   - `peak_density`: the most penetrations in any 2 x 2 mm window, per mm2
     (law 20's contact-time lever).

Both sides go through the same pystitch `EmbPattern` stream: a third-party
file via `pystitch.read`, an EMB-Bot plan via `export.plan_to_pattern` (the
service's own export path), so the rules cannot differ between them.

Every number is a property of the FILE. Which speed any of it deserves is a
physical constant -- ROADMAP gate 1 -- and this tool does not propose one.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import pystitch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools._console import utf8_console  # noqa: E402

UNITS_PER_MM = 10.0
BIN_EDGES_MM = (0.5, 1.0, 4.0, 7.0)
BIN_NAMES = ("lt_0p5", "0p5_1", "1_4", "4_7", "ge_7")
LONG_SATIN_MM = 7.0
SATIN_SWING_DEG = 150.0
TURN_MIN_MM = 1.0
TURN_LO_DEG, TURN_HI_DEG = 60.0, 150.0
NEAR_HOLE_MM = 0.5
NEAR_HOLE_SKIP = 2          # i-1 and i-2 are ordinary neighbours
NEAR_HOLE_WINDOW = 20
DENSITY_CELL_MM = 1.0       # 2 x 2 cells -> a 2 x 2 mm window

COMMAND_NAMES = {
    pystitch.STITCH: "stitch", pystitch.JUMP: "jump", pystitch.TRIM: "trim",
    pystitch.STOP: "stop", pystitch.END: "end",
    pystitch.COLOR_CHANGE: "color_change", pystitch.NEEDLE_SET: "needle_set",
    pystitch.SLOW: "slow", pystitch.FAST: "fast",
}

# The corpus this answers over: the real customer logos the scorecard carries,
# the three synthetic-but-logo-shaped fixtures, and the one real fur photo.
FIXTURES = [
    "becker_marine_logo.png",
    "logo_script_tires.png",
    "photo/logo_bridge_bar.jpg",
    "photo/logo_gaulke_roofing.png",
    "photo/logo_golden_tee.jpg",
    "photo/logo_hotel_fremont.webp",
    "photo/screenshot_phone_ui_golke.jpg",
    "logo_alpha.png",
    "logo_whitebg.png",
    "photo/enthusiast_logo.png",
    "photo/owl_kent.jpg",
]
CFG = {"target_width_mm": 80.0, "garment_id": "left_chest"}


# --- streams -----------------------------------------------------------------

def stream_from_pattern(pattern) -> tuple[list[tuple[float, float, str]], Counter]:
    """-> ([(x_mm, y_mm, command)], tally of every command seen)."""
    out, tally = [], Counter()
    for x, y, cmd in pattern.stitches:
        name = COMMAND_NAMES.get(cmd & pystitch.COMMAND_MASK, f"other_{cmd & pystitch.COMMAND_MASK}")
        tally[name] += 1
        out.append((x / UNITS_PER_MM, y / UNITS_PER_MM, name))
    return out, tally


def read_file(path: Path):
    pattern = pystitch.read(str(path))
    if pattern is None:
        raise ValueError(f"pystitch cannot read {path.name}")
    return pattern


def barudan_controls(data: bytes, header: int) -> Counter:
    """Raw tally of a Barudan 3-byte stream's control codes (U01 / DSB).

    The low five bits of the control byte, as `pystitch.U01Writer` writes
    them: 0 stitch, 1 jump, 2 FAST, 3 FAST+jump, 4 SLOW, 5 SLOW+jump, 7 trim,
    8+ needle/stop. 0xF8 ends the stream.
    """
    tally = Counter()
    for i in range(header, len(data) - 2, 3):
        ctrl = data[i]
        if ctrl == 0xF8:
            break
        low = ctrl & 0x1F
        name = {0: "stitch", 1: "jump", 2: "fast", 3: "fast_jump", 4: "slow",
                5: "slow_jump", 7: "trim"}.get(low, "needle_or_stop" if low >= 8 else f"ctrl_{low}")
        tally[name] += 1
    return tally


# --- the census ----------------------------------------------------------------

def _angle_deg(ax: float, ay: float, bx: float, by: float) -> float:
    na, nb = math.hypot(ax, ay), math.hypot(bx, by)
    if na == 0 or nb == 0:
        return 0.0
    c = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
    return math.degrees(math.acos(c))


def census(stream: list[tuple[float, float, str]]) -> dict:
    """The difficulty census over one command stream (see module docstring)."""
    pens: list[tuple[float, float]] = []         # every needle penetration
    lengths: list[float] = []
    bins = Counter()
    long_satin = sharp = 0
    prev_cmd = None
    prev_pt = None
    prev_vec = None
    for x, y, cmd in stream:
        if cmd == "stitch":
            pens.append((x, y))
            if prev_cmd == "stitch" and prev_pt is not None:
                vx, vy = x - prev_pt[0], y - prev_pt[1]
                length = math.hypot(vx, vy)
                lengths.append(length)
                k = sum(length >= e for e in BIN_EDGES_MM)
                bins[BIN_NAMES[k]] += 1
                if prev_vec is not None:
                    ang = _angle_deg(prev_vec[0], prev_vec[1], vx, vy)
                    if length >= LONG_SATIN_MM and ang > SATIN_SWING_DEG:
                        long_satin += 1
                    if length >= TURN_MIN_MM and TURN_LO_DEG <= ang <= TURN_HI_DEG:
                        sharp += 1
                prev_vec = (vx, vy) if length > 0 else prev_vec
            else:
                prev_vec = None
            prev_pt = (x, y)
        elif cmd in ("jump", "trim", "color_change", "needle_set", "stop"):
            prev_pt = (x, y) if cmd == "jump" else prev_pt
            prev_vec = None
        prev_cmd = cmd

    near = 0
    r2 = NEAR_HOLE_MM ** 2
    for i, (x, y) in enumerate(pens):
        lo = max(0, i - NEAR_HOLE_WINDOW)
        for j in range(lo, i - NEAR_HOLE_SKIP):
            dx, dy = x - pens[j][0], y - pens[j][1]
            if dx * dx + dy * dy <= r2:
                near += 1
                break

    cells = Counter((math.floor(x / DENSITY_CELL_MM), math.floor(y / DENSITY_CELL_MM)) for x, y in pens)
    peak = 0
    for (cx, cy) in cells:
        s = sum(cells.get((cx + a, cy + b), 0) for a in (0, 1) for b in (0, 1))
        peak = max(peak, s)

    n = len(lengths)
    srt = sorted(lengths)

    def q(p):
        return round(srt[min(n - 1, int(p * n))], 2) if n else None

    def share(c):
        return round(c / n, 4) if n else None

    return {
        "penetrations": len(pens),
        "sewn_stitches": n,
        "bins": {b: share(bins[b]) for b in BIN_NAMES},
        "p50_mm": q(0.50), "p95_mm": q(0.95), "max_mm": round(srt[-1], 2) if n else None,
        "long_satin": share(long_satin),
        "sharp_turn": share(sharp),
        "near_hole": round(near / len(pens), 4) if pens else None,
        "peak_density_per_mm2": round(peak / (2 * DENSITY_CELL_MM) ** 2, 1),
    }


def file_row(path: Path) -> dict:
    stream, tally = stream_from_pattern(read_file(path))
    row = {"design": path.name, "source": "file", "commands": dict(tally), **census(stream)}
    ext = path.suffix.lower()
    if ext in (".u01", ".dsb"):
        row["raw_controls"] = dict(barudan_controls(path.read_bytes(), 0x100 if ext == ".u01" else 512))
    return row


def plan_row(fixture: str) -> dict:
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.export import plan_to_pattern
    from tools import corpus_scorecard as sc

    result, plan = digitize(sc.TESTDATA / fixture, PipelineConfig(**CFG))
    stream, tally = stream_from_pattern(plan_to_pattern(plan))
    return {"design": fixture, "source": "embbot", "class": result.design_class,
            "commands": dict(tally), **census(stream)}


# --- output --------------------------------------------------------------------

def table(rows: list[dict]) -> str:
    head = ("| design | stitches | <0.5 | 0.5-1 | 1-4 | 4-7 | >=7 | p95 mm | max mm | "
            "long satin | sharp turn | near hole | peak /mm2 | slow/fast |")
    lines = [head, "|" + "---|" * 14]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['design']} | error: {r['error']} |" + " |" * 12)
            continue
        b = r["bins"]
        c = r["commands"]
        rc = r.get("raw_controls", {})
        speed = (c.get("slow", 0) + c.get("fast", 0) + rc.get("slow", 0) + rc.get("fast", 0)
                 + rc.get("slow_jump", 0) + rc.get("fast_jump", 0))

        def pct(v):
            return "-" if v is None else f"{100 * v:.1f}%"

        lines.append(
            f"| {r['design']} | {r['sewn_stitches']} | {pct(b['lt_0p5'])} | {pct(b['0p5_1'])} | "
            f"{pct(b['1_4'])} | {pct(b['4_7'])} | {pct(b['ge_7'])} | {r['p95_mm']} | {r['max_mm']} | "
            f"{pct(r['long_satin'])} | {pct(r['sharp_turn'])} | {pct(r['near_hole'])} | "
            f"{r['peak_density_per_mm2']} | {speed} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("file", help="census of stitch files (any pystitch-readable format)")
    f.add_argument("paths", nargs="+", type=Path)
    f.add_argument("--json", type=Path)
    c = sub.add_parser("corpus", help="digitize the corpus logos + owl at 80 mm and census each plan")
    c.add_argument("--fixtures", default=",".join(FIXTURES))
    c.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    rows = []
    if a.cmd == "file":
        for p in a.paths:
            try:
                rows.append(file_row(p))
            except Exception as exc:  # noqa: BLE001 -- one bad file must not sink the run
                rows.append({"design": p.name, "error": f"{type(exc).__name__}: {exc}"})
    else:
        for fx in [s for s in a.fixtures.split(",") if s]:
            try:
                rows.append(plan_row(fx))
            except Exception as exc:  # noqa: BLE001
                rows.append({"design": fx, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[done] {fx}", flush=True)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
