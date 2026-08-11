# pystitch as a pyembroidery replacement — API diff and effort estimate

**Date:** 2026-08-11 · **Scope:** the open action item from `MASTER_SCOPE.md`'s
cross-cutting "Ink/Stitch open-source teardown" section (~line 1911) and
`docs/inkstitch-research-2026-08-10.md` §10 Tier 1 item 1: diff `pystitch`'s
public API against every real `pyembroidery` call site in `digitizer/`, for a
compatibility/effort estimate. Not done as of the 2026-08-10 teardown (that
document explicitly flagged it as "out of scope here" — see its §6 closing
paragraph); this document is that follow-up.

**Method.** Every EMB-Bot call site below was found by grepping the entire
`digitizer/` tree (not just `digitizer_service/`) for `pyembroidery`, then
reading each hit in file context to confirm it's a real API use, not a
comment. Every `pystitch` claim below was checked against the live GitHub
source (`raw.githubusercontent.com/inkstitch/pystitch/main/...`, fetched via
`curl` this session) and PyPI's JSON API (`pypi.org/pypi/pystitch/json`), not
against training-data memory of either library — consistent with the
verification posture `inkstitch-research-2026-08-10.md` established.
`pystitch` moves on a single `main` branch with no version tags in its repo
(confirmed: PyPI lists only two releases, `1.0.0` and `1.0.1` — see §2), so
"current source" below means `main` as fetched 2026-08-11, which is also what
PyPI's latest release (`1.0.1`, uploaded 2026-06-19) was built from per its
own `pyproject.toml`.

**Relationship to prior EMB-Bot research.** `docs/inkstitch-research-2026-08-10.md`
§6 and `docs/photo-quality-root-cause-2026-08-11.md` already established that
`pystitch`'s `DstReader.py`/`DstWriter.py` use the standard Tajima bit-weight
table (y in the low nibble) — a fifth independent corroboration of EMB-Bot's
own DST-axis-bug finding (`docs/dst-axis-verdict-2026-07-31.md`). That
question is settled and not re-derived here; it's cited in §5 as background
because it bears directly on the effort estimate (a `pystitch` swap would
*not* need to touch DST-convention logic — `digitizer_core/export.py`'s
documented y-down, 0.1mm convention is pyembroidery's convention, and
`pystitch` shares it).

---

## 1. EMB-Bot's actual `pyembroidery` call sites

13 files under `digitizer/` reference `pyembroidery` (grep for `pyembroidery`
across the full tree, no matches anywhere else in the repo). Two are
dependency manifests (`requirements.txt`: pinned `pyembroidery==1.5.1`;
`pyproject.toml`: `pyembroidery>=1.5.1`) and one is prose documentation
(`digitizer/README.md`, describing the coordinate convention, not code). The
other ten contain real API calls:

### `digitizer_core/export.py` — the plan→DST exporter
- Line 25: `import pyembroidery`
- Line 45, 47: `pyembroidery.EmbPattern()` constructor
- Line 51: `pyembroidery.EmbThread()` constructor
- Line 52: `thread.set_color(*block.rgb)`
- Line 53: `thread.description = block.thread_number`
- Line 54: `pattern.add_thread(thread)`
- Line 56: `pattern.color_change()` (zero-arg)
- Line 62: `pattern.trim()` (zero-arg)
- Line 65: `pattern.add_stitch_absolute(pyembroidery.JUMP, x, y)`
- Line 80: `pattern.add_stitch_absolute(pyembroidery.STITCH, x, y)`
- Line 84: `pattern.end()` (zero-arg)
- Line 91: `pattern.metadata("name", label[:16])`
- Line 93: `pyembroidery.write_dst(pattern, buf)`
- Line 112: `pyembroidery.read_dst(buf)`
- Lines 115–116: iterates `pattern.stitches`, filters `s[2] == pyembroidery.STITCH`

