"""logo_trial_batch: one batch of the K3 logo trial, from Commons to sheets.

WHAT IT IS FOR. The K3 logo trial (2026-11-16 on) has a cheap worker session
digitize ten public-domain logos through the Studio's own request path and
hand the foreman one sheet per logo to judge by eye. Batches 1 to 4 each
rebuilt these three steps in a scratch folder; this is batch 4's code, kept
so the next batch starts from it.

  fetch     LOGOS.json ROOT   download each logo's 960 px PNG thumbnail from
                              Wikimedia Commons, one folder per logo, and
                              record its licence. A file whose page does not
                              read Public domain is skipped and reported.
  digitize  ROOT              `tools.pro_pair.digitize(art, width_mm,
                              garment)` per logo, each in its own process so
                              one crash cannot stop the batch, then the sheet:
                              ORIGINAL ART | MAIN <short sha>, 10 px/mm, one
                              shared frame, JPEG q88.
  page      ROOT              ROOT/pub: index.html, sources.json, sheets/,
                              art/ -- the folder to publish as a PRIVATE
                              artifact.

LOGOS.json is a list of {"n": 1, "name": "nasa_meatball",
"label": "NASA insignia (meatball)", "title": "NASA logo.svg"}; `title` is
the Commons file title without "File:".

WIDTH. 100 mm when the downloaded PNG is wider than 2.5:1, else 80 mm.

WHERE THINGS GO. This repo is public: ROOT must be OUTSIDE the checkout (the
tool refuses one inside it), and no logo art or render is ever committed.
The downloads are untrusted files, so run the steps that read them isolated
and by path, from digitizer/:

  .venv/bin/python -I tools/logo_trial_batch.py fetch LOGOS.json ROOT
  .venv/bin/python -I tools/logo_trial_batch.py digitize ROOT
  .venv/bin/python -I tools/logo_trial_batch.py page ROOT --title "K3 Batch 5 Sheets"

NETWORK. A cloud session on the Default environment cannot reach Commons;
start it on (or move it to) the environment that allows
commons.wikimedia.org and upload.wikimedia.org. Commons answers about half
the requests with 429; `fetch` waits and retries, and skips a logo it
already has, so it can simply be run again.

WHAT IT DOES NOT DO. No scoring and no verdict: the foreman views every
sheet. No `extra` overrides: the request is the Studio's.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

#: Sent on every Commons request. Names no person and no project, on purpose.
USER_AGENT = "logo-digitize-test/1.0"
API = "https://commons.wikimedia.org/w/api.php"
THUMB_PX = 960
PPM = 10.0
PAD_MM = 2.0
FABRIC_BGR = (233, 236, 238)
GARMENT = "left_chest"       # digitizer_core/fabrics.py GARMENT_FABRIC
WIDE_ASPECT = 2.5
LABEL_BAR_PX = 44
TILE_GAP_PX = 24
JPEG_QUALITY = 88
PER_LOGO_TIMEOUT_S = 1500


# ------------------------------------------------------------------ pieces
def width_for(w_px: int, h_px: int) -> float:
    """The trial's width rule: 100 mm for a mark wider than 2.5:1, else 80."""
    return 100.0 if w_px / h_px > WIDE_ASPECT else 80.0


def slug_of(n: int, name: str) -> str:
    return f"{int(n):02d}_{name}"


def outside_checkout(root: Path) -> Path:
    """`root`, resolved, or SystemExit when it sits inside this checkout."""
    root = Path(root).resolve()
    repo = DIGITIZER.parent
    if root == repo or repo in root.parents:
        raise SystemExit(f"{root} is inside the checkout, and this repo is public: "
                         "logo art and renders stay outside it")
    return root


def short_sha() -> tuple[str, str]:
    """(full, short) of the checkout's HEAD: what the sheets are labelled with."""
    full = subprocess.run(["git", "rev-parse", "HEAD"], cwd=DIGITIZER, capture_output=True,
                          text=True, check=True).stdout.strip()
    return full, full[:7]


