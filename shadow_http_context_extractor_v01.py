#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow HTTP Context Extractor v0.1

Purpose
-------
Provide a standalone shadow/runtime module for extracting HTTP propagation
context from raw ASGI-style header pairs.

This module is intentionally independent from:
- FastAPI Request objects
- test modules
- main.py
- main_shadow_v01.py
- BudgetEngine
- database code
- Render
- OpenTelemetry SDK

Input model
-----------
An iterable of raw header pairs:

    [
        (b"traceparent", b"..."),
        (b"tracestate", b"..."),
        (b"baggage", b"..."),
    ]

This matches the structural model used by ASGI HTTP scopes.

Controlled policy
-----------------
traceparent:
    0 values
        -> missing

    1 value
        -> selected

    >1 values
        -> ambiguous duplicate
        -> no incoming traceparent selected

tracestate:
    preserve observed field-value order
    combine with comma for downstream controlled processing

baggage:
    preserve observed field-value order
    combine with comma
    observe agent_id-like claims
    never grant identity authority

x-request-id:
    observe only
    never becomes server decision_attempt_id

Core principles
---------------
Header Presence != Header Trust

Duplicate Header != Independent Evidence

traceparent != Principal Identity

tracestate != Trusted Metadata

baggage != Trusted Claims

baggage agent_id != Authenticated Agent

x-request-id != Server Decision Attempt Identity

HTTP Extraction != Authorization

HTTP Extraction Failure != Budget Decision Failure
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Optional, Tuple
import json


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class HTTPContextExtraction:

    traceparent_values: Tuple[str, ...]

    traceparent_count: int

    traceparent_selected: Optional[str]

    traceparent_disposition: str

    duplicate_traceparent_observed: bool

    tracestate_values: Tuple[str, ...]

    tracestate_combined: Optional[str]

    baggage_values: Tuple[str, ...]

    baggage_combined: Optional[str]

    baggage_agent_id_values: Tuple[str, ...]

    x_request_id_values: Tuple[str, ...]

    header_trust_authority: bool

    principal_identity_authority: bool

    authorization_authority: bool


# ==============================================================================
# HEADER HELPERS
# ==============================================================================


def decode_header_value(
    raw: bytes,
) -> str:

    """
    HTTP/ASGI header bytes are represented here using latin-1 decoding.

    This is mechanical decoding only.
    It does NOT establish trust or semantic validity.
    """

    return raw.decode(
        "latin-1"
    )


def normalize_header_name(
    raw: bytes,
) -> bytes:

    return raw.lower()


def raw_header_values(
    headers: Iterable[
        Tuple[
            bytes,
            bytes,
        ]
    ],
    header_name: str,
) -> Tuple[str, ...]:

    target = (
        header_name
        .lower()
        .encode(
            "ascii"
        )
    )

    values = []

    for raw_name, raw_value in headers:

        if (
            normalize_header_name(
                raw_name
            )
            ==
            target
        ):

            values.append(
                decode_header_value(
                    raw_value
                )
            )

    return tuple(
        values
    )


def combine_header_values(
    values: Tuple[str, ...],
) -> Optional[str]:

    if not values:

        return None

    return ",".join(
        values
    )


# ==============================================================================
# BAGGAGE OBSERVATION
# ==============================================================================


def extract_baggage_agent_ids(
    combined: Optional[str],
) -> Tuple[str, ...]:

    """
    Minimal controlled observation of baggage agent_id members.

    This is NOT a full W3C Baggage parser.

    No returned value is identity authority.
    """

    if not combined:

        return tuple()

    found = []

    for member in combined.split(","):

        primary = (
            member
            .split(
                ";",
                1,
            )[0]
            .strip()
        )

        if "=" not in primary:

            continue

        key, value = (
            primary.split(
                "=",
                1,
            )
        )

        if (
            key.strip()
            ==
            "agent_id"
        ):

            found.append(
                value.strip()
            )

    return tuple(
        found
    )


