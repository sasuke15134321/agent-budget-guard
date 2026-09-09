#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
Shadow Runtime Cell Aggregator v0.1

Purpose
-------
Read JSON-line logs produced by Agent Budget Guard / Shadow Observer,
join events by server-generated request identity, and construct
Decision Attempt Tensegrity Cells.

This module is local analysis only.

It does NOT:
- modify Agent Budget Guard decisions
- call production APIs
- write to PostgreSQL
- modify Render
- establish real action authority
- establish semantic truth
- establish cryptographic attestation

Core distinction
----------------
Known structural slack:
    real_action_authority
    semantic_fact_authority
    external_risk_authority

These are expected NOT_ESTABLISHED fields in Shadow Observer v0.1
and are NOT automatically treated as runtime anomalies.

Actionable observation signals:
    missing shadow event
    shadow observer error
    mechanical review
    insufficient declared action evidence
    decision-attempt identity mismatch
    decision identity mismatch
    repeated review signals
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
import argparse
import json


# ==============================================================================
# CONSTANTS
# ==============================================================================


KNOWN_STRUCTURAL_SLACK = {
    "real_action_authority",
    "semantic_fact_authority",
    "external_risk_authority",
}


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class DecisionAttemptCell:
    decision_attempt_id: str
    request_id: str

    agent_id: Optional[str]
    api_url: Optional[str]

    decision_id: Optional[str]

    existing_decision_observed: bool
    shadow_observation_observed: bool
    shadow_error_observed: bool

    approved: Optional[bool]
    risk_level: Optional[str]

    shadow_recommendation: Optional[str]
    shadow_reason: Optional[str]

    structural_status: Optional[str]

    known_structural_slack: Tuple[str, ...]
    actionable_slack: Tuple[str, ...]

    package_id: Optional[str]

    cell_status: str


@dataclass(frozen=True)
class AggregationSummary:
    total_json_events: int

    decision_events: int
    shadow_events: int
    shadow_error_events: int

    total_cells: int

    complete_cells: int
    review_cells: int
    incomplete_cells: int
    error_cells: int

    recommendations: Dict[str, int]

    actionable_slack_counts: Dict[str, int]

    repeated_review_agents: Dict[str, int]
    repeated_review_api_urls: Dict[str, int]

    duplicate_package_ids: Dict[str, int]


# ==============================================================================
# PARSING
# ==============================================================================


def parse_json_lines(
    lines: Iterable[str],
) -> List[Dict[str, Any]]:

    events: List[Dict[str, Any]] = []

    for raw in lines:

        line = raw.strip()

        if not (
            line.startswith("{")
            and
            line.endswith("}")
        ):
            continue

        try:
            value = json.loads(line)
        except Exception:
            continue

        if isinstance(value, dict):
            events.append(value)

    return events


# ==============================================================================
# IDENTITY
# ==============================================================================


def event_request_id(
    event: Dict[str, Any],
) -> Optional[str]:

    value = event.get("request_id")

    if isinstance(value, str):
        value = value.strip()

        if value:
            return value

    return None


def event_attempt_id(
    event: Dict[str, Any],
) -> Optional[str]:

    value = event.get(
        "decision_attempt_id"
    )

    if isinstance(value, str):
        value = value.strip()

        if value:
            return value

    return event_request_id(event)


# ==============================================================================
# CELL CONSTRUCTION
# ==============================================================================


