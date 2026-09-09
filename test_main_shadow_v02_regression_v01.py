#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Budget Guard
main_shadow_v02 regression v0.1

Goal
----
Compare frozen main_shadow_v01 and main_shadow_v02 under identical
controlled BudgetEngine / DB behavior.

Verify:
- Existing Budget response remains unchanged.
- HTTP propagation context affects shadow observation only.
- Caller trace/baggage does not become Budget authority.
- Runtime shadow failure remains insulated.
- Invalid/unsupported inputs retain existing behavior.

This test does NOT:
- modify main.py
- use production DB
- make network calls
- push GitHub
- deploy Render
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
from typing import Any, Dict, List, Tuple

from fastapi.responses import JSONResponse
from starlette.requests import Request

import main_shadow_v01 as v01
import main_shadow_v02 as v02


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


# ==============================================================================
# CONTROLLED FAKES
# ==============================================================================


class FakeBudgetEngine:

    def __init__(
        self,
        *,
        approved: bool,
        risk_level: str,
        reason: str,
    ):

        self.approved = approved
        self.risk_level = risk_level
        self.reason = reason

    async def check_budget(
        self,
        *,
        agent_id,
        api_url,
        amount_usdc,
        category,
        daily_limit,
    ):

        remaining = max(
            float(daily_limit or 0.0)
            -
            float(amount_usdc or 0.0),
            0.0,
        )

        return {
            "approved": self.approved,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "current_daily_spend": 0.0,
            "remaining_budget": remaining,
            "warnings": [],
        }


class FakeBudgetDB:

    def __init__(self):

        self.calls = []

    async def log_budget_check(
        self,
        *,
        agent_id,
        api_url,
        amount_usdc,
        approved,
        reason,
    ):

        self.calls.append(
            {
                "agent_id": agent_id,
                "api_url": api_url,
                "amount_usdc": amount_usdc,
                "approved": approved,
                "reason": reason,
            }
        )


# ==============================================================================
# REQUEST / RESPONSE HELPERS
# ==============================================================================


def raw_headers(
    values: List[
        Tuple[
            str,
            str,
        ]
    ],
):

    return [
        (
            name.lower().encode("ascii"),
            value.encode("latin-1"),
        )
        for name, value in values
    ]


def make_request(
    *,
    request_id: str,
    headers: List[
        Tuple[
            str,
            str,
        ]
    ],
) -> Request:

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
        },
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/budget/check",
        "raw_path": b"/api/budget/check",
        "query_string": b"",
        "headers": raw_headers(
            headers
        ),
        "client": (
            "127.0.0.1",
            12345,
        ),
        "server": (
            "127.0.0.1",
            8000,
        ),
        "state": {
            "request_id": request_id,
            "requested_at": (
                "2026-09-09T00:00:00Z"
            ),
        },
    }

    return Request(
        scope
    )


def normalize_response(
    value: Any,
) -> Dict[
    str,
    Any,
]:

    if isinstance(
        value,
        JSONResponse,
    ):

        body = json.loads(
            value.body.decode(
                "utf-8"
            )
        )

        return {
            "status_code": (
                value.status_code
            ),
            "body": body,
        }

    return {
        "status_code": 200,
        "body": value,
    }


def parse_json_log_lines(
    stdout_text: str,
) -> List[
    Dict[
        str,
        Any,
    ]
]:

    output = []

    for line in (
        stdout_text.splitlines()
    ):

        stripped = (
            line.strip()
        )

        if not (
            stripped.startswith(
                "{"
            )
            and
            stripped.endswith(
                "}"
            )
        ):

            continue

        try:

            value = json.loads(
                stripped
            )

        except Exception:

            continue

        if isinstance(
            value,
            dict,
        ):

            output.append(
                value
            )

    return output


def events_of_type(
    logs,
    event_type: str,
):

    return [
        item
        for item
        in logs
        if (
            item.get(
                "event_type"
            )
            ==
            event_type
        )
    ]


# ==============================================================================
# CONTROLLED INVOCATION
# ==============================================================================