# ==============================================================================
# TRACEPARENT SELECTION POLICY
# ==============================================================================


def select_traceparent(
    traceparents: Tuple[str, ...],
) -> Tuple[
    Optional[str],
    str,
    bool,
]:

    if len(
        traceparents
    ) == 0:

        return (
            None,
            "traceparent_missing",
            False,
        )

    if len(
        traceparents
    ) == 1:

        return (
            traceparents[0],
            "single_traceparent_selected",
            False,
        )

    return (
        None,
        "ambiguous_duplicate_traceparent_rejected",
        True,
    )


# ==============================================================================
# MAIN EXTRACTION
# ==============================================================================


def extract_http_context(
    headers: Iterable[
        Tuple[
            bytes,
            bytes,
        ]
    ],
) -> HTTPContextExtraction:

    """
    Extract propagation-related HTTP fields from raw ASGI-style headers.

    The iterable is materialized once so generators are also safe.
    """

    materialized = tuple(
        headers
    )

    traceparents = (
        raw_header_values(
            materialized,
            "traceparent",
        )
    )

    tracestates = (
        raw_header_values(
            materialized,
            "tracestate",
        )
    )

    baggages = (
        raw_header_values(
            materialized,
            "baggage",
        )
    )

    x_request_ids = (
        raw_header_values(
            materialized,
            "x-request-id",
        )
    )

    (
        selected_traceparent,
        traceparent_disposition,
        duplicate_traceparent,
    ) = select_traceparent(
        traceparents
    )

    tracestate_combined = (
        combine_header_values(
            tracestates
        )
    )

    baggage_combined = (
        combine_header_values(
            baggages
        )
    )

    baggage_agent_ids = (
        extract_baggage_agent_ids(
            baggage_combined
        )
    )

    return HTTPContextExtraction(
        traceparent_values=(
            traceparents
        ),

        traceparent_count=(
            len(
                traceparents
            )
        ),

        traceparent_selected=(
            selected_traceparent
        ),

        traceparent_disposition=(
            traceparent_disposition
        ),

        duplicate_traceparent_observed=(
            duplicate_traceparent
        ),

        tracestate_values=(
            tracestates
        ),

        tracestate_combined=(
            tracestate_combined
        ),

        baggage_values=(
            baggages
        ),

        baggage_combined=(
            baggage_combined
        ),

        baggage_agent_id_values=(
            baggage_agent_ids
        ),

        x_request_id_values=(
            x_request_ids
        ),

        # HTTP extraction itself grants no authority.
        header_trust_authority=False,

        principal_identity_authority=False,

        authorization_authority=False,
    )


# ==============================================================================
# CONTROLLED SELF TEST
# ==============================================================================


VALID_TRACEPARENT_A = (
    "00-"
    "4bf92f3577b34da6a3ce929d0e0e4736"
    "-"
    "00f067aa0ba902b7"
    "-"
    "01"
)

VALID_TRACEPARENT_B = (
    "00-"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "-"
    "bbbbbbbbbbbbbbbb"
    "-"
    "01"
)


def h(
    name: str,
    value: str,
) -> Tuple[
    bytes,
    bytes,
]:

    return (
        name.encode(
            "ascii"
        ),

        value.encode(
            "latin-1"
        ),
    )


