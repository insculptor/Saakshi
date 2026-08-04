"""The refusals that make a continuity corpus outlive the thing it sampled.

Every test here asserts a **refusal**. The value of this machinery is entirely in what it
will not write: a row with an unresolved input reads exactly like a resolved one, and is
worthless the moment the sampled service stops.
"""

from __future__ import annotations

import datetime as _dt
import textwrap
from pathlib import Path

import pytest

from saakshi.civil import CivilResolutionError, resolve, tzdb_identity
from saakshi.leaves import LeafError, digest, flatten, verify_bits
from saakshi.surface import RESOLVED_FIELDS, SurfaceError, load

# --------------------------------------------------------------------------------------
# civil — the resolved-input law
# --------------------------------------------------------------------------------------

_OK = dict(
    grid_id="g0000",
    stratum="general",
    civil=_dt.datetime(1992, 11, 11, 6, 40),
    zone="Asia/Kolkata",
    latitude=26.4499,
    longitude=80.3319,
)


def test_resolves_the_offset_rather_than_recording_the_zone_alone():
    instant = resolve(**_OK)
    # +05:30 — the fact a later database release could move, written down now.
    assert instant.utc_offset_seconds == 19800
    assert instant.utc == "1992-11-11T01:10:00Z"
    row = instant.as_row()
    assert row["utc_offset_seconds"] == 19800
    assert row["latitude"] == pytest.approx(26.4499)


def test_the_coordinate_crosses_the_text_boundary_as_bits_not_only_as_decimal():
    """⭐ An input is more determinism-bearing than an output.

    An output is compared; an input is *replayed*. A JSON library measured mis-parsing
    18.9 % of shortest-round-tripping doubles by up to 2 ULP would silently regenerate a
    different chart from a decimal coordinate, and the difference would be attributed to the
    engine. So the hex pattern is the value and the decimal beside it is display.
    """
    row = resolve(**_OK).as_row()
    assert row["latitude_bits"] == "403a732ca57a786c"
    assert row["longitude_bits"] == "4054153dd97f62b7"
    # Whole-second offsets and ISO text cross exactly and need no companion.
    assert isinstance(row["utc_offset_seconds"], int)
    assert "utc_bits" not in row


def test_refuses_an_offset_asserted_by_the_caller():
    """An aware datetime carries an offset nobody derived; the point is to derive it."""
    with pytest.raises(CivilResolutionError, match="naive local clock reading"):
        resolve(**{**_OK, "civil": _dt.datetime(1992, 11, 11, 6, 40, tzinfo=_dt.timezone.utc)})


def test_refuses_an_unknown_zone():
    with pytest.raises(CivilResolutionError, match="unknown timezone"):
        resolve(**{**_OK, "zone": "Mars/Olympus"})


@pytest.mark.parametrize("field,value", [("latitude", 90.5), ("longitude", -180.5)])
def test_refuses_an_out_of_range_coordinate(field, value):
    with pytest.raises(CivilResolutionError, match="out of range"):
        resolve(**{**_OK, field: value})


def test_refuses_an_ambiguous_local_time_instead_of_folding_it():
    """⛔ The autumn repeated hour is two instants. Picking one is not the recorder's call.

    A fold chosen here would be invisible in the fixture forever, so it is refused and the
    grid moves clear of the transition and *says* it did.
    """
    with pytest.raises(CivilResolutionError, match="ambiguous or non-existent"):
        resolve(
            **{
                **_OK,
                "zone": "America/New_York",
                "civil": _dt.datetime(2023, 11, 5, 1, 30),
                "latitude": 40.7128,
                "longitude": -74.0060,
            }
        )


def test_refuses_a_local_time_that_never_happened():
    """The spring skipped hour: the same refusal from the other side."""
    with pytest.raises(CivilResolutionError, match="ambiguous or non-existent"):
        resolve(
            **{
                **_OK,
                "zone": "America/New_York",
                "civil": _dt.datetime(2023, 3, 12, 2, 30),
                "latitude": 40.7128,
                "longitude": -74.0060,
            }
        )


