"""Rule 12: read every pro DST (registry) + our re-run DSTs; rings, colours, contrast. -> rows.json"""
import json, sys
from pathlib import Path
import numpy as np
import cv2
HERE = Path(__file__).parent
REPO = Path(r"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot")
sys.path.insert(0, str(REPO / "digitizer")); sys.path.insert(0, str(HERE))
import pystitch
from skimage.color import rgb2lab, deltaE_ciede2000
import reader, ring
from reader import PPM, disk
from tools import pro_intake

PAIRED = ["hotel_fremont_patch", "mfab_hat", "machine_hat", "precision_drone", "becker_hat_large", "golf_hat"]
CARTOONS = ["pooh", "owl_kent", "tux_gradient_mascot", "bison_flat_emoji"]


def lab(rgb):
    return rgb2lab(np.array([[rgb]], np.float64) / 255.0)[0, 0]


def de(a, b):
    return float(deltaE_ciede2000(lab(a)[None, None], lab(b)[None, None])[0, 0])


def dst_block_counts(pts):
    return [sum(1 for q in b if q[2] == "S") for b in reader.blocks_of(pts)]


def pes_colours(pes, dst_counts):
    pat = pystitch.read(str(pes))
    blocks = []
    for st, th in pat.get_as_colorblocks():
        n = sum(1 for s in st if (s[2] & pystitch.COMMAND_MASK) == pystitch.STITCH)
        if n:
            c = th.color if hasattr(th, "color") else th.get_color()
            blocks.append((n, ((c >> 16) & 255, (c >> 8) & 255, c & 255), th.description or th.catalog_number))
    pc = [b[0] for b in blocks]
    if len(pc) != len(dst_counts):
        return None, f"PES has {len(pc)} sewn blocks, DST {len(dst_counts)}"
    worst = max(abs(a - b) / max(1, b) for a, b in zip(pc, dst_counts))
    if worst > 0.05:
        return None, f"block stitch counts differ by up to {worst:.0%}"
    return [dict(rgb=b[1], name=str(b[2])) for b in blocks], f"PES blocks match DST (worst count diff {worst:.1%})"


def plan_colours(plan, dst_counts):
    bl = [b for b in plan["blocks"] if b["n_points"] > 0]
    if len(bl) != len(dst_counts):
        return None, f"plan has {len(bl)} sewn blocks, DST {len(dst_counts)}"
    return [dict(rgb=tuple(b["rgb"]), name=b["thread"]) for b in bl], "plan blocks match DST"


def surround(ctx, r, excl):
    (Xa, Ya, Xb, Yb), P0 = ring._win(ctx, r)
    P = ring.filled(P0)
    Z = cv2.dilate(P, disk(2 * 1.6)) & (1 - cv2.dilate(P, disk(2 * 0.8)))
    n = max(1, int(Z.sum()))
    cs = [(k, float((R[Ya:Yb, Xa:Xb] & Z).sum()) / n) for k, R in enumerate(ctx["rasters"])
          if k != r["block"] and k not in excl]
    cs = [c for c in cs if c[1] > 0]
    if not cs:
        return None
    top = max(c[1] for c in cs)
    return max((c for c in cs if c[1] >= top - 0.02), key=lambda c: c[0])   # near-tie: the later (on top)


