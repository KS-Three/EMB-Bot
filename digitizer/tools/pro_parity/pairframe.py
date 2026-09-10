"""One prepped design pair — the professional's file and ours — in ONE frame.

`overlay.py` draws and `diff.py` measures; both read the pair through this
module so a pixel in the overlay and a row in the catalogue are the same
registration. Registration is: one uniform scale (the pro's stitch width
over ours — never per-axis, an aspect mismatch is a finding), a y-flip
search (both are tried, the better IoU wins, and the result SAYS which), and
`scorecard.register`'s translation search. No rotation: a registration that
could absorb a redesign would hide it (Gaulke's re-composed layout is the
known case, and it is meant to fail loudly).

Frames: machine files are mm y-DOWN once divided by 10 (`prep_all.decode`,
`satin_columns.passes_from_file`); `ours.dst` was written from the plan, so
reading it back gives plan coordinates, the frame `ours_regions.json` is in.
The `Design` dict `stitchviz` draws is 0.1 mm y-UP; `Frame` below is the one
place that mapping lives, so renders and masks agree pixel for pixel.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pystitch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import scorecard as sc                                              # noqa: E402
from prep_all import GREYS                                          # noqa: E402
from digitizer_core.adapter import (design_bbox_units, pattern_to_design,  # noqa: E402
                                    UNITS_PER_MM)


@dataclass
class Pair:
    slug: str
    dir: Path
    pro_path: Path
    ours_path: Path
    regions: list
    art: Path
    garment_id: str | None
    width_mm: float
    pro_rgb: list
    ours_rgb: list


@dataclass
class Reg:
    scale: float
    flip_y: bool
    dx: float
    dy: float
    iou: float

    def apply_xy(self, x: float, y: float) -> tuple[float, float]:
        fy = -1.0 if self.flip_y else 1.0
        return self.scale * x + self.dx, self.scale * fy * y + self.dy

    def matrix(self) -> list[float]:
        """shapely.affinity.affine_transform's [a, b, d, e, xoff, yoff]."""
        fy = -1.0 if self.flip_y else 1.0
        return [self.scale, 0.0, 0.0, self.scale * fy, self.dx, self.dy]

    def as_dict(self) -> dict:
        d = asdict(self)
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def _lane_root(d: Path) -> Path:
    """`<out>/real/<slug>` or `<out>/real/<slug>/flags/<hash>` -> `<out>/real`."""
    d = Path(d).resolve()
    if d.parent.name == "flags":
        return d.parents[2]
    return d.parent


def _slug(d: Path) -> str:
    d = Path(d).resolve()
    return d.parents[1].name if d.parent.name == "flags" else d.name


def _rgbs(path: Path) -> list:
    try:
        return [tuple(b["rgb"]) for b in json.loads(Path(path).read_text())]
    except Exception:
        return []


def load_pair(d: Path) -> Pair:
    d = Path(d).resolve()
    slug = _slug(d)
    root = _lane_root(d)
    base = root / slug
    entry = {}
    man = root / "manifest.json"
    if man.exists():
        for e in json.loads(man.read_text()):
            if e.get("slug") == slug:
                entry = e
    pro = Path(entry["file"]) if entry.get("file") and Path(entry["file"]).exists() else None
    if pro is None:
        for n in ("pro.pes", "pro.dst", "pro.PES", "pro.DST"):
            if (base / n).exists():
                pro = base / n
                break
    if pro is None:
        raise FileNotFoundError(f"no pro file for {slug}: manifest {man} has no readable `file` "
                                f"and {base} holds no pro.pes/pro.dst")
    ours = d / "ours.dst"
    if not ours.exists():
        raise FileNotFoundError(f"{ours} — prep this design first (prep_both.py {slug})")
    regions = json.loads((d / "ours_regions.json").read_text()) if (d / "ours_regions.json").exists() else []
    # width_mm is what PREP used to size ours, i.e. prep_all.pro_meta's own
    # recorded `entry["pro"]["width_mm"]` (`run_ours` is called with that
    # exact number) -- not a fresh remeasurement of the pro file, which can
    # legitimately differ (0.1mm file quantization, or a synthetic fixture
    # that declares its own approximate width). Recompute from the file only
    # when the manifest carries nothing to read.
    pro_width = (entry.get("pro") or {}).get("width_mm")
    if pro_width is None:
        pro_width = x_extent(file_segs(pro, False))
    return Pair(slug=slug, dir=d, pro_path=pro, ours_path=ours, regions=regions,
                art=base / "art.png", garment_id=entry.get("garment_id"),
                width_mm=float(pro_width), pro_rgb=_rgbs(base / "pro_blocks.json"),
                ours_rgb=_rgbs(d / "ours_blocks.json"))


