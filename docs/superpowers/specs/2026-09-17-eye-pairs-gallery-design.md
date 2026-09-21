# Eye-pairs reveal gallery — design — 2026-09-17

**Status:** approved in outline by Kent, 2026-09-17 (this session), as the
one piece the eye-pairs plan does not cover. Companion to
`2026-09-17-eye-pairs-design.md` (the yardstick); depends on that tool's
output files and on nothing else in it. No code exists yet. Nothing here
changes a stitch.

## 0. What already governs this

- **The yardstick's blinding is absolute until the sitting is done.** Its
  `--reveal` refuses until every pair has a pick. This gallery reveals arm
  names per pair, so it inherits the same refusal, verbatim: **no gallery
  until every pair id in `pairs.json` has a pick.** A gallery built earlier
  would name arms for pairs he has not judged and break the repeat controls.
- **Kent's ruling (yardstick §2): the PICKER is a local page, not an
  Artifact.** This gallery is not the picker. It is read after the sitting,
  and it is an Artifact because that is what Kent asked for in this session
  (2026-09-17): *"an interactive artifact … side by side … this will provide
  you feedback for what's working, what isn't."*
- **The 08-27 validation artifact self-republishes, so republishing it
  destroyed notes.** This page stores nothing in its own HTML. Notes go to
  the artifact's `db` capability; republishing the page leaves them alone.
- **No grade on a review sheet** (`acceptance_ab.py`'s decision record). No
  score, letter, or "% agreement" is printed. ROADMAP gate 4 stands.
- **`.claude/worktrees/` is never read or written.** Inputs come from
  `digitizer/eye_pairs_out/` (or `docs/eye-pairs-<date>/`) only.
- **Public repo.** The nine fixtures are already committed; the gallery
  copies only their renders. Kent's notes land in `docs/`, as
  `kent-review-*.md` already does.

## 1. What it is, in one sentence

After the blind sitting, one page that shows every pair *unblinded* — which
side was shipped, which arm, what that arm claims to fix, what Kent picked —
and collects two things the picks alone cannot carry: per pair, *did the arm
do its job*, and per arm, *his ruling*.

## 2. Inputs — the yardstick's file contracts, read-only

From `digitizer/eye_pairs_out/` (yardstick §3.4) — the whole directory, on
the machine that ran the sitting; the `docs/eye-pairs-<date>/` audit copy
carries only picks/pairs/arms and cannot build a gallery on its own:

| file | used for |
|---|---|
| `pairs.json` | pair id → left / right / art image names |
| `img/` | the renders and artwork, copied and de-duplicated |
| `arms.json` | fixture, `left_arm`, `right_arm`, `kind`, `repeat_of` |
| `picks.jsonl` | last line per pair wins (`L` / `R` / `tie`), `undo_of` honoured |
| `features.json` | descriptive counts and per-metric direction reads |
| `skipped.json` | optional; the per-arm `identical_to_base` count |

`results.json` is NOT read (plan revision, 2026-09-17): its exit-clause rows
are exactly the pairs where a metric's sign disagrees with the pick, which
the chips below already carry, so the "disagreements" filter IS the
exit-clause list and a second source for it would only drift.

The gallery never digitizes, renders, or recomputes a metric. It imports
nothing from `tools/eye_pairs/` (that package lands on a different lane);
the arm ids and metric directions it needs are a small table of its own
(`ARM_INTENT`, `METRIC_BETTER`), and a test pins the table to the yardstick
spec's arm ids (§3.2) and directional metrics (§3.7) as restated in the
test, with a comment naming the spec — the spec file itself is not on this
lane until the yardstick PR merges, so the test cannot parse it. Width and
garment per fixture come from `tools.thin_strokes.REAL_ART`, the table the
yardstick's `corpus_cases()` reads (the dict, not the function — no file is
hashed); a fixture the table does not know shows blanks, not an error. The
`ref_0827` arm is carried as `is_ref`, and a pair of it on a photo-class
fixture (`design_class` in `PHOTO_CLASSES`) as `confounded`, because the old
engine ran without the rembg venv there (yardstick `--reveal` marks the same).

