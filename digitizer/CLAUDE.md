# digitizer/ — venv setup traps

Moved here from the root `CLAUDE.md` (2026-10-26) so it loads when a session works
in `digitizer/`. The root file keeps the one-line warning.

- **FIXED 2026-11-17 (PR #1615): `digitizer_core` imports on a cloud
container's `/usr/bin/python3.12` (3.12.3) again.** `plan_stitches` held a
21-item `with`; 3.12.3 allows 20 statically nested blocks and refused the
module (*"SyntaxError: too many statically nested blocks"*, every test and
tool failing in 0.2 s) while 3.12.13, 3.13 and CI's late 3.12 patch compiled
it. The scopes now enter through one `contextlib.ExitStack`: add a new scope
as one more `_enter(...)` line. `tests/test_with_nesting.py` fails any
`with` over 10 managers. On a checkout from before that PR, the workaround
stands: `uv python install 3.12`, venv from `$(uv python find 3.12.13)`.
*(hit 2026-11-17 on main `3608ef63`; measured on 3.12.3, 3.12.13, 3.13.18)*

- **Build that venv with `python3.12` explicitly, NOT the bare `python3`.**
`digitizer/pyproject.toml` sets `requires-python = ">=3.12"` and cloud
containers default `python3` to 3.11. `.claude/skills/run-emb-bot/SKILL.md`
has said this since it was written — it is repeated here because CLAUDE.md is
read first and the skill only when invoked.
**The trap is the `requirements.txt` path**, which does NOT enforce that floor
the way `pip install -e .` does: it gets as far as `numpy==2.5.1`, which
publishes no 3.11 wheel, and leaves a venv with no pystitch in it. The failure
is then quiet exactly where it matters — `node --test` SKIPS the six format
cross-validation tests and still reports green.
*(hit 2026-08-22; CI pins 3.12, which is why CI never saw it)*

**The `pip install -e ".[service]"` path has the MIRROR hole** — but ONLY
that path, and the difference matters. The `service` extra asks for
`fastapi>=0.115` UNPINNED, which now resolves `starlette` 1.6, whose
`TestClient` wants **`httpx2`** — a separate distribution that nothing here
pins. `service` is deliberately minimal (fastapi, uvicorn,
python-multipart), so on its own NEITHER package is present and the import
raises verbatim: *"The starlette.testclient module requires the httpx2
package to be installed."*

**Adding `dev` DOES save you, as of `starlette` 1.6.0** — so the skill's
recommended `pip install -e ".[service,dev]"` is complete, and this entry
used to say the opposite. `testclient.py` tries `httpx2`, then FALLS BACK to
`httpx`, and raises only when neither is installed; `dev` ships
`httpx>=0.27`, so you get a `StarletteDeprecationWarning` and every test in
`tests/test_service.py`. Verified 2026-08-31 by uninstalling `httpx2` and
re-collecting: `123 tests collected` (the file's size that day), warning
only. Don't spend a session chasing a
phantom — but do keep the tripwire below, because the `[service]`-only path
still fails exactly as described, and an older `starlette` has no fallback.

When it DOES bite, it is a COLLECTION error on `tests/test_service.py`, so
**none of its tests run** (123 on 2026-08-31, 180 on 2026-11-17) — and
pytest reports that as a bland `4 errors`
line beside a large passing count, which is very easy to wave past. A
session did exactly that and then published an understated number in a PR
body. **Symptom:** a collection count short of the reference in root
`CLAUDE.md` (footgun 7) by the size of that file. The gap was 123 when this
was found (`1309` against 1432) and on 2026-08-31 (`1441` against 1564).
The file holds **180** tests as of 2026-11-17, against 9368 collected in a
full run that day, so expect a gap of about 180 now and read it as a gap,
not a fixed total *(measured 2026-11-17 — full local run, 3.12.3 venv pinned
to `requirements.txt`; root `CLAUDE.md` footgun 7)*.
**Fix:** `pip install httpx2`, or install the `dev` extra.
CI is unaffected — it installs from `requirements.txt`, which pins
`starlette==1.3.1` and `httpx==0.28.1`, a combination whose TestClient works.
*(found 2026-08-26 by chasing a suspicious number in my own PR body;
scoped down 2026-08-31 after the `[service,dev]` half was measured false)*
