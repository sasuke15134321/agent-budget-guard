#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow Execution Context Binding v0.1

Purpose
-------
Model execution-context binding separately from:
- agent identity
- API target identity
- temporal proximity
- semantic authority
- enforcement authority

This controlled model is inspired by W3C Trace Context / OpenTelemetry
concepts, but is NOT a full W3C or OpenTelemetry implementation.

Key principles
--------------
Correlation != Execution Context

Execution Context != Trusted Execution Authority

Trace Context != Agent Identity

Format Valid != Authentic

Same Trace != Parent/Child

Parent/Child Structure != Trusted Causality

Remote Trace Context != Authorization

External trace headers may be forged. A valid incoming traceparent is
therefore recorded as structurally valid but untrusted.

This module does NOT:
- install OpenTelemetry
- modify Agent Budget Guard
- modify main.py
- make network calls
- authenticate an agent
- authorize execution
- prove causality
- establish cryptographic trace authenticity
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import json
import re


# ==============================================================================
# FORMAT RULES
# ==============================================================================


LOWER_HEX_32 = re.compile(
    r"^[0-9a-f]{32}$"
)

LOWER_HEX_16 = re.compile(
    r"^[0-9a-f]{16}$"
)

LOWER_HEX_2 = re.compile(
    r"^[0-9a-f]{2}$"
)

ZERO_TRACE_ID = (
    "00000000000000000000000000000000"
)

ZERO_SPAN_ID = (
    "0000000000000000"
)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class TraceParentObservation:

    raw_traceparent: Optional[str]

    parse_status: str

    version: Optional[str]

    trace_id: Optional[str]

    remote_parent_span_id: Optional[str]

    trace_flags: Optional[str]

    format_valid: bool

    remote_context: bool

    trusted_context_authority: bool

    authenticated_agent_binding: bool

    semantic_authority: bool

    binding_disposition: str


@dataclass(frozen=True)
class LocalExecutionContext:

    decision_attempt_id: str

    trace_id: Optional[str]

    span_id: Optional[str]

    parent_span_id: Optional[str]

    context_source: str

    context_format_valid: bool

    remote_parent_observed: bool

    trusted_context_authority: bool

    agent_identity_authority: bool

    semantic_authority: bool

    enforcement_authority: bool


@dataclass(frozen=True)
class ExecutionRelation:

    left_attempt_id: str

    right_attempt_id: str

    same_trace: bool

    explicit_parent_child_structure: bool

    parent_attempt_id: Optional[str]

    child_attempt_id: Optional[str]

    relation_type: str

    execution_binding_level: str

    trusted_causality: bool

    agent_identity_authority: bool

    enforcement_effect: bool


# ==============================================================================
# VALIDATION
# ==============================================================================


def valid_trace_id(
    value: Optional[str],
) -> bool:

    return bool(
        isinstance(value, str)
        and
        LOWER_HEX_32.fullmatch(value)
        and
        value != ZERO_TRACE_ID
    )


def valid_span_id(
    value: Optional[str],
) -> bool:

    return bool(
        isinstance(value, str)
        and
        LOWER_HEX_16.fullmatch(value)
        and
        value != ZERO_SPAN_ID
    )


# ==============================================================================
# TRACEPARENT PARSER
# ==============================================================================