def do_file(dst, label, side, cols, colnote):
    pts = reader.points_of(dst)
    rows, summ, ctx = reader.read(pts, label)
    ring.annotate(rows, ctx)
    gid = ctx["gid"]
    out = []
    for r in rows:
        host = max((gid[h] for h in r["_host_ids"]), key=lambda g: g["block"])["block"]
        ringblocks = {c["block"] for c in r["rings"]}
        sb = surround(ctx, r, ringblocks)
        row = dict(job=label, side=side, block=r["block"], host_ground_block=host,
                   area_mm2=float(r["area_mm2"]), width_mm=float(r["width_mm"]),
                   bbox_mm=[round(r["bbox_px"][0] / PPM + ctx["x0"], 2), round(r["bbox_px"][1] / PPM + ctx["y0"], 2),
                            round(r["bbox_px"][2] / PPM + ctx["x0"], 2), round(r["bbox_px"][3] / PPM + ctx["y0"], 2)],
                   is_ring_of_other=r["is_ring_of"] is not None,
                   ring_cands=r["ring_cands"], own_satin_edge_cov=r["own_satin_edge_cov"],
                   own_satin_edge_ring=r["own_satin_edge_ring"],
                   surround_block=None if sb is None else sb[0],
                   surround_cov=None if sb is None else round(sb[1], 3))
        rings_c, rings_own = [], []
        for c in r["rings"]:
            rc = dict(block=c["block"], cov=c["cov"], far=c["far"], sewn=c["sewn"])
            if cols:
                rc["rgb"] = cols[c["block"]]["rgb"]; rc["thread"] = cols[c["block"]]["name"]
                d_own = de(cols[c["block"]]["rgb"], cols[r["block"]]["rgb"])
                rc["dE_to_piece"] = round(d_own, 2)
                rc["dE_to_ground"] = round(de(cols[c["block"]]["rgb"], cols[host]["rgb"]), 2)
                (rings_own if d_own < 1.0 else rings_c).append(rc)
            else:
                rings_c.append(rc)   # thread not read: counted as a ring, colour unknown
        row["contrast_rings"] = rings_c
        row["own_colour_rings_block"] = rings_own
        row["ring"] = bool(rings_c)
        row["own_colour_ring"] = bool(rings_own) or r["own_satin_edge_ring"]
        row["colours"] = colnote
        if cols:
            pc, gc = cols[r["block"]]["rgb"], cols[host]["rgb"]
            row.update(piece_rgb=list(pc), piece_thread=cols[r["block"]]["name"],
                       ground_rgb=list(gc), ground_thread=cols[host]["name"],
                       dE00_ground=round(de(pc, gc), 2), dL_ground=round(float(lab(pc)[0] - lab(gc)[0]), 2))
            if sb is not None:
                sc = cols[sb[0]]["rgb"]
                row.update(surround_rgb=list(sc), dE00_surround=round(de(pc, sc), 2),
                           dL_surround=round(float(lab(pc)[0] - lab(sc)[0]), 2))
        out.append(row)
    return out, dict(job=label, side=side, stitches=summ["stitches"], blocks=summ["blocks"],
                     grounds=summ["grounds"], colours=colnote, dst=str(dst))


def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    return o.item() if hasattr(o, "item") else o


allrows, summs = [], []
reg = json.loads((REPO / "scratch_kent/pro_intake/registry.json").read_text(encoding="utf-8"))
slugs = [p["slug"] for j in reg["jobs"].values() for p in j["pairs"] if not p["slug"].startswith("test_files")]
for s in slugs:
    rec = pro_intake.pair_record(s)
    dst = Path(rec["dst"])
    cnt = dst_block_counts(reader.points_of(dst))
    cols, note = (None, "no PES twin: colours not read")
    if rec.get("pes") and Path(rec["pes"]).exists():
        cols, note = pes_colours(rec["pes"], cnt)
        if cols is None:
            note = "colours not read: " + note
    rows, sm = do_file(dst, s, "pro", cols, note)
    sm.update(art=rec.get("art"), width_mm=rec.get("width_mm"), block_colours=cols)
    allrows += rows; summs.append(sm)
    print("pro", s, len(rows), note, flush=True)
for name in PAIRED + CARTOONS:
    d = HERE / "ours" / name
    if not (d / "ours.dst").exists():
        print("ours", name, "MISSING"); continue
    plan = json.loads((d / "plan.json").read_text())
    cnt = dst_block_counts(reader.points_of(d / "ours.dst"))
    cols, note = plan_colours(plan, cnt)
    if cols is None:
        note = "colours not read: " + note
    side = "ours" if name in PAIRED else "ours_cartoon"
    rows, sm = do_file(d / "ours.dst", name, side, cols, note)
    sm.update(art=plan["art"], width_mm=plan["width_mm"], block_colours=cols)
    allrows += rows; summs.append(sm)
    print(side, name, len(rows), note, flush=True)
json.dump(clean(dict(rows=allrows, summaries=summs)), open(HERE / "rows.json", "w"), indent=1, default=str)
