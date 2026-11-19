# Prime grader runbook

Two procedures: the nightly run (a cloud session, Kent's choice 2026-11-17)
and the fair-test sitting (Kent's machine). Both use
`digitizer/tools/prime_grader.py`; COOKBOOK "The prime grader" explains the
tool.

## A. The nightly run

**Rubric 2026-11-18 (`RUBRIC_VERSION` in `prime_grader.py`).** The first card
written under it is a new baseline: it is not comparable with the 2026-11-17 or
2026-11-18 cards (round-capped renders, the old rubric), and `scorecard --prev`
prints "Not comparable" instead of a movement list. State that in the PR body.
`kit` draws flat-ended strips by default (`--caps round` restores the old
look, for a like-for-like check only).

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
   brief, `<ID>` and `<D>` filled in. **Set `model` on every one of these
   calls to the worker model Kent's 2026-11-02 ruling names** (memory
   `agents-cheap-models-2026-11-02`); a call that leaves it unset inherits
   the session's own model, which that ruling forbids. The first run
   (2026-11-17) left it unset by mistake, so its card was read by a
   different model than every later one: do not read a move between that
   card and the next as the engine's.

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

## C. The repeat test (the grader's agreement with itself)

How far the verdict moves when NOTHING in the engine changed: N fresh blind
readers on ONE kit. The first run is `repeat-2026-11-19.md`; repeat it after a
rubric change or a change of reader model, since either makes it a different
instrument. From `digitizer/`, with `R=eye_pairs_out/prime-repeat-<D>`:

1. Python as in A.1; one capture and one kit as in A.2, into `$R/run` and
   `$R/kit`.
2. For each round `k` of N (three is the measured setup), make `$R/verdicts-r<k>`
   and grade every design with a fresh reader, exactly as in A.3 (same brief,
   same `model`), except that the verdict goes to `$R/verdicts-r<k>/<ID>.json`.
   Run one round at a time (nine readers in one message). When a round is
   done, move its folder out of `digitizer/` (a scratch folder), so a later
   reader cannot list it; move them back before step 3. Do not look at the
   kit's pictures, `_sealed.json` or any scorecard until every verdict exists.
   Do NOT run `record`: the rounds are not a nightly card.
3. Score them against each other:

       .venv/bin/python -m tools.prime_grader repeat --kit $R/kit \
         --verdicts $R/verdicts-r1 $R/verdicts-r2 $R/verdicts-r3 --json $R/repeat.json

   It prints the grade kappa pooled over reader pairs (linear-weighted, CI95
   by bootstrap over designs, with n) and each pair's; each design's grades
   and spread; for every gross fault (ruins or noticeable) and every other
   reader, whether that reader put a fault of the same class within 3 mm,
   beside chance (a random stitched point's rate), overall and by class; and
   per design how many places seeded by a gross fault all, some or one of the
   readers found. Exit 2 means a verdict was missing or malformed; it says which.
4. Write the result as `docs/prime-grader/repeat-<D>.md` (numbers and words,
   no pictures). Commit only that and any code; never `$R`.