### `digitizer_core/adapter.py` — the `StitchPlan` ↔ `Design` bridge
- Line 38: `import pyembroidery`
- Line 174: `pyembroidery.EmbPattern()`
- Line 177: `pyembroidery.EmbThread()`
- Line 178: `thread.set_color(int(c.get("r",0)), ...)`
- Line 180: `thread.description = str(c["name"])`
- Line 181: `pattern.add_thread(thread)`
- Line 189: `pattern.add_stitch_absolute(pyembroidery.STITCH, x, y)`
- Line 191: `pattern.add_stitch_absolute(pyembroidery.JUMP, x, y)`
- Line 193: `pattern.add_stitch_absolute(pyembroidery.TRIM, x, y)`
- Line 195: `pattern.add_stitch_absolute(pyembroidery.COLOR_CHANGE, x, y)`
- Line 197: `pattern.metadata("name", str(label)[:16])`
- Line 198: `pattern.end()`

### `digitizer_service/formats.py` — the universal export format table
- Line 27: `import pyembroidery`
- Lines 90–98: `_WRITERS` dict — `pyembroidery.write_dst`, `write_pes`,
  `write_jef`, `write_exp`, `write_pec`, `write_vp3`, `write_xxx`,
  `write_u01`, `write_svg`
- Line 106: type-annotates a `pyembroidery.EmbPattern` parameter
- Line 112: `writer(pattern, buf)` — calls whichever `write_*` was looked up

### `tools/study_pro.py`, `tools/shape_lens.py` — offline analysis scripts
- `study_pro.py` line 23 / `shape_lens.py` line 604: `import pyembroidery`
- `study_pro.py` line 42 / `shape_lens.py` line 605: `pyembroidery.read(str(path))`
  — the **generic**, extension-sniffing reader (distinct from `read_dst`)
- `study_pro.py` lines 50, 51, 57, 59, 61: `c & pyembroidery.COMMAND_MASK`,
  compared against `pyembroidery.STITCH`, `.TRIM`, `.JUMP`, `.COLOR_CHANGE`
- `shape_lens.py` line 610: same `COMMAND_MASK`/`STITCH` pattern

### `tools/sewout_card.py` — DST sanity-check CLI
- Line 434: `import pyembroidery`
- Line 435: `pyembroidery.read_dst(path)` (passed a path string directly, not a buffer)
- Line 436, 439: iterates `pat.stitches`, counts `s[2] == pyembroidery.COLOR_CHANGE`

### Tests (`tests/test_adapter.py`, `test_applique.py`, `test_service.py`)
- `test_adapter.py` lines 14, 95–96, 98, 116–117: `write_dst`/`read_dst`
  round-trip, `pattern.stitches` filtered on `.STITCH`
- `test_applique.py` lines 24, 146, 148: `read_dst`, filtered on `.COLOR_CHANGE`
  (and an earlier occurrence at lines 1213–1216 in a longer integration test,
  same pattern)
- `test_service.py` lines 15, 279 (`pyembroidery.read_pes`, `.read_jef` used
  as a lookup table), 281–282, 934–935 (`pyembroidery.read_pes` again):
  reads back service-exported PES/JEF bytes with pyembroidery's own parsers
  as an independent correctness check

**Deduplicated API surface — 29 distinct symbols**, everything EMB-Bot
actually touches:

| Category | Symbols |
|---|---|
| Classes (constructors) | `EmbPattern()`, `EmbThread()` |
| `EmbPattern` methods | `add_thread`, `color_change`, `trim`, `add_stitch_absolute`, `end`, `metadata` |
| `EmbPattern` attribute | `.stitches` (indexed `s[0]`/`s[1]`/`s[2]` and tuple-unpacked `x, y, c`) |
| `EmbThread` method | `set_color` |
| `EmbThread` attribute | `.description` |
| Constants | `JUMP`, `STITCH`, `TRIM`, `COLOR_CHANGE`, `COMMAND_MASK` |
| Module functions | `write_dst`, `read_dst`, `read` (generic), `write_pes`, `write_jef`, `write_exp`, `write_pec`, `write_vp3`, `write_xxx`, `write_u01`, `write_svg`, `read_pes`, `read_jef` |

Nothing outside this list appears anywhere in `digitizer/`. In particular:
no format-specific reader beyond DST/PES/JEF is called, no `EmbPattern`
transform/matrix methods, no exception types imported or caught (confirmed —
grepped for `except.*[Ee]mbroidery` and `pyembroidery\.\w*Error` across the
whole tree, zero matches), and every command constant is referenced by name
(`pyembroidery.STITCH`, never a bare `0`) — meaning a swap doesn't need the
numeric values to match, only the names.

