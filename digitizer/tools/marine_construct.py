"""marine_construct: how each letter of MARINE is built, per file, in numbers.

Written 2026-11-18 for `docs/marine-pro-construction-2026-11-18.md`. Reads any
machine file (the pro's DST, or ours written by `digitizer_core.export`) through
`tools.letter_pieces.read` (one reader, one rule, both sides) and adds what that
reader leaves out: cross angle at the start / middle / end of each column, cross
length min / median / max, the overlap between touching columns (mm), thread-free
counter areas, and the underlay runs that come before the satin.

NUMBERS ONLY. This tool draws nothing from a professional's file: the repo is
public and `tests/test_no_new_pro_renders` bars such pictures. Its JSON holds
measurements, never stitch coordinates beyond a column's two end points.

  python -m tools.marine_construct --out DIR [--only SLUG ...] [--no-ours]
      writes DIR/<slug>.json for each Becker placement: {pro, off, on} each
      a list of letters M A R I N E, left to right.

The MARINE row is the bottom line of the Becker logo (`--rows 0.6 1.0`).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import letter_pieces as lp  # noqa: E402

#: the flags that are typed `PipelineConfig` fields (Kent's 2026-11-19 flip); any other `--set NAME=JSON` is `cfg.extra["lettering_columns_NAME"]`
TYPED = ("r_bowl", "block_butt_small", "a_bar", "block_lean")
BECKER = ("becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small", "becker_beanie")
NAMES = "MARINE"
FLAG = "lettering_columns_block_butt"      # a typed field since #1684 (ON on main); "off" arm sets it false
PPM = 24.0
THREAD_MM = 0.4


def _ang(p0, p1) -> float:
    """Cross angle against the line of text, (-90, 90]; 0 = level."""
    a = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) % 180.0
    return a - 180.0 if a > 90.0 else a


def _circ_mean(deg: list[float]) -> float:
    """Mean of axial angles (mod 180) in (-90, 90]."""
    z = sum(complex(math.cos(math.radians(2 * d)), math.sin(math.radians(2 * d))) for d in deg)
    a = math.degrees(math.atan2(z.imag, z.real)) / 2.0
    return a


def _window(vals: list[float], where: str, k: int = 5) -> float:
    if not vals:
        return float("nan")
    if where == "start":
        w = vals[:k]
    elif where == "end":
        w = vals[-k:]
    else:
        m = len(vals) // 2
        w = vals[max(0, m - k // 2): m + k // 2 + 1]
    return round(_circ_mean(w), 1)


def _mask(crosses, bbox, ppm: float):
    import cv2
    x0, y0 = bbox[0] - 1.0, bbox[1] - 1.0
    w = int((bbox[2] - bbox[0] + 2.0) * ppm) + 2
    h = int((bbox[3] - bbox[1] + 2.0) * ppm) + 2
    m = np.zeros((h, w), np.uint8)
    t = max(1, int(round(THREAD_MM * ppm)))
    for a, b in crosses:
        cv2.line(m, (int((a[0] - x0) * ppm), int((a[1] - y0) * ppm)),
                 (int((b[0] - x0) * ppm), int((b[1] - y0) * ppm)), 255, t)
    return m


def _holes(runs, bbox, blocks) -> list[float]:
    """Areas (mm2) of the thread-free pockets inside a letter's bbox: every
    needle-down stitch of the letter's colour block(s), 0.4 mm thread."""
    import cv2
    x0, y0 = bbox[0] - 1.0, bbox[1] - 1.0
    w = int((bbox[2] - bbox[0] + 2.0) * PPM) + 2
    h = int((bbox[3] - bbox[1] + 2.0) * PPM) + 2
    m = np.zeros((h, w), np.uint8)
    t = max(1, int(round(THREAD_MM * PPM)))
    for r in runs:
        if r["block"] not in blocks:
            continue
        pts = r["pts"]
        for a, b in zip(pts, pts[1:]):
            if min(a[0], b[0]) > bbox[2] + 1 or max(a[0], b[0]) < bbox[0] - 1:
                continue
            if min(a[1], b[1]) > bbox[3] + 1 or max(a[1], b[1]) < bbox[1] - 1:
                continue
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 12.0:
                continue      # a travel, not thread on the cloth
            cv2.line(m, (int((a[0] - x0) * PPM), int((a[1] - y0) * PPM)),
                     (int((b[0] - x0) * PPM), int((b[1] - y0) * PPM)), 255, t)
    bg = (m == 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bg, connectivity=4)
    out = []
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        if x == 0 or y == 0 or x + ww >= w or y + hh >= h:
            continue          # touches the frame: open ground, not a counter
        a_mm2 = area / (PPM * PPM)
        if a_mm2 >= 0.5:
            out.append(round(float(a_mm2), 2))
    return sorted(out, reverse=True)