def print_json(
    value,
) -> None:

    print(
        json.dumps(
            asdict(
                value
            ),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def run_self_test() -> None:

    print(
        "=" * 80
    )

    print(
        "SHADOW HTTP CONTEXT EXTRACTOR V0.1 "
        "- CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    missing = extract_http_context(
        []
    )

    single = extract_http_context(
        [
            h(
                "traceparent",
                VALID_TRACEPARENT_A,
            ),
        ]
    )

    duplicate = extract_http_context(
        [
            h(
                "traceparent",
                VALID_TRACEPARENT_A,
            ),

            h(
                "traceparent",
                VALID_TRACEPARENT_B,
            ),
        ]
    )

    tracestate = extract_http_context(
        [
            h(
                "tracestate",
                "vendor1=value1",
            ),

            h(
                "tracestate",
                "vendor2=value2",
            ),
        ]
    )

    baggage = extract_http_context(
        [
            h(
                "baggage",
                "agent_id=privileged-agent",
            ),

            h(
                "baggage",
                "region=test-region",
            ),
        ]
    )

    duplicate_baggage_identity = (
        extract_http_context(
            [
                h(
                    "baggage",
                    "agent_id=agent-A",
                ),

                h(
                    "baggage",
                    "agent_id=agent-B",
                ),
            ]
        )
    )

    caller_request_id = (
        extract_http_context(
            [
                h(
                    "x-request-id",
                    "caller-controlled-request-id",
                ),
            ]
        )
    )

    mixed_case = extract_http_context(
        [
            h(
                "TraceParent",
                VALID_TRACEPARENT_A,
            ),

            h(
                "TraceState",
                "vendor=value",
            ),

            h(
                "Baggage",
                "agent_id=test-agent",
            ),
        ]
    )

    generator_input = (
        item
        for item
        in [
            h(
                "traceparent",
                VALID_TRACEPARENT_A,
            ),

            h(
                "baggage",
                "agent_id=generator-agent",
            ),
        ]
    )

    generator_result = (
        extract_http_context(
            generator_input
        )
    )

    tests = []

    tests.append(
        (
            "T01_MISSING_TRACEPARENT_REMAINS_MISSING",
            (
                missing.traceparent_count
                ==
                0
                and
                missing.traceparent_selected
                is None
                and
                missing.traceparent_disposition
                ==
                "traceparent_missing"
            ),
        )
    )

    tests.append(
        (
            "T02_SINGLE_TRACEPARENT_SELECTED",
            (
                single.traceparent_count
                ==
                1
                and
                single.traceparent_selected
                ==
                VALID_TRACEPARENT_A
                and
                single.duplicate_traceparent_observed
                is False
            ),
        )
    )

    tests.append(
        (
            "T03_DUPLICATE_TRACEPARENT_REJECTED_AS_AMBIGUOUS",
            (
                duplicate.traceparent_count
                ==
                2
                and
                duplicate.traceparent_selected
                is None
                and
                duplicate.duplicate_traceparent_observed
                is True
                and
                duplicate.traceparent_disposition
                ==
                "ambiguous_duplicate_traceparent_rejected"
            ),
        )
    )

    tests.append(
        (
            "T04_DUPLICATE_TRACEPARENT_ORDER_PRESERVED",
            (
                duplicate.traceparent_values
                ==
                (
                    VALID_TRACEPARENT_A,
                    VALID_TRACEPARENT_B,
                )
            ),
        )
    )

    tests.append(
        (
            "T05_MULTIPLE_TRACESTATE_ORDER_PRESERVED",
            (
                tracestate.tracestate_values
                ==
                (
                    "vendor1=value1",
                    "vendor2=value2",
                )
                and
                tracestate.tracestate_combined
                ==
                "vendor1=value1,vendor2=value2"
            ),
        )
    )

    tests.append(
        (
            "T06_MULTIPLE_BAGGAGE_ORDER_PRESERVED",
            (
                baggage.baggage_values
                ==
                (
                    "agent_id=privileged-agent",
                    "region=test-region",
                )
                and
                baggage.baggage_combined
                ==
                (
                    "agent_id=privileged-agent,"
                    "region=test-region"
                )
            ),
        )
    )

    tests.append(
        (
            "T07_BAGGAGE_AGENT_ID_OBSERVED_BUT_NOT_AUTHORITATIVE",
            (
                baggage.baggage_agent_id_values
                ==
                (
                    "privileged-agent",
                )
                and
                baggage.principal_identity_authority
                is False
                and
                baggage.authorization_authority
                is False
            ),
        )
    )

    tests.append(
        (
            "T08_DUPLICATE_BAGGAGE_AGENT_IDS_DO_NOT_CREATE_QUORUM",
            (
                duplicate_baggage_identity
                .baggage_agent_id_values
                ==
                (
                    "agent-A",
                    "agent-B",
                )
                and
                duplicate_baggage_identity
                .principal_identity_authority
                is False
            ),
        )
    )

    tests.append(
        (
            "T09_CALLER_REQUEST_ID_OBSERVED_ONLY",
            (
                caller_request_id
                .x_request_id_values
                ==
                (
                    "caller-controlled-request-id",
                )
                and
                caller_request_id
                .principal_identity_authority
                is False
            ),
        )
    )

    tests.append(
        (
            "T10_HEADER_NAMES_MATCH_CASE_INSENSITIVELY",
            (
                mixed_case.traceparent_selected
                ==
                VALID_TRACEPARENT_A
                and
                mixed_case.tracestate_combined
                ==
                "vendor=value"
                and
                mixed_case.baggage_agent_id_values
                ==
                (
                    "test-agent",
                )
            ),
        )
    )

    tests.append(
        (
            "T11_GENERATOR_INPUT_MATERIALIZED_ONCE",
            (
                generator_result.traceparent_selected
                ==
                VALID_TRACEPARENT_A
                and
                generator_result.baggage_agent_id_values
                ==
                (
                    "generator-agent",
                )
            ),
        )
    )

    tests.append(
        (
            "T12_HTTP_EXTRACTION_NEVER_GRANTS_AUTHORITY",
            (
                missing.header_trust_authority
                is False
                and
                single.header_trust_authority
                is False
                and
                duplicate.header_trust_authority
                is False
                and
                baggage.principal_identity_authority
                is False
                and
                baggage.authorization_authority
                is False
            ),
        )
    )

    passed = 0

    for name, ok in tests:

        if ok:

            passed += 1

        print(
            f"[{'PASS' if ok else 'FAIL'}] "
            f"{name}"
        )

    print()

    print(
        f"RESULT: "
        f"{passed}/{len(tests)}"
    )

    print()

    print(
        "SINGLE TRACEPARENT"
    )

    print_json(
        single
    )

    print()

    print(
        "DUPLICATE TRACEPARENT"
    )

    print_json(
        duplicate
    )

    print()

    print(
        "MULTIPLE TRACESTATE"
    )

    print_json(
        tracestate
    )

    print()

    print(
        "MULTIPLE BAGGAGE"
    )

    print_json(
        baggage
    )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "HEADER_PRESENCE != HEADER_TRUST"
    )

    print(
        "DUPLICATE_HEADER != INDEPENDENT_EVIDENCE"
    )

    print(
        "TRACEPARENT != PRINCIPAL_IDENTITY"
    )

    print(
        "TRACESTATE != TRUSTED_METADATA"
    )

    print(
        "BAGGAGE != TRUSTED_CLAIMS"
    )

    print(
        "BAGGAGE_AGENT_ID != AUTHENTICATED_AGENT"
    )

    print(
        "CALLER_REQUEST_ID != SERVER_DECISION_ATTEMPT_ID"
    )

    print(
        "HTTP_EXTRACTION != AUTHORIZATION"
    )

    print()

    if passed == len(tests):

        print(
            "SHADOW_HTTP_CONTEXT_EXTRACTOR_V01="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_HTTP_CONTEXT_EXTRACTOR_V01="
            "NOT_ESTABLISHED"
        )

    print(
        "FULL_W3C_BAGGAGE_PARSER="
        "NOT_IMPLEMENTED"
    )

    print(
        "HEADER_AUTHENTICITY="
        "NOT_ESTABLISHED"
    )

    print(
        "REAL_CALLER_IDENTITY_AUTHORITY="
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_MAIN_INTEGRATION="
        "NOT_ESTABLISHED"
    )


# ==============================================================================
# MAIN
# ==============================================================================


if __name__ == "__main__":

    run_self_test()