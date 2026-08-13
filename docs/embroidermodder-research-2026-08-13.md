# Embroidermodder / libembroidery — upstream teardown

**Date:** 2026-08-13 · **Scope:** general research pass on
`github.com/Embroidermodder/Embroidermodder` and its sibling
`github.com/Embroidermodder/libembroidery`, asking what (if anything) EMB-Bot
should take from the C upstream that the whole Python embroidery ecosystem
descends from. Not a task from `MASTER_SCOPE.md` — this started as an
open-ended research request and is filed here so it survives a context clear.

**Method.** Repository metrics, commit log, contributor list, issue list and
org repo list come from the GitHub REST API this session. Every code-level
claim below (structs, constants, function prototypes, the format table, the
CLI man page) was verified by `curl`-ing the raw source into a scratch dir and
grepping it directly — **not** from an LLM summary of a rendered page and not
from training-data memory of the library. Line numbers cited are from
`main` as fetched 2026-08-13. Claims verified this way are marked **[V]**.
Claims that are inference, or that come from prose (README, docs site,
`TO_DO.md`) rather than code, are marked as such inline.

**Relationship to prior EMB-Bot research.** `docs/inkstitch-research-2026-08-10.md`
and `docs/pystitch-evaluation-2026-08-11.md` already cover the Python end of
this family tree (`pyembroidery`, `pystitch`, Ink/Stitch) and settled the DST
bit-convention question. This document deliberately does **not** re-derive any
of that. It covers the C ancestor those projects forked away from, and §7
explains why they left — which is the part that bears on EMB-Bot's dependency
choices. **See §3.2 for an important non-corroboration** regarding the DST
axis bug: something in libembroidery's source *looks* like a sixth data point
and is not one.

---

## 1. What the project actually is

Two things under one GitHub org, routinely conflated because the org, the app,
and the docs site all share branding:

| Repo | What it is | Language | Stars | Last push |
|---|---|---|---|---|
| `Embroidermodder` | Qt6 desktop GUI app (CAD-style editor) | C/C++ | 626 | 2026-08-03 |
| `libembroidery` | the file-format library the app sits on | C | 78 | 2026-07-11 |
| `EmbroideryMobile` | Android/iOS viewer | Java | 9 | 2025-07-30 (stale) |
| `website` | project site | Shell | 1 | 2026-07-16 |

- `Embroidermodder` created 2013-07-19; 583 commits on `main`; 25 open issues;
  homepage `libembroidery.org`. **[V, GitHub API]**
- **License: zlib** on both repos — permissive, commercial-use-safe, no
  copyleft. The only obligation is keeping the notice in `embroidery.h`.
  This is a strictly friendlier license than Ink/Stitch's GPL. **[V, API +
  `LICENSE.md`]**
- Status is self-declared **2.0.0-alpha1** for the app and **1.0-alpha** for
  the library, with both READMEs asking users to wait for the stable release
  before serious use. The docs site says the manual is "very incomplete" with
  completion "anticipated by 2026". (prose, not code)

**The library is the only part relevant to EMB-Bot.** The GUI is a desktop
CAD application; it is not a service, has no headless mode beyond the CLI in
§5, and is not a component anything could embed.

## 2. Project health — bus factor is 1

Contributors, all-time: `redteam316` (413), `JoshVarga` (47), `Metallicow`
(46), `robin-swift` (25), then a long tail of ≤13. **[V, API]**

The commit log on `main` jumps straight from **2018-04-01 to 2026-01-12**, and
every commit after that gap is `robin-swift`. **[V, API]** The first commits
after the gap read like a repository reset rather than resumed history —
`rm -fr experimental`, `compiles with Qt6`, `removing qmake, visual studio
files`, `directory structure, changelog started`. **Inference, flagged as
such:** `main`'s history has most likely been rewritten or re-based, so
`git log` on `main` is not a reliable record of what happened 2018–2026;
anyone who needs that history should check other branches rather than trust
the linear log.

