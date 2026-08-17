# EMB-Bot project review — 2026-08-16

> **CORRECTION, 2026-08-17 — §1.1 and opportunity #5 are wrong, and the work
> they ask for already shipped.** This review says "the UI gives the user no
> indication which encoder produced their file" and ranks "Encoder provenance in
> the UI" as opportunity #5, *"Blocked on: nothing. Hours of work."* Both halves
> were already in the product when this was written:
>
> - `app/src/ui/DownloadStep.svelte:268-277` warns **before** a browser-encoded
>   DST download, naming the actual symptom — other software reads it rotated a
>   quarter turn and may not see the colour stops — and the way out (PES/EXP, or
>   a project made only of auto-digitized images).
> - `DownloadStep.svelte:279-284` confirms **after** the download, read from the
>   observed `via` rather than predicted, so a service outage falling back to the
>   browser encoder is still reported honestly.
> - Landed `ad612c9`, **2026-08-12** — four days before this review. Service
>   routing landed `02cd97c`/`51746bd`, 2026-08-10.
>
> So the interim mitigation the 2026-08-11 audit recommended is DONE, not "five
> days on, no trace of it." **§1.1's underlying risk still stands** — designs
> containing lettering or a manual shape do still download through the known-wrong
> browser codec, and that is the headline use case. What is closed is the claim
> that the user is not told. `MASTER_SCOPE.md`'s DST section carries the same
> correction. *(verified 2026-08-17 — code read, commit dates checked)*
>
> §5 said this review could be wrong by omission. This is where it was.

**What this is:** a read across the repo's 131 markdown files and their research
findings, asking two questions Kent posed: *what remains in here that could ship
a flawed product*, and *where are the biggest improvements available*. Written
to scope the project's next phase, not to record a session.

**Method and its limits.** MASTER_SCOPE, PRODUCT.md, README.md, the 2026-08-11
project audit, the 2026-08-14 MASTER_SCOPE fact-check, the 2026-08-02 hardening
close-out dossier and the 2026-08-15/16 real-artwork handoff were read in full.
Every claim in §1-§3 that could be checked against code **was** checked against
code this pass, and the check is named inline. The remaining ~110 docs were
sampled by title and cross-reference, not read end to end — so this review can
be wrong by omission, and §5 says where.

**One thing this review does not do:** it takes no position on whether any
number here is *good*, only on whether the repo's own documents agree with the
repo's own code. Where they disagree, the code wins.

---

## 0. The honest summary

The engineering discipline in this project is unusual and genuinely good — root
cause docs, measured claims, adversarial self-review, corrections kept rather
than deleted. Three of the four risks below were **found by this project's own
documents**; the reviewer's job was mostly to check whether they were still
true.

But there is one structural pattern worth naming above everything else, because
it explains most of what follows:

> **Nothing has been sewn. Every quality number in this repository is
> geometry.**

Zero sew-out testing since the project began, confirmed independently by three
research passes and stated plainly in the 2026-08-02 close-out: *"Nothing was
sewn."* Four hoopings are already specified and would settle nine open
geometric questions at once. Every "Medium" confidence rating in MASTER_SCOPE
traces to this one gap, and no amount of further analysis can move it.

The second pattern, which the repo itself named: **synthetic references have
flattered this codebase in at least four independent places** (stage 0's
flat/gradient gate, `stage6_blend`'s ramp gate, the pro-parity corpus, and the
`direction`/`sttype` weights). Every time real input arrived, the measured
result got worse and more honest. That is a healthy process producing an
uncomfortable conclusion: **the product has been tuned against inputs it does
not actually receive.**

---

## 1. Ship-risk flags — things that could make the product wrong for a customer

Ranked by what they do to a garment or a customer's file.

### 1.1 The DST axis bug still reaches customers on the core use case

`src/dst.js`'s movement bit table is transposed against the Tajima standard.
**Five independent sources agree on the opposite convention**, the fifth being
Ink/Stitch's own `pystitch` DST reader/writer. EMB-Bot's files round-trip
correctly against themselves and read **a quarter-turn wrong in third-party
software**; a related `0x43`-vs-`0xC3` issue means third parties see zero colour
changes.

**Verified this pass:** the Python `/export` route *is* now reachable from the
product (`app/src/lib/digitizer.js:936` posts to `/export`) — the 2026-08-11
audit's "unreachable from the real product" finding is closed. But it is gated
on `DownloadStep.svelte`'s `isPurelyDigitized`, so **any design containing
lettering or a manual shape still downloads through the browser codec.**

