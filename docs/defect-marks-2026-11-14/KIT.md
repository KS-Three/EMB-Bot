# defect-marks-1114: the photo subject-recall kit (built 2026-11-14)

The pre-registration is `subject-recall-preregistration.md` (commit `34bc7177`).
It was pushed before any render existed. This file records how the kit came
out. It does not change the pre-registration.

- **Kit:** `digitizer/eye_pairs_out/defect-marks-1114/` in the live checkout
  (gitignored), kit sha256 `ffd15392…`, **14 items**. Every item was rendered
  on one tree, `838b28ff` (code = `origin/main` `dcd21120`), 80 mm wide,
  left chest. Sizes run 80.5–80.6 mm wide by 45.6–117.9 mm high, except
  `pencil_sketch` at 76.2 × 90.6 mm. Each one is listed in `kit.json`.
- **Deviation: `stained_glass` is not in the kit.** It timed out at the
  capture's 1200 s limit twice. The first time, other work was sharing the
  CPU. The second time it ran alone, from a detached checkout of the same
  commit. (It took 842 s on `950855bf`; on 10-27 it also timed out.) The
  pre-registered set was 15; the sitting has 14. `group_people` also timed out
  once while the CPU was shared, and on a solo rerun it finished in 316 s.
- **Built by:** `build_kit.py` beside this file:
  `python ../docs/defect-marks-2026-11-14/build_kit.py --root <live digitizer/> --corpus-dir <live corpus/>`,
  one digitize at a time. Runs are in `digitizer/corpus_runs/subject-1114-838b28ff/`.
- **Serve** (from the live checkout's `digitizer/`):
  `.venv/Scripts/python.exe -m tools.defect_marks serve --kit eye_pairs_out/defect-marks-1114 --port 8739`,
  then open `http://127.0.0.1:8739/`. Kent's answers go to
  `eye_pairs_out/defect-marks-1114/marks.json`, written before each request
  returns.
- **Checked before the sitting:** all 28 pictures (14 artworks, 14 renders)
  answer 200 and decode. The page's embedded kit carries no preflight grade
  and no metric. `/marks` is empty, and there is no `marks.json`, so no test
  pin was written.
- **Nothing is scored** until the foreman says Kent is done.