# ------------------------------------------------------------ registration
def _read_pattern(path: Path):
    """The one place a machine file is opened. Missing, garbage or empty
    files all end here with the same message, chained to the real cause.

    `pystitch.read` does not reliably raise on bad bytes with a recognised
    extension (a `.dst` of random bytes decodes to a live `EmbPattern` with
    zero or more STITCH records, no exception) -- so a missing/unreadable
    file is caught by the `except`, and a garbage-but-parseable one is
    caught by the stitch count below. `file_segs` and `design_for` both
    call this instead of `pystitch.read` directly, so the two readers can't
    diverge on what counts as unreadable.
    """
    try:
        pat = pystitch.read(str(path))
    except Exception as e:          # pystitch raises OSError, TypeError, ValueError on bad input
        raise SystemExit(f"unreadable: {path} ({type(e).__name__}: {e})") from e
    if pat is None:
        raise SystemExit(f"unreadable: {path} (pystitch returned no pattern)")
    n = sum(1 for _x, _y, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.STITCH)
    if n == 0:
        raise SystemExit(f"unreadable: {path} (no stitches)")
    return pat


def file_segs(path: Path, flip_y: bool = False) -> list:
    """A machine file (DST/PES/...) as scorecard segs, `(x0,y0,x1,y1,len,block,trimmed)`.

    Copied from `design_direction.pro_segs` (Ruling R4): importing that module
    pulls in the whole `digitizer_core` pipeline plus `curve_tiers`/
    `thin_strokes` and measured ~2-2.4s to import, well past the 2s bar for a
    plain file reader, so the body lives here instead.
    """
    pat = _read_pattern(Path(path))
    rows = []
    block = 0
    pending = False
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            rows.append((block, x / 10.0, (-y if flip_y else y) / 10.0, pending))
            pending = False
        elif c == pystitch.COLOR_CHANGE:
            block += 1
            pending = True
        elif c in (pystitch.TRIM, pystitch.STOP):
            pending = True
        elif c == pystitch.END:
            break
    return sc.to_segs(rows)


def x_extent(segs) -> float:
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    return (max(xs) - min(xs)) if xs else 0.0


def centre(segs) -> tuple[float, float]:
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    ys = [s[1] for s in segs] + [s[3] for s in segs]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def scale_segs(segs, s: float):
    return [(x0 * s, y0 * s, x1 * s, y1 * s, d * s, b, t) for (x0, y0, x1, y1, d, b, t) in segs]


def register_pair(pro_path: Path, ours_path: Path) -> Reg:
    pro = file_segs(Path(pro_path), False)
    if not pro:
        raise ValueError(f"{pro_path}: no stitches")
    best = None
    for flip in (False, True):
        ours = file_segs(Path(ours_path), flip)
        if not ours:
            raise ValueError(f"{ours_path}: no stitches")
        s = x_extent(pro) / max(x_extent(ours), 1e-9)
        ours_s = scale_segs(ours, s)
        pcx, pcy = centre(pro)
        ocx, ocy = centre(ours_s)
        dx, dy = pcx - ocx, pcy - ocy
        ours_c = sc.shifted(ours_s, dx, dy)
        bb = sc.bounds(pro, ours_c)
        rdx, rdy, iou = sc.register(pro, ours_c, bb)
        cand = Reg(scale=s, flip_y=flip, dx=dx + rdx, dy=dy + rdy, iou=float(iou))
        if best is None or cand.iou > best.iou:
            best = cand
    return best


