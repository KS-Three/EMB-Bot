"""garment_size_census: the size the professional sews each design at, by
garment, against what our auto-fit gives the same artwork (2026-10-26).

Auto-fit (`src/garments.js` `fitScale`) scales the artwork's box into the
garment's placement box, capped to the largest hoop. The placement boxes are
round inches (Hat Front 5.0 x 2.25 in, Left Chest 4 x 4, Beanie 4.5 x 2.5),
not the pro's: 5 of 13 hats he sews TALLER than our 57.2 mm. This reads every
paired stitch file the same way and states his box per garment.

WHAT IT READS.

  * The stitch files: every DST / PES in `Embroidery Files.zip` (the repo
    root; `__MACOSX` and `Test Files` -- loose third-party illustrations, no
    garment -- left out) and in the Bridge folder
    (`BRIDGE`, outside the repo). Size: `pro_pair.pro_counts` (pystitch
    extents), the census every other pro tool reads.
  * One row per DESIGN: byte-identical files count once (Gaulke Plowing's
    `c golke logo LC.DST` is Gaulke Roofing's), and a DST and PES of one job,
    one garment, within `TWIN_MM` of each other's extents are one design.
  * The garment: `pro_intake.garment_of` -- the file name first (BEANIE >
    PATCH > LC > HAT), else the one folder that names a single garment.
    Unread (Gaulke's `GOLKE LOGO JB 1`, a jacket back) is reported, not sized.
  * The artwork's aspect: its ink box (`pro_intake.ink_aspect`) when the
    pro-intake registry (`scratch_kent/pro_intake/registry.json`, gitignored:
    folder names are client names) or the committed pairs name the art; else
    the pro file's own aspect, flagged.

WHAT IT STATES, per garment: the pro's width and height ranges; auto-fit
today (`TODAY_BOX`, the JS rule mirrored here) per design and its ratio to his
width; and HIS box -- the (w, h) box that, fitting each design's own aspect,
best reproduces his widths (median relative error, grid `GRID_STEP_MM`) --
with every row it misses by more than `MISS_TOL` named.

    python -m tools.garment_size_census [--json OUT] [--registry PATH]

Nothing here changes an engine default; the flip is Kent's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import tempfile
import zipfile
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

ZIP = REPO / "Embroidery Files.zip"
BRIDGE = Path(r"C:\Users\EE-LT-11030\Claude Personal\Embroidery\Digitized Designs\Bridge Logo")


def _up(rel: str) -> Path:
    """`rel` under the nearest checkout holding it: a lane under
    `.claude/worktrees/` has no `scratch_kent` of its own (gitignored, in the
    main checkout)."""
    for base in (REPO, *REPO.parents):
        if (base / rel).exists():
            return base / rel
    return REPO / rel


REGISTRY = _up("scratch_kent/pro_intake/registry.json")
#: the committed pairs' art, by slug prefix, for files the registry does not know
ART_BY_PREFIX = {"bridge": DIGITIZER / "testdata" / "photo" / "logo_bridge_bar.jpg"}

#: `src/garments.js` GARMENTS (inches) for the garments the pro's files hold
GARMENT_IN = {"hat_front": (5.0, 2.25), "left_chest": (4.0, 4.0), "beanie": (4.5, 2.5),
              "patch": (3.5, 3.5)}
GARMENT_ID = {"HAT": "hat_front", "LC": "left_chest", "BEANIE": "beanie", "PATCH": "patch"}
#: `src/garments.js` HOOPS[-1] and HOOP_FIT_MARGIN_MM
LARGEST_HOOP_MM = (200.0, 200.0)
HOOP_FIT_MARGIN_MM = 1.0

TWIN_MM = 0.3          # a DST and a PES of one design (`pro_intake.PES_EXTENT_MM`)
GRID_STEP_MM = 0.5     # his box is searched on this grid
MISS_TOL = 0.05        # a row his box misses by more than this (relative width) is named


def today_box(garment: str) -> tuple[float, float]:
    """`autoFitBoxMm`: the placement box capped to the largest hoop's field."""
    w_in, h_in = GARMENT_IN[garment]
    return (min(w_in * 25.4, LARGEST_HOOP_MM[0] - 2 * HOOP_FIT_MARGIN_MM),
            min(h_in * 25.4, LARGEST_HOOP_MM[1] - 2 * HOOP_FIT_MARGIN_MM))


def fit(aspect: float, box: tuple[float, float]) -> tuple[float, float]:
    """`fitScale` for a design of this width / height: (w, h) mm."""
    bw, bh = box
    s = min(bw / aspect, bh)          # the height it gets
    return s * aspect, s