What 2026 activity there is describes an in-flight architectural rewrite, not
maintenance: `starting c core`, `state and settings structs`, `command_table`,
`embroidery.h API`, plus vendoring `tomlc99` and `sds`. **[V, commit
messages]** Practical consequence: **the C API is being reshaped right now.**
Anything depending on it must pin a commit; tracking `main` would be
volatile.

## 3. The data model — the genuinely portable part

From `include/embroidery.h` on `main`, quoted verbatim:

```c
/* embroidery.h:214-219 */
#define NORMAL                      0x00    /* Stitch to (x, y). */
#define JUMP                        0x01    /* Move to (x, y). */
#define TRIM                        0x02    /* Trim and move to (x, y). */
#define STOP                        0x04    /* Pause machine for a thread change. */
#define SEQUIN                      0x08    /* Add a sequin at the current co-ordinates. */
#define END                         0x10    /* End of program. */
```

```c
/* embroidery.h:759-765 */
typedef struct EmbStitch_
{
    int flags; /* uses codes defined above */
    EmbReal x; /* absolute position (not relative) */
    EmbReal y; /* positive is up, units are in mm  */
    int color; /* color number for this stitch */
} EmbStitch;
```
**[V, both grepped from source]**

`EmbPattern` additionally carries `thread_list`, `stitch_list`, `geometry`,
`layer[EMB_MAX_LAYERS]`, `home`, `hoop_width`/`hoop_height`,
`dstJumpsPerTrim`, and string metadata (`design_name`, `category`, `author`,
`keywords`, `comments`). **[V]**

### 3.1 Public API surface

```c
/* embroidery.h — line numbers as fetched 2026-08-13 */
1359: EMB_PUBLIC EmbPattern* embp_create(void);
1367: EMB_PUBLIC void        embp_free(EmbPattern* p);
1408: EMB_PUBLIC int8_t embp_read (EmbPattern*, const int8_t* fileName, int format);
1409: EMB_PUBLIC int8_t embp_write(EmbPattern*, const int8_t* fileName, int format);
1411: EMB_PUBLIC int8_t embp_read_auto (EmbPattern*, const int8_t* fileName);
1412: EMB_PUBLIC int8_t embp_write_auto(EmbPattern*, const int8_t* fileName);
1234: EMB_PUBLIC int  convert(const int8_t *inf, const int8_t *outf);
1233: EMB_PUBLIC int  emb_identify_format(const int8_t *ending);
1363: EMB_PUBLIC void embp_addStitchAbs(EmbPattern*, EmbReal x, EmbReal y, int flags, int isAutoColorIndex);
1365: EMB_PUBLIC void embp_addStitchRel(EmbPattern*, EmbReal dx, EmbReal dy, int flags, int isAutoColorIndex);
1366: EMB_PUBLIC void embp_changeColor(EmbPattern* p, int index);
1362: EMB_PUBLIC int  embp_addThread(EmbPattern* p, EmbThread thread);
1388: EMB_PUBLIC void embp_end(EmbPattern* p);
1373: EMB_PUBLIC int  embp_realStitches(EmbPattern*);
1374: EMB_PUBLIC int  embp_jumpStitches(EmbPattern*);
1375: EMB_PUBLIC int  embp_trimStitches(EmbPattern*);
1360: EMB_PUBLIC void embp_hideStitchesOverLength(EmbPattern* p, int length);
1380: EMB_PUBLIC void embp_combineJumpStitches(EmbPattern* p);
```
**[V, all grepped]**

The shape is recognisably the same one `pyembroidery`/`pystitch` expose
(create pattern → add threads → add absolute stitches with command flags →
end → write). That is expected: the Python libraries are descendants (§7).
Note `const int8_t*` for filenames — signed-char strings, awkward at every FFI
boundary; anything binding this would want a wrapper.

### 3.2 ⚠ This is NOT a sixth corroboration of the DST axis finding

