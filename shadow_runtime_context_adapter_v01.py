#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow Runtime Context Adapter v0.1

Purpose
-------
Integrate, in a controlled local model:

    Incoming propagation context
        ->
    Trace Trust Boundary Decision
        ->
    Execution Context Observation
        ->
    Shadow Runtime Observation
        ->
    Decision Attempt Cell

without allowing the shadow pipeline to alter the existing
Agent Budget Guard decision.

Core principles
---------------
Decision Attempt Identity != Execution Trace Identity

Trace Continuity != Caller Identity

Same Trace != Same Principal

Boundary Restart != New Decision Attempt

Configured Boundary Class != Network Trust Authority

Baggage Claim != Authenticated Identity

Shadow Pipeline Failure != Existing Decision Failure

This module does NOT:
- modify main.py
- modify main_shadow_v01.py
- modify database schema
- deploy to Render
- authenticate callers
- establish real network trust
- establish semantic authority
- establish cryptographic trace integrity
- enforce Budget Guard decisions
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
import json

from shadow_trace_trust_boundary_v01 import (
    IncomingPropagationContext,
    TraceBoundaryDecision,
    apply_trace_boundary_policy,
    BOUNDARY_INTERNAL,
    BOUNDARY_EXTERNAL,
    BOUNDARY_UNKNOWN,
)

from shadow_execution_context_binding_v01 import (
    LocalExecutionContext,
    valid_trace_id,
    valid_span_id,
)

from shadow_runtime_cell_aggregator_v01 import (
    DecisionAttemptCell,
)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class ExistingBudgetDecision:

    approved: bool
    risk_level: str
    reason: str


@dataclass(frozen=True)
class RuntimeContextInput:

    request_id: str
    decision_id: str

    agent_id: str
    api_url: str

    declared_action_type: Optional[str]

    caller_label: Optional[str]

    incoming_traceparent: Optional[str]

    tracestate_present: bool
    baggage_present: bool

    baggage_agent_id_claim: Optional[str]

    boundary_class: str
    boundary_classification_source: str

    generated_trace_id: str
    generated_span_id: str


@dataclass(frozen=True)
class RuntimeContextObservation:

    request_id: str
    decision_attempt_id: str
    decision_id: str

    agent_id: str
    api_url: str

    declared_action_type: Optional[str]

    caller_label: Optional[str]
    caller_identity_authority: bool

    boundary_class: str
    boundary_disposition: str

    incoming_trace_id: Optional[str]
    effective_trace_id: Optional[str]
    effective_span_id: Optional[str]

    trace_restarted: bool
    trace_preserved: bool
    new_trace_created: bool

    network_trust_authority: bool
    authenticated_trace_source: bool
    agent_identity_authority: bool

    baggage_agent_id_claim: Optional[str]
    baggage_identity_authority: bool

    action_authority: bool
    semantic_authority: bool

    existing_approved: bool
    existing_risk_level: str
    existing_reason: str

    shadow_recommendation: str

    shadow_pipeline_status: str

    enforcement_effect: bool


@dataclass(frozen=True)
class InsulatedShadowResult:

    existing_decision: ExistingBudgetDecision

    shadow_observation: Optional[
        RuntimeContextObservation
    ]

    shadow_exception_observed: bool

    shadow_error_type: Optional[str]

    shadow_error_message: Optional[str]

    existing_decision_preserved: bool


# ==============================================================================
# BASIC VALIDATION
# ==============================================================================


def nonempty(
    value: Optional[str],
) -> bool:

    return bool(
        isinstance(value, str)
        and
        value.strip()
    )


# ==============================================================================
# EXECUTION CONTEXT CONSTRUCTION
# ==============================================================================