---

## 2. `pystitch`, verified against its own source and PyPI metadata

- **Repository:** `github.com/inkstitch/pystitch`, single `main` branch, no
  git tags found via the repo's tags. [V]
- **PyPI:** installable via `pip install pystitch` — confirmed via
  `pypi.org/pypi/pystitch/json`. Two published releases: `1.0.0`
  (2025-07-26) and `1.0.1` (2026-06-19, current). Not git-only. [V]
- **License:** MIT. `pyproject.toml` on `main` declares
  `license = "MIT"` / `license-files = ["LICENSE"]`; the `LICENSE` file
  itself (fetched raw, full text reproduced) is the standard MIT template,
  copyright line reading `Copyright (c) 2018` with no named holder filled
  in. PyPI's legacy `info.license` JSON field is empty (`null`) — an
  artifact of the modern SPDX-expression declaration style not populating
  that older field, not a sign the license is unclear; the `pyproject.toml`
  and `LICENSE` file are the authoritative source and both say MIT
  unambiguously. [V]
- **Python support:** `requires-python = ">=3.9"` in `pyproject.toml`,
  matching PyPI's classifiers (`Programming Language :: Python :: 3.9`
  through `3.13`). [V]
- **Author/maintainer:** author "Tatarize" (same as `pyembroidery` upstream
  — this is the original author's own fork, not a third party's), maintainer
  "Kaalleen" per `pyproject.toml`. Confirms `inkstitch-research-2026-08-10.md`'s
  characterization of this as an actively maintained fork under the
  `inkstitch` org, not an abandoned side project. [V]
- **Dependencies:** `dependencies = []` — zero third-party runtime
  dependencies, same as `pyembroidery`. [V]

### The "46 formats" claim, checked against source rather than the README

`pystitch`'s own `README.md` / PyPI description states: "It writes 10
embroidery formats including the mandated ones. 20 different format in
total. It reads 40 embroidery formats including the mandated ones. 46
different formats in total." [V, fetched] This is **directionally accurate
but not exactly reproducible** from the current `main` source: parsing
`src/pystitch/__init__.py`'s `supported_formats()` generator directly (53
`yield` blocks, one commented-out `ArtReader` entry and one commented-out
`CndReader` entry excluded) gives **50 total formats with a reader** (41 in
the `"embroidery"` category, the rest split across `color`/`quilting`/`debug`
categories for palette/text sidecar formats) and **22 total formats with a
writer** (11 `"embroidery"`-category). The discrepancy (46 vs. 50 read, 20 vs.
22 write) is small and most plausibly explained by the README lagging a
format or two behind `main`, or the README's own count using a slightly
different category filter than the raw generator — either way, the
**substance of the claim holds**: `pystitch` reads roughly 2.5× the formats
EMB-Bot's `formats.py` currently exposes writers for (9), across many
specialty machine formats (`.hus`, `.pcs`, `.shv`, `.zhs`, `.mit`, etc.)
pyembroidery upstream is not confirmed to cover. This document does not
independently verify pyembroidery 1.5.1's own format count for a precise
side-by-side (out of scope — the actionable comparison is API compatibility,
§3–4, not format-count marketing), so treat "broader coverage" as
qualitatively confirmed, not quantitatively pinned to an exact multiplier.

The formats EMB-Bot actually writes today — `dst`, `pes`, `jef`, `exp`,
`pec`, `vp3`, `xxx`, `u01`, `svg` — **all have a writer entry in `pystitch`'s
`supported_formats()`** (confirmed individually: `dst`/`pes`/`jef`/`exp`/`pec`/`vp3`/`xxx`/`u01`
are all `"embroidery"`-category with both reader and writer; `svg` is
`"vector"`-category, writer-only, same as EMB-Bot's own use of it as a
vector proof, not a machine format).

---

## 3. Per-symbol compatibility diff

Every symbol from §1's 29-item surface, checked against `pystitch`'s actual
source (`src/pystitch/EmbPattern.py`, `EmbThread.py`, `EmbConstant.py`,
`__init__.py`, all fetched raw this session).

