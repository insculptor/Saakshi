"""The grid's own property: a bounded run must still be a stratified one.

⚠ This exists because the first version failed it. Enumerating year-major and cutting at
`--natives` produced a subset that was three-quarters one stratum — a bounded sample that
looked like coverage because it had a row count. A limit that quietly picks one corner is
worse than no limit at all.
"""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "generators" / "r5_continuity.py"
_spec = importlib.util.spec_from_file_location("_r5_continuity", _PATH)
assert _spec and _spec.loader
r5 = importlib.util.module_from_spec(_spec)
sys.modules["_r5_continuity"] = r5
_spec.loader.exec_module(r5)

FULL = len(r5.YEARS) * len(r5.SITES)


def _strata(grid):
    return collections.Counter(instant.stratum for instant, _ in grid)


def test_the_full_grid_is_every_year_at_every_site():
    grid = r5.build_grid(None)
    assert len(grid) == FULL
    assert len({instant.grid_id for instant, _ in grid}) == FULL


@pytest.mark.parametrize("limit", [8, 16, 32, 64])
def test_a_bounded_run_still_reaches_every_stratum(limit):
    """⭐ The property the first version broke."""
    grid = r5.build_grid(limit)
    assert len(grid) == limit
    assert set(_strata(grid)) == set(_strata(r5.build_grid(None)))


@pytest.mark.parametrize("limit", [8, 16, 32])
def test_a_bounded_run_spans_the_whole_epoch_range(limit):
    """A subset that stops at the fourth year is not a sample of a two-century range."""
    grid = r5.build_grid(limit)
    years = {int(instant.civil[:4]) for instant, _ in grid}
    quarter = len(r5.YEARS) // 4
    assert any(y in years for y in r5.YEARS[:quarter]), "no early epoch"
    assert any(y in years for y in r5.YEARS[-quarter:]), "no late epoch"


@pytest.mark.parametrize("limit", [8, 16, 32, 64])
def test_a_bounded_run_reaches_sites_an_even_stride_would_alias_past(limit):
    """⚠ The exact failure: a stride aliased against the site count and picked 4 of 16.

    The polar sites are the ones it lost, and they are the ones a house calculation is most
    likely to behave differently at — so losing them cost the corpus its most informative
    rows while the row count still looked right.
    """
    grid = r5.build_grid(limit)
    latitudes = [instant.latitude for instant, _ in grid]
    assert any(abs(lat) > 66.5 for lat in latitudes), "lost the polar sites"
    assert any(abs(lat) < 5.0 for lat in latitudes), "lost the equatorial sites"


def test_no_stratum_swamps_a_bounded_run():
    grid = r5.build_grid(32)
    counts = _strata(grid)
    # The failure was 798 of 1200 rows in one stratum. Any even-handed selection is far
    # from that; this pins the shape without pretending the strata are equal in size.
    assert max(counts.values()) / len(grid) < 0.75


def test_grid_ids_are_stable_across_limits():
    """Two runs at different sizes must be comparable row for row."""
    small = {instant.grid_id for instant, _ in r5.build_grid(8)}
    large = {instant.grid_id for instant, _ in r5.build_grid(64)}
    assert small <= large


def test_every_point_carries_a_resolved_offset_and_coordinate():
    """⭐ The gate, asserted over the grid the generator actually emits."""
    for instant, _ in r5.build_grid(32):
        row = instant.as_row()
        assert isinstance(row["utc_offset_seconds"], int)
        assert row["utc"].endswith("Z")
        assert isinstance(row["latitude"], float)
        assert isinstance(row["longitude"], float)


def test_the_grid_is_deterministic():
    first = [(i.grid_id, i.utc) for i, _ in r5.build_grid(24)]
    second = [(i.grid_id, i.utc) for i, _ in r5.build_grid(24)]
    assert first == second