Lettering is the product's headline feature. So the known-wrong encoder still
serves the core use case, and **the UI gives the user no indication which
encoder produced their file.**

- **Blocked on:** a sew-out, plus Kent's explicit call (a fix re-orients every
  DST EMB-Bot has ever written — a migration decision, not a code decision).
- **Not blocked, available today, still not done:** surfacing encoder
  provenance in DownloadStep and warning when browser-DST is bound for
  third-party software. The 2026-08-11 audit recommended exactly this as the
  interim mitigation. Five days on, no trace of it.

### 1.2 No width floor under satin — a physical risk, and the fix is specified

19 of 162 corpus regions sew **sub-millimetre satin**. At that width the thread
piles and the needle re-punches the same hole: thread breaks, and holes in the
fabric. This is MASTER_SCOPE live defect 2, measured 2026-08-11.

The fix is already written down — `2·p90 < ~1.0 mm` reroutes to a run stitch —
and is *scoped into slice 2 of the satin routing spec currently in flight*
(`docs/superpowers/specs/2026-08-16-satin-routing-gate-attribution-design.md`
§4). It is the cheapest real-fabric improvement on the board.

**Flag:** the threshold is to come "from a sweep, not from this document," and
the sweep is geometry. A width floor is exactly the kind of claim a sew-out
settles in one hooping. Worth putting on the sew-out card rather than shipping
a swept constant and calling it done.

### 1.3 Stage 0 rejects the very art the product tells users to feed it

README's "Honest limits" says: **"Feed it flat art. Solid colors and clear
edges digitize well."** That is the documented promise.

Measured on Kent's 15 real customer designs: **stage 0 routes 10 of the 15 into
the photo lane.** `GRAD_VAR_GRADIENT_MIN = 0.0015` was calibrated on synthetic
fixtures reading below 0.0006; real logo art reads **0.205 to 6.135** — three to
four orders of magnitude out — because real logos carry JPEG ringing,
anti-aliased edges and soft shading that synthetic flat fixtures do not. One
clean two-colour script wordmark on white classifies as `photo_scene` outright.

Forcing `flat` is worth **+3.2 corpus points**, the largest reachable lever the
real-artwork session found.

**Why this is a product risk and not just a score:** the customer does what the
README says, sends clean flat art, and silently gets the photo pipeline. The
promise and the classifier disagree.

**Blocked on:** artwork. Siting a threshold needs more than one genuinely tonal
example, and Kent's own labelling says only `Precision Thermal Drone` is
genuinely tonal. Four approaches were measured and rejected
(`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`).

**This makes "get more real customer artwork" the highest-leverage non-code
action in the project after the sew-out.**

### 1.4 The gradient path advertises a capability it does not deliver

MASTER_SCOPE live defect 1: **every shade of every decomposed region sews in the
same colour.** `stage6_blend` and `stage6_streamline` both compute a per-shade
thread snap (`shade_thread_idx` / `shade_rgb`), put it in their report, and
**nothing reads it** — a block's thread is the region's one assigned thread.

Measured 2026-08-15: **0 of 26 regions shaded** on real artwork. And
`blend_tonal_bands` was built, measured and deleted in the same pass precisely
because the geometry decomposed correctly and *changed nothing visible* — the
shades still shared one thread.

**This compounds 1.3.** Ten of fifteen real logos route into the lane whose
headline capability is inert. So the misroute is not a neutral detour; it lands
real customer art in the one path that cannot deliver what it computes.

Kent tabled gradient work on 2026-08-16 in favour of non-gradient art first,
which is the right sequencing. **The flag is not "fix it now" — it is "do not
ship marketing that implies tonal shading works."** Currently README does not
claim it, which is correct. Keep it that way.

### 1.5 Fragmentation: 129 runs where the professional uses 15

On the same logo at the same size, our output fragments into **129 runs against
the pro's 15**, driving **8.49 trims per 1,000 stitches against the pro's
1.27** — more than double the **4.1** ceiling this repo's own chaining test
treats as the outer limit.

MASTER_SCOPE calls this "unambiguously a defect, unlike the stitch-count gap
beside it," and **the cause is not yet diagnosed.** It is the one item on the
live-defect list with no hypothesis attached.

A customer feels this directly: every trim is a thread cut, a re-tie, and a
place the design can fail. This deserves a diagnosis session of its own.

### 1.6 A latent CRITICAL that ships off, and is missing from the live-defect list