def build_execution_context(
    runtime_input: RuntimeContextInput,
    boundary: TraceBoundaryDecision,
) -> LocalExecutionContext:

    """
    Convert the boundary decision into a local execution-context observation.

    Important:
        effective trace/span context is observability structure only.
        It does NOT become caller identity or authorization authority.
    """

    if (
        not boundary.effective_trace_id
        or
        not boundary.effective_span_id
        or
        not valid_trace_id(
            boundary.effective_trace_id
        )
        or
        not valid_span_id(
            boundary.effective_span_id
        )
    ):

        return LocalExecutionContext(
            decision_attempt_id=(
                runtime_input.request_id
            ),

            trace_id=None,

            span_id=None,

            parent_span_id=None,

            context_source=(
                "boundary_context_not_established"
            ),

            context_format_valid=False,

            remote_parent_observed=(
                boundary.incoming_trace_remote
            ),

            trusted_context_authority=False,

            agent_identity_authority=False,

            semantic_authority=False,

            enforcement_authority=False,
        )

    return LocalExecutionContext(
        decision_attempt_id=(
            runtime_input.request_id
        ),

        trace_id=(
            boundary.effective_trace_id
        ),

        span_id=(
            boundary.effective_span_id
        ),

        parent_span_id=None,

        context_source=(
            "trace_boundary_policy_output"
        ),

        context_format_valid=True,

        remote_parent_observed=(
            boundary.incoming_trace_remote
        ),

        trusted_context_authority=False,

        agent_identity_authority=False,

        semantic_authority=False,

        enforcement_authority=False,
    )


# ==============================================================================
# SHADOW RECOMMENDATION
# ==============================================================================


def derive_shadow_recommendation(
    runtime_input: RuntimeContextInput,
    execution_context: LocalExecutionContext,
) -> str:

    if (
        not execution_context.context_format_valid
    ):

        return (
            "review_signal"
        )

    if not nonempty(
        runtime_input.declared_action_type
    ):

        return (
            "insufficient_evidence"
        )

    return (
        "observe_only"
    )


# ==============================================================================
# ADAPTER
# ==============================================================================


def observe_runtime_context(
    runtime_input: RuntimeContextInput,
    existing_decision: ExistingBudgetDecision,
) -> RuntimeContextObservation:

    """
    Build one controlled runtime-context shadow observation.

    request_id remains the decision_attempt_id regardless of:
    - trace preservation
    - trace restart
    - new trace creation

    effective_trace_id is never promoted to decision identity.
    """

    boundary = apply_trace_boundary_policy(
        IncomingPropagationContext(
            traceparent=(
                runtime_input.incoming_traceparent
            ),

            tracestate_present=(
                runtime_input.tracestate_present
            ),

            baggage_present=(
                runtime_input.baggage_present
            ),

            boundary_class=(
                runtime_input.boundary_class
            ),

            boundary_classification_source=(
                runtime_input.boundary_classification_source
            ),
        ),

        generated_trace_id=(
            runtime_input.generated_trace_id
        ),

        generated_span_id=(
            runtime_input.generated_span_id
        ),
    )

    execution_context = (
        build_execution_context(
            runtime_input,
            boundary,
        )
    )

    recommendation = (
        derive_shadow_recommendation(
            runtime_input,
            execution_context,
        )
    )

    return RuntimeContextObservation(
        request_id=(
            runtime_input.request_id
        ),

        decision_attempt_id=(
            runtime_input.request_id
        ),

        decision_id=(
            runtime_input.decision_id
        ),

        agent_id=(
            runtime_input.agent_id
        ),

        api_url=(
            runtime_input.api_url
        ),

        declared_action_type=(
            runtime_input.declared_action_type
        ),

        caller_label=(
            runtime_input.caller_label
        ),

        # Fixture caller labels are observation labels only.
        caller_identity_authority=False,

        boundary_class=(
            boundary.boundary_class
        ),

        boundary_disposition=(
            boundary.disposition
        ),

        incoming_trace_id=(
            boundary.incoming_trace_id
        ),

        effective_trace_id=(
            boundary.effective_trace_id
        ),

        effective_span_id=(
            boundary.effective_span_id
        ),

        trace_restarted=(
            boundary.restart_trace
        ),

        trace_preserved=(
            boundary.preserve_incoming_trace_id
        ),

        new_trace_created=(
            boundary.create_new_trace
        ),

        network_trust_authority=(
            boundary.network_trust_authority
        ),

        authenticated_trace_source=(
            boundary.authenticated_source_binding
        ),

        agent_identity_authority=False,

        baggage_agent_id_claim=(
            runtime_input.baggage_agent_id_claim
        ),

        baggage_identity_authority=False,

        action_authority=False,

        semantic_authority=False,

        existing_approved=(
            existing_decision.approved
        ),

        existing_risk_level=(
            existing_decision.risk_level
        ),

        existing_reason=(
            existing_decision.reason
        ),

        shadow_recommendation=(
            recommendation
        ),

        shadow_pipeline_status=(
            "observed"
        ),

        enforcement_effect=False,
    )


# ==============================================================================
# INSULATION WRAPPER
# ==============================================================================


