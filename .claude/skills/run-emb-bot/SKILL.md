---
name: run-emb-bot
description: Launch, build, drive, screenshot, and test EMB-Bot — the Svelte Studio app, the JS stitch engine's Node harness, and the Python digitizer service. Use when Kent says "run embot", "run emb bot", "start embot", "pull up emb bot", or otherwise asks to run, start, build, screenshot, verify, or test EMB-Bot, or after changing src/, app/, tools/, or digitizer/.
---

# Running EMB-Bot

Two independent stacks: a browser-side JS stitch engine (the product, no
backend) and an optional Python auto-digitizer service on `127.0.0.1:8721`.

**Paths below are relative to the repo root.** Run the driver from the repo
root or with an absolute path — see Troubleshooting.

## First — decide which kind of "run" this is

Getting this wrong wastes the most time of anything in this file.

**Kent wants EMB-Bot in his own browser** ("run embot", "pull up emb bot").
He is on **Windows**. A server you start in a cloud sandbox lives on *your*
localhost and his browser can never reach it — there is no tunnel out. Give
him the *Launch on Kent's machine* block, and if he wants to see something
now, drive it here and send screenshots.

**You need to run it yourself** to verify a change. That's everything else
in this file.

Ambiguous? Ask before starting anything.

---

## Run (agent path) — the driver

`.claude/skills/run-emb-bot/driver.mjs` is a headless-Chromium harness for
the Studio. It starts the dev server if one isn't up, drives the real UI,
and writes screenshots.

Written because `chromium-cli` is **not** on PATH in this sandbox class and
the `playwright` MCP server is session-scoped — neither is something a future
agent can count on. Playwright itself resolves out of `app/node_modules`.

### One command — proves both lanes work

```bash
node .claude/skills/run-emb-bot/driver.mjs smoke --serve --port 5199
```

Runs the lettering lane (pure browser engine) and, **if** the digitizer
service is answering on 8721, the artwork auto-digitize lane. Starts its own
Vite on 5199 and tears it down. Verified output:

```
  text lane: 2452 stitches · 127×16 mm · 5×7 in hoop
  artwork lane: 2,166 stitches · 80×17 mm · 2 colors
```

Exit 0 = both lanes produced real stitches and nothing unexpected hit the
console. Drop `--serve` to reuse a dev server you already have on 5173.
Screenshots → `/tmp/emb-shots/` (`--shots <dir>` to move them).

### Interactive — pipe commands to the REPL

```bash
node .claude/skills/run-emb-bot/driver.mjs repl <<'EOF'
btn Logo patch
upload input[type=file] app/e2e/fixtures/enthusiast_logo.png
waitbtn Digitize
btn Digitize
ss my-shot
net 8721
console errors
EOF
```

Each command prints `<< <name>` when it finishes (`<< ERR …` on failure,
which never kills the REPL), so a tmux-driven caller can poll
`capture-pane` for the marker instead of sleeping.

| command | what it does |
|---|---|
| `nav [path]` | goto base URL + path |
| `ss [name]` | screenshot → `/tmp/emb-shots/NN-name.png` |
| `outline` | headings + every visible button/input, with labels — **use this instead of dumping HTML** |
| `btn <label>` | click a button by text; **exact match first**, then substring; prints what it resolved and how many matched |
| `waitbtn <label>` | wait for a button whose text is exactly this (needed after `upload`) |
| `click <sel>` / `fill <sel> <v>` / `type <sel> <v>` / `press <key>` | raw Playwright |
| `upload <sel> <path>` | real file upload, path relative to repo root |
| `wait <sel>` / `waittext <text>` | wait for a selector / text |
| `text <sel>` / `html [sel]` / `eval <js>` | read the page |
| `net [filter]` | requests the page made — `net 8721` shows whether a click reached the digitizer |
| `console [errors]` | console messages, each with the URL that produced it |
| `reload` / `quit` | |

`eval` takes an expression and awaits a promise, so you can poll:

```bash
eval new Promise(r=>setTimeout(()=>r(document.body.innerText.match(/[\d,]+ stitches[^\n]*/)?.[0]||'none'),30000))
```

---

## Prerequisites

**No `apt-get` was needed** in this container. Node 22 and `/usr/bin/python3.12`
were already present, and Chromium is pre-cached at `/opt/pw-browsers/chromium`
(the driver and `app/playwright.config.js` both pin that path — outbound access
to Playwright's browser CDN is blocked here, so an unpinned launch fails with
no download fallback).

`tesseract` is **not** installed; the digitizer's OCR tests skip rather than fail.

## Setup

```bash
cd app && npm install                      # ~6s warm, 152 packages
```

Digitizer (only needed for image auto-digitize). **`python3.12` explicitly** —
the default `python3` here is 3.11 and `pyproject.toml` sets
`requires-python = ">=3.12"`:

```bash
cd digitizer
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[service,dev]"    # a few minutes: OpenCV, scipy, scikit-image
.venv/bin/python -m digitizer_service &                # binds 127.0.0.1:8721
curl -s http://127.0.0.1:8721/health | head -c 200     # {"status":"ok","service":"digitizer",...}
```

On Linux it's `.venv/bin/python` — the digitizer README shows the Windows
`.venv/Scripts/python.exe` form throughout.

## Direct invocation — no browser

Hit the service straight (this is how to check a digitizer change without the UI):

```bash
curl -s -X POST http://127.0.0.1:8721/digitize \
  -F "image=@app/e2e/fixtures/enthusiast_logo.png;type=image/png" \
  -F 'config={"target_width_mm":80,"max_colors":6}'
# -> {"job_id":"…","state":"running","cached":false}
curl -s http://127.0.0.1:8721/jobs/<job_id>
# done -> stats: {"stitch_count": 2351, "color_changes": 1, "trims": 20,
#                 "jumps": 37, "size_mm": [80.5, 16.6], "thread_m_total": 4.57}
```

The **JS** engine's own digitize path is separate and reachable from Node:

```bash
node tools/run-digitize.mjs app/e2e/fixtures/enthusiast_logo.png
# -> {"colors":2,"stitches":6536,"satin":6,"fill":7,"sizeMM":[127,25.4]}
```

Also in `tools/`: `run-flatten.mjs` (color-flatten only), `render-dst.mjs`
(DST → PNG for visual inspection), `png.mjs` (decode/encode helper).

## Test

```bash
node --test                    # engine: 356 tests, 350 pass, 6 skip, ~6.5s
cd app && npm test             # Studio vitest: 40 files, 768 tests, ~27s
cd app && npx playwright test  # e2e: 13 tests in 7 spec files, ~48s
cd digitizer && .venv/bin/python -m pytest -q -n auto
```

`npx playwright test` starts its own dev server on **5183** and stops it, so
nothing needs to be running first. It also **auto-starts the digitizer**
itself if `digitizer/.venv` exists (it checks both `bin/python` and
`Scripts/python.exe`).

### Reading a digitizer run

`3 failed, 1218 passed, 8 skipped, 8 xfailed` in ~7min (`-n auto`, 2026-08-20,
this container). **Judge the run by its failure classes, not the count** —
COOKBOOK.md "Running things" is the authority. The three that fail here are
all expected class #1, golden/byte-identical mismatches on a machine that
didn't capture the golden:

```
tests/test_flat_lane_byte_identical.py::…[photo/enthusiast_logo.png]
tests/test_pushcomp.py::…[logo_whitebg.png-towel]
tests/test_stage2_photo_segment.py::…[photo/enthusiast_logo.png]
```

There are now **three different** golden-failure sets in play: CI deselects
its own 3 by node ID, Kent's Windows machine fails a different 3, and this
Linux container fails the 3 above. Don't assume another environment's list
matches yours — and don't "fix" a golden to make it pass.

A failure **outside** that class, or in `node --test` / `npm test` (both
expected clean), is a regression.

The 8 skips include the OCR tests, which need the `tesseract` binary — a
separate non-pip install, absent here.

## Run (human path — Kent's Windows machine)

One command; it resolves the repo root from `$PSScriptRoot`, so there is no
path to fill in:

```powershell
.\tools\start-emb-bot.ps1          # -NoDigitizer to skip the Python half
```

