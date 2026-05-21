#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-budget-guard insulation tests v2
Tests /api/budget/check via FastAPI ASGI (TEST_MODE=true, mocked DB)
No HTTP/x402 payment required.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "postgresql://postgres@localhost:5432/test_dummy"

import database as db_module

async def mock_noop(*args, **kwargs): return None
async def mock_zero(*args, **kwargs): return 0.0
async def mock_half(*args, **kwargs): return 0.5
async def mock_empty_list(*args, **kwargs): return []
async def mock_rules(*args, **kwargs): return {"daily_limit": 5.0, "monthly_limit": 150.0}
async def mock_create_rules(agent_id, daily_limit=5.0, monthly_limit=150.0):
    return {"daily_limit": daily_limit, "monthly_limit": monthly_limit}
async def mock_stats(*args, **kwargs):
    return {"total_agents": 0, "daily_spending": {}, "top_apis": [], "anomalies_detected": []}

db = db_module.budget_db
db.initialize              = mock_noop
db.test_connection         = mock_noop
db.get_budget_rules        = mock_rules
db.create_budget_rules     = mock_create_rules
db.get_daily_spending      = mock_zero
db.get_monthly_spending    = mock_zero
db.log_budget_check        = mock_noop
db.log_anomaly_alert       = mock_noop
db.get_recent_api_payments = mock_empty_list
db.get_average_payment     = mock_zero
db.get_agent_known_apis    = mock_empty_list
db.get_night_spending_pattern = mock_half
db.get_hourly_spending     = mock_zero
db.record_transaction      = mock_noop
db.get_agent_transactions  = mock_empty_list
db.get_agent_alerts        = mock_empty_list
db.get_budget_statistics   = mock_stats

import main as _main_module
from main import app
import httpx

results = []