def run_shadow_insulated(
    runtime_input: RuntimeContextInput,
    existing_decision: ExistingBudgetDecision,
    force_shadow_exception: bool = False,
) -> InsulatedShadowResult:

    """
    Shadow execution is intentionally wrapped.

    Any shadow failure is localized here.

    The existing Budget Guard decision object is returned unchanged.
    """

    try:

        if force_shadow_exception:

            raise RuntimeError(
                "controlled_shadow_pipeline_exception"
            )

        observation = (
            observe_runtime_context(
                runtime_input,
                existing_decision,
            )
        )

        return InsulatedShadowResult(
            existing_decision=(
                existing_decision
            ),

            shadow_observation=(
                observation
            ),

            shadow_exception_observed=False,

            shadow_error_type=None,

            shadow_error_message=None,

            existing_decision_preserved=True,
        )

    except Exception as exc:

        return InsulatedShadowResult(
            existing_decision=(
                existing_decision
            ),

            shadow_observation=None,

            shadow_exception_observed=True,

            shadow_error_type=(
                type(exc).__name__
            ),

            shadow_error_message=(
                str(exc)
            ),

            existing_decision_preserved=True,
        )


# ==============================================================================
# DECISION ATTEMPT CELL ADAPTER
# ==============================================================================


def observation_to_cell(
    observation: RuntimeContextObservation,
) -> DecisionAttemptCell:

    actionable_slack = []

    if (
        observation.shadow_recommendation
        ==
        "insufficient_evidence"
    ):

        actionable_slack.extend([
            "declared_action_type",
            "recommendation:insufficient_evidence",
        ])

    elif (
        observation.shadow_recommendation
        ==
        "review_signal"
    ):

        actionable_slack.extend([
            "execution_context_review",
            "recommendation:review_signal",
        ])

    known_structural_slack = (
        "external_risk_authority",
        "real_action_authority",
        "semantic_fact_authority",
        "real_agent_identity_authority",
        "real_network_trust_authority",
    )

    if actionable_slack:

        cell_status = (
            "review"
        )

    else:

        cell_status = (
            "complete"
        )

    return DecisionAttemptCell(
        decision_attempt_id=(
            observation.decision_attempt_id
        ),

        request_id=(
            observation.request_id
        ),

        agent_id=(
            observation.agent_id
        ),

        api_url=(
            observation.api_url
        ),

        decision_id=(
            observation.decision_id
        ),

        existing_decision_observed=True,

        shadow_observation_observed=True,

        shadow_error_observed=False,

        approved=(
            observation.existing_approved
        ),

        risk_level=(
            observation.existing_risk_level
        ),

        shadow_recommendation=(
            observation.shadow_recommendation
        ),

        shadow_reason=(
            observation.boundary_disposition
        ),

        structural_status=(
            "runtime_context_observed"
        ),

        known_structural_slack=(
            known_structural_slack
        ),

        actionable_slack=tuple(
            actionable_slack
        ),

        package_id=None,

        cell_status=(
            cell_status
        ),
    )


# ==============================================================================
# TEST FIXTURE HELPERS
# ==============================================================================


VALID_TRACEPARENT = (
    "00-"
    "4bf92f3577b34da6a3ce929d0e0e4736"
    "-"
    "00f067aa0ba902b7"
    "-"
    "01"
)

GENERATED_TRACE_A = (
    "11111111111111111111111111111111"
)

GENERATED_TRACE_B = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)

GENERATED_SPAN_A = (
    "2222222222222222"
)

GENERATED_SPAN_B = (
    "bbbbbbbbbbbbbbbb"
)