def build_cells(
    events: List[Dict[str, Any]],
) -> List[DecisionAttemptCell]:

    decision_events: Dict[
        str,
        List[Dict[str, Any]],
    ] = defaultdict(list)

    shadow_events: Dict[
        str,
        List[Dict[str, Any]],
    ] = defaultdict(list)

    shadow_error_events: Dict[
        str,
        List[Dict[str, Any]],
    ] = defaultdict(list)

    all_ids = set()

    for event in events:

        event_type = event.get(
            "event_type"
        )

        request_id = event_request_id(
            event
        )

        attempt_id = event_attempt_id(
            event
        )

        root_id = (
            attempt_id
            or
            request_id
        )

        if not root_id:
            continue

        all_ids.add(root_id)

        if (
            event_type
            ==
            "budget_decision_completed"
        ):
            decision_events[
                root_id
            ].append(event)

        elif (
            event_type
            ==
            "budget_shadow_observation"
        ):
            shadow_events[
                root_id
            ].append(event)

        elif event_type in {
            "budget_shadow_observer_error",
            "budget_shadow_observer_unavailable",
        }:
            shadow_error_events[
                root_id
            ].append(event)

    cells: List[
        DecisionAttemptCell
    ] = []

    for root_id in sorted(all_ids):

        decisions = decision_events.get(
            root_id,
            [],
        )

        shadows = shadow_events.get(
            root_id,
            [],
        )

        errors = shadow_error_events.get(
            root_id,
            [],
        )

        decision = (
            decisions[-1]
            if decisions
            else None
        )

        shadow = (
            shadows[-1]
            if shadows
            else None
        )

        actionable_slack: List[str] = []

        if not decision:
            actionable_slack.append(
                "existing_decision_event_missing"
            )

        if not shadow:
            actionable_slack.append(
                "shadow_observation_missing"
            )

        if errors:
            actionable_slack.append(
                "shadow_observer_error"
            )

        request_id = root_id

        agent_id: Optional[str] = None
        api_url: Optional[str] = None
        decision_id: Optional[str] = None

        approved: Optional[bool] = None
        risk_level: Optional[str] = None

        recommendation: Optional[str] = None
        shadow_reason: Optional[str] = None
        structural_status: Optional[str] = None
        package_id: Optional[str] = None

        known_slack: Tuple[str, ...] = ()

        if decision:

            request_id = (
                event_request_id(
                    decision
                )
                or
                request_id
            )

            agent_id = decision.get(
                "agent_id"
            )

            decision_id = decision.get(
                "decision_id"
            )

            approved = decision.get(
                "approved"
            )

            risk_level = decision.get(
                "risk_level"
            )

        if shadow:

            shadow_request_id = (
                event_request_id(
                    shadow
                )
            )

            shadow_attempt_id = (
                event_attempt_id(
                    shadow
                )
            )

            if (
                shadow_request_id
                and
                shadow_attempt_id
                and
                shadow_request_id
                !=
                shadow_attempt_id
            ):
                actionable_slack.append(
                    "decision_attempt_identity_mismatch"
                )

            if (
                shadow_request_id
                and
                shadow_request_id
                !=
                root_id
            ):
                actionable_slack.append(
                    "request_identity_mismatch"
                )

            shadow_decision_id = (
                shadow.get(
                    "decision_id"
                )
            )

            if (
                decision_id
                and
                shadow_decision_id
                and
                decision_id
                !=
                shadow_decision_id
            ):
                actionable_slack.append(
                    "decision_identity_mismatch"
                )

            observed_input = (
                shadow.get(
                    "observed_input"
                )
                or
                {}
            )

            if isinstance(
                observed_input,
                dict,
            ):

                agent_id = (
                    observed_input.get(
                        "agent_id"
                    )
                    or
                    agent_id
                )

                api_url = (
                    observed_input.get(
                        "api_url"
                    )
                )

            recommendation = (
                shadow.get(
                    "shadow_recommendation"
                )
            )

            shadow_reason = (
                shadow.get(
                    "shadow_reason"
                )
            )

            package_id = shadow.get(
                "shadow_package_id"
            )

            structure = (
                shadow.get(
                    "tensegrity_structure"
                )
                or
                {}
            )

            if isinstance(
                structure,
                dict,
            ):

                structural_status = (
                    structure.get(
                        "structural_status"
                    )
                )

                raw_slack = (
                    structure.get(
                        "slack_links"
                    )
                    or
                    []
                )

                if isinstance(
                    raw_slack,
                    list,
                ):

                    known_slack = tuple(
                        sorted(
                            item
                            for item
                            in raw_slack
                            if item
                            in
                            KNOWN_STRUCTURAL_SLACK
                        )
                    )

                    for item in raw_slack:

                        if (
                            isinstance(
                                item,
                                str,
                            )
                            and
                            item
                            not in
                            KNOWN_STRUCTURAL_SLACK
                        ):
                            actionable_slack.append(
                                item
                            )

            mechanical = (
                shadow.get(
                    "mechanical_evidence"
                )
                or
                {}
            )

            if isinstance(
                mechanical,
                dict,
            ):

                if (
                    mechanical.get(
                        "overall_status"
                    )
                    ==
                    "review_required"
                ):
                    actionable_slack.append(
                        "mechanical_review_required"
                    )

            if recommendation in {
                "review_signal",
                "insufficient_evidence",
            }:
                actionable_slack.append(
                    f"recommendation:{recommendation}"
                )

        actionable_slack = sorted(
            set(
                actionable_slack
            )
        )

        if errors:

            cell_status = "error"

        elif not decision or not shadow:

            cell_status = "incomplete"

        elif actionable_slack:

            cell_status = "review"

        else:

            cell_status = "complete"

        cells.append(
            DecisionAttemptCell(
                decision_attempt_id=root_id,

                request_id=request_id,

                agent_id=agent_id,
                api_url=api_url,

                decision_id=decision_id,

                existing_decision_observed=(
                    bool(decision)
                ),

                shadow_observation_observed=(
                    bool(shadow)
                ),

                shadow_error_observed=(
                    bool(errors)
                ),

                approved=approved,
                risk_level=risk_level,

                shadow_recommendation=(
                    recommendation
                ),

                shadow_reason=(
                    shadow_reason
                ),

                structural_status=(
                    structural_status
                ),

                known_structural_slack=(
                    known_slack
                ),

                actionable_slack=tuple(
                    actionable_slack
                ),

                package_id=package_id,

                cell_status=cell_status,
            )
        )

    return cells


