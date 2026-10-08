# EMB-Bot — Fritsch's Stitches embroidery digitizer

EMB-Bot is Fritsch's Stitches' tool for turning artwork or typed text into
machine-embroidery stitch files that anyone can produce, without digitizing
expertise. It runs locally in the browser: a guided app (garment → content →
review → download) with a live stitch preview, no account and no subscription.

> **Public repo.** Everything committed here is world-readable. Do not add
> client artwork, customer names, third-party stitch files, credentials or
> legal correspondence without asking first.

## The three parts

| Part | Where | What it is |
|---|---|---|
| **JS engine** | `src/` (tests in `test/`) | Hand-written stitch math and file encoding: fill/satin, geometry, flatten, DST/EXP/PES writers, 85-font satin library (`src/fonts/`). Each module works as a browser `<script>` (global `EMB`) and as a CommonJS module. No npm dependencies. |
| **Studio** | `app/` | The product UI: Svelte 5 + Vite. Loads the engine from `src/` and has no CDN runtime dependencies. |
| **Python digitizer** | `digitizer/` | Image auto-digitizing engine (`digitizer_core/`) plus an optional FastAPI service (`digitizer_service/`, loopback only, port 8721) that the Studio uses for the image auto-digitize path. Own venv, own tests, own [README](digitizer/README.md). |

Text and lettering work without the Python service; only image
auto-digitizing needs it.

## Setup and run

You need **Node 22** (the engine has no dependencies; the Studio needs
`npm install`) and **Python 3.12** for the digitizer. The only difference
between platforms is the venv interpreter path:

| | Windows | Linux / macOS |
|---|---|---|
| venv Python | `.venv/Scripts/python` | `.venv/bin/python` |

### Digitizer (Python)

```bash
cd digitizer
python3.12 -m venv .venv          # Windows: py -3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # Windows: .venv/Scripts/python
.venv/bin/python -m digitizer_service                 # service on http://127.0.0.1:8721
```

Build the venv with **`python3.12` explicitly**, not a bare `python3`: the
project needs 3.12 or newer, and on 3.11 `requirements.txt` fails quietly
(no `pystitch`), after which the engine's format cross-validation tests skip
and still report green. Check with `.venv/bin/python -c "import pystitch"`.
If you install with `pip install -e ".[service,dev]"` instead, keep the `dev`
extra, which the service tests need.

Always run Python through `python -m` (`python -m pytest`,
`python -m digitizer_service`), never `python foo.py`, so the working
directory is on `sys.path`.

### Studio

```bash
cd app
npm install                        # first time only
npm run dev                        # http://localhost:5173
```

`npm run dev` first copies the engine and fonts into `app/public/` and, if
`digitizer/.venv` exists, starts the digitizer service for you (it never
blocks if the venv is missing). On Windows, `tools/start-emb-bot.ps1` starts
both servers in their own windows and opens the browser (`-NoDigitizer`
skips the service).

## Run the tests

There is no root `package.json`: three independent suites, each run from its
own directory.

```bash
node --test                        # engine, from the repo root (~1 min)
cd app && npm test                 # Studio unit tests (vitest, ~1 min)
cd app && npm run test:e2e         # Studio browser tests (Playwright)
cd digitizer && .venv/bin/python -m pytest -q -n auto     # digitizer
cd digitizer && .venv/bin/python -m pytest -q tests/test_service.py   # one file
```

Notes that save a wasted session:

- Engine and Studio suites are expected **clean**; any failure there is a
  regression. Re-run the Studio suite solo before blaming code if the machine
  was busy (font-decoding hooks time out under load).
- The engine's PES/EXP/DST cross-validation tests **skip** when the digitizer
  venv cannot import `pystitch`. A green run with skips proves less than it
  looks.
- A full local digitizer run is slow (budget ~45 minutes on 4 cores; ~9 on a
  fast desktop). Start only one at a time, and redirect to a log
  (`pytest ... > log 2>&1; echo EXIT=$? >> log`) rather than piping to
  `tail`, which hides pytest's exit code.
- Three golden-file digitizer tests fail on machines that did not capture the
  golden; CI deselects them by node ID (see
  `.github/workflows/python-package-conda.yml`). A fourth failure is a real
  regression. OCR tests skip without the `tesseract` binary.
- CI runs `engine`, `studio`, `studio-e2e` and a sharded `digitizer` job, all
  required on `main`. The digitizer job takes well over 15 minutes, so three
  green checks is not a green PR.

## Rebuilding the font library

```bash
node tools/build-embf.mjs          # needs the gitignored scratch_ink/ clone
```

Only fonts classified **verified** ship; the tier rules are in `COOKBOOK.md`.

## Outputs

| Format | Machine | Notes |
|---|---|---|
| **.DST** | Tajima | Primary and most reliable; default. |
| **.EXP** | Melco | Standard support, including trims. |
| **.PES** | Brother | Best effort: reverse-engineered, always test-stitch first. |
| **.PNG / .SVG** | n/a | Preview image / vector outline (not stitch files). |
| **PDF worksheet** | n/a | Printable sheet with preview, dimensions, counts and thread sequence. |

The digitizer service can also export other formats (JEF, PEC, VP3, XXX,
U01); `GET /health` lists them.

## Honest limits

EMB-Bot is a strong auto-digitizer for **clean, flat-color art**, not a
replacement for a professional digitizer on complex or critical work. Thread
cannot do continuous tone, very small text breaks up, and fabric presets are
starting points that need a sew-out to tune. For high-stakes jobs, check the
file in professional software before stitching.

## Read these next

Read the one that matches what you are about to do:

- **[`ROADMAP.md`](ROADMAP.md)**: before proposing work. Current phase and the
  hard gates (a gate is a refusal, not a preference).
- **[`COOKBOOK.md`](COOKBOOK.md)**: before touching code. Architecture, how to
  run things, working conventions, and the failure classes to expect.
- **[`PRODUCT.md`](PRODUCT.md)**: before a scope call. Launch scope and
  non-goals.
- **[`DOCTRINE.md`](DOCTRINE.md)**: before proposing work. What has already
  been decided, tried or disproved.
- **[`MASTER_SCOPE.md`](MASTER_SCOPE.md)**: current status of every capability
  area and how far to trust it.
- **[`CLAUDE.md`](CLAUDE.md)**: instructions and known traps for Claude
  sessions; worth a skim for humans too.
- [`digitizer/README.md`](digitizer/README.md): the Python engine and service
  in depth. [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md): index of
  narrative history and decisions.
