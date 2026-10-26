---
name: digitize-speed-2026-10-26
description: Task 19 speed profile -- tesseract reads now batched four at a time (preflight 2.3-2.8x, byte-identical); a loaded laptop inflates process_time ~2.6x; the gate costs ~0 since #1112; Studio poll 300 s vs service 600 s mismatch, Kent's call
metadata:
  type: project
---

2026-10-26, task 19 (follows PR #693, which had swapped two skimage calls). Profiled Fremont, Becker large, MFab hat and ProSeal one job
at a time under the shared `cpu.lock`, on main 5cf8da43.

**Fixed:** `legibility.read_side` ran 24 serial tesseract reads per text
cluster in preflight (144 on Fremont). `_ocr_all` now runs them four at a time
and judges them in the serial order. Preflight wall dropped 2.3-2.8x (Fremont
46.2 -> 17.6 s). Every DST and preflight report was byte-identical, against
main and serial-vs-parallel on the same result.

**Trap:** `process_time` is NOT honest on a busy laptop. The MFab hat read
212.9 s CPU under load and 80.0 s quiet, with the SAME DST md5. Take timings
under `cpu.lock` with the machine quiet.

**Trap:** a child's CPU is invisible to `process_time`, and a venv's
`python.exe` is a launcher, so GetProcessTimes on rembg's handle reads ~0.
A Windows job object counts the grandchild (`procs == 2`). The scratch
`speed_rembg.py` does this for rembg and for pytesseract's Popen.

**The gate is no longer a cost:** since #1112 `sew_enclosed_white` is ON for
everyone, so MFab's stages 5-7 read 101.0 s ON against 102.6 s OFF (profiled).

**Written up, not fixed (busy files):** the Column lane's sewn judge
(`outline_cut._judged_overlong`, 59 s of MFab's 102 s in stages 5-7, W5-02's
file) builds the same column repeatedly, so a per-letter `build_column` memo is
the proposal. Also the tagger's serial OCR (`textcluster.py`) and Fremont's
`rag_mean_color`.

**Timeouts, Kent's call:** the Studio stops polling at 300 s and says the job
"was stopped". The service runs it for up to 600 s on its only worker, so
re-pressing unchanged re-attaches, while "crop it" queues behind it. rembg has
a 60 s limit and falls back silently.

**How to apply:** before quoting a speed number, say the machine's load and
the engine sha; a CPU figure from a busy laptop can be off by 2-3x.
