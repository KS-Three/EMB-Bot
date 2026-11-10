"""A defect-marking sitting: Kent clicks what is wrong on ONE render at a time.

    python -m tools.defect_marks capture-pro --out RUN [--tree DIGITIZER] [--only SLUG]
    python -m tools.defect_marks kit --out KIT [--corpus RUN] [--pro RUN]
    python -m tools.defect_marks serve --kit KIT [--port 8736]
    python -m tools.defect_marks report --kit KIT

Why it exists (2026-11-10). Ten eye-pairs sittings asked Kent "left or right?"
and tested whole-design numbers (trims, pixel agreement, DreamSim, a vision
judge) against the pick; none stands in for him. His 22 written reasons
(2026-11-07) are all LOCAL: a blob in the M, a wavy I, a flat spot on the P, an
anchor that breaks off. A whole-design number averages those away, and a
left/right pick never says where or what. This page asks the other question:
on one render, click each spot that is wrong, say what it is and how bad, and
give the render an absolute grade (his own 2026-10-28 scale).

The yardstick's own reading of the same design (preflight score, grade and
findings, the corpus fidelity figure) is stored in `kit.json` and NEVER sent
to the page, so his marks are blind to it. `report` puts the two side by side.
Every figure it prints is an instrument reading or Kent's own answer, not a
quality claim (ROADMAP gate 4).

* `capture-pro` digitizes one job per pro-paired artwork (`PRO_SLUGS`, rows of
  `pro_baseline.JOBS`) at the job's own garment and width with
  `photo_corpus`'s worker, so a pro logo and a corpus photo carry the same
  record: design, stats, preflight.
* `kit` reads a `photo_corpus capture` run and/or a `capture-pro` run and
  writes `kit.json`, `index.html` and `img/` (artwork, render at `PXMM`, the
  pro's file drawn the same way where one exists). The folder must be
  gitignored: it holds client artwork and renders of pro files.
* `serve` is localhost only; every answer is written to `marks.json` (temp
  file, fsync, replace) before the request is answered.

Pure helpers (`mark_mm`, `clean_item`, `public_kit`, `report_rows`) take plain
dicts so the tests need no engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # digitizer/
PXMM = 12.0          # render scale of the page's pictures, px per mm
PAD_MM = 2.0         # stitchviz.render_design's own default pad
PORT = 8736
GRADES = ("Great", "Good", "Okay", "Bad", "Terrible")           # Kent's 2026-10-28 scale
SEVERITIES = ("ruins", "noticeable", "nitpick")

#: What a pin can be. The first four are lettering, in the words of Kent's
#: 2026-11-07 reasons; the rest apply to any artwork. `other` needs a note.
WHATS = {
    "pen_flow": "Letter stitches don't follow the pen stroke",
    "letter_shape": "Letter shape wrong / can't read it",
    "wavy": "Wavy where it should be straight",
    "lumpy_curve": "Lumpy or flat spot on a curve",
    "blob": "Blob / pile-up of thread",
    "stray": "Stray or crossover stitch",
    "gap": "Gap: fabric shows where it shouldn't",
    "missing": "Piece missing or broken off",
    "extra": "Extra piece that isn't in the art",
    "colour": "Wrong color here",
    "direction": "Stitch direction looks wrong",
    "stitch_type": "Wrong stitch type (fill / satin / line)",
    "mushed": "Detail mushed together",
    "jagged": "Jagged / stair-step edge",
    "other": "Other (type it)",
}

#: Problems with no single spot.
WHOLE = {
    "unrecognizable": "Can't tell what it is",
    "too_busy": "Too busy / too many little pieces",
    "colours_off": "Colors wrong overall",
    "background_sewn": "Background got sewn and shouldn't be",
    "detail_lost": "Too much detail lost",
    "not_for_thread": "This art should not be embroidered as-is",
}

#: One job per pro-paired artwork (the 22 `pro_baseline.JOBS` rows draw 11
#: artworks; marking the same logo on three garments spends Kent's time on
#: repeats). The hat row where there is one: the largest lettering.
PRO_SLUGS = ("becker_hat_large", "bridge_hat", "gaulke_roofing_hat", "hotel_fremont_hat", "mfab_hat",
             "precision_drone", "proseal_hat", "tires_hat_3d", "goldentee_hat", "toat_machine_hat",
             "toat_beanie")


# ------------------------------------------------------------ pure helpers ----

def mark_mm(x: float, y: float, img_w: int, img_h: int, px_per_mm: float = PXMM,
            pad_mm: float = PAD_MM) -> tuple[float, float]:
    """A click at fractions (x, y) of the render -> mm from the design's own
    top-left corner (x right, y down), undoing `stitchviz._frame`'s pad."""
    return (round(x * img_w / px_per_mm - pad_mm, 2), round(y * img_h / px_per_mm - pad_mm, 2))


