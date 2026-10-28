# Photo corpus side-by-side scorecard — design

Date 2026-10-27. Kent's words, after the 18-genre photo census
(`docs/photo-style-census-2026-10-27.md`): "it's as if this digitize was only
building tools to improve the photos we had on hand. This digitizer needs to be
building tools that help and improve ALL photos." Asked what he wants to look at
to judge a photo PR: "Sxs comparison w/ an Artifact that I can say better or
worse." Then: "Make it an html, whatever idc, you know what I want." The rest of
this document is the builder's reading of that; every call below is the
builder's unless quoted.

## Intent

A standing cross-genre corpus of licence-clean Wikimedia Commons images (the
census's 18 photos, plus the logo census's 21 when its manifest lands), a tool
that digitizes all of them at a given tree with the Studio's own request, and a
single self-contained HTML page that puts each row's `main` render beside the
PR's render with the instrument numbers under both and better / same / worse
buttons Kent clicks. His clicks export as a JSON file that is committed as the
PR's quality evidence. A photo PR is judged by Kent across all genres, not by
one fixture and not by a number.

## Goals

- One command fetches the corpus from Commons into a gitignored folder with a
  licence manifest; the committed list carries titles, page URLs and licences
  only. Nothing downloaded is ever committed (public repo).
- One command captures a run: every row digitized in its own process with a
  per-row timeout, a render and the instrument numbers saved per row, stamped
  with the tree's commit. `--base REF` captures the merge-base tree so a stale
  baseline cannot flatter a PR.
- One command builds the side-by-side HTML from two runs. Rows grouped by kind
  then genre. Each row: source thumbnail, before render, after render, numbers
  before / after / delta, three verdict buttons, a free-text note. A row that
  timed out or errored in either run still appears, with the failure as its
  tile. "Export verdicts" downloads JSON. Verdicts persist in the page's
  localStorage until exported.
- One command files an exported verdict JSON under
  `docs/scoreboards/photo-corpus/` and appends a tally line (date, before and
  after shas, better / same / worse counts by kind, the slugs judged worse).

## Non-goals and anti-goals

- Not a golden, not a CI gate: no row fails a build on its own. Capture takes
  hours (the census had 7 of 18 rows over 600 s), so it runs by hand before a
  photo PR is opened, never in CI.
- No quality claim from a number (ROADMAP gate 4). SSIM and ΔE are shown as raw
  instrument readings and labelled so; the one chance-corrected figure defines
  its null in the page. The verdict column is Kent's alone.
- No new pipeline behaviour, no flag flips, no stage-0 recalibration (gate 2).
- No image, render or HTML under `docs/`; `test_no_new_pro_renders` and the
  public-repo rule both stand.

## Constraints

- Public repo: committed corpus rows must be CC0, public domain, CC BY or
  CC BY-SA, with the Commons page and author on every row and in the HTML.
  The fetch re-reads the live licence and refuses a row whose licence left
  that set.
- Request contract: rows are digitized with `tools.fremont_triage.studio_request`
  (the Studio's real `/digitize` config) at 80 mm, `garment_id` `left_chest`,
  as the census was.
- Each digitize runs in a subprocess with `cwd` = the tree under test, so the
  before run imports the merge-base's `digitizer_core`
  (`tools.default_path_diff.merge_base_tree`) and the after run imports HEAD's.
  Env as `default_path_diff.RUNNER_ENV`.
- The HTML is one file, images inline as data URIs (the census sheet was
  15 MB at 18 rows; 39 rows with three images each is acceptable for a file
  Kent opens locally). It is written to a gitignored folder and sent to Kent,
  never committed.

## Decided here (builder's calls)

- Layout: `digitizer/tools/photo_corpus.py` with subcommands `fetch`,
  `capture`, `sxs`, `tally`; corpus list `digitizer/testdata/photo/corpus/corpus.json`;
  images beside it, gitignored except the list and a README; runs under
  `digitizer/corpus_runs/<label>/` (gitignored); verdicts and tally under
  `docs/scoreboards/photo-corpus/`.
- Instrument numbers per row: class and confidence, route, cutout background
  fraction removed, stitches, trims, colour changes, colours in design vs cap,
  size mm, stitches per cm², preflight grade and raw score (labelled raw),
  wall seconds and stage stamps, SSIM and ΔE (raw), and `fidelity_cc` =
  (SSIM − SSIM_null) / (1 − SSIM_null) where SSIM_null is the photo against a
  blank fabric-coloured frame of the same size. All labelled instrument
  readings.
- Timeout default 1200 s per row, 2 processes, both flags.
- Verdict JSON: `{"before": sha, "after": sha, "date", "rows": {slug:
  {"verdict": "better|same|worse", "note": str}}}`.

## Left to the builder

Thumbnail sizes, CSS, how the delta column colours, how `tally` orders its
table.