Or two windows by hand (each blocks until Ctrl+C, so they can't share one):

```powershell
cd <repo>\app ; npm install ; npm run dev
cd <repo>\digitizer ; .venv\Scripts\python -m digitizer_service
```

Then browser → `http://localhost:5173`, **with** the `http://` prefix.

### Confirmed failure modes on Kent's machine

Each has actually happened; check in this order.

1. **No server running.** `Test-NetConnection -ComputerName localhost -Port 5173`
   → `TcpTestSucceeded : False` means start Window 1, not debug the browser.
   (`PingSucceeded : True` only says loopback resolves.)
2. **`Test-NetConnection` with no arguments** silently checks
   `internetbeacon.msedge.net` and reports success while telling you nothing.
3. **URL typed into PowerShell** → `CommandNotFoundException`. It goes in the
   address bar.
4. **Scheme omitted** — Chrome/Edge auto-upgrade bare `localhost:5173` to
   HTTPS; Vite serves plain HTTP.
5. **A different port.** Vite auto-increments to 5174, 5175… and prints what
   it bound. `start-emb-bot.ps1` assumes 5173 and will open the wrong URL.
6. **Server never started.** `app/scripts/copy-engine.mjs` hard-throws
   `missing engine file: <name>` if any of the **22** files it copies is
   absent from `src/`; it runs in `predev`, so Vite never boots. The error is
   above where the Vite banner would be.
7. **Wrong tree.** A `.claude/worktrees/` lane has its own `node_modules` and
   `src/`. `git worktree list` confirms which is being served.
8. **Python too old.** `requires-python = ">=3.12"`; on 3.11 the install dies
   with `Package 'digitizer-core' requires a different Python`. `py --list`,
   then use the launcher form `py -3.12` (a bare `python` may resolve older).

---

## Gotchas

These are the ones that cost real time here.

- **`btn Digitize` clicks the wrong thing if you substring-match.** Three
  controls match "Digitize": the element chip **"Digitized · empty"** (first
  in DOM order), **"Digitize as flat art"** (only flips `forced_class`), and
  the real **"Digitize"**. Clicking the chip *succeeds* and submits nothing —
  you then debug the service for an hour. The driver's `btn` tries exact
  first and prints every candidate; `net 8721` confirms a POST actually left.

- **The Digitize button does not exist right after `upload`.** It mounts only
  once the file has been read into `sourcePng`. Immediately after upload, *no*
  button matching `/digitiz/i` is in the DOM. Always `waitbtn Digitize` first.

- **The service rejects unknown config fields with 400.** It's
  `target_width_mm`, not `width_mm` →
  `{"detail":"unknown config field(s): width_mm"}`. The allowlist is
  `PipelineConfig`'s 70 dataclass fields:
  `.venv/bin/python -c "from dataclasses import fields; from digitizer_core.config import PipelineConfig; print(sorted(f.name for f in fields(PipelineConfig)))"`

- **`app/scripts/ensure-digitizer.mjs` is Windows-only.** It looks for
  `.venv/Scripts/python.exe` and, on Linux, just warns
  `digitizer venv not found (…Scripts/python.exe)` and exits 0. So
  `npm run dev` **never** auto-starts the digitizer here — start it yourself.
  (The e2e specs handle both layouts; only this predev hook doesn't.)

- **A green `npx playwright test` can be a smaller run than you think.** The
  digitize specs `test.skip` when the service is down. 13 tests pass with it
  up. Confirm the service is healthy before reading a green run as coverage.

- **Playwright *can* upload files.** `setInputFiles` on the hidden
  `input[type=file]` works headless — earlier notes here claimed agent
  browsers can't upload and that the `tools/` harness was the only way. It
  isn't; both paths work.

- **`npm run dev` survives a killed npm.** npm doesn't forward SIGTERM to
  Vite, so killing the wrapper leaves the port bound and the next run dies on
  `EADDRINUSE`. The driver spawns `detached: true` and kills the whole process
  group. By hand: `lsof -ti:5173 -sTCP:LISTEN | xargs -r kill`.

- **Never pipe a test run to `tail`** — you get tail's exit code, so a red run
  reads green. (CLAUDE.md says this for pytest; it bites identically for the
  driver: `node driver.mjs smoke | tail` reported `EXIT=0` on a failing run.)
  Redirect to a file and read it.

- **A "404 Not Found" console error is almost always the favicon.** The
  message text is generic — the URL is only in `location()`. The driver
  records and prints it; its smoke filters favicon 404s and the digitizer
  probe's `ERR_CONNECTION_REFUSED` (expected when the service is down).

- **`node --test` and `tools/run-digitize.mjs` write into the repo root** —
  `scratch_flat.png`, `scratch_new.dst`, `scratch_new_colors.json`. Gitignored,
  but per CLAUDE.md footgun #5 `scratch_*` is *not* safe to delete blindly.

- **DST orientation.** When checking DST for *correctness* rather than
  round-tripping, decode through pyembroidery/the service's `/export`, never
  `src/dstimport.js` — CLAUDE.md footgun #1.

## Troubleshooting

- **`Cannot find module '…/app/.claude/skills/run-emb-bot/driver.mjs'`** —
  you're in `app/`. The path is relative to the **repo root**; use an absolute
  path or `cd` up first.

- **`nothing serving http://localhost:PORT — start it, or pass --serve`** —
  the driver won't guess. Add `--serve`, or start `npm run dev` yourself.

- **Driver appears to hang with no output** — `repl` mode blocks on stdin by
  design. Pipe it a heredoc, or use `smoke`.

- **`ERROR: Package 'digitizer-core' requires a different Python: 3.11.x not
  in '>=3.12'`** — you used the default `python3`. Use `python3.12 -m venv`.

- **Studio console shows repeated `ERR_CONNECTION_REFUSED` to 127.0.0.1:8721** —
  the digitizer isn't running. Expected; text/lettering is unaffected and the
  Content step shows an offline note with a "check again" link.

## Standalone bundle — deleted, do not rebuild

`EMB-Bot-standalone.html` was deleted 2026-08-04 (Kent's call) and
`tools/bundle.mjs` is dead code. Test `EMB-Bot.html` + `src/`, or the Studio.

## Where things live

Architecture is in COOKBOOK.md; the DST axis bug is CLAUDE.md footgun #1.
Both are read before this skill, so they aren't repeated here.
