#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow Observer v0.1

Standalone, non-enforcing observation layer.

Design inspiration:
    Tensegrity-like control structure

    Compression / Struts
        = locally fixed observations / identities

    Tension Links
        = explicit bindings between those observations

    Slack
        = missing / NOT_ESTABLISHED evidence

    Structural Stability
        = joint package consistency without changing
          the production allow / deny decision

IMPORTANT:

- This module does NOT alter the existing Budget Guard decision.
- This module does NOT perform payment settlement.
- This module does NOT establish real semantic authority.
- This module does NOT establish real action authority.
- Hashes here are local integrity bindings only.
- This module does NOT claim cryptographic attestation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
import hashlib
import json
import math


SHADOW_VERSION = "0.1"

SUPPORTED_CURRENCIES = {
    "USD",
    "USDC",
    "JPYC",
}


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class ShadowInput:
    request_id: str
    decision_id: str

    agent_id: str

    amount: float
    currency: str

    api_url: str

    declared_action_type: Optional[str]

    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class ExistingDecision:
    approved: bool
    risk_level: str
    reason: str


@dataclass(frozen=True)
class MechanicalEvidence:
    agent_id_status: str
    amount_status: str
    currency_status: str
    api_url_status: str

    overall_status: str


@dataclass(frozen=True)
class ShadowEvidenceStatus:
    mechanical: str

    declared_action: str
    action_authority: str

    semantic_facts: str

    existing_internal_risk: str
    external_risk_authority: str


@dataclass(frozen=True)
class TensegrityStructure:
    """
    Struts:
        rigid/local observations

    Tension links:
        explicit bindings between observations

    This is descriptive controlled structure,
    not a proof of real-world authority.
    """

    struts: Tuple[str, ...]

    tension_links: Tuple[str, ...]

    slack_links: Tuple[str, ...]

    structural_status: str


@dataclass(frozen=True)
class ShadowObservation:
    event_type: str
    shadow_version: str

    enforcement: bool
    shadow_effect_on_existing_decision: bool

    decision_attempt_id: str

    request_id: str
    decision_id: str
    correlation_id: Optional[str]

    input_digest: str
    shadow_package_id: str

    observed_input: Dict[str, Any]

    existing_decision: Dict[str, Any]

    mechanical_evidence: Dict[str, Any]

    shadow_evidence: Dict[str, Any]

    tensegrity_structure: Dict[str, Any]

    shadow_recommendation: str
    shadow_reason: str


# ==============================================================================
# CANONICAL LOCAL DIGEST
# ==============================================================================


def canonical_digest(value: Dict[str, Any]) -> str:
    """
    Deterministic local SHA-256 integrity binding.

    NOT:
        identity authority
        semantic truth
        external attestation
        production trust proof
    """

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


# ==============================================================================
# NORMALIZATION
# ==============================================================================


def normalize_currency(
    currency: str,
) -> str:

    if not isinstance(
        currency,
        str,
    ):
        return "UNKNOWN"

    value = currency.strip().upper()

    return value or "UNKNOWN"


def normalize_optional_string(
    value: Optional[str],
) -> Optional[str]:

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.strip()

    return value or None


# ==============================================================================
# MECHANICAL EVIDENCE
# ==============================================================================


def evaluate_mechanical_evidence(
    shadow_input: ShadowInput,
) -> MechanicalEvidence:

    agent_id_ok = (
        isinstance(
            shadow_input.agent_id,
            str,
        )
        and
        bool(
            shadow_input.agent_id.strip()
        )
    )

    amount_value = shadow_input.amount

    amount_ok = (
        isinstance(
            amount_value,
            (int, float),
        )
        and
        not isinstance(
            amount_value,
            bool,
        )
        and
        math.isfinite(
            float(
                amount_value
            )
        )
        and
        float(
            amount_value
        )
        > 0
    )

    currency_value = normalize_currency(
        shadow_input.currency
    )

    currency_ok = (
        currency_value
        in SUPPORTED_CURRENCIES
    )

    api_url_ok = (
        isinstance(
            shadow_input.api_url,
            str,
        )
        and
        bool(
            shadow_input.api_url.strip()
        )
        and
        shadow_input.api_url.strip()
        != "unknown"
    )

    checks = (
        agent_id_ok,
        amount_ok,
        currency_ok,
        api_url_ok,
    )

    overall_status = (
        "observed"
        if all(checks)
        else "review_required"
    )

    return MechanicalEvidence(
        agent_id_status=(
            "observed"
            if agent_id_ok
            else "invalid_or_missing"
        ),

        amount_status=(
            "observed"
            if amount_ok
            else "invalid_or_missing"
        ),

        currency_status=(
            "observed"
            if currency_ok
            else "unsupported_or_missing"
        ),

        api_url_status=(
            "observed"
            if api_url_ok
            else "missing_or_unknown"
        ),

        overall_status=overall_status,
    )