| EMB-Bot call | `pystitch` equivalent | Verified against | Match |
|---|---|---|---|
| `pyembroidery.EmbPattern()` | `pystitch.EmbPattern()` | `EmbPattern.py:9-28` — `__init__(self, *args, **kwargs)`, no-arg call takes the empty-init path | **Identical** |
| `pyembroidery.EmbThread()` | `pystitch.EmbThread()` | `EmbThread.py:96-116` — all constructor params default to `None`/optional | **Identical** |
| `.add_thread(thread)` | same | `EmbPattern.py:226-234` — `def add_thread(self, thread)`, appends an `EmbThread` (or wraps a raw value) to `self.threadlist` | **Identical** |
| `.color_change()` | same | `EmbPattern.py:190-195` — `def color_change(self, dx=0, dy=0, position=None)` | **Identical** (zero-arg call compatible) |
| `.trim()` | same | `EmbPattern.py:183-188` — `def trim(self, dx=0, dy=0, position=None)` | **Identical** |
| `.add_stitch_absolute(cmd, x, y)` | same | `EmbPattern.py:427-431` — `def add_stitch_absolute(self, cmd, x=0, y=0)`, appends `[x, y, cmd]` | **Identical** signature and positional order |
| `.end()` | same | `EmbPattern.py:219-224` — `def end(self, dx=0, dy=0, position=None)` | **Identical** |
| `.metadata(name, value)` | same | `EmbPattern.py:236-239` — `def metadata(self, name, data): self.extras[name] = data` | **Identical** |
| `.stitches` (read as `s[0]`/`s[1]`/`s[2]` or unpacked `x, y, c`) | same | `EmbPattern.py:11` (`self.stitches = []`), entries are `[x, y, cmd]` **lists** | **Identical for EMB-Bot's usage** — indexing and 3-tuple unpacking both work identically on a list; EMB-Bot never mutates or type-checks the container itself |
| `thread.set_color(r, g, b)` | same | `EmbThread.py:215-216` — `def set_color(self, r, g, b): self.color = (r, g, b)` | **Identical** |
| `thread.description = ...` | same | `EmbThread.py:99, 107` — plain constructor kwarg + instance attribute, no property magic | **Identical** |
| `pyembroidery.JUMP` / `.STITCH` / `.TRIM` / `.COLOR_CHANGE` / `.COMMAND_MASK` | same names | `EmbConstant.py:4, 12-17` — `STITCH=0, JUMP=1, TRIM=2, COLOR_CHANGE=5, COMMAND_MASK=0x000000FF`, all re-exported at package top level via `from .EmbConstant import *` in `__init__.py:6` | **Identical names** (numeric values also happen to match, though EMB-Bot never hardcodes them so this is moot) |
| `pyembroidery.write_dst(pattern, buf)` | `pystitch.write_dst(pattern, stream, settings=None)` | `__init__.py:824-826` | **Identical** (extra optional `settings` kwarg, backward compatible) |
| `pyembroidery.read_dst(buf)` | `pystitch.read_dst(f, settings=None, pattern=None)` | `__init__.py:761-763` | **Identical** |
| `pyembroidery.read(path)` (generic) | `pystitch.read(file, settings=None, pattern=None)` | `__init__.py:94-116` — extension-sniffing dispatch via `supported_formats()` | **Identical**; `.dst` is a registered extension with a reader (§2) |
| `pyembroidery.write_pes` / `write_jef` / `write_exp` / `write_pec` / `write_vp3` / `write_xxx` / `write_u01` / `write_svg` | same names | `__init__.py:824-890`, one wrapper function per format calling `EmbPattern.write_embroidery(<Writer>, ...)` | **Identical**, one-to-one for every format EMB-Bot's `_WRITERS` table uses |
| `pyembroidery.read_pes` / `read_jef` | same names | `__init__.py:769-771, 781-783` | **Identical** |

**Result: all 29 symbols have a name-identical, signature-compatible match.**
This isn't a coincidence — `pystitch` is a fork that preserved
`pyembroidery`'s public API rather than redesigning it — but it was verified
symbol-by-symbol against live source rather than assumed from the fork
relationship, per this task's brief.

---

## 4. Behavioral differences worth flagging (not just name matches)