def _case(label, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    results.append((status, label, detail))
    print(f"{status} {label}: {detail}")

async def run_tests():
    print("=" * 68)
    print("agent-budget-guard Internal Tests v2 (TEST_MODE=true, mocked DB)")
    print("=" * 68)

    try:
        transport = httpx.ASGITransport(app=app)
    except AttributeError:
        from httpx._transports.asgi import ASGITransport
        transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # ---- original 7 cases (re-validated with fixes) ----

        # Case 1: small amount -> approved / low
        r = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0.01,
            "daily_limit": 1.0, "currency": "USDC"
        })
        b = r.json()
        _case("Case1 small amount (0.01/limit 1.0) -> allowed/low",
              r.status_code == 200 and b.get("approved") is True and b.get("risk_level") == "low",
              f"status={r.status_code} approved={b.get('approved')} risk={b.get('risk_level')}")

        # Case 2: daily limit exceeded -> denied
        r2 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent-over", "amount": 0.99, "daily_limit": 0.50
        })
        b2 = r2.json()
        _case("Case2 daily limit exceeded (0.99/limit 0.50) -> denied",
              r2.status_code == 200 and b2.get("approved") is False,
              f"status={r2.status_code} approved={b2.get('approved')} risk={b2.get('risk_level')}")

        # Case 3: agent_id omitted -> no 500
        r3 = await client.post("/api/budget/check", json={"amount": 0.01})
        b3 = r3.json()
        _case("Case3 agent_id omitted (no 500)",
              r3.status_code != 500,
              f"status={r3.status_code} approved={b3.get('approved')}")

        # Case 4: amount=-1 -> denied (FIXED)
        r4 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": -1, "daily_limit": 5.0
        })
        b4 = r4.json()
        _case("Case4 amount=-1 -> denied (fixed)",
              r4.status_code == 200 and b4.get("approved") is False,
              f"status={r4.status_code} approved={b4.get('approved')} risk={b4.get('risk_level')}")

        # Case 5: amount=9999 extreme -> denied / high
        r5 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 9999.0, "daily_limit": 5.0
        })
        b5 = r5.json()
        _case("Case5 amount=9999 extreme -> denied/high",
              r5.status_code == 200 and b5.get("approved") is False and b5.get("risk_level") == "high",
              f"status={r5.status_code} approved={b5.get('approved')} risk={b5.get('risk_level')}")

        # Case 6: currency=XYZ -> denied/requires_review (FIXED)
        r6 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0.01,
            "currency": "XYZ", "daily_limit": 5.0
        })
        b6 = r6.json()
        _case("Case6 currency=XYZ -> denied/requires_review (fixed)",
              r6.status_code == 200 and b6.get("approved") is False,
              f"status={r6.status_code} approved={b6.get('approved')} risk={b6.get('risk_level')}")

        # Case 7: empty JSON -> no 500
        r7 = await client.post("/api/budget/check", json={})
        b7 = r7.json()
        _case("Case7 empty JSON all defaults (no 500)",
              r7.status_code != 500,
              f"status={r7.status_code} approved={b7.get('approved')}")

        # ---- new validation cases ----
        print("\n--- Additional validation test cases ---")

        # New1: amount=0 -> denied
        rn1 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0, "daily_limit": 5.0
        })
        bn1 = rn1.json()
        _case("New1 amount=0 -> denied",
              rn1.status_code == 200 and bn1.get("approved") is False,
              f"status={rn1.status_code} approved={bn1.get('approved')} risk={bn1.get('risk_level')}")

        # New2: amount="abc" -> Pydantic 422 (not 500)
        rn2 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": "abc"
        })
        _case("New2 amount='abc' -> 422 not 500",
              rn2.status_code == 422,
              f"status={rn2.status_code} (Pydantic coercion failure)")

        # New3: currency="JPYC" -> normal budget rules apply (supported)
        rn3 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0.01,
            "currency": "JPYC", "daily_limit": 5.0
        })
        bn3 = rn3.json()
        _case("New3 currency=JPYC -> approved (supported currency)",
              rn3.status_code == 200 and bn3.get("approved") is True,
              f"status={rn3.status_code} approved={bn3.get('approved')}")

        # New4: currency="USDC" -> normal budget rules apply (supported)
        rn4 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0.01,
            "currency": "USDC", "daily_limit": 5.0
        })
        bn4 = rn4.json()
        _case("New4 currency=USDC -> approved (supported currency)",
              rn4.status_code == 200 and bn4.get("approved") is True,
              f"status={rn4.status_code} approved={bn4.get('approved')}")

        # New5: currency="usdc" (lowercase) -> supported (case-insensitive)
        rn5 = await client.post("/api/budget/check", json={
            "agent_id": "test-agent", "amount": 0.01,
            "currency": "usdc", "daily_limit": 5.0
        })
        bn5 = rn5.json()
        _case("New5 currency='usdc' lowercase -> approved (case-insensitive)",
              rn5.status_code == 200 and bn5.get("approved") is True,
              f"status={rn5.status_code} approved={bn5.get('approved')}")

    # ---- syntax check ----
    try:
        import py_compile
        py_compile.compile(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
            doraise=True
        )
        _case("main.py syntax check", True, "compilation OK")
    except py_compile.PyCompileError as e:
        _case("main.py syntax check", False, str(e))

    # ---- risk level unit tests ----
    print("\n--- BudgetEngine._calculate_risk_level unit tests ---")
    from budget_engine import BudgetEngine
    engine = BudgetEngine()

    _case("risk_level 0.2%",  engine._calculate_risk_level(0.01, 5.0) == "low",    f"-> {engine._calculate_risk_level(0.01, 5.0)}")
    _case("risk_level 80%",   engine._calculate_risk_level(4.0,  5.0) == "medium", f"-> {engine._calculate_risk_level(4.0, 5.0)}")
    _case("risk_level 100%",  engine._calculate_risk_level(5.0,  5.0) == "high",   f"-> {engine._calculate_risk_level(5.0, 5.0)}")
    _case("risk_level 120%",  engine._calculate_risk_level(6.0,  5.0) == "high",   f"-> {engine._calculate_risk_level(6.0, 5.0)}")

    # ---- summary ----
    print("\n" + "=" * 68)
    total        = len(results)
    passed_count = sum(1 for s, _, _ in results if s == "[PASS]")
    failed_count = total - passed_count
    print(f"Total: {total} / Pass: {passed_count} / Fail: {failed_count}")

    if failed_count:
        print("\nFailed cases:")
        for s, label, detail in results:
            if s == "[FAIL]":
                print(f"  {label}: {detail}")
    else:
        print("All tests passed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