## 3. The generator — `digitizer/tools/eye_pairs_gallery.py`

```
python -m tools.eye_pairs_gallery [--src digitizer/eye_pairs_out] [--out <src>/gallery]
```

1. **Refuse** unless every pair id in `pairs.json` has a final pick that is
   not undone. Same wording as `--reveal`.
2. **Join** pairs × arms × picks × features into one list of pair records.
3. **De-duplicate images by content hash.** The yardstick writes one file per
   pair side, so a fixture's base render is copied ~ten times; the gallery
   keeps one copy per distinct content, named `<sha256[:12]>.jpg`. Expected
   ~120 unique files for 9 fixtures × 12 arms + artwork — under the
   artifact's 255-file limit. **Re-encoded** with OpenCV at JPEG q85, long
   edge ≤ 1400 px, so the set stays under the 64 MB per-version limit; the
   generator prints the total and refuses above 60 MB.
4. **Emit** `<out>/index.html` with the pair records inlined as JSON (a few
   hundred bytes a pair) and `<out>/img/*.jpg`. Nothing else. Paths in the
   HTML are relative (`img/<hash>.jpg`), never absolute.

Per pair record: `pair, kind, repeat_of, fixture, width_mm, garment,
shipped_side ("L"|"R"|null for identical), arm_side, arm, arm_change,
arm_intent, pick, picked_arm, consistent (repeat pairs only: true if the
same ARM was chosen both times), counts {L: {stitches, trims_per_1000,
cones}, R: {...}}, chips: [{metric, prefers ("L"|"R"), agrees (bool),
base, arm, refused (bool)}], img {L, R, art}`.

A chip exists only where the metric is non-null on both arms and differs;
`prefers` follows `METRIC_BETTER`; `agrees` is `prefers == pick`. Ties and
control pairs get no chips. This is a per-pair read of sign, printed as a
list — never summed into a percentage, and **the values themselves are not
carried to the page** (review revision 2026-09-17): a review sheet holds no
scorecard number, so a chip is direction and a refused flag, nothing more.

## 4. The page

One static HTML document, no framework, no script dependency (the only
external fetch is a Google Fonts stylesheet with a full fallback stack),
tokens on `:root`, dark mode honoured, phone width usable.

**Layout.** Pairs grouped by arm (default) or by fixture. Each pair card:

- header: `fixture · arm` with the arm's change and intent, and its kind
  (`live`, `identical control`, `repeat of P###` with `consistent` /
  `flipped`);
- artwork thumb centred above; left and right renders below, each labelled
  `shipped` or `<arm>` — the picked side carries a ring and the word
  *picked*; a tie says so on both;
