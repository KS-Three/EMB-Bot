"""A: which path closes the ground's hole under later shapes. Usage: a_instrument.py JOB [extra.KEY=JSON ...]
Captures the regions entering stage 5 (after silhouette_underfill) and the planned polygons leaving it."""
import json, sys
from pathlib import Path
REPO = Path(r"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot")
sys.path.insert(0, str(REPO / "digitizer"))
from shapely.geometry import Polygon
from tools import pro_pair, pro_intake
import digitizer_core.pipeline as P
from digitizer_core import silhouette_underfill as SU

cap = {}
_ro = P.resolve_overlaps
def ro(regions, *a, **k):
    out = _ro(regions, *a, **k)
    cap["in"] = list(regions); cap["out"] = out[0]
    return out
P.resolve_overlaps = ro
_ac = SU.apply_cfg
def ac(regions, unsewn, cfg, outlines, pinned=()):
    out = _ac(regions, unsewn, cfg, outlines, pinned=pinned)
    cap["underfill_report"] = out[1]
    return out
SU.apply_cfg = ac
_gate = P.gate_underfill_for_photo
def gate(cfg, cls, keyline_art=False):
    c = _gate(cfg, cls, keyline_art)
    cap["class"] = cls; cap["keyline_art"] = keyline_art
    cap["underfill_after_gate"] = (c.silhouette_underfill, c.silhouette_underfill_panels)
    return c
P.gate_underfill_for_photo = gate

job = sys.argv[1]
extra = {}
for kv in sys.argv[2:]:
    k, v = kv.split("=", 1); extra[k] = json.loads(v)
rec = pro_intake.pair_record(job)
width = rec.get("width_mm") or pro_pair.pro_counts(rec["dst"])["width_mm"]
d = pro_pair.digitize(rec["art"], width, rec.get("garment_id") or "hat_front", extra or None)
print("job", job, "width", width, "extra", extra, "class", cap.get("class"), "keyline_art", cap.get("keyline_art"),
      "underfill flags after gate", cap.get("underfill_after_gate"))
print("cfg.silhouette_underfill", d.cfg.silhouette_underfill, "panels", d.cfg.silhouette_underfill_panels,
      "sew_enclosed_white", d.cfg.sew_enclosed_white, "overlap_mm", d.cfg.overlap_mm)
print("underfill report:", json.dumps(cap.get("underfill_report"), default=str)[:1500])

stage4 = {r.shape_id: r for r in d.result.regions}
ins = {r.shape_id: r for r in cap["in"]}
outp = {p.region.shape_id: p for p in cap["out"]}
pairs = 0; covered = 0
for rid, r in ins.items():
    if r.polygon is None or r.polygon.is_empty or not r.meta.get("stitched", True):
        continue
    pt = r.polygon.representative_point()
    for gid, g in ins.items():
        if gid == rid or g.meta["layer"] >= r.meta["layer"]:
            continue
        g4 = stage4.get(gid)
        gp4 = g4.polygon if g4 is not None else None
        if gp4 is None or gp4.geom_type != "Polygon" or not Polygon(gp4.exterior).contains(pt):
            continue
        hole4 = not gp4.contains(pt)
        pin = g.polygon
        hole_in = pin.geom_type == "Polygon" and Polygon(pin.exterior).contains(pt) and not pin.contains(pt)
        sil = g.meta.get(SU.UNDERFILL_KEY)
        sil_covers = sil is not None and sil.contains(pt)
        po = outp.get(gid)
        sewn_after5 = po is not None and po.polygon.contains(pt)
        pairs += 1; covered += sewn_after5
        if pairs <= 12 or not sewn_after5:
            print(f"piece {rid} (layer {r.meta['layer']}, thread {r.thread_index}, {r.polygon.area:.1f} mm2) "
                  f"on ground {gid} (layer {g.meta['layer']}, {g.polygon.area:.0f} mm2): "
                  f"hole after stage4={hole4}  hole entering stage5={hole_in}  "
                  f"underfill outline covers={sil_covers}  ground polygon after stage5 covers={sewn_after5}")
print("pairs (piece inside an earlier region's outer contour):", pairs,
      "covered after stage 5:", covered)