# ==============================================================================
# TENSEGRITY-LIKE STRUCTURE
# ==============================================================================


def build_tensegrity_structure(
    *,
    shadow_input: ShadowInput,
    mechanical: MechanicalEvidence,
) -> TensegrityStructure:

    struts = (
        "server_request_identity",
        "server_decision_identity",
        "normalized_request_input",
        "existing_budget_decision",
    )

    tension_links = [
        "request_id->decision_attempt_id",
        "decision_attempt_id->input_digest",
        "decision_attempt_id->decision_id",
        "input_digest->shadow_package_id",
        "decision_id->shadow_package_id",
    ]

    slack_links = []

    if (
        mechanical.overall_status
        != "observed"
    ):
        slack_links.append(
            "mechanical_input_integrity"
        )

    declared_action = (
        normalize_optional_string(
            shadow_input.declared_action_type
        )
    )

    if declared_action is None:

        slack_links.append(
            "declared_action_type"
        )

    # These evidence classes are intentionally not invented in v0.1.
    slack_links.extend(
        [
            "real_action_authority",
            "semantic_fact_authority",
            "external_risk_authority",
        ]
    )

    if (
        mechanical.overall_status
        == "observed"
    ):

        structural_status = (
            "partially_tensioned_observation"
        )

    else:

        structural_status = (
            "mechanically_unstable_shadow_observation"
        )

    return TensegrityStructure(
        struts=struts,

        tension_links=tuple(
            tension_links
        ),

        slack_links=tuple(
            slack_links
        ),

        structural_status=structural_status,
    )


# ==============================================================================
# SHADOW OBSERVER
# ==============================================================================