def make_runtime_input(
    *,
    request_id: str,
    decision_id: str,
    boundary_class: str,
    caller_label: str,
    traceparent: Optional[str] = VALID_TRACEPARENT,
    declared_action_type: Optional[str] = "x402_payment",
    baggage_present: bool = False,
    baggage_agent_id_claim: Optional[str] = None,
    generated_trace_id: str = GENERATED_TRACE_A,
    generated_span_id: str = GENERATED_SPAN_A,
) -> RuntimeContextInput:

    return RuntimeContextInput(
        request_id=(
            request_id
        ),

        decision_id=(
            decision_id
        ),

        agent_id=(
            "test-agent"
        ),

        api_url=(
            "https://example.com/paid"
        ),

        declared_action_type=(
            declared_action_type
        ),

        caller_label=(
            caller_label
        ),

        incoming_traceparent=(
            traceparent
        ),

        tracestate_present=True,

        baggage_present=(
            baggage_present
        ),

        baggage_agent_id_claim=(
            baggage_agent_id_claim
        ),

        boundary_class=(
            boundary_class
        ),

        boundary_classification_source=(
            "controlled_fixture"
        ),

        generated_trace_id=(
            generated_trace_id
        ),

        generated_span_id=(
            generated_span_id
        ),
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
        "SHADOW RUNTIME CONTEXT ADAPTER V0.1 "
        "- CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    existing_allow = (
        ExistingBudgetDecision(
            approved=True,
            risk_level="low",
            reason="within_budget",
        )
    )

    # ------------------------------------------------------------------
    # T01
    # External valid trace -> restart.
    # ------------------------------------------------------------------

    external = observe_runtime_context(
        make_runtime_input(
            request_id="req-external",
            decision_id="decision-external",
            boundary_class=(
                BOUNDARY_EXTERNAL
            ),
            caller_label="caller-A",
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T02
    # Internal valid trace -> preserve.
    # ------------------------------------------------------------------

    internal = observe_runtime_context(
        make_runtime_input(
            request_id="req-internal",
            decision_id="decision-internal",
            boundary_class=(
                BOUNDARY_INTERNAL
            ),
            caller_label="caller-internal",
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T03
    # Invalid incoming trace -> new local trace.
    # ------------------------------------------------------------------

    invalid = observe_runtime_context(
        make_runtime_input(
            request_id="req-invalid",
            decision_id="decision-invalid",
            boundary_class=(
                BOUNDARY_INTERNAL
            ),
            caller_label="caller-invalid",
            traceparent=(
                "invalid-traceparent"
            ),
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T04
    # Unknown boundary -> conservative restart.
    # ------------------------------------------------------------------

    unknown = observe_runtime_context(
        make_runtime_input(
            request_id="req-unknown",
            decision_id="decision-unknown",
            boundary_class=(
                BOUNDARY_UNKNOWN
            ),
            caller_label="caller-unknown",
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T06 / T12
    # Baggage contains an agent_id-like claim.
    # ------------------------------------------------------------------

    baggage = observe_runtime_context(
        make_runtime_input(
            request_id="req-baggage",
            decision_id="decision-baggage",
            boundary_class=(
                BOUNDARY_EXTERNAL
            ),
            caller_label="caller-baggage",
            baggage_present=True,
            baggage_agent_id_claim=(
                "privileged-agent"
            ),
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T07
    # Invalid generated execution context.
    # Boundary cannot establish effective execution context.
    # ------------------------------------------------------------------

    invalid_execution = observe_runtime_context(
        make_runtime_input(
            request_id="req-execution-failure",
            decision_id="decision-execution-failure",
            boundary_class=(
                BOUNDARY_EXTERNAL
            ),
            caller_label="caller-execution-failure",
            generated_trace_id="invalid",
            generated_span_id="invalid",
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T11
    # Same incoming trace ID, different fixture caller labels.
    #
    # IMPORTANT:
    # caller-A / caller-B are OBSERVATION LABELS ONLY.
    # They are NOT authenticated caller identities.
    # ------------------------------------------------------------------

    caller_a = observe_runtime_context(
        make_runtime_input(
            request_id="req-caller-A",
            decision_id="decision-caller-A",
            boundary_class=(
                BOUNDARY_EXTERNAL
            ),
            caller_label="caller-A",
            generated_trace_id=(
                GENERATED_TRACE_A
            ),
            generated_span_id=(
                GENERATED_SPAN_A
            ),
        ),
        existing_allow,
    )

    caller_b = observe_runtime_context(
        make_runtime_input(
            request_id="req-caller-B",
            decision_id="decision-caller-B",
            boundary_class=(
                BOUNDARY_EXTERNAL
            ),
            caller_label="caller-B",
            generated_trace_id=(
                GENERATED_TRACE_B
            ),
            generated_span_id=(
                GENERATED_SPAN_B
            ),
        ),
        existing_allow,
    )

    # ------------------------------------------------------------------
    # T15
    # Boundary/execution failure still preserves existing decision.
    # ------------------------------------------------------------------

    invalid_execution_insulated = (
        run_shadow_insulated(
            make_runtime_input(
                request_id="req-insulated-invalid",
                decision_id="decision-insulated-invalid",
                boundary_class=(
                    BOUNDARY_EXTERNAL
                ),
                caller_label="caller-insulated",
                generated_trace_id="invalid",
                generated_span_id="invalid",
            ),
            existing_allow,
        )
    )

    # ------------------------------------------------------------------
    # T16
    # Forced unhandled shadow pipeline exception.
    # ------------------------------------------------------------------

    forced_exception = (
        run_shadow_insulated(
            make_runtime_input(
                request_id="req-forced-exception",
                decision_id="decision-forced-exception",
                boundary_class=(
                    BOUNDARY_EXTERNAL
                ),
                caller_label="caller-forced-exception",
            ),
            existing_allow,
            force_shadow_exception=True,
        )
    )

    tests = []

    tests.append(
        (
            "T01_EXTERNAL_VALID_TRACE_RESTARTED",
            (
                external.trace_restarted
                is True
                and
                external.trace_preserved
                is False
                and
                external.effective_trace_id
                ==
                GENERATED_TRACE_A
            ),
        )
    )

    tests.append(
        (
            "T02_INTERNAL_VALID_TRACE_PRESERVED",
            (
                internal.trace_preserved
                is True
                and
                internal.trace_restarted
                is False
                and
                internal.incoming_trace_id
                ==
                internal.effective_trace_id
            ),
        )
    )

    tests.append(
        (
            "T03_INVALID_TRACE_STARTS_NEW_LOCAL_TRACE",
            (
                invalid.new_trace_created
                is True
                and
                invalid.effective_trace_id
                ==
                GENERATED_TRACE_A
            ),
        )
    )

    tests.append(
        (
            "T04_UNKNOWN_BOUNDARY_RESTARTS_CONSERVATIVELY",
            (
                unknown.trace_restarted
                is True
                and
                unknown.trace_preserved
                is False
            ),
        )
    )

    tests.append(
        (
            "T05_TRACE_POLICY_DOES_NOT_CHANGE_EXISTING_APPROVED",
            (
                external.existing_approved
                is True
                and
                internal.existing_approved
                is True
                and
                invalid.existing_approved
                is True
                and
                unknown.existing_approved
                is True
            ),
        )
    )

    tests.append(
        (
            "T06_BAGGAGE_DOES_NOT_CHANGE_BUDGET_DECISION",
            (
                baggage.existing_approved
                is True
                and
                baggage.enforcement_effect
                is False
            ),
        )
    )

    tests.append(
        (
            "T07_EXECUTION_CONTEXT_FAILURE_LOCALIZED_TO_SHADOW",
            (
                invalid_execution.shadow_recommendation
                ==
                "review_signal"
                and
                invalid_execution.existing_approved
                is True
                and
                invalid_execution.enforcement_effect
                is False
            ),
        )
    )

    tests.append(
        (
            "T08_REQUEST_ID_REMAINS_DECISION_ATTEMPT_ID",
            (
                external.request_id
                ==
                external.decision_attempt_id
            ),
        )
    )

    tests.append(
        (
            "T08A_RESTART_DOES_NOT_REPLACE_DECISION_ATTEMPT_ID",
            (
                external.trace_restarted
                is True
                and
                external.decision_attempt_id
                ==
                external.request_id
                and
                external.decision_attempt_id
                !=
                external.effective_trace_id
            ),
        )
    )

    tests.append(
        (
            "T09_EFFECTIVE_TRACE_ID_NOT_AGENT_IDENTITY_AUTHORITY",
            (
                external.effective_trace_id
                is not None
                and
                external.agent_identity_authority
                is False
                and
                external.authenticated_trace_source
                is False
            ),
        )
    )

    # ------------------------------------------------------------------
    # T10
    # Adapter output -> Decision Attempt Cell.
    # ------------------------------------------------------------------

    cell = observation_to_cell(
        external
    )

    tests.append(
        (
            "T10_ADAPTER_OUTPUT_CONVERTS_TO_DECISION_ATTEMPT_CELL",
            (
                isinstance(
                    cell,
                    DecisionAttemptCell,
                )
                and
                cell.decision_attempt_id
                ==
                external.request_id
                and
                cell.existing_decision_observed
                is True
            ),
        )
    )

    # ------------------------------------------------------------------
    # T11
    #
    # Same incoming trace from differently labelled observations
    # must NOT merge caller identity.
    #
    # This does NOT prove the callers are really distinct.
    # ------------------------------------------------------------------

    tests.append(
        (
            "T11_SAME_INCOMING_TRACE_DOES_NOT_MERGE_CALLER_IDENTITY",
            (
                caller_a.incoming_trace_id
                ==
                caller_b.incoming_trace_id
                and
                caller_a.caller_label
                !=
                caller_b.caller_label
                and
                caller_a.caller_identity_authority
                is False
                and
                caller_b.caller_identity_authority
                is False
                and
                caller_a.decision_attempt_id
                !=
                caller_b.decision_attempt_id
            ),
        )
    )

    tests.append(
        (
            "T12_BAGGAGE_AGENT_ID_NOT_AUTHENTICATED_AGENT",
            (
                baggage.baggage_agent_id_claim
                ==
                "privileged-agent"
                and
                baggage.baggage_identity_authority
                is False
                and
                baggage.agent_identity_authority
                is False
            ),
        )
    )

    tests.append(
        (
            "T13_INTERNAL_CONFIGURED_NOT_NETWORK_TRUST_AUTHORITY",
            (
                internal.boundary_class
                ==
                BOUNDARY_INTERNAL
                and
                internal.network_trust_authority
                is False
                and
                internal.authenticated_trace_source
                is False
            ),
        )
    )

    tests.append(
        (
            "T14_RESTART_PRESERVES_INCOMING_VS_EFFECTIVE_TRACE_DISTINCTION",
            (
                external.trace_restarted
                is True
                and
                external.incoming_trace_id
                is not None
                and
                external.effective_trace_id
                is not None
                and
                external.incoming_trace_id
                !=
                external.effective_trace_id
            ),
        )
    )

    tests.append(
        (
            "T15_TRACE_BOUNDARY_FAILURE_DOES_NOT_CHANGE_EXISTING_DECISION",
            (
                invalid_execution_insulated.existing_decision_preserved
                is True
                and
                invalid_execution_insulated.existing_decision
                ==
                existing_allow
                and
                invalid_execution_insulated.existing_decision.approved
                is True
            ),
        )
    )

    tests.append(
        (
            "T16_UNHANDLED_SHADOW_PIPELINE_EXCEPTION_IS_INSULATED",
            (
                forced_exception.shadow_exception_observed
                is True
                and
                forced_exception.shadow_error_type
                ==
                "RuntimeError"
                and
                forced_exception.existing_decision_preserved
                is True
                and
                forced_exception.existing_decision
                ==
                existing_allow
                and
                forced_exception.existing_decision.approved
                is True
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
        "EXTERNAL RESTART OBSERVATION"
    )

    print_json(
        external
    )

    print()

    print(
        "INTERNAL PRESERVE OBSERVATION"
    )

    print_json(
        internal
    )

    print()

    print(
        "BAGGAGE CLAIM OBSERVATION"
    )

    print_json(
        baggage
    )

    print()

    print(
        "EXECUTION CONTEXT FAILURE OBSERVATION"
    )

    print_json(
        invalid_execution
    )

    print()

    print(
        "FORCED PIPELINE EXCEPTION INSULATION"
    )

    print_json(
        forced_exception
    )

    print()

    print(
        "DECISION ATTEMPT CELL"
    )

    print_json(
        cell
    )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "DECISION_ATTEMPT_IDENTITY != EXECUTION_TRACE_IDENTITY"
    )

    print(
        "TRACE_CONTINUITY != CALLER_IDENTITY"
    )

    print(
        "SAME_TRACE != SAME_PRINCIPAL"
    )

    print(
        "CALLER_LABEL != AUTHENTICATED_CALLER_IDENTITY"
    )

    print(
        "BAGGAGE_CLAIM != AUTHENTICATED_IDENTITY"
    )

    print(
        "BOUNDARY_RESTART != NEW_DECISION_ATTEMPT"
    )

    print(
        "CONFIGURED_BOUNDARY != NETWORK_TRUST_AUTHORITY"
    )

    print(
        "SHADOW_PIPELINE_FAILURE != EXISTING_DECISION_FAILURE"
    )

    print()

    if passed == len(tests):

        print(
            "SHADOW_RUNTIME_CONTEXT_ADAPTER_V01="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_RUNTIME_CONTEXT_ADAPTER_V01="
            "NOT_ESTABLISHED"
        )

    print(
        "REAL_CALLER_IDENTITY_AUTHORITY="
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
        "REAL_SEMANTIC_AUTHORITY="
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_RUNTIME_CONTEXT_INTEGRATION="
        "NOT_ESTABLISHED"
    )


# ==============================================================================
# MAIN
# ==============================================================================


if __name__ == "__main__":

    run_self_test()