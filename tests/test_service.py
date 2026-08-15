"""The service split's own refusals.

⭐ These need no network. The whole point of writing the split down as a rule over a text is
that the rule can be exercised against a text — including texts the service has never
produced and hopefully never will, which are exactly the ones that matter.

⛔ **What is being tested is that the recorder REFUSES**, not that it parses. A parser that
copes with a changed response is the failure: it would digest a region it can no longer
identify and emit a fixture claiming stability it has not got.
"""

from __future__ import annotations

import json

import pytest

from saakshi.acquisition import AcquisitionError, Retrieval
from saakshi.service import (
    DRIFT_OUTCOMES,
    DRIFT_PROPOSALS,
    ServiceFormatError,
    build_url,
    canonical_form,
    classify_drift,
    parse,
)

QUERY = {"COMMAND": "'499'", "format": "json"}

_RESULT = """\

*******************************************************************************
Ephemeris / API_USER Tue Aug  4 12:03:07 2026 Pasadena, USA      / Horizons
*******************************************************************************
Target body name: Mars (499)                      {source: mar099}
Center body name: Solar System Barycenter (0)     {source: DE441}
*******************************************************************************
Output units    : AU-D
Calendar mode   : Mixed Julian/Gregorian
Output type     : GEOMETRIC cartesian states
Reference frame : ICRF
*******************************************************************************
            JDTDB,            Calendar Date (TDB),      X,      Y,      Z,     VX,     VY,     VZ,
**********************************************************************************
$$SOE
2451545.000000000, A.D. 2000-Jan-01 12:00:00.0000,  1.0,  2.0,  3.0,  4.0,  5.0,  6.0,
$$EOE
**********************************************************************************
  Symbol meaning [1 au= 149597870.700 km, 1 day= 86400.0 s]:
*******************************************************************************
"""


def payload(result: str = _RESULT, *, signature: dict | None = None) -> bytes:
    envelope = {
        "signature": (
            {"source": "NASA/JPL Horizons API", "version": "1.2"}
            if signature is None
            else signature
        ),
        "result": result,
    }
    return json.dumps(envelope).encode("utf-8")


# --------------------------------------------------------------------------------------
# The split itself
# --------------------------------------------------------------------------------------


def test_the_transaction_stamp_is_excluded_and_never_recorded():
    """⭐ The whole design in one assertion: the stamp leaves the digest and leaves the file."""
    response = parse(payload(), query=QUERY)
    assert "12:03:07" not in response.resource_text
    assert "generation_stamp" in response.envelope_excluded
    # ⛔ Located by name, and the value is nowhere in what gets written down.
    assert "12:03:07" not in json.dumps(
        [response.service_state, response.stated, list(response.envelope_excluded)]
    )


def test_two_responses_differing_only_in_the_stamp_have_one_resource_digest():
    """⚠ The measured behaviour of the real service, pinned as a property of the split."""
    other = _RESULT.replace("12:03:07", "23:59:59")
    assert other != _RESULT
    first = canonical_form(QUERY)(payload())
    second = canonical_form(QUERY)(payload(other))
    assert first == second


def test_service_state_is_recorded_and_kept_out_of_the_digest():
    """⭐ Recorded as data, excluded from the digest — the three-way split's middle part."""
    response = parse(payload(), query=QUERY)
    assert response.service_state["target_solution"] == "mar099"
    assert response.service_state["center_solution"] == "DE441"
    assert response.service_state["interface_version"] == "1.2"
    assert "mar099" not in response.resource_text

    moved = _RESULT.replace("mar099", "mar097")
    assert canonical_form(QUERY)(payload(moved)) == canonical_form(QUERY)(payload())


def test_a_value_change_does_move_the_resource_digest():
    """⚠ The other half: excluding the volatile must not have excluded the answer."""
    moved = _RESULT.replace(" 1.0,", " 1.5,")
    assert canonical_form(QUERY)(payload(moved)) != canonical_form(QUERY)(payload())


def test_an_unclassified_change_moves_the_digest():
    """⭐ Deliberate. A region nobody classified is digested, so it becomes visible."""
    moved = _RESULT.replace("Reference frame : ICRF", "Reference frame : ICRF2")
    assert canonical_form(QUERY)(payload(moved)) != canonical_form(QUERY)(payload())


# --------------------------------------------------------------------------------------
# ⛔ The refusals
# --------------------------------------------------------------------------------------