def test_a_historical_offset_is_resolved_not_assumed():
    """The stratum that actually exercises a timezone database.

    ⚠ This asserts only that *an* offset was resolved and written down — not which one. A
    later database release may legitimately give a different answer for a date this old,
    and that difference is a finding, which is exactly why the value is on the row.
    """
    instant = resolve(**{**_OK, "civil": _dt.datetime(1901, 6, 15, 12, 0)})
    assert isinstance(instant.utc_offset_seconds, int)
    assert instant.utc.endswith("Z")


def test_the_database_identity_is_reported_without_being_guessed():
    identity = tzdb_identity()
    assert identity["system_version"] and identity["packaged_version"]
    # ⭐ The honest part: it does not claim to know which one answered.
    assert "unreported" in identity["answered_by"]


# --------------------------------------------------------------------------------------
# leaves — the sampled engine's names stay on the value side
# --------------------------------------------------------------------------------------


def test_a_sampled_objects_field_names_become_values_never_keys():
    """⭐ The whole reason for flattening.

    `"Sun"` is capitalised and `2` is an integer; both are legal field names in a sampled
    object and neither is a legal fixture key. As leaf *paths* they are simply data.
    """
    leaves = flatten({"Sun": {"D1": 12.5}, 2: "Moon"})
    paths = {leaf["path"] for leaf in leaves}
    assert paths == {"Sun.D1", "2"}
    assert all(set(leaf) <= {"path", "number", "bits", "integer", "text", "flag", "null",
                             "temporal", "unrepresentable"} for leaf in leaves)


def test_a_float_carries_its_bit_pattern():
    (leaf,) = flatten(1.0 / 3.0)
    assert leaf["number"] == pytest.approx(1.0 / 3.0)
    assert leaf["bits"] == "3fd5555555555555"


def test_a_bool_is_not_recorded_as_an_integer():
    """⚠ `bool` is a subclass of `int`; conflating them loses a fact about the value."""
    assert flatten(True) == [{"path": "", "flag": True}]
    assert flatten(1) == [{"path": "", "integer": 1}]


def test_an_unrepresentable_value_is_named_not_stringified():
    """⛔ `str(object())` writes a memory address that looks like a value."""
    (leaf,) = flatten(object())
    assert leaf["unrepresentable"] == "object"
    assert "0x" not in repr(leaf)


def test_a_cycle_is_refused_rather_than_walked_forever():
    node: dict = {}
    node["self"] = node
    with pytest.raises(LeafError, match="refusing to walk on"):
        flatten(node)


def test_what_the_walker_writes_passes_its_own_round_trip():
    verify_bits(flatten({"a": 0.1, "b": [1.5, -2.75], "c": "text"}), where="t")


def test_a_decimal_that_disagrees_with_its_pattern_is_refused():
    """⭐ The invariant the whole arrangement rests on.

    If the two forms disagree, a consumer reading the decimal and one reading the bits hold
    different numbers from the same row, and neither can tell. That is worse than a missing
    value, because both look correct.
    """
    leaves = flatten(1.5)
    leaves[0]["number"] = 2.5
    with pytest.raises(LeafError, match="different numbers"):
        verify_bits(leaves, where="t")


def test_the_sign_of_zero_survives_the_check():
    """⚠ `-0.0 == 0.0` is true, so the comparison goes through the pattern, not through `==`.

    Preserving the sign of zero is one of the reasons the hex form exists at all.
    """
    (leaf,) = flatten(-0.0)
    assert leaf["bits"] == "8000000000000000"
    verify_bits([leaf], where="t")
    leaf["number"] = 0.0  # a different number that compares equal
    with pytest.raises(LeafError, match="different numbers"):
        verify_bits([leaf], where="t")


def test_a_non_finite_pattern_is_refused():
    """⛔ A hex form can express what JSON decimal cannot, so the two could never agree."""
    with pytest.raises(LeafError, match="not finite"):
        verify_bits([{"path": "a", "number": 0.0, "bits": "7ff0000000000000"}], where="t")


def test_a_malformed_pattern_is_refused():
    with pytest.raises(LeafError, match="malformed bits"):
        verify_bits([{"path": "a", "number": 1.0, "bits": "abc"}], where="t")


def test_mapping_order_does_not_change_the_digest():
    """Two runs over structurally equal objects must produce an identical file."""
    assert digest(flatten({"b": 1.0, "a": 2.0})) == digest(flatten({"a": 2.0, "b": 1.0}))