def clean_item(body: dict, item: dict) -> dict:
    """One item's answer as the page posts it -> the record `marks.json` keeps.
    Raises ValueError on anything outside the page's own vocabulary, so a
    typo'd client cannot write a category `report` would silently drop."""
    grade = body.get("grade")
    if grade is not None and grade not in GRADES:
        raise ValueError("grade")
    whole = body.get("whole") or []
    if not isinstance(whole, list) or any(w not in WHOLE for w in whole):
        raise ValueError("whole")
    pins = []
    for p in body.get("pins") or []:
        x, y = float(p["x"]), float(p["y"])
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError("pin position")
        what, sev = p.get("what"), p.get("severity")
        if what is not None and what not in WHATS:
            raise ValueError("pin what")
        if sev is not None and sev not in SEVERITIES:
            raise ValueError("pin severity")
        xm, ym = mark_mm(x, y, item["img_w"], item["img_h"], item["px_per_mm"], item["pad_mm"])
        pins.append({"x": round(x, 5), "y": round(y, 5), "x_mm": xm, "y_mm": ym, "what": what,
                     "severity": sev, "note": str(p.get("note") or "")[:300]})
    if len(pins) > 40:
        raise ValueError("too many pins")
    return {"grade": grade, "nothing_wrong": bool(body.get("nothing_wrong")), "whole": list(whole),
            "reason": str(body.get("reason") or "")[:500], "pins": pins}


def public_kit(kit: dict) -> dict:
    """The kit as the PAGE gets it: no yardstick reading, no tree sha, nothing
    that could lead his marks."""
    keep = ("id", "group", "title", "size", "art", "render", "pro", "pro_colours", "img_w", "img_h")
    return {"kit_sha256": kit["kit_sha256"], "whats": WHATS, "whole": WHOLE, "grades": list(GRADES),
            "severities": list(SEVERITIES),
            "items": [{k: it.get(k) for k in keep} for it in kit["items"]]}


def answered(rec: dict | None) -> bool:
    """An item counts as done when it has a grade and either a pin, a
    whole-design tick or an explicit "nothing wrong"."""
    return bool(rec and rec.get("grade") and (rec.get("pins") or rec.get("whole") or rec.get("nothing_wrong")))


GRADE_OF_LETTER = {"A": "Great", "B": "Good", "C": "Okay", "D": "Bad", "F": "Terrible"}


def report_rows(kit: dict, marks: dict) -> list[dict]:
    """One row per answered item: Kent's grade beside the yardstick's, the
    step between them on the five-point scale (+ = yardstick kinder than
    Kent), his pins by category, and the yardstick's finding codes."""
    rows = []
    for it in kit["items"]:
        rec = (marks.get("items") or {}).get(it["id"])
        if not answered(rec):
            continue
        y = it.get("yardstick") or {}
        ylet = y.get("grade")
        step = None
        if ylet in GRADE_OF_LETTER:
            step = GRADES.index(rec["grade"]) - GRADES.index(GRADE_OF_LETTER[ylet])
        pins: dict[str, int] = {}
        for p in rec["pins"]:
            pins[p.get("what") or "unnamed"] = pins.get(p.get("what") or "unnamed", 0) + 1
        codes: dict[str, int] = {}
        for f in y.get("findings") or []:
            codes[f["code"]] = codes.get(f["code"], 0) + 1
        rows.append({"id": it["id"], "group": it["group"], "kent": rec["grade"], "yardstick": ylet,
                     "yardstick_score": y.get("score"), "step": step, "pins": pins,
                     "ruins": sum(1 for p in rec["pins"] if p.get("severity") == "ruins"),
                     "whole": rec["whole"], "codes": codes, "fidelity_cc": y.get("fidelity_cc"),
                     "reason": rec.get("reason") or ""})
    return rows


# ------------------------------------------------------------- capture-pro ----