# ------------------------------------------------------------------ the files
def _stitch_files():
    """(source label, relative path, local file) for every pro stitch file."""
    tmp = Path(tempfile.mkdtemp(prefix="garment_size_"))
    if ZIP.exists():
        with zipfile.ZipFile(ZIP) as z:
            for name in z.namelist():
                low = name.lower()
                if (not low.endswith((".dst", ".pes")) or "__macosx" in low
                        or "/test files/" in low or Path(name).name.startswith("._")):
                    continue
                out = tmp / hashlib.sha1(name.encode()).hexdigest()[:12] / Path(name).name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(z.read(name))
                rel = name.split("/", 1)[1] if name.startswith("Embroidery Files/") else name
                yield "zip", rel, out
    if BRIDGE.exists():
        for f in sorted(BRIDGE.iterdir()):
            if f.suffix.lower() in (".dst", ".pes"):
                yield "bridge", f"Bridge Logo/{f.name}", f


def _job_key(job: str) -> str:
    """A job folder as both sources spell it: the zip has "To a T:Becker
    Beanies", the registry "To a T-Becker Beanies"."""
    return "".join(ch for ch in job.lower() if ch.isalnum())


def _art_path(art: str | None, root: Path) -> Path | None:
    """The registry's art reference as a file: `testdata:X` is committed,
    `job:X` lies under the registry's root (the unzipped jobs)."""
    if not art:
        return None
    kind, _, rest = art.partition(":")
    if kind == "testdata":
        return DIGITIZER / "testdata" / rest.strip()
    if kind == "job":
        return root / rest.strip()
    return Path(art)


def _registry(registry: Path) -> dict:
    """{(job key, file name lower): {slug, garment, art}} from the pro-intake
    registry, when it is on this machine."""
    if not registry.exists():
        return {}
    d = json.loads(registry.read_text(encoding="utf-8"))
    root = Path(d.get("root") or registry.parent)
    out = {}
    for job, j in d.get("jobs", {}).items():
        for p in j.get("pairs", []):
            for key in ("dst", "pes"):
                path = p.get(key)
                if path:
                    out[(_job_key(job), path.split("/")[-1].lower())] = {
                        "slug": p["slug"], "garment": p.get("garment_id"),
                        "art": _art_path(p.get("art"), root)}
    return out


def _committed_art() -> dict:
    """{slug: art} for the committed pairs (`border_census.PAIRS`): the art a
    pro tool already digitizes them from. Ahead of the registry, whose art
    match is by aspect (it gives Becker's beanie the To a T art)."""
    from tools import border_census as bc
    out = {}
    for row in bc.PAIRS:
        try:
            _pro, art = bc.find_pair(*row[:3])
        except Exception:      # noqa: BLE001 -- a missing Drive is not this tool's failure
            art = None
        if art is not None:
            out[row[0]] = Path(art)
    return out


def designs(registry: Path = REGISTRY) -> list[dict]:
    from tools.pro_intake import garment_of, ink_aspect
    from tools.pro_pair import pro_counts

    reg = _registry(registry)
    committed = _committed_art()
    seen_sha: dict[str, str] = {}
    rows: list[dict] = []
    for source, rel, path in _stitch_files():
        data = path.read_bytes()
        sha = hashlib.sha1(data).hexdigest()
        job = rel.split("/")[0].strip()
        known = reg.get((_job_key(job), Path(rel).name.lower()), {})
        g, how = garment_of(rel)
        garment = GARMENT_ID.get(g) if g else None
        if known.get("garment"):
            garment, how = known["garment"], "registry"
        c = pro_counts(path)
        row = {"source": source, "job": job, "file": Path(rel).name, "garment": garment,
               "garment_from": how, "w": c["width_mm"], "h": c["height_mm"], "same_as": None}
        if sha in seen_sha:
            row["same_as"] = seen_sha[sha]
        else:
            seen_sha[sha] = f"{job}/{row['file']}"
        twin = next((r for r in rows if r["same_as"] is None and r["job"] == job
                     and r["garment"] == garment and abs(r["w"] - row["w"]) <= TWIN_MM
                     and abs(r["h"] - row["h"]) <= TWIN_MM), None)
        if twin is not None and row["same_as"] is None:
            row["same_as"] = f"{twin['job']}/{twin['file']}"
        slug = known.get("slug")
        art = committed.get(slug) if slug else None
        art = art or known.get("art")
        if art is None:
            for pre, fb in ART_BY_PREFIX.items():
                if job.lower().startswith(pre) and fb.exists():
                    art = fb
        if source == "bridge" and garment:       # the committed pairs' slugs
            slug = slug or {"hat_front": "bridge_hat", "left_chest": "bridge_lc"}.get(garment)
        row["slug"] = slug or f"{_job_key(job)}_{garment or 'unread'}"
        row["pro_aspect"] = round(row["w"] / row["h"], 3)
        asp = ink_aspect(art) if art is not None and Path(art).exists() else None
        row["art"] = Path(art).name if art is not None else None
        row["art_aspect"] = round(asp, 3) if asp else None
        rows.append(row)
    return rows