def parse_traceparent(
    raw: Optional[str],
) -> TraceParentObservation:

    if not isinstance(
        raw,
        str,
    ):

        return TraceParentObservation(
            raw_traceparent=None,

            parse_status="missing",

            version=None,

            trace_id=None,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=False,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "execution_context_not_established"
            ),
        )

    value = raw.strip()

    if not value:

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="missing",

            version=None,

            trace_id=None,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=False,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "execution_context_not_established"
            ),
        )

    parts = value.split("-")

    if len(parts) != 4:

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="invalid_format",

            version=None,

            trace_id=None,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=True,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "ignore_for_execution_binding"
            ),
        )

    (
        version,
        trace_id,
        parent_id,
        trace_flags,
    ) = parts

    # --------------------------------------------------------------
    # Controlled v0.1 intentionally supports only W3C version 00.
    #
    # This is NOT a claim of full forward-compatible W3C parsing.
    # --------------------------------------------------------------

    if version != "00":

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="unsupported_version",

            version=version,

            trace_id=None,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=True,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "ignore_for_execution_binding"
            ),
        )

    if not valid_trace_id(
        trace_id
    ):

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="invalid_trace_id",

            version=version,

            trace_id=None,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=True,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "ignore_for_execution_binding"
            ),
        )

    if not valid_span_id(
        parent_id
    ):

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="invalid_parent_id",

            version=version,

            trace_id=trace_id,

            remote_parent_span_id=None,

            trace_flags=None,

            format_valid=False,

            remote_context=True,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "ignore_for_execution_binding"
            ),
        )

    if not (
        LOWER_HEX_2.fullmatch(
            trace_flags
        )
    ):

        return TraceParentObservation(
            raw_traceparent=value,

            parse_status="invalid_trace_flags",

            version=version,

            trace_id=trace_id,

            remote_parent_span_id=parent_id,

            trace_flags=None,

            format_valid=False,

            remote_context=True,

            trusted_context_authority=False,

            authenticated_agent_binding=False,

            semantic_authority=False,

            binding_disposition=(
                "ignore_for_execution_binding"
            ),
        )

    return TraceParentObservation(
        raw_traceparent=value,

        parse_status="parsed",

        version=version,

        trace_id=trace_id,

        remote_parent_span_id=parent_id,

        trace_flags=trace_flags,

        format_valid=True,

        remote_context=True,

        # Valid remote format is still NOT trusted authority.
        trusted_context_authority=False,

        authenticated_agent_binding=False,

        semantic_authority=False,

        binding_disposition=(
            "observe_as_untrusted_remote_context"
        ),
    )


# ==============================================================================
# LOCAL EXECUTION CONTEXT
# ==============================================================================


def build_local_context_from_remote(
    decision_attempt_id: str,

    local_span_id: str,

    remote: TraceParentObservation,

) -> LocalExecutionContext:

    if (
        not remote.format_valid
        or
        not valid_span_id(
            local_span_id
        )
    ):

        return LocalExecutionContext(
            decision_attempt_id=(
                decision_attempt_id
            ),

            trace_id=None,

            span_id=None,

            parent_span_id=None,

            context_source=(
                "not_established"
            ),

            context_format_valid=False,

            remote_parent_observed=(
                remote.remote_context
            ),

            trusted_context_authority=False,

            agent_identity_authority=False,

            semantic_authority=False,

            enforcement_authority=False,
        )

    return LocalExecutionContext(
        decision_attempt_id=(
            decision_attempt_id
        ),

        trace_id=(
            remote.trace_id
        ),

        span_id=(
            local_span_id
        ),

        parent_span_id=(
            remote.remote_parent_span_id
        ),

        context_source=(
            "remote_traceparent_observed"
        ),

        context_format_valid=True,

        remote_parent_observed=True,

        # Inheriting a structurally valid remote trace does not
        # establish trust in that remote source.
        trusted_context_authority=False,

        agent_identity_authority=False,

        semantic_authority=False,

        enforcement_authority=False,
    )


def build_local_context(
    decision_attempt_id: str,

    trace_id: str,

    span_id: str,

    parent_span_id: Optional[str] = None,

) -> LocalExecutionContext:

    trace_valid = valid_trace_id(
        trace_id
    )

    span_valid = valid_span_id(
        span_id
    )

    parent_valid = (
        parent_span_id is None
        or
        valid_span_id(
            parent_span_id
        )
    )

    format_valid = (
        trace_valid
        and
        span_valid
        and
        parent_valid
    )

    if not format_valid:

        return LocalExecutionContext(
            decision_attempt_id=(
                decision_attempt_id
            ),

            trace_id=None,

            span_id=None,

            parent_span_id=None,

            context_source=(
                "invalid_local_context"
            ),

            context_format_valid=False,

            remote_parent_observed=False,

            trusted_context_authority=False,

            agent_identity_authority=False,

            semantic_authority=False,

            enforcement_authority=False,
        )

    return LocalExecutionContext(
        decision_attempt_id=(
            decision_attempt_id
        ),

        trace_id=(
            trace_id
        ),

        span_id=(
            span_id
        ),

        parent_span_id=(
            parent_span_id
        ),

        context_source=(
            "controlled_local_context"
        ),

        context_format_valid=True,

        remote_parent_observed=False,

        # Even locally generated trace structure is observability
        # context, not authentication/authorization authority.
        trusted_context_authority=False,

        agent_identity_authority=False,

        semantic_authority=False,

        enforcement_authority=False,
    )