def capture_pro(out: Path, tree: Path, slugs=PRO_SLUGS, timeout: float = 1200.0) -> int:
    """Each pro job at its own garment and width through `photo_corpus`'s
    worker (the service's call sequence + preflight), one at a time.
    `<slug>.json` kept = resume."""
    import subprocess
    from tools import photo_corpus as pc
    from tools import pro_baseline as pb
    from tools import pro_pair
    out.mkdir(parents=True, exist_ok=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tree), capture_output=True,
                         text=True).stdout.strip() or None
    bad = 0
    for slug in slugs:
        garment, width, art = pb.JOBS[slug][0], float(pb.JOBS[slug][1]), pb.resolve(pb.JOBS[slug][2])
        dest = out / f"{slug}.json"
        if dest.exists() and json.loads(dest.read_text(encoding="utf-8")).get("state") == "done":
            print(slug, "kept", flush=True)
            continue
        res = pc.run_row(tree, art, dest, pro_pair.request(width, garment), timeout, sha)
        bad += res.get("state") != "done"
        print(slug, res.get("state"), (res.get("_meta") or {}).get("elapsed_s"), flush=True)
    return 1 if bad else 0


# --------------------------------------------------------------------- kit ----

def _yardstick(output: dict, row: dict | None = None) -> dict:
    pf = output.get("preflight") or {}
    st = output.get("stats") or {}
    return {"grade": pf.get("grade"), "score": pf.get("score"), "findings": pf.get("findings") or [],
            "metrics": pf.get("metrics") or {}, "stitches": st.get("stitch_count"), "trims": st.get("trims"),
            "class": (output.get("_meta") or {}).get("class"),
            "fidelity_cc": (row or {}).get("fidelity_cc"), "score_raw": (row or {}).get("score_raw")}