`EmbStitch.y` is commented `positive is up, units are in mm`. It is tempting
to read that as another independent data point for
`docs/dst-axis-verdict-2026-07-31.md` / `docs/pystitch-evaluation-2026-08-11.md`
§4.1. **It is not, and should not be cited as one.**

That comment describes libembroidery's **in-memory** coordinate convention.
The EMB-Bot DST question is about the **bit layout of DST records on disk** —
which nibble of the encoded byte carries x and which carries y. Those are
different layers and one does not imply the other.

**libembroidery's actual DST reader/writer bit-packing code was not read in
this session**, so this document makes no claim in either direction about it.
If that evidence is ever wanted, the place to look is the DST implementation
under `src/` (`file.c` / `unsorted.c` region), and it would need the same
`decode_dx`/`decode_dy`-level reading that the `pystitch` pass in
`docs/pystitch-evaluation-2026-08-11.md` §4.1 did. Not done here.

## 4. Format coverage — and a caveat that matters

`embroidery.h:222-282` defines **61** `EMB_FORMAT_*` constants, `EMB_FORMAT_100`
(0) through `EMB_FORMAT_ZSK` (60); `#define numberOfFormats 61` at line 319.
**[V]** The table itself is `formatTable[]` in `src/data.c`.

Format classification is only three-valued **[V, `embroidery.h:314-317`]**:

```c
#define EMBFORMAT_UNSUPPORTED          0
#define EMBFORMAT_STITCHONLY           1
#define EMBFORMAT_OBJECTONLY           2
#define EMBFORMAT_STCHANDOBJ           3 /* binary operation: 1+2=3 */
```

**Every entry in the table is `EMBFORMAT_STITCHONLY` except `.dxf` and `.svg`,
which are `EMBFORMAT_OBJECTONLY`.** **[V]** `data.c`'s own header comment
carries a `.. todo::` admitting "This list needs reviewed in case some stitch
formats also can contain object data". So the library is fundamentally a
**stitch-list** library; object/vector round-tripping is thin and
self-acknowledged as under-reviewed.

### The reader/writer state codes are undocumented — do not trust a rendered table

`EmbFormatList` (`embroidery.h:975-976`) declares `int8_t reader_state;` and
`int8_t writer_state;` — single chars, e.g.:

```c
/* data.c */
{".dst", "Tajima Embroidery Format", 'U', 'U', EMBFORMAT_STITCHONLY, 0, ...},
{".dxf", "Drawing Exchange Format",  ' ', ' ', EMBFORMAT_OBJECTONLY, 0, ...},
```

Across the whole table **only two values ever appear: `'U'` and `' '`** **[V,
grepped and counted]**, and **no legend for them exists anywhere in
`embroidery.h`, `data.c`, the README, or the docs site** — searched, not
found. The correlation is that blank entries line up with formats known to be
unimplemented (`.dxf`, `.art`, `.gnc`, `.pel`, `.pem`, `.cnd`, `.gc`), so the
working reading is **`'U'` = a handler exists, `' '` = stub/none**. That is an
inference, not documentation.

**Practical rule: treat the format table as a claim to be tested, not a
capability matrix.** Any format EMB-Bot might care about should be verified by
actually round-tripping a real file, exactly the way
`docs/pes-crossval-verdict-2026-08-04.md` handled PES.

With that caveat, the shape of coverage **[V, `data.c`]**:

- **Read + write:** `dst`, `pes`, `pec`, `jef`, `sew`, `exp`, `hus`, `vp3`,
  `pcs`, `pcd`, `pcq`, `ksm`, `max`, `xxx`, `tap`, `thr`, `plt`, `csv`, `svg`,
  plus colour-only sidecars `col`, `inf`, `edr`, `rgb`. `txt` is write-only.