# ==============================================================================
# EXECUTION RELATION
# ==============================================================================


def relate_execution_contexts(
    left: LocalExecutionContext,

    right: LocalExecutionContext,

) -> ExecutionRelation:

    if (
        not left.context_format_valid
        or
        not right.context_format_valid
        or
        not left.trace_id
        or
        not right.trace_id
        or
        not left.span_id
        or
        not right.span_id
    ):

        return ExecutionRelation(
            left_attempt_id=(
                left.decision_attempt_id
            ),

            right_attempt_id=(
                right.decision_attempt_id
            ),

            same_trace=False,

            explicit_parent_child_structure=False,

            parent_attempt_id=None,

            child_attempt_id=None,

            relation_type=(
                "execution_context_not_established"
            ),

            execution_binding_level=(
                "not_established"
            ),

            trusted_causality=False,

            agent_identity_authority=False,

            enforcement_effect=False,
        )

    same_trace = (
        left.trace_id
        ==
        right.trace_id
    )

    if not same_trace:

        return ExecutionRelation(
            left_attempt_id=(
                left.decision_attempt_id
            ),

            right_attempt_id=(
                right.decision_attempt_id
            ),

            same_trace=False,

            explicit_parent_child_structure=False,

            parent_attempt_id=None,

            child_attempt_id=None,

            relation_type=(
                "different_trace"
            ),

            execution_binding_level=(
                "separate_execution_context"
            ),

            trusted_causality=False,

            agent_identity_authority=False,

            enforcement_effect=False,
        )

    # --------------------------------------------------------------
    # Same trace alone does NOT establish parent/child.
    # --------------------------------------------------------------

    if (
        right.parent_span_id
        ==
        left.span_id
    ):

        return ExecutionRelation(
            left_attempt_id=(
                left.decision_attempt_id
            ),

            right_attempt_id=(
                right.decision_attempt_id
            ),

            same_trace=True,

            explicit_parent_child_structure=True,

            parent_attempt_id=(
                left.decision_attempt_id
            ),

            child_attempt_id=(
                right.decision_attempt_id
            ),

            relation_type=(
                "parent_child_structure"
            ),

            execution_binding_level=(
                "structurally_bound_execution_candidate"
            ),

            # Structure is observed, but authority/trusted causality
            # is still not established.
            trusted_causality=False,

            agent_identity_authority=False,

            enforcement_effect=False,
        )

    if (
        left.parent_span_id
        ==
        right.span_id
    ):

        return ExecutionRelation(
            left_attempt_id=(
                left.decision_attempt_id
            ),

            right_attempt_id=(
                right.decision_attempt_id
            ),

            same_trace=True,

            explicit_parent_child_structure=True,

            parent_attempt_id=(
                right.decision_attempt_id
            ),

            child_attempt_id=(
                left.decision_attempt_id
            ),

            relation_type=(
                "parent_child_structure"
            ),

            execution_binding_level=(
                "structurally_bound_execution_candidate"
            ),

            trusted_causality=False,

            agent_identity_authority=False,

            enforcement_effect=False,
        )

    return ExecutionRelation(
        left_attempt_id=(
            left.decision_attempt_id
        ),

        right_attempt_id=(
            right.decision_attempt_id
        ),

        same_trace=True,

        explicit_parent_child_structure=False,

        parent_attempt_id=None,

        child_attempt_id=None,

        relation_type=(
            "same_trace_without_parent_child"
        ),

        execution_binding_level=(
            "trace_group_only"
        ),

        trusted_causality=False,

        agent_identity_authority=False,

        enforcement_effect=False,
    )


