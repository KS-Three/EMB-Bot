# Photo Corpus Side-by-Side Scorecard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One tool that fetches a licence-clean Commons corpus, digitizes it at two trees, and builds a self-contained HTML where Kent marks each row better / same / worse, with his verdicts filed under `docs/scoreboards/photo-corpus/`.

**Architecture:** `digitizer/tools/photo_corpus.py` with four subcommands over plain JSON on disk: `fetch` (corpus.json -> images + manifest), `capture` (images + tree -> one folder of per-row json + png), `sxs` (two run folders -> one HTML), `tally` (verdict json -> scoreboard files). Each digitize is a subprocess with `cwd` = the tree under test, the `default_path_diff` pattern, so `--base REF` runs the merge-base's code. Unit tests never touch the network or the pipeline: fetch takes an injected API callable, capture's row summariser is tested on saved outputs, sxs on tiny synthetic runs.

**Tech Stack:** Python 3.12, stdlib `urllib`/`json`/`subprocess`, OpenCV + scikit-image (already in the venv), `digitizer_core.stitchviz.render_design`, `tools.fremont_triage.studio_request`, `tools.default_path_diff.merge_base_tree` / `RUNNER_ENV`. Tests: pytest.

**Spec:** `docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md`

## Global Constraints

- Public repo: no downloaded image, render or HTML is ever committed. Committed: `corpus.json` (titles, page URLs, authors, licences), `README.md`, verdict JSON and the tally markdown.
- Allowed licences, lower-cased substring match on Commons `LicenseShortName`: `cc0`, `public domain`, `pd`, `cc by 4.0`, `cc by 3.0`, `cc by 2.0`, `cc by-sa 4.0`, `cc by-sa 3.0`, `cc by-sa 2.0`.
- Request: `studio_request(80.0)` with `garment_id = "left_chest"` (the fixture's `garment_rgb` for that garment). No other config.
- Numbers are instrument readings; the HTML and the tally say so in a fixed line: `All numbers are instrument readings, not quality claims (ROADMAP gate 4). The verdict column is Kent's.`
- Per-row timeout default 1200 s, `--procs` default 2.
- Env for workers: `default_path_diff.RUNNER_ENV` over `os.environ`.
- Run with `python -m tools.photo_corpus ...` from `digitizer/`; never `python tools/photo_corpus.py`.
- Memory notes LF, index under 24,986 chars (`tests/test_memory_budget.py`).

## Review Focus

- A corpus row whose Commons licence changed since it was listed: `fetch` must skip it and say so, not download it (Task 2 test `test_fetch_refuses_row_whose_live_licence_left_the_set`).
- A row that timed out in one run and finished in the other: the sxs row must still appear with the failure in that tile (Task 5 `test_sxs_row_with_a_missing_or_failed_side_still_renders`).
- A design with zero stitches (the census's cutout-removed-everything rows): the summariser must report `stitches 0` and `fidelity_cc` as `None`, not divide by zero on area or crash in SSIM (Task 3 `test_summarise_handles_an_empty_design`).
- Two captures of the same tree must not be mistaken for before/after: `sxs` refuses when both runs' `tree_sha` are equal unless `--allow-same-sha` (Task 5 `test_sxs_refuses_identical_tree_shas`).
- Re-filing the same verdict JSON twice must not duplicate the tally line (Task 6 `test_tally_is_idempotent_per_sha_pair`).

---

### Task 0: Lane housekeeping

**Files:**
- Modify: `.claude/memory/MEMORY.md` (lane copy), `.claude/memory/MEMORY-archive.md`
- Existing untracked: `.claude/memory/photo-lane-generalise-2026-10-27.md`

- [ ] **Step 1: Rename the branch**

```bash
git branch -m claude/photo-corpus-sxs
```

- [ ] **Step 2: Move the five `embot-*` SNAPSHOT lines (dated 10-03/10-04, index lines 43-47) from `MEMORY.md` to the bottom of `MEMORY-archive.md`**

The archive header already says "through 10-04". Use the Edit tool (PowerShell round-trips mangle UTF-8).

- [ ] **Step 3: Run the budget test**

Run: `python -m pytest tests/test_memory_budget.py -q`
Expected: all pass (index under 24,986 chars, every note indexed once)

- [ ] **Step 4: Commit**

```bash
git add .claude/memory/MEMORY.md .claude/memory/MEMORY-archive.md .claude/memory/photo-lane-generalise-2026-10-27.md docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md docs/superpowers/plans/2026-10-27-photo-corpus-sxs.md
git commit -m "Memory: photo lane must generalise (Kent 10-27); corpus sxs spec + plan; archive five 10-03/10-04 snapshot lines"
```

### Task 1: Corpus list and its test

**Files:**
- Create: `digitizer/testdata/photo/corpus/corpus.json`, `digitizer/testdata/photo/corpus/README.md`
- Modify: `.gitignore` (repo root)
- Create: `digitizer/tools/photo_corpus.py` (constants + `load_corpus`)
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Produces: `CORPUS_DIR = TESTDATA / "photo" / "corpus"`, `CORPUS_JSON = CORPUS_DIR / "corpus.json"`, `OK_LICENCES: tuple[str, ...]`, `licence_ok(short_name: str) -> bool`, `load_corpus(path: Path = CORPUS_JSON) -> list[dict]` (rows with keys `slug, kind, genre, title, page, author, licence`; raises `ValueError` on duplicate slug or missing key).

- [ ] **Step 1: Write the failing tests**

```python
from tools import photo_corpus as pc

def test_corpus_rows_are_complete_unique_and_licence_clean():
    rows = pc.load_corpus()
    assert len(rows) >= 18
    assert len({r["slug"] for r in rows}) == len(rows)
    for r in rows:
        assert set(r) >= {"slug", "kind", "genre", "title", "page", "author", "licence"}
        assert r["kind"] in {"photo", "logo"}
        assert r["title"].startswith("File:")
        assert pc.licence_ok(r["licence"]), r["slug"]

def test_no_image_is_tracked_under_the_corpus_dir():
    out = subprocess.run(["git", "ls-files", str(pc.CORPUS_DIR)], capture_output=True, text=True, cwd=pc.DIGITIZER).stdout
    names = {Path(p).name for p in out.split()}
    assert names <= {"corpus.json", "README.md"}

def test_licence_ok_is_a_lowercase_substring_match():
    assert pc.licence_ok("CC BY-SA 4.0")
    assert pc.licence_ok("Public domain")
    assert not pc.licence_ok("CC BY-NC 2.0")
    assert not pc.licence_ok("")

def test_load_corpus_rejects_duplicate_slugs(tmp_path):
    p = tmp_path / "c.json"; row = {"slug": "a", "kind": "photo", "genre": "g", "title": "File:x.jpg", "page": "u", "author": "me", "licence": "cc0"}
    p.write_text(json.dumps([row, row]), encoding="utf-8")
    with pytest.raises(ValueError):
        pc.load_corpus(p)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: FAIL, `ModuleNotFoundError: tools.photo_corpus`

- [ ] **Step 3: Write `corpus.json` with the 18 photo rows**

Rows from the census manifest (slug = genre, `kind: "photo"`); author = the manifest's `author` with HTML tags stripped, or `see Commons page`. The 18: bw_street, night_neon, architecture, landscape_lake, food_plate, vintage_sepia, fireworks, snow_highkey, flower_macro, dark_dog, underwater_reef, watercolor, pencil_sketch, stained_glass, group_people, sports_action, night_skyline, oil_painting. Titles and licences are in `C:\Users\EE-LT-~1\AppData\Local\Temp\claude\C--Users-EE-LT-11030--claude-spares-spare-rEx2QB\bcfc7e3b-3d02-4715-a5fc-e43bc9ee39e6\scratchpad\photos\manifest.json`. Logo rows are appended in Task 7.

- [ ] **Step 4: Write `README.md` (why the folder is gitignored, the four commands, the gate-4 line) and the `.gitignore` block**

```
# Commons corpus for the photo side-by-side scorecard (tools/photo_corpus.py).
# Downloaded images stay local; the list and README are tracked.
digitizer/testdata/photo/corpus/*
!digitizer/testdata/photo/corpus/corpus.json
!digitizer/testdata/photo/corpus/README.md
digitizer/corpus_runs/
```

- [ ] **Step 5: Implement the module head: constants, `licence_ok`, `load_corpus`**

`DIGITIZER = Path(__file__).resolve().parent.parent`; `TESTDATA = DIGITIZER / "testdata"`. Module docstring: the four commands and the gate-4 line.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add ../.gitignore testdata/photo/corpus/corpus.json testdata/photo/corpus/README.md tools/photo_corpus.py tests/test_photo_corpus.py
git commit -m "Photo corpus: committed Commons list (18 photo rows, licences), gitignored image folder"
```

### Task 2: `fetch`

**Files:**
- Modify: `digitizer/tools/photo_corpus.py`
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Consumes: `load_corpus`, `licence_ok`.
- Produces: `commons_imageinfo(title: str, get=_http_json) -> dict` (one Commons `imageinfo` dict with `extmetadata`, `thumburl`, `url`, `width`, `height`, `mime`, via `action=query&titles=<title>&prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=1600`); `strip_html(s: str) -> str`; `fetch(rows, out: Path, get=_http_json, download=_http_bytes) -> dict` writing `<slug>.jpg` and `out / "manifest.json"` = `{slug: {title, page, file_url, author, licence, orig_size, bytes, sha256}}`, returning `{"fetched": [...], "skipped": {slug: reason}}`. Rows already present on disk with a manifest entry are skipped as `"cached"`.
- User agent: `EMB-Bot-corpus/1.0 (https://github.com/KS-Three/EMB-Bot)`.

- [ ] **Step 1: Write the failing tests**

```python
def _fake_api(licence="CC BY-SA 4.0", mime="image/jpeg", width=2000):
    def get(params):
        return {"query": {"pages": {"1": {"title": params["titles"], "imageinfo": [{
            "url": "https://x/orig.jpg", "thumburl": "https://x/1600.jpg", "width": width, "height": 1000, "mime": mime,
            "descriptionurl": "https://commons/x", "extmetadata": {"LicenseShortName": {"value": licence},
            "Artist": {"value": "<a href='u'>Someone</a>"}}}]}}}}
    return get

ROW = {"slug": "a", "kind": "photo", "genre": "g", "title": "File:x.jpg", "page": "u", "author": "Someone", "licence": "cc by-sa 4.0"}

def test_fetch_writes_image_and_manifest_with_stripped_author(tmp_path):
    r = pc.fetch([ROW], tmp_path, get=_fake_api(), download=lambda url: b"\xff\xd8jpegbytes")
    assert r["fetched"] == ["a"] and (tmp_path / "a.jpg").read_bytes().startswith(b"\xff\xd8")
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["a"]
    assert m["author"] == "Someone" and m["licence"] == "cc by-sa 4.0" and m["file_url"] == "https://x/1600.jpg"
    assert m["sha256"] == hashlib.sha256(b"\xff\xd8jpegbytes").hexdigest()

def test_fetch_refuses_row_whose_live_licence_left_the_set(tmp_path):
    called = []
    r = pc.fetch([ROW], tmp_path, get=_fake_api(licence="CC BY-NC 4.0"), download=lambda url: called.append(url) or b"")
    assert r["fetched"] == [] and "licence" in r["skipped"]["a"] and called == [] and not (tmp_path / "a.jpg").exists()

def test_fetch_skips_a_row_already_on_disk(tmp_path):
    pc.fetch([ROW], tmp_path, get=_fake_api(), download=lambda url: b"\xff\xd8")
    r = pc.fetch([ROW], tmp_path, get=_fake_api(), download=lambda url: pytest.fail("downloaded again"))
    assert r["skipped"] == {"a": "cached"}

def test_strip_html():
    assert pc.strip_html("<a href='u' class='x'>Wilfredor</a>") == "Wilfredor"
    assert pc.strip_html("") == "see Commons page"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q -k "fetch or strip"`
Expected: FAIL, `AttributeError: ... has no attribute 'fetch'`

- [ ] **Step 3: Implement `_http_json(params) -> dict`, `_http_bytes(url) -> bytes`, `commons_imageinfo`, `strip_html`, `fetch`**

Download `thumburl` if present else `url`; refuse `mime` outside `image/jpeg`, `image/png`; write bytes as `<slug>.jpg` regardless of mime (OpenCV reads by content). Sleep 0.5 s between live downloads only when `download is _http_bytes`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 8 passed

- [ ] **Step 5: Fetch the real corpus once and read the manifest back**

Run: `python -m tools.photo_corpus fetch`
Expected: 18 lines `slug: title | licence | KB`, `manifest.json` with 18 entries; `git status --short testdata/photo/corpus` shows nothing new.

- [ ] **Step 6: Commit**

```bash
git add tools/photo_corpus.py tests/test_photo_corpus.py
git commit -m "Photo corpus: fetch from Commons by title, live licence re-check, manifest with sha256"
```

### Task 3: Row summariser and fidelity numbers

**Files:**
- Modify: `digitizer/tools/photo_corpus.py`
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Produces: `fidelity(photo_bgr: np.ndarray, render_bgr: np.ndarray, fabric_bgr) -> dict` = `{"ssim", "dE", "ssim_null", "fidelity_cc"}` (photo resized to the render's frame inside the 2 mm pad at 8 px/mm; `ssim_null` = SSIM of the photo against a frame filled with `fabric_bgr`; `fidelity_cc = (ssim - ssim_null) / (1 - ssim_null)`, `None` when `1 - ssim_null < 1e-6`); `summarise(output: dict, cap: int) -> dict` over a worker output (`state, stats, warnings, preflight, design, _meta`) returning the row numbers: `state, class, class_conf, route, cutout_removed_frac, stitches, trims, color_changes, colors_used, cap, cap_kept, size_mm, st_per_cm2, grade, score_raw, wall_s, stamps, error`.
- `route` = `"faces_flat"` if any warning code `FACE_ROUTED_FLAT`, else `"photo"` if class in photo classes else `"graphic"`. `cutout_removed_frac` from the `PHOTO_BACKGROUND_REMOVED` warning's `background_frac_after - background_frac_before`, else `None`. `colors_used = len(design["colors"])`, `cap_kept = colors_used <= cap`.

- [ ] **Step 1: Write the failing tests**

```python
def _output(stitches=10, colors=2, warnings=(), state="done", size=(80.0, 50.0)):
    return {"state": state, "stats": {"stitch_count": stitches, "trims": 1, "color_changes": colors - 1, "size_mm": list(size), "thread_m_total": 1.0},
            "warnings": list(warnings), "preflight": {"grade": "F", "score": 0, "metrics": {"raw_score": -38}},
            "design": {"stitches": [], "colors": [{"r": 0, "g": 0, "b": 0}] * colors},
            "_meta": {"elapsed_s": 12.5, "stamps": {"plan_stitches": 9.0}, "class": "photo_scene", "class_conf": 0.9}}

def test_summarise_reads_counts_cap_and_route():
    row = pc.summarise(_output(colors=7, warnings=[{"code": "FACE_ROUTED_FLAT"}, {"code": "PHOTO_BACKGROUND_REMOVED", "background_frac_before": 0.1, "background_frac_after": 0.6}]), cap=6)
    assert row["colors_used"] == 7 and row["cap_kept"] is False and row["route"] == "faces_flat"
    assert row["cutout_removed_frac"] == pytest.approx(0.5) and row["score_raw"] == -38 and row["st_per_cm2"] == pytest.approx(10 / 40)

def test_summarise_handles_an_empty_design():
    row = pc.summarise(_output(stitches=0, size=(0.0, 0.0)), cap=6)
    assert row["stitches"] == 0 and row["st_per_cm2"] is None

def test_summarise_timeout_row():
    row = pc.summarise({"state": "timeout", "_meta": {"elapsed_s": 1200.0}}, cap=6)
    assert row["state"] == "timeout" and row["stitches"] is None and row["wall_s"] == 1200.0

def test_fidelity_cc_is_one_for_a_perfect_render_and_zero_for_blank():
    rng = np.random.default_rng(0); photo = rng.integers(0, 255, (64, 96, 3), np.uint8)
    pad = 16; frame = np.full((64 + 2 * pad, 96 + 2 * pad, 3), (223, 232, 235), np.uint8); frame[pad:-pad, pad:-pad] = photo
    f = pc.fidelity(photo, frame, (223, 232, 235))
    assert f["fidelity_cc"] == pytest.approx(1.0, abs=1e-6)
    blank = np.full_like(frame, (223, 232, 235))
    assert pc.fidelity(photo, blank, (223, 232, 235))["fidelity_cc"] == pytest.approx(0.0, abs=1e-6)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q -k "summarise or fidelity"`
Expected: FAIL, no attribute `summarise`

- [ ] **Step 3: Implement `fidelity` and `summarise`**

`PXMM = 8.0`, `PAD_MM = 2.0`; luminance SSIM via `skimage.metrics.structural_similarity(data_range=255)`; `dE` as the census did (mean CIE76 in OpenCV Lab scaled by 100/255).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add tools/photo_corpus.py tests/test_photo_corpus.py
git commit -m "Photo corpus: row summariser (cap kept, route, cutout fraction) and chance-corrected fidelity with a blank-frame null"
```

### Task 4: `capture`

**Files:**
- Modify: `digitizer/tools/photo_corpus.py`
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Consumes: `summarise`, `fidelity`, `load_corpus`, `tools.default_path_diff.merge_base_tree`, `RUNNER_ENV`, `_git`; `tools.fremont_triage.studio_request`.
- Produces: `WORKER: str` (the census worker as a `-c` program: argv json spec `{photo, out, config, tree}`; inserts `tree` at `sys.path[0]`; runs `_decode_bounded` -> `build_generation(pixels, cfg, exif_source=data)` -> `finish_generation(gen.fork(), cfg)` -> `plan_stitches` -> `plan_to_design` -> `run_preflight`; writes `out` json with `state, stats, warnings, preflight, design, _meta{elapsed_s, stamps, class, class_conf, config_sent}`; `faulthandler.dump_traceback_later(120, repeat=True)` to stderr); `request_config() -> dict` = `studio_request(80.0)` with `garment_id="left_chest"`; `run_row(tree: Path, photo: Path, out: Path, cfg: dict, timeout: float) -> dict` (subprocess, `cwd=tree`, writes `out` itself on timeout/error as `{"state": "timeout"|"error", "rc", "stderr_tail", "_meta": {"elapsed_s", "photo"}}`); `capture(rows, photos: Path, tree: Path, out: Path, tree_sha: str, timeout: float, procs: int) -> dict` writing per row `<slug>.json` (worker output), `<slug>.png` (render at 8 px/mm on the request's `garment_rgb`), `<slug>.row.json` (`summarise` + `fidelity`), and `out / "run.json"` = `{tree_sha, date, config, timeout_s, procs, rows: {slug: row}}`; skips rows whose `<slug>.row.json` exists (resume).
- CLI: `capture --label L [--base REF | --tree DIR] [--photos DIR] [--only SLUG]... [--timeout 1200] [--procs 2]`; default tree = `DIGITIZER`, `tree_sha` = `git rev-parse HEAD` (or `default_path_diff.last_merge_base` under `--base`); output `DIGITIZER / "corpus_runs" / L`.

- [ ] **Step 1: Write the failing tests** (no pipeline: a stub worker)

```python
STUB_OK = "import json,sys; s=json.loads(sys.argv[1]); open(s['out'],'w').write(json.dumps({'state':'done','stats':{'stitch_count':3,'trims':0,'color_changes':0,'size_mm':[80,40],'thread_m_total':0.1},'warnings':[],'preflight':{'grade':'A','score':100,'metrics':{'raw_score':100}},'design':{'stitches':[[0,0],[10,0],[10,10]],'colors':[{'r':0,'g':0,'b':0}]},'_meta':{'elapsed_s':0.1,'stamps':{},'class':'photo_subject','class_conf':0.8}}))"
STUB_HANG = "import time; time.sleep(30)"

def test_run_row_writes_timeout_output(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_HANG)
    out = tmp_path / "a.json"
    res = pc.run_row(tmp_path, tmp_path / "a.jpg", out, {}, timeout=1.0)
    assert res["state"] == "timeout" and json.loads(out.read_text())["state"] == "timeout"

def test_capture_writes_row_png_and_run_json(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    photos = tmp_path / "p"; photos.mkdir(); cv2.imwrite(str(photos / "a.jpg"), np.zeros((20, 30, 3), np.uint8))
    out = tmp_path / "run"
    run = pc.capture([ROW], photos, tmp_path, out, tree_sha="abc", timeout=10, procs=1)
    assert (out / "a.png").exists() and (out / "a.row.json").exists()
    assert run["tree_sha"] == "abc" and run["rows"]["a"]["stitches"] == 3 and "fidelity_cc" in run["rows"]["a"]

def test_capture_resumes_past_finished_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "WORKER", STUB_OK)
    photos = tmp_path / "p"; photos.mkdir(); cv2.imwrite(str(photos / "a.jpg"), np.zeros((20, 30, 3), np.uint8))
    out = tmp_path / "run"; pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    monkeypatch.setattr(pc, "WORKER", "raise SystemExit('must not run')")
    run = pc.capture([ROW], photos, tmp_path, out, "abc", 10, 1)
    assert run["rows"]["a"]["stitches"] == 3

def test_request_config_is_the_studio_request_on_left_chest():
    cfg = pc.request_config()
    assert cfg["target_width_mm"] == 80.0 and cfg["garment_id"] == "left_chest" and "garment_rgb" in cfg
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q -k "run_row or capture or request_config"`
Expected: FAIL, no attribute `run_row`

- [ ] **Step 3: Implement `WORKER`, `request_config`, `run_row`, `capture`, the `capture` CLI**

`procs` via `concurrent.futures.ThreadPoolExecutor` (each thread blocks on its subprocess). Render with `stitchviz.render_design(design, px_per_mm=8.0, fabric_bgr=tuple(reversed(cfg["garment_rgb"])))`; on a non-done row write a placeholder png (fabric colour, the state text drawn with `cv2.putText`). `fidelity` reads the photo with `cv2.imread`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 16 passed

- [ ] **Step 5: Smoke one real row at HEAD**

Run: `python -m tools.photo_corpus capture --label smoke --only flower_macro --timeout 900`
Expected: `flower_macro: done <s> stitches=<n>` and `corpus_runs/smoke/flower_macro.png` opens as a render. Paste the line.

- [ ] **Step 6: Commit**

```bash
git add tools/photo_corpus.py tests/test_photo_corpus.py
git commit -m "Photo corpus: capture a run per tree (subprocess per row, timeout, resume, --base merge-base), render + row numbers"
```

### Task 5: `sxs` HTML

**Files:**
- Modify: `digitizer/tools/photo_corpus.py`
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Consumes: run folders from Task 4 (`run.json`, `<slug>.png`), corpus rows, photos dir (thumbnails), manifest (attribution).
- Produces: `load_run(dir: Path) -> dict` (run.json plus `png: {slug: Path}`); `build_sxs(before: dict, after: dict, rows: list[dict], photos: Path, manifest: dict, allow_same_sha=False) -> str` (HTML); `sxs` CLI: `sxs --before DIR --after DIR [--out FILE] [--allow-same-sha]`, default out `corpus_runs/sxs-<before7>-<after7>.html`.
- HTML contract: `<tr data-slug=…>` per corpus row, grouped under `<h2>` per `kind / genre`; three `<img>` (thumb, before, after; a failed side shows the placeholder png); numbers table `metric | before | after | delta`; buttons `<button data-verdict="better|same|worse">`, `<input class="note">`; verdicts kept in `localStorage` under key `sxs:<before_sha>:<after_sha>`; "Export verdicts" downloads `verdicts-<before7>-<after7>.json` = `{"before", "after", "date", "rows": {slug: {"verdict", "note"}}}`; the gate-4 line at the top; each row shows title, author and licence with the Commons page link.

- [ ] **Step 1: Write the failing tests**

```python
def _run(tmp_path, name, sha, slugs=("a",), state="done"):
    d = tmp_path / name; d.mkdir()
    rows = {s: {"state": state, "stitches": 5 if state == "done" else None, "trims": 1, "wall_s": 3.0} for s in slugs}
    (d / "run.json").write_text(json.dumps({"tree_sha": sha, "date": "2026-10-27", "config": {}, "timeout_s": 1, "procs": 1, "rows": rows}))
    for s in slugs: cv2.imwrite(str(d / f"{s}.png"), np.zeros((8, 8, 3), np.uint8))
    return pc.load_run(d)

def test_sxs_has_a_row_per_corpus_slug_with_buttons_and_export(tmp_path):
    photos = tmp_path / "p"; photos.mkdir(); cv2.imwrite(str(photos / "a.jpg"), np.zeros((8, 8, 3), np.uint8))
    html = pc.build_sxs(_run(tmp_path, "b", "aaa1111"), _run(tmp_path, "h", "bbb2222"), [ROW], photos, {"a": {"author": "Someone"}})
    assert 'data-slug="a"' in html and html.count('data-verdict=') == 3 and "sxs:aaa1111:bbb2222" in html
    assert "instrument readings" in html and "Someone" in html and html.count("data:image/png;base64") == 3

def test_sxs_row_with_a_missing_or_failed_side_still_renders(tmp_path):
    photos = tmp_path / "p"; photos.mkdir(); cv2.imwrite(str(photos / "a.jpg"), np.zeros((8, 8, 3), np.uint8))
    html = pc.build_sxs(_run(tmp_path, "b", "aaa1111", state="timeout"), _run(tmp_path, "h", "bbb2222", slugs=()), [ROW], photos, {})
    assert 'data-slug="a"' in html and "timeout" in html and "missing" in html

def test_sxs_refuses_identical_tree_shas(tmp_path):
    with pytest.raises(SystemExit):
        pc.build_sxs(_run(tmp_path, "b", "same"), _run(tmp_path, "h", "same"), [ROW], tmp_path, {})
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q -k sxs`
Expected: FAIL, no attribute `load_run`

- [ ] **Step 3: Implement `load_run`, `build_sxs`, the `sxs` CLI**

Thumbnail long side 360 px; renders `max-width: 560px`; dark page as the census sheet; delta column green/red by sign only for `stitches, trims, color_changes, wall_s`, grey elsewhere. Inline `<script>`: restore verdicts from localStorage on load, write on click, export via a Blob download.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 19 passed

- [ ] **Step 5: Build an sxs from the smoke run against itself with `--allow-same-sha`, open it in the browser pane, click a verdict, export, read the JSON**

Run: `python -m tools.photo_corpus sxs --before corpus_runs/smoke --after corpus_runs/smoke --allow-same-sha --out corpus_runs/smoke.html`
Expected: the page shows one row with three images and the buttons; clicking `better` then reload keeps it; export produces the verdict JSON with `rows.flower_macro.verdict == "better"`.

- [ ] **Step 6: Commit**

```bash
git add tools/photo_corpus.py tests/test_photo_corpus.py
git commit -m "Photo corpus: side-by-side HTML (before/after renders, instrument numbers, better/same/worse verdicts with export)"
```

### Task 6: `tally`

**Files:**
- Modify: `digitizer/tools/photo_corpus.py`
- Create: `docs/scoreboards/photo-corpus/README.md`
- Test: `digitizer/tests/test_photo_corpus.py`

**Interfaces:**
- Produces: `tally_counts(verdicts: dict, rows: list[dict]) -> dict` = `{kind: {"better": n, "same": n, "worse": n, "unjudged": n, "worse_slugs": [...]}}`; `file_verdicts(verdicts: dict, rows, out_dir: Path) -> Path` copying the JSON to `out_dir / f"{date}-{before7}-{after7}.json"` and appending one table line to `out_dir / "README.md"` (`| date | before | after | photo better/same/worse | logo better/same/worse | worse slugs |`), replacing an existing line with the same before/after pair.
- CLI: `tally VERDICTS.json [--out-dir ../docs/scoreboards/photo-corpus]`.

- [ ] **Step 1: Write the failing tests**

```python
V = {"before": "aaa1111", "after": "bbb2222", "date": "2026-10-27", "rows": {"a": {"verdict": "worse", "note": "halo"}}}
ROWS = [ROW, {**ROW, "slug": "b", "kind": "logo"}]

def test_tally_counts_by_kind_and_lists_worse_slugs():
    t = pc.tally_counts(V, ROWS)
    assert t["photo"] == {"better": 0, "same": 0, "worse": 1, "unjudged": 0, "worse_slugs": ["a"]}
    assert t["logo"]["unjudged"] == 1

def test_tally_is_idempotent_per_sha_pair(tmp_path):
    pc.file_verdicts(V, ROWS, tmp_path); pc.file_verdicts(V, ROWS, tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.count("aaa1111") == 1 and (tmp_path / "2026-10-27-aaa1111-bbb2222.json").exists()
    assert "instrument readings" in readme
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_photo_corpus.py -q -k tally`
Expected: FAIL, no attribute `tally_counts`

- [ ] **Step 3: Implement `tally_counts`, `file_verdicts`, the `tally` CLI; write the scoreboard README head (what the folder is, the four commands, the gate-4 line, the empty table header)**

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_photo_corpus.py -q`
Expected: 21 passed

- [ ] **Step 5: Commit**

```bash
git add tools/photo_corpus.py tests/test_photo_corpus.py ../docs/scoreboards/photo-corpus/README.md
git commit -m "Photo corpus: file Kent's verdicts under docs/scoreboards/photo-corpus with a per-PR tally line"
```

### Task 7: Logo rows and the standing baseline

**Files:**
- Modify: `digitizer/testdata/photo/corpus/corpus.json`, `docs/photo-style-census-2026-10-27.md` (copy from the main checkout, then edit), `COOKBOOK.md` (one "Running things" entry)

- [ ] **Step 1: Ask the logo session for its manifest** (`SendMessage` to `local_2adc16c5-9635-4e2c-9427-ec0facebb4f6`: the path of its Commons manifest and its licence column). Append its rows to `corpus.json` with `kind: "logo"`, slug = its genre key. Re-run Task 1's tests.

- [ ] **Step 2: Fetch the logo rows**

Run: `python -m tools.photo_corpus fetch`
Expected: 21 new lines, 18 `cached`.

- [ ] **Step 3: Capture the baseline on `main` in the background**

Run: `python -m tools.photo_corpus capture --label main-$(git rev-parse --short origin/main) --base origin/main --procs 2 --timeout 1200 > corpus_runs/baseline.log 2>&1; echo EXIT=$? >> corpus_runs/baseline.log`
Expected: one line per row; `EXIT=0`. Budget hours; `faulthandler` stacks in `<slug>.stderr.txt` name the stage of any timeout.

- [ ] **Step 4: Copy the baseline's `run.json` rows (numbers only, no design) to `docs/scoreboards/photo-corpus/baseline-<sha7>.json`** via a `--summary` flag on `capture` or a short `python -c`; commit it as the standing instrument record.

- [ ] **Step 5: Copy `docs/photo-style-census-2026-10-27.md` from the main checkout into the lane; replace its "sibling logo census" placeholder with a pointer to the logo doc when it lands; add a "Standing scorecard" section pointing at the tool and the baseline file.**

- [ ] **Step 6: COOKBOOK "Running things": the before/after recipe for a photo PR**

```
python -m tools.photo_corpus fetch
python -m tools.photo_corpus capture --label base --base origin/main
python -m tools.photo_corpus capture --label head
python -m tools.photo_corpus sxs --before corpus_runs/base --after corpus_runs/head
# Kent clicks, exports verdicts-<a>-<b>.json
python -m tools.photo_corpus tally verdicts-<a>-<b>.json
```

- [ ] **Step 7: Full digitizer suite, then commit**

Run: `python -m pytest -q -n auto > ../corpus_runs/pytest.log 2>&1; echo EXIT=$? >> ../corpus_runs/pytest.log`
Expected: only the three named platform goldens red (`test_pushcomp`, `test_flat_lane_byte_identical`, `test_stage2_photo_segment`); `test_memory_budget`, `test_no_new_pro_renders`, `test_photo_corpus` green.

```bash
git add testdata/photo/corpus/corpus.json ../docs/scoreboards/photo-corpus/baseline-*.json ../docs/photo-style-census-2026-10-27.md ../COOKBOOK.md
git commit -m "Photo corpus: 21 logo rows, main baseline instrument record, census doc, COOKBOOK recipe"
```

### Task 8: PR

- [ ] **Step 1: Re-read the diff adversarially** (`git diff main...HEAD --stat`, then the tool file whole). Check no image or HTML is staged: `git diff main...HEAD --name-only | grep -Ei '\.(png|jpg|html)$'` prints nothing.
- [ ] **Step 2: Push, open ready-for-review against `main`, body: Kent's quote, the four commands, the baseline numbers table (labelled instrument readings), the gate-4 line, the sxs smoke screenshot described in words (no image). Arm auto-merge while `mergeable_state` is `blocked`.**