# ==============================================================================
# AGGREGATION
# ==============================================================================


def aggregate(
    events: List[Dict[str, Any]],
    cells: List[DecisionAttemptCell],
) -> AggregationSummary:

    event_types = Counter(
        event.get(
            "event_type"
        )
        for event in events
    )

    cell_statuses = Counter(
        cell.cell_status
        for cell in cells
    )

    recommendations = Counter(
        cell.shadow_recommendation
        for cell in cells
        if cell.shadow_recommendation
    )

    slack_counts = Counter()

    for cell in cells:

        for item in (
            cell.actionable_slack
        ):
            slack_counts[
                item
            ] += 1

    review_agent_counts = Counter()

    review_api_counts = Counter()

    package_counts = Counter(
        cell.package_id
        for cell in cells
        if cell.package_id
    )

    for cell in cells:

        if cell.cell_status not in {
            "review",
            "error",
            "incomplete",
        }:
            continue

        if cell.agent_id:
            review_agent_counts[
                cell.agent_id
            ] += 1

        if (
            cell.api_url
            and
            cell.api_url
            !=
            "unknown"
        ):
            review_api_counts[
                cell.api_url
            ] += 1

    repeated_review_agents = {
        key: count
        for key, count
        in review_agent_counts.items()
        if count >= 2
    }

    repeated_review_api_urls = {
        key: count
        for key, count
        in review_api_counts.items()
        if count >= 2
    }

    duplicate_package_ids = {
        key: count
        for key, count
        in package_counts.items()
        if count >= 2
    }

    return AggregationSummary(
        total_json_events=len(events),

        decision_events=event_types[
            "budget_decision_completed"
        ],

        shadow_events=event_types[
            "budget_shadow_observation"
        ],

        shadow_error_events=(
            event_types[
                "budget_shadow_observer_error"
            ]
            +
            event_types[
                "budget_shadow_observer_unavailable"
            ]
        ),

        total_cells=len(cells),

        complete_cells=cell_statuses[
            "complete"
        ],

        review_cells=cell_statuses[
            "review"
        ],

        incomplete_cells=cell_statuses[
            "incomplete"
        ],

        error_cells=cell_statuses[
            "error"
        ],

        recommendations=dict(
            sorted(
                recommendations.items()
            )
        ),

        actionable_slack_counts=dict(
            sorted(
                slack_counts.items()
            )
        ),

        repeated_review_agents=dict(
            sorted(
                repeated_review_agents.items()
            )
        ),

        repeated_review_api_urls=dict(
            sorted(
                repeated_review_api_urls.items()
            )
        ),

        duplicate_package_ids=dict(
            sorted(
                duplicate_package_ids.items()
            )
        ),
    )


# ==============================================================================
# OUTPUT
# ==============================================================================


