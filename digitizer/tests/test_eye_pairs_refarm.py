import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import refarm  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("bad", ["", "   ", None, "relative/path"])
def test_an_empty_or_relative_worktree_path_is_refused(bad):
    with pytest.raises(ValueError):
        refarm.guard_scratch(bad, REPO)


def test_a_worktree_inside_the_repo_is_refused():
    with pytest.raises(ValueError, match="inside"):
        refarm.guard_scratch(REPO / ".claude" / "worktrees" / "x", REPO)
    with pytest.raises(ValueError, match="inside"):
        refarm.guard_scratch(REPO, REPO)


def test_an_ancestor_of_the_repo_is_refused_too():
    """Review finding 14 (2026-09-17): the guard rejected a path INSIDE the
    repo but not one the repo is inside of — and the default runner rmtree's
    whatever the guard accepts. Memory `worktree-add-empty-var-wipes-cwd`
    records what that class of path costs."""
    with pytest.raises(ValueError, match="contains"):
        refarm.guard_scratch(REPO.parent, REPO)
    with pytest.raises(ValueError, match="contains"):
        refarm.guard_scratch(REPO.parents[1], REPO)


def test_a_scratch_path_outside_the_repo_is_accepted(tmp_path):
    assert refarm.guard_scratch(tmp_path / "wt", REPO) == (tmp_path / "wt").resolve()


def stub_engine(root: Path) -> Path:
    """A fake `digitizer_core` that answers with what it was asked."""
    pkg = root / "digitizer_core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "config.py").write_text(textwrap.dedent("""
        class PipelineConfig:
            def __init__(self, **kw):
                self.kw = kw
    """))
    (pkg / "pipeline.py").write_text("def digitize(image, cfg):\n    return None, (image, cfg.kw)\n")
    (pkg / "adapter.py").write_text(textwrap.dedent("""
        def plan_to_design(plan):
            image, kw = plan
            return {"stitches": [{"x": 0, "y": 0, "type": "end"}], "colors": [],
                    "widthMM": kw["target_width_mm"], "asked": kw, "image": image}
    """))
    return root


def test_the_driver_runs_the_engine_in_its_working_directory(tmp_path):
    engine = stub_engine(tmp_path / "engine")
    design = refarm.run_ref_design(sys.executable, engine, tmp_path / "art.png",
                                   92.5, "patch", 6)
    assert design["asked"] == {"target_width_mm": 92.5, "garment_id": "patch",
                               "max_colors": 6}
    assert design["widthMM"] == 92.5


def test_the_driver_refuses_to_run_todays_engine_by_accident(tmp_path):
    """No `digitizer_core` in the working directory: the import would fall
    through to the INSTALLED package — today's engine — and the '08-27 arm'
    would silently be the base arm again. The driver must refuse instead."""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="REFUSED|No module named"):
        refarm.run_ref_design(sys.executable, empty, tmp_path / "art.png",
                              80.0, "left_chest", 6)
