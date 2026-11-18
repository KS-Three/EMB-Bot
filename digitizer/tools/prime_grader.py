"""The prime grader: a Claude session's eye as the standing yardstick.

    python -m tools.prime_grader capture   --out RUN [--only SLUG ...]
    python -m tools.prime_grader kit       --run RUN --out KIT
    python -m tools.prime_grader record    --kit KIT --verdict FILE.json
    python -m tools.prime_grader scorecard --kit KIT --out DIR [--prev PREV.json] [--date D]
    python -m tools.prime_grader kent      --kit KIT --marks MARKS.json [...] [--json OUT]

Why it exists (Kent, 2026-11-17: "When I ask claude to grade the image it is
almost SPOT ON ... we need the yardstick to match"). No computed yardstick has
held up against his eye (`docs/lagging-areas-2026-11-06/1-yardstick.md`); an
agent eye with the original beside the render read linear kappa 0.66 against
his grades on 2026-11-13 and found his gross faults at his spot 0.35 above
chance, weakest on jagged edges and pen flow, which a whole-design picture is
too small to show. This tool makes that eye a repeatable instrument and gives
it a magnifier:

* `capture` digitizes one job per pro-paired artwork whose art and pro file
  are both in the repo (`population()`), through `defect_marks.capture_pro`.
* `kit` writes, per design, an overview (original | ours | pro), magnifier
  tiles at `ZOOM_PXMM` (the original's patch beside ours, with a mm ruler) and
  a travel picture, plus `kit.json`. The computed yardstick's reading goes in
  `_sealed.json`, which the grader must not open.
* The grading itself is done by a Claude session reading the pictures under
  `prime_grader_rubric.md` (pinned by `RUBRIC_SHA256`). `record` validates one
  design's verdict and stores it in `readings.json`.
* `scorecard` rolls the readings up and says what moved since `--prev`.
* `kent` scores the readings against Kent's defect-marks sittings: grade
  agreement as linear-weighted kappa, and his gross pins found within
  `RADIUS_MM`, each beside its chance figure (ROADMAP gate 4).

Every figure this prints is an instrument reading. It flips no flag and makes
no quality claim; picking between two close variants stays Kent's. The kit
folder holds client artwork and renders of pro files: keep it gitignored
(`eye_pairs_out/`). The scorecard is text only and may be committed.

Pure helpers (`tile_grid`, `clean_verdict`, `rollup`, `movement`,
`weighted_kappa`, `pin_rows`) take plain data, so the tests need no engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.defect_marks import GRADES, PAD_MM, PRO_SLUGS, PXMM, SEVERITIES, WHATS, WHOLE  # noqa: E402

RUBRIC = Path(__file__).with_name("prime_grader_rubric.md")
RUBRIC_VERSION = "2026-11-18"
RUBRIC_SHA256 = "9a169b10624376fc30dc5fa515bb347826565c2fc463855a9fd9b8f8dd2bd2ec"
#: How the kit's renders end a stitch. "butt" draws a satin column's edge as the
#: envelope it sews (flat ends at the thread width); the default "round" draw is
#: round-capped strokes, which scallop a column edge into bumps that a blind
#: reader called "saw-toothed on every edge" (#1648, 2026-11-18). Kit-only:
#: `stitchviz.render_design(caps=)` leaves every other render round.
KIT_CAPS = "butt"
ZOOM_PXMM = 30.0          # the magnifier's scale; the overview is PXMM (12)
TILE_MM = 32.0            # target tile side
MAX_TILES = 9
MAX_FAULTS = 40
GROSS = ("ruins", "noticeable")
RADIUS_MM = 3.0           # the fault-reader harness's pre-registered radius
BOOT_DRAWS = 5000
SEED = 20261117
SENTINEL_BGR = (255, 0, 255)

#: Kent's pin kinds folded into the classes the 2026-11-13 agent-eye report
#: used, so "same kind of fault" has one meaning here.
CLASS_OF = {"jagged": "edge", "wavy": "edge", "lumpy_curve": "edge",
            "pen_flow": "pen_flow", "direction": "pen_flow",
            "letter_shape": "letter", "mushed": "letter",
            "missing": "missing", "extra": "extra", "colour": "colour", "gap": "gap",
            "blob": "artefact", "stray": "artefact", "stitch_type": "stitch_type", "other": "other"}


def rubric_sha() -> str:
    return hashlib.sha256(RUBRIC.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def population() -> list[str]:
    """One job per artwork (`defect_marks.PRO_SLUGS`) whose art and pro file
    are both committed (`tripwire.committed_jobs`), so a cloud session with a
    fresh clone can run it."""
    from tools.tripwire import committed_jobs
    have = set(committed_jobs())
    return [s for s in PRO_SLUGS if s in have]


# ------------------------------------------------------------ pure helpers ----

def tile_grid(w_mm: float, h_mm: float, tile_mm: float = TILE_MM, max_tiles: int = MAX_TILES) -> list[dict]:
    """Rows x columns of equal tiles covering w x h, as near `tile_mm` square
    as the count cap allows. Names are row letter + column number (A1 top-left)."""
    cols = max(1, math.ceil(w_mm / tile_mm))
    rows = max(1, math.ceil(h_mm / tile_mm))
    while cols * rows > max_tiles:
        if w_mm / cols <= h_mm / rows and rows > 1:
            rows -= 1
        elif cols > 1:
            cols -= 1
        else:
            rows -= 1
    tw, th = w_mm / cols, h_mm / rows
    return [{"name": f"{chr(65 + r)}{c + 1}", "x0": round(c * tw, 2), "y0": round(r * th, 2),
             "x1": round((c + 1) * tw, 2), "y1": round((r + 1) * th, 2)}
            for r in range(rows) for c in range(cols)]


def clean_verdict(body: dict, item: dict) -> dict:
    """One design's verdict as the grader wrote it -> the record `readings.json`
    keeps. Raises ValueError naming the first thing outside the rubric."""
    if body.get("item") != item["id"]:
        raise ValueError(f"item: {body.get('item')!r} is not {item['id']!r}")
    grade = body.get("grade")
    if grade not in GRADES:
        raise ValueError(f"grade: {grade!r} is not one of {GRADES}")
    whole = body.get("whole") or []
    if not isinstance(whole, list) or any(w not in WHOLE for w in whole):
        raise ValueError(f"whole: {whole!r}")
    reason = str(body.get("reason") or "").strip()
    if not reason:
        raise ValueError("reason: empty")
    tiles = [t["name"] for t in item["tiles"]]
    unread = [t for t in tiles if t not in (body.get("tiles_read") or [])]
    if unread:
        raise ValueError(f"tiles_read: missing {unread}")
    places = {"overview", "travel", *tiles}
    faults = []
    for n, f in enumerate(body.get("faults") or []):
        try:
            x, y = float(f["x_mm"]), float(f["y_mm"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"fault {n}: x_mm / y_mm") from None
        if not (-PAD_MM <= x <= item["w_mm"] + PAD_MM and -PAD_MM <= y <= item["h_mm"] + PAD_MM):
            raise ValueError(f"fault {n}: ({x}, {y}) is off the design ({item['w_mm']} x {item['h_mm']} mm)")
        if f.get("what") not in WHATS:
            raise ValueError(f"fault {n}: what {f.get('what')!r}")
        if f.get("severity") not in SEVERITIES:
            raise ValueError(f"fault {n}: severity {f.get('severity')!r}")
        note = str(f.get("note") or "").strip()
        if not note:
            raise ValueError(f"fault {n}: note is empty")
        if f.get("seen_in") not in places:
            raise ValueError(f"fault {n}: seen_in {f.get('seen_in')!r}")
        faults.append({"x_mm": round(x, 2), "y_mm": round(y, 2), "what": f["what"], "severity": f["severity"],
                       "note": note[:300], "seen_in": f["seen_in"]})
    if len(faults) > MAX_FAULTS:
        raise ValueError("too many faults")
    return {"grade": grade, "whole": list(whole), "reason": reason[:600], "faults": faults}


def rollup(kit: dict, readings: dict) -> dict:
    """Per design: grade and gross faults by class. Over the set: the grade
    spread and, per class, how many designs carry a gross fault of it."""
    rows, classes, grades = [], {}, {g: 0 for g in GRADES}
    for it in kit["items"]:
        rec = (readings.get("items") or {}).get(it["id"])
        if not rec:
            continue
        by: dict[str, int] = {}
        for f in rec["faults"]:
            if f["severity"] in GROSS:
                c = CLASS_OF[f["what"]]
                by[c] = by.get(c, 0) + 1
        for c in by:
            classes.setdefault(c, []).append(it["id"])
        grades[rec["grade"]] += 1
        rows.append({"id": it["id"], "size": it["size"], "grade": rec["grade"],
                     "step": GRADES.index(rec["grade"]), "whole": rec["whole"],
                     "ruins": sum(f["severity"] == "ruins" for f in rec["faults"]),
                     "noticeable": sum(f["severity"] == "noticeable" for f in rec["faults"]),
                     "nitpick": sum(f["severity"] == "nitpick" for f in rec["faults"]),
                     "gross_by_class": dict(sorted(by.items())), "reason": rec["reason"]})
    steps = [r["step"] for r in rows]
    return {"designs": len(rows), "grades": grades,
            "mean_step": round(sum(steps) / len(steps), 2) if steps else None,
            "classes": {c: sorted(v) for c, v in sorted(classes.items(), key=lambda kv: (-len(kv[1]), kv[0]))},
            "rows": rows}


def movement(now: dict, prev: dict | None) -> list[dict]:
    """Designs whose grade or gross-fault classes differ from `prev` (an
    earlier scorecard json). `better` is by grade only."""
    if not prev:
        return []
    old = {r["id"]: r for r in (prev.get("rollup") or {}).get("rows") or []}
    out = []
    for r in now["rows"]:
        o = old.get(r["id"])
        if o is None:
            out.append({"id": r["id"], "new": True, "grade": r["grade"]})
            continue
        gained = sorted(set(r["gross_by_class"]) - set(o["gross_by_class"]))
        cleared = sorted(set(o["gross_by_class"]) - set(r["gross_by_class"]))
        if r["step"] != o["step"] or gained or cleared:
            out.append({"id": r["id"], "was": o["grade"], "grade": r["grade"], "steps": r["step"] - o["step"],
                        "gained": gained, "cleared": cleared})
    return out


def weighted_kappa(a: list[int], b: list[int], k: int = len(GRADES)) -> float | None:
    """Linear-weighted Cohen's kappa of two ratings on 0..k-1. None when chance
    disagreement is 0 (both raters constant and equal)."""
    n = len(a)
    if not n or n != len(b):
        return None
    w = lambda i, j: abs(i - j) / (k - 1)           # noqa: E731
    obs = sum(w(i, j) for i, j in zip(a, b)) / n
    pa = [a.count(i) / n for i in range(k)]
    pb = [b.count(i) / n for i in range(k)]
    exp = sum(pa[i] * pb[j] * w(i, j) for i in range(k) for j in range(k))
    return None if exp == 0 else round(1 - obs / exp, 4)


def kappa_ci(a: list[int], b: list[int], boots: int = BOOT_DRAWS, seed: int = SEED) -> list | None:
    """95% bootstrap over designs."""
    import numpy as np
    if len(a) < 3:
        return None
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(boots):
        ix = rng.integers(0, len(a), len(a))
        v = weighted_kappa([a[i] for i in ix], [b[i] for i in ix])
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def pin_rows(pins: list[dict], faults: list[dict], radius: float = RADIUS_MM) -> list[dict]:
    """Per pin of Kent's: is one of the grader's faults within `radius` mm,
    and is one of the SAME class (`CLASS_OF`) within it."""
    out = []
    for p in pins:
        near = [f for f in faults if math.hypot(f["x_mm"] - p["x_mm"], f["y_mm"] - p["y_mm"]) <= radius]
        cls = CLASS_OF.get(p.get("what") or "other", "other")
        out.append({"class": cls, "severity": p.get("severity"), "hit": bool(near),
                    "hit_class": any(CLASS_OF[f["what"]] == cls for f in near)})
    return out


# ----------------------------------------------------------------- capture ----

def cmd_capture(a) -> int:
    from tools import defect_marks as dm
    from tools.tripwire import materialise
    slugs = a.only or population()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    materialise(out / "_kent", slugs)
    return dm.capture_pro(out, ROOT, slugs)


# --------------------------------------------------------------------- kit ----

def _load_art(src: Path, fabric_bgr):
    import cv2
    import numpy as np
    from tools.photo_corpus import load_photo
    img = load_photo(src, fabric_bgr)
    if img is None:                                   # webp / gif cv2 cannot read
        from PIL import Image
        rgba = np.array(Image.open(src).convert("RGBA")).astype(np.float32)
        al = rgba[:, :, 3:4] / 255.0
        rgb = rgba[:, :, :3] * al + np.array(fabric_bgr[::-1], np.float32) * (1 - al)
        img = cv2.cvtColor(rgb.round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return img


def _ink_mask(art):
    """Pixels that differ from the art's own background (the median of its
    border). Good for a logo on a plain ground; a photo reads as all ink."""
    import numpy as np
    b = np.concatenate([art[0], art[-1], art[:, 0], art[:, -1]]).astype(np.int32)
    bg = np.median(b, axis=0)
    return np.abs(art.astype(np.int32) - bg).sum(-1) > 60


def register(art, thread_mask, mask_pxmm: float) -> dict:
    """Fit art pixels -> design mm (uniform scale + shift): mm = s * px + t.
    Starts from ink bbox onto thread bbox, then tries nearby scales and shifts
    and keeps the best overlap, so one dropped edge element does not skew the
    whole fit. `fit` = that overlap (IoU); under ~0.3 treat the tile's
    left-hand patch as a rough guide only."""
    import cv2
    import numpy as np
    # silhouettes on both sides (holes filled): a white fill is thread in the
    # render and "background" in the art, and must not pull the fit about
    def solid(m):
        cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = np.zeros(m.shape, np.uint8)
        cv2.drawContours(out, cs, -1, 1, -1)
        return out > 0
    ink = solid(_ink_mask(art))
    thread_mask = solid(thread_mask)
    H, W = thread_mask.shape
    ys, xs = np.nonzero(ink)
    ty_, tx_ = np.nonzero(thread_mask)
    if not len(xs) or not len(tx_) or ink.mean() > 0.9:
        s = (W / mask_pxmm - 2 * PAD_MM) / art.shape[1]
        return {"s": s, "tx": 0.0, "ty": 0.0, "fit": None}
    ix0, ix1, iy0, iy1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    mx0, mx1, my0, my1 = tx_.min(), tx_.max() + 1, ty_.min(), ty_.max() + 1
    s0 = ((mx1 - mx0) / (ix1 - ix0) + (my1 - my0) / (iy1 - iy0)) / 2.0        # mask px per art px
    k = min(1.0, 220.0 / max(H, W))                                          # work small
    small = cv2.resize(thread_mask.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA) > 0
    h, w = small.shape
    best = (-1.0, s0, 0.0, 0.0)
    icx, icy = (ix0 + ix1) / 2.0, (iy0 + iy1) / 2.0
    mcx, mcy = (mx0 + mx1) / 2.0, (my0 + my1) / 2.0
    ink8 = ink.astype(np.uint8)
    for ds in (0.90, 0.94, 0.97, 1.0, 1.03, 1.06, 1.10):
        s = s0 * ds
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                ox = mcx - s * icx + dx * 0.02 * W
                oy = mcy - s * icy + dy * 0.02 * H
                M = np.array([[s * k, 0, ox * k], [0, s * k, oy * k]], np.float64)
                warped = cv2.warpAffine(ink8, M, (w, h), flags=cv2.INTER_NEAREST) > 0
                union = (warped | small).sum()
                iou = float((warped & small).sum()) / union if union else 0.0
                if iou > best[0]:
                    best = (iou, s, ox, oy)
    iou, s, ox, oy = best
    return {"s": s / mask_pxmm, "tx": ox / mask_pxmm - PAD_MM, "ty": oy / mask_pxmm - PAD_MM,
            "fit": round(iou, 3)}


def _label(img, text: str, scale: float = 0.6):
    import cv2
    import numpy as np
    bar = np.full((28, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, scale, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _ruler(img, x0_mm: float, y0_mm: float, pxmm: float, step: float):
    """White margins on the top and left with a tick and a number every `step` mm."""
    import cv2
    import numpy as np
    m = 34
    h, w = img.shape[:2]
    out = np.full((h + m, w + m, 3), 255, np.uint8)
    out[m:, m:] = img
    v = math.ceil(x0_mm / step) * step
    while (v - x0_mm) * pxmm < w:
        x = int(m + (v - x0_mm) * pxmm)
        cv2.line(out, (x, m - 8), (x, m), (0, 0, 0), 1)
        cv2.putText(out, f"{v:g}", (x - 8, m - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
        v += step
    v = math.ceil(y0_mm / step) * step
    while (v - y0_mm) * pxmm < h:
        y = int(m + (v - y0_mm) * pxmm)
        cv2.line(out, (m - 8, y), (m, y), (0, 0, 0), 1)
        cv2.putText(out, f"{v:g}", (1, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
        v += step
    return out


def _fit_h(img, h: int):
    import cv2
    s = h / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), h),
                      interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def _hstack(parts, gap: int = 14):
    import numpy as np
    h = max(p.shape[0] for p in parts)
    cols = []
    for n, p in enumerate(parts):
        if p.shape[0] < h:
            p = np.vstack([p, np.full((h - p.shape[0], p.shape[1], 3), 255, np.uint8)])
        cols.append(p)
        if n < len(parts) - 1:
            cols.append(np.full((h, gap, 3), 255, np.uint8))
    return np.hstack(cols)


def travel_picture(design: dict, fabric_bgr, pxmm: float = PXMM, caps: str = KIT_CAPS):
    """The render dimmed, every needle-up move (jump / trim, over 1 mm) in
    magenta, each colour block numbered where it starts."""
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    base = stitchviz.render_design(design, px_per_mm=pxmm, fabric_bgr=fabric_bgr, pad_mm=PAD_MM, caps=caps)
    img = (base.astype(np.float32) * 0.45 + 255 * 0.55).astype(np.uint8)
    frame = stitchviz._frame(design.get("stitches") or [], pxmm, PAD_MM)
    if frame is None:
        return img
    _hw, to_px = frame
    last, broke, block, starts = None, False, 1, []
    need_start = True
    for s in design["stitches"]:
        kind = s.get("type")
        if kind == "color":
            block += 1
            need_start, broke = True, True
            continue
        if kind in ("jump", "trim"):
            broke = True
            continue
        if kind != "stitch":
            continue
        p = to_px(s)
        if need_start:
            starts.append((block, p))
            need_start = False
        if broke and last is not None and math.hypot(p[0] - last[0], p[1] - last[1]) > pxmm:
            cv2.line(img, last, p, (255, 0, 255), 2, cv2.LINE_AA)
        broke, last = False, p
    for n, p in starts:
        cv2.circle(img, p, 11, (255, 255, 255), -1)
        cv2.circle(img, p, 11, (0, 0, 0), 1)
        cv2.putText(img, str(n), (p[0] - (5 if n < 10 else 9), p[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (0, 0, 0), 1, cv2.LINE_AA)
    return img


def build_item(slug: str, output: dict, img_dir: Path, caps: str = KIT_CAPS) -> tuple[dict, dict]:
    """Write one design's pictures. -> (kit item, sealed yardstick reading)."""
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from tools import defect_marks as dm
    from tools import pro_baseline as pb
    from tools.eye_pairs.filearm import design_from_file
    iid = f"L_{slug}"
    _g, _w, art_spec, pro_dst, pro_pes, _wj = pb.JOBS[slug]
    cfg = (output.get("_meta") or {}).get("config_sent") or {}
    fabric = tuple(reversed(cfg.get("garment_rgb") or [235, 232, 223]))
    design = output["design"]
    x0, x1, y0, y1 = stitchviz._bounds(design["stitches"])
    w_mm, h_mm = (x1 - x0) / 10.0, (y1 - y0) / 10.0
    art = _load_art(pb.resolve(art_spec), fabric)

    render = stitchviz.render_design(design, px_per_mm=PXMM, fabric_bgr=fabric, pad_mm=PAD_MM, caps=caps)
    bare = stitchviz.render_design(design, px_per_mm=PXMM, fabric_bgr=SENTINEL_BGR, pad_mm=PAD_MM, lit=False)
    thread = np.abs(bare.astype(np.int32) - np.array(SENTINEL_BGR)).sum(-1) > 90
    reg = register(art, thread, PXMM)

    panel_h = min(900, max(360, render.shape[0]))
    parts = [_label(_fit_h(art, panel_h), "ORIGINAL"),
             _label(_fit_h(_ruler(render, -PAD_MM, -PAD_MM, PXMM, 10.0), panel_h), "OURS (ruler in design mm)")]
    pro_src = next((p for p in (pro_pes, pro_dst) if p and pb.resolve(p).exists()), None)
    if pro_src:
        pro = stitchviz.render_design(design_from_file(pb.resolve(pro_src)), px_per_mm=PXMM, fabric_bgr=fabric,
                                      pad_mm=PAD_MM, caps=caps)
        parts.append(_label(_fit_h(pro, panel_h), "PROFESSIONAL'S FILE" + ("" if pro_src == pro_pes
                                                                          else " (no thread colours)")))
    cv2.imwrite(str(img_dir / f"{iid}_overview.png"), _hstack(parts))
    cv2.imwrite(str(img_dir / f"{iid}_travel.png"),
                _label(_ruler(travel_picture(design, fabric, caps=caps), -PAD_MM, -PAD_MM, PXMM, 10.0),
                       "TRAVEL: magenta = needle-up move, numbers = colour blocks in sewing order"))

    zoom = stitchviz.render_design(design, px_per_mm=ZOOM_PXMM, fabric_bgr=fabric, pad_mm=PAD_MM, caps=caps)
    tiles = []
    for t in tile_grid(w_mm, h_mm):
        mx0, my0 = t["x0"] - 1.0, t["y0"] - 1.0                      # 1 mm of context round the tile
        tw = int((t["x1"] - t["x0"] + 2.0) * ZOOM_PXMM)
        th = int((t["y1"] - t["y0"] + 2.0) * ZOOM_PXMM)
        px, py = int((mx0 + PAD_MM) * ZOOM_PXMM), int((my0 + PAD_MM) * ZOOM_PXMM)
        ours = zoom[py:py + th, px:px + tw]
        if ours.shape[0] < th or ours.shape[1] < tw:
            pad = np.full((th, tw, 3), fabric, np.uint8)
            pad[:ours.shape[0], :ours.shape[1]] = ours
            ours = pad
        tm = thread[int((my0 + PAD_MM) * PXMM):int((t["y1"] + 1 + PAD_MM) * PXMM),
                    int((mx0 + PAD_MM) * PXMM):int((t["x1"] + 1 + PAD_MM) * PXMM)]
        k = reg["s"] * ZOOM_PXMM                                       # art px -> tile px
        M = np.array([[k, 0, (reg["tx"] - mx0) * ZOOM_PXMM], [0, k, (reg["ty"] - my0) * ZOOM_PXMM]], np.float64)
        orig = cv2.warpAffine(art, M, (tw, th), flags=cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA,
                              borderValue=tuple(int(c) for c in fabric))
        if tm.size and tm.mean() < 0.005 and _ink_mask(np.vstack([orig, np.full((1, tw, 3), fabric, np.uint8)]))[:-1].mean() < 0.005:
            continue                                                   # nothing sewn, nothing drawn
        pic = _hstack([_label(orig, "ORIGINAL, same patch (placed by fit)"),
                       _label(_ruler(ours, mx0, my0, ZOOM_PXMM, 5.0), f"OURS, tile {t['name']} (mm)")])
        cv2.imwrite(str(img_dir / f"{iid}_tile_{t['name']}.png"), pic)
        tiles.append({**t, "file": f"{iid}_tile_{t['name']}.png"})
    item = {"id": iid, "slug": slug, "w_mm": round(w_mm, 1), "h_mm": round(h_mm, 1),
            "size": f"{round(w_mm, 1)} x {round(h_mm, 1)} mm on {cfg.get('garment_id', '?')}",
            "overview": f"{iid}_overview.png", "travel": f"{iid}_travel.png", "has_pro": bool(pro_src),
            "tiles": tiles, "art_fit": reg["fit"], "tree_sha": (output.get("_meta") or {}).get("tree_sha"),
            "render_px": [int(render.shape[1]), int(render.shape[0])]}
    cv2.imwrite(str(img_dir / f"{iid}_thread.png"), thread.astype(np.uint8) * 255)
    return item, dm._yardstick(output)


