"""Close-ups OFF | ON+guard | pro at apex_cut's gaining tips, single stitches visible.
argv: tree corpus_dir tipgroups.json out_dir
ON+guard = ON at these tips (Becker x5 / ProSeal md5 = ON; Bridge, duotone window-identical),
so the corpus ON pickle's runs are drawn for it."""
import json
import pickle
import sys
from pathlib import Path

tree, corpus, tg, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(tree))
out.mkdir(parents=True, exist_ok=True)
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pystitch  # noqa: E402

from tools import pro_baseline as pb  # noqa: E402
import tools.pro_parity.pairframe as pf  # noqa: E402  (puts scorecard on the path)
import scorecard as sc  # noqa: E402

tips = json.load(open(tg))
GAINS = {"becker_hat_large": ["Se264484b"], "proseal_hat": ["S29dcc431", "Sedf6da54"],
         "bridge_hat": ["S3526e394", "Se8e1faff"], "duotone_poster": ["Sb080876a"]}
S, HALF = 40.0, 4.0
GROUND = (223, 232, 235)


def our_rows(runs, flip):
    rows = []
    for bi, blk in enumerate(runs):
        for _rgb, rs in blk:
            for pts, kind, jump, trim, sid in rs:
                pend = True
                for x, y in pts:
                    rows.append((bi, x, -y if flip else y, pend))
                    pend = False
    return rows


def register(pro_path, runs):
    pro = pf.file_segs(Path(pro_path), False)
    best = None
    for flip in (False, True):
        ours = sc.to_segs(our_rows(runs, flip))
        s = pf.x_extent(pro) / max(pf.x_extent(ours), 1e-9)
        ours_s = pf.scale_segs(ours, s)
        (pcx, pcy), (ocx, ocy) = pf.centre(pro), pf.centre(ours_s)
        dx, dy = pcx - ocx, pcy - ocy
        ours_c = sc.shifted(ours_s, dx, dy)
        rdx, rdy, iou = sc.register(pro, ours_c, sc.bounds(pro, ours_c))
        if best is None or iou > best[4]:
            best = (s, flip, dx + rdx, dy + rdy, float(iou))
    return best


def pro_runs(pro_path, reg):
    s, flip, dx, dy, _iou = reg
    pat = pystitch.read(str(pro_path))
    cols = [((t.color >> 16) & 255, (t.color >> 8) & 255, t.color & 255) for t in pat.threadlist] or [(60, 60, 60)]
    runs, cur, block = [], [], 0
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            ox, oy = (x / 10.0 - dx) / s, (y / 10.0 - dy) / s
            cur.append((ox, -oy if flip else oy))
        else:
            if len(cur) > 1:
                runs.append((cols[min(block, len(cols) - 1)], cur))
            cur = []
            if c == pystitch.COLOR_CHANGE:
                block += 1
            if c == pystitch.END:
                break
    if len(cur) > 1:
        runs.append((cols[min(block, len(cols) - 1)], cur))
    return runs


def flat(runs):
    return [(rgb, pts) for blk in runs for rgb, rs in blk for pts, kind, jump, trim, sid in rs]


def panel(runs, cx, cy, title):
    img = np.full((int(2 * HALF * S), int(2 * HALF * S), 3), GROUND, np.uint8)
    w = max(1, int(round(0.38 * S)))
    for rgb, pts in runs:
        a = np.round((np.asarray(pts, float)[:, :2] - [cx - HALF, cy - HALF]) * S).astype(np.int32)
        if len(a) < 2 or (a[:, 0].max() < -50 or a[:, 0].min() > img.shape[1] + 50
                          or a[:, 1].max() < -50 or a[:, 1].min() > img.shape[0] + 50):
            continue
        col = tuple(int(v) for v in reversed(rgb))
        for p0, p1 in zip(a[:-1], a[1:]):       # each stitch: grey outline, then thread
            if np.hypot(*(p1 - p0)) > 12.5 * S:   # a jump drawn as one stitch would hide the rest
                continue
            cv2.line(img, tuple(map(int, p0)), tuple(map(int, p1)), (120, 120, 120), w + 3, cv2.LINE_AA)
            cv2.line(img, tuple(map(int, p0)), tuple(map(int, p1)), col, w, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (img.shape[1], 24), (255, 255, 255), -1)
    cv2.putText(img, title, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 180), 1)
    return img


def changed_windows(off, on, sid_list, n=3):
    """The n most-changed 8 mm windows between OFF and ON (needle lines rasterised at 4 px/mm)."""
    def ras(runs):
        pts = [p for _rgb, ps in flat(runs) for p in ps]
        return pts
    allp = np.array(ras(off) + ras(on))
    x0, y0 = allp.min(axis=0) - 5
    W, H = (allp.max(axis=0) - allp.min(axis=0) + 10) * 4
    ims = []
    for runs in (off, on):
        im = np.zeros((int(H) + 1, int(W) + 1), np.uint8)
        for _rgb, pts in flat(runs):
            a = np.round((np.asarray(pts) - [x0, y0]) * 4).astype(np.int32)
            cv2.polylines(im, [a], False, 255, 1)
        ims.append(im.astype(np.float32))
    d = cv2.boxFilter(np.abs(ims[0] - ims[1]), -1, (32, 32))
    picks = []
    for _ in range(n):
        y, x = np.unravel_index(int(np.argmax(d)), d.shape)
        if d[y, x] <= 0:
            break
        picks.append((x / 4 + x0, y / 4 + y0))
        cv2.rectangle(d, (x - 40, y - 40), (x + 40, y + 40), 0, -1)
    return picks


for name, sids in GAINS.items():
    off = pickle.load(open(corpus / "off" / f"{name}.pkl", "rb"))
    on = pickle.load(open(corpus / "on" / f"{name}.pkl", "rb"))
    spots = [(t["at"][0], t["at"][1], f"{t['sid']} tip") for t in tips if t["design"] == name and t["sid"] in sids]
    if name == "becker_hat_large":
        spots += [(x, y, f"changed #{i + 2}") for i, (x, y) in enumerate(changed_windows(off["runs"], on["runs"], sids, 3))
                  if all(np.hypot(x - a, y - b) > 3.0 for a, b, _ in spots)][:2]
    pro = None
    if name in pb.JOBS:
        j = pb.JOBS[name]
        path = pb.resolve(j[4]) if len(j) > 4 and j[4] else pb.resolve(j[3])
        reg = register(path, on["runs"])
        pro = pro_runs(path, reg)
        print(name, "registered iou", round(reg[4], 3), "scale", round(reg[0], 3), flush=True)
    rows = []
    for x, y, lab in spots:
        row = [panel(flat(off["runs"]), x, y, f"OFF  {name} {lab}"), panel(flat(on["runs"]), x, y, "ON+guard (= ON here)")]
        row.append(panel(pro, x, y, "pro") if pro is not None else
                   np.full_like(row[0], 255))
        rows.append(cv2.copyMakeBorder(np.hstack(row), 0, 6, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    cv2.imwrite(str(out / f"gain_{name}.png"), np.vstack(rows))
    print(name, len(rows), "windows", flush=True)
