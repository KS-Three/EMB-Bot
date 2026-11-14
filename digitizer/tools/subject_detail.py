"""Did the result keep the subject's detail? Two candidate readings, measured
before anything ships (build walkthrough 2026-11-13, "What did not work" 2:
the toadstool photo lost its spots and stem and preflight still said B 76).

An INSTRUMENT, not a preflight check. Both readings use only what preflight
already holds -- stage 1's re-read of the artwork (`prep`: `rgb`, `bg_mask`,
`art_bbox`, `px_per_mm`) and the sewn stitches with their thread colours --
so either could become a metric without new inputs. Plan millimetres map to
the re-read exactly as `preflight._uncovered_findings` maps them.

The sewn picture is a THREAD MAP: every needle-down run drawn as a 0.45 mm
line in its thread's colour, in sew order (a later thread covers an earlier
one), on the garment colour. Both pictures are converted to CIE Lab and
smoothed (Gaussian, sigma 0.3 mm) so stitch texture and JPEG noise are not
read as detail.

Readings (constants fixed BEFORE any corpus row was read, 2026-11-14):

* `edge_recall` -- of the artwork's strong edges (a CIE76 step of at least
  EDGE_DE across 1 mm, inside the artwork mask), the share that has a strong
  edge in the thread map within MATCH_MM. A subject sewn as one flat blob
  keeps its outline at best and loses everything inside it.
* `blob_lost_frac` -- the artwork quantised to K_COLOURS (k-means in Lab);
  every connected patch of one colour of at least BLOB_MIN_MM2 inside the
  artwork mask, after an opening by a BLOB_CORE_MM disk (so the band of
  in-between colours along an edge is not a blob), is a blob, and a blob is
  LOST when the thread map's median
  colour over it is more than LOST_DE00 (CIEDE2000) from the blob's own mean
  colour. The share of blobs lost. A stem sewn in the meadow's olive is lost.
* `salient_lost_frac` -- the same blobs, each weighted by its SALIENCE (its
  mean colour against the RING_MM of artwork around it, CIEDE2000): the
  share of the picture's salience that sits in lost blobs. A small bright
  subject on a soft background weighs more than a bokeh disc. Added
  2026-11-14 AFTER the toadstool's whole-frame readings came back (they
  dilute a small subject) and BEFORE any reading was scored against Kent's
  grades; its constants are the blob reading's own.
* `edge_density` -- the CONTROL: strong source edges per artwork pixel, no
  stitches involved. A reading that separates Kent's grades no better than
  this one measures how busy the picture is, not what the result lost.

`python -m tools.subject_detail --runs DIR [DIR...] --photos DIR --out FILE`
reads photo_corpus captures (`<slug>.json` + `<slug>.row.json`) and writes
one json row per capture. Prints ASCII only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from digitizer_core.subject_detail import (BORDER_MM, EDGE_DE, EDGE_SPAN_MM,  # noqa: F401 -- re-exported
                                           MATCH_MM, SMOOTH_MM, THREAD_W_MM, Pictures,
                                           edge_readings, plan_segments, thread_map)

K_COLOURS = 8         # source quantisation for the blob reading
BLOB_MIN_MM2 = 4.0    # a 2 x 2 mm patch: sewable detail
LOST_DE00 = 15.0      # blob colour vs the thread over it
RING_MM = 1.0         # a blob's surround, for its salience
BLOB_CORE_MM = 1.0    # a blob is what survives an opening by a disk this wide


def _de00(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    from skimage.color import deltaE_ciede2000
    return deltaE_ciede2000(lab1, lab2)


def readings(p, segments, garment_rgb) -> dict:
    """The four readings for one job. `p` is stage 1's re-read. The edge
    half is `digitizer_core.subject_detail`, the code preflight runs."""
    pic = Pictures(p, segments, garment_rgb)
    ppm = pic.grid.px_per_mm
    area, src, sew = pic.area, pic.src, pic.sew
    e = edge_readings(pic)
    if not int(area.sum()):
        return {"edge_recall": None, "blob_lost_frac": None, "salient_lost_frac": None,
                "edge_density": None, "blobs": 0, "blobs_lost": 0, "strong_px": 0}

    # Blobs: k-means on a subsample of artwork pixels, every pixel labelled.
    pix = src[area].reshape(-1, 3)
    rng = np.random.default_rng(0)
    sample = pix[rng.choice(len(pix), size=min(len(pix), 40000), replace=False)]
    k = min(K_COLOURS, len(sample))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.2)
    cv2.setRNGSeed(0)
    _c, _l, centres = cv2.kmeans(sample.astype(np.float32), k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    best = np.full(src.shape[:2], np.inf, np.float32)
    label = np.zeros(src.shape[:2], np.int32)
    for c in range(k):
        dc = ((src - centres[c]) ** 2).sum(axis=2)
        closer = dc < best
        best[closer] = dc[closer]
        label[closer] = c
    label[~area] = -1
    min_px = BLOB_MIN_MM2 * ppm * ppm
    rr = max(1, int(round(RING_MM * ppm)))
    ring_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rr + 1, 2 * rr + 1))
    h, w = label.shape
    blobs = lost = 0
    sal_all = sal_lost = 0.0
    # A blob must hold a BLOB_CORE_MM core: the smoothing leaves a thin band of
    # in-between colours along every edge, k-means gives that band its own
    # cluster, and the thread map (one thread or the other) never matches it.
    # Without the opening every clean edge read as a lost blob (caught by
    # the synthetic test before any corpus row was scored).
    cr = max(1, int(round(BLOB_CORE_MM * ppm / 2.0)))
    core_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cr + 1, 2 * cr + 1))
    for c in range(k):
        solid = cv2.morphologyEx((label == c).astype(np.uint8), cv2.MORPH_OPEN, core_k)
        n, cc, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < min_px:
                continue
            x, y, bw, bh = (int(v) for v in stats[i, :4])
            m = cc[y:y + bh, x:x + bw] == i
            s_mean = src[y:y + bh, x:x + bw][m].mean(axis=0)
            t_med = np.median(sew[y:y + bh, x:x + bw][m], axis=0)
            blobs += 1
            is_lost = float(_de00(s_mean[None, :], t_med[None, :])[0]) > LOST_DE00
            lost += is_lost
            # Salience: the blob against the 1 mm of artwork around it.
            X0, Y0 = max(0, x - rr), max(0, y - rr)
            X1, Y1 = min(w, x + bw + rr), min(h, y + bh + rr)
            mm = (cc[Y0:Y1, X0:X1] == i).astype(np.uint8)
            ring = (cv2.dilate(mm, ring_k) > 0) & (mm == 0) & area[Y0:Y1, X0:X1]
            if ring.any():
                sal = float(_de00(s_mean[None, :], src[Y0:Y1, X0:X1][ring].mean(axis=0)[None, :])[0])
                sal_all += sal
                sal_lost += sal if is_lost else 0.0
    return {
        "edge_recall": e["edge_recall"],
        "blob_lost_frac": round(lost / blobs, 4) if blobs else None,
        "salient_lost_frac": round(sal_lost / sal_all, 4) if sal_all > 0 else None,
        "edge_density": e["edge_density"],
        "blobs": blobs, "blobs_lost": lost, "strong_px": e["strong_px"],
    }


def design_segments(design: dict) -> list:
    """[(rgb, points plan-mm)] from a service Design: 0.1 mm y-up, origin at
    the artwork bbox centre (`adapter`), split at every jump/trim/colour."""
    colours = [(c["r"], c["g"], c["b"]) for c in design["colors"]]
    ci = 0
    out, cur = [], []

    def flush():
        if len(cur) >= 2:
            out.append((colours[min(ci, len(colours) - 1)], list(cur)))
        cur.clear()

    for s in design["stitches"]:
        t = s.get("type")
        if t == "stitch":
            cur.append((s["x"] / 10.0, -s["y"] / 10.0))
        else:
            flush()
            if t == "color":
                ci += 1
            elif t == "jump":       # the needle lands here; the next stitch sews from it
                cur.append((s["x"] / 10.0, -s["y"] / 10.0))
    flush()
    return out


def somers_d(lost, good, sign: int) -> float:
    """2 x AUC - 1 for "a LOST value sits on the lost side of a GOOD one":
    `sign` +1 when high means lost, -1 when low does; ties count half. 0 is
    chance, 1 every pair ordered."""
    a = sign * np.asarray(lost, float)[:, None]
    b = sign * np.asarray(good, float)[None, :]
    auc = float(((a > b).sum() + 0.5 * (a == b).sum()) / (a.size * b.size))
    return 2.0 * auc - 1.0


def score_capture(json_path: Path, row_path: Path, photo: Path) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.stage1_prep import prep
    from digitizer_service.app import _decode, _parse_config
    out = json.loads(json_path.read_text(encoding="utf-8"))
    row = json.loads(row_path.read_text(encoding="utf-8")) if row_path.exists() else {}
    if out.get("state") != "done":
        return {"state": out.get("state")}
    meta = out.get("_meta") or {}
    cfgd = meta.get("config_sent") or {}
    cfg = PipelineConfig(**_parse_config(json.dumps(cfgd)))
    pixels = _decode(photo.read_bytes())
    p = prep(pixels, cfg, design_class=row.get("class") or meta.get("class"))
    garment = tuple(cfgd.get("garment_rgb") or (235, 232, 223))
    r = readings(p, design_segments(out["design"]), garment)
    pf = (out.get("preflight") or {})
    r.update({"grade": pf.get("grade"), "score": pf.get("score"),
              "element_dropped_frac": (pf.get("metrics") or {}).get("element_dropped_frac"),
              "class": row.get("class") or meta.get("class"), "kind": row.get("kind"),
              "tree_sha": (row.get("tree_sha") or meta.get("tree_sha") or "")[:8],
              "px_per_mm": round(float(p.px_per_mm), 2)})
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--photos", nargs="+", required=True, help="folders holding <slug>.png/.jpg")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from tools.photo_corpus import photo_path
    rows = {}
    outp = Path(a.out)
    if outp.exists():
        rows = json.loads(outp.read_text(encoding="utf-8"))
    for run in a.runs:
        for jp in sorted(Path(run).glob("*.json")):
            if jp.name.endswith(".row.json") or jp.stem in rows:
                continue
            slug = jp.stem
            photo = next((q for d in a.photos if (q := photo_path(Path(d), slug))), None)
            if photo is None:
                continue
            try:
                rows[slug] = score_capture(jp, jp.with_suffix(".row.json"), photo)
            except Exception as exc:  # noqa: BLE001 -- one bad row must not sink the sweep
                rows[slug] = {"error": f"{type(exc).__name__}: {exc}"}
            outp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
            print(slug, json.dumps(rows[slug])[:160], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
