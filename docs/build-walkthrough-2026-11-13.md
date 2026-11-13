# EMB-Bot build walkthrough, second pass — 2026-11-13

Second walkthrough of the Studio built from `main` at `84fe69d8` (after #1437). It covers what [the first one](build-walkthrough-2026-11-12.md) skipped: the Windows launcher, Compare, Simulate, garments and hoops, a photo-lane image, the stale-stitch cue, the re-made starters, and resizing. Nothing was changed; broken things are recorded, not fixed. Artwork used is already committed: the starter pack, `app/e2e/fixtures/{enthusiast_logo,two-squares}.png`, `digitizer/testdata/photo/photo_dof_meadow.png`. Images are in [`build-walkthrough-2026-11-13/`](build-walkthrough-2026-11-13/).

**How it was run.** `npm run build` in `app/` (10 s), then the Windows launcher from a checkout, which served that build on `127.0.0.1:8721` (below). A headless Chromium drove the page at that address. **Timings were taken on a busy laptop**: other workers were running digitize jobs the whole time, so read every digitize time as an upper-ish bound (the same logo took 21 s here, 12–15 s last time).

## 0. The Windows launcher (#1419, #1425) — works from a checkout

`python digitizer/embbot_launcher.py --console` printed `Starting EMB-Bot...` then `EMB-Bot is running at http://127.0.0.1:8721/`. `/health` answered **5.9 s** after the start (last time, from the same checkout: "not ready after 120 seconds", twice). `/health` reported `engine.commit` `84fe69d8…`, `dirty: false`, the same commit as the checkout, and the Studio came from that checkout's `app/dist`. A Chrome window titled "EMB Bot Studio" opened by itself (I read the window title, not its address bar). A second launch while the first was up exited with code 0 after 3.7 s and left the service running, which is the intended "a second double-click is not an error"; it printed nothing.

**Frozen exe: not built.** The build script (`digitizer/packaging/build_freeze.py`) wants Python 3.12 with the pinned wheels, and PyInstaller in a throwaway venv. This checkout's venv is 3.14.6 with no PyInstaller, so it means a new multi-GB environment, then about 9 minutes (the spike's measurement) and a 440 MB folder plus a 167 MB zip, on a C: drive down to 13 GB free and shared. The brief said no extra installs, so I skipped it. What I can say: the `Windows app` workflow's two most recent runs, 2026-11-12 15:05 UTC (`ffefc3b1`) and 2026-11-13 22:37 UTC (`530a8e65`), both concluded `success`. I did not download or run what they built, so a frozen `/health` is unchecked.

## 1. Compare view — works; ended by re-digitizing

Digitized `enthusiast_logo.png` (2,954 stitches, 96×19 mm, 21.5 s click to caption). Compare lays the artwork over the stitches at the same size with a draggable divider, tagged Artwork on the left and Stitches on the right; its tooltip says it changes the view only. After clicking the divider the arrow keys move it (0.50 to 0.44; Shift moves it further, 0.24 after two presses). **What ends it:** pressing Auto Digitize Image again put the view back on Realistic (the run came back in 0.8 s, a cached result). On starter designs Original and Compare are greyed out, since a starter has no source art.

![logo digitized](build-walkthrough-2026-11-13/10-logo-digitized.jpg)
![compare](build-walkthrough-2026-11-13/11-compare-view.jpg)
![split moved](build-walkthrough-2026-11-13/12-compare-split-moved.jpg)
![ended by the re-digitize](build-walkthrough-2026-11-13/13-compare-ended-by-redigitize.jpg)

## 2. Simulate — works

It plays on opening: "424 / 2,954 stitches" 0.7 s in, "2,090 / 2,954" 3.7 s in. The bar has previous/next thread, a jump to each thread ("1 of 2, 0134 Smoky", "2 of 2, 1720 Not Quite Red"), Isolate, Stops, a speed button and Close, and reads "about 2 min left of 6". In the second shot only the black is sewn; the red mark is thread 2.

![simulate early](build-walkthrough-2026-11-13/14-simulate-early.jpg)
![simulate later](build-walkthrough-2026-11-13/15-simulate-later.jpg)

## 3. Garments, hoops and Rotate to fit — garments work, Rotate to fit does not

Starter monarch, then Hat: the hoop jumps to 5×7 and the design is shrunk to 60×57 mm; placements are Centered, Front left, Front right, Side left, Side right, Rear; the fabric preset is "Structured cap, pull comp 0.4 mm · rows ×1 · cut floats past 3 mm". Tee: Full back in an 8×8 hoop (Suggested badge), the design stays 91×86 mm; placements Full back, Left chest, Right chest, Upper back, Sleeve; preset "Fleece / sweatshirt, pull comp 0.5 mm". The hoop picker lists 4×4, 5×7, 6×10 and 8×8 with a "Suggested" badge and a "Use the suggested … hoop" link. There is no garment picture, only the hoop.

