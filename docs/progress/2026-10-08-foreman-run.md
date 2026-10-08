# What changed on 2026-10-08 — the foreman run

For Kent. 132 pull requests merged today (#663–#795). Most were tests and
background work; this page pulls out what you can see, what got better, and
what is waiting on you. **Nothing below has been sewn** — every quality
claim is from renders and measurements, not cloth.

## Studio features you can try

Start the app (`tools/start-emb-bot.ps1`), then:

- **Zoom to 800%** — keep pressing zoom in on the design field. (#676)
- **Corner-drag a digitized logo** — the drag now changes the Design width,
  same as typing it. (#670)
- **Watch Auto Digitize run** — a pinwheel spins while it works, and the
  outline pulses when it lands. Reload the page mid-run: it picks back up
  instead of starting over. (#678, #780)
- **Auto Digitize is about 2.4× faster**, same stitches. Upload any logo and
  time it. (#693)
- **Sharper digitizing of big uploads** — a large image is shrunk to 2,800 px
  for the digitizer, not the 1,200 px preview. (#776)
- **Upload a logo into a fresh design** — it replaces the empty text box and
  fills the placement, instead of sitting 42 mm wide. (#731)
- **"Put on two lines"** — type a long name on one line at a small size; when
  it would sew too thin, one click splits it. (#709)
- **"Fits your text"** — type a name, open the font browser, tick the
  filter: only fonts that have every letter you typed. (#763)
- **Why was my size capped?** — type a size bigger than the hoop allows; the
  message now says why and what makes it bigger. (#766)
- **Thread vanishes into fabric** — pick a thread close to the garment colour;
  you get a warning. (#740)
- **Per-letter colours** — colour letters one by one, then edit the word: the
  colours follow the letters. Recolouring already-coloured letters now
  works. (#739, #749)
- **Plain-English errors** — every failure and warning a customer can see now
  has a sentence written for a person, not a code. (#695, #753)
- **Downloaded files are named after the design**, not a generic name. (#735)
- **Size in inches** on the Review/quote Size row, matching the worksheet. (#761)
- **Press `?`** for a keyboard-shortcuts overlay. (#729)
- **Laptop screens** — the field's control bar fits 1300–1500 px laptops and
  wraps on smaller screens (Zoom out was falling off-screen). (#688, #706)
- Smaller fixes: readable labels on every artwork swatch (#708); the tracing
  image's Remove button is visible (#771); the app respects "reduce motion"
  (#762); faster first load (#770) and smoother preview (#712, #777);
  Download sheet works with the keyboard (#725).

## Digitizer quality

**Turned ON today (your calls):**

- **Fill columns everywhere** — the browser's fills no longer float thread
  across gaps, in all three lanes (drawn shapes, basic shapes, uploaded
  images). Cost: about 2% more stitches on shapes, about 10% on images.
  (#673; #697 tried four cheaper versions — none was worth it, so it held.)
- **Cut long floats** in drawn and basic shapes — a float a machine would
  read as a cut now gets a real trim. (#672, #682)
- **Underlay under ordinary fills in gradient-style logos.** (#664)
- **Square joins and square free ends on lettering**, with foot and T slabs
  sewn as their own short columns — the fanning at serifs is gone. (#666, #679)

**Fixed:**

- A drawn shape with two anchors a pixel apart no longer sews a spike. (#690)
- The edge-run underlay closes its loop instead of stopping a stitch short. (#713)
- A lettering connector no longer lays the next letter's first stitch twice. (#728)
- A satin bar's stitches reach its full width: a 38 mm bar was sewing a
  37.7 mm stitch. (#779)

**Built but OFF** (waiting on evidence or on you): about fifteen, including
fewer trims by riding under columns (#746, #773: 534 → ~516 trims on nine
real logos) and fewer colour stops on photos (#714: owl 32 → 28). Each PR
carries before/after pictures.

## Export / DST

- **A DST crash was live on `main` for about half an hour.** Two changes
  merged close together — a 40× faster DST writer (#726) and a fix to the
  stitch count in the DST header (#742). Each was fine alone; together every
  DST download threw an error. **#793 fixed it** (merged 11:16 UTC). If you
  downloaded a DST between roughly 10:45 and 11:16 UTC today and it failed,
  that was this; download again. DST tests pass on `main` now.
- **The DST header's stitch count now matches the industry reader** (#742,
  as fixed by #793).
- **Export audit** — every format, on 12 real designs, read back by an
  independent reader. Four fixes: long stitches split on the service path;
  PES black no longer comes out green; service PES and JEF keep their
  cuts. (#696)
- **PES/JEF thread names** — your ruling today: each colour names its
  nearest thread cone by the perceptual colour measure, so near-black asks
  for Black, not dark brown, on both PES routes. (#792)
- New tests prove a downloaded DST is the size the app shows (#754) and
  that empty, one-stitch and 200-colour designs export cleanly (#794).

## CI / infrastructure

- **The slow `digitizer` check is split six ways** — about 25 minutes instead
  of 70+. (#669, #790, #791) PRs that don't touch the digitizer now skip
  most of it. (#795)
- Studio browser tests run faster (#720); a cancelled run no longer shows
  red (#687).
- The digitizer service is hardened: upload size limit, deadlines, a busy
  guard, no internal error traces shown to customers. (#710)
- Four high-severity npm security advisories patched. (#691)
- A foreman skill (`K3`), a contributor README, COOKBOOK how-tos. (#743, #692, #683)

## Tests

About 50 PRs were tests only — browser guards on the main customer flows,
export and importer edge cases, every OFF flag switched ON once without a
crash (#765), and a **provenance manifest for every image and stitch file**
(#717). They change nothing a customer sees; they catch breakage first.

## Waiting on you

1. **Contact sheet of four OFF flags — #786.** Before/after pictures, real
   art, nothing sewn:
   - `two_tone_snap` — black-and-white logos sew 2 colours, not 5–6
     (one logo: 75 → 52 trims). Catch: it changes every B&W logo.
   - `satin_tip_corner_gate` — letter arms stop fanning into neighbours.
     Catch: it moves junction ends on every logo.
   - `lettering_columns` + `lettering_words` — lettering as proper columns
     (Becker: 60 → 29 trims, ~20% fewer stitches). Catch: letters look
     different; no overlap at junctions yet.
   - **Image lane: cuts vs stitches (#697)** — ~3–4% fewer stitches for
     about 30× more cuts. Only a sew-out says which costs more.
2. **Satin pull compensation: per side or total? (#768)** The browser and
   the digitizer disagree — the same 2.5 mm column sews 2.8 mm in one and
   3.1 mm in the other. This is a physical number, so it waits on a sew-out
   (roadmap gate 1). Your relayed ruling today: leave both as they are until
   it becomes a real problem. It is pinned by a test so it can't drift.
3. **12 logos with no recorded origin (#717).** Six in
   `digitizer/testdata/art/` (golke roofing, hotel fremont patch, mfab hat,
   mfab lc, toat beanie, toat machine) and six real logos with no clearance
   on file (script tires, hotel fremont, bridge bar, golden tee, gaulke
   roofing, a phone screenshot). The repo is public. Tell us where each came
   from and whether it may stay.