def test_a_missing_classified_region_is_refused():
    """⛔ The classification outliving the format is the failure this refusal exists for."""
    without = _RESULT.replace(
        "Ephemeris / API_USER Tue Aug  4 12:03:07 2026 Pasadena, USA      / Horizons",
        "Ephemeris produced by Horizons",
    )
    with pytest.raises(ServiceFormatError, match="generation_stamp"):
        parse(payload(without), query=QUERY)


def test_a_missing_solution_identifier_is_refused():
    """⛔ A response that does not say what answered is not one this instrument can file."""
    without = _RESULT.replace("                      {source: mar099}", "")
    with pytest.raises(ServiceFormatError, match="target_solution"):
        parse(payload(without), query=QUERY)


def test_an_absent_interface_version_is_refused():
    with pytest.raises(ServiceFormatError, match="interface version"):
        parse(payload(signature={"source": "NASA/JPL Horizons API"}), query=QUERY)


def test_an_ambiguous_classified_region_is_refused():
    """⛔ Excluding only the first match would leave the rest in the digest."""
    doubled = _RESULT.replace(
        "Center body name: Solar System Barycenter (0)     {source: DE441}",
        "Center body name: Solar System Barycenter (0)     {source: DE441}\n"
        "Center body name: Solar System Barycenter (0)     {source: DE441}",
    )
    with pytest.raises(ServiceFormatError, match="matched 2 times"):
        parse(payload(doubled), query=QUERY)


def test_reordered_columns_are_refused():
    """⛔ A positional parser that never checks its columns reads a moved table confidently."""
    swapped = _RESULT.replace(
        "      X,      Y,      Z,     VX,     VY,     VZ,",
        "     VX,     VY,     VZ,      X,      Y,      Z,",
    )
    with pytest.raises(ServiceFormatError, match="are not"):
        parse(payload(swapped), query=QUERY)


def test_a_second_column_header_is_refused():
    """⛔ The one classified region that used to resolve its own ambiguity, silently.

    Every other region goes through `_locate`, which refuses a pattern matching twice on
    the argument that a classification matching two places cannot say which one it
    describes. This one took the first match and said nothing — and it is the region the
    data block is read against BY POSITION, so it is the one where being wrong is quietest.

    ⚠ The second header here differs from the first. A parser taking the first match reads
    every data line under a header that is not the one it was given.
    """
    twice = _RESULT.replace(
        "            JDTDB,            Calendar Date (TDB),      X,      Y,      Z,     VX,     VY,     VZ,\n",
        "            JDTDB,            Calendar Date (TDB),      X,      Y,      Z,     VX,     VY,     VZ,\n"
        "            JDTDB,            Calendar Date (TDB),      Q,      Y,      Z,     VX,     VY,     VZ,\n",
    )
    with pytest.raises(ServiceFormatError, match="matched 2 times"):
        parse(payload(twice), query=QUERY)


def test_one_column_header_is_still_accepted():
    """⭐ The control. A rule that refuses the ambiguous case and the ordinary one too has
    not tightened anything, it has stopped the instrument working — and both halves were
    measured against every response this repository has sampled before it was armed."""
    assert parse(payload(), query=QUERY).data_rows


def test_an_empty_data_block_is_refused():
    """⛔ An empty answer read as an answer is the failure the whole contract prevents."""
    empty = _RESULT.replace(
        "2451545.000000000, A.D. 2000-Jan-01 12:00:00.0000,  1.0,  2.0,  3.0,  4.0,  5.0,  6.0,\n",
        "",
    )
    with pytest.raises(ServiceFormatError, match="empty"):
        parse(payload(empty), query=QUERY)


def test_a_rejected_query_is_refused_rather_than_parsed():
    """⚠ The service reports a bad request as a well-formed document with no result."""
    with pytest.raises(ServiceFormatError, match="no 'result'"):
        parse(json.dumps({"signature": {}, "error": "no matches"}).encode(), query=QUERY)


def test_a_format_error_is_an_acquisition_error():
    """⭐ A classification that no longer matches is an acquisition failure, not a parse one."""
    assert issubclass(ServiceFormatError, AcquisitionError)


# --------------------------------------------------------------------------------------
# The rest of the split
# --------------------------------------------------------------------------------------


def test_the_stated_constants_are_resolved_out_of_the_response():
    """⭐ Resolved into the artifact, so a later consumer needs nothing the service holds."""
    response = parse(payload(), query=QUERY)
    assert response.stated["au_in_km"] == "149597870.700"
    assert response.stated["seconds_per_day"] == "86400.0"
    assert response.stated["reference_frame"] == "ICRF"