- **synced zoom/pan**: wheel to zoom, drag to pan, both renders move
  together so the same patch of both designs is on screen (the yardstick
  picker's behaviour, kept so what he saw is what he re-sees);
- counts under each side: stitches, trims/1000;
- the chips row: metric names, green where the metric points the way he
  picked, red where it points the other way, dashed where the instrument
  refused the artwork; hover names the direction, never a value;
- **inputs**: *did the arm do what it claims?* — `yes` / `no` / `can't tell`
  — and a note. Autosaved; a `saved` mark confirms each write.

**Per-arm header card** (when grouped by arm): wins / losses / ties of the
arm against shipped, per fixture as a strip and pooled as counts (counts,
not rates), the arm's `identical_to_base` skips, and **the ruling control**:
`flip ON` / `keep OFF` / `needs work`, with a note. This is where Kent's flag
decisions are recorded; the page flips nothing. **The `ref_0827` arm is an
engine snapshot, not a flag:** its header reads *then preferred / today
preferred* instead of wins / losses, carries a note but no ruling control,
and its sides are captioned *today* and *08-27 engine*; a confounded pair
wears a badge saying so.

**Filters** as chips at the top: all · picked arm · picked shipped · ties ·
controls · disagreements. *Disagreements* is the yardstick's exit-clause
list exactly: live flag pairs (repeats and the ref arm excluded) with any
red chip.

**Nothing on the page is a quality number.** `preflight_raw_score` appears
only as a chip name like any other metric.

## 5. Persistence and the feedback channel

- `capabilities: {db: {}, downloads: true}`.
- `db` docs: `notes/<pair>` → `{job_done: "yes"|"no"|"unsure"|null, note,
  updated}`; `rulings/<arm_id>` → `{ruling: "flip_on"|"keep_off"|
  "needs_work"|null, note, updated}`. One write per doc per change,
  debounced 600 ms on the note field. Default rules: signed-in interact+
  writes, so a share-link viewer reads only.
- `claude.use("db")` resolving `null` (local preview, or a viewer without
  the grant) falls back to `localStorage` under the same keys and shows a
  *not synced* mark; nothing is lost silently.
- **Export.** A `save notes` button (`downloads`) writes
  `eye-pairs-notes-<date>.json`: `{exported, notes: {...}, rulings: {...}}`.
  The same shape is what I read with `ArtifactData` after the sitting and
  commit as `docs/eye-pairs-<date>/kent-notes.json` beside the yardstick's
  `picks.jsonl` / `pairs.json` / `arms.json`.
- **Republishing is safe by construction**: the HTML holds pair data and
  images only; notes never enter it.

## 6. What comes back to the repo, and what it licenses

`docs/eye-pairs-<date>/kent-notes.json` plus a short markdown summary
(`docs/kent-review-<date>.md`, the existing precedent's format): per arm,
the ruling and W/L/T; per pair, any note. A `flip_on` ruling is evidence for
a default flip that still goes through its own PR with its own tests; a
`needs_work` with notes becomes a defect entry. The gallery claims nothing
about instruments — that is the yardstick's `--reveal`.

## 7. Testing — TDD, `digitizer/tests/test_eye_pairs_gallery.py`

All on a synthetic `eye_pairs_out/` built in-test from the yardstick's
schemas (tiny generated JPEGs; no digitize, no real logo):

- refuses on a missing pick, an undone-and-not-repicked pick, and an
  unknown pair id in `picks.jsonl`;
- last line wins; `undo_of` returns a pair to unpicked;
- de-dup: two pairs sharing a base render yield one file; a byte-different
  render yields two; every `img/` reference in the HTML exists on disk;
- chips: lower-better and higher-better directions, null on either side →
  no chip, equal → no chip, tie pick → no chips, controls → no chips;
- repeat `consistent` for same-arm, flipped, and tie/tie;
- W/L/T tally per arm, with identical skips counted from `skipped.json`;
- the ref arm is marked, a photo-class fixture's ref pair is `confounded`,
  and `PHOTO_CLASSES` is pinned to `digitizer_core.config`;
- chip records carry no values; a missing source image is a refusal;
- `ARM_INTENT` keys == the yardstick spec's arm ids; `METRIC_BETTER` keys ==
  its directional metrics (both restated in the test with a pointer to the
  spec section; when the yardstick's `tools/eye_pairs/pairs.py` exists on
  the same checkout, the test also asserts equality with its `ARMS` keys);
- size budget: an over-budget synthetic set is refused with the total named;
- the HTML contains no absolute path and no `%` beside a metric name.

The page itself is verified in the browser pane against the synthetic set
(served statically): computed styles in light and dark, keyboard and zoom
sync, note autosave round-trip through the `localStorage` fallback, phone
width. Evidence (screenshots, console clean) goes in the PR.

## 8. Runtime and sequence

Generator: seconds (re-encoding ~120 images). Sequence: yardstick PR merges
→ Kent's sitting → `--reveal` → this generator → publish artifact with
`files` = `img/*` → Kent annotates → I read `db` → commit notes. The
generator and page are built and tested now against the synthetic set, so
the only step waiting on the sitting is the publish.

## 9. Out of scope

Any picking (the yardstick owns it); any statistic beyond per-pair sign
chips and W/L/T counts; cross-design pairs; any engine change or default
flip; a phone picker; editing picks (a pick is final; a disagreement with
oneself is a note).
