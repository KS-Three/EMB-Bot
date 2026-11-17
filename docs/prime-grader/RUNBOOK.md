# Prime grader runbook

Two procedures: the nightly run (a cloud session, Kent's choice 2026-11-17)
and the fair-test sitting (Kent's machine). Both use
`digitizer/tools/prime_grader.py`; COOKBOOK "The prime grader" explains the
tool.

## A. The nightly run

Cost, measured on the first run: about 950,000 tokens (nine readers at about
105,000 each) and under ten minutes of wall time after the venv is built.

1. **Python.** The container's `/usr/bin/python3.12` is 3.12.3 and cannot
   import `digitizer_core` (`digitizer/CLAUDE.md`).

       cd digitizer
       uv python install 3.12
       "$(uv python find 3.12.13)" -m venv .venv
       .venv/bin/pip install -q -e ".[service,dev]"

2. **Capture and kit** (`D` = today's date, UTC, `YYYY-MM-DD`):

       .venv/bin/python -m tools.prime_grader capture --out eye_pairs_out/prime-$D/run
       .venv/bin/python -m tools.prime_grader kit --run eye_pairs_out/prime-$D/run --out eye_pairs_out/prime-$D/kit
       mkdir -p eye_pairs_out/prime-$D/verdicts

   A design whose capture did not finish is listed under `skipped` in
   `kit.json`; say so in the PR body and carry on with the rest.

3. **Grade, blind, one fresh reader per design.** Do NOT look at the kit's
   pictures yourself, and do not open `docs/prime-grader/latest.json` or any
   scorecard before step 4. For each item id in `kit.json`, start one
   subagent (all in one message, so they run together) with exactly this
   brief, `<ID>` and `<D>` filled in:

   > You are a blind grader of ONE machine-embroidery render. Work only in
   > `digitizer/`.
   > 1. Read `tools/prime_grader_rubric.md` in full and follow it exactly.
   > 2. Your design is item `<ID>`. In `eye_pairs_out/prime-<D>/kit/kit.json`
   >    find that item (its size and its list of tiles). Do NOT open
   >    `_sealed.json`, `readings.json`, anything under `docs/`, any memory
   >    file, or any other item's pictures.
   > 3. Look at every picture of the item in `eye_pairs_out/prime-<D>/kit/img/`:
   >    `<ID>_overview.png`, every `<ID>_tile_<name>.png` listed in kit.json,
   >    and `<ID>_travel.png`. Read every tile against its patch of the
   >    original. Read fault positions off the mm rulers.
   > 4. Write your verdict as JSON, in the shape the rubric gives, to
   >    `eye_pairs_out/prime-<D>/verdicts/<ID>.json`.
   > 5. Validate it: `.venv/bin/python -m tools.prime_grader record --kit
   >    eye_pairs_out/prime-<D>/kit --verdict
   >    eye_pairs_out/prime-<D>/verdicts/<ID>.json --check`. Fix the file until
   >    it says "well formed". Do NOT run record without `--check`.
   >
   > Grade as a paying customer and a professional digitizer would, neither
   > kind nor harsh. Reply with only the grade, the fault count by severity,
   > and one sentence on what most holds the design back.

4. **Record and write the card** (one `record` at a time; they share a file):

       for f in eye_pairs_out/prime-$D/verdicts/*.json; do
         .venv/bin/python -m tools.prime_grader record --kit eye_pairs_out/prime-$D/kit --verdict "$f"; done
       .venv/bin/python -m tools.prime_grader scorecard --kit eye_pairs_out/prime-$D/kit \
         --out ../docs/prime-grader --prev ../docs/prime-grader/latest.json --date $D

   Pass `--prev` BEFORE the command overwrites `latest.json`: it is read
   first, so the line above is safe as written.

5. **Commit only** `docs/prime-grader/scorecard-$D.md`, `scorecard-$D.json`
   and `latest.json`. Never the kit: it holds client artwork. Open a PR ready
   for review, arm auto-merge, and put in the body: the grade row, each
   design under "Since the last scorecard", and any skipped design. State
   that the figures are instrument readings (ROADMAP gate 4).

6. **Do not act on it.** No flag flip, no engine change, no issue filed. If a
   design dropped two grade steps or gained a `ruins` fault, say so at the top
   of the PR body; the fix is a separate, human-started piece of work.

## B. The fair-test sitting (Kent's machine)

The first run could not be compared cleanly with Kent's marks: his were made
on older renders (`README.md`). This puts Kent and the readers on the SAME
renders. From `digitizer/` on his machine, with `K=eye_pairs_out/prime-sitting-<date>`:

    python -m tools.prime_grader capture --out $K/run
    python -m tools.defect_marks kit   --out $K/marks --pro $K/run
    python -m tools.prime_grader kit   --run $K/run --out $K/kit
    python -m tools.defect_marks serve --kit $K/marks        # Kent marks at http://127.0.0.1:8736

Nine designs (Bridge and ProSeal are skipped: `prime_grader capture` runs
only the designs whose files are committed). While or after he marks, grade
`$K/kit` with fresh readers as in A.3 and A.4 (verdicts under `$K/verdicts`),
without opening `$K/marks/marks.json` first. Then:

    python -m tools.prime_grader kent --kit $K/kit --marks $K/marks/marks.json --json $K/against-kent.json

Report the grade kappa with its interval and n, the pins found at his spot
beside chance, and the by-class rows. Copy `marks.json` and the report to
`docs/prime-grader/sitting-<date>/` (text only, no pictures).
