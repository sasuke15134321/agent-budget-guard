#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow Trace Trust Boundary v0.1

Purpose
-------
Model trust-boundary handling for incoming trace context separately
from trace format validation and separately from authorization.

External references motivating the controlled model:
- W3C Trace Context allows trace restart at secure-network front gates.
- OpenTelemetry recommends caution with context from untrusted sources.
- OpenTelemetry Baggage has no built-in integrity guarantee.

This is NOT a full W3C Trace Context implementation.
This is NOT an OpenTelemetry SDK integration.

Core principles
---------------
Format Valid != Trusted

Configured Boundary Class != Observed Network Trust

Observed Network Trust != Authenticated Source

Trace Preservation != Authorization

Trace Restart != Attack Detection

Tracestate != Trusted Metadata

Baggage != Trusted Claims

Boundary Policy Failure != Existing Budget Decision Failure
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import json

from shadow_execution_context_binding_v01 import (
    TraceParentObservation,
    parse_traceparent,
    valid_trace_id,
    valid_span_id,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


BOUNDARY_INTERNAL = (
    "internal_configured"
)

BOUNDARY_EXTERNAL = (
    "external_untrusted"
)

BOUNDARY_UNKNOWN = (
    "unknown"
)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class IncomingPropagationContext:

    traceparent: Optional[str]

    tracestate_present: bool

    baggage_present: bool

    boundary_class: str

    boundary_classification_source: str


@dataclass(frozen=True)
class TraceBoundaryDecision:

    boundary_class: str

    boundary_classification_source: str

    incoming_trace_format_valid: bool

    incoming_trace_remote: bool

    disposition: str

    preserve_incoming_trace_id: bool

    restart_trace: bool

    create_new_trace: bool

    propagate_tracestate: bool

    propagate_baggage: bool

    sanitize_tracestate: bool

    sanitize_baggage: bool

    incoming_trace_id: Optional[str]

    effective_trace_id: Optional[str]

    effective_span_id: Optional[str]

    configured_boundary_policy_applied: bool

    network_trust_authority: bool

    authenticated_source_binding: bool

    agent_identity_authority: bool

    semantic_authority: bool

    authorization_authority: bool

    enforcement_effect: bool


# ==============================================================================
# BOUNDARY VALIDATION
# ==============================================================================


def normalize_boundary_class(
    value: str,
) -> str:

    if value in {
        BOUNDARY_INTERNAL,
        BOUNDARY_EXTERNAL,
        BOUNDARY_UNKNOWN,
    }:
        return value

    return BOUNDARY_UNKNOWN


# ==============================================================================
# POLICY
# ==============================================================================


def apply_trace_boundary_policy(
    incoming: IncomingPropagationContext,

    generated_trace_id: str,

    generated_span_id: str,

) -> TraceBoundaryDecision:

    """
    Apply controlled local propagation policy.

    generated_trace_id / generated_span_id are supplied by the caller
    so the controlled self-test remains deterministic.

    Their format is checked, but this function does NOT claim that
    their randomness or cryptographic quality is established.
    """

    boundary = normalize_boundary_class(
        incoming.boundary_class
    )

    parsed: TraceParentObservation = (
        parse_traceparent(
            incoming.traceparent
        )
    )

    generated_ids_valid = (
        valid_trace_id(
            generated_trace_id
        )
        and
        valid_span_id(
            generated_span_id
        )
    )

    # ------------------------------------------------------------------
    # If local replacement identifiers are invalid, do not fabricate an
    # effective execution context.
    # ------------------------------------------------------------------

    if not generated_ids_valid:

        return TraceBoundaryDecision(
            boundary_class=boundary,

            boundary_classification_source=(
                incoming.boundary_classification_source
            ),

            incoming_trace_format_valid=(
                parsed.format_valid
            ),

            incoming_trace_remote=(
                parsed.remote_context
            ),

            disposition=(
                "replacement_context_not_established"
            ),

            preserve_incoming_trace_id=False,

            restart_trace=False,

            create_new_trace=False,

            propagate_tracestate=False,

            propagate_baggage=False,

            sanitize_tracestate=(
                incoming.tracestate_present
            ),

            sanitize_baggage=(
                incoming.baggage_present
            ),

            incoming_trace_id=(
                parsed.trace_id
            ),

            effective_trace_id=None,

            effective_span_id=None,

            configured_boundary_policy_applied=True,

            network_trust_authority=False,

            authenticated_source_binding=False,

            agent_identity_authority=False,

            semantic_authority=False,

            authorization_authority=False,

            enforcement_effect=False,
        )

    # ------------------------------------------------------------------
    # No valid incoming trace context:
    # create a local trace.
    #
    # W3C processing similarly creates new trace context when usable
    # traceparent is absent/invalid.
    # ------------------------------------------------------------------

    if not parsed.format_valid:

        return TraceBoundaryDecision(
            boundary_class=boundary,

            boundary_classification_source=(
                incoming.boundary_classification_source
            ),

            incoming_trace_format_valid=False,

            incoming_trace_remote=(
                parsed.remote_context
            ),

            disposition=(
                "start_new_local_trace"
            ),

            preserve_incoming_trace_id=False,

            restart_trace=False,

            create_new_trace=True,

            propagate_tracestate=False,

            propagate_baggage=False,

            sanitize_tracestate=(
                incoming.tracestate_present
            ),

            sanitize_baggage=(
                incoming.baggage_present
            ),

            incoming_trace_id=None,

            effective_trace_id=(
                generated_trace_id
            ),

            effective_span_id=(
                generated_span_id
            ),

            configured_boundary_policy_applied=True,

            network_trust_authority=False,

            authenticated_source_binding=False,

            agent_identity_authority=False,

            semantic_authority=False,

            authorization_authority=False,

            enforcement_effect=False,
        )

    # ------------------------------------------------------------------
    # Configured internal boundary:
    #
    # Preserve structurally valid trace identity for observability.
    # This still does NOT authenticate the caller.
    #
    # Baggage remains stripped by this conservative v0.1 policy.
    # ------------------------------------------------------------------

    if boundary == BOUNDARY_INTERNAL:

        return TraceBoundaryDecision(
            boundary_class=boundary,

            boundary_classification_source=(
                incoming.boundary_classification_source
            ),

            incoming_trace_format_valid=True,

            incoming_trace_remote=True,

            disposition=(
                "preserve_valid_trace_context"
            ),

            preserve_incoming_trace_id=True,

            restart_trace=False,

            create_new_trace=False,

            propagate_tracestate=(
                incoming.tracestate_present
            ),

            propagate_baggage=False,

            sanitize_tracestate=False,

            sanitize_baggage=(
                incoming.baggage_present
            ),

            incoming_trace_id=(
                parsed.trace_id
            ),

            effective_trace_id=(
                parsed.trace_id
            ),

            effective_span_id=(
                generated_span_id
            ),

            configured_boundary_policy_applied=True,

            # "internal_configured" is configuration,
            # not proof of actual network trust.
            network_trust_authority=False,

            authenticated_source_binding=False,

            agent_identity_authority=False,

            semantic_authority=False,

            authorization_authority=False,

            enforcement_effect=False,
        )

    # ------------------------------------------------------------------
    # External or unknown boundary:
    #
    # Restart trace.
    #
    # Do not carry caller-provided trace identity, tracestate or baggage
    # into the local trusted observability domain.
    # ------------------------------------------------------------------

    return TraceBoundaryDecision(
        boundary_class=boundary,

        boundary_classification_source=(
            incoming.boundary_classification_source
        ),

        incoming_trace_format_valid=True,

        incoming_trace_remote=True,

        disposition=(
            "restart_at_trust_boundary"
        ),

        preserve_incoming_trace_id=False,

        restart_trace=True,

        create_new_trace=False,

        propagate_tracestate=False,

        propagate_baggage=False,

        sanitize_tracestate=(
            incoming.tracestate_present
        ),

        sanitize_baggage=(
            incoming.baggage_present
        ),

        incoming_trace_id=(
            parsed.trace_id
        ),

        effective_trace_id=(
            generated_trace_id
        ),

        effective_span_id=(
            generated_span_id
        ),

        configured_boundary_policy_applied=True,

        network_trust_authority=False,

        authenticated_source_binding=False,

        agent_identity_authority=False,

        semantic_authority=False,

        authorization_authority=False,

        enforcement_effect=False,
    )


# ==============================================================================
# OUTPUT
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
        "SHADOW TRACE TRUST BOUNDARY V0.1 "
        "- CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    valid_traceparent = (
        "00-"
        "4bf92f3577b34da6a3ce929d0e0e4736"
        "-"
        "00f067aa0ba902b7"
        "-"
        "01"
    )

    replacement_trace = (
        "11111111111111111111111111111111"
    )

    replacement_span = (
        "2222222222222222"
    )

    # ------------------------------------------------------------------
    # A. Configured internal boundary.
    # ------------------------------------------------------------------

    internal = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=(
                valid_traceparent
            ),

            tracestate_present=True,

            baggage_present=True,

            boundary_class=(
                BOUNDARY_INTERNAL
            ),

            boundary_classification_source=(
                "controlled_fixture"
            ),
        ),

        generated_trace_id=(
            replacement_trace
        ),

        generated_span_id=(
            replacement_span
        ),
    )

    # ------------------------------------------------------------------
    # B. External boundary.
    # ------------------------------------------------------------------

    external = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=(
                valid_traceparent
            ),

            tracestate_present=True,

            baggage_present=True,

            boundary_class=(
                BOUNDARY_EXTERNAL
            ),

            boundary_classification_source=(
                "controlled_fixture"
            ),
        ),

        generated_trace_id=(
            replacement_trace
        ),

        generated_span_id=(
            replacement_span
        ),
    )

    # ------------------------------------------------------------------
    # C. Unknown boundary.
    # ------------------------------------------------------------------

    unknown = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=(
                valid_traceparent
            ),

            tracestate_present=True,

            baggage_present=False,

            boundary_class=(
                BOUNDARY_UNKNOWN
            ),

            boundary_classification_source=(
                "controlled_fixture"
            ),
        ),

        generated_trace_id=(
            replacement_trace
        ),

        generated_span_id=(
            replacement_span
        ),
    )

    # ------------------------------------------------------------------
    # D. Invalid incoming traceparent.
    # ------------------------------------------------------------------

    invalid = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=(
                "invalid-traceparent"
            ),

            tracestate_present=True,

            baggage_present=True,

            boundary_class=(
                BOUNDARY_INTERNAL
            ),

            boundary_classification_source=(
                "controlled_fixture"
            ),
        ),

        generated_trace_id=(
            replacement_trace
        ),

        generated_span_id=(
            replacement_span
        ),
    )

    # ------------------------------------------------------------------
    # E. Missing traceparent but tracestate/baggage exist.
    # ------------------------------------------------------------------

    missing = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=None,

            tracestate_present=True,

            baggage_present=True,

            boundary_class=(
                BOUNDARY_EXTERNAL
            ),

            boundary_classification_source=(
                "controlled_fixture"
            ),
        ),

        generated_trace_id=(
            replacement_trace
        ),

        generated_span_id=(
            replacement_span
        ),
    )

    tests = []

    tests.append(
        (
            "T01_INTERNAL_VALID_TRACE_PRESERVED",
            (
                internal.preserve_incoming_trace_id
                is True
                and
                internal.effective_trace_id
                ==
                "4bf92f3577b34da6a3ce929d0e0e4736"
            ),
        )
    )

    tests.append(
        (
            "T02_INTERNAL_CLASSIFICATION_NOT_TRUST_AUTHORITY",
            (
                internal.network_trust_authority
                is False
                and
                internal.authenticated_source_binding
                is False
            ),
        )
    )

    tests.append(
        (
            "T03_EXTERNAL_VALID_TRACE_RESTARTED",
            (
                external.restart_trace
                is True
                and
                external.preserve_incoming_trace_id
                is False
                and
                external.effective_trace_id
                ==
                replacement_trace
            ),
        )
    )

    tests.append(
        (
            "T04_EXTERNAL_TRACESTATE_REMOVED",
            (
                external.propagate_tracestate
                is False
                and
                external.sanitize_tracestate
                is True
            ),
        )
    )

    tests.append(
        (
            "T05_EXTERNAL_BAGGAGE_REMOVED",
            (
                external.propagate_baggage
                is False
                and
                external.sanitize_baggage
                is True
            ),
        )
    )

    tests.append(
        (
            "T06_UNKNOWN_BOUNDARY_FAILS_CONSERVATIVELY",
            (
                unknown.restart_trace
                is True
                and
                unknown.preserve_incoming_trace_id
                is False
            ),
        )
    )

    tests.append(
        (
            "T07_INVALID_TRACEPARENT_STARTS_NEW_TRACE",
            (
                invalid.incoming_trace_format_valid
                is False
                and
                invalid.create_new_trace
                is True
                and
                invalid.effective_trace_id
                ==
                replacement_trace
            ),
        )
    )

    tests.append(
        (
            "T08_ORPHAN_TRACESTATE_NOT_PROPAGATED",
            (
                missing.create_new_trace
                is True
                and
                missing.propagate_tracestate
                is False
                and
                missing.sanitize_tracestate
                is True
            ),
        )
    )

    tests.append(
        (
            "T09_BAGGAGE_NEVER_BECOMES_AUTHORITY",
            (
                internal.authorization_authority
                is False
                and
                external.authorization_authority
                is False
                and
                internal.semantic_authority
                is False
                and
                external.semantic_authority
                is False
            ),
        )
    )

    tests.append(
        (
            "T10_BOUNDARY_POLICY_HAS_NO_BUDGET_ENFORCEMENT",
            (
                internal.enforcement_effect
                is False
                and
                external.enforcement_effect
                is False
                and
                unknown.enforcement_effect
                is False
                and
                invalid.enforcement_effect
                is False
                and
                missing.enforcement_effect
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
        "INTERNAL CONFIGURED BOUNDARY"
    )

    print_json(
        internal
    )

    print()

    print(
        "EXTERNAL UNTRUSTED BOUNDARY"
    )

    print_json(
        external
    )

    print()

    print(
        "UNKNOWN BOUNDARY"
    )

    print_json(
        unknown
    )

    print()

    print(
        "INVALID INCOMING TRACE"
    )

    print_json(
        invalid
    )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "FORMAT_VALID != TRUSTED"
    )

    print(
        "CONFIGURED_BOUNDARY_CLASS != OBSERVED_NETWORK_TRUST"
    )

    print(
        "OBSERVED_NETWORK_TRUST != AUTHENTICATED_SOURCE"
    )

    print(
        "TRACE_PRESERVATION != AUTHORIZATION"
    )

    print(
        "TRACE_RESTART != ATTACK_DETECTION"
    )

    print(
        "TRACESTATE != TRUSTED_METADATA"
    )

    print(
        "BAGGAGE != TRUSTED_CLAIMS"
    )

    print(
        "BOUNDARY_POLICY_FAILURE != EXISTING_DECISION_FAILURE"
    )

    print()

    if passed == len(tests):

        print(
            "SHADOW_TRACE_TRUST_BOUNDARY_V01="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_TRACE_TRUST_BOUNDARY_V01="
            "NOT_ESTABLISHED"
        )

    print(
        "REAL_NETWORK_TRUST_CLASSIFICATION="
        "NOT_ESTABLISHED"
    )

    print(
        "AUTHENTICATED_TRACE_SOURCE="
        "NOT_ESTABLISHED"
    )

    print(
        "CRYPTOGRAPHIC_TRACE_INTEGRITY="
        "NOT_ESTABLISHED"
    )

    print(
        "BAGGAGE_INTEGRITY="
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_TRUST_BOUNDARY_INTEGRATION="
        "NOT_ESTABLISHED"
    )


# ==============================================================================
# MAIN
# ==============================================================================


if __name__ == "__main__":

    run_self_test()