def _underlay(runs, bbox, blocks) -> list[dict]:
    """Runs of the letter's colour block whose centre lies in its bbox, in sewing
    order, each as {kind, n, len, pitch}. kind: `satin` (zigzag at <= 0.35 mm
    pitch), `zigzag` (zigzag, wider pitch), `walk` (a run of stitches)."""
    out = []
    for r in runs:
        if r["block"] not in blocks:
            continue
        p = r["pts"]
        c = p.mean(axis=0)
        if not (bbox[0] - 0.5 <= c[0] <= bbox[2] + 0.5 and bbox[1] - 0.5 <= c[1] <= bbox[3] + 0.5):
            continue
        if len(p) < 4:
            continue
        d = np.diff(p, axis=0)
        ln = np.hypot(d[:, 0], d[:, 1])
        if ln.mean() > 12:
            continue
        ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
        turn = np.abs((ang[1:] - ang[:-1] + 180) % 360 - 180)
        anti = float((turn > 135).mean()) if len(turn) else 0.0
        mids = (p[:-1] + p[1:]) / 2
        adv = np.hypot(*np.diff(mids, axis=0).T) if len(mids) > 1 else np.zeros(1)
        # a zigzag's midpoints alternate sides of the spine: pair them
        adv2 = np.hypot(*(mids[2:] - mids[:-2]).T) / 2 if len(mids) > 2 else adv
        pitch = float(np.median(adv2))
        if anti > 0.6:
            kind = "satin" if pitch <= 0.35 else "zigzag"
        else:
            kind = "walk"
        out.append({"kind": kind, "n": int(len(p)), "len_mm": round(float(ln.sum()), 1),
                    "stitch_mm": round(float(ln.mean()), 2), "pitch_mm": round(pitch, 2),
                    "anti": round(anti, 2)})
    return out


def read_file(path: Path) -> list[dict]:
    """-> the MARINE letters of one machine file, left to right."""
    res = lp.read(Path(path), rows=(0.6, 1.0))
    runs = lp.runs_of(Path(path))
    letters = [L for L in res["letters"] if L["bbox"][3] - L["bbox"][1] >= 5.0]
    letters.sort(key=lambda L: L["bbox"][0])
    out = []
    for i, L in enumerate(letters):
        pcs = L["pieces"]
        cr = L["crosses"]
        by_piece: dict[int, list] = {}
        for c, k in zip(cr, L["piece_of_cross"]):
            by_piece.setdefault(k, []).append(c)
        masks = {}
        pieces = []
        for k, st in enumerate(pcs):
            cs = by_piece.get(k, [])
            ang = [_ang(a, b) for a, b in cs]
            ln = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in cs]
            masks[k] = _mask(cs, L["bbox"], PPM) > 0
            pieces.append({
                "i": k, "order": st["order"], "block": st["block"], "role": st["role"], "n": st["n"],
                "spine_mm": st["spine_mm"], "start": st["start"], "end": st["end"],
                "angle_start": _window(ang, "start"), "angle_mid": _window(ang, "mid"),
                "angle_end": _window(ang, "end"),
                "cross_min": round(min(ln), 2) if ln else None,
                "cross_med": round(float(np.median(ln)), 2) if ln else None,
                "cross_max": round(max(ln), 2) if ln else None,
                "crosses_per_mm": round(1.0 / st["pitch_mid_mm"], 2) if st.get("pitch_mid_mm") else None,
                "axis": st["axis_deg"], "drift": st["drift_deg"], "ends": st.get("ends"),
            })
        overlaps = []
        keys = sorted(masks)
        for a in keys:
            for b in keys:
                if b <= a:
                    continue
                inter = float(np.logical_and(masks[a], masks[b]).sum()) / (PPM * PPM)
                if inter >= 0.05:
                    wid = min((pieces[a]["cross_med"] or 0), (pieces[b]["cross_med"] or 0)) or 1.0
                    overlaps.append({"a": a, "b": b, "area_mm2": round(inter, 2),
                                     "depth_mm": round(inter / wid, 2)})
        blocks = {st["block"] for st in pcs}
        out.append({
            "letter": NAMES[i] if len(letters) == 6 else f"#{i}", "bbox": L["bbox"],
            "height_mm": round(L["bbox"][3] - L["bbox"][1], 2), "width_mm": round(L["bbox"][2] - L["bbox"][0], 2),
            "pieces": pieces, "cuts": L["cuts"], "overlaps": overlaps,
            "holes_mm2": _holes(runs, L["bbox"], blocks), "runs": _underlay(runs, L["bbox"], blocks),
        })
        o = out[-1]
        o["stitches"] = sum(r["n"] for r in o["runs"])
        o["crosses"] = sum(p["n"] for p in pieces)
        o["stitches_per_cross"] = round(o["stitches"] / max(o["crosses"], 1), 2)
    return out