- **Read only:** `csd`, `dat`, `dsb`, `u00`, `dsz`, `zsk`, `emd`, `exy`, `fxy`,
  `gt`, `inb`, `mit`, `new`, `ofm`, `phb`, `phc`, `shv`, `sst`, `stx`, `t01`,
  `t09`, `vip`, `10o`, `100`, `bro`.
- **Neither:** `dxf`, `art` (Bernina), `bmc`, `cnd`, `dem`, `eys`, `gc`
  (Smoothie G-code), `gnc`, `pel`, `pem`, `u01`.

Cross-check against EMB-Bot's own `digitizer_service/formats.py` writer table
(`dst`, `pes`, `jef`, `exp`, `pec`, `vp3`, `xxx`, `u01`, `svg`): **libembroidery
has a writer for all of them except `u01`, which is blank/blank here.** Not a
problem for EMB-Bot — it is a note that upstream is not uniformly ahead of
what EMB-Bot already ships via pyembroidery.

## 5. The `embroider` CLI

There is a command-line front end. Naming is inconsistent upstream: the
README calls it `sew`, the man page file is `sew.1`, and the man page itself
declares `.TH EMBROIDER 1 "2024-03-28"` and documents the binary as
`embroider`. **[V, raw `sew.1`]** Anyone shelling out to it should check what
the build actually produces.

Verified flags: `-o/--output`, `-f/--from`, `-t/--to`, `-F/--formats`,
`-r/--render` (PNG preview), `-s/--satin`, `-S/--stitch`, `--combine` (layer
multiple patterns), `-c/--commands`, `--test`, `--full-test-suite`,
`-q/--quiet`, `-V/--verbose`, `-v/--version`, `-h/--help`.

```sh
$ embroider -o output.dst input.pes          # convert
$ embroider -c "50 60 40 circle" -o out.dst  # scripted generation
```

The odd part: **run with no arguments it drops into an embedded PostScript
interpreter.** The man page's own example:

```
emb> 50 60 40 circle
emb> "output.dst" saveas
emb> quit
```

libembroidery embeds a basic PostScript language interpreter to process vector
drawings as designs. **[V, `sew.1`]** That explains the `postscript-language`
GitHub topic on the repo, which otherwise looks like a mistake.

## 6. What it does *not* do — the digitizing gap

This is the finding that most affects how EMB-Bot should regard upstream.

`TO_DO.md` in the app repo is stale (it still lists alpha1 items — saving
DST/PES/JEF, CSV/SVG — as WIP) but it is a fair statement of ambition, and the
ambition is a CAD program: roughly 40 unimplemented CAD commands (array,
offset, trim, extend, fillet, chamfer, break, divide…). More to the point,
**every fill algorithm is a TODO**: stippling, honeycomb, Hilbert curve,
spiral, brick, offset, gradient, Sierpinski, circle-grid, "user designed
custom fill". Also TODO: raster image import and tracing, DXF read and write,
stitch simulation, thread and machine-time estimation.

Open issues corroborate the same gap: **#94 "Generating Stitches and Saving"
has been open since 2017 with 17 comments; #44 "Open a bitmap image behind
threads for tracing" has been open since 2014 tagged `priority-high`.** **[V,
API]** Other live issues: #356 save requires the user to type both filename
and extension (Jul 2026), #329 JEF fails to display after load, #337 crash on
Linux Mint 22.1, #326/#339 no AppImage/flatpak/.deb packaging.

**Conclusion: libembroidery converts and parses; it does not digitize.** There
is no production-quality fill or satin generation upstream (`-s/--satin`
exists but the fill roadmap above shows what state that is in). The entire
problem EMB-Bot's `digitizer/` exists to solve is *not* solved here. Nothing
in this repo shortcuts EMB-Bot's core work.

## 7. Lineage — and why Ink/Stitch left

The chain, per Ink/Stitch's own developer documentation:

> libembroidery (C) → Embroidermodder MobileViewer (Java) → **pyembroidery**
> (Python, by Tatarize) → **pystitch** (inkstitch fork, current)