![hat](build-walkthrough-2026-11-13/04-hat-placement.jpg)
![tee](build-walkthrough-2026-11-13/05-tee-placement.jpg)

**Rotate to fit.** To get a design that fits only turned I used a 5×7 hoop (130×180 mm) and a 150 mm wide design, once as lettering ("ROTATE ME", 150×15 mm) and once as the American football starter (150×100 mm). Both show the new button: "Exceeds your 5×7 in hoop — rotate the design 90° and it fits · Rotate to fit". Pressing it turns the design **and also rescales it**:

- lettering: 1,899 stitches, 150×15 mm became **3,636 stitches, 31×305 mm**, "Exceeds your 5×7 in hoop, and every hoop this app offers — make it smaller under Size";
- football: 150×100 mm became **150×225 mm**, "Exceeds your 5×7 in hoop — a 6×10 in hoop fits it". The Width box still reads 5.90 in after the turn.

Neither ends up fitting. Undo (Ctrl+Z) restored the lettering case.

![5x7, rotate offered (lettering)](build-walkthrough-2026-11-13/06-hoop-5x7-exceeds-rotate-offered.jpg)
![after Rotate to fit (lettering)](build-walkthrough-2026-11-13/07-rotate-to-fit-text-blown-up.jpg)
![5x7, rotate offered (football)](build-walkthrough-2026-11-13/08-football-exceeds-rotate-offered.jpg)
![after Rotate to fit (football)](build-walkthrough-2026-11-13/09-rotate-to-fit-football-rescaled.jpg)

## 4. Photo-lane image, reading row, result, quality report — runs, but the result is crude

`photo_dof_meadow.png` (two toadstools on a blurred green meadow). The reading row says "Read as a photo, so it's sewing with shaded thread." with two choices, "Sew as flat art" and "Add fine detail lines". Auto Digitize took **171.7 s** (busy machine) and gave 27,609 stitches, 94×63 mm, "59 shapes, 5 colors at 93.3 mm". The Download step's quality check says **B 76/100** with three notes: the photo has 8.4 pixels per output mm and needs 10; "8 of 11 satin shapes sew below readable size"; and 3 mm² of artwork has no thread. Run time ~58 min at 650 spm, cutaway stabilizer, 75/11 ballpoint needle. The Compare shot shows what the grade does not: the toadstool's spotted cap and stem on the left become a flat orange half-dome with no stem on the right, and the blurred background becomes three flat olive blobs.

![reading row](build-walkthrough-2026-11-13/16-photo-lane-reading-row.jpg)
![result](build-walkthrough-2026-11-13/17-photo-result.jpg)
![compare](build-walkthrough-2026-11-13/18-photo-compare.jpg)
![quality report](build-walkthrough-2026-11-13/19-photo-quality-report.jpg)

## 5. The stale-stitch cue (#1420) — works

`two-squares.png` digitized (9,050 stitches, 97×37 mm). Click the black square, Edit points, drag a corner out, press Enter (Done). The run button now carries `dgp-run-stale dgp-run-lit` and a 1.6 s pulse animation, and the panel says "Changed since the last run — press Auto Digitize Image to restitch." with a **Restitch now** button; the canvas still shows the old stitches (9,050). Pressing Restitch now ran **3.9 s** and gave 9,515 stitches, 97×39 mm; the banner, the button and the pulse all went away. No console errors.

![digitized](build-walkthrough-2026-11-13/20-squares-digitized.jpg)
![cue](build-walkthrough-2026-11-13/21-stale-cue.jpg)
![after Restitch now](build-walkthrough-2026-11-13/22-after-restitch-now.jpg)

## 6. The re-made starters — work