async def invoke(
    module,
    *,
    request_id: str,
    approved: bool,
    risk_level: str,
    reason: str,
    headers,
    payload_values,
):

    fake_engine = (
        FakeBudgetEngine(
            approved=approved,
            risk_level=risk_level,
            reason=reason,
        )
    )

    fake_db = (
        FakeBudgetDB()
    )

    old_engine = (
        module.budget_engine
    )

    old_db = (
        module.budget_db
    )

    old_test_mode = (
        module.TEST_MODE
    )

    module.budget_engine = (
        fake_engine
    )

    module.budget_db = (
        fake_db
    )

    module.TEST_MODE = True

    try:

        payload = (
            module.BudgetCheckRequest(
                **payload_values
            )
        )

        request = (
            make_request(
                request_id=request_id,
                headers=headers,
            )
        )

        buffer = io.StringIO()

        with contextlib.redirect_stdout(
            buffer
        ):

            result = await module.check_budget(
                payload,
                request,
            )

        normalized = (
            normalize_response(
                result
            )
        )

        logs = (
            parse_json_log_lines(
                buffer.getvalue()
            )
        )

        return {
            "response": normalized,
            "db_calls": list(
                fake_db.calls
            ),
            "logs": logs,
            "stdout": buffer.getvalue(),
        }

    finally:

        module.budget_engine = (
            old_engine
        )

        module.budget_db = (
            old_db
        )

        module.TEST_MODE = (
            old_test_mode
        )


# ==============================================================================
# TEST CASE
# ==============================================================================


async def compare_case(
    *,
    name: str,
    request_id: str,
    approved: bool,
    risk_level: str,
    reason: str,
    headers,
    payload_values,
):

    result_v01 = await invoke(
        v01,
        request_id=request_id,
        approved=approved,
        risk_level=risk_level,
        reason=reason,
        headers=headers,
        payload_values=payload_values,
    )

    result_v02 = await invoke(
        v02,
        request_id=request_id,
        approved=approved,
        risk_level=risk_level,
        reason=reason,
        headers=headers,
        payload_values=payload_values,
    )

    return {
        "name": name,
        "v01": result_v01,
        "v02": result_v02,
        "response_equal": (
            result_v01[
                "response"
            ]
            ==
            result_v02[
                "response"
            ]
        ),
        "db_equal": (
            result_v01[
                "db_calls"
            ]
            ==
            result_v02[
                "db_calls"
            ]
        ),
    }


# ==============================================================================
# MAIN TEST
# ==============================================================================


