#!/usr/bin/env python
"""The cross-genre Commons corpus and its side-by-side scorecard.

Kent, 2026-10-27, after the 18-genre photo census: "it's as if this digitize
was only building tools to improve the photos we had on hand. This digitizer
needs to be building tools that help and improve ALL photos." Asked what he
wants to look at to judge a photo PR: "Sxs comparison w/ an Artifact that I
can say better or worse." Spec: docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md.

Four commands, run from `digitizer/` as `python -m tools.photo_corpus ...`:

    fetch                      testdata/photo/corpus/corpus.json -> <slug>.jpg + manifest.json
                               (Commons API by title; the LIVE licence is re-read and a row
                               whose licence left the allowed set is refused, not downloaded)
    capture --label L [--base REF | --tree DIR]
                               every row digitized with the Studio's own request (80 mm,
                               left_chest) in its own process, cwd = the tree under test, so
                               `--base origin/main` runs the merge-base's digitizer_core;
                               writes corpus_runs/L/<slug>.json|.png|.row.json + run.json
    sxs --before DIR --after DIR
                               one self-contained HTML: source thumbnail, before render, after
                               render, the numbers under both, better / same / worse buttons;
                               "Export verdicts" downloads the JSON `tally` files
    tally VERDICTS.json        copies the verdicts under docs/scoreboards/photo-corpus/ and
                               appends one tally line per before/after pair

All numbers are instrument readings, not quality claims (ROADMAP gate 4). The
verdict column is Kent's. Nothing downloaded or rendered is ever committed:
this repo is public.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
TESTDATA = DIGITIZER / "testdata"
CORPUS_DIR = TESTDATA / "photo" / "corpus"
CORPUS_JSON = CORPUS_DIR / "corpus.json"
RUNS_DIR = DIGITIZER / "corpus_runs"
SCOREBOARD_DIR = DIGITIZER.parent / "docs" / "scoreboards" / "photo-corpus"

#: The fixed line every page and tally carries.
GATE4_LINE = ("All numbers are instrument readings, not quality claims (ROADMAP gate 4). "
              "The verdict column is Kent's.")

#: Commons `LicenseShortName` substrings a public repo may list (lower-cased match).
OK_LICENCES = ("cc0", "public domain", "pd", "cc by 4.0", "cc by 3.0", "cc by 2.0",
               "cc by-sa 4.0", "cc by-sa 3.0", "cc by-sa 2.0")

ROW_KEYS = ("slug", "kind", "genre", "title", "page", "author", "licence")


def licence_ok(short_name: str) -> bool:
    """Lower-cased substring match against OK_LICENCES; empty is never ok."""
    s = (short_name or "").lower()
    return bool(s) and any(k in s for k in OK_LICENCES)


def load_corpus(path: Path = CORPUS_JSON) -> list[dict]:
    """The committed rows. Raises ValueError on a missing key or a repeated slug."""
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    seen: set[str] = set()
    for r in rows:
        missing = [k for k in ROW_KEYS if k not in r]
        if missing:
            raise ValueError(f"corpus row {r.get('slug')!r} lacks {missing}")
        if r["slug"] in seen:
            raise ValueError(f"corpus slug repeated: {r['slug']!r}")
        seen.add(r["slug"])
    return rows


# ------------------------------------------------------------------ fetch
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "EMB-Bot-corpus/1.0 (https://github.com/KS-Three/EMB-Bot)"
THUMB_WIDTH = 1600
OK_MIMES = ("image/jpeg", "image/png")


def _retry(fn, tries: int = 6, sleep=time.sleep):
    """Call `fn` up to `tries` times, sleeping 1, 2, 4... s between. The Commons
    API answered 503 on 17 of 18 titles on 2026-10-27, then on 1 of 4 identical
    probes a minute later, with either user agent: transient on their side, so
    a patient retry (63 s over six tries) is the fix, and `fetch` is resumable."""
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            sleep(2 ** i)


def _http_json(params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{COMMONS_API}?{q}", headers={"User-Agent": USER_AGENT})

    def go():
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    return _retry(go)


def _http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    def go():
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    return _retry(go)


def commons_imageinfo(title: str, get=_http_json) -> dict:
    """Commons `imageinfo` for one `File:` title: url, thumburl (THUMB_WIDTH), size,
    mime, descriptionurl, extmetadata. {} when the title is unknown."""
    data = get({"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata", "iiurlwidth": THUMB_WIDTH})
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = page.get("imageinfo") or []
        if info:
            return info[0]
    return {}


def strip_html(s: str) -> str:
    """Commons `Artist` is HTML; the attribution line wants the text. Empty -> a
    pointer to the page, which carries the author anyway."""
    text = _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
    return text or "see Commons page"


def fetch(rows: list[dict], out: Path, get=_http_json, download=_http_bytes) -> dict:
    """Download every row's image as `<slug>.jpg` and write `manifest.json` beside
    them. The LIVE licence is read from the API and must still be in OK_LICENCES,
    else the row is skipped with the reason (a licence can change after it was
    listed; a public repo cannot carry what Commons no longer grants). Rows
    already on disk with a manifest entry are skipped as "cached".
    -> {"fetched": [slug...], "skipped": {slug: reason}}"""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    fetched: list[str] = []
    skipped: dict[str, str] = {}
    live = download is _http_bytes
    for r in rows:
        slug, dest = r["slug"], out / f"{r['slug']}.jpg"
        if slug in manifest and dest.exists():
            skipped[slug] = "cached"
            continue
        try:
            info = commons_imageinfo(r["title"], get)
        except Exception as e:  # network / API
            skipped[slug] = f"api: {e!r}"[:200]
            continue
        if not info:
            skipped[slug] = "title not found on Commons"
            continue
        meta = info.get("extmetadata") or {}
        licence = ((meta.get("LicenseShortName") or {}).get("value") or "").lower()
        if not licence_ok(licence):
            skipped[slug] = f"licence now {licence!r}, not in the allowed set; not downloaded"
            continue
        if info.get("mime") not in OK_MIMES:
            skipped[slug] = f"mime {info.get('mime')!r}"
            continue
        url = info.get("thumburl") or info["url"]
        try:
            data = download(url)
        except Exception as e:
            skipped[slug] = f"download: {e!r}"[:200]
            continue
        dest.write_bytes(data)
        manifest[slug] = {
            "title": r["title"], "page": info.get("descriptionurl") or r["page"], "file_url": url,
            "author": strip_html((meta.get("Artist") or {}).get("value") or ""),
            "licence": licence, "orig_size": [info.get("width"), info.get("height")],
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
        fetched.append(slug)
        print(f"{slug}: {r['title'][:70]} | {licence} | {len(data) // 1024} KB", flush=True)
        if live:
            time.sleep(0.5)
    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    for slug, why in skipped.items():
        if why != "cached":
            print(f"{slug}: SKIPPED {why}", flush=True)
    return {"fetched": fetched, "skipped": skipped}


# ------------------------------------------------------------------ row numbers
PXMM = 8.0      # render scale, px per mm (the census's)
PAD_MM = 2.0    # stitchviz.render_design's default pad
PHOTO_CLASSES = ("photo_subject", "photo_scene")   # mirrors digitizer_core.config.PHOTO_CLASSES


def fidelity(photo_bgr, render_bgr, fabric_bgr) -> dict:
    """Instrument readings between the photo and the render (not quality claims):
    `ssim` (luminance SSIM, photo resized to the render's frame inside the pad),
    `dE` (mean CIE76 in OpenCV Lab, scaled 100/255), `ssim_null` (the photo
    against a frame of plain fabric, the same shape) and the chance-corrected
    `fidelity_cc = (ssim - ssim_null) / (1 - ssim_null)`: 1 when the render IS the
    photo, 0 when it is bare fabric, None when the null leaves no room."""
    import cv2
    import numpy as np
    from skimage.metrics import structural_similarity

    pad = int(round(PAD_MM * PXMM))
    r = render_bgr[pad:-pad, pad:-pad] if min(render_bgr.shape[:2]) > 2 * pad + 6 else render_bgr
    im = cv2.resize(photo_bgr, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
    g_photo = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    g_render = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
    null = np.full_like(r, fabric_bgr)
    g_null = cv2.cvtColor(null, cv2.COLOR_BGR2GRAY)
    win = min(7, (min(g_photo.shape) // 2) * 2 - 1)
    ssim = float(structural_similarity(g_photo, g_render, data_range=255, win_size=win))
    ssim_null = float(structural_similarity(g_photo, g_null, data_range=255, win_size=win))
    l1 = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    l2 = cv2.cvtColor(r, cv2.COLOR_BGR2LAB).astype(np.float32)
    de = float(np.sqrt(((l1 - l2) ** 2).sum(axis=2)).mean()) * (100 / 255)
    room = 1.0 - ssim_null
    cc = (ssim - ssim_null) / room if room > 1e-6 else None
    return {"ssim": round(ssim, 4), "dE": round(de, 2), "ssim_null": round(ssim_null, 4),
            "fidelity_cc": None if cc is None else round(cc, 4)}


def summarise(output: dict, cap: int) -> dict:
    """The row's instrument numbers from one worker output (`state, stats,
    warnings, preflight, design, _meta`). A non-done row carries its state,
    wall time and error, every count None."""
    meta = output.get("_meta") or {}
    row = {"state": output.get("state"), "wall_s": meta.get("elapsed_s"),
           "stamps": meta.get("stamps") or {}, "class": meta.get("class"),
           "class_conf": meta.get("class_conf"), "error": output.get("error") or output.get("stderr_tail"),
           "route": None, "cutout_removed_frac": None, "stitches": None, "trims": None,
           "color_changes": None, "colors_used": None, "cap": cap, "cap_kept": None,
           "size_mm": None, "st_per_cm2": None, "grade": None, "score_raw": None}
    if output.get("state") != "done":
        return row
    stats = output.get("stats") or {}
    design = output.get("design") or {}
    pf = output.get("preflight") or {}
    codes = {w.get("code") for w in (output.get("warnings") or [])}
    if "FACE_ROUTED_FLAT" in codes:
        route = "faces_flat"
    elif row["class"] in PHOTO_CLASSES:
        route = "photo"
    else:
        route = "graphic"
    cut = next((w for w in output.get("warnings") or [] if w.get("code") == "PHOTO_BACKGROUND_REMOVED"), None)
    if cut and cut.get("background_frac_after") is not None and cut.get("background_frac_before") is not None:
        row["cutout_removed_frac"] = round(cut["background_frac_after"] - cut["background_frac_before"], 4)
    w, h = (stats.get("size_mm") or [0, 0])[:2]
    area_cm2 = (w or 0) * (h or 0) / 100.0
    stitches = stats.get("stitch_count")
    colors_used = len(design.get("colors") or [])
    row.update({
        "route": route, "stitches": stitches, "trims": stats.get("trims"),
        "color_changes": stats.get("color_changes"), "colors_used": colors_used,
        "cap_kept": colors_used <= cap, "size_mm": [round(w or 0, 1), round(h or 0, 1)],
        "st_per_cm2": round(stitches / area_cm2, 2) if stitches is not None and area_cm2 > 0 else None,
        "grade": pf.get("grade"), "score_raw": (pf.get("metrics") or {}).get("raw_score", pf.get("score")),
    })
    return row


# ------------------------------------------------------------------ CLI
def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m tools.photo_corpus",
                                 description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download the corpus images + manifest.json")
    f.add_argument("--out", type=Path, default=CORPUS_DIR)
    f.add_argument("--only", action="append", default=[], metavar="SLUG")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        rows = load_corpus()
        if a.only:
            rows = [r for r in rows if r["slug"] in a.only]
        res = fetch(rows, a.out)
        print(f"fetched {len(res['fetched'])}, skipped {len(res['skipped'])}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
