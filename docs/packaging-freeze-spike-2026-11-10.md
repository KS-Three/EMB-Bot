# Packaging freeze spike, 2026-11-10

**Question:** can the Python digitizer service be frozen into a folder a
customer double-clicks, and does the frozen engine sew the same file?

**Answer: yes on both, on the three fixtures tried.** Design, review payload,
warnings, DST bytes and PES bytes are identical between the frozen exe and the
venv service. Not yet tried: a clean machine, the photo lanes, an installer.

**Why now.** `docs/organic-review-2026-09-22.md` §2.1 found that nobody can
install the product and no checklist row says so. The hosted-site answer
(PR #550) was built and then reversed by Kent on 2026-09-28. On 2026-11-10 he
picked the vehicle: **one local Windows app, in which the service also serves
the built Studio** (PRODUCT.md launch row 8). This spike is step 1 of that.

## Result

Frozen exe run with `PATH` cut to `C:\Windows\System32;C:\Windows` and its
working directory outside the repo, against the venv service at `ac3d77fa`.
Default config: the request names no option.

| Fixture | Stitches (venv / frozen) | Design | Review | Warnings | DST | PES | JEF |
|---|---|---|---|---|---|---|---|
| `logo_whitebg.png` | 6711 / 6711 | same | same | same | same, 20,732 B | same, 42,939 B | differs |
| `becker_marine_logo.png` | 11111 / 11111 | same | same | same | same, 33,962 B | same, 68,293 B | differs |
| `logo_script_tires.png` | 2515 / 2515 | same | same | same | same, 8,087 B | same, 16,267 B | differs |

Every export on both sides came back `X-Export-Verified: true`.

**The JEF difference is the clock, not the freeze.** pystitch's JEF writer
stamps `YYYYMMDDHHMMSS` at offset 8. Two writes of one pattern two seconds
apart, in ONE process, differ at exactly one byte (offset 21, `...092116`
against `...092118`). So no two JEF exports of the same design have ever been
byte-identical, and `packaging/freeze_check.py` reports JEF without comparing
it.

**OCR runs from bundled data.** `/health` reports `capabilities.ocr: true`
with the system Tesseract off `PATH`, and `false` when the bundled `tessdata/`
folder is renamed away. `eng.traineddata` (4.1 MB) is the only file needed;
`tesserocr`'s wheel carries the engine.

## Numbers

| | |
|---|---|
| Folder | 415 MB, 430 files |
| Zip (`Compress-Archive -CompressionLevel Optimal`) | 166.9 MB |
| Largest | `cv2` 137 MB (`cv2.pyd` 107, `opencv_videoio_ffmpeg500_64.dll` 29), `scipy` 49 + 40 MB of OpenBLAS, ICU data 32 MB |
| Import to app built | 2.86 s (printed by the exe) |
| Launch to first `/health` | about 3.5 s (3.43 on each of three runs, so the poll loop is quantizing it: read it as coarse) |
| Job time, venv / frozen | 4.7 / 4.1 s, 13.8 / 13.2 s, 8.1 / 7.7 s |
| Build | 91 s, PyInstaller 6.22.3, Python 3.14.6, one-folder |

Installer compression (LZMA) is unmeasured and will beat the zip. Nothing was
pruned: the ffmpeg DLL alone is 29 MB the engine has no known use for.

## What the frozen service is missing

- **`/health` `engine.commit` is `null`.** The stamp shells out to `git` in
  the engine's directory, and a frozen folder is not a checkout. `defaults_sha`
  survives (same value as the venv). A build-time version stamp is step 4's.
- **`background_removal` and `sam2` read `false`.** Their isolated venvs are
  not bundled. Both are default OFF, and SAM2 is post-v1 by the 2026-08-11
  ruling, so this is the intended v1 shape, not a regression.
- **Two build warnings**, neither with an effect on these fixtures: hidden
  imports `tzdata` and `scipy.special._cdflib` not found.

## What this does NOT show

- **A clean machine.** Same laptop with `PATH` stripped is not a PC without
  the VC++ runtime or with a different CPU. Needs a second machine or a VM.
- **The photo and gradient lanes**, `/lettering`, `/digitize-manual`, the
  calibration routes. Three flat-lane logos is the whole sample.
- **Python 3.12.** The spike froze Kent's 3.14 venv; CI pins 3.12. The
  release build has to pick one and re-run this on it.
- **Antivirus.** One-folder was chosen over one-file because one-file
  unpacks to `%TEMP%` on every start and draws more false positives; nothing
  here measured either.

## Recipe

Run from `digitizer/`. PyInstaller goes in a THROWAWAY venv, not the
project's: a `.pth` file makes the project venv's wheels visible to it, so the
frozen binaries are the very files the tests ran against and nothing is
installed beside the pinned set.

```bash
python -m venv /tmp/freeze-venv
/tmp/freeze-venv/Scripts/python -m pip install pyinstaller
# one line: the absolute path of digitizer/.venv/Lib/site-packages
echo "<repo>\digitizer\.venv\Lib\site-packages" > /tmp/freeze-venv/Lib/site-packages/digitizer_wheels.pth
mkdir tessdata && cp "<Tesseract-OCR>/tessdata/eng.traineddata" tessdata/

/tmp/freeze-venv/Scripts/python -m PyInstaller --noconfirm --onedir --console \
  --name embbot-digitizer --paths . \
  --collect-submodules digitizer_core --collect-submodules digitizer_service \
  --add-data "digitizer_core/chart_data;digitizer_core/chart_data" \
  --add-data "digitizer_core/outline_fonts;digitizer_core/outline_fonts" \
  --add-data "digitizer_core/model_data;digitizer_core/model_data" \
  --add-data "tessdata;tessdata" \
  --exclude-module pytest --exclude-module _pytest --exclude-module xdist --exclude-module pip \
  packaging/freeze_entry.py
```

Then one service at a time (two digitizes at once move the job times):

```bash
.venv/Scripts/python -m digitizer_service --port 8731 &
.venv/Scripts/python packaging/freeze_check.py run http://127.0.0.1:8731 venv.json \
  testdata/logo_whitebg.png testdata/becker_marine_logo.png testdata/logo_script_tires.png
# stop it, then:
PATH="/c/Windows/System32:/c/Windows" dist/embbot-digitizer/embbot-digitizer.exe 8732 &
.venv/Scripts/python packaging/freeze_check.py run http://127.0.0.1:8732 frozen.json \
  testdata/logo_whitebg.png testdata/becker_marine_logo.png testdata/logo_script_tires.png
.venv/Scripts/python packaging/freeze_check.py compare venv.json frozen.json   # exit 0 = identical
```

The three `--add-data` lines are every directory the engine opens by
`Path(__file__)`: thread charts, the outline-font starter set, the YuNet face
model. A new one added to `digitizer_core` without a line here is a frozen
build that fails only on the route that reads it.

## Step 2, landed with this record: one port

`python -m digitizer_service --studio ../app/dist` serves the built Studio at
`/` from the service's own port (`digitizer_service/studio.py`, off by
default). Driven 2026-11-10 on port 8731 against a production build: the page
loads with the engine global present and no console error, `/health` and the
fonts answer from the same origin, engine files revalidate as 304, and typing
FRITSCH gives 96 x 14 mm, 1,296 stitches with Download enabled.