def test_the_digest_moves_when_a_value_moves():
    assert digest(flatten({"a": 1.0})) != digest(flatten({"a": 1.0000000000000002}))


def test_the_digest_is_taken_over_bits_not_over_the_display_decimal():
    """⭐ A consumer must be able to check the digest without touching the decimal path.

    The decimal is display. Hashing it would make the digest reproducible only by something
    that also reproduces this writer's float formatting, and checkable only through the one
    path that must never be load-bearing — so a consumer with a mis-parsing reader could
    fail the digest while holding the right value.
    """
    leaves = flatten({"a": 0.1, "b": 3})
    tampered = [dict(leaf) for leaf in leaves]
    for leaf in tampered:
        if "number" in leaf:
            leaf["number"] = 99.0  # display changed, bits untouched
    assert digest(tampered) == digest(leaves)

    rebitted = [dict(leaf) for leaf in leaves]
    for leaf in rebitted:
        if "bits" in leaf:
            leaf["bits"] = "0000000000000000"
    assert digest(rebitted) != digest(leaves)


# --------------------------------------------------------------------------------------
# surface — a recorder may not be asked for an unresolved input
# --------------------------------------------------------------------------------------


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "surface.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_a_missing_declaration_refuses_rather_than_defaulting(tmp_path):
    """⛔ No default surface: a recorder with nothing declared writes an empty fixture."""
    with pytest.raises(SurfaceError, match="no surface declaration"):
        load(tmp_path / "absent.toml")


def test_an_unresolved_input_has_no_name_to_ask_for(tmp_path):
    """⭐ The gate, asserted directly.

    `place_name` is not in the resolved vocabulary — so a surface cannot bind a call to one,
    so a sampled call cannot depend on a place-name service.
    """
    path = _write(
        tmp_path,
        """
        [engine]
        root = "."
        label = "an implementation"
        native_builder = "datetime:datetime"
        [engine.native_fields]
        place = "place_name"
        [[atom]]
        id = "a"
        call = "math:floor"
        """,
    )
    with pytest.raises(SurfaceError, match="not a resolved input"):
        load(path, allow_dirty=True)
    assert "place_name" not in RESOLVED_FIELDS


def test_a_label_may_not_carry_a_reserved_name(tmp_path):
    path = _write(
        tmp_path,
        """
        [engine]
        root = "."
        label = "the saakshi engine"
        native_builder = "datetime:datetime"
        [engine.native_fields]
        year = "latitude"
        [[atom]]
        id = "a"
        call = "math:floor"
        """,
    )
    with pytest.raises(SurfaceError, match="reserved name"):
        load(path, allow_dirty=True)


def test_two_varied_axes_are_refused_because_they_multiply(tmp_path):
    """⛔ A grid whose size is not obvious from its declaration is what a manifest bounds."""
    path = _write(
        tmp_path,
        """
        [engine]
        root = "."
        label = "an implementation"
        native_builder = "datetime:datetime"
        [engine.native_fields]
        year = "latitude"
        [[atom]]
        id = "a"
        call = "math:floor"
        [atom.vary]
        first = [1, 2]
        second = [3, 4]
        """,
    )
    with pytest.raises(SurfaceError, match="One axis only"):
        load(path, allow_dirty=True)


def test_an_atom_id_obeys_the_fixture_key_law(tmp_path):
    """An id becomes a `section`, so it is a key and is held to the key rules."""
    path = _write(
        tmp_path,
        """
        [engine]
        root = "."
        label = "an implementation"
        native_builder = "datetime:datetime"
        [engine.native_fields]
        year = "latitude"
        [[atom]]
        id = "KpSnapshot"
        call = "math:floor"
        """,
    )
    with pytest.raises(SurfaceError, match="lower_snake_case"):
        load(path, allow_dirty=True)


def test_an_unresolvable_call_refuses_at_load_not_at_sample_time(tmp_path):
    """Refusing here means a bad surface never half-fills a fixture."""
    path = _write(
        tmp_path,
        """
        [engine]
        root = "."
        label = "an implementation"
        native_builder = "datetime:datetime"
        [engine.native_fields]
        year = "latitude"
        [[atom]]
        id = "a"
        call = "math:no_such_function"
        """,
    )
    with pytest.raises(SurfaceError, match="has no 'no_such_function'"):
        load(path, allow_dirty=True)