# ------------------------------------------------------------------- frame
@dataclass
class Frame:
    """`render_design`'s pixel mapping, made explicit so masks and renders
    agree: px = (X - x0_mm + pad) * ppm, py = (Y + y1_mm + pad) * ppm for a
    file-frame point (X, Y) in mm y-down, where (x0, y1) are the pinned
    Design bounds in units (y-up)."""
    x0_units: int
    x1_units: int
    y0_units: int
    y1_units: int
    pad_mm: float
    ppm: float

    @property
    def size(self) -> tuple[int, int]:
        w = max(8, int(((self.x1_units - self.x0_units) / UNITS_PER_MM + 2 * self.pad_mm) * self.ppm))
        h = max(8, int(((self.y1_units - self.y0_units) / UNITS_PER_MM + 2 * self.pad_mm) * self.ppm))
        return w, h

    def to_px(self, X: float, Y: float) -> tuple[float, float]:
        return ((X - self.x0_units / UNITS_PER_MM + self.pad_mm) * self.ppm,
                (Y + self.y1_units / UNITS_PER_MM + self.pad_mm) * self.ppm)

    def mm_to_px_affine(self) -> np.ndarray:
        """2x3 matrix taking file-frame mm (X, Y) to frame pixels."""
        return np.array([[self.ppm, 0.0, (-self.x0_units / UNITS_PER_MM + self.pad_mm) * self.ppm],
                         [0.0, self.ppm, (self.y1_units / UNITS_PER_MM + self.pad_mm) * self.ppm]])

    @property
    def bounds_units(self):
        return (self.x0_units, self.x1_units, self.y0_units, self.y1_units)


def design_for(path: Path, reg: Reg | None, colors: list | None, name: str) -> dict:
    """A machine file as a Design dict, `reg` applied (ours) or not (pro)."""
    pat = _read_pattern(Path(path))
    fb = colors or list(GREYS)
    t = (lambda x, y: reg.apply_xy(x, y)) if reg is not None else None
    return pattern_to_design(pat, name=name, transform_mm=t, fallback_colors=fb)


def pin_frame(design: dict, bounds_units) -> dict:
    """Two jump records at the frame corners: `stitchviz._bounds` counts
    jumps and `render_design` draws nothing for them, so both sides of a
    pair render on identical canvases without touching the renderer."""
    x0, x1, y0, y1 = bounds_units
    d = dict(design)
    d["stitches"] = list(design["stitches"]) + [
        {"x": int(x0), "y": int(y0), "type": "jump"},
        {"x": int(x1), "y": int(y1), "type": "jump"},
    ]
    return d


def frame_for(designs: list, ppm: float, pad_mm: float = 2.0,
              crop_mm: tuple | None = None) -> Frame:
    """The union frame of several designs, or a crop window (file-frame mm,
    x0 y0 x1 y1, y-down) at `ppm`."""
    if crop_mm is not None:
        cx0, cy0, cx1, cy1 = crop_mm
        return Frame(int(round(cx0 * UNITS_PER_MM)), int(round(cx1 * UNITS_PER_MM)),
                     int(round(-cy1 * UNITS_PER_MM)), int(round(-cy0 * UNITS_PER_MM)), 0.0, ppm)
    boxes = [design_bbox_units(d) for d in designs]
    return Frame(min(b[0] for b in boxes), max(b[1] for b in boxes),
                 min(b[2] for b in boxes), max(b[3] for b in boxes), pad_mm, ppm)


# -------------------------------------------------------------- flag arms
def flags_hash(flags: dict) -> str:
    key = json.dumps(sorted(flags.items()), default=str)
    return hashlib.sha1(key.encode()).hexdigest()[:8]


def flags_dir(pair: Pair, flags: dict) -> Path:
    base = pair.dir if pair.dir.parent.name != "flags" else pair.dir.parents[1]
    return base / "flags" / flags_hash(flags)