def test_the_data_block_is_parsed_past_the_trailing_separator():
    response = parse(payload(), query=QUERY)
    assert response.data_rows == (
        (
            "2451545.000000000",
            "A.D. 2000-Jan-01 12:00:00.0000",
            "1.0",
            "2.0",
            "3.0",
            "4.0",
            "5.0",
            "6.0",
        ),
    )


def test_one_query_has_one_address():
    """⚠ Sorted, so the URL is not itself in the volatile set."""
    assert build_url({"b": "2", "a": "1"}) == build_url({"a": "1", "b": "2"})


# --------------------------------------------------------------------------------------
# What the acquisition record may and may not say about a service response
# --------------------------------------------------------------------------------------


def _retrieval(payload_bytes: bytes, resource: bytes) -> Retrieval:
    import hashlib

    return Retrieval(
        url="https://example.invalid/x",
        final_url="https://example.invalid/x",
        status=200,
        size_bytes=len(payload_bytes),
        sha256=hashlib.sha256(payload_bytes).hexdigest(),
        validators={},
        payload=payload_bytes,
        prior_copy_agreed=None,
        resource=resource,
        resource_sha256=hashlib.sha256(resource).hexdigest(),
    )


def test_a_service_record_omits_the_payload_size_and_digest():
    """⛔ Both are properties of one transaction, and the response's byte count moves with
    the width of a date. Writing one down breaks reproducibility on the second Tuesday of a
    month, for a reason no reader would guess from the field name."""
    record = _retrieval(b"stamped-at-12:03:07 body", b"body").as_record()
    assert record["payload_is_the_resource"] is False
    assert "sha256" not in record
    assert "size_bytes" not in record
    assert record["resource_bytes"] == 4


def test_a_published_file_record_keeps_them():
    """⭐ Where the payload IS the resource, its size and digest are properties of the answer."""
    record = _retrieval(b"body", b"body").as_record()
    assert record["payload_is_the_resource"] is True
    assert record["sha256"] == record["resource_sha256"]
    assert record["size_bytes"] == 4


# --------------------------------------------------------------------------------------
# The drift vocabulary. ⛔ Detect and propose; never gate, never band.
# --------------------------------------------------------------------------------------


def test_every_outcome_has_a_proposal():
    """⚠ An outcome with no proposal is a detect-only report, which is the weak half."""
    assert set(DRIFT_OUTCOMES) == set(DRIFT_PROPOSALS)


def test_no_proposal_proposes_adopting_or_widening_a_band():
    """⛔ The one thing a detect-and-propose job must never propose."""
    for outcome, proposal in DRIFT_PROPOSALS.items():
        lowered = proposal.lower()
        assert "widen" not in lowered or "do not" in lowered, outcome
        assert "adopt" not in lowered, outcome


def test_a_service_state_move_is_not_hidden_by_the_digest_it_causes():
    """⭐ THE PRECEDENCE THAT MATTERS. Classifying on the digest first would collapse every
    finding into `unclassified_region_moved` and the report would stop saying anything."""
    assert (
        classify_drift(
            values_changed=0, service_state_changed=1, resource_digest_moved=True
        )
        == "service_state_moved"
    )


def test_values_win_over_everything_else():
    assert (
        classify_drift(
            values_changed=3, service_state_changed=2, resource_digest_moved=True
        )
        == "values_moved"
    )


def test_a_digest_move_nobody_can_name_is_its_own_outcome():
    """⚠ Defined by what it is NOT — the case where the recorder's model is incomplete."""
    assert (
        classify_drift(
            values_changed=0, service_state_changed=0, resource_digest_moved=True
        )
        == "unclassified_region_moved"
    )


def test_nothing_moving_is_no_drift():
    assert (
        classify_drift(
            values_changed=0, service_state_changed=0, resource_digest_moved=False
        )
        == "no_drift"
    )


def test_not_observed_is_distinct_from_no_drift():
    """⛔ Collapsing the two would make an outage read as a pass."""
    assert DRIFT_OUTCOMES["not_observed"] != DRIFT_OUTCOMES["no_drift"]
    assert "not_observed" not in {
        classify_drift(
            values_changed=v, service_state_changed=s, resource_digest_moved=d
        )
        for v in (0, 1)
        for s in (0, 1)
        for d in (False, True)
    }
