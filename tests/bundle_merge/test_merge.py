# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


import shutil
from pathlib import Path

import pytest

from ecbundle import BundleMerger


@pytest.fixture
def here():
    return Path(__file__).parent.resolve()


@pytest.fixture
def out_dir(here):
    d = here / "merge-output"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    yield d
    if d.exists():
        shutil.rmtree(d)


def _args(bundles, output):
    return {
        "no_colour": True,
        "verbose": False,
        "bundles": [str(b) for b in bundles],
        "output": str(output),
    }


def test_merge_single_update(here, out_dir):
    """Original bundle merged with a single update file."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    assert output.exists()
    content = output.read_text()
    assert "project1" in content
    assert "updated-branch" in content


def test_merge_multiple_updates_applied_in_order(here, out_dir):
    """With two updates, the later one wins on conflicting fields."""
    base = here / "bundle-merge-base.yml"
    upd1 = here / "bundle-merge-update.yml"
    upd2 = here / "bundle-merge-update2.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd1, upd2], output)).merge()

    assert rc == 0
    assert output.exists()
    content = output.read_text()
    assert "final-branch" in content
    assert "updated-branch" not in content


def test_merge_preserves_untouched_project(here, out_dir):
    """A project not mentioned in the update should be preserved unchanged."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    # project2 is only in the base, must survive the merge
    assert "project2" in content


def test_merge_missing_original_fails(here, out_dir):
    """A non-existent original bundle should cause merge to return non-zero."""
    base = here / "does-not-exist.yml"
    upd = here / "bundle-merge-update.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc != 0


def test_merge_missing_update_fails(here, out_dir):
    """A non-existent update bundle should cause merge to return non-zero."""
    base = here / "bundle-merge-base.yml"
    upd = here / "does-not-exist-update.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc != 0


def test_merge_requires_at_least_one_update(here, out_dir):
    """Passing only the original bundle should be rejected by merge()."""
    base = here / "bundle-merge-base.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base], output)).merge()

    assert rc != 0


# ---------------------------------------------------------------------------
# Options section
# ---------------------------------------------------------------------------

def test_merge_updates_existing_option(here, out_dir):
    """An option present in both base and update should take the update's values."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update-options.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    assert "without-mpi" in content
    assert "MPI disabled (updated)" in content
    # Original help text must be gone
    assert "Disable MPI" not in content


def test_merge_adds_new_option(here, out_dir):
    """An option only in the update should be added to the merged bundle."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update-options.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    assert "with-openmp" in content
    assert "ENABLE_OMP=ON" in content


def test_merge_preserves_untouched_option(here, out_dir):
    """An option not mentioned in the update should remain in the merged bundle."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update-options.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    # with-gpu is only in the base, must survive
    assert "with-gpu" in content
    assert "ENABLE_GPU=ON" in content


def test_merge_multiple_option_updates_apply_in_order(here, out_dir):
    """With two option updates, later values override earlier ones."""
    base = here / "bundle-merge-base.yml"
    upd1 = here / "bundle-merge-update-options.yml"
    upd2 = here / "bundle-merge-update-options2.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd1, upd2], output)).merge()

    assert rc == 0
    content = output.read_text()
    # Values from the second update must win
    assert "OpenMP (final)" in content
    assert "GPU (final)" in content
    # Values overridden by the second update must not remain
    assert "Enable OpenMP" not in content
    assert "Enable GPU support" not in content


# ---------------------------------------------------------------------------
# Top-level scalar keys
# ---------------------------------------------------------------------------

def test_merge_overrides_toplevel_scalars(here, out_dir):
    """Top-level scalar keys like `name` and `cmake` must be overridden by the update."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update-toplevel.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    assert "merge-test-renamed" in content
    assert "CMAKE_BUILD_TYPE=Debug" in content
    # Original scalar values must be gone
    assert "merge-test-full" not in content
    assert "CMAKE_BUILD_TYPE=Release" not in content


def test_merge_toplevel_update_preserves_projects_and_options(here, out_dir):
    """An update that only touches top-level keys must leave projects/options intact."""
    base = here / "bundle-merge-base.yml"
    upd = here / "bundle-merge-update-toplevel.yml"
    output = out_dir / "merged.yml"

    rc = BundleMerger(**_args([base, upd], output)).merge()

    assert rc == 0
    content = output.read_text()
    assert "project1" in content
    assert "project2" in content
    assert "without-mpi" in content
    assert "with-gpu" in content


def test_merge_mixed_updates_across_sections(here, out_dir):
    """Chained updates touching different sections should all be reflected."""
    base = here / "bundle-merge-base.yml"
    upd_projects = here / "bundle-merge-update.yml"          # touches projects
    upd_options = here / "bundle-merge-update-options.yml"   # touches options
    upd_toplevel = here / "bundle-merge-update-toplevel.yml" # touches scalars
    output = out_dir / "merged.yml"

    rc = BundleMerger(
        **_args([base, upd_projects, upd_options, upd_toplevel], output)
    ).merge()

    assert rc == 0
    content = output.read_text()

    # Projects update
    assert "updated-branch" in content
    # Options update
    assert "with-openmp" in content
    assert "MPI disabled (updated)" in content
    # Top-level update
    assert "merge-test-renamed" in content
    assert "CMAKE_BUILD_TYPE=Debug" in content
    # Untouched items still present
    assert "project2" in content
    assert "with-gpu" in content