async def run_tests():

    print(
        "=" * 80
    )

    print(
        "MAIN SHADOW V02 REGRESSION V0.1 "
        "- CONTROLLED LOCAL TEST"
    )

    print(
        "=" * 80
    )

    base_payload = {
        "agent_id": (
            "regression-agent"
        ),
        "amount": 0.03,
        "currency": "USDC",
        "api_url": (
            "https://example.com/paid"
        ),
        "daily_limit": 5.0,
        "action_type": (
            "x402_payment"
        ),
        "correlation_id": (
            "regression-series"
        ),
    }

    cases = []

    # ------------------------------------------------------------------
    # 1. Standard allow + valid traceparent.
    # ------------------------------------------------------------------

    cases.append(
        await compare_case(
            name=(
                "standard_allow_valid_trace"
            ),
            request_id=(
                "req-v02-reg-01"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[
                (
                    "traceparent",
                    VALID_TRACEPARENT_A,
                ),
            ],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # 2. Existing deny.
    # ------------------------------------------------------------------

    cases.append(
        await compare_case(
            name=(
                "standard_deny"
            ),
            request_id=(
                "req-v02-reg-02"
            ),
            approved=False,
            risk_level="high",
            reason="daily_limit_exceeded",
            headers=[],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # 3. Duplicate traceparent.
    # ------------------------------------------------------------------

    cases.append(
        await compare_case(
            name=(
                "duplicate_traceparent"
            ),
            request_id=(
                "req-v02-reg-03"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[
                (
                    "traceparent",
                    VALID_TRACEPARENT_A,
                ),
                (
                    "traceparent",
                    VALID_TRACEPARENT_B,
                ),
            ],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # 4. Baggage agent identity claim.
    # ------------------------------------------------------------------

    cases.append(
        await compare_case(
            name=(
                "baggage_agent_claim"
            ),
            request_id=(
                "req-v02-reg-04"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[
                (
                    "traceparent",
                    VALID_TRACEPARENT_A,
                ),
                (
                    "baggage",
                    (
                        "agent_id="
                        "caller-claimed-agent"
                    ),
                ),
            ],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # 5. Malformed traceparent.
    # ------------------------------------------------------------------

    cases.append(
        await compare_case(
            name=(
                "malformed_traceparent"
            ),
            request_id=(
                "req-v02-reg-05"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[
                (
                    "traceparent",
                    "not-a-valid-traceparent",
                ),
            ],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # 6. Missing declared action type.
    # ------------------------------------------------------------------

    missing_action_payload = (
        dict(
            base_payload
        )
    )

    missing_action_payload[
        "action_type"
    ] = None

    cases.append(
        await compare_case(
            name=(
                "missing_action_type"
            ),
            request_id=(
                "req-v02-reg-06"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[],
            payload_values=(
                missing_action_payload
            ),
        )
    )

    # ------------------------------------------------------------------
    # 7. Existing invalid amount early-return path.
    # ------------------------------------------------------------------

    invalid_amount_payload = (
        dict(
            base_payload
        )
    )

    invalid_amount_payload[
        "amount"
    ] = -1.0

    cases.append(
        await compare_case(
            name=(
                "invalid_amount"
            ),
            request_id=(
                "req-v02-reg-07"
            ),
            approved=True,
            risk_level="low",
            reason="unused",
            headers=[
                (
                    "traceparent",
                    VALID_TRACEPARENT_A,
                ),
            ],
            payload_values=(
                invalid_amount_payload
            ),
        )
    )

    # ------------------------------------------------------------------
    # 8. Existing unsupported currency early-return path.
    # ------------------------------------------------------------------

    invalid_currency_payload = (
        dict(
            base_payload
        )
    )

    invalid_currency_payload[
        "currency"
    ] = "DOGE"

    cases.append(
        await compare_case(
            name=(
                "unsupported_currency"
            ),
            request_id=(
                "req-v02-reg-08"
            ),
            approved=True,
            risk_level="low",
            reason="unused",
            headers=[],
            payload_values=(
                invalid_currency_payload
            ),
        )
    )

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    tests = []

    tests.append(
        (
            "T01_RUNTIME_CONTEXT_IMPORT_AVAILABLE",
            (
                getattr(
                    v02,
                    "SHADOW_RUNTIME_CONTEXT_AVAILABLE",
                    False,
                )
                is True
            ),
        )
    )

    tests.append(
        (
            "T02_ALL_EXISTING_RESPONSES_EQUAL_V01_V02",
            all(
                case[
                    "response_equal"
                ]
                for case
                in cases
            ),
        )
    )

    tests.append(
        (
            "T03_ALL_EXISTING_DB_CALLS_EQUAL_V01_V02",
            all(
                case[
                    "db_equal"
                ]
                for case
                in cases
            ),
        )
    )

    allow_case = (
        cases[0]
    )

    deny_case = (
        cases[1]
    )

    duplicate_case = (
        cases[2]
    )

    baggage_case = (
        cases[3]
    )

    malformed_case = (
        cases[4]
    )

    missing_action_case = (
        cases[5]
    )

    invalid_amount_case = (
        cases[6]
    )

    invalid_currency_case = (
        cases[7]
    )

    tests.append(
        (
            "T04_ALLOW_DECISION_UNCHANGED",
            (
                allow_case[
                    "v01"
                ][
                    "response"
                ]
                ==
                allow_case[
                    "v02"
                ][
                    "response"
                ]
                and
                allow_case[
                    "v02"
                ][
                    "response"
                ][
                    "body"
                ].get(
                    "approved"
                )
                is True
            ),
        )
    )

    tests.append(
        (
            "T05_DENY_DECISION_UNCHANGED",
            (
                deny_case[
                    "v01"
                ][
                    "response"
                ]
                ==
                deny_case[
                    "v02"
                ][
                    "response"
                ]
                and
                deny_case[
                    "v02"
                ][
                    "response"
                ][
                    "body"
                ].get(
                    "approved"
                )
                is False
            ),
        )
    )

    completed_allow = (
        events_of_type(
            allow_case[
                "v02"
            ][
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_completed"
            ),
        )
    )

    tests.append(
        (
            "T06_V02_NORMAL_PATH_EMITS_RUNTIME_CONTEXT_EVENT",
            (
                len(
                    completed_allow
                )
                ==
                1
            ),
        )
    )

    tests.append(
        (
            "T07_DECISION_ATTEMPT_ID_REMAINS_SERVER_REQUEST_ID",
            (
                len(
                    completed_allow
                )
                ==
                1
                and
                completed_allow[
                    0
                ].get(
                    "decision_attempt_id"
                )
                ==
                "req-v02-reg-01"
            ),
        )
    )

    duplicate_events = (
        events_of_type(
            duplicate_case[
                "v02"
            ][
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_completed"
            ),
        )
    )

    tests.append(
        (
            "T08_DUPLICATE_TRACEPARENT_OBSERVED_WITHOUT_DECISION_CHANGE",
            (
                duplicate_case[
                    "response_equal"
                ]
                and
                len(
                    duplicate_events
                )
                ==
                1
                and
                duplicate_events[
                    0
                ].get(
                    "duplicate_traceparent_observed"
                )
                is True
            ),
        )
    )

    tests.append(
        (
            "T09_DUPLICATE_TRACEPARENT_NOT_USED_AS_INCOMING_TRACE",
            (
                len(
                    duplicate_events
                )
                ==
                1
                and
                duplicate_events[
                    0
                ].get(
                    "incoming_trace_id"
                )
                is None
            ),
        )
    )

    baggage_events = (
        events_of_type(
            baggage_case[
                "v02"
            ][
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_completed"
            ),
        )
    )

    tests.append(
        (
            "T10_BAGGAGE_AGENT_CLAIM_DOES_NOT_CHANGE_BUDGET_DECISION",
            (
                baggage_case[
                    "response_equal"
                ]
                and
                len(
                    baggage_events
                )
                ==
                1
                and
                baggage_events[
                    0
                ].get(
                    "real_caller_identity_authority"
                )
                is False
            ),
        )
    )

    malformed_events = (
        events_of_type(
            malformed_case[
                "v02"
            ][
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_completed"
            ),
        )
    )

    tests.append(
        (
            "T11_MALFORMED_TRACE_DOES_NOT_CHANGE_BUDGET_DECISION",
            (
                malformed_case[
                    "response_equal"
                ]
                and
                len(
                    malformed_events
                )
                ==
                1
            ),
        )
    )

    missing_action_events = (
        events_of_type(
            missing_action_case[
                "v02"
            ][
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_completed"
            ),
        )
    )

    tests.append(
        (
            "T12_MISSING_ACTION_TYPE_REMAINS_OBSERVATION_ONLY",
            (
                missing_action_case[
                    "response_equal"
                ]
                and
                len(
                    missing_action_events
                )
                ==
                1
            ),
        )
    )

    tests.append(
        (
            "T13_INVALID_AMOUNT_EXISTING_PATH_UNCHANGED",
            (
                invalid_amount_case[
                    "response_equal"
                ]
                and
                invalid_amount_case[
                    "v02"
                ][
                    "response"
                ][
                    "body"
                ].get(
                    "approved"
                )
                is False
            ),
        )
    )

    tests.append(
        (
            "T14_UNSUPPORTED_CURRENCY_EXISTING_PATH_UNCHANGED",
            (
                invalid_currency_case[
                    "response_equal"
                ]
                and
                invalid_currency_case[
                    "v02"
                ][
                    "response"
                ][
                    "body"
                ].get(
                    "approved"
                )
                is False
            ),
        )
    )

    tests.append(
        (
            "T15_V02_RUNTIME_EVENTS_NEVER_CLAIM_ENFORCEMENT",
            all(
                event.get(
                    "enforcement_effect"
                )
                is False
                for case
                in cases[:6]
                for event
                in events_of_type(
                    case[
                        "v02"
                    ][
                        "logs"
                    ],
                    (
                        "shadow_runtime_"
                        "context_completed"
                    ),
                )
            ),
        )
    )

    tests.append(
        (
            "T16_V02_RUNTIME_EVENTS_NEVER_CLAIM_NETWORK_TRUST",
            all(
                event.get(
                    "real_network_trust_authority"
                )
                is False
                for case
                in cases[:6]
                for event
                in events_of_type(
                    case[
                        "v02"
                    ][
                        "logs"
                    ],
                    (
                        "shadow_runtime_"
                        "context_completed"
                    ),
                )
            ),
        )
    )

    # ------------------------------------------------------------------
    # Forced v0.2 runtime shadow exception.
    # ------------------------------------------------------------------

    original_run_shadow = (
        v02.run_shadow_insulated
    )

    def forced_failure(
        *args,
        **kwargs,
    ):

        raise RuntimeError(
            "forced_regression_shadow_failure"
        )

    v02.run_shadow_insulated = (
        forced_failure
    )

    try:

        forced_v02 = await invoke(
            v02,
            request_id=(
                "req-v02-reg-forced-error"
            ),
            approved=True,
            risk_level="low",
            reason="within_budget",
            headers=[
                (
                    "traceparent",
                    VALID_TRACEPARENT_A,
                ),
            ],
            payload_values=(
                dict(
                    base_payload
                )
            ),
        )

    finally:

        v02.run_shadow_insulated = (
            original_run_shadow
        )

    baseline_v01 = (
        allow_case[
            "v01"
        ][
            "response"
        ]
    )

    forced_error_events = (
        events_of_type(
            forced_v02[
                "logs"
            ],
            (
                "shadow_runtime_"
                "context_error"
            ),
        )
    )

    tests.append(
        (
            "T17_FORCED_RUNTIME_SHADOW_FAILURE_PRESERVES_RESPONSE",
            (
                forced_v02[
                    "response"
                ]
                ==
                baseline_v01
            ),
        )
    )

    tests.append(
        (
            "T18_FORCED_RUNTIME_SHADOW_FAILURE_IS_OBSERVED",
            (
                len(
                    forced_error_events
                )
                ==
                1
                and
                forced_error_events[
                    0
                ].get(
                    "error_type"
                )
                ==
                "RuntimeError"
            ),
        )
    )

    tests.append(
        (
            "T19_FORCED_RUNTIME_SHADOW_FAILURE_HAS_NO_ENFORCEMENT",
            (
                len(
                    forced_error_events
                )
                ==
                1
                and
                forced_error_events[
                    0
                ].get(
                    "existing_decision_preserved"
                )
                is True
                and
                forced_error_events[
                    0
                ].get(
                    "enforcement_effect"
                )
                is False
            ),
        )
    )

    # ------------------------------------------------------------------
    # Print results.
    # ------------------------------------------------------------------

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
        "CASE SUMMARY"
    )

    for case in cases:

        print(
            json.dumps(
                {
                    "name": (
                        case[
                            "name"
                        ]
                    ),
                    "response_equal": (
                        case[
                            "response_equal"
                        ]
                    ),
                    "db_equal": (
                        case[
                            "db_equal"
                        ]
                    ),
                    "v02_runtime_completed_events": (
                        len(
                            events_of_type(
                                case[
                                    "v02"
                                ][
                                    "logs"
                                ],
                                (
                                    "shadow_runtime_"
                                    "context_completed"
                                ),
                            )
                        )
                    ),
                    "v02_runtime_error_events": (
                        len(
                            events_of_type(
                                case[
                                    "v02"
                                ][
                                    "logs"
                                ],
                                (
                                    "shadow_runtime_"
                                    "context_error"
                                ),
                            )
                        )
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    print()

    print(
        "FORCED SHADOW FAILURE"
    )

    print(
        json.dumps(
            {
                "response_equal_to_v01": (
                    forced_v02[
                        "response"
                    ]
                    ==
                    baseline_v01
                ),
                "error_events": (
                    forced_error_events
                ),
            },
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
        "HTTP_CONTEXT_OBSERVATION != BUDGET_AUTHORITY"
    )

    print(
        "TRACE_CONTEXT != CALLER_IDENTITY"
    )

    print(
        "BAGGAGE_AGENT_ID != AUTHENTICATED_AGENT"
    )

    print(
        "SHADOW_RUNTIME_FAILURE != EXISTING_DECISION_FAILURE"
    )

    print(
        "V02_ADDITIONAL_OBSERVATION != EXISTING_RESPONSE_CHANGE"
    )

    print()

    if passed == len(
        tests
    ):

        print(
            "MAIN_SHADOW_V02_REGRESSION="
            "OBSERVED_IN_CONTROLLED_LOCAL_TEST"
        )

        print(
            "EXISTING_DECISION_BEHAVIOR="
            "UNCHANGED_IN_TESTED_CASES"
        )

    else:

        print(
            "MAIN_SHADOW_V02_REGRESSION="
            "NOT_ESTABLISHED"
        )

        print(
            "EXISTING_DECISION_BEHAVIOR="
            "NOT_ESTABLISHED"
        )

    print(
        "GITHUB_WRITE="
        "NOT_PERFORMED"
    )

    print(
        "RENDER_DEPLOY="
        "NOT_PERFORMED"
    )

    print(
        "PRODUCTION_INTEGRATION="
        "NOT_ESTABLISHED"
    )


if __name__ == "__main__":

    asyncio.run(
        run_tests()
    )