def art_tile(raw, width_mm: float):
    """The art at `width_mm` x PPM px wide, alpha composited on fabric grey,
    inside the renderer's 2 mm pad."""
    import cv2
    import numpy as np
    im = raw
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    h0, w0 = im.shape[:2]
    w = int(round(width_mm * PPM))
    h = int(round(h0 * w / w0))
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA if w < w0 else cv2.INTER_CUBIC)
    if im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = im[:, :, :3].astype(np.float32) * a + np.array(FABRIC_BGR, np.float32) * (1 - a)
        im = np.clip(im + 0.5, 0, 255).astype(np.uint8)
    pad = int(round(PAD_MM * PPM))
    return cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=FABRIC_BGR)


def sheet(art, render, sha7: str):
    """ORIGINAL ART | MAIN <sha7>: both tiles centred on one frame of the
    larger of the two sizes, same scale, no resize, a white label bar over
    each."""
    import cv2
    import numpy as np

    fw, fh = max(art.shape[1], render.shape[1]), max(art.shape[0], render.shape[0])

    def framed(im):
        canvas = np.full((fh, fw, 3), FABRIC_BGR, np.uint8)
        y, x = (fh - im.shape[0]) // 2, (fw - im.shape[1]) // 2
        canvas[y:y + im.shape[0], x:x + im.shape[1]] = im
        return canvas

    def labelled(im, text):
        bar = np.full((LABEL_BAR_PX, im.shape[1], 3), 255, np.uint8)
        cv2.putText(bar, text, (12, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
        return np.vstack([bar, im])

    gap = np.full((fh + LABEL_BAR_PX, TILE_GAP_PX, 3), 255, np.uint8)
    return np.hstack([labelled(framed(art), "ORIGINAL ART"), gap,
                      labelled(framed(render), f"MAIN {sha7}")])


# ------------------------------------------------------------------- fetch
def _get(url: str) -> bytes:
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 5:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 15 * (attempt + 1)
            print(f"   {e.code}, retry in {wait} s", flush=True)
            time.sleep(min(wait, 120))
    raise AssertionError("unreachable")


def licence_of(extmetadata: dict) -> dict:
    """The licence fields of a Commons `extmetadata` block, tags stripped,
    plus `public_domain`: License is "pd" or the short name says so."""
    def g(k):
        return re.sub(r"<[^>]+>", "", (extmetadata.get(k) or {}).get("value", "")).strip()
    lic = {k: g(k) for k in ("LicenseShortName", "License", "UsageTerms", "Categories")}
    lic["public_domain"] = (lic["License"].lower() == "pd"
                            or "public domain" in lic["LicenseShortName"].lower())
    return lic


def licence_text(lic: dict) -> str:
    tags = [c for c in lic.get("Categories", "").split("|") if c.upper().startswith("PD")]
    parts = [lic.get("LicenseShortName", ""), "License=" + lic.get("License", "")]
    if lic.get("UsageTerms") and lic["UsageTerms"] != lic.get("LicenseShortName"):
        parts.append(lic["UsageTerms"])
    if tags:
        parts.append("Commons tag: " + ", ".join(tags))
    return "; ".join(p for p in parts if p)


def cmd_fetch(args) -> int:
    root = outside_checkout(args.root)
    logos = json.loads(Path(args.logos).read_text(encoding="utf-8"))
    (root / "meta").mkdir(parents=True, exist_ok=True)
    out, skipped = [], 0
    for lg in logos:
        slug = slug_of(lg["n"], lg["name"])
        q = urllib.parse.urlencode({
            "action": "query", "prop": "imageinfo", "iiprop": "url|extmetadata",
            "iiurlwidth": THUMB_PX, "format": "json", "redirects": 1,
            "titles": "File:" + lg["title"]})
        page = next(iter(json.loads(_get(API + "?" + q))["query"]["pages"].values()))
        info = (page.get("imageinfo") or [None])[0]
        rec = {"n": lg["n"], "slug": slug, "label": lg.get("label", lg["name"]),
               "requested_title": "File:" + lg["title"], "title": page.get("title"),
               "licence": None, "public_domain": False, "descriptionurl": None, "bytes": None}
        if info is None:
            print(f"{slug}: no such file on Commons, SKIPPED")
        else:
            lic = licence_of(info["extmetadata"])
            rec.update(licence=lic, public_domain=lic["public_domain"],
                       descriptionurl=info.get("descriptionurl"))
            if lic["public_domain"]:
                png = root / "art" / slug / f"{slug}.png"
                if not png.exists():
                    png.parent.mkdir(parents=True, exist_ok=False)
                    png.write_bytes(_get(info["thumburl"]))
                rec["bytes"] = png.stat().st_size
            print(f"{slug}: {page['title']} | {lic['LicenseShortName']} | "
                  f"{'ok' if rec['bytes'] else 'NOT public domain, SKIPPED'}")
        skipped += rec["bytes"] is None
        out.append(rec)
        time.sleep(3.0)
    (root / "meta" / "fetch.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{len(out) - skipped} fetched, {skipped} skipped (take the next from the backup list)")
    return 0


# ---------------------------------------------------------------- digitize
def digitize_one(art: Path, root: Path, garment: str, sha7: str) -> dict:
    """Digitize `art`, write its sheet and stats under ROOT/out. An error is
    recorded on the row (and an ERROR tile drawn); it does not raise."""
    import cv2
    import numpy as np
    slug = art.stem
    (root / "out" / "sheets").mkdir(parents=True, exist_ok=True)
    (root / "out" / "stats").mkdir(parents=True, exist_ok=True)
    raw = cv2.imread(str(art), cv2.IMREAD_UNCHANGED)
    h0, w0 = raw.shape[:2]
    width_mm = width_for(w0, h0)
    rec = {"slug": slug, "art_px": [w0, h0], "width_mm": width_mm, "garment_id": garment,
           "stitches": None, "trims": None, "jumps": None, "size_mm": None, "blocks": None,
           "threads": None, "warnings": None, "design_class": None, "secs": None, "error": None}
    render = None
    try:
        from tools import pro_pair
        from digitizer_core.stitchviz import render_design
        d = pro_pair.digitize(art, width_mm, garment)
        st = d.plan.stats
        rec.update(
            stitches=int(st.stitch_count), trims=int(st.trims), jumps=int(st.jumps),
            size_mm=[round(float(v), 2) for v in st.size_mm], blocks=len(d.plan.blocks),
            threads=[c.get("name") or "#%02x%02x%02x" % (c.get("r", 0), c.get("g", 0), c.get("b", 0))
                     for c in d.design.get("colors", [])],
            warnings=[w.get("code") if isinstance(w, dict) else str(w)
                      for w in (getattr(d.plan, "warnings", None) or [])],
            design_class=getattr(d.result, "design_class", None), secs=round(float(d.secs), 1))
        render = render_design(d.design, px_per_mm=PPM)
    except Exception as e:  # noqa: BLE001 -- one logo erroring must not stop the batch
        rec["error"] = f"{type(e).__name__}: {e}"[:600]
        rec["traceback"] = traceback.format_exc()[-2500:]
    art_img = art_tile(raw, width_mm)
    if render is None:
        render = np.full(art_img.shape, FABRIC_BGR, np.uint8)
        cv2.putText(render, "ERROR - no render", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (0, 0, 200), 2, cv2.LINE_AA)
    cv2.imwrite(str(root / "out" / "sheets" / f"{slug}.jpg"), sheet(art_img, render, sha7),
                [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    (root / "out" / "stats" / f"{slug}.json").write_text(
        json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return rec


def cmd_digitize(args) -> int:
    root = outside_checkout(args.root)
    _full, sha7 = short_sha()
    if args.only:
        rec = digitize_one(root / "art" / args.only / f"{args.only}.png", root, args.garment, sha7)
        print(args.only, {k: rec[k] for k in ("width_mm", "stitches", "trims", "jumps", "size_mm",
                                              "blocks", "design_class", "secs", "error")}, flush=True)
        return 0
    arts = sorted((root / "art").glob("*/*.png"))
    if not arts:
        raise SystemExit(f"no art under {root / 'art'}: run fetch first")
    crashed = 0
    for art in arts:
        # one process per logo: a native crash or a hang costs that logo only
        cmd = [sys.executable, "-I", str(Path(__file__).resolve()), "digitize", str(root),
               "--only", art.stem, "--garment", args.garment]
        try:
            code = subprocess.run(cmd, timeout=PER_LOGO_TIMEOUT_S).returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        if code != 0:
            crashed += 1
            print(f"{art.stem}: process ended {code}, no sheet", flush=True)
    print(f"{len(arts) - crashed} of {len(arts)} digitized at {sha7}")
    return 0


# -------------------------------------------------------------------- page
_PAGE_CSS = """
:root { --bg:#f3f4f6; --panel:#ffffff; --fg:#16191d; --mute:#5a626d; --line:#d5d9df; --accent:#1f5fae; --err:#b3261e;
  --sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#14171b; --panel:#1d2126; --fg:#e7eaee; --mute:#9aa3ae; --line:#333a43; --accent:#7fb2f0; --err:#ff8a80; color-scheme: dark } }
:root[data-theme="dark"] { --bg:#14171b; --panel:#1d2126; --fg:#e7eaee; --mute:#9aa3ae; --line:#333a43; --accent:#7fb2f0; --err:#ff8a80; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font: 14px/1.5 var(--sans); padding-block: 24px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
main { max-width: 1500px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }
h1 { font-size: 22px; margin: 0; }
.meta { color: var(--mute); margin: 4px 0 0; overflow-wrap: anywhere; }
code { font-family: var(--mono); font-size: 0.92em; }
section { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; min-width: 0; }
h2 { font-size: 16px; margin: 0; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
h2 .n { font-family: var(--mono); color: var(--mute); }
h2 .w { font-weight: 400; font-size: 13px; color: var(--mute); }
.stats { margin: 4px 0 10px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.err { color: var(--err); font-weight: 700; }
section img { display: block; width: 100%; height: auto; border: 1px solid var(--line); }
.src { margin: 8px 0 0; font-size: 12px; color: var(--mute); overflow-wrap: anywhere; }
a { color: var(--accent); }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
"""


def stats_line(rec: dict) -> str:
    """One logo's stats as the page's single HTML line."""
    e = html.escape
    if rec["error"]:
        return f'<span class="err">ERROR</span> {e(rec["error"])}'
    w, h = rec["size_mm"]
    line = (f'{rec["stitches"]:,} stitches · {rec["trims"]} trims · {rec["jumps"]} jumps · '
            f'{w:g} × {h:g} mm · {rec["blocks"]} block{"s" if rec["blocks"] != 1 else ""} · '
            f'class {e(str(rec["design_class"]))} · {rec["secs"]:g} s')
    if rec["threads"]:
        line += " · threads: " + e(", ".join(rec["threads"]))
    return line + " · warnings: " + (e(", ".join(rec["warnings"])) if rec["warnings"] else "none")


def cmd_page(args) -> int:
    root = outside_checkout(args.root)
    full, _sha7 = short_sha()
    pub = root / "pub"
    (pub / "sheets").mkdir(parents=True, exist_ok=True)
    (pub / "art").mkdir(parents=True, exist_ok=True)
    fetched = json.loads((root / "meta" / "fetch.json").read_text(encoding="utf-8"))
    e = html.escape
    logos, sections = [], []
    for f in fetched:
        slug = f["slug"]
        stats = root / "out" / "stats" / f"{slug}.json"
        if not f.get("bytes") or not stats.exists():
            continue
        st = json.loads(stats.read_text(encoding="utf-8"))
        shutil.copyfile(root / "out" / "sheets" / f"{slug}.jpg", pub / "sheets" / f"{slug}.jpg")
        shutil.copyfile(root / "art" / slug / f"{slug}.png", pub / "art" / f"{slug}.png")
        rec = {"n": f["n"], "logo": f["label"], "slug": slug, "commons_title": f["title"],
               "commons_page": f["descriptionurl"], "licence": licence_text(f["licence"]),
               **{k: st[k] for k in ("width_mm", "garment_id", "stitches", "trims", "jumps", "size_mm",
                                     "blocks", "threads", "warnings", "design_class", "secs", "error")},
               "art": f"art/{slug}.png", "sheet": f"sheets/{slug}.jpg"}
        logos.append(rec)
        sections.append(
            f'<section>\n<h2><span class="n">{rec["n"]:02d}</span> {e(rec["logo"])} '
            f'<span class="w">{rec["width_mm"]:g} mm · {e(rec["garment_id"])}</span></h2>\n'
            f'<p class="stats">{stats_line(rec)}</p>\n'
            f'<a href="{rec["sheet"]}"><img src="{rec["sheet"]}" '
            f'alt="{e(rec["logo"])}: original art beside the render" loading="lazy"></a>\n'
            f'<p class="src">{e(rec["commons_title"])} · {e(rec["licence"])} · '
            f'<a href="{rec["art"]}">{rec["art"]}</a></p>\n</section>')
    (pub / "sources.json").write_text(json.dumps({
        "batch": args.title, "git_sha": full,
        "request_path": "tools.pro_pair.digitize(art, width_mm, garment_id), no extra overrides",
        "render": "digitizer_core.stitchviz.render_design(design, px_per_mm=10.0)",
        "width_rule": "100 mm when the downloaded PNG is wider than 2.5:1, else 80 mm",
        "art_source": "Wikimedia Commons 960 px PNG thumbnail (iiurlwidth=960)",
        "logos": logos}, indent=1), encoding="utf-8")
    title = e(args.title)
    (pub / "index.html").write_text(
        f'<title>{title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        f'<style>{_PAGE_CSS}</style>\n<main>\n<header>\n<h1>{title}</h1>\n'
        f'<p class="meta">{len(logos)} public-domain logos digitized on <code>main</code> at '
        f'<code>{full}</code> through <code>tools.pro_pair.digitize</code>, no overrides. Each sheet '
        'is the original art beside the render at 10 px/mm on one shared frame; select a sheet to '
        'open it at full resolution. Files: <a href="sources.json">sources.json</a>, '
        '<code>sheets/NN_name.jpg</code>, <code>art/NN_name.png</code>.</p>\n</header>\n'
        + "\n".join(sections) + "\n</main>\n", encoding="utf-8")
    print(f"wrote {pub}: {len(logos)} logos")
    return 0


# --------------------------------------------------------------------- cli
def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="logo_trial_batch", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download the batch's PNGs from Commons")
    f.add_argument("logos", help="LOGOS.json")
    f.add_argument("root", help="batch folder, outside the checkout")
    f.set_defaults(fn=cmd_fetch)
    d = sub.add_parser("digitize", help="digitize every fetched logo and write its sheet")
    d.add_argument("root")
    d.add_argument("--garment", default=GARMENT)
    d.add_argument("--only", metavar="SLUG", help="one logo, in this process")
    d.set_defaults(fn=cmd_digitize)
    p = sub.add_parser("page", help="assemble ROOT/pub for a private artifact")
    p.add_argument("root")
    p.add_argument("--title", required=True, help='the artifact title, e.g. "K3 Batch 5 Sheets"')
    p.set_defaults(fn=cmd_page)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