def _write_art(src: Path, dest: Path, fabric_bgr, max_px: int = 1100) -> None:
    import cv2
    from tools.photo_corpus import load_photo
    img = load_photo(src, fabric_bgr)
    if img is None:                                   # webp / gif cv2 cannot read
        from PIL import Image
        import numpy as np
        img = cv2.cvtColor(np.array(Image.open(src).convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    s = min(1.0, max_px / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 90])


def _item(iid: str, group: str, title: str, output: dict, art: Path, img: Path, *,
          pro_file: Path | None = None, pro_pes: Path | None = None, row: dict | None = None) -> dict:
    import cv2
    from digitizer_core.stitchviz import render_design
    cfg = (output.get("_meta") or {}).get("config_sent") or {}
    fabric = tuple(reversed(cfg.get("garment_rgb") or [235, 232, 223]))
    design = output["design"]
    render = render_design(design, px_per_mm=PXMM, fabric_bgr=fabric, pad_mm=PAD_MM)
    cv2.imwrite(str(img / f"{iid}_render.png"), render)
    _write_art(art, img / f"{iid}_art.jpg", fabric)
    it = {"id": iid, "group": group, "title": title, "art": f"{iid}_art.jpg", "render": f"{iid}_render.png",
          "pro": None, "pro_colours": False, "img_w": int(render.shape[1]), "img_h": int(render.shape[0]), "px_per_mm": PXMM,
          "pad_mm": PAD_MM,
          "size": f"{design.get('widthMM')} x {design.get('heightMM')} mm on {cfg.get('garment_id', '?')}",
          "tree_sha": (output.get("_meta") or {}).get("tree_sha"), "yardstick": _yardstick(output, row)}
    if pro_file is not None and pro_file.exists():
        # a DST stores no thread colours; the job's PES does, so draw that when there is one
        from tools.eye_pairs.filearm import design_from_file
        it["pro_colours"] = bool(pro_pes is not None and pro_pes.exists())
        src = pro_pes if it["pro_colours"] else pro_file
        pro = render_design(design_from_file(src), px_per_mm=PXMM, fabric_bgr=fabric, pad_mm=PAD_MM)
        cv2.imwrite(str(img / f"{iid}_pro.png"), pro)
        it["pro"] = f"{iid}_pro.png"
    return it


def build_kit(out: Path, corpus: Path | None, pro: Path | None, photos: Path | None = None) -> dict:
    """`kit.json` + `index.html` + `img/`. Order: pro logos, photos, Commons
    logo styles (Kent graded those on 2026-10-28; they are last on purpose).
    `photos` = the corpus image folder (gitignored, so a lane has none of its
    own; default `photo_corpus.CORPUS_DIR`)."""
    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    skipped: list[str] = []
    if pro is not None:
        from tools import pro_baseline as pb
        for slug in PRO_SLUGS:
            f = pro / f"{slug}.json"
            output = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
            if output.get("state") != "done":
                skipped.append(slug)
                continue
            pes = pb.JOBS[slug][4] if len(pb.JOBS[slug]) > 4 else None
            items.append(_item(f"L_{slug}", "pro_logo", slug.replace("_", " "), output,
                               pb.resolve(pb.JOBS[slug][2]), img, pro_file=pb.resolve(pb.JOBS[slug][3]),
                               pro_pes=pb.resolve(pes) if pes else None))
    if corpus is not None:
        from tools import photo_corpus as pc
        photos = Path(photos) if photos else pc.CORPUS_DIR
        rows = json.loads((photos / "corpus.json").read_text(encoding="utf-8"))
        for kind, group, tag in (("photo", "photo", "P"), ("logo", "commons_logo", "C")):
            for r in rows:
                if r["kind"] != kind:
                    continue
                f = corpus / f"{r['slug']}.json"
                output = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
                photo = pc.photo_path(photos, r["slug"])
                if output.get("state") != "done" or photo is None or not (output.get("stats") or {}).get("stitch_count"):
                    skipped.append(r["slug"])
                    continue
                rj = corpus / f"{r['slug']}.row.json"
                row = json.loads(rj.read_text(encoding="utf-8")) if rj.exists() else None
                items.append(_item(f"{tag}_{r['slug']}", group, r["genre"].replace("_", " "), output, photo, img,
                                   row=row))
    sha = hashlib.sha256(json.dumps([[it["id"], it["tree_sha"], it["img_w"], it["img_h"]] for it in items],
                                    sort_keys=True).encode()).hexdigest()
    kit = {"built": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kit_sha256": sha,
           "px_per_mm": PXMM, "skipped": skipped, "items": items}
    (out / "kit.json").write_text(json.dumps(kit), encoding="utf-8")
    (out / "index.html").write_text(page_html(kit), encoding="utf-8")
    return kit


# -------------------------------------------------------------------- page ----

PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>Mark what's wrong</title>
<style>
body{margin:0;background:#2b2b2b;color:#ddd;font:14px system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:#222;padding:8px 12px;display:flex;gap:12px;align-items:center;border-bottom:1px solid #444;flex-wrap:wrap}
header b{color:#fff}#msg{color:#ffb454}
button{font:inherit;padding:5px 12px;background:#444;color:#eee;border:1px solid #666;border-radius:4px;cursor:pointer}
button.on{background:#2d6cdf;border-color:#2d6cdf;color:#fff}
button:disabled{opacity:.4;cursor:default}
main{padding:10px 12px 60px;max-width:1700px;margin:0 auto}
details{background:#333;border:1px solid #444;border-radius:6px;padding:8px 12px;margin-bottom:10px}
details p,details li{line-height:1.5;margin:4px 0}
.cols{display:flex;gap:10px;align-items:flex-start}
.side{flex:0 0 24%;min-width:220px}
.side img{width:100%;display:block;background:#fff;margin-bottom:4px}
.cap{color:#999;font-size:12px;margin:2px 0 8px}
.stage{flex:1 1 0;min-width:0}
.scroll{overflow:auto;max-height:74vh;border:1px solid #555;background:#111}
.canvas{position:relative;cursor:crosshair}
.canvas img{width:100%;display:block}
.pin{position:absolute;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:#e33;color:#fff;font:bold 12px system-ui;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 0 0 1px #000;pointer-events:none}
.pin.sel{background:#2d6cdf}
.tools{display:flex;gap:8px;align-items:center;margin:6px 0}
.q{background:#333;border:1px solid #444;border-radius:6px;padding:8px 12px;margin-top:10px}
.q h3{margin:0 0 6px;font-size:14px;color:#fff}
.q .hint{color:#aaa;font-size:12px;margin:0 0 6px}
.row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:4px 0}
.pinrow{border-top:1px solid #444;padding:6px 0}
.pinrow.sel{background:#2f3a4d}
.num{display:inline-flex;width:22px;height:22px;border-radius:50%;background:#e33;color:#fff;font-weight:bold;align-items:center;justify-content:center;font-size:12px}
select,input[type=text]{font:inherit;padding:5px;background:#1e1e1e;color:#eee;border:1px solid #555;border-radius:4px}
input[type=text]{flex:1 1 200px}
label{display:inline-flex;gap:5px;align-items:center;margin-right:12px}
.need{color:#ffb454;font-size:12px}
.real{background:#fff;display:inline-block;max-width:100%;overflow:auto;margin-top:8px}.real img{display:block;max-width:none}
</style>
<header><b>Mark what's wrong</b><span id="count"></span>
<button id="prev">&larr; Back</button><button id="next">Next &rarr;</button>
<span id="where"></span><span id="saved" style="color:#7c7"></span><span id="msg"></span>
<button id="dl" style="margin-left:auto">Download marks.json</button></header>
<main>
<details id="brief" open><summary><b>What I need from you (read once)</b></summary>
<p><b>Why:</b> every number I have scores the WHOLE design as one figure. Your written reasons are about
SPOTS: a blob in the M, a wavy I, a piece that broke off. I need to know <b>where</b> you look and
<b>what</b> you call it, so I can build a reader for each kind of fault and check it against your marks.</p>
<ol>
<li><b>Grade it</b> as if a customer got it sewn exactly like this (Great / Good / Okay / Bad / Terrible).
Grade the stitching against the artwork on the left, not the artwork itself.</li>
<li><b>Click every spot that is wrong</b> on the big picture. Each click drops a numbered pin. For each pin
pick <b>what it is</b> and <b>how bad</b>: <i>Ruins it</i> = customer would reject it; <i>Noticeable</i> = you'd
want it fixed; <i>Nitpick</i> = only a digitizer would see it. Add a few words if the list doesn't say it.
If the same fault repeats (every letter is wavy), pin the 2-3 worst and say "all letters" in the note.</li>
<li>Faults with <b>no single spot</b> (can't tell what it is, wrong colors overall): tick them under the pins.</li>
<li>If nothing is worth marking, tick <b>Nothing wrong worth marking</b>.</li>
</ol>
<p><b>Ignore:</b> the picture is a drawing of the stitches, not a sew-out. It shows no fabric pull, no sheen,
and thread colors are approximate. The plain background is the garment. Zoom is for finding the spot; judge
how bad it is from the small "about actual size" picture.</p>
<p><b>Not asked:</b> left-vs-right, or what the fix is. First 11 are your pro-file logos (the pro's own file is
shown small for reference), then 18 photos, then Commons logo styles (optional, you graded those 10-28).
Stop any time: every answer saves as you go.</p>
</details>
<div class="cols">
 <div class="side">
  <img id="art" alt="artwork"><div class="cap">Artwork (what the customer sent)</div>
  <div id="probox"><img id="pro" alt="pro file"><div class="cap" id="procap"></div></div>
 </div>
 <div class="stage">
  <div class="tools"><b id="title"></b><span class="cap" id="size" style="margin:0"></span>
   <span style="margin-left:auto">Zoom</span><button data-z="1" class="z on">Fit</button><button data-z="2" class="z">2x</button><button data-z="4" class="z">4x</button></div>
  <div class="scroll" id="scroll"><div class="canvas" id="canvas"><img id="render" alt="our stitches" draggable="false"></div></div>
  <div class="cap">Our stitches. Click a spot to pin it. Click a pin's row below to highlight it.</div>
  <div class="real"><img id="real" alt="actual size"></div><div class="cap">About actual size (depends on your screen). Judge "how bad" from this one.</div>
  <div class="q"><h3>1. Grade: a customer gets this sewn exactly as shown</h3><div class="row" id="grades"></div></div>
  <div class="q"><h3>2. What is wrong, and where? <span class="cap" id="npins"></span></h3>
   <p class="hint">Click the picture to add a pin, then say what it is and how bad.</p>
   <div id="pins"></div>
   <div class="row" style="margin-top:8px"><label><input type="checkbox" id="nothing"> Nothing wrong worth marking</label></div></div>
  <div class="q"><h3>3. Problems with no single spot (tick any)</h3><div class="row" id="whole"></div></div>
  <div class="q"><h3>4. In one line: the main reason for your grade (optional)</h3>
   <div class="row"><input type="text" id="reason" maxlength="500" placeholder="e.g. the lettering is unreadable, everything else is fine"></div></div>
  <div class="row" style="margin-top:10px"><span class="need" id="need"></span><button id="next2" style="margin-left:auto">Next &rarr;</button></div>
 </div>
</div>
</main>
<script id="kit" type="application/json">__KIT__</script>
<script>
const KIT=JSON.parse(document.getElementById('kit').textContent);
const SERVED=location.protocol.startsWith('http');
const KEY='defect-marks:'+KIT.kit_sha256;
const $=id=>document.getElementById(id);
const SEV={ruins:'Ruins it',noticeable:'Noticeable',nitpick:'Nitpick'};
const GROUP={pro_logo:'your pro-file logos',photo:'photos',commons_logo:'Commons logo styles (optional)'};
let marks={}, i=0, sel=-1, zoom=1, timer=null;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function rec(){const id=KIT.items[i].id;return marks[id]||(marks[id]={grade:null,nothing_wrong:false,whole:[],reason:'',pins:[]});}
function done(r){return !!(r&&r.grade&&(r.pins.length||r.whole.length||r.nothing_wrong));}
function pinsOk(r){return r.pins.every(p=>p.what&&p.severity&&(p.what!=='other'||p.note.trim()));}
function count(){
  const n=KIT.items.filter(it=>done(marks[it.id])).length;
  $('count').textContent=n+' of '+KIT.items.length+' done';
}
function need(){
  const r=rec();let t='';
  if(!r.grade)t='Pick a grade.';
  else if(!r.pins.length&&!r.whole.length&&!r.nothing_wrong)t='Pin a spot, tick a whole-design problem, or tick "Nothing wrong".';
  else if(!pinsOk(r))t='Each pin needs a "what" and a "how bad" ("Other" needs a few words).';
  $('need').textContent=t;
}
function save(){
  need();count();
  try{localStorage.setItem(KEY,JSON.stringify(marks));}catch(e){}
  if(!SERVED){$('saved').textContent='kept in this browser';return;}
  clearTimeout(timer);const id=KIT.items[i].id, body=JSON.stringify(Object.assign({id:id},marks[id]));
  timer=setTimeout(async()=>{
    try{const r=await fetch('/mark',{method:'POST',headers:{'Content-Type':'application/json'},body:body});
      if(!r.ok)throw new Error('HTTP '+r.status);$('saved').textContent='saved';$('msg').textContent='';
    }catch(err){$('saved').textContent='';$('msg').textContent='Not saved ('+err.message+'); kept in this browser.';}
  },400);
}
function drawPins(){
  const c=$('canvas');for(const el of c.querySelectorAll('.pin'))el.remove();
  rec().pins.forEach((p,k)=>{const d=document.createElement('div');d.className='pin'+(k===sel?' sel':'');
    d.style.left=(100*p.x)+'%';d.style.top=(100*p.y)+'%';d.textContent=k+1;c.appendChild(d);});
  $('npins').textContent=rec().pins.length?'('+rec().pins.length+' pinned)':'';
}
function drawRows(){
  const r=rec(), box=$('pins');box.innerHTML='';
  r.pins.forEach((p,k)=>{
    const d=document.createElement('div');d.className='pinrow'+(k===sel?' sel':'');
    d.innerHTML='<div class="row"><span class="num">'+(k+1)+'</span><select data-f="what"><option value="">What is it?</option>'+
      Object.entries(KIT.whats).map(([v,t])=>'<option value="'+v+'"'+(p.what===v?' selected':'')+'>'+esc(t)+'</option>').join('')+'</select>'+
      KIT.severities.map(s=>'<button data-sev="'+s+'" class="'+(p.severity===s?'on':'')+'">'+SEV[s]+'</button>').join('')+
      '<input type="text" data-f="note" maxlength="300" placeholder="a few words (optional)" value="'+esc(p.note)+'">'+
      '<button data-del="1">Remove</button></div>';
    d.addEventListener('click',()=>{if(sel!==k){sel=k;drawPins();for(const x of box.children)x.classList.remove('sel');d.classList.add('sel');}});
    d.querySelector('select').addEventListener('change',e=>{p.what=e.target.value||null;save();});
    d.querySelector('input').addEventListener('input',e=>{p.note=e.target.value;save();});
    for(const b of d.querySelectorAll('[data-sev]'))b.addEventListener('click',()=>{p.severity=b.dataset.sev;drawRows();save();});
    d.querySelector('[data-del]').addEventListener('click',e=>{e.stopPropagation();r.pins.splice(k,1);sel=-1;drawPins();drawRows();save();});
    box.appendChild(d);
  });
}
function show(){
  const it=KIT.items[i], r=rec();sel=-1;
  $('art').src='img/'+it.art;$('render').src='img/'+it.render;$('real').src='img/'+it.render;
  $('real').style.width=Math.round(it.img_w/KIT_PXMM*3.78)+'px';
  $('probox').style.display=it.pro?'':'none';if(it.pro){$('pro').src='img/'+it.pro;$('procap').textContent="The pro's file for this job, drawn the same way. Reference only, don't mark it."+(it.pro_colours?'':' (This file stores no thread colors, so the colors shown are made up.)');}
  $('title').textContent=(i+1)+'. '+it.title;$('size').textContent=it.size;
  $('where').textContent=(i+1)+' / '+KIT.items.length+' · '+GROUP[it.group];
  $('grades').innerHTML=KIT.grades.map(g=>'<button data-g="'+g+'" class="'+(r.grade===g?'on':'')+'">'+g+'</button>').join('');
  for(const b of $('grades').children)b.onclick=()=>{r.grade=b.dataset.g;show0();save();};
  $('whole').innerHTML=Object.entries(KIT.whole).map(([v,t])=>'<label><input type="checkbox" data-w="'+v+'"'+(r.whole.includes(v)?' checked':'')+'> '+esc(t)+'</label>').join('');
  for(const c of $('whole').querySelectorAll('input'))c.onchange=()=>{r.whole=[...$('whole').querySelectorAll('input:checked')].map(x=>x.dataset.w);save();};
  $('nothing').checked=r.nothing_wrong;$('reason').value=r.reason;
  $('prev').disabled=i===0;$('next').disabled=$('next2').disabled=i===KIT.items.length-1;
  setZoom(1);drawPins();drawRows();need();count();$('saved').textContent='';
  window.scrollTo(0,0);
}
function show0(){const r=rec();for(const b of $('grades').children)b.classList.toggle('on',b.dataset.g===r.grade);}
function setZoom(z){zoom=z;$('canvas').style.width=(100*z)+'%';for(const b of document.querySelectorAll('.z'))b.classList.toggle('on',+b.dataset.z===z);}
const KIT_PXMM=__PXMM__;
$('canvas').addEventListener('click',e=>{
  const b=$('render').getBoundingClientRect();
  const x=(e.clientX-b.left)/b.width, y=(e.clientY-b.top)/b.height;
  if(x<0||x>1||y<0||y>1)return;
  const r=rec();r.pins.push({x:x,y:y,what:null,severity:null,note:''});r.nothing_wrong=false;$('nothing').checked=false;
  sel=r.pins.length-1;drawPins();drawRows();save();
});
for(const b of document.querySelectorAll('.z'))b.onclick=()=>setZoom(+b.dataset.z);
$('nothing').onchange=e=>{rec().nothing_wrong=e.target.checked;save();};
$('reason').oninput=e=>{rec().reason=e.target.value;save();};
function go(d){const n=i+d;if(n<0||n>=KIT.items.length)return;i=n;try{localStorage.setItem(KEY+':at',String(i));}catch(e){}show();}
$('prev').onclick=()=>go(-1);$('next').onclick=$('next2').onclick=()=>go(1);
$('dl').onclick=()=>{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify({kit_sha256:KIT.kit_sha256,items:marks},null,1)],{type:'application/json'}));
  a.download='marks.json';a.click();};
async function load(){
  try{marks=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){marks={};}
  if(SERVED){try{const r=await (await fetch('/marks')).json();Object.assign(marks,r.items||{});}catch(e){}}
  try{i=Math.min(KIT.items.length-1,Math.max(0,+(localStorage.getItem(KEY+':at')||0)));}catch(e){i=0;}
  if(Object.keys(marks).length)$('brief').open=false;
  show();window.PAGE_READY=true;
}
load();
</script>
"""


def page_html(kit: dict) -> str:
    data = json.dumps(public_kit(kit)).replace("</", "<\\/")
    return PAGE.replace("__KIT__", data).replace("__PXMM__", repr(float(kit.get("px_per_mm", PXMM))))


# ------------------------------------------------------------------ server ----

def read_marks(kit_dir: Path) -> dict:
    p = Path(kit_dir) / "marks.json"
    if not p.exists():
        return {"kit_sha256": None, "updated": None, "items": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def make_server(kit_dir, port: int = PORT, host: str = "127.0.0.1"):
    """localhost only. GET / (the page, built from kit.json WITHOUT the
    yardstick), /img/<name> for the names kit.json lists and nothing else,
    /marks; POST /mark {id, grade, pins, ...} writes `marks.json` before it
    answers."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import unquote, urlparse
    kd = Path(kit_dir)
    kit = json.loads((kd / "kit.json").read_text(encoding="utf-8"))
    page = page_html(kit).encode("utf-8")
    by_id = {it["id"]: it for it in kit["items"]}
    allowed = {n for it in kit["items"] for n in (it["art"], it["render"], it.get("pro")) if n}
    lock = threading.Lock()

    def write(data: dict) -> None:
        tmp = kd / "marks.json.tmp"
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=1, ensure_ascii=False))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, kd / "marks.json")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = unquote(urlparse(self.path).path)
            if path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif path == "/marks":
                with lock:
                    body = json.dumps(read_marks(kd)).encode("utf-8")
                self._send(200, body, "application/json")
            elif path.startswith("/img/") and path[5:] in allowed:
                name = path[5:]
                self._send(200, (kd / "img" / name).read_bytes(),
                           "image/png" if name.endswith(".png") else "image/jpeg")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/mark":
                self._send(404, b"not found", "text/plain")
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if not 0 <= n <= 65536:
                    raise ValueError
                body = json.loads(self.rfile.read(n) or b"{}")
                item = by_id[body["id"]]
                record = clean_item(body, item)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                self._send(400, b"bad mark", "text/plain")
                return
            with lock:
                data = read_marks(kd)
                record["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                data["items"][item["id"]] = record
                data["kit_sha256"] = kit["kit_sha256"]
                data["updated"] = record["ts"]
                write(data)
            self._send(200, b'{"ok": true}', "application/json")

    return ThreadingHTTPServer((host, port), Handler)


# ------------------------------------------------------------------ report ----

def report_text(kit: dict, marks: dict) -> str:
    rows = report_rows(kit, marks)
    out = [f"{len(rows)} of {len(kit['items'])} items answered. Kent's grade beside the yardstick's "
           "(preflight letter mapped A..F -> Great..Terrible); step > 0 = yardstick kinder than Kent.", ""]
    out.append("| item | Kent | yardstick (score) | step | pins (ruins) | his pins by kind | yardstick findings |")
    out.append("|---|---|---|---|---|---|---|")
    for r in rows:
        pins = ", ".join(f"{k} {v}" for k, v in sorted(r["pins"].items())) or "-"
        codes = ", ".join(f"{k} {v}" for k, v in sorted(r["codes"].items())) or "-"
        out.append(f"| {r['id']} | {r['kent']} | {r['yardstick']} ({r['yardstick_score']}) | "
                   f"{'' if r['step'] is None else format(r['step'], '+d')} | "
                   f"{sum(r['pins'].values())} ({r['ruins']}) | {pins}{'; ' + ', '.join(r['whole']) if r['whole'] else ''} | {codes} |")
    kinds: dict[str, int] = {}
    for r in rows:
        for k, v in r["pins"].items():
            kinds[k] = kinds.get(k, 0) + v
    out += ["", "Pins by kind, all items: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])) or "none")]
    return "\n".join(out)


# -------------------------------------------------------------------- main ----

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("capture-pro", help="digitize one job per pro-paired artwork, with preflight")
    cp.add_argument("--out", type=Path, required=True)
    cp.add_argument("--tree", type=Path, default=ROOT, help="the digitizer/ tree to run (default: this one)")
    cp.add_argument("--only", action="append", default=[], metavar="SLUG")
    kt = sub.add_parser("kit", help="build the marking page from finished runs")
    kt.add_argument("--out", type=Path, required=True, help="a gitignored folder, e.g. eye_pairs_out/defect-marks-1110")
    kt.add_argument("--corpus", type=Path, help="a `photo_corpus capture` run folder")
    kt.add_argument("--pro", type=Path, help="a `capture-pro` run folder")
    kt.add_argument("--photos", type=Path, help="the corpus image folder (default: this tree's)")
    sv = sub.add_parser("serve", help="serve the page on localhost; answers -> <kit>/marks.json")
    sv.add_argument("--kit", type=Path, required=True)
    sv.add_argument("--port", type=int, default=PORT)
    rp = sub.add_parser("report", help="Kent's marks beside the yardstick's reading")
    rp.add_argument("--kit", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "capture-pro":
        return capture_pro(a.out, a.tree.resolve(), tuple(a.only) or PRO_SLUGS)
    if a.cmd == "kit":
        kit = build_kit(a.out, a.corpus, a.pro, a.photos)
        print(f"{len(kit['items'])} items, {len(kit['skipped'])} skipped -> {a.out}", flush=True)
        return 0
    if a.cmd == "serve":
        srv = make_server(a.kit, port=a.port)
        print(f"http://127.0.0.1:{srv.server_address[1]}/", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    kit = json.loads((a.kit / "kit.json").read_text(encoding="utf-8"))
    sys.stdout.reconfigure(encoding="utf-8")
    print(report_text(kit, read_marks(a.kit)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