The 2026-08-02 hardening close-out found, with an instrument built to share no
code with the thing it measured:

> **chaining sews needle-down thread on bare fabric, on a stock preset, with a
> green suite** — 16.15 mm of exposed thread over 17 links on
> `full_back`/`fleece_sweatshirt`, one point more than a full millimetre from
> any thread in the design.

**Verified this pass: `chain_links: bool = False` (`config.py:1064`).** So it is
latent, not live, and the product is safe today. Two further things are
verified and matter:

- The two shipped instruments were **structurally blind** to it in three
  separate ways (one-point links skipped — 37% of the benchmark's links; the
  first and last sewn segment never tested; cover measured as polygons rather
  than as where thread actually lands). A green suite meant nothing here.
- **MASTER_SCOPE's live-defect list does not mention it at all.** Someone
  flipping that default in good faith — it reads like an optimisation — would
  ship visible thread on bare fabric with a passing test suite and no warning
  anywhere in the status dashboard.

**Recommendation:** add a "latent, gated OFF, do not flip" section to
MASTER_SCOPE, and put chaining in it with the instrument rebuild named as its
precondition. This is a five-line documentation change that closes a real trap.

**Credit where due:** contour's three CRITICALs from the same dossier *were*
fixed on 2026-08-04 and the work is documented in unusual depth at
`config.py:462-521`, including one figure that did not survive re-measurement
(the star's "2.94 mm bare disc" is a diameter, not a radius). That is the
standard the chaining lane should be held to.

---

## 2. Documentation integrity — where the repo's own docs disagree

The 2026-08-14 fact-check found **30 of 56 sampled claims stale and 17 outright
false**, and led to good rules (classify before you write; every claim carries a
verb and a date; 800-line budget; no test counts in prose). Those rules are
working. What follows is what the rules have not caught yet.

### 2.1 MASTER_SCOPE live defect 4 contradicts its own handoff doc

MASTER_SCOPE says of the Becker comparison:

> the 1-colour-vs-4 difference is **not** defect #1 … the pro worked from
> richer artwork than we were given

`docs/handoff-2026-08-16.md` §0 explicitly corrects this: the artwork is not
richer, it is **the same file**, and the missing piece is the **alpha channel** —
7,272 fully transparent pixels forming the letter counters, which the pro sewed
as a second colour. The gap is the enclosed-background capability being off by
default, **worth +8.0 per Becker design**.

Both documents are on `main` and they disagree. The stale reading is the one in
the status dashboard, which is the document people read first. **One-line fix.**

### 2.2 The standing ruling about Windows goldens is half wrong — including my own

MASTER_SCOPE's ruling states that the three platform-divergent goldens fail on
Windows and pass on CI, "which is what CI runs and where the goldens were
captured."

**Verified against the workflow this pass, and it does not hold as written.**
`.github/workflows/python-package-conda.yml:96-98` deselects three tests, and
its own comment says they *"compare against goldens pinned on the original
development machine"* — i.e. they **fail on CI**. The deselected set is
`logo_alpha.png` ×2 plus `pushcomp[logo_whitebg.png-towel]`. The set that fails
on Windows is `enthusiast_logo` ×2 plus that same pushcomp case.

So the true picture is three-way, not two-way:

| fixture | Windows | CI |
|---|---|---|
| `pushcomp[logo_whitebg-towel]` | fails | fails (deselected) |
| `logo_alpha` goldens | passes | fails (deselected) |
| `enthusiast_logo` goldens | fails | passes |

The blanket claim "the goldens were captured on ubuntu-latest" is false for
`logo_alpha`. **This matters** because the ruling is what a session uses to
decide whether a local golden failure is real — and the correct rule is
per-fixture, not per-platform. The safe part of the ruling stands unchanged:
never re-capture a golden from a Windows run.

**Second-order flag:** two byte-identical golden tests are deselected in CI
permanently. The workflow argues this correctly — a *new* break still fails the
job — but it means the byte-identical guard has two known holes, and the comment
"if these three ever pass on CI runners, remove the deselects and find out why"
has been standing since the file was written with nobody assigned to it.

### 2.3 README understates the satin cap by 67% — user-facing

README's "What the stitch engine does" says:

> **Satin vs. fill** — genuinely thin shapes (≤ ~3 mm at final size) get satin
> columns

**Verified: `machine.py:336` is `SATIN_MAX_WIDTH_MM = 5.0`.** The 3.0 figure was
main's value back on 2026-08-02 and was raised since. A user sizing artwork
against the README's number will predict the wrong stitch type for everything
between 3 and 5 mm.

This is the clearest instance of the pattern Kent described: the tool is doing
something reasonable and *the document says a different number*.

### 2.4 `match_shape_ids` is dead code that six comments describe as running

**Verified this pass**, and unchanged since the 2026-08-14 fact-check named it:
`match_shape_ids` is defined at `regions.py:106` and has **no production
caller**. It is described as live machinery in `digitizer/README.md:373`,
`regions.py` (×3), `config.py:386`, `:694`, `:708`, `:860`, and
`pipeline.py:327`.

The behaviour those comments promise *does* happen — `assign_shape_ids` derives
ids deterministically from bucketed centroid plus thread number, so edits carry
forward by plain id matching. **The docs are wrong about the mechanism and right
about the behaviour**, which is the most dangerous combination: a future session
optimising `assign_shape_ids` could break carry-forward while every comment
still points at the function that isn't running.

The fact-check's recommendation — wire it or delete it and fix the comments — is
still open. **Delete is almost certainly right.**

### 2.5 Both quality harnesses have corpus halves that do not exist in a checkout

- `scratch_corpus/` — 37 files. Gitignored, **confirmed empty in every checkout,
  no session has ever had them.** Blocks the DT-first classifier's M2/M3, and
  has since 2026-08-01.
- `tools/pro_parity/` — its 23 prepped designs are built by `prep_all.py` from a
  local reference-art folder that is not in the repo and is unreachable from a
  fresh checkout.
- The 2026-08-02 dossier's own §9: every chaining headline number was measured
  on a PNG **in Kent's Downloads folder**, and preflight's "5 artworks" is four
  committed PNGs plus a gitignored file in the repo root.

**Net effect: the two instruments that judge whether digitizing quality improved
cannot be run by anyone but Kent, on one machine.** That is a bus-factor problem
and a reproducibility problem at the same time, and it is the reason several
"pending a corpus run" items have sat open for two weeks.

Eight real-artwork files did land in `FIXTURES` on 2026-08-15, which is the first
genuine progress on this in the project's history. It does not close
`scratch_corpus/`.

---

## 3. The "counter counts 1, 2, 3, 5, 6, 7, 9.1, 10" list

Small, concrete, individually cheap. Each one is a case where the tool or the
test does something *almost* right and nobody would notice.

1. **`assert p.stitch_angle_deg != pytest.approx(on_grown, abs=1e-9) or True`**
   — `test_pushcomp.py:316`. **Verified present today.** `X or True` is always
   true: this assertion **carries zero bits** and can never fail. It is the line
   whose own comment claims to guard the circularity cut the entire push-comp
   lane exists to close. Flagged on 2026-08-02; still here 14 days later.
   *Fix: delete the `or True`, watch it fail or pass honestly, then decide.*

2. **README's satin cap says 3 mm; the engine says 5 mm.** §2.3.

3. **MASTER_SCOPE's live defect 4 states a cause its own handoff doc
   disproved.** §2.1.

4. **`match_shape_ids` — dead function, six comments say it runs.** §2.4.

5. **`ColorRangesEditor.svelte` renders a literal `×` as a button's entire
   content**, against a documented "zero raw Unicode/emoji affordances" claim
   (2026-08-14 fact-check item 7, not re-verified this pass). Screen readers
   announce "multiplication sign".

6. **The `direction` component carries 20 of 100 scorecard points and measures a
   preference, not a standard.** Two files by the *same* professional for the
   *same* logo score `direction` at **0.11 on one pair and 0.85 on another.** By
   contrast `density`/`underlay`/`travel` ceiling at 0.89-1.00. A fifth of the
   score is being paid out for matching one digitizer's mood on one day.
   *Fix: it is the least defensible weight in the scorecard and the repo already
   says so — reweight it, or report it separately from the headline score.*

7. **The 95 target sits above the metric's own ceiling.** A professional scores
   **75-84 against a professional** on this scorecard. So `42.5 / 95` reads as a
   52-point engine deficit and is not one. Deliberately not revised because
   n=2 — which is correct rigour, but it means **every plan quoting "we need to
   get to 95" is quoting an unreachable number.**
   *Fix: state the target as a fraction of the measured ceiling, or grow n
   (needs scale-normalised registration in `scorecard.py`; every other same-logo
   PES pair is 4-17% apart in width, so translation-only registration cannot
   compare them).*

8. **`CONTOUR_BARE_CORE_MM` was recalibrated 0.87 → 0.13** and the derived
   `starved_threshold_mm` moved with it — good work, but it means every
   `starved` number quoted in a doc older than 2026-08-04 is on the old scale.
   Same class of trap as the pre-2026-08-14 pro-parity scores, which
   MASTER_SCOPE already warns about. This one has no warning.

---

## 4. Biggest opportunities, ranked

Ordered by (value to a real garment) ÷ (effort), with blockers named honestly.

| # | Opportunity | Why it's the size it is | Blocked on |
|---|---|---|---|
| 1 | **Schedule the sew-out** | Settles **nine** open geometric questions in four hoopings; unblocks the DST fix, fabric presets, Law 19, `LINK_COVER_TOL_MM`, the satin width floor, and every "Medium" confidence rating. Zero engineering. | Kent's calendar. Nothing else. |
| 2 | **Collect more real customer artwork** | The single non-code action that unblocks the largest measured lever (1.3, +3.2 corpus). Also the only thing that can retire the synthetic-flattery pattern, which has cost this project four wrong conclusions. | Kent supplying files; specifically at least 2-3 genuinely tonal ones. |
| 3 | **Diagnose the 129-vs-15 fragmentation** | The one live defect with no hypothesis, and the one a customer feels most directly (8.49 trims/1k against 1.27). | Nothing. Available now. |
| 4 | **Satin/fill routing + the width floor** | In flight today on `claude/satin-gate-attribution`; slice 1 measured that 63.6% of the pro's lost satin ground is rejected by one gate, and slice 2's promotion path measures **+300 cells** of stitch-type agreement. Carries the width floor (1.2) with it. | Nothing — but see the note below on its acceptance criterion. |
| 5 | **Encoder provenance in the UI** | Turns 1.1 from a silent wrong answer into an informed choice, today, without touching the codec or migrating anyone's files. | Nothing. Hours of work. |
| 6 | **Resolve the blend tier's dead shade path** | Either wire `shade_thread_idx` in `stage7_sequence` or delete it. Today it is computed, reported, and ignored — the worst of the three options, and it makes the photo lane look capable in code review while doing nothing on fabric. | Kent tabled gradient work; the *deletion* half is not blocked. |
| 7 | **Make the corpus reproducible** | Commit what can be committed, and document the reference-art folder as a named prerequisite with a manifest. Two weeks of "pending a corpus run" items are downstream of this. | Licensing judgement on committing customer artwork — Kent's call. |
| 8 | **The doc corrections in §2 and §3** | Roughly one line each, and every one of them is currently able to send a future session down a wrong path. Cheapest ratio on this table. | Nothing. |

**A note on #4's acceptance criterion, since it is live right now.** The satin
routing spec sets the **primary** bar as corrected kappa from `scorecard.py`'s
`parts["sttype"]`, and explicitly says the raw agreement figure will not do,
because promotion shifts the satin/fill marginals and therefore moves the chance
floor itself. The work committed so far quotes **raw** (55.4% → 58.9%). That
gain may be real, partly real, or entirely the floor moving — and the spec
predicted exactly this ambiguity. **Measuring the corrected number is a short
task and it is the difference between "we improved routing" and "we think we
did."**

---

## 5. What this review did not establish

- **~110 of the 131 markdown files were not read end to end.** The four largest
  (`docs/scope-history.md` at 2,016 lines, the SAM2 and SVG-import plans, and
  `docs/scope/1-auto-digitizing-quality.md` at 1,654) were sampled via
  MASTER_SCOPE's summaries of them, not read directly. **A defect described only
  inside one of those four would not appear here.** `docs/scope/1-auto-digitizing-quality.md`
  is the most likely place for that, and is the first thing a follow-up should read.
- **No code was changed and nothing was committed by this review.**
- **Nothing here was sewn.** Same caveat the rest of the repo carries.
- **Three items are taken from the 2026-08-14 fact-check without independent
  re-verification** and are marked as such: the `ColorRangesEditor` `×`, the
  meander/streamline exposure claims, and the corpus-scorecard fixture count.
- **The full digitizer suite was started but had not finished** when this was
  written, so no fresh pass/fail count is quoted. Per this repo's own rule, test
  counts do not belong in prose anyway.
- **The `app/` and `src/` JavaScript were checked only where a specific claim
  pointed at them** (`/export` reachability, `isPurelyDigitized`). No general
  review of the Studio or the browser engine was attempted.