def observe_budget_shadow(
    shadow_input: ShadowInput,
    existing_decision: ExistingDecision,
) -> ShadowObservation:

    """
    Produce an observation only.

    This function has no authority to alter:
        approved
        allow
        deny
        approval_required
        budget state
        transaction state
    """

    request_id = (
        shadow_input.request_id.strip()
        if isinstance(
            shadow_input.request_id,
            str,
        )
        else ""
    )

    decision_id = (
        shadow_input.decision_id.strip()
        if isinstance(
            shadow_input.decision_id,
            str,
        )
        else ""
    )

    # For v0.1 the server-generated request_id is the
    # root identity for one decision attempt.
    decision_attempt_id = request_id

    normalized_currency = (
        normalize_currency(
            shadow_input.currency
        )
    )

    declared_action = (
        normalize_optional_string(
            shadow_input.declared_action_type
        )
    )

    normalized_input = {
        "agent_id": shadow_input.agent_id,
        "amount": shadow_input.amount,
        "currency": normalized_currency,
        "api_url": shadow_input.api_url,
        "declared_action_type": declared_action,
    }

    input_digest = canonical_digest(
        normalized_input
    )

    # correlation_id is intentionally excluded.
    #
    # It is caller-provided and must not define
    # decision-attempt or package identity.
    package_material = {
        "shadow_version": SHADOW_VERSION,
        "decision_attempt_id": decision_attempt_id,
        "decision_id": decision_id,
        "input_digest": input_digest,
    }

    shadow_package_id = canonical_digest(
        package_material
    )

    mechanical = (
        evaluate_mechanical_evidence(
            shadow_input
        )
    )

    action_status = (
        "declared"
        if declared_action is not None
        else "not_established"
    )

    evidence_status = ShadowEvidenceStatus(
        mechanical=(
            mechanical.overall_status
        ),

        declared_action=action_status,

        # No real independent action evidence exists in v0.1.
        action_authority="not_established",

        # Do not infer recipient / goal / asset classifications.
        semantic_facts="not_established",

        # Existing BudgetEngine risk is real local runtime output,
        # but it is not equivalent to an externally grounded
        # independent RiskAssessment authority.
        existing_internal_risk="observed",

        external_risk_authority="not_established",
    )

    structure = build_tensegrity_structure(
        shadow_input=shadow_input,
        mechanical=mechanical,
    )

    if (
        not request_id
        or
        not decision_id
    ):

        recommendation = (
            "review_signal"
        )

        reason = (
            "decision_attempt_identity_incomplete"
        )

    elif (
        mechanical.overall_status
        != "observed"
    ):

        recommendation = (
            "review_signal"
        )

        reason = (
            "mechanical_input_requires_review"
        )

    elif declared_action is None:

        recommendation = (
            "insufficient_evidence"
        )

        reason = (
            "declared_action_type_not_established"
        )

    else:

        recommendation = (
            "observe_only"
        )

        reason = (
            "shadow_observation_recorded"
        )

    return ShadowObservation(
        event_type=(
            "budget_shadow_observation"
        ),

        shadow_version=(
            SHADOW_VERSION
        ),

        enforcement=False,

        shadow_effect_on_existing_decision=False,

        decision_attempt_id=(
            decision_attempt_id
        ),

        request_id=request_id,

        decision_id=decision_id,

        correlation_id=(
            shadow_input.correlation_id
        ),

        input_digest=input_digest,

        shadow_package_id=(
            shadow_package_id
        ),

        observed_input=(
            normalized_input
        ),

        existing_decision=asdict(
            existing_decision
        ),

        mechanical_evidence=asdict(
            mechanical
        ),

        shadow_evidence=asdict(
            evidence_status
        ),

        tensegrity_structure=asdict(
            structure
        ),

        shadow_recommendation=(
            recommendation
        ),

        shadow_reason=reason,
    )


# ==============================================================================
# SERIALIZATION
# ==============================================================================