Ink/Stitch originally used libembroidery and then moved to pyembroidery,
"provided by @tartarize", as a Python backend to replace libembroidery in that
project. (prose, from inkstitch.org developer docs)

That is the single most useful fact in this document. **The largest, most
active open-source consumer of this format knowledge evaluated the C library
in production and moved off it.** EMB-Bot is already on the far end of that
same chain (`pyembroidery`, with `docs/pystitch-evaluation-2026-08-11.md`
recommending the `pystitch` step). There is no evidence found here that
walking back up the chain to the C original would gain anything.

## 8. What this means for EMB-Bot

**Do not adopt as a dependency.** Every reason points the same way:

1. **No capability gain.** libembroidery writes essentially the same formats
   EMB-Bot already writes through `formats.py` (§4), and the one thing EMB-Bot
   actually needs — digitizing — is explicitly unbuilt upstream (§6).
2. **Alpha, mid-rewrite, bus factor 1** (§2). The C API is being restructured
   this year by a single contributor.
3. **Cost is high.** C FFI from a Python service, `int8_t*` filename strings,
   no published bindings, and no packaging story (no PyPI/apt/AppImage
   equivalent to `pip install pystitch`).
4. **The ecosystem already voted** (§7).

**What is worth keeping from it:**

- **As a format reference.** The `data.c` format table plus one C file per
  vendor under `src/formats/` (`brother.c`, `janome.c`, `pfaff.c`,
  `barudan.c`, `singer.c`, `melco.c`, `toyota.c`, …) is a readable, zlib-
  licensed, cross-checkable second source on binary format layout. If a
  future PES/JEF/VP3 question ever needs a tiebreaker beyond pyembroidery and
  pystitch, this is where a third independent implementation lives.
  `docs/pes-crossval-verdict-2026-08-04.md` is the precedent for that kind of
  cross-validation.
- **`data/samples/` in the app repo** — an extra free test corpus, zlib
  licensed, alongside `scratch_corpus/`.
- **The stitch model as a sanity check** (§3): absolute mm coordinates,
  `NORMAL/JUMP/TRIM/STOP/SEQUIN/END`, per-stitch colour index. EMB-Bot's
  internal representation already matches this; it is reassuring
  cross-confirmation that the model is universal across three independent
  implementations, not a pyembroidery quirk.
- **`SEQUIN` (0x08)** is one flag EMB-Bot does not currently model. Not a gap
  today — noted only in case sequin work is ever scoped.

**Explicitly not recommended:** binding to it, vendoring it, shelling out to
`embroider` in the service path, or citing §3.2's `+y is up` comment as
evidence in the DST axis matter.

## 9. Open items this document does not close

- libembroidery's DST record bit-packing was **not** read (§3.2). If a sixth
  independent read on the axis question is ever wanted, that is the specific
  file to open.
- The `'U'` / `' '` reader/writer state codes remain officially undocumented
  (§4); the reading here is inference from correlation.
- `main`'s pre-2026 history could not be recovered from the linear log (§2);
  other branches were not enumerated.
- No format was empirically round-tripped through libembroidery in this
  session — nothing was built or run. Everything here is source reading plus
  API metadata.

---

## Sources

- `github.com/Embroidermodder/Embroidermodder` — repo, commit log, issues,
  contributors, `TO_DO.md` (GitHub REST API + raw files, 2026-08-13)
- `github.com/Embroidermodder/libembroidery` — `include/embroidery.h`,
  `src/data.c`, `sew.1` (raw source, fetched and grepped 2026-08-13)
- `libembroidery.org/docs/` — project documentation site (prose only)
- `inkstitch.org/developers/pyembroidery/` — the lineage statement in §7
- Prior EMB-Bot research: `docs/inkstitch-research-2026-08-10.md`,
  `docs/pystitch-evaluation-2026-08-11.md`,
  `docs/dst-axis-verdict-2026-07-31.md`,
  `docs/pes-crossval-verdict-2026-08-04.md`