Three things found on the way, each now pinned in
`tests/test_service_studio.py`:

- **The first version printed its URL and served a 404.**
  `digitizer_service/__init__.py` imports `app`, so under `python -m` the app
  is built before `__main__` parses a flag, and the environment variable set
  there arrives after the one moment `app.py` reads it. Eighteen tests passed
  while that was true, because they set the variable from outside. Found by
  starting the real command and asking for `/`.
- **Content type must not come from the machine.** Python reads `.js` from
  the Windows registry; a machine where that says `text/plain` gets a Studio
  whose module scripts the browser refuses.
- **`engine/*.js` keeps its name across releases**, so every response carries
  `Cache-Control: no-cache` or an updated app runs the old engine.

**The port has to stay 8721, always.** Saved projects live in `localStorage`,
which a browser keys by origin: `127.0.0.1:8722` is a different, empty Studio.
A launcher that finds 8721 busy must reuse its own running instance or stop
with a message. "Next free port" would look like the customer's designs had
been deleted. On 8721 the Studio needs no change at all: its default service
URL is already its own origin.

**One namespace, two owners.** The bundle's `fonts/` directory (manifest,
`.embf` binaries, previews) and the service's `/fonts/outline*` routes share a
prefix. They do not collide today, and API routes win where they would. A
file named `outline` in `app/public/fonts/` would be silently unreachable.

## Next

3. Launcher: fixed port and single-instance rule above, `TESSDATA_PREFIX`,
   open the browser, a way to quit, a log file.
4. Build script and a tag-triggered Windows CI job; version stamp for
   `/health`; prune and measure the installer.
5. A clean-machine run of this same check.

Kent's calls, not yet asked: a code-signing certificate (unsigned means a
SmartScreen warning), how an update is announced, and where installers are
hosted while billing is undecided.
