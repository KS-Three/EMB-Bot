"""tools/ci_wire_tests.py picks the tests a non-digitizer PR still runs.

Pinned both ways: the repo-root readers must be in, and the heavy pipeline
files must stay out -- otherwise the subset is either unsafe or no cheaper
than the full suite."""

from tools.ci_wire_tests import wire_files


def test_the_files_that_read_outside_digitizer_are_in():
    got = set(wire_files())
    for must in ("tests/test_scope_budget.py",        # MASTER_SCOPE.md
                 "tests/test_warning_codes_mapped.py",  # app/src/lib/digitizer.js
                 "tests/test_stitchviz.py",            # app/src/lib/preview.js
                 "tests/test_machine_wire.py",         # src/*.js
                 "tests/test_house_anchor.py",         # src/fonts/*.json
                 "tests/test_doc_claims.py"):          # root docs
        assert must in got, must


def test_the_pipeline_files_are_out():
    got = set(wire_files())
    for heavy in ("tests/test_preflight.py",
                  "tests/test_photo_detection.py",
                  "tests/test_revalidate_small_shapes.py"):
        assert heavy not in got, heavy


def test_it_is_a_small_subset():
    assert 0 < len(wire_files()) < 60