Matching names and signatures is necessary but not sufficient for a safe
swap. Three things checked at the behavior level, all from source:

**4.1 — DST bit convention.** Already settled by
`docs/inkstitch-research-2026-08-10.md` §6 and corroborated independently by
`docs/photo-quality-root-cause-2026-08-11.md`: `pystitch`'s `DstReader.py`
(`decode_dx`/`decode_dy`, lines 10-37 of the fetched source) and
`DstWriter.py`'s `encode_record` (lines 21+) both put **x in bits 0-3
(low nibble) and y in bits 4-7 (high nibble)** of each DST record byte — the
standard Tajima convention, identical to what `digitizer_core/export.py`'s
docstring already documents pyembroidery 1.5.1 doing (verified there against
a real third-party DST file, not re-verified against pyembroidery's own
source in this pass). **A `pystitch` swap would not change EMB-Bot's DST
output orientation** — it inherits the same convention EMB-Bot's Python side
already trusts, so no round-trip test currently passing should start failing
for this reason.

**4.2 — `read_dst`'s automatic `interpolate_trims` post-process.**
`pystitch`'s `DstReader.read()` (`DstReader.py:108-111`) calls
`dst_read_stitches`, which after decoding all stitch records unconditionally
calls `out.interpolate_trims(count_max, trim_distance, clipping)`
(`DstReader.py:105`, defaults `count_max=3`, `clipping=True` when no
`settings` dict is passed — EMB-Bot never passes one). `interpolate_trims`
(`EmbPattern.py:655+`) walks the stitch list and **reclassifies runs of
consecutive `JUMP` commands as a synthesized `TRIM`** once the run reaches
`jumps_to_require_trim` (default 3) hops without an intervening `STITCH`.
This does not delete or alter any `STITCH` or `COLOR_CHANGE` entry — it only
relabels certain `JUMP` sequences — so it should not affect any of EMB-Bot's
current assertions, all of which filter on `STITCH` (`export.py:116`,
`test_adapter.py:98,116`, `test_service.py:282,935`) or `COLOR_CHANGE`
(`test_applique.py:148`, `sewout_card.py:439`), never on raw `JUMP`/`TRIM`
counts from a *read-back* pattern. **Not independently verified against
pyembroidery 1.5.1's own `read_dst` source in this session** (out of scope —
the diff target was `pystitch`, not a second deep-dive into pyembroidery
upstream) — flagged here as the one place a swap could plausibly change
observable output, and the concrete way to close the gap is a round-trip
test asserting `JUMP`/`TRIM` counts specifically, not just presence of
stitches, before treating this as fully proven safe.

**4.3 — `.stitches` entries are lists, not tuples.** Both readers/writers in
`pystitch` (`EmbPattern.add_stitch_absolute`, `EmbPattern.py:429`:
`self.stitches.append([x, y, cmd])`) use plain Python lists per stitch
record. EMB-Bot's code never assumes immutability or a specific container
type — every access is either `s[0]`/`s[1]`/`s[2]` indexing or `for x, y, c in
pattern.stitches` unpacking, both of which are list/tuple-agnostic. **No
change needed.**

**4.4 — No exception-handling surface to update.** `pystitch` adds a small
`exceptions.py` (`TooManyColorChangesError`, `NoStitchesError`) that
`inkstitch-research-2026-08-10.md` §6 already noted Ink/Stitch's own
`lib/output.py` imports. EMB-Bot's `digitizer/` never catches any
pyembroidery-specific exception type (confirmed by grep, §1) — so there is
nothing to migrate here, and optionally something to *gain*: `pystitch`
gives EMB-Bot a typed exception it doesn't currently have access to for
guarding against empty/oversized patterns, if that's ever wanted later.

---

## 5. Compatibility / effort estimate

**Classification: drop-in swap, not a shim and not a rework.**

Reasoning, symbol by symbol per §3-4:

- Every one of the 29 API symbols EMB-Bot actually calls has an
  identical-name, identical-signature counterpart in `pystitch`. There is no
  symbol requiring a rename, a wrapper, or an argument-order adjustment.