def cmd_kit(a) -> int:
    from tools.tripwire import materialise
    run, out = Path(a.run), Path(a.out)
    (out / "img").mkdir(parents=True, exist_ok=True)
    slugs = [s for s in population() if (run / f"{s}.json").exists()]
    materialise(run / "_kent", slugs)
    items, sealed, skipped = [], {}, []
    for slug in slugs:
        output = json.loads((run / f"{slug}.json").read_text(encoding="utf-8"))
        if output.get("state") != "done":
            skipped.append({"slug": slug, "state": output.get("state")})
            continue
        it, y = build_item(slug, output, out / "img", a.caps)
        items.append(it)
        sealed[it["id"]] = y
        print(it["id"], it["size"], f"{len(it['tiles'])} tiles", f"art fit {it['art_fit']}", flush=True)
    body = {"schema": 1, "rubric_version": RUBRIC_VERSION, "rubric_sha256": rubric_sha(), "items": items,
            "skipped": skipped, "caps": a.caps, "pxmm": PXMM, "zoom_pxmm": ZOOM_PXMM, "pad_mm": PAD_MM}
    body["kit_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    _dump(body, out / "kit.json")
    _dump(sealed, out / "_sealed.json")
    print(f"{len(items)} designs, {sum(len(i['tiles']) for i in items)} tiles -> {out}")
    return 1 if skipped else 0


# ------------------------------------------------------------------ record ----

def _dump(obj, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_record(a) -> int:
    kit_dir = Path(a.kit)
    kit = _load(kit_dir / "kit.json")
    if kit["rubric_sha256"] != RUBRIC_SHA256 or rubric_sha() != RUBRIC_SHA256:
        print("the rubric is not the pinned one; a changed rubric is a new dated version", file=sys.stderr)
        return 2
    body = _load(a.verdict)
    item = next((i for i in kit["items"] if i["id"] == body.get("item")), None)
    if item is None:
        print(f"no item {body.get('item')!r} in this kit", file=sys.stderr)
        return 2
    path = kit_dir / "readings.json"
    readings = _load(path) if path.exists() else {"kit_sha256": kit["kit_sha256"],
                                                  "rubric_sha256": kit["rubric_sha256"], "items": {}}
    if a.check:
        try:
            clean_verdict(body, item)
        except ValueError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(f"{item['id']}: the verdict is well formed (not recorded)")
        return 0
    if item["id"] in readings["items"] and not a.replace:
        print(f"{item['id']} is already recorded (the rubric: do not go back)", file=sys.stderr)
        return 2
    try:
        readings["items"][item["id"]] = clean_verdict(body, item)
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    _dump(readings, path)
    left = [i["id"] for i in kit["items"] if i["id"] not in readings["items"]]
    print(f"recorded {item['id']}; {len(left)} left" + (f": {', '.join(left)}" if left else ""))
    return 0


# --------------------------------------------------------------- scorecard ----

def scorecard_markdown(card: dict) -> str:
    ru = card["rollup"]
    L = [f"# Prime grader scorecard, {card['date']}", "",
         f"A Claude session graded {ru['designs']} designs by eye against the original artwork, under rubric "
         f"{card['rubric_version']} (`{card['rubric_sha256'][:12]}`), on tree `{(card.get('tree_sha') or '?')[:8]}`. "
         "Each figure is an instrument reading, not a quality claim (ROADMAP gate 4). The grader's repeat "
         "agreement with itself is not measured yet, so a one-step move on one night is not evidence by itself.", "",
         "## Grades", "",
         "| " + " | ".join(GRADES) + " | mean step (0 = Great, 4 = Terrible) |", "|" + "---|" * (len(GRADES) + 1),
         "| " + " | ".join(str(ru["grades"][g]) for g in GRADES) + f" | {ru['mean_step']} |", "",
         "## Designs", "",
         "| design | size | grade | computed yardstick | ruins | noticeable | nitpick | gross fault classes | whole-design |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in ru["rows"]:
        y = (card.get("yardstick") or {}).get(r["id"]) or {}
        ys = f"{y.get('grade')} {y.get('score')}" if y.get("grade") else "-"
        L.append(f"| `{r['id']}` | {r['size']} | {r['grade']} | {ys} | {r['ruins']} | {r['noticeable']} | "
                 f"{r['nitpick']} | {', '.join(f'{c} {n}' for c, n in r['gross_by_class'].items()) or '-'} | "
                 f"{', '.join(r['whole']) or '-'} |")
    L += ["", "## Gross faults by class (designs affected)", ""]
    L += [f"- **{c}**: {len(ids)} of {ru['designs']} ({', '.join(f'`{i}`' for i in ids)})"
          for c, ids in ru["classes"].items()] or ["- none"]
    L += ["", "## Since the last scorecard", ""]
    pr = card.get("prev_rubric_version")
    if card.get("prev_date") is None:
        L.append("No earlier scorecard was given.")
    elif pr and pr != card["rubric_version"]:
        L.append(f"**Not comparable.** This is the first card under rubric {card['rubric_version']}; "
                 f"{card['prev_date']} was read under {pr} (and the kit's renders changed with it), so no move "
                 "is listed. Read this card as a new baseline.")
    elif not card["movement"]:
        L.append(f"Nothing moved against {card['prev_date']}.")
    else:
        L.append(f"Against {card['prev_date']} (tree `{(card.get('prev_tree_sha') or '?')[:8]}`):")
        for m in card["movement"]:
            if m.get("new"):
                L.append(f"- `{m['id']}`: new, {m['grade']}")
            else:
                bits = [f"{m['was']} -> {m['grade']}"] if m["steps"] else [f"still {m['grade']}"]
                if m["gained"]:
                    bits.append("gained " + ", ".join(m["gained"]))
                if m["cleared"]:
                    bits.append("cleared " + ", ".join(m["cleared"]))
                L.append(f"- `{m['id']}`: " + "; ".join(bits))
    L += ["", "## Why each grade", ""]
    L += [f"- `{r['id']}` ({r['grade']}): {r['reason']}" for r in ru["rows"]]
    L += ["", "## Every fault", ""]
    for it_id, rec in card["readings"].items():
        if rec["faults"]:
            L.append(f"**`{it_id}`**")
            L += [f"- ({f['x_mm']}, {f['y_mm']}) mm, {f['what']}, {f['severity']}, seen in {f['seen_in']}: {f['note']}"
                  for f in rec["faults"]]
            L.append("")
    return "\n".join(L).rstrip() + "\n"


def cmd_scorecard(a) -> int:
    kit_dir, out = Path(a.kit), Path(a.out)
    kit, readings = _load(kit_dir / "kit.json"), _load(kit_dir / "readings.json")
    missing = [i["id"] for i in kit["items"] if i["id"] not in readings["items"]]
    if missing and not a.partial:
        print(f"not recorded yet: {', '.join(missing)} (--partial to write anyway)", file=sys.stderr)
        return 2
    prev = _load(a.prev) if a.prev else None
    ru = rollup(kit, readings)
    date = a.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sealed = kit_dir / "_sealed.json"
    ys = {k: {"grade": v.get("grade"), "score": v.get("score")} for k, v in _load(sealed).items()} \
        if sealed.exists() else {}
    card = {"schema": 1, "date": date, "rubric_version": kit["rubric_version"],
            "rubric_sha256": kit["rubric_sha256"], "kit_sha256": kit["kit_sha256"],
            "tree_sha": next((i["tree_sha"] for i in kit["items"] if i.get("tree_sha")), None),
            "rollup": ru, "yardstick": ys, "readings": readings["items"],
            "prev_date": (prev or {}).get("date"), "prev_tree_sha": (prev or {}).get("tree_sha"),
            "prev_rubric_version": (prev or {}).get("rubric_version"),
            "movement": movement(ru, prev), "not_recorded": missing}
    out.mkdir(parents=True, exist_ok=True)
    _dump(card, out / f"scorecard-{date}.json")
    _dump(card, out / "latest.json")
    (out / f"scorecard-{date}.md").write_text(scorecard_markdown(card), encoding="utf-8")
    print(out / f"scorecard-{date}.md")
    return 0


# -------------------------------------------------------------------- kent ----

def cmd_kent(a) -> int:
    """Readings against Kent's sittings. His marks were made on OLDER trees'
    renders, so a fault a later change cured scores as a miss for him and an
    extra for the grader; the report says which trees."""
    import cv2
    from tools.fault_reader_harness import chance_rate
    kit_dir = Path(a.kit)
    kit, readings = _load(kit_dir / "kit.json"), _load(kit_dir / "readings.json")
    kent: dict[str, dict] = {}
    for mp in a.marks:                                 # a later sitting replaces an earlier one's item
        for iid, rec in (_load(mp).get("items") or {}).items():
            if rec.get("grade") or rec.get("pins"):
                kent[iid] = rec
    ga, gb, rows = [], [], []
    per_class: dict[str, dict] = {}
    tot = {"n": 0, "hit": 0, "hit_class": 0, "chance": 0.0}
    for it in kit["items"]:
        rec, k = readings["items"].get(it["id"]), kent.get(it["id"])
        if not rec or not k:
            continue
        if k.get("grade"):
            ga.append(GRADES.index(rec["grade"]))
            gb.append(GRADES.index(k["grade"]))
        pins = [p for p in k.get("pins") or [] if p.get("severity") in GROSS]
        pr = pin_rows(pins, rec["faults"])
        mask = cv2.imread(str(kit_dir / "img" / f"{it['id']}_thread.png"), cv2.IMREAD_GRAYSCALE) > 0
        ch = chance_rate(rec["faults"] and [{"x_mm": f["x_mm"], "y_mm": f["y_mm"]} for f in rec["faults"]],
                         mask, len(pins), PXMM, PAD_MM) if pins and rec["faults"] else 0.0
        for r in pr:
            c = per_class.setdefault(r["class"], {"n": 0, "hit": 0, "hit_class": 0})
            c["n"] += 1
            c["hit"] += r["hit"]
            c["hit_class"] += r["hit_class"]
        tot["n"] += len(pins)
        tot["hit"] += sum(r["hit"] for r in pr)
        tot["hit_class"] += sum(r["hit_class"] for r in pr)
        tot["chance"] += ch * len(pins)
        rows.append({"id": it["id"], "grader": rec["grade"], "kent": k.get("grade"), "gross_pins": len(pins),
                     "hit": sum(r["hit"] for r in pr), "hit_class": sum(r["hit_class"] for r in pr),
                     "chance": round(ch, 3), "grader_faults": len(rec["faults"])})
    n = tot["n"]
    hr, cr = (tot["hit"] / n, tot["chance"] / n) if n else (None, None)
    res = {"designs": len(rows), "grade_n": len(ga), "grade_kappa_linear": weighted_kappa(ga, gb),
           "grade_kappa_ci95": kappa_ci(ga, gb), "gross_pins": n, "hit_rate": hr and round(hr, 4),
           "chance": cr and round(cr, 4),
           "above_chance": round((hr - cr) / (1 - cr), 4) if n and cr < 1 else None,
           "hit_same_class": tot["hit_class"], "by_class": dict(sorted(per_class.items())), "rows": rows,
           "radius_mm": RADIUS_MM}
    if a.json:
        _dump(res, Path(a.json))
    print(f"designs with both a reading and Kent's marks: {res['designs']}")
    print(f"grade, linear-weighted kappa: {res['grade_kappa_linear']} CI95 {res['grade_kappa_ci95']} (n {res['grade_n']})")
    print(f"Kent's gross pins with a grader fault within {RADIUS_MM} mm: {tot['hit']} of {n}"
          f" (chance {res['chance']}, above chance {res['above_chance']}); same class {tot['hit_class']}")
    for c, v in res["by_class"].items():
        print(f"  {c}: {v['hit']} of {v['n']} at his spot, {v['hit_class']} named as the same class")
    for r in rows:
        print(f"  {r['id']}: grader {r['grader']}, Kent {r['kent']}, pins {r['hit']}/{r['gross_pins']}"
              f" (chance {r['chance']})")
    return 0


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("capture")
    p.add_argument("--out", required=True)
    p.add_argument("--only", nargs="*")
    p = sub.add_parser("kit")
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--caps", choices=("butt", "round"), default=KIT_CAPS,
                   help="stitch ends in the kit's renders (default butt; round is the pre-2026-11-18 look)")
    p = sub.add_parser("record")
    p.add_argument("--kit", required=True)
    p.add_argument("--verdict", required=True)
    p.add_argument("--replace", action="store_true", help="overwrite a recorded design (a malformed first write)")
    p.add_argument("--check", action="store_true", help="validate only; write nothing")
    p = sub.add_parser("scorecard")
    p.add_argument("--kit", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--prev")
    p.add_argument("--date")
    p.add_argument("--partial", action="store_true")
    p = sub.add_parser("kent")
    p.add_argument("--kit", required=True)
    p.add_argument("--marks", nargs="+", required=True)
    p.add_argument("--json")
    a = ap.parse_args(argv)
    return {"capture": cmd_capture, "kit": cmd_kit, "record": cmd_record, "scorecard": cmd_scorecard,
            "kent": cmd_kent}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
