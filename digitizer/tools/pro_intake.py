"""pro_intake: a professional job Kent drops in is measurable in one command.

WHAT IT IS FOR. Kent drops a job folder -- the art he sent the digitizer and
everything the digitizer sent back (DST, EMB, PES, a PDF worksheet, a preview
JPG), sometimes still zipped -- into `scratch_kent/Embroidery Files/<Job>/`.
This reads each NEW folder once, registers its pairs, and prints a census
that says which jobs carry fine lettering. After it, `tools.pro_pair --job
SLUG`, `tools.flip_sheet_renders --fixtures SLUG` and `tools.word_legibility
--digitize SLUG` take the new job by its slug.

THE REGISTRY. The pairs this repo already measures are a registry IN CODE
(DOCTRINE 2026-09-28, "count the registry, not the folder"):
`pro_parity.prep_all.DESIGNS` names every pro stitch file,
`pro_parity.blockcensus.FIXTURES` pairs committed ARTWORK with them,
`pro_parity.preview_split.MANIFEST` says which preview panel is artwork, and
`border_census.PAIRS` holds the (slug, pro, art, garment) rows the census
tools share. A new job cannot be added there by a script: the repo is PUBLIC
and a new job's folder name is a client's name. So this extends that registry
with ONE gitignored file beside the jobs (`scratch_kent/pro_intake/
registry.json`): a file the code tables already name keeps its slug and its
committed artwork, and only what they do not know is minted here.
`registered_pairs()` hands the pairs out in `border_census.PAIRS`' row
shape; a consumer searches its own table first, so a code row still wins.

PER JOB (each top-level folder under the root):
  zips     every .zip is extracted to a COPY under the scratch dir, never in
           place; a member byte-identical to a file already in the job is
           dropped (TIRES ships one zip twice beside its own unzipped folder).
  images   SOURCE ART vs the pro's PREVIEW, by content. A vendor preview is
           two panels of the SAME design (the art beside his stitch
           simulation, or two simulations: every Becker). Measured 2026-10-25
           over the 17 previews in the folder: the panels' ink boxes agree in
           aspect 0.96-1.00 and overlap (dilated IoU) 0.55-0.99, while every
           genuine artwork file has no gutter or splits into parts of aspect
           <= 0.70 (`PANEL_ASPECT_MIN`). The content decides and the name
           must agree: two panels named like a stitch file is a `preview`,
           one panel named like none is `art`. Disagreement is flagged and
           never used: `art?` (one panel named like a stitch file -- content
           cannot tell a one-panel simulation from art) and `preview?` (two
           panels named like none -- art that repeats a motif side by side,
           "AB  AB", splits exactly like a preview). WHICH panel of a preview
           is artwork is NOT inferred -- both statistics tried fail
           (DOCTRINE), so it stays `preview_split.MANIFEST`, set by a human; a
           preview listed there brings its recovered panel. A job with no
           usable art is flagged.
  pdf      the pro's worksheet when it is named like a stitch file or has a
           text layer (`PDF_TEXT_RUNS`); anything else is flagged.
  pairs    every DST is a pair; its garment (HAT / LC / BEANIE / PATCH) is
           read from its name, else from the one folder name that names one
           garment. Its PES (thread colours) is matched by CONTENT -- same
           colour changes, stitches within 0.5%, extents within 0.3 mm --
           because names drift ("beckers beanie.DST" is "beckers logo hat 2 A
           a.PES"). Its art: committed artwork registered for its slug, else
           art in the folder whose ink aspect agrees with the DST's within
           `ART_ASPECT_TOL`, else committed artwork of another pair of the job
           that agrees. A job holding two designs gets each its own.
  census   per pair, from the DST (never the PES: pystitch reports a TRIM at
           every PES jump -- Fremont patch 53 as PES, 21 as DST): size mm,
           colour blocks (distinct PES threads beside them), stitches, trims;
           and the smallest lettering cap per colour, read with
           `small_text_columns`' own piece reader (per colour block, stitches
           of 6 mm or less drawn 0.4 mm wide, opened 0.55 mm) and its own cap
           rule (`small_text_columns.line`), on lines found here: 3 or more
           pieces of one block of similar height, centres aligned, gaps under
           `LINE_GAP` heights, and not all one shape (a honeycomb is not a
           word). `--overlay DIR` draws them: look before quoting a number.

IDEMPOTENT. A registered job is not read again: its fingerprint (every file's
size and sha1) is checked, and a changed job is reported and re-read only
with --rescan.

    python -m tools.pro_intake                         # intake new jobs; census of them
    python -m tools.pro_intake --all [--markdown]      # census of every registered job
    python -m tools.pro_intake --rescan "Job Folder"   # read one job again
    python -m tools.pro_intake --list                  # registered pairs
    python -m tools.pro_intake --overlay DIR           # also draw each pair's lettering lines
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

TESTDATA = DIGITIZER / "testdata"
REGISTRY_VERSION = 1

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}
VECTOR_EXT = {".ai", ".eps", ".svg", ".cdr"}
#: machine formats pystitch reads; DST is the census's own
STITCH_EXT = {".dst", ".pes", ".pec", ".exp", ".jef", ".vp3", ".xxx", ".dsb", ".dsz", ".u01",
              ".tbf", ".sew", ".hus", ".vip", ".shv"}
PRO_SOURCE_EXT = {".emb", ".ofm", ".pxf", ".art", ".jan"}   # editing sources pystitch cannot read
JUNK = {".ds_store", "thumbs.db", "desktop.ini"}

PANEL_ASPECT_MIN = 0.90   # previews 0.96-1.00; genuine art splits at <= 0.70 (2026-10-25)
PANEL_IOU_MIN = 0.45      # previews 0.55-0.99 (dilated ink-mask IoU at 200 px wide)
PDF_TEXT_RUNS = 20        # text-showing operators in a worksheet's content streams
ART_ASPECT_TOL = 0.20     # art ink box vs the DST's extents, relative
PES_STITCH_TOL = 0.005    # a PES is the DST's twin within this share of stitches ...
PES_EXTENT_MM = 0.3       # ... and these mm of extents

GARMENT_IDS = {"HAT": "hat_front", "LC": "left_chest", "BEANIE": "beanie", "PATCH": "patch"}
#: precedence order: "C GOLKE hat beanie" is the beanie cut of the hat design
GARMENT_RX = [("BEANIE", re.compile(r"beani")),
              ("PATCH", re.compile(r"patch")),
              ("LC", re.compile(r"lc(?![a-z])|left ?chest|chest|polo")),
              ("HAT", re.compile(r"hat(?![a-z])|(?<![a-z])cap(?![a-z])"))]   # PROSEALHAT

LINE_MIN_PIECES = 3       # a lettering line has at least this many pieces
LINE_H_RATIO = 0.6        # pieces of one line: shorter / taller at least this
LINE_ALIGN = 0.35         # vertical centres within this many (taller) heights
LINE_GAP = 1.2            # horizontal gap at most this many heights
#: a piece outside these heights is not a letter: under 2 mm drawn (1.6 mm cap)
#: are knockdown-fill crumbs and bean dots -- the pro's own floor is 3.65 mm
PIECE_H_MM = (2.0, 40.0)
SAME_SHAPE_IOU = 0.85     # neighbours this alike (and within 5% in size) are one motif
#: a line whose pieces are this convex (median area / hull area) is cells of
#: a motif, not letters: ProSeal's honeycomb read as three "lines" at 3.5-5.7
#: mm at 0.96-0.97 without it -- and tesseract read one of them as "ODE" at
#: 95 -- while every real line on the 11 jobs sits at 0.66-0.90 (2026-10-25)
LINE_SOLIDITY_MAX = 0.93
#: a candidate line is LETTERING when tesseract reads at least this many
#: letters off its pieces at this confidence (psm 7, any of
#: `legibility.VARIANTS_MM`). Real lines on the 11 jobs read 73-96 (Becker's
#: MARINE lowest); graphic look-alikes 2-68 with 3+ letters (a truck's wheel
#: "AHN" 42, a strip inside GOLF "A" 44, cat fur "ARS" 68). Three letters is
#: `legibility.ART_MIN_LETTERS`: a lone confident letter is not a word.
OCR_CONF_MIN = 70.0
OCR_MIN_LETTERS = 3
OCR_TRIES_PER_COLOUR = 3    # candidates read per colour, smallest first (real jobs needed 2 at most)
FINE_CAP_MM = 5.0         # "fine lettering": the pro raises text under ~4 mm to ~4 (2026-10-21)


# ------------------------------------------------------------------ places
def kent_root() -> Path | None:
    """`EMB_SCRATCH_KENT`, else the first `scratch_kent/` above this checkout
    (a lane under .claude/worktrees/ finds the primary checkout's)."""
    env = os.environ.get("EMB_SCRATCH_KENT")
    if env:
        return Path(env)
    for p in (DIGITIZER, *DIGITIZER.parents):
        if (p / "scratch_kent").is_dir():
            return p / "scratch_kent"
    return None


def default_paths() -> tuple[Path | None, Path | None, Path | None]:
    """(jobs root, registry file, scratch dir) on this machine."""
    k = kent_root()
    if k is None:
        return None, None, None
    return k / "Embroidery Files", k / "pro_intake" / "registry.json", k / "pro_intake" / "unzipped"


def spec_of(path: Path, root: Path, scratch: Path) -> str:
    """A path as the registry stores it: `job:` under the jobs root,
    `scratch:` under the unzip dir, `testdata:` committed, else absolute."""
    path = Path(path).resolve()
    for kind, base in (("job", root), ("scratch", scratch), ("testdata", TESTDATA)):
        try:
            return f"{kind}:{path.relative_to(Path(base).resolve()).as_posix()}"
        except ValueError:
            continue
    return str(path)


def resolve(spec: str | None, reg: dict) -> Path | None:
    if not spec:
        return None
    kind, sep, rel = spec.partition(":")
    bases = {"job": reg.get("root"), "scratch": reg.get("scratch"), "testdata": str(TESTDATA)}
    if sep and kind in bases and bases[kind]:
        return Path(bases[kind]) / rel
    return Path(spec)


# ------------------------------------------------------------------ registry file
def load_registry(path: Path | None = None) -> dict:
    if path is None:
        path = default_paths()[1]
    if path is None or not Path(path).exists():
        return {"version": REGISTRY_VERSION, "jobs": {}}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_registry(reg: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def registered_pairs(path: Path | None = None, *, minted_only: bool = False,
                     with_art: bool = True) -> list[tuple[str, str, str, str]]:
    """Registered pairs in `border_census.PAIRS`' row shape (slug, the pro's
    DST, art, garment_id), ABSOLUTE paths (so `border_census.find` returns
    them as given); [] on a machine with no registry. `minted_only`: only
    the pairs no code table carries. `with_art`: only pairs with usable art."""
    reg = load_registry(path)
    rows = []
    for job in reg["jobs"].values():
        for p in job["pairs"]:
            if minted_only and p.get("slug_from") != "minted":
                continue
            art = resolve(p.get("art"), reg)
            if with_art and art is None:
                continue
            rows.append((p["slug"], str(resolve(p["dst"], reg)), str(art) if art else "",
                         p.get("garment_id") or ""))
    return rows


def pair_record(slug: str, path: Path | None = None) -> dict | None:
    """One registered pair, paths resolved: {slug, job, dst, pes, art,
    garment_id, width_mm, ...}; None when the slug is not registered."""
    reg = load_registry(path)
    for job_name, job in reg["jobs"].items():
        for p in job["pairs"]:
            if p["slug"] == slug:
                out = dict(p)
                out["job"] = job_name
                for k in ("dst", "pes", "art"):
                    out[k] = resolve(p.get(k), reg)
                out["width_mm"] = (p.get("census") or {}).get("width_mm")
                return out
    return None


# ------------------------------------------------------------------ the code tables
def norm_rel(rel: str) -> str:
    """A path under the jobs root, spelled so the zip's `To a T:Becker`, the
    Drive's `To a T_Becker` and the disk's `To a T-Becker` (and the zip's
    leading-space folder names) compare equal."""
    parts = [p.strip().lower().replace(":", "-").replace("_", "-") for p in re.split(r"[\\/]", rel)]
    return "/".join(p for p in parts if p)


def code_registry() -> dict:
    """What the committed tables already know, keyed for lookup."""
    from tools import border_census as bc
    from tools.pro_parity import blockcensus, prep_all, preview_split
    by_rel: dict[str, str] = {}
    for slug, rel in prep_all.DESIGNS:
        by_rel.setdefault(norm_rel(rel), slug)
    garment: dict[str, str] = {}
    for slug, pro_rel, _art, gid in bc.PAIRS:
        by_rel.setdefault(norm_rel(pro_rel), slug)
        garment.setdefault(slug, gid)
    art = {}
    for _name, path, input_class, pro_slug in blockcensus.FIXTURES:
        if input_class == "artwork" and Path(path).exists():
            art.setdefault(pro_slug, Path(path))
    manifest = {norm_rel(rel): (preview_split.OUT_DIR / f"{stem}.png", slug)
                for rel, (_which, stem, slug) in preview_split.MANIFEST.items()}
    known = set(by_rel.values()) | set(garment) | set(art) | {s for _p, s in manifest.values()}
    return {"by_rel": by_rel, "garment": garment, "art": art, "manifest": manifest, "known": known}


# ------------------------------------------------------------------ files
def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _junk(rel_parts) -> bool:
    return any(p == "__MACOSX" or p.startswith("._") or p.lower() in JUNK for p in rel_parts)


def loose_files(job_dir: Path) -> list[Path]:
    return sorted(p for p in job_dir.rglob("*")
                  if p.is_file() and not _junk(p.relative_to(job_dir).parts))


def fingerprint(job_dir: Path) -> str:
    h = hashlib.sha1()
    for p in loose_files(job_dir):
        h.update(f"{p.relative_to(job_dir).as_posix()}|{p.stat().st_size}|{_sha1(p)}\n".encode())
    return h.hexdigest()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "job"


def extract_zips(job_dir: Path, scratch: Path, job_slug: str) -> tuple[list[tuple[Path, str]], list[str]]:
    """Every zip in the job (and every zip inside one) extracted to a copy
    under `scratch/<job_slug>/`; -> ([(extracted file, "zip name!member")],
    [refused zip]). A zip with a member leaving its folder (absolute, ``..``)
    is refused whole; a Mac name's ``:`` becomes ``-`` (`To a T:Becker`);
    macOS metadata is skipped. A copy already there is not written again."""
    out: list[tuple[Path, str]] = []
    refused: list[str] = []
    queue = [(z, z.relative_to(job_dir).as_posix()) for z in loose_files(job_dir)
             if z.suffix.lower() == ".zip"]
    seen: set[str] = set()
    while queue:
        zpath, label = queue.pop(0)
        digest = _sha1(zpath)
        if digest in seen:
            continue
        seen.add(digest)
        dest = scratch / job_slug / f"{slugify(Path(label).stem)}_{digest[:8]}"
        with zipfile.ZipFile(zpath) as zf:
            members = []
            for info in zf.infolist():
                parts = [p for p in re.split(r"[\\/]", info.filename) if p not in ("", ".")]
                if info.is_dir() or not parts or _junk(parts):
                    continue
                if (info.filename.startswith(("/", "\\")) or ".." in parts
                        or re.match(r"^[A-Za-z]:", parts[0])):
                    members = None
                    break
                members.append((info, [q.replace(":", "-") for q in parts]))
            if members is None:
                refused.append(label)
                continue
            for info, parts in members:
                target = dest.joinpath(*parts)
                if not target.exists() or target.stat().st_size != info.file_size:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                member = f"{label}!{'/'.join(parts)}"
                if target.suffix.lower() == ".zip":
                    queue.append((target, member))
                else:
                    out.append((target, member))
    return out, refused


# ------------------------------------------------------------------ images
def _load_rgb(path: Path):
    import numpy as np
    from PIL import Image
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P", "PA"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return np.asarray(im.convert("RGB")).astype(int)


def _ink_box(mask):
    import numpy as np
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def ink_aspect(path: Path) -> float | None:
    """Width / height of an image's ink box (`preview_split`'s ink rule)."""
    import numpy as np
    from tools.pro_parity.preview_split import INK_DELTA, _background
    a = _load_rgb(path)
    m = _ink_box(np.abs(a - _background(a)).sum(2) > INK_DELTA)
    return None if m is None else m.shape[1] / m.shape[0]


def panel_test(path: Path) -> dict:
    """Is this image two panels of one design (a vendor preview)? Splits at
    `preview_split.find_gutter` and compares the two panels' ink boxes:
    aspect agreement (min/max) and dilated ink-mask IoU at a common size."""
    import cv2
    import numpy as np
    from tools.pro_parity.preview_split import INK_DELTA, NoSplit, _background, find_gutter
    a = _load_rgb(path)
    out = {"size": [int(a.shape[1]), int(a.shape[0])], "panels": 1, "aspect": None, "iou": None}
    try:
        axis, s, e = find_gutter(a)
    except NoSplit:
        return out
    p1, p2 = (a[:s], a[e:]) if axis == "H" else (a[:, :s], a[:, e:])
    m1 = _ink_box(np.abs(p1 - _background(a)).sum(2) > INK_DELTA)
    m2 = _ink_box(np.abs(p2 - _background(a)).sum(2) > INK_DELTA)
    out["axis"] = axis
    if m1 is None or m2 is None:
        return out
    r1, r2 = m1.shape[1] / m1.shape[0], m2.shape[1] / m2.shape[0]
    W = 200
    H = max(20, int(round(W / ((r1 + r2) / 2))))
    k = np.ones((5, 5), np.uint8)
    t1, t2 = (cv2.dilate((cv2.resize(m.astype(np.uint8), (W, H), interpolation=cv2.INTER_AREA) > 0)
                         .astype(np.uint8), k) > 0 for m in (m1, m2))
    out.update(panels=2, aspect=round(min(r1, r2) / max(r1, r2), 3),
               iou=round(float((t1 & t2).sum() / max(1, (t1 | t2).sum())), 3))
    return out


def is_preview(panel: dict) -> bool:
    return (panel.get("panels") == 2 and (panel.get("aspect") or 0) >= PANEL_ASPECT_MIN
            and (panel.get("iou") or 0) >= PANEL_IOU_MIN)


def pdf_text_runs(path: Path) -> int:
    """Text-showing operators (Tj / TJ) in a PDF's Flate content streams --
    a worksheet is a page of text; a vector logo's text is outlines."""
    import zlib
    data = path.read_bytes()
    n = 0
    for m in re.finditer(rb"stream\r?\n", data):
        end = data.find(b"endstream", m.end())
        if end < 0:
            break
        try:
            body = zlib.decompress(data[m.end():end])
        except zlib.error:
            body = data[m.end():end]
        n += len(re.findall(rb"\)\s*Tj|\]\s*TJ", body))
    return n


# ------------------------------------------------------------------ garments
def garments_in(name: str) -> list[str]:
    low = name.lower()
    return [g for g, rx in GARMENT_RX if rx.search(low)]


def garment_of(rel: str) -> tuple[str | None, str]:
    """(HAT / LC / BEANIE / PATCH or None, where it came from) for a path
    inside a job: the file name first (precedence BEANIE > PATCH > LC > HAT),
    else the nearest folder naming exactly ONE garment ("Hat & Polo" names
    two and says nothing)."""
    parts = [p for p in re.split(r"[\\/!]", rel) if p]
    found = garments_in(Path(parts[-1]).stem)
    if found:
        return found[0], "name"
    for folder in reversed(parts[:-1]):
        g = garments_in(Path(folder).stem)
        if len(g) == 1:
            return g[0], f"folder {folder.strip()!r}"
        if len(g) > 1:
            break
    return None, "unread"


# ------------------------------------------------------------------ the census
def lettering_lines(pcs: list[dict]) -> list[list[dict]]:
    """Groups of `small_text_columns.pieces` that read as lines of lettering
    (module docstring): per block, letter-sized pieces linked when similar in
    height, centred together and near in x; groups of `LINE_MIN_PIECES`+
    that are not one repeated motif."""
    import numpy as np
    cands = [p for p in pcs
             if PIECE_H_MM[0] <= p["y1"] - p["y0"] <= PIECE_H_MM[1]
             and (p["x1"] - p["x0"]) <= 3 * (p["y1"] - p["y0"])]
    parent = list(range(len(cands)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(cands):
        ha, ca = a["y1"] - a["y0"], (a["y0"] + a["y1"]) / 2
        for j in range(i + 1, len(cands)):
            b = cands[j]
            if b["block"] != a["block"]:
                continue
            hb, cb = b["y1"] - b["y0"], (b["y0"] + b["y1"]) / 2
            h = max(ha, hb)
            if min(ha, hb) / h < LINE_H_RATIO or abs(ca - cb) > LINE_ALIGN * h:
                continue
            gap = max(b["x0"] - a["x1"], a["x0"] - b["x1"])
            overlap = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            if gap > LINE_GAP * h or overlap > 0.5 * min(a["x1"] - a["x0"], b["x1"] - b["x0"]):
                continue
            parent[find(i)] = find(j)
    groups: dict[int, list[dict]] = {}
    for i, p in enumerate(cands):
        groups.setdefault(find(i), []).append(p)
    lines = []
    for g in groups.values():
        if len(g) < LINE_MIN_PIECES:
            continue
        g.sort(key=lambda p: p["x0"])
        alike = [_same_shape(a, b) for a, b in zip(g, g[1:])]
        if alike and np.mean(alike) > 0.6:
            continue
        if np.median([solidity(p["mask"]) for p in g]) > LINE_SOLIDITY_MAX:
            continue
        lines.append(g)
    return lines


def solidity(mask) -> float:
    """Area over convex-hull area of a piece's mask (the hull of pixel
    centres, grown by half its perimeter: a filled square reads 1.0)."""
    import cv2
    import numpy as np
    ys, xs = np.nonzero(mask)
    if len(xs) < 3:
        return 1.0
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    return float(len(xs)) / max(1.0, cv2.contourArea(hull) + 0.5 * cv2.arcLength(hull, True) + 1)


def block_pieces(blocks) -> list[dict]:
    """`small_text_columns.pieces`, one colour block at a time, each on a
    canvas cut to its own block (1 mm margin): the reader draws every block
    on the whole design's canvas, 29 s for a 40-block 150 mm design. Piece
    coordinates (mm and px) come back in the file's own frame, as there."""
    from tools import small_text_columns as stc
    out = []
    for bi, b in enumerate(blocks):
        pts = [q for q in b if q is not None]
        if not pts:
            continue
        ox = int(math.floor(min(q[0] for q in pts) * stc.PPM)) - int(stc.PPM)
        oy = int(math.floor(min(q[1] for q in pts) * stc.PPM)) - int(stc.PPM)
        dx, dy = ox / stc.PPM, oy / stc.PPM
        for p in stc.pieces([[None if q is None else (q[0] - dx, q[1] - dy) for q in b]]):
            p.update(block=bi, x0=p["x0"] + dx, x1=p["x1"] + dx, y0=p["y0"] + dy, y1=p["y1"] + dy,
                     ox=p["ox"] + ox, oy=p["oy"] + oy)
            out.append(p)
    return out


def _same_shape(a: dict, b: dict) -> bool:
    import cv2
    wa, ha = a["x1"] - a["x0"], a["y1"] - a["y0"]
    wb, hb = b["x1"] - b["x0"], b["y1"] - b["y0"]
    if abs(wa - wb) > 0.05 * max(wa, wb) or abs(ha - hb) > 0.05 * max(ha, hb):
        return False
    size = (32, 32)
    ma = cv2.resize(a["mask"].astype("uint8"), size, interpolation=cv2.INTER_AREA) > 0
    mb = cv2.resize(b["mask"].astype("uint8"), size, interpolation=cv2.INTER_AREA) > 0
    return (ma & mb).sum() / max(1, (ma | mb).sum()) >= SAME_SHAPE_IOU


def line_image(g: list[dict], pad_mm: float = 1.0):
    """A line's own pieces (the reader's opened masks), black on white, in
    the reader's px: travel, other blocks and neighbours left out."""
    import numpy as np
    from tools import small_text_columns as stc
    pp = int(round(pad_mm * stc.PPM))
    x0, y0 = min(p["ox"] for p in g), min(p["oy"] for p in g)
    x1 = max(p["ox"] + p["mask"].shape[1] for p in g)
    y1 = max(p["oy"] + p["mask"].shape[0] for p in g)
    img = np.full((y1 - y0 + 2 * pp, x1 - x0 + 2 * pp), 255, np.uint8)
    for p in g:
        h, w = p["mask"].shape
        img[p["oy"] - y0 + pp:p["oy"] - y0 + pp + h, p["ox"] - x0 + pp:p["ox"] - x0 + pp + w][p["mask"]] = 0
    return img


def read_line(g: list[dict]) -> dict:
    """Tesseract on a line (`legibility.ocr`, psm 7, its three variants):
    `ok` at the first variant reading `OCR_MIN_LETTERS`+ letters at
    `OCR_CONF_MIN`+, else the most confident reading, not ok."""
    from digitizer_core import legibility as core
    from tools import small_text_columns as stc
    from tools.word_legibility import norm
    img = line_image(g)
    best = ("", 0.0)
    for blur_mm, thin_mm in core.VARIANTS_MM:
        txt, conf = core.ocr(img, 7, blur_mm * stc.PPM, thin_mm * stc.PPM)
        if len(norm(txt)) >= OCR_MIN_LETTERS and conf >= OCR_CONF_MIN:
            return {"text": norm(txt), "conf": round(conf, 1), "ok": True}
        if norm(txt) and conf > best[1]:
            best = (norm(txt), conf)
    return {"text": best[0], "conf": round(best[1], 1), "ok": False}


def census_of(dst: Path, pes: Path | None = None, overlay: Path | None = None,
              ocr: bool | None = None) -> dict:
    """One pair's numbers, read off the DST (module docstring). Lettering
    per colour is its smallest line tesseract confirms (smallest first, at
    most `OCR_TRIES_PER_COLOUR` read); with no tesseract (`ocr` False) it is
    the smallest geometric line, and `ocr` says so."""
    from tools import small_text_columns as stc
    from tools.pro_pair import pro_counts
    if ocr is None:
        from digitizer_core.legibility import tesseract_available
        ocr = tesseract_available()
    c = pro_counts(dst)
    out = {"width_mm": c["width_mm"], "height_mm": c["height_mm"], "stitches": c["stitches"],
           "trims": c["trims"], "blocks": c["colour_changes"] + 1, "threads": None,
           "ocr": "tesseract" if ocr else "none: geometric lines only",
           "lettering": {}, "lines": []}
    colours = None
    if pes is not None:
        import pystitch
        tl = pystitch.read(str(pes)).threadlist
        hexes = [t.hex_color() for t in tl]
        out["threads"] = len(set(hexes)) or None
        if len(hexes) == out["blocks"]:
            colours = hexes
    blocks = stc.read_blocks(dst)
    found = []
    for g in lettering_lines(block_pieces(blocks)):
        res = stc.line(g, [], (-1e9, 1e9))
        if res.get("pieces"):
            found.append((res["cap_mm"], g, res))
    found.sort(key=lambda t: t[0])
    tries: dict[str, int] = {}
    for cap, g, res in found:
        b = g[0]["block"]
        label = colours[b] if colours else f"block {b + 1}"
        row = {"block": b + 1, "colour": label, "cap_mm": cap, "pieces": res["pieces"],
               "gap_med": res.get("gap_med"),
               "box": [round(min(p["x0"] for p in g), 1), round(min(p["y0"] for p in g), 1),
                       round(max(p["x1"] for p in g), 1), round(max(p["y1"] for p in g), 1)]}
        if ocr and label not in out["lettering"] and tries.get(label, 0) < OCR_TRIES_PER_COLOUR:
            tries[label] = tries.get(label, 0) + 1
            row["read"] = read_line(g)
            row["lettering"] = row["read"]["ok"]
        else:
            row["lettering"] = None if ocr else "unconfirmed"
        if label not in out["lettering"] and (row["lettering"] is True or not ocr):
            out["lettering"][label] = cap
        out["lines"].append(row)
    caps = list(out["lettering"].values())
    out["smallest_cap_mm"] = min(caps) if caps else None
    out["fine_lettering"] = bool(caps) and min(caps) < FINE_CAP_MM
    if overlay is not None:
        draw_overlay(blocks, out["lines"], overlay)
    return out


def draw_overlay(blocks, lines: list[dict], path: Path, ppm: float = 10.0) -> None:
    """The DST's needle-down runs, each found line boxed with its cap: red
    when tesseract confirmed it lettering, blue when it read something else,
    orange when it was not read."""
    import cv2
    import numpy as np
    from tools import small_text_columns as stc
    pts = [q for b in blocks for q in b if q is not None]
    W, H = (max(q[0] for q in pts) + 2) * ppm, (max(q[1] for q in pts) + 2) * ppm
    img = np.full((int(H) + 1, int(W) + 1, 3), 255, np.uint8)
    for b in blocks:
        for r in stc._runs(b):
            cv2.polylines(img, [np.round(np.array(r) * ppm).astype(np.int32)], False, (150, 150, 150), 1)
    for ln in lines:
        x0, y0, x1, y1 = (int(round(v * ppm)) for v in ln["box"])
        col = {True: (0, 0, 220), False: (220, 120, 0)}.get(ln.get("lettering"), (0, 150, 255))
        cv2.rectangle(img, (x0, y0), (x1, y1), col, 2 if ln.get("lettering") is True else 1)
        cv2.putText(img, f"{ln['cap_mm']:.1f}", (x0, max(12, y0 - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, col, 1, cv2.LINE_AA)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)


# ------------------------------------------------------------------ one job
def _counts(path: Path, cache: dict) -> dict | None:
    if path not in cache:
        try:
            from tools.pro_pair import pro_counts
            cache[path] = pro_counts(path)
        except (Exception, SystemExit):  # noqa: BLE001 -- an unreadable file is a finding
            cache[path] = None
    return cache[path]


def _twin(a: dict | None, b: dict | None) -> bool:
    return bool(a and b and a["colour_changes"] == b["colour_changes"]
                and abs(a["stitches"] - b["stitches"]) <= max(5, PES_STITCH_TOL * a["stitches"])
                and abs(a["width_mm"] - b["width_mm"]) <= PES_EXTENT_MM
                and abs(a["height_mm"] - b["height_mm"]) <= PES_EXTENT_MM)


def stem_key(name: str) -> str:
    """A file stem without its copy marks: "Machine beanie E-1 (1)" and
    "Machine beanie E" are one name."""
    k = Path(name).stem.strip().lower()
    while True:
        cut = re.sub(r"(\s*\(\d+\)|-\d+)$", "", k).strip()
        if cut == k:
            return k
        k = cut


def classify_files(files: list[tuple[Path, str]]) -> list[dict]:
    """Each file of a job -> {path, rel, kind, ...} (module docstring). An
    image is NAMED like a stitch file when its stem, copy marks off, is one;
    a two-panel image also when it CONTAINS one ("multi c golke logo hat
    (1)") -- containment confirms a preview, it never demotes art."""
    stems = {stem_key(rel) for _p, rel in files if Path(rel).suffix.lower() in STITCH_EXT | PRO_SOURCE_EXT}
    out = []
    for path, rel in files:
        ext = path.suffix.lower()
        row = {"path": path, "rel": rel}
        named_like_pro = stem_key(rel) in stems
        contains_pro = named_like_pro or any(k and k in stem_key(rel) for k in stems)
        if ext == ".dst":
            row["kind"] = "dst"
        elif ext in STITCH_EXT:
            row["kind"] = "stitch"
        elif ext in PRO_SOURCE_EXT:
            row["kind"] = "pro-source"
        elif ext in IMAGE_EXT:
            try:
                panel = panel_test(path)
            except Exception as e:  # noqa: BLE001 -- an unreadable image is a finding
                row.update(kind="unreadable", note=f"{type(e).__name__}: {e}"[:120])
                out.append(row)
                continue
            row["panel"] = panel
            if is_preview(panel) and contains_pro:
                row["kind"] = "preview"
            elif is_preview(panel):
                row["kind"] = "preview?"
                row["note"] = ("two panels of one shape, but named like no stitch file: a preview, "
                               "or art that repeats a motif side by side? look")
            elif named_like_pro:
                row["kind"] = "art?"
                row["note"] = "one panel, named like a stitch file: a simulation or art? look"
            else:
                row["kind"] = "art"
        elif ext == ".pdf":
            runs = pdf_text_runs(path)
            row["text_runs"] = runs
            row["kind"] = "worksheet" if named_like_pro or runs >= PDF_TEXT_RUNS else "pdf?"
        elif ext in VECTOR_EXT:
            row["kind"] = "vector-art"
            row["note"] = "vector art: export a PNG beside it to digitize"
        else:
            row["kind"] = "other"
        out.append(row)
    return out


def intake_job(job_dir: Path, root: Path, scratch: Path, code: dict, taken: set[str],
               overlay_dir: Path | None = None, ocr: bool | None = None) -> dict:
    """Read one job folder -> its registry record (module docstring)."""
    job_slug = slugify(job_dir.name)
    loose = loose_files(job_dir)
    files = [(p, p.relative_to(job_dir).as_posix()) for p in loose if p.suffix.lower() != ".zip"]
    have = {_sha1(p) for p, _ in files}
    dropped = 0
    extracted, refused = extract_zips(job_dir, scratch, job_slug)
    for p, label in extracted:
        h = _sha1(p)
        if h in have:
            dropped += 1
            continue
        have.add(h)
        files.append((p, label))
    rows = classify_files(files)
    flags: list[str] = [f"zip {z!r} refused: a member leaves the archive's folder" for z in refused]
    cache: dict = {}

    def job_rel(row) -> str:
        return f"{job_dir.name}/{row['rel']}"

    # art candidates: in the folder, and recovered panels of listed previews
    art_rows = []
    for r in rows:
        if r["kind"] == "art":
            asp = ink_aspect(r["path"])
            if asp:
                art_rows.append({"art": r["path"], "aspect": asp, "how": "job folder"})
        elif r["kind"] == "preview":
            hit = code["manifest"].get(norm_rel(job_rel(r)))
            r["art_panel"] = str(hit[0].relative_to(TESTDATA).as_posix()) if hit else None
            if hit is not None and hit[0].exists():
                art_rows.append({"art": hit[0], "aspect": ink_aspect(hit[0]),
                                 "how": "committed: preview_split.MANIFEST panel"})
            if hit is None:
                flags.append(f"preview {r['rel']!r}: which panel is art is a human call "
                             "(add it to preview_split.MANIFEST)")
        elif r["kind"] in ("art?", "preview?", "pdf?", "vector-art", "unreadable"):
            flags.append(f"{r['kind']} {r['rel']!r}: {r.get('note', 'look at it')}")

    dsts = [r for r in rows if r["kind"] == "dst"]
    others = [r for r in rows if r["kind"] == "stitch"]
    anchors = dsts or others
    if not anchors:
        flags.append("no readable stitch file")
    if not dsts and others:
        flags.append("no DST: trims below are the PES reader's, not a fair count")
    pairs = []
    for r in anchors:
        dc = _counts(r["path"], cache)
        if dc is None:
            flags.append(f"unreadable stitch file {r['rel']!r}")
            continue
        pes = None
        if r["kind"] == "dst":
            twins = [o for o in others if o["path"].suffix.lower() == ".pes"
                     and _twin(dc, _counts(o["path"], cache))]
            twins.sort(key=lambda o: Path(o["rel"]).stem.strip().lower() != Path(r["rel"]).stem.strip().lower())
            pes = twins[0] if twins else None
        slug = (code["by_rel"].get(norm_rel(job_rel(r)))
                or (pes and code["by_rel"].get(norm_rel(job_rel(pes)))))
        slug_from = "code" if slug else "minted"
        g, g_from = garment_of(r["rel"])
        if not slug:
            base = f"{job_slug}_{g.lower()}" if g else f"{job_slug}_{slugify(Path(r['rel']).stem)}"
            slug = base if base not in taken else f"{job_slug}_{slugify(Path(r['rel']).stem)}"
            n = 2
            while slug in taken:
                slug = f"{base}_{n}"
                n += 1
        taken.add(slug)
        gid = GARMENT_IDS.get(g) if g else code["garment"].get(slug)
        if g is None:
            flags.append(f"garment unread for {r['rel']!r}")
        pairs.append({"slug": slug, "slug_from": slug_from, "dst": r["path"], "dst_rel": r["rel"],
                      "pes": pes["path"] if pes else None, "garment": g, "garment_from": g_from,
                      "garment_id": gid, "aspect": dc["width_mm"] / max(1e-6, dc["height_mm"])})

    # art per pair (module docstring)
    committed = [{"art": code["art"][p["slug"]], "how": "committed: blockcensus.FIXTURES",
                  "aspect": ink_aspect(code["art"][p["slug"]])} for p in pairs if p["slug"] in code["art"]]
    for p in pairs:
        choice = None
        if p["slug"] in code["art"]:
            choice = next(c for c in committed if c["art"] == code["art"][p["slug"]])
        else:
            for pool in (art_rows, committed):
                ok = [c for c in pool if c["aspect"] and abs(c["aspect"] / p["aspect"] - 1) <= ART_ASPECT_TOL]
                if ok:
                    choice = min(ok, key=lambda c: abs(c["aspect"] / p["aspect"] - 1))
                    break
        p["art"] = choice["art"] if choice else None
        p["art_how"] = choice["how"] if choice else None
        p["art_aspect"] = round(choice["aspect"], 3) if choice and choice["aspect"] else None
        p["sha1"] = _sha1(p["dst"])
        p["census"] = census_of(p["dst"], p["pes"],
                                overlay_dir / f"{p['slug']}.png" if overlay_dir else None, ocr)
    if pairs and not any(p["art"] for p in pairs):
        flags.append("NO SOURCE ART: nothing here or committed can be digitized for this job")
    elif any(not p["art"] for p in pairs):
        flags.append("no art for: " + ", ".join(p["slug"] for p in pairs if not p["art"]))

    def sp(path):
        return spec_of(path, root, scratch) if path else None

    return {
        "slug": job_slug, "intake": date.today().isoformat(), "fingerprint": fingerprint(job_dir),
        "zip_members_dropped_as_duplicates": dropped,
        "files": [{"file": f"{r['rel']}", "kind": r["kind"],
                   **({"panel": r["panel"]} if "panel" in r else {}),
                   **({"art_panel": r["art_panel"]} if r.get("art_panel") else {}),
                   **({"text_runs": r["text_runs"]} if "text_runs" in r else {}),
                   **({"note": r["note"]} if r.get("note") else {}),
                   "path": sp(r["path"])} for r in rows],
        "flags": flags,
        "pairs": [{"slug": p["slug"], "slug_from": p["slug_from"], "dst": sp(p["dst"]),
                   "pes": sp(p["pes"]), "garment": p["garment"], "garment_from": p["garment_from"],
                   "garment_id": p["garment_id"], "art": sp(p["art"]), "art_how": p["art_how"],
                   "art_aspect": p["art_aspect"], "dst_aspect": round(p["aspect"], 3),
                   "sha1": p["sha1"], "same_as": None, "census": p["census"]} for p in pairs],
    }


# ------------------------------------------------------------------ the run
def job_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and not _junk([p.name]))


def run(root: Path, registry: Path, scratch: Path, *, rescan: list[str] | None = None,
        overlay_dir: Path | None = None, ocr: bool | None = None, log=print) -> dict:
    """Intake every job folder not yet registered (and `rescan`'s); -> a
    report {new, changed, unchanged, gone}. Writes the registry once."""
    reg = load_registry(registry)
    reg["version"] = REGISTRY_VERSION
    reg["root"], reg["scratch"] = str(Path(root).resolve()), str(Path(scratch).resolve())
    code = code_registry()
    taken = set(code["known"]) | {p["slug"] for j in reg["jobs"].values() for p in j["pairs"]}
    report = {"new": [], "changed": [], "unchanged": [], "gone": []}
    present = job_dirs(Path(root))
    again = {r.strip() for r in rescan or []}      # " Golden Tee": the zip's leading space
    for d in present:
        old = reg["jobs"].get(d.name)
        if old is not None and d.name.strip() not in again:
            (report["unchanged"] if fingerprint(d) == old["fingerprint"] else report["changed"]).append(d.name)
            continue
        if old is not None:
            taken -= {p["slug"] for p in old["pairs"]}
        log(f"[intake] {d.name}")
        reg["jobs"][d.name] = intake_job(d, Path(root), Path(scratch), code, taken, overlay_dir, ocr)
        report["new"].append(d.name)
    report["gone"] = sorted(set(reg["jobs"]) - {d.name for d in present})
    if report["new"]:
        mark_duplicates(reg, report["new"])
        save_registry(reg, registry)
    return report


def mark_duplicates(reg: dict, new: list[str]) -> None:
    """A DST byte-identical to another registered one (Gaulke Plowing's
    `c golke logo LC.DST` is Gaulke Roofing's): in each NEW job, every copy
    but the canonical one -- the code tables' pair, else the one registered
    first -- gets `same_as` and a flag (count it once in an aggregate), and
    takes the canonical's art when it found none."""
    groups: dict[str, list[tuple[str, dict]]] = {}
    for name, job in reg["jobs"].items():
        for p in job["pairs"]:
            groups.setdefault(p.get("sha1") or id(p), []).append((name, p))
    for members in groups.values():
        if len(members) < 2:
            continue
        canon = next((m for m in members if m[1]["slug_from"] == "code"), members[0])
        for name, p in members:
            if p is canon[1] or name not in new:
                continue
            p["same_as"] = canon[1]["slug"]
            msg = f"{p['slug']} is byte-identical to {canon[1]['slug']}: count it once in an aggregate"
            if not p.get("art") and canon[1].get("art"):
                p["art"], p["art_how"] = canon[1]["art"], f"same bytes as {canon[1]['slug']}"
                reg["jobs"][name]["flags"] = [f for f in reg["jobs"][name]["flags"]
                                              if not f.startswith(("NO SOURCE ART", "no art for"))]
                missing = [q["slug"] for q in reg["jobs"][name]["pairs"] if not q.get("art")]
                if missing:
                    reg["jobs"][name]["flags"].append("no art for: " + ", ".join(missing))
            reg["jobs"][name]["flags"].append(msg)


def census_rows(reg: dict, jobs: list[str] | None = None) -> list[dict]:
    rows = []
    for name, job in reg["jobs"].items():
        if jobs is not None and name not in jobs:
            continue
        for p in job["pairs"] or [{}]:
            c = p.get("census") or {}
            rows.append({"job": name.strip(), "pair": p.get("slug", "-"), "garment": p.get("garment") or "?",
                         "size": f"{c['width_mm']:.1f} x {c['height_mm']:.1f}" if c else "-",
                         "colours": (f"{c['blocks']}" + (f" ({c['threads']} thr)" if c.get("threads") else ""))
                         if c else "-",
                         "stitches": c.get("stitches", "-"), "trims": c.get("trims", "-"),
                         "smallest": (f"{c['smallest_cap_mm']:.1f}"
                                      + ("" if c.get("ocr") == "tesseract" else "?"))
                         if c.get("smallest_cap_mm") else "-",
                         "per_colour": ", ".join(f"{k} {v:.1f}" for k, v in sorted(
                             (c.get("lettering") or {}).items(), key=lambda kv: kv[1])) or "-",
                         "fine": "FINE" if c.get("fine_lettering") else "",
                         "art": (p.get("art_how") or "NONE").split(":")[0] if p else "-",
                         "flags": len(job["flags"])})
    return rows


COLUMNS = [("job", "job"), ("pair", "pair"), ("garment", "garment"), ("size", "size mm"),
           ("colours", "colours"), ("stitches", "stitches"), ("trims", "trims (DST)"),
           ("smallest", "min cap mm"), ("per_colour", "min cap per colour, mm"), ("fine", "fine"),
           ("art", "art"), ("flags", "flags")]


def format_table(rows: list[dict], markdown: bool = False) -> str:
    heads = [h for _k, h in COLUMNS]
    cells = [[str(r[k]) for k, _h in COLUMNS] for r in rows]
    if markdown:
        lines = ["| " + " | ".join(heads) + " |", "|" + "---|" * len(heads)]
        lines += ["| " + " | ".join(c) + " |" for c in cells]
        return "\n".join(lines)
    widths = [max(len(h), *(len(c[i]) for c in cells)) if cells else len(h) for i, h in enumerate(heads)]
    fmt = "  ".join(f"{{:{w}}}" for w in widths)
    return "\n".join([fmt.format(*heads), fmt.format(*("-" * w for w in widths))]
                     + [fmt.format(*c) for c in cells])


def print_flags(reg: dict, jobs: list[str]) -> None:
    for name in jobs:
        job = reg["jobs"].get(name)
        if job and job["flags"]:
            print(f"\n{name.strip()}:")
            for f in job["flags"]:
                print(f"  - {f}")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.pro_intake",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    root, registry, scratch = default_paths()
    ap.add_argument("--root", type=Path, default=root, help="the folder holding the job folders")
    ap.add_argument("--registry", type=Path, default=registry)
    ap.add_argument("--scratch", type=Path, default=scratch, help="where zips are extracted")
    ap.add_argument("--rescan", action="append", default=[], metavar="JOB", help="read this job again")
    ap.add_argument("--all", action="store_true", help="census of every registered job")
    ap.add_argument("--list", action="store_true", help="registered pairs, one per line")
    ap.add_argument("--markdown", action="store_true", help="the census as a Markdown table")
    ap.add_argument("--json", type=Path, help="write the census rows here")
    ap.add_argument("--overlay", type=Path, help="draw each new pair's lettering lines here")
    ap.add_argument("--no-ocr", action="store_true",
                    help="skip tesseract: lettering lines are geometric only (marked '?')")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    args = parse_args(argv)
    if args.registry is None or (args.root is None and not (args.all or args.list)):
        raise SystemExit("no scratch_kent/ found: set EMB_SCRATCH_KENT or pass --root/--registry/--scratch")
    if args.list:
        reg = load_registry(args.registry)
        for name, job in reg["jobs"].items():
            for p in job["pairs"]:
                print(f"{p['slug']:32s} {p.get('garment') or '?':7s} {name.strip()!r}  "
                      f"dst={p['dst']}  art={p.get('art')}")
        return 0
    if not args.all:
        if not args.root.is_dir():
            raise SystemExit(f"jobs root not found: {args.root}")
        rep = run(args.root, args.registry, args.scratch, rescan=args.rescan, overlay_dir=args.overlay,
                  ocr=False if args.no_ocr else None)
        print(f"\nnew {len(rep['new'])}, unchanged {len(rep['unchanged'])}, "
              f"changed {len(rep['changed'])}, gone {len(rep['gone'])}  (registry: {args.registry})")
        for name in rep["changed"]:
            print(f"  CHANGED since intake: {name!r} -- read it again with --rescan {name!r}")
        for name in rep["gone"]:
            print(f"  registered but no longer on disk: {name!r}")
        jobs = rep["new"]
    else:
        jobs = None
    reg = load_registry(args.registry)
    rows = census_rows(reg, jobs)
    if rows:
        print()
        print(format_table(rows, markdown=args.markdown))
        print_flags(reg, jobs if jobs is not None else list(reg["jobs"]))
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