def print_report(
    events: List[Dict[str, Any]],
    cells: List[DecisionAttemptCell],
) -> None:

    summary = aggregate(
        events,
        cells,
    )

    print(
        "=" * 80
    )

    print(
        "SHADOW RUNTIME CELL AGGREGATOR V0.1"
    )

    print(
        "=" * 80
    )

    print()

    print(
        "L1 OVERVIEW"
    )

    print(
        json.dumps(
            asdict(summary),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    print()

    print(
        "L2 REVIEW CANDIDATES"
    )

    review_cells = [
        cell
        for cell in cells
        if cell.cell_status
        !=
        "complete"
    ]

    if not review_cells:

        print(
            "NONE"
        )

    else:

        for cell in review_cells:

            print(
                json.dumps(
                    asdict(cell),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

    print()

    print(
        "INTERPRETATION"
    )

    print(
        "KNOWN_STRUCTURAL_SLACK != RUNTIME_ANOMALY"
    )

    print(
        "SINGLE_REVIEW != REPEATED_REVIEW_PATTERN"
    )

    print(
        "DECISION_ATTEMPT_IDENTITY != CALLER_CORRELATION"
    )

    print(
        "DUPLICATE_PACKAGE_ID != AUTOMATIC_PROOF_OF_REPLAY"
    )

    print(
        "L1_OVERVIEW != L2_DIAGNOSIS"
    )

    print(
        "SHADOW_OBSERVATION != PRODUCTION_ENFORCEMENT"
    )


# ==============================================================================
# CONTROLLED SELF-TEST
# ==============================================================================


def fixture_events() -> List[
    Dict[str, Any]
]:

    base_slack = [
        "real_action_authority",
        "semantic_fact_authority",
        "external_risk_authority",
    ]

    events = [

        # --------------------------------------------------------------
        # Attempt A: normal complete cell.
        # --------------------------------------------------------------

        {
            "event_type":
                "budget_decision_completed",

            "request_id":
                "req-A",

            "decision_id":
                "decision-A",

            "agent_id":
                "agent-normal",

            "approved":
                True,

            "risk_level":
                "low",
        },

        {
            "event_type":
                "budget_shadow_observation",

            "request_id":
                "req-A",

            "decision_attempt_id":
                "req-A",

            "decision_id":
                "decision-A",

            "shadow_package_id":
                "package-A",

            "observed_input": {
                "agent_id":
                    "agent-normal",

                "api_url":
                    "https://example.com/paid",

                "declared_action_type":
                    "x402_payment",
            },

            "mechanical_evidence": {
                "overall_status":
                    "observed",
            },

            "tensegrity_structure": {
                "structural_status":
                    "partially_tensioned_observation",

                "slack_links":
                    base_slack,
            },

            "shadow_recommendation":
                "observe_only",

            "shadow_reason":
                "shadow_observation_recorded",
        },

        # --------------------------------------------------------------
        # Attempt B/C:
        # same agent repeatedly omits action.
        # --------------------------------------------------------------

        {
            "event_type":
                "budget_decision_completed",

            "request_id":
                "req-B",

            "decision_id":
                "decision-B",

            "agent_id":
                "agent-repeat",

            "approved":
                True,

            "risk_level":
                "low",
        },

        {
            "event_type":
                "budget_shadow_observation",

            "request_id":
                "req-B",

            "decision_attempt_id":
                "req-B",

            "decision_id":
                "decision-B",

            "shadow_package_id":
                "package-B",

            "observed_input": {
                "agent_id":
                    "agent-repeat",

                "api_url":
                    "https://example.com/paid",

                "declared_action_type":
                    None,
            },

            "mechanical_evidence": {
                "overall_status":
                    "observed",
            },

            "tensegrity_structure": {
                "structural_status":
                    "partially_tensioned_observation",

                "slack_links":
                    base_slack
                    +
                    [
                        "declared_action_type"
                    ],
            },

            "shadow_recommendation":
                "insufficient_evidence",

            "shadow_reason":
                "declared_action_type_not_established",
        },

        {
            "event_type":
                "budget_decision_completed",

            "request_id":
                "req-C",

            "decision_id":
                "decision-C",

            "agent_id":
                "agent-repeat",

            "approved":
                True,

            "risk_level":
                "low",
        },

        {
            "event_type":
                "budget_shadow_observation",

            "request_id":
                "req-C",

            "decision_attempt_id":
                "req-C",

            "decision_id":
                "decision-C",

            "shadow_package_id":
                "package-C",

            "observed_input": {
                "agent_id":
                    "agent-repeat",

                "api_url":
                    "https://example.com/paid",

                "declared_action_type":
                    None,
            },

            "mechanical_evidence": {
                "overall_status":
                    "observed",
            },

            "tensegrity_structure": {
                "structural_status":
                    "partially_tensioned_observation",

                "slack_links":
                    base_slack
                    +
                    [
                        "declared_action_type"
                    ],
            },

            "shadow_recommendation":
                "insufficient_evidence",

            "shadow_reason":
                "declared_action_type_not_established",
        },

        # --------------------------------------------------------------
        # Attempt D:
        # decision exists but shadow event is missing.
        # --------------------------------------------------------------

        {
            "event_type":
                "budget_decision_completed",

            "request_id":
                "req-D",

            "decision_id":
                "decision-D",

            "agent_id":
                "agent-missing-shadow",

            "approved":
                False,

            "risk_level":
                "high",
        },

        # --------------------------------------------------------------
        # Attempt E:
        # explicit shadow observer error.
        # --------------------------------------------------------------

        {
            "event_type":
                "budget_decision_completed",

            "request_id":
                "req-E",

            "decision_id":
                "decision-E",

            "agent_id":
                "agent-shadow-error",

            "approved":
                True,

            "risk_level":
                "low",
        },

        {
            "event_type":
                "budget_shadow_observer_error",

            "request_id":
                "req-E",

            "decision_attempt_id":
                "req-E",

            "decision_id":
                "decision-E",

            "error_type":
                "FixtureError",

            "error":
                "controlled fixture",
        },
    ]

    return events


def run_self_test() -> None:

    print(
        "=" * 80
    )

    print(
        "SHADOW RUNTIME CELL AGGREGATOR "
        "V0.1 - CONTROLLED SELF TEST"
    )

    print(
        "=" * 80
    )

    events = fixture_events()

    cells = build_cells(
        events
    )

    summary = aggregate(
        events,
        cells,
    )

    tests = []

    tests.append(
        (
            "T01_FIVE_DECISION_ATTEMPT_CELLS",
            summary.total_cells
            ==
            5,
        )
    )

    tests.append(
        (
            "T02_NORMAL_CELL_COMPLETE",
            any(
                cell.decision_attempt_id
                ==
                "req-A"
                and
                cell.cell_status
                ==
                "complete"
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T03_KNOWN_STRUCTURAL_SLACK_NOT_ANOMALY",
            any(
                cell.decision_attempt_id
                ==
                "req-A"
                and
                len(
                    cell.known_structural_slack
                )
                ==
                3
                and
                not
                cell.actionable_slack
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T04_MISSING_ACTION_BECOMES_REVIEW",
            any(
                cell.decision_attempt_id
                ==
                "req-B"
                and
                cell.cell_status
                ==
                "review"
                and
                "declared_action_type"
                in
                cell.actionable_slack
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T05_REPEATED_REVIEW_AGENT_DETECTED",
            summary.repeated_review_agents.get(
                "agent-repeat"
            )
            ==
            2,
        )
    )

    tests.append(
        (
            "T06_MISSING_SHADOW_EVENT_DETECTED",
            any(
                cell.decision_attempt_id
                ==
                "req-D"
                and
                "shadow_observation_missing"
                in
                cell.actionable_slack
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T07_SHADOW_ERROR_LOCALIZED",
            any(
                cell.decision_attempt_id
                ==
                "req-E"
                and
                cell.cell_status
                ==
                "error"
                and
                cell.approved
                is True
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T08_EXISTING_DECISION_PRESERVED_IN_ERROR_CELL",
            any(
                cell.decision_attempt_id
                ==
                "req-E"
                and
                cell.existing_decision_observed
                is True
                and
                cell.shadow_error_observed
                is True
                for cell in cells
            ),
        )
    )

    tests.append(
        (
            "T09_NO_DUPLICATE_PACKAGE_IN_FIXTURE",
            summary.duplicate_package_ids
            ==
            {},
        )
    )

    tests.append(
        (
            "T10_L1_L2_SEPARATION_PRESENT",
            (
                summary.complete_cells
                ==
                1
                and
                (
                    summary.review_cells
                    +
                    summary.incomplete_cells
                    +
                    summary.error_cells
                )
                ==
                4
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

    print_report(
        events,
        cells,
    )

    print()

    if passed == len(tests):

        print(
            "SHADOW_RUNTIME_CELL_AGGREGATOR_V01="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

    else:

        print(
            "SHADOW_RUNTIME_CELL_AGGREGATOR_V01="
            "NOT_ESTABLISHED"
        )

    print(
        "REAL_RENDER_LOG_OBSERVATION="
        "NOT_ESTABLISHED"
    )

    print(
        "REAL_RUNTIME_PATTERN="
        "NOT_ESTABLISHED"
    )

    print(
        "PRODUCTION_ENFORCEMENT="
        "NOT_ESTABLISHED"
    )


# ==============================================================================
# CLI
# ==============================================================================


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Aggregate Agent Budget Guard "
            "shadow JSON-line logs into "
            "Decision Attempt Tensegrity Cells."
        )
    )

    parser.add_argument(
        "log_file",
        nargs="?",
        help=(
            "Optional JSON-line log file. "
            "If omitted, controlled self-test runs."
        ),
    )

    args = parser.parse_args()

    if not args.log_file:

        run_self_test()
        return

    with open(
        args.log_file,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as f:

        events = parse_json_lines(
            f
        )

    cells = build_cells(
        events
    )

    print_report(
        events,
        cells,
    )


if __name__ == "__main__":
    main()