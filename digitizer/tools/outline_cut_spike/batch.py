"""Run the outline-cut spike, untouched, over every text-tagged shape in the
seven saved runs. Per design: a sheet (cut plan over thread) and numbers that
say how much of each letter got sewn and how much thread landed outside it."""
import sys, pickle, time, traceback
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import oc
from shapely.geometry import LineString

PPM = 30
THREAD_MM = 0.4
names = sys.argv[1:] or ["becker", "gaulke", "drone", "enthusiast", "fremont", "tires", "bridge"]
rows = []
for name in names:
    d = pickle.load(open(HERE / f"{name}.pkl", "rb"))
    regs = [r for r in d["regions"] if r["meta"].get("text_candidate")]
    if not regs:
        print(f"{name}: no text-tagged shapes ({len(d['regions'])} regions)")
        rows.append(dict(design=name, letters=0))
        continue
    x0 = min(r["polygon"].bounds[0] for r in regs) - 1
    y0 = min(r["polygon"].bounds[1] for r in regs) - 1
    x1 = max(r["polygon"].bounds[2] for r in regs) + 1
    y1 = max(r["polygon"].bounds[3] for r in regs) + 1
    H, Wd = int((y1 - y0) * PPM), int((x1 - x0) * PPM)
    px = lambda p: (int((p[0] - x0) * PPM), int((p[1] - y0) * PPM))
    plan = np.full((H, Wd, 3), 245, np.uint8)
    thread = np.full((H, Wd, 3), (232, 236, 238), np.uint8)
    rng = np.random.default_rng(3)
    st = dict(letters=0, crashed=0, pieces=0, unsewn_pieces=0, straight=0, curved=0, cuts=0, clean=0)
    tot_len = out_len = long_len = 0.0
    art_px = cov_px = spill_px = 0
    widths, worst = [], []
    t0 = time.time()
    for r in regs:
        st["letters"] += 1
        poly = r["polygon"]
        try:
            res = oc.letter_columns(poly)
        except Exception:
            st["crashed"] += 1
            print(f"  {name} {r['shape_id']} CRASH: {traceback.format_exc().splitlines()[-1]}")
            cv2.polylines(plan, [np.array([px(p) for p in poly.exterior.coords], np.int32)], True, (0, 0, 255), 3)
            continue
        widths.append(res["W"])
        st["cuts"] += len(res["cuts"])
        art = np.zeros((H, Wd), np.uint8)
        cv2.fillPoly(art, [np.array([px(p) for p in res["poly"].exterior.coords], np.int32)], 1)
        for h in res["poly"].interiors:
            cv2.fillPoly(art, [np.array([px(p) for p in h.coords], np.int32)], 0)
        sewn = np.zeros((H, Wd), np.uint8)
        l_tot = l_out = l_long = 0.0
        unsewn_here = 0
        safe = res["poly"].buffer(0.15)
        for c in res["cols"]:
            st["pieces"] += 1
            col = tuple(int(v) for v in rng.integers(150, 235, 3))
            cv2.fillPoly(plan, [np.array([px(p) for p in c["piece"].exterior.coords], np.int32)], col)
            for h in c["piece"].interiors:
                cv2.fillPoly(plan, [np.array([px(p) for p in h.coords], np.int32)], (245, 245, 245))
            if not c["stitches"]:
                st["unsewn_pieces"] += 1
                unsewn_here += 1
                cp = c["piece"].representative_point().coords[0]
                cv2.putText(plan, "X", px(cp), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                continue
            st["straight" if c["axis"] else "curved"] += 1
            pw = 2.0 * c["piece"].area / max(c["piece"].length, 1e-9)       # this piece's own stroke width
            for p, q in zip(c["stitches"][:-1], c["stitches"][1:]):
                seg = LineString([p, q])
                l_tot += seg.length
                l_out += seg.length - seg.intersection(safe).length      # thread over bare ground or a counter
                if seg.length > 1.6 * res["W"]:
                    l_long += seg.length                                  # a stitch far longer than the stroke is wide
            bad = (0, 0, 255)
            pts = np.array([px(p) for p in c["stitches"]], np.int32)
            cv2.polylines(sewn, [pts], False, 1, max(1, int(round(THREAD_MM * PPM))))
            cv2.polylines(thread, [pts], False, (70, 66, 60), max(1, int(round(THREAD_MM * PPM)) - 2), cv2.LINE_AA)
            cv2.polylines(thread, [pts], False, (128, 120, 112), 2, cv2.LINE_AA)
        for ring in [res["poly"].exterior] + list(res["poly"].interiors):
            cv2.polylines(plan, [np.array([px(p) for p in ring.coords], np.int32)], True, (60, 60, 60), 1)
        for a, b, kind, _ in res["cuts"]:
            cv2.line(plan, px(a), px(b), (0, 0, 255), 2)
        a_n = int(art.sum()); c_n = int((art & sewn).sum()); s_n = int((sewn & (1 - art)).sum())
        tot_len += l_tot; out_len += l_out; long_len += l_long
        ok = unsewn_here == 0 and l_tot > 0 and l_out / l_tot < 0.02 and l_long / l_tot < 0.05 and c_n / max(a_n, 1) > 0.9
        st["clean"] += int(ok)
        if not ok:
            bx = res["poly"].bounds
            cv2.rectangle(thread, px((bx[0] - 0.3, bx[1] - 0.3)), px((bx[2] + 0.3, bx[3] + 0.3)), (0, 0, 220), 2)
        art_px += a_n; cov_px += c_n; spill_px += s_n
        if a_n:
            worst.append((c_n / a_n, s_n / a_n, r["shape_id"], r["meta"].get("ocr_char"), round(res["W"], 2)))
    out = np.vstack([plan, np.full((6, Wd, 3), 90, np.uint8), thread])
    cv2.imwrite(str(HERE / f"sheet_{name}.png"), out)
    worst.sort()
    row = dict(design=name, **st, W_med=float(np.median(widths)) if widths else None,
               W_min=float(min(widths)) if widths else None,
               covered=cov_px / max(art_px, 1), spill=spill_px / max(art_px, 1), secs=time.time() - t0)
    rows.append(row)
    print(f"{name}: letters={st['letters']} crashed={st['crashed']} cuts={st['cuts']} pieces={st['pieces']} "
          f"(straight {st['straight']}, curved {st['curved']}, UNSEWN {st['unsewn_pieces']}) "
          f"W med {row['W_med']:.2f} min {row['W_min']:.2f} mm | covered {row['covered']:.1%} | "
          f"thread off the art {out_len / max(tot_len, 1e-9):.1%} | over-long stitches {long_len / max(tot_len, 1e-9):.1%} | "
          f"CLEAN LETTERS {st['clean']}/{st['letters']} | {row['secs']:.0f}s")