def observation_to_json(
    observation: ShadowObservation,
) -> str:

    return json.dumps(
        asdict(
            observation
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


# ==============================================================================
# CONTROLLED SELF-TEST
# ==============================================================================


def run_self_test():

    print(
        "=" * 80
    )

    print(
        "SHADOW OBSERVER V0.1 - CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    base_input = ShadowInput(
        request_id="req-001",
        decision_id="decision-001",

        agent_id="agent-001",

        amount=0.05,
        currency="USDC",

        api_url=(
            "https://example.com/api/paid"
        ),

        declared_action_type=(
            "x402_payment"
        ),

        correlation_id="series-A",
    )

    base_decision = ExistingDecision(
        approved=True,
        risk_level="low",
        reason="Budget check passed",
    )

    base = observe_budget_shadow(
        base_input,
        base_decision,
    )

    tests = []

    # ------------------------------------------------------------------
    # T01
    # Normal observation.
    # ------------------------------------------------------------------

    tests.append(
        (
            "T01_NORMAL_OBSERVATION",
            (
                base.shadow_recommendation
                == "observe_only"
                and
                base.enforcement
                is False
                and
                base.shadow_effect_on_existing_decision
                is False
            ),
        )
    )

    # ------------------------------------------------------------------
    # T02
    # Caller correlation label must not define package identity.
    # ------------------------------------------------------------------

    changed_correlation = (
        ShadowInput(
            request_id=base_input.request_id,
            decision_id=base_input.decision_id,

            agent_id=base_input.agent_id,

            amount=base_input.amount,
            currency=base_input.currency,

            api_url=base_input.api_url,

            declared_action_type=(
                base_input.declared_action_type
            ),

            correlation_id="series-B",
        )
    )

    correlation_result = (
        observe_budget_shadow(
            changed_correlation,
            base_decision,
        )
    )

    tests.append(
        (
            "T02_CALLER_CORRELATION_NOT_DECISION_IDENTITY",
            (
                correlation_result.shadow_package_id
                ==
                base.shadow_package_id
            ),
        )
    )

    # ------------------------------------------------------------------
    # T03
    # Different server request means a different decision attempt.
    # ------------------------------------------------------------------

    second_attempt_input = (
        ShadowInput(
            request_id="req-002",
            decision_id=base_input.decision_id,

            agent_id=base_input.agent_id,

            amount=base_input.amount,
            currency=base_input.currency,

            api_url=base_input.api_url,

            declared_action_type=(
                base_input.declared_action_type
            ),

            correlation_id=(
                base_input.correlation_id
            ),
        )
    )

    second_attempt = (
        observe_budget_shadow(
            second_attempt_input,
            base_decision,
        )
    )

    tests.append(
        (
            "T03_REQUEST_ID_DEFINES_DECISION_ATTEMPT",
            (
                second_attempt.decision_attempt_id
                !=
                base.decision_attempt_id
                and
                second_attempt.shadow_package_id
                !=
                base.shadow_package_id
            ),
        )
    )

    # ------------------------------------------------------------------
    # T04
    # Same request with different input must alter package binding.
    # ------------------------------------------------------------------

    amount_changed_input = (
        ShadowInput(
            request_id=base_input.request_id,
            decision_id=base_input.decision_id,

            agent_id=base_input.agent_id,

            amount=0.50,
            currency=base_input.currency,

            api_url=base_input.api_url,

            declared_action_type=(
                base_input.declared_action_type
            ),

            correlation_id=(
                base_input.correlation_id
            ),
        )
    )

    amount_changed = (
        observe_budget_shadow(
            amount_changed_input,
            base_decision,
        )
    )

    tests.append(
        (
            "T04_INPUT_CHANGE_ALTERS_PACKAGE_BINDING",
            (
                amount_changed.input_digest
                !=
                base.input_digest
                and
                amount_changed.shadow_package_id
                !=
                base.shadow_package_id
            ),
        )
    )

    # ------------------------------------------------------------------
    # T05
    # Missing action is not invented.
    # ------------------------------------------------------------------

    missing_action_input = (
        ShadowInput(
            request_id="req-003",
            decision_id="decision-003",

            agent_id="agent-003",

            amount=0.05,
            currency="USDC",

            api_url=(
                "https://example.com/api/paid"
            ),

            declared_action_type=None,

            correlation_id=None,
        )
    )

    missing_action = (
        observe_budget_shadow(
            missing_action_input,
            base_decision,
        )
    )

    tests.append(
        (
            "T05_MISSING_ACTION_NOT_FABRICATED",
            (
                missing_action.shadow_evidence[
                    "declared_action"
                ]
                ==
                "not_established"
                and
                missing_action.shadow_recommendation
                ==
                "insufficient_evidence"
            ),
        )
    )

    # ------------------------------------------------------------------
    # T06
    # Invalid mechanical amount generates review signal,
    # but still cannot alter production decision.
    # ------------------------------------------------------------------

    bad_amount_input = (
        ShadowInput(
            request_id="req-004",
            decision_id="decision-004",

            agent_id="agent-004",

            amount=-1.0,
            currency="USDC",

            api_url=(
                "https://example.com/api/paid"
            ),

            declared_action_type=(
                "x402_payment"
            ),

            correlation_id=None,
        )
    )

    bad_amount = (
        observe_budget_shadow(
            bad_amount_input,
            base_decision,
        )
    )

    tests.append(
        (
            "T06_MECHANICAL_FAILURE_LOCALIZED_TO_SHADOW",
            (
                bad_amount.shadow_recommendation
                ==
                "review_signal"
                and
                bad_amount.shadow_effect_on_existing_decision
                is False
            ),
        )
    )

    # ------------------------------------------------------------------
    # T07
    # Unsupported currency also stays local to shadow.
    # ------------------------------------------------------------------

    bad_currency_input = (
        ShadowInput(
            request_id="req-005",
            decision_id="decision-005",

            agent_id="agent-005",

            amount=0.05,
            currency="XYZ",

            api_url=(
                "https://example.com/api/paid"
            ),

            declared_action_type=(
                "x402_payment"
            ),

            correlation_id=None,
        )
    )

    bad_currency = (
        observe_budget_shadow(
            bad_currency_input,
            base_decision,
        )
    )

    tests.append(
        (
            "T07_UNSUPPORTED_CURRENCY_LOCALIZED_TO_SHADOW",
            (
                bad_currency.shadow_recommendation
                ==
                "review_signal"
                and
                bad_currency.shadow_effect_on_existing_decision
                is False
            ),
        )
    )

    # ------------------------------------------------------------------
    # T08
    # Semantic / authority gaps remain explicit.
    # ------------------------------------------------------------------

    tests.append(
        (
            "T08_NOT_ESTABLISHED_EVIDENCE_REMAINS_EXPLICIT",
            (
                base.shadow_evidence[
                    "action_authority"
                ]
                ==
                "not_established"
                and
                base.shadow_evidence[
                    "semantic_facts"
                ]
                ==
                "not_established"
                and
                base.shadow_evidence[
                    "external_risk_authority"
                ]
                ==
                "not_established"
            ),
        )
    )

    # ------------------------------------------------------------------
    # T09
    # Tensegrity structure retains slack rather than pretending
    # to have complete evidence.
    # ------------------------------------------------------------------

    tests.append(
        (
            "T09_TENSEGRITY_SLACK_REPRESENTS_MISSING_AUTHORITY",
            (
                "real_action_authority"
                in
                base.tensegrity_structure[
                    "slack_links"
                ]
                and
                "semantic_fact_authority"
                in
                base.tensegrity_structure[
                    "slack_links"
                ]
                and
                "external_risk_authority"
                in
                base.tensegrity_structure[
                    "slack_links"
                ]
            ),
        )
    )

    # ------------------------------------------------------------------
    # T10
    # Existing decision remains observation-only.
    # ------------------------------------------------------------------

    tests.append(
        (
            "T10_SHADOW_HAS_NO_COMMIT_AUTHORITY",
            (
                base.existing_decision[
                    "approved"
                ]
                is True
                and
                base.enforcement
                is False
                and
                base.shadow_effect_on_existing_decision
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
        "-" * 80
    )

    print(
        f"RESULT: {passed}/{len(tests)}"
    )

    print(
        "-" * 80
    )

    print()

    print(
        "BASE OBSERVATION"
    )

    print(
        observation_to_json(
            base
        )
    )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "LOCAL_FACT != REAL_AUTHORITY"
    )

    print(
        "INDIVIDUAL_BINDING != JOINT_PACKAGE_AUTHORITY"
    )

    print(
        "CALLER_CORRELATION != DECISION_ATTEMPT_IDENTITY"
    )

    print(
        "SHADOW_OBSERVATION != PRODUCTION_ENFORCEMENT"
    )

    print(
        "MISSING_EVIDENCE != PERMISSION_TO_INFER"
    )

    print(
        "TENSEGRITY_SLACK != STRUCTURAL_FAILURE"
    )

    print(
        "LOCAL_SHADOW_FAILURE != EXISTING_DECISION_FAILURE"
    )

    if passed == len(
        tests
    ):

        print(
            "SHADOW_OBSERVER_V01 = "
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_OBSERVER_V01 = "
            "NOT_ESTABLISHED"
        )

    print(
        "REAL_ACTION_AUTHORITY = "
        "NOT_ESTABLISHED"
    )

    print(
        "REAL_SEMANTIC_FACT_AUTHORITY = "
        "NOT_ESTABLISHED"
    )

    print(
        "REAL_EXTERNAL_RISK_AUTHORITY = "
        "NOT_ESTABLISHED"
    )

    print(
        "CRYPTOGRAPHIC_PACKAGE_ATTESTATION = "
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_SHADOW_INTEGRATION = "
        "NOT_ESTABLISHED"
    )


if __name__ == "__main__":
    run_self_test()