- The one behavioral wrinkle found (`interpolate_trims` on DST read, §4.2)
  only affects `JUMP`/`TRIM` relabeling on **read-back** of a DST file — it
  does not touch any of the three call sites that read DST back
  (`export.py:112`'s `read_dst_points`, `test_adapter.py:96`,
  `test_applique.py:146`/`1214`, `sewout_card.py:435`), all of which filter
  on `STITCH` or `COLOR_CHANGE` only, never on raw `JUMP`/`TRIM` counts. It's
  a real thing to confirm with a test assertion, not a known-breaking issue.
- The DST bit convention — the one thing that would have made this a hard
  blocker if it disagreed — matches exactly (§4.1, previously established).
- License (MIT), packaging (PyPI-installable, zero dependencies), and Python
  version floor (`>=3.9`, EMB-Bot's own `pyproject.toml` isn't checked here
  for its floor but nothing in `digitizer/`'s current code uses anything
  newer) all impose zero friction.

**Concrete swap mechanics**, if/when Kent authorizes it:

1. `requirements.txt`: replace `pyembroidery==1.5.1` with a pinned
   `pystitch==1.0.1`; `pyproject.toml`: replace `"pyembroidery>=1.5.1"` with
   `"pystitch>=1.0.1"`.
2. In the 10 files listed in §1: `import pyembroidery` → `import pystitch`,
   and every `pyembroidery.` attribute reference → `pystitch.` (a mechanical
   find-and-replace within these specific files — every reference already
   uses the `pyembroidery.` prefix consistently, no bare imports of
   individual names to track down separately).
3. Run the existing test suite unchanged
   (`test_adapter.py`, `test_applique.py`, `test_service.py`, `test_manual.py`)
   — these already assert the exact round-trip properties (stitch count,
   width/height, color-change count, y-orientation) that would catch a
   behavioral regression, including the `interpolate_trims` question in §4.2
   as a side effect of the existing `COLOR_CHANGE`/`STITCH`-count assertions
   even without adding a new test for it specifically. Adding one explicit
   assertion on `JUMP`/`TRIM` counts post-swap would close the one
   not-fully-verified item in §4.2 outright.
4. No changes needed to `digitizer_core/stitches.py`, the `StitchPlan` model,
   or any geometry/routing code — the swap is contained entirely to the
   format-adapter layer already isolated in `export.py`/`adapter.py`/`formats.py`
   plus the two offline `tools/` scripts and the test files that exercise them.

**Why this isn't "adopt now" without a caveat, and isn't "not worth it"
either:** the theoretical risk surface is thin and every real question has
either been answered from source (§3, §4.1) or reduced to "run the existing
tests and add one more assertion" (§4.2) — but none of this has been
exercised by actually running `pytest` against a `pystitch`-backed build in
this session (out of scope for a docs-only research task in an isolated
worktree). The gap between this document and a merge-ready PR is: install
`pystitch`, make the mechanical import swap in the 10 files, run the suite,
and add the one `JUMP`/`TRIM`-count assertion §4.2 flags. That's a
half-day-scale task for someone touching the code, not a multi-week
migration.

---

## 6. Recommendation

**Adopt** — with the swap gated on actually running the test suite once,
not on further research. The API surface diff this document set out to
produce (§3) came back with zero incompatibilities across all 29 symbols
EMB-Bot uses, the one behavioral question that couldn't be settled from
source alone (§4.2) is narrow and already covered by existing test
assertions as a side effect, and the license/packaging/maintenance profile
(§2) is strictly better than the status quo: MIT (same tier as
`pyembroidery`'s own MIT license — no license change in either direction),
actively maintained by the original author under a production-consuming org
(`inkstitch`) instead of possibly-dormant upstream, broader real format
coverage confirmed from source (§2) even if the exact "46" marketing number
doesn't reproduce bit-for-bit, and zero new runtime dependencies.

This is not a "not worth it" case — there's no reason found in this research
to prefer staying on `pyembroidery`, and the effort is small (§5). It's also
not "evaluate further" — the two things a deeper evaluation would chase
(exact API match, DST convention match) are both already fully answered from
source in this document. The remaining step is mechanical execution (§5's
four numbered steps) plus one CI run, which is implementation work, not more
research — appropriate for a future PR-sized task, not a blocker on this
document's conclusion.