# ==============================================================================
# REPORT HELPERS
# ==============================================================================


def print_json(
    value,
) -> None:

    print(
        json.dumps(
            asdict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


# ==============================================================================
# CONTROLLED SELF TEST
# ==============================================================================


def run_self_test() -> None:

    print(
        "=" * 80
    )

    print(
        "SHADOW EXECUTION CONTEXT BINDING V0.1 "
        "- CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    valid_header = (
        "00-"
        "4bf92f3577b34da6a3ce929d0e0e4736"
        "-"
        "00f067aa0ba902b7"
        "-"
        "01"
    )

    parsed = parse_traceparent(
        valid_header
    )

    malformed = parse_traceparent(
        "not-a-valid-traceparent"
    )

    zero_trace = parse_traceparent(
        "00-"
        "00000000000000000000000000000000"
        "-"
        "00f067aa0ba902b7"
        "-"
        "01"
    )

    zero_parent = parse_traceparent(
        "00-"
        "4bf92f3577b34da6a3ce929d0e0e4736"
        "-"
        "0000000000000000"
        "-"
        "01"
    )

    # --------------------------------------------------------------
    # Controlled local execution contexts.
    # --------------------------------------------------------------

    parent_context = (
        build_local_context(
            decision_attempt_id="attempt-parent",

            trace_id=(
                "11111111111111111111111111111111"
            ),

            span_id=(
                "1111111111111111"
            ),
        )
    )

    child_context = (
        build_local_context(
            decision_attempt_id="attempt-child",

            trace_id=(
                "11111111111111111111111111111111"
            ),

            span_id=(
                "2222222222222222"
            ),

            parent_span_id=(
                "1111111111111111"
            ),
        )
    )

    same_trace_unrelated = (
        build_local_context(
            decision_attempt_id="attempt-peer",

            trace_id=(
                "11111111111111111111111111111111"
            ),

            span_id=(
                "3333333333333333"
            ),

            parent_span_id=(
                "9999999999999999"
            ),
        )
    )

    different_trace = (
        build_local_context(
            decision_attempt_id="attempt-other-trace",

            trace_id=(
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ),

            span_id=(
                "4444444444444444"
            ),
        )
    )

    missing_context = (
        build_local_context(
            decision_attempt_id="attempt-no-context",

            trace_id="invalid",

            span_id="invalid",
        )
    )

    parent_child_relation = (
        relate_execution_contexts(
            parent_context,
            child_context,
        )
    )

    peer_relation = (
        relate_execution_contexts(
            parent_context,
            same_trace_unrelated,
        )
    )

    different_relation = (
        relate_execution_contexts(
            parent_context,
            different_trace,
        )
    )

    missing_relation = (
        relate_execution_contexts(
            parent_context,
            missing_context,
        )
    )

    tests = []

    tests.append(
        (
            "T01_VALID_TRACEPARENT_PARSED",
            (
                parsed.format_valid
                is True
                and
                parsed.parse_status
                ==
                "parsed"
            ),
        )
    )

    tests.append(
        (
            "T02_MALFORMED_TRACEPARENT_REJECTED",
            malformed.format_valid
            is False,
        )
    )

    tests.append(
        (
            "T03_ALL_ZERO_TRACE_ID_REJECTED",
            (
                zero_trace.format_valid
                is False
                and
                zero_trace.parse_status
                ==
                "invalid_trace_id"
            ),
        )
    )

    tests.append(
        (
            "T04_ALL_ZERO_PARENT_ID_REJECTED",
            (
                zero_parent.format_valid
                is False
                and
                zero_parent.parse_status
                ==
                "invalid_parent_id"
            ),
        )
    )

    tests.append(
        (
            "T05_FORMAT_VALID_REMOTE_CONTEXT_REMAINS_UNTRUSTED",
            (
                parsed.format_valid
                is True
                and
                parsed.remote_context
                is True
                and
                parsed.trusted_context_authority
                is False
                and
                parsed.authenticated_agent_binding
                is False
            ),
        )
    )

    tests.append(
        (
            "T06_PARENT_CHILD_STRUCTURE_DETECTED",
            (
                parent_child_relation.same_trace
                is True
                and
                parent_child_relation.explicit_parent_child_structure
                is True
                and
                parent_child_relation.parent_attempt_id
                ==
                "attempt-parent"
                and
                parent_child_relation.child_attempt_id
                ==
                "attempt-child"
            ),
        )
    )

    tests.append(
        (
            "T07_SAME_TRACE_ALONE_NOT_PARENT_CHILD",
            (
                peer_relation.same_trace
                is True
                and
                peer_relation.explicit_parent_child_structure
                is False
                and
                peer_relation.execution_binding_level
                ==
                "trace_group_only"
            ),
        )
    )

    tests.append(
        (
            "T08_DIFFERENT_TRACE_REMAINS_SEPARATE",
            (
                different_relation.same_trace
                is False
                and
                different_relation.execution_binding_level
                ==
                "separate_execution_context"
            ),
        )
    )

    tests.append(
        (
            "T09_MISSING_CONTEXT_NOT_REPLACED_BY_HEURISTICS",
            (
                missing_relation.execution_binding_level
                ==
                "not_established"
                and
                missing_relation.enforcement_effect
                is False
            ),
        )
    )

    tests.append(
        (
            "T10_EXECUTION_CONTEXT_NEVER_BECOMES_IDENTITY_AUTHORITY",
            (
                parent_child_relation.agent_identity_authority
                is False
                and
                parent_child_relation.trusted_causality
                is False
                and
                parent_child_relation.enforcement_effect
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
        "VALID REMOTE TRACEPARENT"
    )

    print_json(
        parsed
    )

    print()

    print(
        "PARENT / CHILD STRUCTURE"
    )

    print_json(
        parent_child_relation
    )

    print()

    print(
        "SAME TRACE WITHOUT PARENT/CHILD"
    )

    print_json(
        peer_relation
    )

    print()

    print(
        "DIFFERENT TRACE"
    )

    print_json(
        different_relation
    )

    print()

    print(
        "MISSING EXECUTION CONTEXT"
    )

    print_json(
        missing_relation
    )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "FORMAT_VALID != AUTHENTIC"
    )

    print(
        "TRACE_CONTEXT != AGENT_IDENTITY"
    )

    print(
        "SAME_TRACE != PARENT_CHILD"
    )

    print(
        "PARENT_CHILD_STRUCTURE != TRUSTED_CAUSALITY"
    )

    print(
        "EXECUTION_CONTEXT != AUTHORIZATION"
    )

    print(
        "EXECUTION_BINDING_FAILURE != EXISTING_DECISION_FAILURE"
    )

    print()

    if passed == len(tests):

        print(
            "SHADOW_EXECUTION_CONTEXT_BINDING_V01="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_EXECUTION_CONTEXT_BINDING_V01="
            "NOT_ESTABLISHED"
        )

    print(
        "FULL_W3C_TRACE_CONTEXT_COMPLIANCE="
        "NOT_CLAIMED"
    )

    print(
        "REMOTE_TRACE_CONTEXT_TRUST="
        "NOT_ESTABLISHED"
    )

    print(
        "REAL_AGENT_IDENTITY_AUTHORITY="
        "NOT_ESTABLISHED"
    )

    print(
        "TRUSTED_CAUSALITY="
        "NOT_ESTABLISHED"
    )

    print(
        "CRYPTOGRAPHIC_TRACE_ATTESTATION="
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_EXECUTION_CONTEXT_INTEGRATION="
        "NOT_ESTABLISHED"
    )


# ==============================================================================
# MAIN
# ==============================================================================


if __name__ == "__main__":

    run_self_test()