Baseball (#1417/#1421): 23,637 stitches, 76×74 mm, 5 colors, 57 trims, white ball with red stitching and black seam. Monarch butterflies: 16,743 stitches, 91×86 mm, 3 colors, 68 trims, both butterflies with their orange cells. Each appears on the canvas in about 0.2 s, no service call. Both look right at this size.

![baseball](build-walkthrough-2026-11-13/02-baseball-on-canvas.jpg)
![monarch](build-walkthrough-2026-11-13/03-monarch-on-canvas.jpg)

## 7. Resizing a starter by about 1% and re-digitizing — could not be done from the Studio

A starter is a stitch file, so there is nothing to re-digitize; I uploaded each starter's committed SVG (`app/public/starter/*.svg`) instead, which takes the artwork route (not the route the starters were made on). The Studio **does not re-digitize a resize under 2%** (`RESIZE_TOLERANCE = 0.02`, `app/src/lib/digitizer.js`). With the monarch at 3.56 in (90.4 mm), pressing Auto Digitize Image at 3.60 in (+1.1%) and 3.52 in (−1.1%) returned in 3 s with the same 15,693 stitches, the canvas caption scaled to 91×87 / 89×85 mm and the panel's own line still reading 90×86 mm. At +2.2% it re-digitized for real. So the ±1% probe cannot be made through the UI, and the exact widths named in the brief (monarch 90.50 and 91.75 mm, owl 79–81 mm) are out of reach one percent apart.

What I could run, with the busy-machine times: monarch 3.56 in (90.4 mm) 15,693 stitches, 65 s; 3.64 in (92.5 mm) 15,949 stitches, 115 s; 3.72 in (94.5 mm) 16,999 stitches, 114 s. Owl 3.15 in (80.0 mm) 20,913 stitches, 115 s; 3.19 in (81.0 mm) not re-digitized (4 s); 3.30 in (83.8 mm) 22,610 stitches, 159 s. **No missing wing cell or other lost feature was visible at any of them**, and no errors. I did not hit the known cliffs, so this is not evidence they are fixed.

![monarch at three widths](build-walkthrough-2026-11-13/23-monarch-resize-3-widths.jpg)
![owl at three widths](build-walkthrough-2026-11-13/24-owl-resize-3-widths.jpg)

## What did not work, most serious first

1. **"Rotate to fit" (#1414) rescales the design, so it never makes it fit.** Reproduced on lettering and on a starter, section 3. Lettering 150×15 mm → 31×305 mm and 3,636 stitches (it doubled); football 150×100 mm → 150×225 mm. The Width box keeps its old value (5.90 in), so the turned design is scaled up to keep the same width. The cause was not traced; the unit tests for the button's rotation maths (`app/src/lib/hoop.spec.js`) say nothing about size.
2. **The photo lane's result loses the subject and the quality grade does not say so.** Section 4: B 76/100 on a design whose toadstool has lost its spots and stem. The notes it gives talk about "lettering" ("Remove or simplify the smallest lettering") on a photo with no lettering. One image only, and a hard one (blur), so this is a sample, not a rate. 172 s.
3. **Switching to Hat shrinks a stitch file outside the safe range with no warning.** The monarch went from 91×86 to 60×57 mm (66% of native) with the same 16,743 stitches, yet the panel kept saying "Pre-digitized file: it sews exactly as digitized." Typing a size by hand (1.5 in, 42%) does show "Resized to 42% … well outside the safe 75–150% range — expect gaps or bunching". The auto-fit path skips that warning. Football on Hat (90 → 86 mm) likewise showed no resize note, though the rule is any change over 2%. Also on Hat: the file's own line still reads "91×86 mm" while the canvas says 60×57.
4. **A resize under 2% does nothing, and nothing says so.** Pressing Auto Digitize Image after a ±1.1% width change finished in 3 s with identical stitches, the canvas caption changed, the panel's own size line did not (section 7). By design in the code, but it reads like a hang or a silent failure, and it makes the known near-1% cliffs untestable from the UI.
5. **A width typed before the first digitize is ignored.** The size boxes are empty until the first run, the first run uses a default (monarch 78.2 mm, owl 91 mm), then a "Resized to 89 mm — the stitches are only scaled until you press Auto Digitize Image to restitch at that width. Restitch now" cue appears. That costs one extra full digitize (owl: 140 s, then 115 s). The mm box also rounds to whole millimetres (90.5 shows as 91).
6. **Auto-crop on `owl.svg` kept only the face.** Uploading the committed owl SVG put the crop frame around the eyes and beak, leaving the ears and the head outline outside it ("Use whole image" is offered). The preview behind the artwork is dark-on-dark, so this may be the cause; I did not check. The starter itself, made from a PNG, has the ears. Image 25.
7. **Slow digitizes, partly the busy machine.** Monarch SVG 65–115 s, owl 115–159 s, photo 172 s, logo 21.5 s, squares 5.9 s. I have no quiet-machine baseline, so I cannot say how much is load.
8. Nitpicks: the launcher writes nothing to `%LOCALAPPDATA%\EMB-Bot\logs\emb-bot.log` on a successful start (its 8 lines are all from yesterday's failures) and a second launch prints nothing in `--console`; Compare and Original are greyed out on starters with no hint why; the first walkthrough's items (quiet "Saved ZIP", undo steps not mapping one to one) were not re-tested.

**Not covered:** the frozen exe and the installer (not built, see section 0), the Windows `.cmd` shortcut, anything needing the rembg/SAM2 venvs (the service reports `background_removal: false`, `sam2: false`, so photo cut-outs were not exercised), the Polo placements other than Left chest, Tee placements other than Full back, a quiet-machine timing baseline, the service-side export of digitized art, and the exact widths the brief named for monarch and owl.

**Process notes:** `node_modules` in this worktree is a junction to the main checkout's, so no install was needed. I started and stopped only my own launcher and browser processes; the launcher I started (a Python process tree on port 8721) is the one this walkthrough used, and it is stopped at the end.
