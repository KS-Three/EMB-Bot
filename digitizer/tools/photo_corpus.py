#!/usr/bin/env python
"""The cross-genre Commons corpus and its side-by-side scorecard.

Kent, 2026-10-27, after the 18-genre photo census: "it's as if this digitize
was only building tools to improve the photos we had on hand. This digitizer
needs to be building tools that help and improve ALL photos." Asked what he
wants to look at to judge a photo PR: "Sxs comparison w/ an Artifact that I
can say better or worse." Spec: docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md.

Five commands, run from `digitizer/` as `python -m tools.photo_corpus ...`:

    fetch                      testdata/photo/corpus/corpus.json -> <slug>.jpg|.png + manifest.json
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
    summary RUN_DIR            the run's numbers without designs or images ->
                               docs/scoreboards/photo-corpus/baseline-<sha7>.json

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
from typing import TYPE_CHECKING

if TYPE_CHECKING:   # the annotation below; numpy itself is imported where used
    import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
TESTDATA = DIGITIZER / "testdata"
CORPUS_DIR = TESTDATA / "photo" / "corpus"
CORPUS_JSON = CORPUS_DIR / "corpus.json"
RUNS_DIR = DIGITIZER / "corpus_runs"
SCOREBOARD_DIR = DIGITIZER.parent / "docs" / "scoreboards" / "photo-corpus"

#: The fixed line every page and tally carries.
GATE4_LINE = ("All numbers are instrument readings, not quality claims (ROADMAP gate 4). "
              "The verdict column is Kent's.")

#: What the one chance-corrected figure is corrected against.
CC_NULL_LINE = ("fidelity cc = (SSIM(photo, render) − SSIM(photo, blank fabric)) / (1 − SSIM(photo, blank fabric)): "
                "0 = the render agrees with the photo exactly as much as bare fabric does, negative = less, "
                "None when the design is empty.")

#: `wall s` is a load reading, not an engine one: two digitizes at once on
#: Kent's laptop each took 4.1x the time one alone did, same md5 (2026-10-29).
WALL_LINE = ("wall s is load-sensitive: it was taken with that many processes at once, beside whatever else "
             "the machine ran; two concurrent digitizes measured 4.1x one alone. Time a row at --procs 1 on a quiet box.")

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
EXT_BY_MIME = {"image/jpeg": ".jpg", "image/png": ".png"}


def photo_path(photos: Path, slug: str) -> Path | None:
    """`<slug>.png` or `<slug>.jpg` under `photos`, whichever exists (logo rows
    are mostly PNG, photo rows JPEG; the extension follows the Commons mime)."""
    for ext in (".png", ".jpg"):
        p = Path(photos) / f"{slug}{ext}"
        if p.exists():
            return p
    return None


def load_photo(path: Path, fabric_bgr) -> "np.ndarray | None":
    """BGR pixels with any alpha composited onto the fabric colour, so a
    transparent logo is compared against what the garment would show, not
    against the black cv2.imread() would put behind it."""
    import cv2
    import numpy as np
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        a = img[:, :, 3:4].astype(np.float32) / 255.0
        fabric = np.array(fabric_bgr, np.float32).reshape(1, 1, 3)
        return (img[:, :, :3].astype(np.float32) * a + fabric * (1 - a)).round().astype(np.uint8)
    return img[:, :, :3]


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
    """Download every row's image as `<slug>.jpg|.png` (by mime) and write `manifest.json` beside
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
        slug = r["slug"]
        if slug in manifest and photo_path(out, slug) is not None:
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
        dest = out / f"{slug}{EXT_BY_MIME[info['mime']]}"
        dest.write_bytes(data)
        manifest[slug] = {
            "file": dest.name, "title": r["title"], "page": info.get("descriptionurl") or r["page"], "file_url": url,
            "author": strip_html((meta.get("Artist") or {}).get("value") or ""),
            "licence": licence, "orig_size": [info.get("width"), info.get("height")],
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
        fetched.append(slug)
        # written per row: a crash on the next row must not lose this one
        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
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


def distinct_threads(colors: list) -> set:
    """The distinct thread colours in a design's `colors` list. That list is
    the colour-BLOCK sequence — one entry per colour change, so a thread the
    design returns to appears again — not the thread list; architecture on
    main (2026-10-27) had 14 blocks over 6 threads. Entries are {r,g,b,...}
    dicts or [r,g,b] lists."""
    out = set()
    for c in colors:
        if isinstance(c, dict):
            out.add((c.get("r"), c.get("g"), c.get("b")))
        else:
            out.add(tuple(c[:3]))
    return out


def summarise(output: dict, cap: int) -> dict:
    """The row's instrument numbers from one worker output (`state, stats,
    warnings, preflight, design, _meta`). A non-done row carries its state,
    wall time and error, every count None."""
    meta = output.get("_meta") or {}
    row = {"state": output.get("state"), "wall_s": meta.get("elapsed_s"),
           "stamps": meta.get("stamps") or {}, "class": meta.get("class"),
           "class_conf": meta.get("class_conf"), "error": output.get("error") or output.get("stderr_tail"),
           "route": None, "cutout_removed_frac": None, "cutout_refused_kept_frac": None,
           "stitches": None, "trims": None,
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
    # the cut-out ran, kept under cfg.photo_cutout_min_kept of stage 1's artwork and was
    # refused (#1179): the share it kept, the reading the refusal was made on
    kept = next((w for w in output.get("warnings") or [] if w.get("code") == "PHOTO_CUTOUT_REFUSED"), None)
    if kept and kept.get("kept_frac") is not None:
        row["cutout_refused_kept_frac"] = kept["kept_frac"]
    w, h = (stats.get("size_mm") or [0, 0])[:2]
    area_cm2 = (w or 0) * (h or 0) / 100.0
    stitches = stats.get("stitch_count")
    colors_used = len(distinct_threads(design.get("colors") or []))
    row.update({
        "route": route, "stitches": stitches, "trims": stats.get("trims"),
        "color_changes": stats.get("color_changes"), "colors_used": colors_used,
        "cap_kept": colors_used <= cap, "size_mm": [round(w or 0, 1), round(h or 0, 1)],
        "st_per_cm2": round(stitches / area_cm2, 2) if stitches is not None and area_cm2 > 0 else None,
        "grade": pf.get("grade"), "score_raw": (pf.get("metrics") or {}).get("raw_score", pf.get("score")),
    })
    return row


# ------------------------------------------------------------------ capture
TIMEOUT_S = 1200.0
PROCS = 2
WIDTH_MM = 80.0
GARMENT = "left_chest"

#: One digitize, the service's own call sequence, in its own process. argv[1] is a
#: json spec {photo, out, config, tree}; `tree` goes first on sys.path so the
#: merge-base's digitizer_core is the one imported under `--base`. faulthandler
#: dumps every thread's stack to stderr every 120 s, so a killed row still says
#: which stage it was in (the census's trick).
WORKER = r'''
import faulthandler, json, sys, time
faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
spec = json.loads(sys.argv[1])
sys.path.insert(0, spec["tree"])
from digitizer_core import PipelineConfig
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.adapter import plan_to_design
from digitizer_core.preflight import run_preflight
from digitizer_core.stage0_classify import classify
from digitizer_service.app import _decode, _parse_config, _stats_payload
data = open(spec["photo"], "rb").read()
t0 = time.time(); stamps = {}
cfg = PipelineConfig(**_parse_config(json.dumps(spec["config"])))
pixels = _decode(data); stamps["decode"] = round(time.time() - t0, 1)
cls = classify(pixels, cfg, forced_class=cfg.forced_class); stamps["classify"] = round(time.time() - t0, 1)
gen = build_generation(pixels, cfg, exif_source=data); stamps["build_generation"] = round(time.time() - t0, 1)
result = finish_generation(gen.fork(), cfg); stamps["finish_generation"] = round(time.time() - t0, 1)
plan = plan_stitches(result, cfg); stamps["plan_stitches"] = round(time.time() - t0, 1)
design = plan_to_design(plan, name="Digitized design")
pf = run_preflight(result, plan, cfg, image=pixels) if cfg.preflight else None
stamps["preflight"] = round(time.time() - t0, 1)
json.dump({"state": "done", "design": design,
           "stats": _stats_payload(plan, design, {r.shape_id for r in result.regions}),
           "warnings": plan.warnings, "preflight": pf,
           "_meta": {"elapsed_s": round(time.time() - t0, 1), "stamps": stamps,
                     "class": gen.classification_class, "class_conf": round(float(cls.confidence), 3),
                     "config_sent": spec["config"], "tree_sha": spec.get("tree_sha")}},
          open(spec["out"], "w", encoding="utf-8"))
'''


def request_config() -> dict:
    """The Studio's own /digitize config at WIDTH_MM on GARMENT (the request
    contract fixture, `tools.fremont_triage.studio_request`), as the census ran."""
    from tools.fremont_triage import studio_request
    req = studio_request(WIDTH_MM)
    req["target_width_mm"] = WIDTH_MM
    req["garment_id"] = GARMENT
    return req


TREE_REQUEST = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from tools.fremont_triage import studio_request
req = studio_request(float(sys.argv[2]))
req["target_width_mm"] = float(sys.argv[2])
req["garment_id"] = sys.argv[3]
print(json.dumps(req))
'''


def tree_request(tree: Path, fallback: dict) -> dict:
    """The Studio request THE TREE UNDER TEST builds (its own
    `tools.fremont_triage.studio_request` at WIDTH_MM on GARMENT), so a base
    run sends the base's contract, not HEAD's: a PR that adds a request field
    would otherwise error every base row, and one that changes a value would
    hide the change. `fallback` when the tree cannot build one."""
    import os
    import subprocess
    import sys
    try:
        out = subprocess.run([sys.executable, "-c", TREE_REQUEST, str(tree), str(WIDTH_MM), GARMENT],
                             cwd=str(tree), capture_output=True, text=True, timeout=120,
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if out.returncode == 0:
            return json.loads(out.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        pass
    return fallback


def run_row(tree: Path, photo: Path, out: Path, cfg: dict, timeout: float = TIMEOUT_S,
            tree_sha: str | None = None) -> dict:
    """One row in its own process, cwd = `tree`. Writes `out` itself on timeout or
    error (`state`, `rc`, `stderr_tail`) so every row has a json, stamped with
    `tree_sha` in `_meta`. -> that json."""
    import os
    import subprocess
    import sys
    from tools.default_path_diff import RUNNER_ENV

    spec = {"photo": str(photo), "out": str(out), "config": cfg, "tree": str(tree), "tree_sha": tree_sha}
    err_path = Path(out).with_suffix(".stderr.txt")
    t0 = time.time()
    with open(err_path, "w", encoding="utf-8") as ef:
        proc = subprocess.Popen([sys.executable, "-c", WORKER, json.dumps(spec)], cwd=str(tree),
                                stdout=subprocess.DEVNULL, stderr=ef, env={**RUNNER_ENV, **os.environ})
        try:
            rc = proc.wait(timeout=timeout)
            state = "done" if rc == 0 and Path(out).exists() else "error"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            rc, state = None, "timeout"
    if state != "done":
        tail = err_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
        Path(out).write_text(json.dumps({"state": state, "rc": rc, "stderr_tail": " | ".join(tail)[:400],
                                         "_meta": {"elapsed_s": round(time.time() - t0, 1),
                                                   "photo": Path(photo).name, "tree_sha": tree_sha}}),
                              encoding="utf-8")
    return json.loads(Path(out).read_text(encoding="utf-8"))


def _placeholder_png(path: Path, text: str, fabric_bgr) -> None:
    import cv2
    import numpy as np
    img = np.full((160, 480, 3), fabric_bgr, np.uint8)
    cv2.putText(img, text[:40], (12, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 40, 40), 2)
    cv2.imwrite(str(path), img)


def _render_row(photo: Path, output: dict, png: Path, fabric_bgr) -> dict:
    """Write the row's render (or a placeholder) and return its fidelity numbers."""
    import cv2
    from digitizer_core.stitchviz import render_design
    if output.get("state") != "done":
        _placeholder_png(png, output.get("state", "error"), fabric_bgr)
        return {}
    render = render_design(output["design"], px_per_mm=PXMM, fabric_bgr=fabric_bgr)
    cv2.imwrite(str(png), render)
    if not (output.get("stats") or {}).get("stitch_count"):
        # an empty design renders as the 8x8 frame and would score cc 0.0,
        # above most real rows (review 2026-10-28): no number, not a flattering one
        return {"ssim": None, "dE": None, "ssim_null": None, "fidelity_cc": None}
    photo_bgr = load_photo(photo, fabric_bgr)
    if photo_bgr is None:
        return {}
    return fidelity(photo_bgr, render, fabric_bgr)


def parse_sets(sets: list[str]) -> dict:
    """`--set FIELD=JSON` pairs -> {field: value}; a value that is not JSON is
    taken as a string. Raises ValueError on a pair with no `=`."""
    out: dict = {}
    for s in sets or []:
        if "=" not in s:
            raise ValueError(f"--set needs FIELD=JSON, got {s!r}")
        key, raw = s.split("=", 1)
        try:
            out[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            out[key.strip()] = raw
    return out


def capture(rows: list[dict], photos: Path, tree: Path, out: Path, tree_sha: str,
            timeout: float = TIMEOUT_S, procs: int = PROCS, cfg: dict | None = None,
            overrides: dict | None = None) -> dict:
    """Every row digitized at `tree`, `procs` at a time. Per row: `<slug>.json`
    (the worker's output), `<slug>.png` (render, or a placeholder naming the
    failure), `<slug>.row.json` (summarise + fidelity + the corpus row's kind
    and genre). `out/run.json` = {tree_sha, date, config, timeout_s, procs,
    rows}. A row whose `.row.json` exists is kept (resume); one whose `<slug>.json`
    exists is re-summarised from it without re-running the worker. Every row
    carries `tree_sha`; a folder holding another tree's rows is refused, so a
    reused `--label` can never present one tree's renders under another's sha.
    `cfg` defaults to the request THE TREE builds (`tree_request`)."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import date
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = {**(cfg or tree_request(tree, request_config())), **(overrides or {})}
    fabric = tuple(reversed(cfg.get("garment_rgb") or [235, 232, 223]))

    prior = out / "run.json"
    folder_sha = json.loads(prior.read_text(encoding="utf-8")).get("tree_sha") if prior.exists() else None

    def refuse(found, what):
        raise SystemExit(f"{out} holds {what} from tree {str(found)[:8]}, this capture is tree "
                         f"{tree_sha[:8]}: use another --label, or delete the folder to recapture")
    cap = int(cfg.get("max_colors") or 6)

    def one(row: dict) -> tuple[str, dict]:
        slug = row["slug"]
        row_json = out / f"{slug}.row.json"
        if row_json.exists():
            kept = json.loads(row_json.read_text(encoding="utf-8"))
            if kept.get("tree_sha") != tree_sha:
                refuse(kept.get("tree_sha"), f"{slug}.row.json")
            return slug, kept
        photo = photo_path(photos, slug)
        worker_json = out / f"{slug}.json"
        if worker_json.exists():
            # the worker's output is the slow, raw record; the summary is
            # derived from it, so an instrument fix re-reads rather than re-runs.
            # A stamped output must be this tree's; an unstamped one (captured
            # before the stamp existed) is judged by the folder's run.json —
            # on 2026-10-28 a moved merge-base re-summarised 5ff48c56's
            # outputs under 5a3181dc because an unstamped one was trusted.
            output = json.loads(worker_json.read_text(encoding="utf-8"))
            stamped = (output.get("_meta") or {}).get("tree_sha")
            if stamped is None:
                stamped = folder_sha
            if stamped is not None and stamped != tree_sha:
                refuse(stamped, f"{slug}.json")
        elif photo is not None:
            output = run_row(tree, photo, worker_json, cfg, timeout, tree_sha)
        else:
            output = {"state": "error", "error": f"no image: {slug}.jpg|.png (run fetch)",
                      "_meta": {"elapsed_s": 0.0}}
            (out / f"{slug}.json").write_text(json.dumps(output), encoding="utf-8")
        summary = summarise(output, cap)
        summary.update(_render_row(photo, output, out / f"{slug}.png", fabric))
        summary.update({"slug": slug, "kind": row["kind"], "genre": row["genre"], "tree_sha": tree_sha})
        row_json.write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print(f"{slug}: {summary['state']} {summary['wall_s']}s stitches={summary['stitches']} "
              f"trims={summary['trims']} colors={summary['colors_used']}/{cap} grade={summary['grade']} "
              f"cc={summary.get('fidelity_cc')}", flush=True)
        return slug, summary

    with ThreadPoolExecutor(max_workers=max(1, procs)) as pool:
        results = dict(pool.map(one, rows))
    run = {"tree_sha": tree_sha, "date": date.today().isoformat(), "config": cfg,
           "timeout_s": timeout, "procs": procs, "rows": {r["slug"]: results[r["slug"]] for r in rows}}
    (out / "run.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    return run


def _head_sha(tree: Path) -> str:
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tree), capture_output=True,
                          text=True).stdout.strip() or "unknown"


# ------------------------------------------------------------------ sxs
#: Row numbers shown under the renders, in order: (key, label, lower-is-better or None).
SXS_METRICS = (
    ("state", "state", None), ("class", "class", None), ("route", "route", None),
    ("stitches", "stitches", True), ("trims", "trims", True), ("color_changes", "colour changes", True),
    ("colors_used", "colours used (cap)", None), ("cap_kept", "cap kept", None),
    ("cutout_removed_frac", "cutout removed (frac)", None),
    ("cutout_refused_kept_frac", "cutout refused (kept frac)", None), ("size_mm", "size mm", None),
    ("st_per_cm2", "stitches / cm²", None), ("grade", "preflight grade (raw)", None),
    ("score_raw", "preflight score (raw)", None), ("wall_s", "wall s", True),
    ("ssim", "SSIM (raw)", None), ("dE", "ΔE (raw)", None), ("fidelity_cc", "fidelity cc", None),
)


def load_run(run_dir: Path) -> dict:
    """run.json plus `png: {slug: path}` and `dir`."""
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    run["png"] = {p.stem: p for p in run_dir.glob("*.png")}
    run["dir"] = run_dir
    return run


def baseline_summary(run: dict) -> dict:
    """A loaded run minus its images and paths: tree_sha, date, config,
    timeout_s, procs and the per-row instrument numbers. This is what
    `docs/scoreboards/photo-corpus/baseline-<sha7>.json` holds."""
    keep = ("tree_sha", "date", "config", "timeout_s", "procs")
    out = {k: run.get(k) for k in keep}
    out["rows"] = {slug: {k: v for k, v in row.items() if k != "design"} for slug, row in run["rows"].items()}
    return out


def _data_uri(path: Path | None, max_side: int | None = None) -> str | None:
    import base64
    import cv2
    if path is None or not Path(path).exists():
        return None
    img = load_photo(path, fabric_bgr=tuple(reversed(request_config().get("garment_rgb") or [235, 232, 223])))
    if img is None:
        return None
    if max_side:
        h, w = img.shape[:2]
        s = max_side / max(h, w)
        if s < 1:
            img = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode() if ok else None


def _fmt(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "NO"
    if isinstance(v, float):
        return f"{v:.3g}" if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, list):
        return " × ".join(_fmt(x) for x in v)
    return str(v)


def _delta(key: str, a, b, lower_better) -> tuple[str, str]:
    """(text, css class) for the delta column."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        d = b - a
        if d == 0:
            return "0", "same"
        text = f"{d:+.3g}" if abs(d) < 1000 else f"{d:+,.0f}"
        if lower_better is None:
            return text, "neutral"
        return text, ("good" if (d < 0) == lower_better else "bad")
    if a == b:
        return "", "same"
    return f"{_fmt(a)} → {_fmt(b)}", "neutral"


def build_sxs(before: dict, after: dict, rows: list[dict], photos: Path, manifest: dict,
              allow_same_sha: bool = False) -> str:
    """One self-contained HTML: per corpus row the source thumbnail, the before
    render, the after render, SXS_METRICS before / after / delta, and Kent's
    better / same / worse buttons with a note. Verdicts live in localStorage
    under `sxs:<before>:<after>` until "Export verdicts" downloads them as
    {before, after, date, rows{slug{verdict, note}}}. Refuses two runs of the
    same tree unless `allow_same_sha` (a before/after of one sha judges nothing)."""
    import html as h
    from datetime import date
    bsha, asha = before.get("tree_sha", "?"), after.get("tree_sha", "?")
    if bsha == asha and not allow_same_sha:
        raise SystemExit(f"both runs are tree {bsha[:8]}: a before/after of one sha judges nothing "
                         "(--allow-same-sha to build it anyway)")
    key = f"sxs:{bsha}:{asha}"
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["kind"], r["genre"]), []).append(r)
    parts = [f"""<!doctype html><html><head><meta charset="utf-8"><title>Photo corpus sxs {bsha[:7]} → {asha[:7]}</title>
<style>
body{{font:14px system-ui,sans-serif;background:#1e1e1e;color:#eee;margin:0;padding:16px}}
h1{{font-size:18px}} h2{{font-size:15px;color:#bbb;margin:28px 0 8px;border-top:1px solid #444;padding-top:8px}}
.row{{display:grid;grid-template-columns:260px 1fr 1fr 300px;gap:14px;align-items:start;padding:12px 0;border-bottom:1px solid #333}}
.row img{{max-width:100%;max-height:420px;background:#333}} .cap{{font-size:12px;color:#aaa;margin-top:4px}}
.cap a{{color:#8ab}} table{{border-collapse:collapse;font-size:12px;width:100%}} td{{padding:1px 6px;border-bottom:1px solid #2a2a2a}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}} .good{{color:#7c7}} .bad{{color:#e77}} .same{{color:#777}} .neutral{{color:#aaa}}
.verdict button{{font:13px system-ui;padding:6px 12px;margin:6px 6px 6px 0;border:1px solid #555;background:#2a2a2a;color:#eee;border-radius:4px;cursor:pointer}}
.verdict button.on{{background:#3a6;border-color:#5c8;color:#fff}} .verdict input{{width:95%;background:#222;color:#eee;border:1px solid #444;padding:4px}}
.bar{{position:sticky;top:0;background:#1e1e1e;padding:8px 0;border-bottom:1px solid #444;z-index:2}}
.bar button{{font:13px system-ui;padding:6px 12px;border:1px solid #5c8;background:#3a6;color:#fff;border-radius:4px;cursor:pointer}}
.gate{{color:#c9a;font-size:12px}} .state{{font-weight:bold;color:#e77}}
</style></head><body>
<div class="bar"><b>Photo corpus side by side</b> &nbsp; before <code>{h.escape(bsha[:12])}</code> ({h.escape(str(before.get('date')))}, {before.get('procs', '?')} proc) → after <code>{h.escape(asha[:12])}</code> ({h.escape(str(after.get('date')))}, {after.get('procs', '?')} proc)
&nbsp; <button id="export">Export verdicts</button> <span id="count"></span><br><span class="gate">{h.escape(GATE4_LINE)} {h.escape(CC_NULL_LINE)} {h.escape(WALL_LINE)}</span></div>
<h1>{len(rows)} rows: source · before · after · numbers (before / after / Δ)</h1>"""]
    for (kind, genre), grp in groups.items():
        parts.append(f"<h2>{h.escape(kind)} / {h.escape(genre)}</h2>")
        for r in grp:
            slug = r["slug"]
            rb, ra = before["rows"].get(slug), after["rows"].get(slug)
            m = manifest.get(slug, {})
            thumb = _data_uri(photo_path(photos, slug), 360) or ""
            cells = []
            for tag, run, rr in (("before", before, rb), ("after", after, ra)):
                uri = _data_uri(run["png"].get(slug))
                if rr is None or uri is None:
                    cells.append(f'<div><div class="state">{tag}: missing</div><img alt="{tag} missing" src=""></div>')
                else:
                    state = "" if rr.get("state") == "done" else f'<div class="state">{h.escape(str(rr.get("state")))}: {h.escape(str(rr.get("error") or ""))[:160]}</div>'
                    cells.append(f'<div>{state}<img src="{uri}" alt="{tag}"><div class="cap">{tag} · {h.escape(run.get("tree_sha", "?")[:7])}</div></div>')
            trs = []
            for key_, label, lower in SXS_METRICS:
                a = (rb or {}).get(key_)
                b = (ra or {}).get(key_)
                dt, cls = _delta(key_, a, b, lower)
                trs.append(f'<tr><td>{h.escape(label)}</td><td class="n">{h.escape(_fmt(a))}</td>'
                           f'<td class="n">{h.escape(_fmt(b))}</td><td class="n {cls}">{h.escape(dt)}</td></tr>')
            attribution = (f'<a href="{h.escape(m.get("page") or r.get("page") or "#")}">{h.escape(r["title"])}</a> · '
                           f'{h.escape(m.get("author") or r.get("author") or "")} · {h.escape(m.get("licence") or r.get("licence") or "")}')
            parts.append(f"""<div class="row" data-slug="{h.escape(slug)}">
<div><img src="{thumb}" alt="source"><div class="cap"><b>{h.escape(slug)}</b><br>{attribution}</div></div>
{cells[0]}{cells[1]}
<div><table>{''.join(trs)}</table>
<div class="verdict"><button data-verdict="better">better</button><button data-verdict="same">same</button><button data-verdict="worse">worse</button><br>
<input class="note" placeholder="note (optional)"></div></div></div>""")
    parts.append(f"""<script>
const KEY = {json.dumps(key)}, BEFORE = {json.dumps(bsha)}, AFTER = {json.dumps(asha)};
let V = {{}}; try {{ V = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{ V = {{}}; }}
function save() {{ try {{ localStorage.setItem(KEY, JSON.stringify(V)); }} catch (e) {{}} count(); }}
function count() {{ const n = Object.values(V).filter(v => v.verdict).length; document.getElementById("count").textContent = n + " / " + document.querySelectorAll(".row").length + " judged"; }}
document.querySelectorAll(".row").forEach(row => {{
  const slug = row.dataset.slug, note = row.querySelector(".note"), btns = row.querySelectorAll("[data-verdict]");
  const paint = () => btns.forEach(b => b.classList.toggle("on", (V[slug] || {{}}).verdict === b.dataset.verdict));
  if (V[slug]) note.value = V[slug].note || "";
  btns.forEach(b => b.onclick = () => {{ V[slug] = {{verdict: b.dataset.verdict, note: note.value}}; save(); paint(); }});
  note.oninput = () => {{ V[slug] = {{verdict: (V[slug] || {{}}).verdict || null, note: note.value}}; save(); }};
  paint();
}});
document.getElementById("export").onclick = () => {{
  const out = {{before: BEFORE, after: AFTER, date: {json.dumps(date.today().isoformat())}, rows: V}};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {{type: "application/json"}}));
  a.download = "verdicts-" + BEFORE.slice(0, 7) + "-" + AFTER.slice(0, 7) + ".json"; a.click();
}};
count();
</script></body></html>""")
    return "\n".join(parts)


# ------------------------------------------------------------------ tally
VERDICTS = ("better", "same", "worse")
TALLY_HEADER = ("| date | before | after | photo better / same / worse | logo better / same / worse "
                "| unjudged | worse slugs |\n|---|---|---|---|---|---|---|")


def tally_counts(verdicts: dict, rows: list[dict]) -> dict:
    """{kind: {better, same, worse, unjudged, worse_slugs}} over the corpus rows."""
    out: dict[str, dict] = {}
    judged = verdicts.get("rows") or {}
    for r in rows:
        t = out.setdefault(r["kind"], {"better": 0, "same": 0, "worse": 0, "unjudged": 0, "worse_slugs": []})
        v = (judged.get(r["slug"]) or {}).get("verdict")
        if v in VERDICTS:
            t[v] += 1
            if v == "worse":
                t["worse_slugs"].append(r["slug"])
        else:
            t["unjudged"] += 1
    return out


def _tally_line(verdicts: dict, rows: list[dict]) -> str:
    t = tally_counts(verdicts, rows)

    def trio(kind):
        k = t.get(kind)
        return f"{k['better']} / {k['same']} / {k['worse']}" if k else "–"
    unjudged = sum(k["unjudged"] for k in t.values())
    worse = ", ".join(s for k in t.values() for s in k["worse_slugs"]) or "–"
    b, a = verdicts.get("before", "?"), verdicts.get("after", "?")
    return (f"| {verdicts.get('date', '?')} | `{b[:7]}` | `{a[:7]}` | {trio('photo')} | {trio('logo')} "
            f"| {unjudged} | {worse} |")


def file_verdicts(verdicts: dict, rows: list[dict], out_dir: Path) -> Path:
    """Copy the exported verdicts to `out_dir/<date>-<before7>-<after7>.json` and
    put one tally line in `out_dir/README.md`, replacing an earlier line for the
    same before/after pair. -> the json path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    b, a = verdicts.get("before", "?")[:7], verdicts.get("after", "?")[:7]
    dest = out_dir / f"{verdicts.get('date', 'undated')}-{b}-{a}.json"
    dest.write_text(json.dumps(verdicts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    readme = out_dir / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
    else:
        text = ("# Photo corpus scoreboard\n\nKent's better / same / worse verdicts per photo PR, read off the "
                "side-by-side page `python -m tools.photo_corpus sxs` builds over the Commons corpus "
                "(`digitizer/testdata/photo/corpus/corpus.json`, 18 photo genres + the logo census). "
                "Each json here is one exported verdict set; the table has one line per before/after pair.\n\n"
                f"{GATE4_LINE}\n\n{TALLY_HEADER}\n")
    pair = f"| `{b}` | `{a}` |"
    lines = [ln for ln in text.rstrip("\n").split("\n") if pair not in ln]
    lines.append(_tally_line(verdicts, rows))
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


# ------------------------------------------------------------------ CLI
def main(argv: list[str] | None = None) -> int:
    import argparse
    from tools._console import utf8_console
    utf8_console()   # Commons titles and authors carry non-cp1252 letters (Kabukichō)
    ap = argparse.ArgumentParser(prog="python -m tools.photo_corpus",
                                 description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download the corpus images + manifest.json")
    f.add_argument("--out", type=Path, default=CORPUS_DIR)
    f.add_argument("--only", action="append", default=[], metavar="SLUG")
    c = sub.add_parser("capture", help="digitize every row at a tree; corpus_runs/<label>/")
    c.add_argument("--label", required=True)
    c.add_argument("--base", metavar="REF", help="run the merge-base of HEAD and REF (git archive)")
    c.add_argument("--tree", type=Path, help="run this digitizer/ tree (default: this one)")
    c.add_argument("--photos", type=Path, default=CORPUS_DIR)
    c.add_argument("--only", action="append", default=[], metavar="SLUG")
    c.add_argument("--timeout", type=float, default=TIMEOUT_S)
    c.add_argument("--procs", type=int, default=PROCS)
    c.add_argument("--set", action="append", default=[], metavar="FIELD=JSON",
                   help="override one request field on top of the tree's own request, e.g. "
                        "--set photo_cutout_min_kept=0.0 (the other arm of a flag); "
                        "recorded in run.json's config")
    s = sub.add_parser("sxs", help="build the side-by-side HTML from two runs")
    s.add_argument("--before", type=Path, required=True)
    s.add_argument("--after", type=Path, required=True)
    s.add_argument("--photos", type=Path, default=CORPUS_DIR)
    s.add_argument("--out", type=Path, help="default corpus_runs/sxs-<before7>-<after7>.html")
    s.add_argument("--allow-same-sha", action="store_true")
    s.add_argument("--only", action="append", default=[], metavar="SLUG",
                   help="only these rows (a page over the rows a partial capture holds)")
    m = sub.add_parser("summary", help="a run's numbers without designs or images (the baseline-<sha7>.json record)")
    m.add_argument("run", type=Path)
    m.add_argument("--out", type=Path, help="default docs/scoreboards/photo-corpus/baseline-<sha7>.json")
    t = sub.add_parser("tally", help="file an exported verdicts json under docs/scoreboards/photo-corpus")
    t.add_argument("verdicts", type=Path)
    t.add_argument("--out-dir", type=Path, default=SCOREBOARD_DIR)
    a = ap.parse_args(argv)
    rows = load_corpus()
    if getattr(a, "only", None):
        rows = [r for r in rows if r["slug"] in a.only]
    if a.cmd == "fetch":
        res = fetch(rows, a.out)
        print(f"fetched {len(res['fetched'])}, skipped {len(res['skipped'])}")
        return 0
    if a.cmd == "capture":
        out = RUNS_DIR / a.label
        overrides = parse_sets(a.set)
        if a.base:
            from tools import default_path_diff as dpd
            with dpd.merge_base_tree(a.base) as base_tree:
                run = capture(rows, a.photos, base_tree, out, dpd.last_merge_base, a.timeout, a.procs,
                              overrides=overrides)
        else:
            tree = a.tree or DIGITIZER
            run = capture(rows, a.photos, tree, out, _head_sha(tree), a.timeout, a.procs,
                          overrides=overrides)
        states = {}
        for r in run["rows"].values():
            states[r["state"]] = states.get(r["state"], 0) + 1
        print(f"run {a.label} at {run['tree_sha'][:8]}: {states} -> {out}")
        return 0
    if a.cmd == "summary":
        summary = baseline_summary(load_run(a.run))
        out = a.out or SCOREBOARD_DIR / f"baseline-{summary['tree_sha'][:7]}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        states = {}
        for r in summary["rows"].values():
            states[r["state"]] = states.get(r["state"], 0) + 1
        print(f"wrote {out}: {len(summary['rows'])} rows {states}")
        return 0
    if a.cmd == "sxs":
        before, after = load_run(a.before), load_run(a.after)
        mpath = a.photos / "manifest.json"
        manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
        page = build_sxs(before, after, rows, a.photos, manifest, a.allow_same_sha)
        out = a.out or RUNS_DIR / f"sxs-{before['tree_sha'][:7]}-{after['tree_sha'][:7]}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(rows)} rows)")
        return 0
    if a.cmd == "tally":
        verdicts = json.loads(a.verdicts.read_text(encoding="utf-8"))
        dest = file_verdicts(verdicts, rows, a.out_dir)
        print(_tally_line(verdicts, rows))
        print(f"filed {dest}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