# ------------------------------------------------------------------- inputs
def pro_path(slug: str, kent_root: Path | None) -> Path:
    from tools.pro_baseline import JOBS, resolve
    return Path(resolve(JOBS[slug][3]))


def ours_path(slug: str, extra: dict, out: Path, tag: str) -> Path:
    from digitizer_core.export import write_dst
    from tools import pro_pair
    from tools.pro_baseline import JOBS, resolve
    garment, width, art = JOBS[slug][0], JOBS[slug][1], JOBS[slug][2]
    d = pro_pair.digitize(Path(resolve(art)), float(width), garment, extra)
    dst = out / f"{slug}_{tag}.dst"
    write_dst(d.plan, dst)
    return dst


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-ours", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON",
                    help="an extra.KEY laid over the ON arm (repeatable)")
    a = ap.parse_args(argv)
    from tools import tripwire as tw
    slugs = [s for s in BECKER if not a.only or s in a.only]
    a.out.mkdir(parents=True, exist_ok=True)
    tw.materialise(a.out / "_kent", slugs)
    on_extra = {}
    for item in a.set:
        k, _, v = item.partition("=")
        on_extra[f"lettering_columns_{k}" if k in TYPED else f"extra.lettering_columns_{k}"] = json.loads(v)
    for s in slugs:
        doc = {"slug": s, "pro": read_file(pro_path(s, None))}
        if not a.no_ours:
            doc["off"] = read_file(ours_path(s, {FLAG: False}, a.out, "off"))
            doc["on"] = read_file(ours_path(s, on_extra, a.out, "on"))
        (a.out / f"{s}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(s, {k: len(v) for k, v in doc.items() if isinstance(v, list)}, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------- summary
def brief(L: dict) -> dict:
    """One letter in a few numbers: columns, patches, spans, level share, cross lengths."""
    cols = [p for p in L["pieces"] if p["role"] != "patch"]
    pat = [p for p in L["pieces"] if p["role"] == "patch"]
    meds = [p["cross_med"] for p in cols if p["cross_med"]]
    lo = min((p["cross_min"] for p in cols if p["cross_min"]), default=None)
    hi = max((p["cross_max"] for p in cols if p["cross_max"]), default=None)
    ov = [o["depth_mm"] for o in L["overlaps"] if o["depth_mm"] >= 0.3]
    srt = sorted(cols, key=lambda p: p["order"])
    return {"columns": len(cols), "patches": len(pat),
            "spans": [p["spine_mm"] for p in srt],
            "fan_deg": [round(abs(p["angle_end"] - p["angle_start"]), 0) for p in srt],
            "cross_med": round(float(np.median(meds)), 2) if meds else None, "cross_min": lo, "cross_max": hi,
            "cpm": round(float(np.median([p["crosses_per_mm"] for p in cols if p["crosses_per_mm"]] or [0])), 2),
            "holes": L["holes_mm2"], "st_per_cross": L.get("stitches_per_cross"),
            "overlap_depths": ov, "ends": [e for p in cols for e in (p["ends"] or [])]}


# --------------------------------------------------------------- markdown
def _piece_table(L: dict) -> list[str]:
    rows = ["| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |",
            "|---|---|---|---|---|---|---|"]
    for k, p in enumerate(sorted(L["pieces"], key=lambda p: p["order"])):
        rows.append(f"| {k + 1} | {p['role']} | {p['spine_mm']} | {p['angle_start']} / {p['angle_mid']} / {p['angle_end']} | "
                    f"{p['cross_min']} / {p['cross_med']} / {p['cross_max']} | {p['crosses_per_mm'] or '-'} | "
                    f"{', '.join(p['ends']) if p['ends'] else 'patch'} |")
    return rows


def markdown(doc: dict, arms=("pro", "on"), full: bool = True) -> str:
    out = [f"#### {doc['slug']}", ""]
    for i, name in enumerate(NAMES):
        out.append(f"**{name}**")
        out.append("")
        for arm in arms:
            L = doc[arm][i]
            b = brief(L)
            lab = {"pro": "pro", "off": "ours OFF", "on": "ours ON"}[arm]
            out.append(f"*{lab}*: {b['columns']} columns + {b['patches']} patches; counters {b['holes'] or 'none'} mm2; "
                       f"{b['st_per_cross']} stitches per cross; overlaps >= 0.3 mm: {b['overlap_depths'] or 'none'}")
            out.append("")
            if full:
                out += _piece_table(L)
                out.append("")
    return "\n".join(out)