# ------------------------------------------------------------------ the boxes
def _aspect(r: dict, key: str) -> float:
    return r[key] or r["pro_aspect"]


def his_box(rows: list[dict], key: str = "art_aspect") -> dict:
    """The box that, fitting each design at `key`'s aspect (the ARTWORK's
    ink box: what auto-fit sees, the pro file's where no art is known),
    best reproduces his widths: median relative error first, then the
    worst. `key="pro_aspect"` reads his own designs' box instead."""
    best = None
    ws = [r["w"] for r in rows]
    hs = [r["h"] for r in rows]
    w0, w1 = math.floor(min(ws)), math.ceil(max(ws) * 1.15)
    h0, h1 = math.floor(min(hs)), math.ceil(max(hs) * 1.15)
    steps_w = int((w1 - w0) / GRID_STEP_MM) + 1
    steps_h = int((h1 - h0) / GRID_STEP_MM) + 1
    for i in range(steps_w):
        bw = w0 + i * GRID_STEP_MM
        for j in range(steps_h):
            bh = h0 + j * GRID_STEP_MM
            errs = [fit(_aspect(r, key), (bw, bh))[0] / r["w"] - 1 for r in rows]
            score = (round(statistics.median(abs(e) for e in errs), 4), round(max(abs(e) for e in errs), 4))
            if best is None or score < best[0]:
                best = (score, bw, bh, errs)
    (med, worst), bw, bh, errs = best
    return {"w": bw, "h": bh, "median_err": med, "worst_err": worst,
            "misses": [(r["slug"], round(e, 3)) for r, e in zip(rows, errs) if abs(e) > MISS_TOL]}


def census(rows: list[dict]) -> dict:
    out = {}
    for garment in GARMENT_IN:
        rs = [r for r in rows if r["garment"] == garment and r["same_as"] is None]
        if not rs:
            continue
        box = today_box(garment)
        for r in rs:
            asp = r["art_aspect"] or r["pro_aspect"]
            fw, fh = fit(asp, box)
            r["today"] = (round(fw, 1), round(fh, 1))
            r["today_ratio"] = round(fw / r["w"], 3)
        out[garment] = {
            "n": len(rs), "today_box": [round(v, 2) for v in box],
            "w_range": [min(r["w"] for r in rs), max(r["w"] for r in rs)],
            "h_range": [min(r["h"] for r in rs), max(r["h"] for r in rs)],
            "taller_than_today": [r["slug"] for r in rs if r["h"] > box[1] + 0.05],
            "wider_than_today": [r["slug"] for r in rs if r["w"] > box[0] + 0.05],
            "his_box": his_box(rs) if len(rs) >= 3 else None,
            "his_box_own_aspect": his_box(rs, "pro_aspect") if len(rs) >= 3 else None,
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    a = ap.parse_args(argv)
    rows = designs(a.registry)
    summary = census(rows)
    for r in sorted(rows, key=lambda r: (str(r["garment"]), r["slug"])):
        flag = f"  same as {r['same_as']}" if r["same_as"] else ""
        today = r.get("today")
        print(f"{str(r['garment']):10s} {r['slug'][:30]:30s} pro {r['w']:6.1f} x {r['h']:5.1f}"
              f"  art {r['art_aspect'] or '(pro)'!s:>6s}"
              + (f"  today {today[0]:6.1f} x {today[1]:5.1f} ({r['today_ratio']:.2f})" if today else "")
              + flag)
    for g, s in summary.items():
        print(f"\n{g}: n={s['n']} today box {s['today_box']}  pro w {s['w_range']} h {s['h_range']}")
        print(f"  taller than today's box: {s['taller_than_today']}")
        print(f"  wider than today's box:  {s['wider_than_today']}")
        if s["his_box"]:
            b, o = s["his_box"], s["his_box_own_aspect"]
            print(f"  his box for our artwork {b['w']} x {b['h']} mm: median width error "
                  f"{b['median_err']:.3f}, worst {b['worst_err']:.3f}; misses > {MISS_TOL:.0%}: {b['misses']}")
            print(f"  (on his designs' own aspect: {o['w']} x {o['h']} mm, median {o['median_err']:.3f})")
    if a.json:
        a.json.write_text(json.dumps({"rows": rows, "garments": summary}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
