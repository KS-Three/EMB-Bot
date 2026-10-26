# digitizer/ — venv setup traps

Moved here from the root `CLAUDE.md` (2026-10-26) so it loads when a session works
in `digitizer/`. The root file keeps the one-line warning.

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
`httpx>=0.27`, so you get a `StarletteDeprecationWarning` and all 123 tests.
Verified 2026-08-31 by uninstalling `httpx2` and re-collecting:
`123 tests collected`, warning only. Don't spend a session chasing a
phantom — but do keep the tripwire below, because the `[service]`-only path
still fails exactly as described, and an older `starlette` has no fallback.

When it DOES bite, it is a COLLECTION error on `tests/test_service.py`, so
its **123 tests never run** — and pytest reports that as a bland `4 errors`
line beside a large passing count, which is very easy to wave past. A
session did exactly that and then published an understated number in a PR
body. **Symptom:** a collection count ~123 short of the reference below
(`1309` against 1432 when this was found; `1441` against 1564 on
2026-08-31). **Fix:** `pip install httpx2`, or install the `dev` extra.
CI is unaffected — it installs from `requirements.txt`, which pins
`starlette==1.3.1` and `httpx==0.28.1`, a combination whose TestClient works.
*(found 2026-08-26 by chasing a suspicious number in my own PR body;
scoped down 2026-08-31 after the `[service,dev]` half was measured false)*
