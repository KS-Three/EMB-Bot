# Digitized image study: the scripts and tables behind it

Supporting material for [`../digitized-image-study-2026-11-13.md`](../digitized-image-study-2026-11-13.md).
Saved 2026-11-16 so the two stitch-file measurements (rule 7, rule 12) can be
re-run and checked after the session that made them is gone.

Research scripts, kept as they ran. They are not pipeline code, have no tests,
and nothing imports them.

## What is here

| path | what it is |
|---|---|
| `tally.py` | counts over the per-picture study notes (kinds, rules, duplicates) |
| `rule7/reader.py` | the DST reader: colour blocks, grounds, pieces on a ground, under-cover |
| `rule7/synth.py` | the synthetic check the reader had to pass first (solid, tongue, gap) |
| `rule7/run_ours.ps1`, `run_all.py`, `summarize.py` | run our pipeline per job, read both sides, build the tables |
| `rule7/a_instrument.py`, `b_cartoons.py`, `b_summary.py` | the under-fill trace and the four cartoon fixtures |
| `rule7/results.md`, `tables.md`, `wide_pieces.txt` | the full write-up, per-file tables, and every piece 5 mm or wider |
| `rule12/reader.py`, `ring.py` | the same reader plus ring detection (contrast ring, own-colour ring) |
| `rule12/synth.py` | the synthetic check for rings (bare, contrast, own-colour, run line, widths) |
| `rule12/run_ours.py`, `run_ours_main.py`, `analyze.py`, `summarize.py`, `contrast2.py` | pipeline runs, per-piece rows, tables, thread contrast |
| `rule12/crops.py`, `mkcrops.py` | cut the look-at crops (art beside render) |
| `rule12/results.md`, `tables.md`, `contrast.md` | the full write-up, counts per file, contrast of unringed pairs |

## What is not here, and where it is

Kept out of this public repo on purpose, in the gitignored
`scratch_digitized_study/` of Kent's main checkout (local only, no backup):

- `scratch_digitized_study/images/`, `notes/`: the 119 study pictures
  (third-party work) and the per-picture notes.
- `scratch_digitized_study/measure/rule7/`, `measure/rule12/`: everything above
  plus the per-piece JSON (`results.json`, `rows.json`, `raw.json`), our DSTs
  for each job (`ours/<job>/ours.dst`), the run logs, and the crops and debug
  renders. The crops show the professional's stitch files, so they may not go
  under `docs/` (`digitizer/tests/test_no_new_pro_renders.py`).

The `results.md` files name `results.json`, `crops\` and `peek*.py`; those are
in the local folder, not here.

## To run one again

1. The professional's files come from `scratch_kent/pro_intake/registry.json`,
   which is also gitignored. Without it only `synth.py` runs.
2. Each script sets `REPO` to Kent's main checkout by absolute path and writes
   beside itself. Change `REPO`, and run from the digitizer venv
   (`python <script>`; the scripts add `digitizer/` to `sys.path` themselves).
3. Order: `synth.py` (must read as its log says), then the pipeline runs
   (`run_ours.ps1` / `run_ours.py`, one job at a time, 33 to 82 s each), then
   `run_all.py` / `analyze.py`, then `summarize.py`.

## Read before quoting a number

- Our DSTs were made on main `19013abe` (2026-11-13). Main has moved since;
  nothing here was re-run on a later commit, and the one attempt (MFab on
  `336e2eb3`) was cut off and is unverified.
- Ring and ground calls rest on the reader's geometric constants (0.4 mm thread,
  0.55 mm opening, 4.5 mm own-colour blind spot). They are reading choices, not
  physical constants.
- "In the artwork or added" for rule 12 was decided by eye from crops.
